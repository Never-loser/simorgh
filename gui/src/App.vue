<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import ChessBoard from "./components/ChessBoard.vue";
import ExplainPanel from "./components/ExplainPanel.vue";
import { Engine } from "./engine/engine";
import type { GameState, Color, EngineInfo } from "./engine/types";
import { fenToBoard, FILES } from "./engine/protocol";
import { t, type Lang } from "./i18n";
import { THEMES, applyTheme, savedTheme, type ThemeId } from "./themes";

const lang = ref<Lang>("fa");
const S = computed(() => t(lang.value));
const dir = computed(() => (lang.value === "fa" ? "rtl" : "ltr"));

const theme = ref<ThemeId>(savedTheme());
applyTheme(theme.value);
function setTheme(id: ThemeId) {
  theme.value = id;
  applyTheme(id);
}

const engine = new Engine();
const booting = ref(true);
const engineError = ref(false);

const moves = ref<string[]>([]);
const state = ref<GameState | null>(null);
const thinking = ref(false);
const info = reactive<EngineInfo>({ raw: "" });

const playerColor = ref<Color>("w");
const orientation = ref<Color>("w");
const strength = ref<number>(1600); // elo; 0 = max

const STRENGTHS = [
  { label: "800", elo: 800 },
  { label: "1200", elo: 1200 },
  { label: "1600", elo: 1600 },
  { label: "2000", elo: 2000 },
  { label: "2400", elo: 2400 },
  { label: "MAX", elo: 0 },
];

const stm = computed<Color>(() => state.value?.status.stm ?? "w");
const gameOver = computed(() => !!state.value && state.value.status.legal === 0);
const lastMove = computed(() => moves.value[moves.value.length - 1] ?? null);

const checkSquare = computed<string | null>(() => {
  if (!state.value || !state.value.status.incheck) return null;
  const board = fenToBoard(state.value.fen);
  const king = stm.value === "w" ? "K" : "k";
  for (let r = 0; r < 8; r++)
    for (let c = 0; c < 8; c++)
      if (board[r][c] === king) return FILES[c] + (8 - r);
  return null;
});

const statusText = computed(() => {
  if (booting.value) return S.value.connecting;
  if (engineError.value) return S.value.noEngine;
  if (!state.value) return "";
  if (gameOver.value) {
    if (state.value.status.incheck)
      return stm.value === "w" ? `${S.value.checkmate} — ${S.value.blackWins}` : `${S.value.checkmate} — ${S.value.whiteWins}`;
    return S.value.stalemate;
  }
  if (thinking.value) return S.value.thinking;
  const chk = state.value.status.incheck ? `${S.value.check} · ` : "";
  return chk + (stm.value === playerColor.value ? S.value.yourMove : S.value.engineMove);
});

const evalWhite = computed(() => state.value?.explain?.white ?? 0);
const evalBarPct = computed(() => {
  // logistic-ish clamp of centipawns to 0..100 (white at top)
  const cp = evalWhite.value;
  const p = 50 + 50 * (2 / (1 + Math.exp(-cp / 300)) - 1);
  return Math.max(2, Math.min(98, p));
});

async function refresh() {
  state.value = await engine.snapshot(moves.value);
}

async function applyStrength() {
  if (strength.value === 0) {
    await engine.setOption("UCI_LimitStrength", false);
  } else {
    await engine.setOption("UCI_LimitStrength", true);
    await engine.setOption("UCI_Elo", strength.value);
  }
}

async function engineMoveIfNeeded() {
  if (!state.value || gameOver.value) return;
  if (stm.value === playerColor.value) return;
  thinking.value = true;
  info.raw = "";
  try {
    const movetime = strength.value === 0 ? 1000 : 700;
    const best = await engine.go(moves.value, movetime, (i) => Object.assign(info, i));
    if (best && best !== "0000") {
      moves.value.push(best);
      await refresh();
    }
  } finally {
    thinking.value = false;
  }
}

async function onMove(uci: string) {
  if (thinking.value || gameOver.value) return;
  moves.value.push(uci);
  await refresh();
  await engineMoveIfNeeded();
}

async function newGame() {
  moves.value = [];
  await engine.newGame();
  await applyStrength();
  orientation.value = playerColor.value;
  await refresh();
  await engineMoveIfNeeded();
}

async function setPlayer(c: Color) {
  playerColor.value = c;
  await newGame();
}

