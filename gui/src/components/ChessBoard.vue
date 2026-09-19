<script setup lang="ts">
import { computed, ref } from "vue";
import Piece from "./Piece.vue";
import { fenToBoard, FILES } from "../engine/protocol";
import type { Color } from "../engine/types";

const props = defineProps<{
  fen: string;
  legal: Set<string>;
  orientation: Color;
  stm: Color;
  lastMove: string | null;
  interactive: boolean;
  checkSquare: string | null;
}>();

const emit = defineEmits<{ (e: "move", uci: string): void }>();

const board = computed(() => fenToBoard(props.fen));
const selected = ref<string | null>(null);
const dragging = ref<{ from: string; code: string; x: number; y: number } | null>(null);
const hoverSq = ref<string | null>(null);
const promotion = ref<{ from: string; to: string; color: Color } | null>(null);

// display cell (r,c) -> algebraic square, respecting orientation
function cellSquare(r: number, c: number): string {
  if (props.orientation === "w") return FILES[c] + (8 - r);
  return FILES[7 - c] + (r + 1);
}
function cellPiece(r: number, c: number): string | null {
  if (props.orientation === "w") return board.value[r][c];
  return board.value[7 - r][7 - c];
}

const targets = computed<Set<string>>(() => {
  const s = new Set<string>();
  if (!selected.value) return s;
  for (const m of props.legal)
    if (m.slice(0, 2) === selected.value) s.add(m.slice(2, 4));
  return s;
});

function isOwnPiece(code: string | null): boolean {
  if (!code) return false;
  const white = code === code.toUpperCase();
  return (white ? "w" : "b") === props.stm;
}

function movesFor(from: string, to: string): string[] {
  return [...props.legal].filter((m) => m.slice(0, 2) === from && m.slice(2, 4) === to);
}

function tryMove(from: string, to: string) {
  const ms = movesFor(from, to);
  if (ms.length === 0) return;
  if (ms.length === 1 && ms[0].length === 4) {
    emit("move", ms[0]);
    selected.value = null;
    return;
  }
  // promotion: several moves same from/to differing by suffix
  promotion.value = { from, to, color: props.stm };
  selected.value = null;
}

function pickPromotion(piece: string) {
  if (!promotion.value) return;
  emit("move", promotion.value.from + promotion.value.to + piece);
  promotion.value = null;
}

function onSquareClick(sq: string, code: string | null) {
  if (!props.interactive || promotion.value) return;
  if (selected.value && targets.value.has(sq)) {
    tryMove(selected.value, sq);
    return;
  }
  if (isOwnPiece(code)) selected.value = sq === selected.value ? null : sq;
  else selected.value = null;
}

// pointer drag
function onPointerDown(e: PointerEvent, sq: string, code: string | null) {
  if (!props.interactive || promotion.value || !isOwnPiece(code) || !code) return;
  selected.value = sq;
  dragging.value = { from: sq, code, x: e.clientX, y: e.clientY };
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
}
function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return;
  dragging.value.x = e.clientX;
  dragging.value.y = e.clientY;
  const el = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
  hoverSq.value = el?.closest<HTMLElement>("[data-sq]")?.dataset.sq ?? null;
}
function onPointerUp() {
  window.removeEventListener("pointermove", onPointerMove);
  window.removeEventListener("pointerup", onPointerUp);
  const d = dragging.value;
  dragging.value = null;
  if (!d) return;
  if (hoverSq.value && hoverSq.value !== d.from && targets.value.has(hoverSq.value)) {
    tryMove(d.from, hoverSq.value);
  }
  hoverSq.value = null;
}

function squareClasses(sq: string, r: number, c: number) {
  const dark = (r + c) % 2 === 1;
  return {
    dark,
    light: !dark,
    sel: selected.value === sq,
    target: targets.value.has(sq),
    "last-from": props.lastMove?.slice(0, 2) === sq,
    "last-to": props.lastMove?.slice(2, 4) === sq,
    check: props.checkSquare === sq,
    hover: hoverSq.value === sq && dragging.value !== null,
  };
}

const promoPieces = computed(() =>
  (promotion.value?.color === "w" ? ["Q", "R", "B", "N"] : ["q", "r", "b", "n"])
);
</script>

