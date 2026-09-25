<script setup lang="ts">
import { computed, ref } from "vue";
import ChessBoard from "./ChessBoard.vue";
import type { Engine } from "../engine/engine";
import type { Color, GameState } from "../engine/types";
import raw from "../../../data/puzzles.tsv?raw";
import { t, type Lang } from "../i18n";
import { themeLabel } from "../puzzleThemes";

// Puzzles from the Lichess puzzle database (CC0), chosen by
// python/puzzles.py. A puzzle's first move is the opponent's, played for
// the player; the player finds the rest. On the last move any mate counts,
// as on Lichess.
interface Puzzle { id: string; fen: string; moves: string[]; rating: number; themes: string[] }
const PUZZLES: Puzzle[] = raw
  .split("\n")
  .filter((l) => l && !l.startsWith("#"))
  .map((l) => {
    const [id, fen, moves, rating, themes] = l.split("\t");
    return { id, fen, moves: moves.split(" "), rating: Number(rating), themes: themes ? themes.split(" ") : [] };
  });

const props = defineProps<{ engine: Engine; lang: Lang }>();
const S = computed(() => t(props.lang));

// ---- the player's puzzle record
interface Record_ { rating: number; played: number; streak: number; seen: string[] }
const KEY = "simorgh.puzzles";
function loadRecord(): Record_ {
  try {
    const r = JSON.parse(localStorage.getItem(KEY) ?? "null");
    if (r && typeof r.rating === "number") return { rating: r.rating, played: r.played ?? 0, streak: r.streak ?? 0, seen: r.seen ?? [] };
  } catch {
    /* start fresh */
  }
  return { rating: 1200, played: 0, streak: 0, seen: [] };
}
const record = ref<Record_>(loadRecord());
function saveRecord() {
  try {
    localStorage.setItem(KEY, JSON.stringify(record.value));
  } catch {
    /* not remembered, still playable */
  }
}

// ---- the current puzzle
const puzzle = ref<Puzzle | null>(null);
const step = ref(0); // moves of the solution played so far, the setup move included
const state = ref<GameState | null>(null);
const busy = ref(false);
const failed = ref(false); // a wrong move, a hint or the solution: this one is lost
const wrongNow = ref(false);
const finished = ref(false);
const delta = ref<number | null>(null);
const hint = ref<string[]>([]);

const player = computed<Color>(() => (puzzle.value?.fen.split(" ")[1] === "w" ? "b" : "w"));
const yourTurn = computed(
  () => !!state.value && !busy.value && !finished.value && state.value.status.stm === player.value
);

const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function show() {
  state.value = await props.engine.snapshot(puzzle.value!.moves.slice(0, step.value), puzzle.value!.fen);
}

function pickNext(): Puzzle {
  const seen = new Set(record.value.seen);
  const r = record.value.rating;
  for (const spread of [75, 150, 300, 3000]) {
    const near = PUZZLES.filter((p) => !seen.has(p.id) && Math.abs(p.rating - r) <= spread);
    if (near.length) return near[Math.floor(Math.random() * near.length)];
  }
  record.value.seen = []; // every puzzle done: start the round again
  return PUZZLES[Math.floor(Math.random() * PUZZLES.length)];
}

async function next() {
  puzzle.value = pickNext();
  step.value = 0;
  failed.value = wrongNow.value = finished.value = false;
  delta.value = null;
  hint.value = [];
  busy.value = true;
  await show();
  await pause(600);
  step.value = 1; // the opponent's move that sets the puzzle
  await show();
  busy.value = false;
}
next();

/** Score the puzzle once, the first time it is settled. */
function settle(solved: boolean) {
  if (finished.value) return;
  finished.value = true;
  const rec = record.value;
  const p = puzzle.value!;
  const expected = 1 / (1 + Math.pow(10, (p.rating - rec.rating) / 400));
  const k = rec.played < 20 ? 40 : 20; // settle quickly at first
  const change = Math.round(k * ((solved ? 1 : 0) - expected));
  rec.rating = Math.max(100, rec.rating + change);
  rec.played += 1;
  rec.streak = solved ? rec.streak + 1 : 0;
  rec.seen = [...rec.seen, p.id];
  delta.value = change;
  record.value = { ...rec };
  saveRecord();
}

async function onMove(uci: string) {
  if (!yourTurn.value) return;
  const p = puzzle.value!;
  const expected = p.moves[step.value];
  hint.value = [];
  const before = p.moves.slice(0, step.value);
  const after = await props.engine.snapshot([...before, uci], p.fen);
  const mates = after.status.legal === 0 && after.status.incheck;
  if (uci !== expected && !mates) {
    failed.value = true;
    wrongNow.value = true;
    return; // not played: the board is redrawn as it was
  }
  wrongNow.value = false;
  if (uci !== expected) {
    // A different mate: the puzzle is solved all the same.
    state.value = after;
    settle(!failed.value);
    return;
  }
  step.value += 1;
  state.value = after;
  if (step.value >= p.moves.length) return settle(!failed.value);
  busy.value = true;
  await pause(450);
  step.value += 1; // the opponent's reply
  await show();
  busy.value = false;
  if (step.value >= p.moves.length) settle(!failed.value);
}

