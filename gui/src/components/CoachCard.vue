<script setup lang="ts">
import { computed } from "vue";
import type { MoveReview } from "../coach";
import { t, termLabel, type Lang } from "../i18n";

const props = defineProps<{ review: MoveReview | null; lang: Lang; pending?: boolean }>();
const S = computed(() => t(props.lang));

function pawns(cp: number): string {
  if (cp >= 9000) return "#";
  if (cp <= -9000) return "-#";
  const v = cp / 100;
  return (v > 0 ? "+" : v < 0 ? "−" : "±") + Math.abs(v).toFixed(2);
}

const label = computed(() => (props.review ? S.value[`verdict_${props.review.verdict}`] : ""));
const moveNo = computed(() => {
  const r = props.review;
  return r ? `${Math.floor(r.ply / 2) + 1}${r.mover === "w" ? "." : "..."}` : "";
});
</script>

<template>
  <div class="coach">
    <div v-if="pending" class="pending">{{ S.coachThinking }}</div>
    <div v-else-if="!review" class="empty">{{ S.coachEmpty }}</div>
    <template v-else>
      <div class="head" :class="review.verdict">
        <span class="move" dir="ltr">{{ moveNo }} {{ review.san }}</span>
        <span class="verdict">{{ label }}</span>
      </div>

      <div class="line">
        <span>{{ S.evaluation2 }}</span>
        <span dir="ltr">{{ pawns(review.before) }} → <b>{{ pawns(review.after) }}</b></span>
      </div>
      <div v-if="review.verdict !== 'best'" class="line">
        <span>{{ S.coachLoss }}</span>
        <span dir="ltr">{{ Math.round(review.loss) }}%</span>
      </div>

      <p v-if="review.verdict === 'best'" class="note">{{ S.coachBestNote }}</p>
      <template v-else>
        <div class="line">
          <span>{{ S.coachBetter }}</span>
          <b class="san" dir="ltr">{{ review.bestSan }}</b>
        </div>
        <div v-if="review.replySan" class="line">
          <span>{{ S.coachReply }}</span>
          <b class="san" dir="ltr">{{ review.replySan }}</b>
        </div>
        <div v-if="review.why && review.why.length" class="why">
          <div class="sub">{{ S.coachWhy }}</div>
          <div v-for="w in review.why" :key="w.name" class="line">
            <span>{{ termLabel(w.name, lang) }}</span>
            <span class="neg" dir="ltr">{{ pawns(w.cp) }}</span>
          </div>
        </div>
        <p v-else-if="review.verdict !== 'good'" class="note">{{ S.coachNoReason }}</p>
      </template>
    </template>
  </div>
</template>

<style scoped>
.coach {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pending,
.empty {
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.6;
  padding: 10px 0;
}
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface-2);
}
.move {
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 16px;
  font-weight: 800;
}
.verdict {
  font-weight: 700;
  font-size: 14px;
}
/* Verdict colours are the usual ones and stay the same in every theme. */
.head.best { border-color: #3aa76d; }
.head.best .verdict { color: #3aa76d; }
.head.good .verdict { color: var(--fg-dim); }
.head.inaccuracy { border-color: #d6b23a; }
.head.inaccuracy .verdict { color: #d6b23a; }
.head.mistake { border-color: #e08a36; }
.head.mistake .verdict { color: #e08a36; }
.head.blunder { border-color: #e0534a; }
.head.blunder .verdict { color: #e0534a; }
.line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
  color: var(--fg-dim);
  font-variant-numeric: tabular-nums;
}
.line b {
  color: var(--fg);
}
.san {
  font-family: "SF Mono", "Cascadia Code", monospace;
}
.why {
  padding-top: 8px;
  border-top: 1px solid var(--border-soft);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sub {
  font-size: 11px;
  color: var(--muted);
}
.neg {
  color: #e0534a;
  font-weight: 700;
}
.note {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--fg-dim);
}
</style>
