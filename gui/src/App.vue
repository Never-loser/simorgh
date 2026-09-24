<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import ChessBoard from "./components/ChessBoard.vue";
import ExplainPanel from "./components/ExplainPanel.vue";
import OpeningExplorer from "./components/OpeningExplorer.vue";
import LessonView from "./components/LessonView.vue";
import { Engine } from "./engine/engine";
import type { GameState, Color, EngineInfo } from "./engine/types";
import { fenToBoard, FILES } from "./engine/protocol";
import { t, type Lang } from "./i18n";
import { THEMES, applyTheme, savedTheme, type ThemeId } from "./themes";
import { normalizeSan, readPgnMoves, toPgn } from "./pgn";

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
// The same moves in SAN, for the move list. Each is looked up in the
// position it was played from, which is the only place SAN is defined.
const sanMoves = ref<string[]>([]);
const tab = ref<"eval" | "explorer">("eval");
const mode = ref<"play" | "lessons">("play");
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

// ---- clock
// Base time and increment in ms; "none" is an untimed game, as before.
const TIME_CONTROLS = [
  { id: "none", base: 0, inc: 0, label: "∞" },
  { id: "3+2", base: 180_000, inc: 2_000, label: "3+2" },
  { id: "5+0", base: 300_000, inc: 0, label: "5+0" },
  { id: "10+0", base: 600_000, inc: 0, label: "10+0" },
  { id: "15+10", base: 900_000, inc: 10_000, label: "15+10" },
];
const tcId = ref("none");
const tc = computed(() => TIME_CONTROLS.find((x) => x.id === tcId.value) ?? TIME_CONTROLS[0]);
const timed = computed(() => tc.value.base > 0);
const remain = reactive<Record<Color, number>>({ w: 0, b: 0 }); // ms, at the start of the turn
const running = ref<Color | null>(null);
let turnStart = 0;
const now = ref(performance.now());
const flagged = ref<Color | null>(null); // who ran out of time

function timeLeft(c: Color): number {
  return running.value === c ? Math.max(0, remain[c] - (now.value - turnStart)) : remain[c];
}
function clockStart(c: Color) {
  if (!timed.value || flagged.value) return;
  running.value = c;
  turnStart = performance.now();
  now.value = turnStart;
}
function clockStop(c: Color) {
  if (!timed.value || running.value !== c) return;
  remain[c] = Math.max(0, remain[c] - (performance.now() - turnStart)) + tc.value.inc;
  running.value = null;
}
function resetClock() {
  running.value = null;
  flagged.value = null;
  remain.w = remain.b = tc.value.base;
}
const ticker = window.setInterval(() => {
  if (!running.value) return;
  now.value = performance.now();
  const c = running.value;
  if (timeLeft(c) <= 0) {
    remain[c] = 0;
    running.value = null;
    flagged.value = c;
    if (thinking.value) engine.stop();
    saveGame();
  }
}, 100);
onBeforeUnmount(() => clearInterval(ticker));

function clockText(ms: number): string {
  const s = Math.max(0, ms) / 1000;
  if (s < 10) return s.toFixed(1);
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

const stm = computed<Color>(() => state.value?.status.stm ?? "w");
const gameOver = computed(
  () => !!state.value && (state.value.status.legal === 0 || flagged.value !== null)
);
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
  if (flagged.value) {
    return flagged.value === playerColor.value ? S.value.youFlagged : S.value.engineFlagged;
  }
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

function push(uci: string) {
  sanMoves.value.push(state.value?.san.get(uci) ?? uci);
  moves.value.push(uci);
}

const canMove = computed(
  () => !!state.value && !thinking.value && !gameOver.value && stm.value === playerColor.value
);

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
  const side = stm.value;
  clockStart(side);
  try {
    const limits = timed.value
      ? `wtime ${Math.round(timeLeft("w"))} btime ${Math.round(timeLeft("b"))} winc ${tc.value.inc} binc ${tc.value.inc}`
      : strength.value === 0 ? 1000 : 700;
    const best = await engine.go(moves.value, limits, (i) => Object.assign(info, i));
    // Out of time while thinking: the move comes too late to count.
    if (best && best !== "0000" && !flagged.value) {
      clockStop(side);
      push(best);
      await refresh();
      if (!gameOver.value) clockStart(stm.value);
    }
  } finally {
    thinking.value = false;
    saveGame();
  }
}

