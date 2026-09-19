<script setup lang="ts">
import { computed } from "vue";
import { PIECES, type PieceType } from "../pieces";

const props = defineProps<{ code: string }>(); // "P".."k"; upper = white

const isWhite = computed(() => props.code === props.code.toUpperCase());
const type = computed(() => props.code.toLowerCase() as PieceType);
const inner = computed(() => PIECES[type.value] ?? "");
</script>

<template>
  <svg
    class="piece"
    :class="isWhite ? 'w' : 'b'"
    viewBox="0 0 45 45"
    v-html="inner"
  />
</template>

<style scoped>
.piece {
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
  pointer-events: none;
}
.piece :deep(*) {
  stroke-linejoin: round;
  stroke-linecap: round;
}
.piece.w {
  color: #f3f5f8;
}
.piece.w :deep(ellipse),
.piece.w :deep(path),
.piece.w :deep(circle),
.piece.w :deep(rect) {
  fill: currentColor;
  stroke: #20262e;
  stroke-width: 1.3;
}
.piece.b {
  color: #2b3138;
}
.piece.b :deep(ellipse),
.piece.b :deep(path),
.piece.b :deep(circle),
.piece.b :deep(rect) {
  fill: currentColor;
  stroke: #0a0d11;
  stroke-width: 1.3;
}
/* base ellipse: softer, reads as a shadow */
.piece :deep(ellipse) {
  fill: rgba(0, 0, 0, 0.28);
  stroke: none;
}
/* the small overrides in the markup (eye, slit) keep their own attrs */
.piece :deep([fill="#000"]) {
  fill: rgba(0, 0, 0, 0.55) !important;
}
.piece :deep([fill="none"]) {
  fill: none !important;
}
.piece.w :deep([fill="none"]) {
  stroke: #20262e;
}
.piece.b :deep([fill="none"]) {
  stroke: #0a0d11;
}
.piece {
  filter: drop-shadow(0 3px 3px rgba(0, 0, 0, 0.35));
}
</style>
