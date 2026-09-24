<script setup lang="ts">
import { computed } from "vue";
import CoachCard from "./CoachCard.vue";
import { accuracy, glyph, winChance, type GameReview, type Verdict } from "../coach";
import type { Color } from "../engine/types";
import { t, type Lang } from "../i18n";

const props = defineProps<{ review: GameReview; selected: number; lang: Lang }>();
const emit = defineEmits<{ (e: "select", ply: number): void; (e: "close"): void }>();
const S = computed(() => t(props.lang));

const VERDICTS: Verdict[] = ["best", "good", "inaccuracy", "mistake", "blunder"];

const sides = computed(() =>
  (["w", "b"] as Color[]).map((c) => {
    const mine = props.review.plies.filter((p) => p.mover === c);
    const counts = Object.fromEntries(VERDICTS.map((v) => [v, mine.filter((p) => p.verdict === v).length]));
    const acc = accuracy(mine.map((p) => p.loss));
    return { c, counts, acc };
  })
);

// ---- the graph: White's win chance through the game
const W = 300;
const H = 110;
const n = computed(() => Math.max(1, props.review.evals.length - 1));
const x = (i: number) => (i / n.value) * W;
const y = (cp: number) => H - (winChance(cp) / 100) * H;
const area = computed(() => {
  const pts = props.review.evals.map((e, i) => `${x(i).toFixed(1)},${y(e).toFixed(1)}`);
  return `M0,${H} L${pts.join(" L")} L${W},${H} Z`;
});
const marks = computed(() =>
  props.review.plies
    .filter((p) => p.verdict === "mistake" || p.verdict === "blunder" || p.verdict === "inaccuracy")
    .map((p) => ({ ply: p.ply, verdict: p.verdict, cx: x(p.ply + 1), cy: y(props.review.evals[p.ply + 1]) }))
);
function pick(ev: MouseEvent) {
  const box = (ev.currentTarget as SVGElement).getBoundingClientRect();
  const i = Math.round(((ev.clientX - box.left) / box.width) * n.value);
  emit("select", Math.max(0, Math.min(props.review.plies.length - 1, i - 1)));
}

const pairs = computed(() => {
  const out: { n: number; w: number; b: number | null }[] = [];
  for (let i = 0; i < props.review.plies.length; i += 2)
    out.push({ n: i / 2 + 1, w: i, b: i + 1 < props.review.plies.length ? i + 1 : null });
  return out;
});
</script>

<template>
  <div class="review">
    <div class="top">
      <h3>{{ S.reviewTitle }}</h3>
      <button class="close" @click="emit('close')">{{ S.reviewClose }}</button>
    </div>

    <table class="summary">
      <thead>
        <tr>
          <th />
          <th><span class="dot w" />{{ S.white }}</th>
          <th><span class="dot b" />{{ S.black }}</th>
        </tr>
      </thead>
      <tbody>
        <tr class="acc">
          <td>{{ S.accuracy }}</td>
          <td v-for="s in sides" :key="s.c" dir="ltr">{{ s.acc === null ? "—" : `${Math.round(s.acc)}%` }}</td>
        </tr>
        <tr v-for="v in VERDICTS" :key="v" :class="v">
          <td>{{ S[`verdict_${v}`] }}</td>
          <td v-for="s in sides" :key="s.c">{{ s.counts[v] }}</td>
        </tr>
      </tbody>
    </table>

    <svg class="graph" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" dir="ltr" @click="pick">
      <rect :width="W" :height="H" class="bg" />
      <path :d="area" class="white" />
      <line :x1="0" :x2="W" :y1="H / 2" :y2="H / 2" class="mid" />
      <line v-if="selected >= 0" :x1="x(selected + 1)" :x2="x(selected + 1)" y1="0" :y2="H" class="sel" />
      <circle v-for="m in marks" :key="m.ply" :cx="m.cx" :cy="m.cy" r="3.2" :class="m.verdict" />
    </svg>

    <div class="moves" dir="ltr">
      <span v-for="p in pairs" :key="p.n" class="pair">
        <span class="num">{{ p.n }}.</span>
        <button :class="[review.plies[p.w].verdict, { on: selected === p.w }]" @click="emit('select', p.w)">
          {{ review.plies[p.w].san }}{{ glyph(review.plies[p.w].verdict) }}
        </button>
        <button
          v-if="p.b !== null"
          :class="[review.plies[p.b].verdict, { on: selected === p.b }]"
          @click="emit('select', p.b!)"
        >{{ review.plies[p.b].san }}{{ glyph(review.plies[p.b].verdict) }}</button>
      </span>
    </div>

    <CoachCard :review="review.plies[selected] ?? null" :lang="lang" />
  </div>
</template>

<style scoped>
.review {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding-inline-end: 4px;
}
/* The panel scrolls; its parts keep their size rather than being squeezed
   to fit, which would flatten the graph to nothing. */
.review > * {
  flex-shrink: 0;
}
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
h3 {
  margin: 0;
  font-size: 15px;
}
.close {
  padding: 5px 12px;
  font-size: 12px;
}
.summary {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}
.summary th,
.summary td {
  padding: 3px 6px;
  text-align: center;
}
.summary td:first-child {
  text-align: start;
  color: var(--fg-dim);
}
.summary th {
  font-weight: 600;
  color: var(--fg-dim);
}
.summary .acc td {
  font-size: 15px;
  font-weight: 800;
  color: var(--fg);
  padding-bottom: 6px;
}
.summary .acc td:first-child {
  font-size: 12.5px;
  font-weight: 400;
  color: var(--fg-dim);
}
.summary tr.best td:not(:first-child) { color: #3aa76d; }
.summary tr.inaccuracy td:not(:first-child) { color: #d6b23a; }
.summary tr.mistake td:not(:first-child) { color: #e08a36; }
.summary tr.blunder td:not(:first-child) { color: #e0534a; }
.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-inline-end: 5px;
  border: 1px solid var(--border);
}
.dot.w { background: #eef1f4; }
.dot.b { background: #262c34; }
/* The graph keeps fixed colours: White's share is white, like the eval bar. */
.graph {
  width: 100%;
  height: 110px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.graph .bg { fill: #262c34; }
.graph .white { fill: #dfe4ea; }
.graph .mid { stroke: #8a939e; stroke-width: 0.6; stroke-dasharray: 3 3; }
.graph .sel { stroke: var(--accent); stroke-width: 1.6; }
.graph circle { stroke: #10151b; stroke-width: 0.8; }
.graph circle.inaccuracy { fill: #d6b23a; }
.graph circle.mistake { fill: #e08a36; }
.graph circle.blunder { fill: #e0534a; }
.moves {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 8px;
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 12.5px;
}
.pair {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.num {
  color: var(--muted);
  font-size: 11.5px;
}
.moves button {
  padding: 1px 4px;
  border: 1px solid transparent;
  background: none;
  font: inherit;
  color: var(--fg-dim);
  border-radius: 4px;
}
.moves button.inaccuracy { color: #d6b23a; }
.moves button.mistake { color: #e08a36; }
.moves button.blunder { color: #e0534a; font-weight: 700; }
.moves button.on {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--fg);
}
</style>
