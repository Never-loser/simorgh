<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ChessBoard from "./ChessBoard.vue";
import type { Engine } from "../engine/engine";
import type { Color, GameState } from "../engine/types";
import { GROUPS, LESSONS, type Lesson } from "../lessons";
import { t, termLabel, type Lang } from "../i18n";

const props = defineProps<{ engine: Engine; lang: Lang }>();
const emit = defineEmits<{
  (e: "continue", game: { moves: string[]; sans: string[]; side: Color }): void;
}>();
const S = computed(() => t(props.lang));

const KEY = "simorgh.lesson";
function savedLesson(): string {
  try {
    const v = localStorage.getItem(KEY);
    if (v && LESSONS.some((l) => l.id === v)) return v;
  } catch {
    /* storage unavailable: start at the first lesson */
  }
  return LESSONS[0].id;
}

const lessonId = ref(savedLesson());
const step = ref(0); // plies of the line played so far
const flipped = ref(false);
const lesson = computed<Lesson>(() => LESSONS.find((l) => l.id === lessonId.value) ?? LESSONS[0]);
const total = computed(() => lesson.value.moves.length);
const orientation = computed<Color>(() => {
  const side = lesson.value.side;
  return flipped.value ? (side === "w" ? "b" : "w") : side;
});

function pick(id: string) {
  lessonId.value = id;
  step.value = 0;
  flipped.value = false;
  try {
    localStorage.setItem(KEY, id);
  } catch {
    /* not remembering the lesson is fine */
  }
}

// ---- positions, asked of the engine and kept per lesson and step
const snaps = ref(new Map<string, GameState>());
const key = (s: number) => `${lessonId.value}:${s}`;
async function need(s: number) {
  const k = key(s);
  if (snaps.value.has(k)) return;
  const moves = lesson.value.moves.slice(0, s).map((m) => m.uci);
  const st = await props.engine.snapshot(moves);
  snaps.value.set(k, st);
  snaps.value = new Map(snaps.value);
}
watch(
  [lessonId, step],
  async () => {
    await need(step.value);
    if (step.value > 0) await need(step.value - 1);
  },
  { immediate: true }
);

// Keep showing the last position while the next one is on its way, rather
// than flashing an empty board.
const shown = ref<GameState | null>(null);
watch(
  () => snaps.value.get(key(step.value)),
  (s) => {
    if (s) shown.value = s;
  },
  { immediate: true }
);

const current = computed(() => (step.value > 0 ? lesson.value.moves[step.value - 1] : null));
const moveNumber = computed(() => Math.ceil(step.value / 2));
const moverIsWhite = computed(() => step.value % 2 === 1);

// ---- what the move changed, term by term, as the engine sees it
const delta = computed(() => {
  if (step.value === 0) return null;
  const before = snaps.value.get(key(step.value - 1))?.explain;
  const after = snaps.value.get(key(step.value))?.explain;
  if (!before || !after) return null;
  const names = new Set([...before.terms, ...after.terms].map((x) => x.name));
  const get = (e: typeof before, n: string) => e.terms.find((x) => x.name === n)?.cp ?? 0;
  const rows = [...names]
    .filter((n) => n !== "rounding")
    .map((n) => ({ name: n, cp: get(after, n) - get(before, n) }))
    .filter((r) => Math.abs(r.cp) >= 5)
    .sort((a, b) => Math.abs(b.cp) - Math.abs(a.cp))
    .slice(0, 3);
  return { rows, from: before.white, to: after.white };
});

function pawns(cp: number): string {
  const v = cp / 100;
  return (v > 0 ? "+" : v < 0 ? "−" : "±") + Math.abs(v).toFixed(2);
}

// ---- navigation
function go(s: number) {
  step.value = Math.max(0, Math.min(total.value, s));
}
function onKey(e: KeyboardEvent) {
  if (e.key === "ArrowRight") go(step.value + 1);
  else if (e.key === "ArrowLeft") go(step.value - 1);
  else if (e.key === "Home") go(0);
  else if (e.key === "End") go(total.value);
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));

const pairs = computed(() => {
  const out: { n: number; w: number; b: number | null }[] = [];
  for (let i = 0; i < total.value; i += 2) out.push({ n: i / 2 + 1, w: i, b: i + 1 < total.value ? i + 1 : null });
  return out;
});

function continueGame() {
  const line = lesson.value.moves.slice(0, step.value);
  emit("continue", {
    moves: line.map((m) => m.uci),
    sans: line.map((m) => m.san),
    side: lesson.value.side,
  });
}
</script>