<template>
  <!-- A chessboard is not a text run: a1 stays bottom-left whatever the
       interface language. Without this the grid inherits rtl from the app
       and the whole board mirrors, king and queen swapped. -->
  <div class="board-wrap" dir="ltr">
    <div class="board" :class="{ flip: orientation === 'b' }">
      <template v-for="r in 8" :key="r">
        <div
          v-for="c in 8"
          :key="r + '-' + c"
          class="sq"
          :class="squareClasses(cellSquare(r - 1, c - 1), r - 1, c - 1)"
          :data-sq="cellSquare(r - 1, c - 1)"
          @click="onSquareClick(cellSquare(r - 1, c - 1), cellPiece(r - 1, c - 1))"
          @pointerdown="onPointerDown($event, cellSquare(r - 1, c - 1), cellPiece(r - 1, c - 1))"
        >
          <span v-if="c === 1" class="coord rank">{{ cellSquare(r - 1, 0)[1] }}</span>
          <span v-if="r === 8" class="coord file">{{ cellSquare(7, c - 1)[0] }}</span>

          <span v-if="targets.has(cellSquare(r - 1, c - 1))" class="dot"
            :class="{ capture: !!cellPiece(r - 1, c - 1) }" />

          <div
            v-if="cellPiece(r - 1, c - 1)"
            class="piece-holder"
            :class="{ ghost: dragging && dragging.from === cellSquare(r - 1, c - 1) }"
          >
            <Piece :code="cellPiece(r - 1, c - 1)!" />
          </div>
        </div>
      </template>
    </div>

    <!-- dragged piece follows the cursor -->
    <div
      v-if="dragging"
      class="drag-layer"
      :style="{ left: dragging.x + 'px', top: dragging.y + 'px' }"
    >
      <Piece :code="dragging.code" />
    </div>

    <!-- promotion picker -->
    <div v-if="promotion" class="promo-mask" @click="promotion = null">
      <div class="promo">
        <button
          v-for="p in promoPieces"
          :key="p"
          class="promo-btn"
          @click.stop="pickPromotion(p.toLowerCase())"
        >
          <Piece :code="p" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.board-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
}
.board {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  grid-template-rows: repeat(8, 1fr);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow), 0 0 0 1px rgba(255, 255, 255, 0.04) inset;
}
.sq {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sq.light {
  background: var(--light-sq);
}
.sq.dark {
  background: var(--dark-sq);
}
.sq.last-from,
.sq.last-to {
  box-shadow: inset 0 0 0 100px var(--last);
}
.sq.sel {
  box-shadow: inset 0 0 0 100px var(--sel);
}
.sq.check {
  background: radial-gradient(circle, var(--check) 0%, transparent 72%);
}
.sq.hover {
  box-shadow: inset 0 0 0 3px rgba(255, 255, 255, 0.7);
}
.piece-holder {
  width: 92%;
  height: 92%;
  z-index: 2;
  transition: transform 0.12s ease;
}
.piece-holder.ghost {
  opacity: 0.28;
}
.dot {
  position: absolute;
  width: 30%;
  height: 30%;
  border-radius: 50%;
  background: rgba(20, 30, 20, 0.32);
  z-index: 1;
}
.dot.capture {
  width: 88%;
  height: 88%;
  background: transparent;
  border: 6px solid rgba(20, 30, 20, 0.3);
  box-sizing: border-box;
}
.coord {
  position: absolute;
  font-size: 11px;
  font-weight: 700;
  opacity: 0.65;
  pointer-events: none;
}
.coord.rank {
  top: 3px;
  inset-inline-start: 4px;
}
.coord.file {
  bottom: 2px;
  inset-inline-end: 5px;
}
.sq.light .coord {
  color: #4a5a6b;
}
.sq.dark .coord {
  color: #cdd8e2;
}
.drag-layer {
  position: fixed;
  width: 68px;
  height: 68px;
  transform: translate(-50%, -50%) scale(1.08);
  pointer-events: none;
  z-index: 50;
}
.promo-mask {
  position: absolute;
  inset: 0;
  background: rgba(6, 9, 14, 0.55);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
  border-radius: 12px;
}
.promo {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow);
}
.promo-btn {
  width: 64px;
  height: 64px;
  padding: 6px;
  background: var(--surface-3);
}
.promo-btn:hover {
  background: var(--accent-dim);
}
</style>
