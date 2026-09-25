<script setup lang="ts">
import { computed, ref, watch } from "vue";
import ChessBoard from "./ChessBoard.vue";
import type { Engine } from "../engine/engine";
import type { Color, GameState } from "../engine/types";
import data from "../../../data/endgames.json";
import { t, type Lang } from "../i18n";

// The endgame lessons: data/endgames.json, built and checked against the
// Syzygy tablebase by python/endgames.py and shared with the Android app.
interface Text { fa: string; en: string }
interface Endgame {
  id: string;
  group: string;
  goal: "mate" | "promote" | "hold";
  limit: number; // the player's moves
  fen: string;
  side: Color;
  name: Text;
  summary: Text;
  steps: { fa: string[]; en: string[] };
}
const GROUPS: { id: string; fa: string; en: string }[] = data.groups;
const ENDGAMES = data.endgames as Endgame[];

const props = defineProps<{ engine: Engine; lang: Lang }>();
const S = computed(() => t(props.lang));

const KEY = "simorgh.endgames";
function loadDone(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "{}");
  } catch {
    return {};
  }
}
const done = ref<Record<string, boolean>>(loadDone());

const selId = ref(ENDGAMES[0].id);
const eg = computed(() => ENDGAMES.find((e) => e.id === selId.value) ?? ENDGAMES[0]);
const moves = ref<string[]>([]);
const sans = ref<string[]>([]);
const state = ref<GameState | null>(null);
const thinking = ref(false);
const hint = ref<string[]>([]);
const result = ref<null | { won: boolean; why: string }>(null);

const playerMoves = computed(() => Math.ceil(moves.value.length / 2));
const yourTurn = computed(
  () => !!state.value && !thinking.value && !result.value && state.value.status.stm === eg.value.side
);

async function refresh() {
  state.value = await props.engine.snapshot(moves.value, eg.value.fen);
}

async function start(id: string = selId.value) {
  selId.value = id;
  moves.value = [];
  sans.value = [];
  hint.value = [];
  result.value = null;
  await props.engine.newGame();
  await refresh();
}
watch(() => props.engine, () => start(), { immediate: true });

function pawnsOf(c: Color): number {
  const board = state.value?.fen.split(" ")[0] ?? "";
  return [...board].filter((ch) => ch === (c === "w" ? "P" : "p")).length;
}

/** Whether the last move settled the lesson, one way or the other. */
function judge(lastUci: string, byPlayer: boolean) {
  const st = state.value!;
  const e = eg.value;
  const noMoves = st.status.legal === 0;
  const mated = noMoves && st.status.incheck;
  const promoted = lastUci.length === 5;
  const other: Color = e.side === "w" ? "b" : "w";
  const finish = (won: boolean, why: string) => {
    result.value = { won, why };
    if (won) {
      done.value = { ...done.value, [e.id]: true };
      try {
        localStorage.setItem(KEY, JSON.stringify(done.value));
      } catch {
        /* the tick just is not remembered */
      }
    }
  };

  if (e.goal === "hold") {
    if (mated && byPlayer) return finish(true, S.value.egWonMate);
    if (mated) return finish(false, S.value.egLostMated);
    if (!byPlayer && promoted) return finish(false, S.value.egLostPromoted);
    if (noMoves) return finish(true, S.value.egWonStalemate);
    if (pawnsOf(other) === 0) return finish(true, S.value.egWonNoPawns);
    if (byPlayer && playerMoves.value >= e.limit) return finish(true, S.value.egWonHeld);
    return;
  }
  if (mated && byPlayer) return finish(true, S.value.egWonMate);
  if (mated) return finish(false, S.value.egLostMated);
  if (noMoves) return finish(false, S.value.egLostStalemate);
  if (e.goal === "promote" && byPlayer && promoted) return finish(true, S.value.egWonPromoted);
  if (e.goal === "promote" && pawnsOf(e.side) === 0) return finish(false, S.value.egLostPawn);
  if (st.status.halfmove >= 100) return finish(false, S.value.egLostFifty);
  if (byPlayer && playerMoves.value >= e.limit) return finish(false, S.value.egLostLimit);
}

async function onMove(uci: string) {
  if (!yourTurn.value) return;
  hint.value = [];
  sans.value.push(state.value?.san.get(uci) ?? uci);
  moves.value.push(uci);
  await refresh();
  judge(uci, true);
  if (result.value) return;

  // The engine defends (or attacks) at full strength, whatever the game's
  // strength setting: the lesson is only worth anything against best play.
  thinking.value = true;
  try {
    const a = await props.engine.analyse(moves.value, 700, eg.value.fen);
    if (!a) return;
    sans.value.push(state.value?.san.get(a.best) ?? a.best);
    moves.value.push(a.best);
    await refresh();
    judge(a.best, false);
  } finally {
    thinking.value = false;
  }
}

async function showHint() {
  if (!yourTurn.value) return;
  const a = await props.engine.analyse(moves.value, 500, eg.value.fen);
  if (a) hint.value = [a.best.slice(0, 2), a.best.slice(2, 4)];
}