<template>
  <main class="lessons">
    <!-- lesson list -->
    <aside class="list">
      <div v-for="g in GROUPS" :key="g.id" class="group">
        <div class="group-label">{{ g[lang] }}</div>
        <button
          v-for="l in LESSONS.filter((x) => x.group === g.id)"
          :key="l.id"
          class="item"
          :class="{ on: l.id === lessonId }"
          @click="pick(l.id)"
        >
          <span class="side" :class="l.side" />
          <span class="item-name">{{ l.name[lang] }}</span>
          <span class="item-eco" dir="ltr">{{ l.eco }}</span>
        </button>
      </div>
    </aside>

    <!-- board and the line -->
    <section class="center">
      <div class="board-col">
        <ChessBoard
          v-if="shown"
          :fen="shown.fen"
          :legal="new Set()"
          :orientation="orientation"
          :stm="shown.status.stm"
          :last-move="current?.uci ?? null"
          :check-square="null"
          :interactive="false"
        />
        <div class="nav" dir="ltr">
          <button :disabled="step === 0" @click="go(0)" :title="S.first">⏮</button>
          <button :disabled="step === 0" @click="go(step - 1)" :title="S.prev">◀</button>
          <span class="count">{{ step }} / {{ total }}</span>
          <button class="next" :disabled="step === total" @click="go(step + 1)" :title="S.next">▶</button>
          <button :disabled="step === total" @click="go(total)" :title="S.last">⏭</button>
          <button class="flip" @click="flipped = !flipped" :title="S.flip">⇅</button>
        </div>
        <div class="line" dir="ltr">
          <span v-for="p in pairs" :key="p.n" class="pair">
            <span class="num">{{ p.n }}.</span>
            <button class="mv" :class="{ cur: step === p.w + 1, past: step > p.w }" @click="go(p.w + 1)">
              {{ lesson.moves[p.w].san }}
            </button>
            <button
              v-if="p.b !== null"
              class="mv"
              :class="{ cur: step === p.b + 1, past: step > p.b }"
              @click="go(p.b + 1)"
            >{{ lesson.moves[p.b].san }}</button>
          </span>
        </div>
      </div>
    </section>

    <!-- the lesson -->
    <aside class="panel">
      <div class="card">
        <h2>{{ lesson.name[lang] }}</h2>
        <div class="named" dir="ltr">
          <span class="eco">{{ lesson.eco }}</span>
          <span class="table-name">{{ lesson.tableName }}</span>
        </div>
        <p class="summary">{{ lesson.summary[lang] }}</p>
        <div class="sub">{{ S.keyIdeas }}</div>
        <ul class="ideas">
          <li v-for="(idea, i) in lesson.ideas[lang]" :key="i">{{ idea }}</li>
        </ul>
        <div class="plays-as">
          <span class="side" :class="lesson.side" />
          {{ lesson.side === "w" ? S.lessonAsWhite : S.lessonAsBlack }}
        </div>
      </div>

      <div class="card move-card">
        <template v-if="current">
          <div class="move-head">
            <span class="side" :class="moverIsWhite ? 'w' : 'b'" />
            <span class="move-san" dir="ltr">{{ moveNumber }}{{ moverIsWhite ? "." : "..." }} {{ current.san }}</span>
          </div>
          <p class="note">{{ current[lang] }}</p>

          <div v-if="delta" class="delta">
            <div class="sub">{{ S.engineSees }}</div>
            <div v-for="r in delta.rows" :key="r.name" class="delta-row">
              <span>{{ termLabel(r.name, lang) }}</span>
              <span class="dv" :class="r.cp > 0 ? 'pos' : 'neg'" dir="ltr">{{ pawns(r.cp) }}</span>
            </div>
            <div v-if="delta.rows.length === 0" class="quiet">{{ S.noChange }}</div>
            <div class="delta-total">
              <span>{{ S.evaluation2 }}</span>
              <span dir="ltr">{{ pawns(delta.from) }} → <b>{{ pawns(delta.to) }}</b></span>
            </div>
            <div class="legend">{{ S.deltaLegend }}</div>
          </div>
        </template>
        <p v-else class="note start">{{ S.lessonStart }}</p>

        <button class="primary block" @click="continueGame">{{ S.continueVsEngine }}</button>
      </div>
    </aside>
  </main>
</template>

<style scoped>
.lessons {
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
  margin: 4px 4px 4px;
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
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-eco {
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 10.5px;
  color: var(--muted);
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
.nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav button {
  width: 44px;
  padding: 7px 0;
  font-size: 13px;
}
.nav .next {
  width: 72px;
  background: color-mix(in srgb, var(--accent) 22%, var(--surface-2));
  border-color: var(--accent);
}
.nav .flip {
  margin-left: auto;
}
.count {
  min-width: 64px;
  text-align: center;
  font-size: 13px;
  color: var(--fg-dim);
  font-variant-numeric: tabular-nums;
}
.line {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 13px;
}
.pair {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.num {
  color: var(--muted);
  font-size: 12px;
  margin-right: 2px;
}
.mv {
  padding: 2px 5px;
  border: 1px solid transparent;
  background: none;
  color: var(--muted);
  font: inherit;
  border-radius: 5px;
}
.mv.past {
  color: var(--fg-dim);
}
.mv.cur {
  color: var(--fg);
  background: var(--accent-dim);
  border-color: var(--accent);
  font-weight: 700;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  padding: 16px;
}
h2 {
  margin: 0 0 6px;
  font-size: 18px;
}
.named {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-bottom: 10px;
  min-width: 0;
}
.eco {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 5px;
  background: var(--surface-2);
  border: 1px solid var(--border-soft);
  color: var(--accent);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 11px;
  font-weight: 700;
}
.table-name {
  font-size: 11.5px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.summary {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--fg-dim);
}
.sub {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin-bottom: 6px;
}
.ideas {
  margin: 0 0 12px;
  padding-inline-start: 18px;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--fg);
}
.plays-as {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--fg-dim);
}
.move-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.move-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.move-san {
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 17px;
  font-weight: 800;
}
.note {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: var(--fg);
}
.note.start {
  color: var(--fg-dim);
}
.delta {
  padding-top: 10px;
  border-top: 1px solid var(--border-soft);
}
.delta-row,
.delta-total {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  padding: 3px 0;
  color: var(--fg-dim);
}
.delta-total {
  margin-top: 4px;
  padding-top: 7px;
  border-top: 1px dashed var(--border-soft);
  color: var(--fg);
  font-variant-numeric: tabular-nums;
}
.dv {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.dv.pos { color: var(--pos-text); }
.dv.neg { color: var(--neg-text); }
.quiet {
  font-size: 12px;
  color: var(--muted);
}
.legend {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--muted);
}
.block {
  width: 100%;
}
</style>