async function setStrength(elo: number) {
  strength.value = elo;
  await applyStrength();
}

async function undo() {
  if (thinking.value || moves.value.length === 0) return;
  // step back to the player's turn
  moves.value.pop();
  if (moves.value.length > 0 && stmAfter(moves.value) !== playerColor.value)
    moves.value.pop();
  await refresh();
}
function stmAfter(ms: string[]): Color {
  return ms.length % 2 === 0 ? "w" : "b";
}

function flip() {
  orientation.value = orientation.value === "w" ? "b" : "w";
}
function toggleLang() {
  lang.value = lang.value === "fa" ? "en" : "fa";
}

// paired move list
const movePairs = computed(() => {
  const out: { n: number; w: string; b: string }[] = [];
  for (let i = 0; i < moves.value.length; i += 2)
    out.push({ n: i / 2 + 1, w: moves.value[i], b: moves.value[i + 1] ?? "" });
  return out;
});

onMounted(async () => {
  try {
    await engine.start();
    await applyStrength();
    await refresh();
    booting.value = false;
  } catch {
    booting.value = false;
    engineError.value = true;
  }
});
</script>

<template>
  <div class="app" :dir="dir">
    <header class="topbar">
      <div class="brand">
        <div class="logo">
          <svg viewBox="0 0 45 45" width="26" height="26"><g
            style="fill:var(--accent);stroke:var(--bg);stroke-width:1.3;stroke-linejoin:round">
            <path d="M22.5 4v7M19 7.5h7" style="stroke:var(--accent);stroke-width:2.2"/>
            <path d="M22.5 12c3.6 0 6.3 2.7 6.3 6 0 1.9-.9 3.6-2.3 4.7h-8c-1.4-1.1-2.3-2.8-2.3-4.7 0-3.3 2.7-6 6.3-6z"/>
            <path d="M12 25c3.2-2.3 6.9-2 10.5.4 3.6-2.4 7.3-2.7 10.5-.4 1.7 2.6 2.5 5.4 2.5 8.4-3.9 1.6-8.5 2.4-13 2.4s-9.1-.8-13-2.4c0-3 .8-5.8 2.5-8.4z"/>
          </g></svg>
        </div>
        <div class="titles">
          <div class="title">{{ S.appTitle }}</div>
          <div class="subtitle">{{ S.subtitle }}</div>
        </div>
      </div>
      <button class="lang-btn" @click="toggleLang">{{ S.lang }}</button>
    </header>

    <main class="layout">
      <!-- left rail -->
      <aside class="rail">
        <button class="primary block" @click="newGame">{{ S.newGame }}</button>

        <div class="group">
          <div class="group-label">{{ S.playAs }}</div>
          <div class="seg">
            <button :class="{ on: playerColor === 'w' }" @click="setPlayer('w')">{{ S.white }}</button>
            <button :class="{ on: playerColor === 'b' }" @click="setPlayer('b')">{{ S.black }}</button>
          </div>
        </div>

        <div class="group">
          <div class="group-label">{{ S.strength }}</div>
          <div class="seg wrap">
            <button
              v-for="s in STRENGTHS"
              :key="s.elo"
              :class="{ on: strength === s.elo }"
              @click="setStrength(s.elo)"
            >{{ s.label }}</button>
          </div>
        </div>

        <div class="group">
          <div class="group-label">{{ S.theme }}</div>
          <div class="themes">
            <button
              v-for="th in THEMES"
              :key="th.id"
              class="theme-chip"
              :class="{ on: theme === th.id }"
              :title="th.name[lang]"
              @click="setTheme(th.id)"
            >
              <span class="swatch">
                <i :style="{ background: th.tokens['light-sq'] }" />
                <i :style="{ background: th.tokens['dark-sq'] }" />
                <i :style="{ background: th.tokens['dark-sq'] }" />
                <i :style="{ background: th.tokens['light-sq'] }" />
              </span>
              <span class="theme-name">{{ th.name[lang] }}</span>
            </button>
          </div>
        </div>

        <div class="group row-btns">
          <button class="block" @click="undo">{{ S.undo }}</button>
          <button class="block" @click="flip">{{ S.flip }}</button>
        </div>
      </aside>

      <!-- board + eval bar -->
      <section class="center">
        <div class="eval-bar" :title="(evalWhite / 100).toFixed(2)">
          <div class="eval-white" :style="{ height: evalBarPct + '%' }" />
          <div class="eval-mid" />
        </div>
        <div class="board-col">
          <ChessBoard
            v-if="state"
            :fen="state.fen"
            :legal="state.legal"
            :orientation="orientation"
            :stm="stm"
            :last-move="lastMove"
            :check-square="checkSquare"
            :interactive="!thinking && !gameOver && stm === playerColor"
            @move="onMove"
          />
          <div class="statusbar" :class="{ warn: engineError }">
            <span class="dot-live" :class="{ think: thinking }" />
            {{ statusText }}
            <span v-if="thinking && info.depth" class="depth">
              · {{ S.depth }} {{ info.depth }}
              <template v-if="info.scoreCp != null">· {{ (info.scoreCp / 100).toFixed(2) }}</template>
            </span>
          </div>
        </div>
      </section>

      <!-- right panel -->
      <aside class="panel">
        <div class="explain-box">
          <ExplainPanel :explain="state?.explain ?? null" :lang="lang" />
        </div>
        <div class="moves-box">
          <div class="moves-head">{{ S.moves }}</div>
          <div class="moves-scroll">
            <table>
              <tbody>
                <tr v-for="p in movePairs" :key="p.n">
                  <td class="mn">{{ p.n }}.</td>
                  <td class="mv" :class="{ cur: p.w === lastMove }">{{ p.w }}</td>
                  <td class="mv" :class="{ cur: p.b === lastMove }">{{ p.b }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px 20px 18px;
  gap: 14px;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 0 24px -6px var(--accent-glow);
}
.title {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.2px;
}
.subtitle {
  font-size: 12px;
  color: var(--muted);
}
.lang-btn {
  border-radius: 999px;
  padding: 7px 16px;
}

.layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 210px minmax(320px, 1fr) 320px;
  gap: 18px;
  align-items: stretch;
}

.rail,
.panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}
.block {
  width: 100%;
}
.group {
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  padding: 12px;
}
.group-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 9px;
}
.seg {
  display: flex;
  gap: 6px;
}
.seg.wrap {
  flex-wrap: wrap;
}
.seg button {
  flex: 1;
  min-width: 42px;
  padding: 7px 6px;
  font-size: 12px;
}
.seg button.on {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--on-accent-dim);
}
.row-btns {
  display: flex;
  flex-direction: row;
  gap: 8px;
  background: none;
  border: none;
  padding: 0;
}

.center {
  display: flex;
  gap: 12px;
  align-items: stretch;
  justify-content: center;
  min-width: 0;
}
.board-col {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  flex: 1;
  max-width: min(72vh, 100%);
  margin: 0 auto;
}
.eval-bar {
  position: relative;
  width: 14px;
  align-self: stretch;
  max-height: min(72vh, 100%);
  background: var(--black-side);
  border-radius: 7px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.eval-white {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--white-side);
  transition: height 0.4s ease;
}
.eval-mid {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(0, 0, 0, 0.4);
}
.statusbar {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--fg-dim);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  padding: 10px 14px;
}
.statusbar.warn {
  color: var(--warn);
}
.depth {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.dot-live {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ok);
  flex-shrink: 0;
}
.dot-live.think {
  background: var(--accent);
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.panel {
  min-width: 0;
}
.explain-box {
  flex: 1;
  min-height: 0;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  padding: 16px;
}
.moves-box {
  height: 34%;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  overflow: hidden;
}
.moves-head {
  padding: 10px 14px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  border-bottom: 1px solid var(--border-soft);
}
.moves-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}
.mn {
  width: 36px;
  color: var(--muted);
  font-size: 12px;
  text-align: end;
  padding: 3px 8px;
}
.mv {
  font-size: 13px;
  padding: 3px 10px;
  font-family: "SF Mono", "Cascadia Code", monospace;
}
.mv.cur {
  color: var(--accent);
  font-weight: 700;
}

.themes {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}
.theme-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 6px 2px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface-2);
  cursor: pointer;
}
.theme-chip.on {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-glow);
}
.swatch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 26px;
  height: 26px;
  border-radius: 5px;
  overflow: hidden;
}
.swatch i {
  display: block;
}
.theme-name {
  font-size: 10.5px;
  color: var(--fg-dim);
  white-space: nowrap;
}
.theme-chip.on .theme-name {
  color: var(--fg);
}
</style>