const goalText = computed(() => {
  const e = eg.value;
  const key = e.goal === "mate" ? "egGoalMate" : e.goal === "promote" ? "egGoalPromote" : "egGoalHold";
  return S.value[key].replace("{n}", String(e.limit));
});

const pairs = computed(() => {
  // Numbered as the game would be, from whoever moves first in the position.
  const blackFirst = eg.value.fen.split(" ")[1] === "b";
  const out: string[] = [];
  sans.value.forEach((s, i) => {
    const ply = i + (blackFirst ? 1 : 0);
    if (ply % 2 === 0) out.push(`${ply / 2 + 1}.`);
    else if (i === 0) out.push(`${(ply + 1) / 2}...`);
    out.push(s);
  });
  return out.join(" ");
});
</script>

<template>
  <main class="endgames">
    <aside class="list">
      <div v-for="g in GROUPS" :key="g.id" class="group">
        <div class="group-label">{{ g[lang] }}</div>
        <button
          v-for="e in ENDGAMES.filter((x) => x.group === g.id)"
          :key="e.id"
          class="item"
          :class="{ on: e.id === selId }"
          @click="start(e.id)"
        >
          <span class="side" :class="e.side" />
          <span class="item-name">{{ e.name[lang] }}</span>
          <span v-if="done[e.id]" class="tick">✓</span>
        </button>
      </div>
    </aside>

    <section class="center">
      <div class="board-col">
        <ChessBoard
          v-if="state"
          :fen="state.fen"
          :legal="yourTurn ? state.legal : new Set()"
          :orientation="eg.side"
          :stm="state.status.stm"
          :last-move="moves[moves.length - 1] ?? null"
          :check-square="null"
          :interactive="yourTurn"
          :hint="hint"
          @move="onMove"
        />
        <div class="bar">
          <span class="count">{{ S.egMoves }} <b dir="ltr">{{ playerMoves }} / {{ eg.limit }}</b></span>
          <button :disabled="!yourTurn" @click="showHint">{{ S.egHint }}</button>
          <button @click="start()">{{ S.restart }}</button>
        </div>
        <div v-if="sans.length" class="line" dir="ltr">{{ pairs }}</div>
      </div>
    </section>

    <aside class="panel">
      <div class="card">
        <h2>{{ eg.name[lang] }}</h2>
        <p class="summary">{{ eg.summary[lang] }}</p>
        <div class="goal">{{ goalText }}</div>
        <div class="sub">{{ S.egHow }}</div>
        <ol class="steps">
          <li v-for="(s, i) in eg.steps[lang]" :key="i">{{ s }}</li>
        </ol>
      </div>
      <div v-if="result" class="card result" :class="{ won: result.won }">
        <div class="result-title">{{ result.won ? S.egWon : S.egLost }}</div>
        <div class="result-body">{{ result.why }}</div>
        <button class="block" @click="start()">{{ S.again }}</button>
      </div>
      <div v-else-if="thinking" class="card thinking">{{ S.thinking }}</div>
      <div v-else class="card thinking">{{ S.egYourMove }}</div>
    </aside>
  </main>
</template>

<style scoped>
.endgames {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 230px minmax(320px, 1fr) 340px;
  gap: 18px;
}
.list,
.panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow-y: auto;
}
.group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.group-label {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin: 4px;
}
.item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: none;
  text-align: start;
  color: var(--fg-dim);
  font-size: 13px;
}
.item:hover {
  background: var(--surface);
}
.item.on {
  background: var(--surface);
  border-color: var(--accent);
  color: var(--fg);
  font-weight: 600;
}
.item-name {
  flex: 1;
}
.tick {
  color: var(--ok);
  font-weight: 800;
}
.side {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid var(--border);
}
.side.w { background: #eef1f4; }
.side.b { background: #262c34; }
.center {
  display: flex;
  justify-content: center;
  min-width: 0;
}
.board-col {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-width: 0;
  max-width: min(68vh, 100%);
}
.bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bar .count {
  flex: 1;
  font-size: 13px;
  color: var(--fg-dim);
}
.bar button {
  padding: 7px 14px;
  font-size: 13px;
}
.line {
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 13px;
  color: var(--fg-dim);
  line-height: 1.7;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  padding: 16px;
}
h2 {
  margin: 0 0 8px;
  font-size: 18px;
}
.summary {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--fg-dim);
}
.goal {
  padding: 8px 10px;
  margin-bottom: 12px;
  border-radius: var(--radius-sm);
  background: var(--accent-dim);
  color: var(--on-accent-dim);
  font-size: 13px;
  font-weight: 600;
}
.sub {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 6px;
}
.steps {
  margin: 0;
  padding-inline-start: 20px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--fg);
}
.result {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-color: #e0534a;
}
.result.won {
  border-color: var(--ok);
  background: color-mix(in srgb, var(--ok) 10%, var(--surface));
}
.result-title {
  font-size: 16px;
  font-weight: 800;
}
.result-body {
  font-size: 13px;
  color: var(--fg-dim);
  line-height: 1.6;
}
.thinking {
  font-size: 13px;
  color: var(--fg-dim);
}
.block {
  width: 100%;
}
</style>