async function onMove(uci: string) {
  if (thinking.value || gameOver.value) return;
  clockStop(playerColor.value);
  push(uci);
  await refresh();
  saveGame();
  await engineMoveIfNeeded();
}

async function newGame() {
  moves.value = [];
  sanMoves.value = [];
  resetClock();
  await engine.newGame();
  await applyStrength();
  orientation.value = playerColor.value;
  await refresh();
  saveGame();
  if (stm.value === playerColor.value) clockStart(playerColor.value);
  await engineMoveIfNeeded();
}

async function setTimeControl(id: string) {
  if (thinking.value) return;
  tcId.value = id;
  await newGame();
}

async function setPlayer(c: Color) {
  playerColor.value = c;
  await newGame();
}

async function setStrength(elo: number) {
  strength.value = elo;
  saveGame();
  await applyStrength();
}

async function undo() {
  // Taking a move back against the clock is not a timed game any more.
  if (thinking.value || moves.value.length === 0 || timed.value) return;
  // step back to the player's turn
  moves.value.pop();
  sanMoves.value.pop();
  if (moves.value.length > 0 && stmAfter(moves.value) !== playerColor.value) {
    moves.value.pop();
    sanMoves.value.pop();
  }
  await refresh();
  saveGame();
}
function stmAfter(ms: string[]): Color {
  return ms.length % 2 === 0 ? "w" : "b";
}

function flip() {
  orientation.value = orientation.value === "w" ? "b" : "w";
}
// From a lesson: carry on from where the line was left, as a game against
// the engine, playing the side the lesson teaches.
async function continueFrom(g: { moves: string[]; sans: string[]; side: Color }) {
  if (thinking.value) return;
  mode.value = "play";
  playerColor.value = g.side;
  orientation.value = g.side;
  moves.value = [...g.moves];
  sanMoves.value = [...g.sans];
  tcId.value = "none";
  resetClock();
  await engine.newGame();
  await applyStrength();
  await refresh();
  saveGame();
  await engineMoveIfNeeded();
}

// ---- the game survives closing the app
const GAME_KEY = "simorgh.game";
interface SavedGame {
  moves: string[];
  sans: string[];
  player: Color;
  strength: number;
  tc: string;
  remain: Record<Color, number>;
  flagged: Color | null;
}
function saveGame() {
  // A running clock is saved as it stands now; it resumes on load.
  const r = { w: timeLeft("w"), b: timeLeft("b") };
  const g: SavedGame = {
    moves: moves.value, sans: sanMoves.value, player: playerColor.value,
    strength: strength.value, tc: tcId.value, remain: r, flagged: flagged.value,
  };
  try {
    localStorage.setItem(GAME_KEY, JSON.stringify(g));
  } catch {
    /* not saving is survivable: the game just will not be there next time */
  }
}
function loadGame(): SavedGame | null {
  try {
    const g = JSON.parse(localStorage.getItem(GAME_KEY) ?? "null") as SavedGame | null;
    if (g && Array.isArray(g.moves) && Array.isArray(g.sans) && g.moves.length === g.sans.length) return g;
  } catch {
    /* unreadable: start fresh */
  }
  return null;
}
window.addEventListener("beforeunload", saveGame);

// ---- PGN
const pgnNotice = ref("");
const importOpen = ref(false);
const importText = ref("");
const importError = ref("");

function resultTag(): string {
  if (flagged.value) return flagged.value === "w" ? "0-1" : "1-0";
  if (!state.value || state.value.status.legal !== 0) return "*";
  if (!state.value.status.incheck) return "1/2-1/2";
  return stm.value === "w" ? "0-1" : "1-0";
}

