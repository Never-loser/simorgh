# Simorgh Desktop — سیمرغ

A high-quality desktop board for the [Simorgh](../README.md) chess engine, built
with **Tauri 2 + Vue 3**. You play; the engine answers — and, unlike every other
engine, it shows you *why* it evaluates the position the way it does. Each
evaluation term is drawn as a bar, and the bars sum to exactly the number the
engine searched on.

The interface is bilingual (Persian / English), right-to-left in Persian, with a
dark theme, drag-and-drop and click-to-move, legal-move dots, last-move and
check highlights, adjustable opponent strength (Elo 800 → max), and a live
evaluation bar.

The app never implements chess rules. It asks the engine for the board (`d`),
the legal moves (`legal`), the state (`status`) and the evaluation (`explain`),
so the two can never disagree — the same principle as the original Tkinter GUI.

## Architecture

```
Vue 3 frontend  ──invoke/events──►  Rust backend  ──stdin/stdout──►  simorgh.exe (UCI)
  board, panels                     owns the child                   the only rules engine
```

The Rust backend (`src-tauri/src/lib.rs`) spawns one engine process, forwards
every line it prints to the webview as an `engine-line` event, and writes
commands back. The engine and its data (opening book, tuned weights) are
bundled as resources and run from their own directory so the engine's relative
`data/…` paths resolve.

## Build the installer

Requires Node, Rust, and a C++ toolchain (the engine builds with CMake).

```bash
npm install
npm run bundle-engine     # builds simorgh.exe and copies it + data into resources
npm run tauri build       # produces the Windows setup .exe (NSIS)
```

The installer lands in `src-tauri/target/release/bundle/nsis/`.

## Develop

The packaged app talks to the engine through Rust. For a fast browser preview
(`vite`), a tiny dev bridge pipes the real engine over a WebSocket instead:

```bash
npm run bridge     # terminal 1: pipes ../build/simorgh.exe over ws://localhost:8137
npm run dev        # terminal 2: vite preview at http://localhost:1420
# or, for the real Tauri window:
npm run app        # bundle-engine + tauri dev
```

## Layout

```
src/
  engine/
    types.ts       shapes mirroring the engine's output
    protocol.ts    parse d / legal / status / explain / info, FEN <-> board
    engine.ts      transport-agnostic UCI layer (Tauri events or dev WebSocket)
  components/
    ChessBoard.vue board, drag/drop, highlights, promotion picker
    Piece.vue      one SVG piece, coloured by side
    ExplainPanel.vue  the evaluation breakdown — the signature feature
  pieces.ts        the flat SVG piece set
  i18n.ts          UI + evaluation-term labels (ported from python/explain.py)
  App.vue          game state, engine turn, controls, eval bar, move list
src-tauri/
  src/lib.rs       spawns and pipes the engine, emits engine-line events
  resources/engine generated: simorgh.exe + data (see scripts/bundle-engine.mjs)
dev/engine-bridge.mjs   dev-only WebSocket bridge for the browser preview
```
