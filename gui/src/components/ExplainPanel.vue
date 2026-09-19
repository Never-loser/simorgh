<script setup lang="ts">
import { computed } from "vue";
import type { Explain } from "../engine/types";
import { termLabel, t, type Lang } from "../i18n";

const props = defineProps<{ explain: Explain | null; lang: Lang }>();
const S = computed(() => t(props.lang));

const rows = computed(() => {
  if (!props.explain) return [];
  return props.explain.terms
    .filter((x) => x.name !== "rounding" || x.cp !== 0)
    .slice()
    .sort((a, b) => Math.abs(b.cp) - Math.abs(a.cp));
});

const scale = computed(() => {
  const max = Math.max(20, ...rows.value.map((r) => Math.abs(r.cp)));
  return max;
});

function pawns(cp: number): string {
  const v = cp / 100;
  return (v > 0 ? "+" : v < 0 ? "" : "±") + v.toFixed(2);
}
function barPct(cp: number): number {
  return Math.min(50, (Math.abs(cp) / scale.value) * 50);
}

// White-perspective engine score, in pawns
const whitePawns = computed(() =>
  props.explain ? pawns(props.explain.white) : "±0.00"
);
const consistent = computed(() => {
  if (!props.explain) return true;
  const sum = props.explain.terms.reduce((a, x) => a + x.cp, 0);
  return sum === props.explain.white && Math.abs(props.explain.score) === Math.abs(props.explain.actual);
});
</script>

<template>
  <div class="explain">
    <div class="head">
      <h3>{{ S.evaluation }}</h3>
      <p class="hint">{{ S.evalHint }}</p>
    </div>

    <div v-if="!explain || rows.length === 0" class="empty">—</div>

    <div v-else class="rows">
      <div v-for="row in rows" :key="row.name" class="row">
        <div class="label" :title="row.name">{{ termLabel(row.name, lang) }}</div>
        <div class="bar">
          <div class="axis" />
          <div
            class="fill"
            :class="row.cp >= 0 ? 'white' : 'black'"
            :style="row.cp >= 0
              ? { left: '50%', width: barPct(row.cp) + '%' }
              : { right: '50%', width: barPct(row.cp) + '%' }"
          />
        </div>
        <div class="val" :class="row.cp >= 0 ? 'pos' : 'neg'">{{ pawns(row.cp) }}</div>
      </div>
    </div>

    <div v-if="explain" class="total">
      <div class="total-line">
        <span>{{ S.total }}</span>
        <span class="total-val" :class="explain.white >= 0 ? 'pos' : 'neg'">
          {{ whitePawns }}
        </span>
      </div>
      <div class="reconcile" :class="{ ok: consistent }">
        <svg viewBox="0 0 16 16" width="14" height="14">
          <path d="M2 8.5l3.5 3.5L14 3.5" fill="none" stroke="currentColor"
            stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>{{ S.engineScore }} {{ pawns(explain.actual) }} · {{ S.matches }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.explain {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.head h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
}
.hint {
  margin: 0 0 12px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--muted);
}
.empty {
  color: var(--muted);
  padding: 20px 0;
  text-align: center;
}
.rows {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding-inline-end: 4px;
}
.row {
  display: grid;
  grid-template-columns: 96px 1fr 52px;
  align-items: center;
  gap: 8px;
}
.label {
  font-size: 12px;
  color: var(--fg-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bar {
  position: relative;
  height: 16px;
  background: var(--surface-2);
  border-radius: 5px;
  direction: ltr;
  overflow: hidden;
}
.axis {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--border);
}
.fill {
  position: absolute;
  top: 3px;
  bottom: 3px;
  border-radius: 3px;
}
.fill.white {
  background: linear-gradient(90deg, #cdd6e0, #f1f4f8);
}
.fill.black {
  background: linear-gradient(90deg, #4aa877, #63c187);
}
.val {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  text-align: end;
  font-weight: 600;
}
.val.pos {
  color: #dfe6ee;
}
.val.neg {
  color: #63c187;
}
.total {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.total-line {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 13px;
  color: var(--fg-dim);
}
.total-val {
  font-size: 20px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.total-val.pos {
  color: #f1f4f8;
}
.total-val.neg {
  color: #63c187;
}
.reconcile {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 11.5px;
  color: var(--muted);
}
.reconcile.ok {
  color: var(--ok);
}
.reconcile svg {
  flex-shrink: 0;
}
</style>