async function copyPgn() {
  // Tag values in plain ASCII: not every program reads anything else.
  const you = "Player";
  const text = toPgn({
    sans: sanMoves.value,
    white: playerColor.value === "w" ? you : "Simorgh",
    black: playerColor.value === "b" ? you : "Simorgh",
    result: resultTag(),
    eco: state.value?.opening?.eco,
    opening: state.value?.opening?.name,
    timeControl: timed.value ? `${tc.value.base / 1000}+${tc.value.inc / 1000}` : undefined,
  });
  try {
    await navigator.clipboard.writeText(text);
    pgnNotice.value = S.value.pgnCopied;
  } catch {
    pgnNotice.value = S.value.pgnCopyFailed;
  }
  setTimeout(() => (pgnNotice.value = ""), 2500);
}

async function importPgn() {
  importError.value = "";
  const read = readPgnMoves(importText.value);
  if ("error" in read) {
    importError.value = read.error === "setup" ? S.value.pgnSetup : S.value.pgnEmpty;
    return;
  }
  // Each written move is looked up among the engine's legal moves for the
  // position it is played in.
  const line: string[] = [];
  const sans: string[] = [];
  for (let i = 0; i < read.sans.length; i++) {
    const legal = await engine.sanMap(line);
    const want = normalizeSan(read.sans[i]);
    const hit = [...legal].find(([, san]) => normalizeSan(san) === want);
    if (!hit) {
      importError.value = S.value.pgnBadMove
        .replace("{n}", `${Math.floor(i / 2) + 1}${i % 2 ? "..." : "."}`)
        .replace("{move}", read.sans[i]);
      return;
    }
    line.push(hit[0]);
    sans.push(hit[1]);
  }
  importOpen.value = false;
  importText.value = "";
  // Carry on from the imported position, playing the side to move.
  moves.value = line;
  sanMoves.value = sans;
  tcId.value = "none";
  resetClock();
  playerColor.value = line.length % 2 === 0 ? "w" : "b";
  orientation.value = playerColor.value;
  await engine.newGame();
  await applyStrength();
  await refresh();
  saveGame();
}

function toggleLang() {
  lang.value = lang.value === "fa" ? "en" : "fa";
}

// paired move list
const movePairs = computed(() => {
  const out: { n: number; w: string; b: string }[] = [];
  for (let i = 0; i < moves.value.length; i += 2)
    out.push({ n: i / 2 + 1, w: sanMoves.value[i], b: sanMoves.value[i + 1] ?? "" });
  return out;
});

