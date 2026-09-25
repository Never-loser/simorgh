<script setup lang="ts">
import { computed, ref } from "vue";
import LessonView from "./LessonView.vue";
import EndgameView from "./EndgameView.vue";
import PuzzleView from "./PuzzleView.vue";
import type { Engine } from "../engine/engine";
import type { Color } from "../engine/types";
import { t, type Lang } from "../i18n";

// The learning side of the app: opening lessons, endgame lessons and
// puzzles, one tab each.
const props = defineProps<{ engine: Engine; lang: Lang }>();
const emit = defineEmits<{
  (e: "continue", game: { moves: string[]; sans: string[]; side: Color }): void;
}>();
const S = computed(() => t(props.lang));

const KEY = "simorgh.learnTab";
type Tab = "openings" | "endgames" | "puzzles";
function saved(): Tab {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "openings" || v === "endgames" || v === "puzzles") return v;
  } catch {
    /* default below */
  }
  return "openings";
}
const tab = ref<Tab>(saved());
function pick(t: Tab) {
  tab.value = t;
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* not remembered */
  }
}
</script>

<template>
  <div class="learn">
    <nav class="tabs">
      <button :class="{ on: tab === 'openings' }" @click="pick('openings')">{{ S.learnOpenings }}</button>
      <button :class="{ on: tab === 'endgames' }" @click="pick('endgames')">{{ S.learnEndgames }}</button>
      <button :class="{ on: tab === 'puzzles' }" @click="pick('puzzles')">{{ S.learnPuzzles }}</button>
    </nav>
    <LessonView v-if="tab === 'openings'" :engine="engine" :lang="lang" @continue="(g) => emit('continue', g)" />
    <EndgameView v-else-if="tab === 'endgames'" :engine="engine" :lang="lang" />
    <PuzzleView v-else :engine="engine" :lang="lang" />
  </div>
</template>

<style scoped>
.learn {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tabs {
  display: flex;
  gap: 4px;
  align-self: flex-start;
  padding: 3px;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.tabs button {
  padding: 5px 16px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: none;
  font-size: 13px;
  color: var(--fg-dim);
}
.tabs button.on {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--on-accent-dim);
  font-weight: 600;
}
</style>
