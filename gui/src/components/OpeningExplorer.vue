<script setup lang="ts">
import { computed } from "vue";
import type { BookMove } from "../engine/types";
import { t, type Lang } from "../i18n";

const props = defineProps<{ book: BookMove[]; lang: Lang; interactive: boolean }>();
const emit = defineEmits<{ (e: "play", uci: string): void }>();
const S = computed(() => t(props.lang));

// The book lists everything it has ever seen, down to single games; past the
// first dozen the rows are noise.
const rows = computed(() => props.book.slice(0, 12));
const total = computed(() => props.book.reduce((a, m) => a + m.games, 0));

function pct(n: number, of: number): number {
  return of ? (n / of) * 100 : 0;
}
function label(n: number, of: number): string {
  const p = pct(n, of);
  // Only label a segment wide enough to hold the number.
  return p >= 14 ? Math.round(p) + "%" : "";
}
function count(n: number): string {
  return n.toLocaleString("en-US");
}
</script>

<template>
  <div class="explorer">
    <div class="head">
      <h3>{{ S.explorer }}</h3>
      <p class="hint">{{ S.explorerHint }}</p>
    </div>

    <div v-if="rows.length === 0" class="empty">{{ S.noBook }}</div>

    <div v-else class="rows">
      <button
        v-for="m in rows"
        :key="m.uci"
        class="row"
        :disabled="!interactive"
        :title="m.uci"
        @click="emit('play', m.uci)"
      >
        <span class="san" dir="ltr">{{ m.san }}</span>
        <span class="games" dir="ltr">
          {{ count(m.games) }}
          <span class="share">{{ Math.round(pct(m.games, total)) }}%</span>
        </span>
        <span class="wdl" dir="ltr">
          <i class="w" :style="{ width: pct(m.white, m.games) + '%' }">{{ label(m.white, m.games) }}</i>
          <i class="d" :style="{ width: pct(m.draws, m.games) + '%' }">{{ label(m.draws, m.games) }}</i>
          <i class="b" :style="{ width: pct(m.black, m.games) + '%' }">{{ label(m.black, m.games) }}</i>
        </span>
      </button>
    </div>

    <div v-if="rows.length" class="legend">
      <span><i class="w" />{{ S.whiteShort }}</span>
      <span><i class="d" />{{ S.drawShort }}</span>
      <span><i class="b" />{{ S.blackShort }}</span>
      <span class="sum">{{ count(total) }} {{ S.games }}</span>
    </div>
  </div>
</template>

<style scoped>
.explorer {
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
  font-size: 12.5px;
  line-height: 1.6;
  padding: 16px 0;
  text-align: center;
}
.rows {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-inline-end: 4px;
}
.row {
  display: grid;
  grid-template-columns: 58px 74px 1fr;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: none;
  text-align: start;
  cursor: pointer;
}
.row:hover:not(:disabled) {
  background: var(--surface-2);
  border-color: var(--border-soft);
}
.row:disabled {
  cursor: default;
  opacity: 1;
}
.san {
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--fg);
  text-align: start;
}
.games {
  font-size: 12px;
  color: var(--fg-dim);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.share {
  color: var(--muted);
  font-size: 11px;
  margin-inline-start: 3px;
}
/* Fixed colours, not theme tokens: white, draw and black mean the same on
   every board, like the pieces. */
.wdl {
  display: flex;
  height: 18px;
  border-radius: 4px;
  overflow: hidden;
  font-size: 10.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.wdl i {
  display: grid;
  place-items: center;
  font-style: normal;
  overflow: hidden;
  white-space: nowrap;
}
.w { background: #eef1f4; color: #1d232b; }
.d { background: #8a939e; color: #10151b; }
.b { background: #262c34; color: #e6ebf0; }
.legend {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 10px;
  margin-top: 8px;
  border-top: 1px solid var(--border-soft);
  font-size: 11px;
  color: var(--muted);
}
.legend span {
  display: flex;
  align-items: center;
  gap: 5px;
}
.legend i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  border: 1px solid var(--border);
}
.legend .sum {
  margin-inline-start: auto;
  font-variant-numeric: tabular-nums;
}
</style>