onMounted(async () => {
  try {
    await engine.start();
    const saved = loadGame();
    if (saved) {
      moves.value = saved.moves;
      sanMoves.value = saved.sans;
      playerColor.value = saved.player;
      orientation.value = saved.player;
      strength.value = saved.strength;
      tcId.value = TIME_CONTROLS.some((x) => x.id === saved.tc) ? saved.tc : "none";
      remain.w = saved.remain?.w ?? tc.value.base;
      remain.b = saved.remain?.b ?? tc.value.base;
      flagged.value = saved.flagged ?? null;
    } else {
      resetClock();
    }
    await applyStrength();
    await refresh();
    booting.value = false;
    if (!gameOver.value) {
      if (stm.value === playerColor.value) clockStart(playerColor.value);
      else await engineMoveIfNeeded();
    }
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
        <img class="logo" src="/simorgh.svg" alt="" />
        <div class="titles">
          <div class="title">{{ S.appTitle }}</div>
          <div class="subtitle">{{ S.subtitle }}</div>
        </div>
      </div>
      <div class="modes">
        <button :class="{ on: mode === 'play' }" @click="mode = 'play'">{{ S.modePlay }}</button>
        <button :class="{ on: mode === 'lessons' }" :disabled="booting || engineError" @click="mode = 'lessons'">
          {{ S.modeLessons }}
        </button>
      </div>
      <button class="lang-btn" @click="toggleLang">{{ S.lang }}</button>
    </header>

    <LessonView v-if="mode === 'lessons'" :engine="engine" :lang="lang" @continue="continueFrom" />

    <main v-else class="layout">
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
          <div class="group-label">{{ S.timeControl }}</div>
          <div class="seg wrap">
            <button
              v-for="x in TIME_CONTROLS"
              :key="x.id"
              :class="{ on: tcId === x.id }"
              :title="x.id === 'none' ? S.noClock : x.label"
              @click="setTimeControl(x.id)"
            >{{ x.label }}</button>
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
          <button class="block" :disabled="timed" @click="undo">{{ S.undo }}</button>
          <button class="block" @click="flip">{{ S.flip }}</button>
        </div>
        <div class="group row-btns">
          <button class="block" :disabled="moves.length === 0" @click="copyPgn">{{ S.pgnCopy }}</button>
          <button class="block" :disabled="thinking" @click="importOpen = true; importError = ''">{{ S.pgnImport }}</button>
        </div>
        <div v-if="pgnNotice" class="notice">{{ pgnNotice }}</div>
      </aside>

      <!-- board + eval bar -->
      <section class="center">
        <div class="eval-bar" :title="(evalWhite / 100).toFixed(2)">
          <div class="eval-white" :style="{ height: evalBarPct + '%' }" />
          <div class="eval-mid" />
        </div>
        <div class="board-col" :class="{ timed }">
          <div v-if="timed" class="clock" :class="{ on: running === (orientation === 'w' ? 'b' : 'w'), low: timeLeft(orientation === 'w' ? 'b' : 'w') < 20000 }">
            <span class="clock-side" :class="orientation === 'w' ? 'b' : 'w'" />
            <span class="clock-time" dir="ltr">{{ clockText(timeLeft(orientation === 'w' ? 'b' : 'w')) }}</span>
          </div>
          <ChessBoard
            v-if="state"
            :fen="state.fen"
            :legal="state.legal"
            :orientation="orientation"
            :stm="stm"
            :last-move="lastMove"
            :check-square="checkSquare"
            :interactive="canMove"
            @move="onMove"
          />
          <div v-if="timed" class="clock" :class="{ on: running === orientation, low: timeLeft(orientation) < 20000 }">
            <span class="clock-side" :class="orientation" />
            <span class="clock-time" dir="ltr">{{ clockText(timeLeft(orientation)) }}</span>
          </div>
          <div class="statusbar" :class="{ warn: engineError }">
            <span class="dot-live" :class="{ think: thinking }" />
            {{ statusText }}
            <span v-if="thinking && info.depth" class="depth">
              · {{ S.depth }} {{ info.depth }}
              <template v-if="info.scoreCp != null">· {{ (info.scoreCp / 100).toFixed(2) }}</template>
            </span>
          </div>
          <div v-if="state" class="opening-strip">
            <template v-if="moves.length === 0">
              <span class="op-main">{{ S.startPos }}</span>
            </template>
            <template v-else-if="state.opening">
              <span class="eco" dir="ltr">{{ state.opening.eco }}</span>
              <span v-if="lang === 'fa'" class="op-main">{{ state.opening.fa }}</span>
              <span class="op-sub" :class="{ 'op-main': lang === 'en' }" dir="ltr">{{ state.opening.name }}</span>
            </template>
            <template v-else>
              <span class="op-none">{{ S.noOpening }}</span>
            </template>
          </div>
        </div>
      </section>

      <!-- right panel -->
      <aside class="panel">
        <div class="explain-box">
          <div class="tabs">
            <button :class="{ on: tab === 'eval' }" @click="tab = 'eval'">{{ S.tabEval }}</button>
            <button :class="{ on: tab === 'explorer' }" @click="tab = 'explorer'">
              {{ S.tabExplorer }}
              <span v-if="state?.book.length" class="badge">{{ state.book.length }}</span>
            </button>
          </div>
          <div class="tab-body">
            <ExplainPanel v-if="tab === 'eval'" :explain="state?.explain ?? null" :lang="lang" />
            <OpeningExplorer
              v-else
              :book="state?.book ?? []"
              :lang="lang"
              :interactive="canMove"
              @play="onMove"
            />
          </div>
        </div>
        <div class="moves-box">
          <div class="moves-head">{{ S.moves }}</div>
          <div class="moves-scroll">
            <table>
              <tbody>
                <tr v-for="p in movePairs" :key="p.n">
                  <td class="mn">{{ p.n }}.</td>
                  <td class="mv" :class="{ cur: p.n * 2 - 1 === moves.length }">{{ p.w }}</td>
                  <td class="mv" :class="{ cur: p.n * 2 === moves.length }">{{ p.b }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </aside>
    </main>

    <div v-if="importOpen" class="modal-back" @click.self="importOpen = false">
      <div class="modal">
        <h3>{{ S.pgnImport }}</h3>
        <p class="modal-hint">{{ S.pgnImportHint }}</p>
        <textarea v-model="importText" dir="ltr" rows="10" placeholder="1. e4 e5 2. Nf3 Nc6 3. Bb5 a6"></textarea>
        <div v-if="importError" class="modal-error">{{ importError }}</div>
        <div class="modal-actions">
          <button class="primary" @click="importPgn">{{ S.pgnLoad }}</button>
          <button @click="importOpen = false">{{ S.cancel }}</button>
        </div>
      </div>
    </div>
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
  display: block;
  border-radius: 10px;
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
.modes {
  display: flex;
  gap: 4px;
  padding: 3px;
  margin-inline-start: auto;
  margin-inline-end: 12px;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.modes button {
  padding: 6px 18px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: none;
  font-size: 13px;
  color: var(--fg-dim);
}
.modes button.on {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--on-accent-dim);
  font-weight: 600;
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
/* Room for a clock above and below the board. */
.board-col.timed {
  max-width: min(62vh, 100%);
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
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  padding: 12px 16px 16px;
}
.tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  margin-bottom: 14px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}
.tabs button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 8px;
  font-size: 12.5px;
  border: 1px solid transparent;
  background: none;
  color: var(--fg-dim);
}
.tabs button.on {
  background: var(--surface);
  border-color: var(--border);
  color: var(--fg);
  font-weight: 600;
}
.badge {
  min-width: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--accent-dim);
  color: var(--on-accent-dim);
  font-size: 10.5px;
  line-height: 17px;
  font-variant-numeric: tabular-nums;
}
.tab-body {
  flex: 1;
  min-height: 0;
}
.opening-strip {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  padding: 0 4px;
  font-size: 13px;
}
.eco {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 5px;
  background: var(--surface-2);
  border: 1px solid var(--border-soft);
  color: var(--accent);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 11.5px;
  font-weight: 700;
}
.op-main {
  flex-shrink: 0;
  font-weight: 700;
  color: var(--fg);
}
.op-sub {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
  font-size: 12px;
}
.op-sub.op-main {
  flex-shrink: 1;
  font-size: 13px;
  color: var(--fg);
}
.op-none {
  color: var(--muted);
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

.clock {
  align-self: flex-end;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 108px;
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  font-variant-numeric: tabular-nums;
}
.clock.on {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-glow);
}
.clock.low .clock-time {
  color: var(--danger);
}
.clock-time {
  flex: 1;
  text-align: end;
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 20px;
  font-weight: 700;
}
.clock-side {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid var(--border);
}
.clock-side.w { background: #eef1f4; }
.clock-side.b { background: #262c34; }
.notice {
  font-size: 12px;
  color: var(--ok);
  text-align: center;
}
.modal-back {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.55);
}
.modal {
  width: min(560px, calc(100vw - 32px));
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
}
.modal h3 {
  margin: 0;
}
.modal-hint {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.6;
}
.modal textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 12.5px;
}
.modal-error {
  font-size: 12.5px;
  color: var(--danger);
}
.modal-actions {
  display: flex;
  gap: 8px;
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
  padding: 6px 0;
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
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 9.5px;
  color: var(--fg-dim);
  white-space: nowrap;
}
.theme-chip.on .theme-name {
  color: var(--fg);
}
</style>