function showHint() {
  if (!yourTurn.value) return;
  failed.value = true;
  const m = puzzle.value!.moves[step.value];
  hint.value = [m.slice(0, 2)];
}

async function showSolution() {
  if (finished.value || busy.value) return;
  failed.value = true;
  settle(false);
  busy.value = true;
  const p = puzzle.value!;
  while (step.value < p.moves.length) {
    await pause(650);
    step.value += 1;
    await show();
  }
  busy.value = false;
}

const lastMove = computed(() => (puzzle.value && step.value > 0 ? puzzle.value.moves[step.value - 1] : null));
</script>

<template>
  <main class="puzzles">
    <aside class="side-panel">
      <div class="card stat">
        <div class="label">{{ S.pzRating }}</div>
        <div class="rating" dir="ltr">
          {{ record.rating }}
          <span v-if="delta !== null" class="delta" :class="{ up: delta > 0, down: delta < 0 }">
            {{ delta > 0 ? "+" : "" }}{{ delta }}
          </span>
        </div>
        <div class="row"><span>{{ S.pzPlayed }}</span><b>{{ record.played }}</b></div>
        <div class="row"><span>{{ S.pzStreak }}</span><b>{{ record.streak }}</b></div>
      </div>
      <p class="note">{{ S.pzSource }}</p>
    </aside>

    <section class="center">
      <div class="board-col">
        <ChessBoard
          v-if="state"
          :fen="state.fen"
          :legal="yourTurn ? state.legal : new Set()"
          :orientation="player"
          :stm="state.status.stm"
          :last-move="lastMove"
          :check-square="null"
          :interactive="yourTurn"
          :hint="hint"
          @move="onMove"
        />
      </div>
    </section>

    <aside class="side-panel">
      <div class="card">
        <div class="to-move">
          <span class="dot" :class="player" />
          {{ player === "w" ? S.pzWhiteToMove : S.pzBlackToMove }}
        </div>
        <div v-if="finished" class="verdict" :class="{ good: !failed }">
          {{ failed ? S.pzFailed : S.pzSolved }}
        </div>
        <div v-else-if="wrongNow" class="verdict bad">{{ S.pzWrong }}</div>
        <div v-else class="verdict">{{ S.pzFind }}</div>

        <div v-if="finished && puzzle" class="info">
          <div class="row"><span>{{ S.pzPuzzleRating }}</span><b dir="ltr">{{ puzzle.rating }}</b></div>
          <div v-if="puzzle.themes.length" class="themes">
            <span v-for="th in puzzle.themes" :key="th" class="theme">{{ themeLabel(th, lang) }}</span>
          </div>
        </div>

        <div class="buttons">
          <button v-if="!finished" :disabled="!yourTurn" @click="showHint">{{ S.egHint }}</button>
          <button v-if="!finished" :disabled="busy" @click="showSolution">{{ S.pzSolution }}</button>
          <button class="primary" :disabled="busy" @click="next">{{ S.pzNext }}</button>
        </div>
      </div>
    </aside>
  </main>
</template>

<style scoped>
.puzzles {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 230px minmax(320px, 1fr) 340px;
  gap: 18px;
}
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.center {
  display: flex;
  justify-content: center;
  min-width: 0;
}
.board-col {
  flex: 1;
  min-width: 0;
  max-width: min(72vh, 100%);
}
.card {
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stat .label {
  font-size: 11px;
  color: var(--muted);
}
.rating {
  font-size: 34px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.delta {
  font-size: 15px;
  font-weight: 700;
  margin-left: 6px;
}
.delta.up { color: var(--ok); }
.delta.down { color: #e0534a; }
.row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--fg-dim);
}
.row b {
  color: var(--fg);
}
.note {
  margin: 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--muted);
}
.to-move {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid var(--border);
}
.dot.w { background: #eef1f4; }
.dot.b { background: #262c34; }
.verdict {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 13.5px;
  line-height: 1.6;
}
.verdict.good {
  border-color: var(--ok);
  color: var(--ok);
  font-weight: 700;
}
.verdict.bad {
  border-color: #e0534a;
}
.info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.themes {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.theme {
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--accent-dim);
  color: var(--on-accent-dim);
  font-size: 11.5px;
}
.buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.buttons button {
  flex: 1;
  padding: 8px 10px;
  font-size: 13px;
}
</style>
