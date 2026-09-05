"""Graphical front end for the Simorgh engine.

    python python/gui.py

The GUI never implements chess rules. It asks the engine for the board
(`d`), the legal moves (`legal`) and the game state (`status`), so there is
exactly one source of truth and the two can never disagree.

All engine traffic happens on a worker thread; the Tk main loop only ever
drains a queue. That is why the window stays responsive while the engine
thinks - the old terminal script blocked on a pipe read that, thanks to the
bare-`go` bug, never returned.
"""
from __future__ import annotations

import argparse
import queue
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

# The term names and their translations live in explain.py, so adding an
# evaluation term means editing one dictionary rather than two front ends.
from explain import EN as TERMS_EN, FA as TERMS_FA, squares  # noqa: E402

# --------------------------------------------------------------------- theme
BG = "#0e1116"
SURFACE = "#161b22"
SURFACE_2 = "#1c232c"
BORDER = "#2b3440"
ACCENT = "#4c9aff"
ACCENT_DIM = "#1f4f8f"
FG = "#e6edf3"
FG_DIM = "#a9b6c3"
MUTED = "#6e7d8d"
OK = "#3fb950"
WARN = "#d29922"
DANGER = "#f85149"

LIGHT_SQ = "#c8cfd6"
DARK_SQ = "#41586e"
SEL_SQ = "#6f9fd8"
LAST_SQ = "#7f8f4e"

CELL = 68
MARGIN = 24
BOARD_PX = CELL * 8

GLYPHS = {"k": "♚", "q": "♛", "r": "♜",
          "b": "♝", "n": "♞", "p": "♟"}
GLYPH_FONTS = ("Segoe UI Symbol", "Arial Unicode MS", "DejaVu Sans")

# Ratings are nominal - see the README on how they were calibrated.
STRENGTHS = [("Beginner (~800)", 800), ("Casual (~1000)", 1000),
             ("Club (~1200)", 1200), ("Strong club (~1400)", 1400),
             ("Advanced (~1600)", 1600), ("Expert (~1900)", 1900),
             ("Full strength", None)]

FILES = "abcdefgh"


ZWNJ = chr(0x200C)


def tk_rtl(text: str) -> str:
    """Make a Persian string safe for Tk's bidi.

    Tk shapes Arabic script correctly, but it treats a zero-width
    non-joiner as a segment break and then reverses the pieces around it,
    so a word spelled with one comes out inside out. The Unicode isolate
    characters that would normally pin a run in place are not an option
    either -- Tk draws them as empty boxes. Turning the joiner into an
    ordinary space costs a little typographic polish and gets the reading
    order right, which matters more. explain.py keeps the proper spelling
    for the terminal, which handles it correctly.
    """
    return text.replace(ZWNJ, " ")


def find_engine() -> str:
    for cand in [ROOT / "cpp" / "build" / "simorgh.exe",
                 ROOT / "cpp" / "build" / "simorgh"]:
        if cand.exists():
            return str(cand)
    sys.exit("engine binary not found; build the cpp project first")


def pick_font(candidates) -> str:
    try:
        available = {f.lower() for f in tkfont.families()}
    except Exception:
        return candidates[-1]
    for name in candidates:
        if name.lower() in available:
            return name
    return candidates[-1]


# ==========================================================================
# Engine plumbing
# ==========================================================================
class EngineWorker(threading.Thread):
    """Owns the engine process; serialises every request onto one thread."""

    def __init__(self, path: str, out: queue.Queue):
        super().__init__(daemon=True)
        self.out = out
        self.requests: queue.Queue = queue.Queue()
        self.proc = subprocess.Popen(
            [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self._write_lock = threading.Lock()
        self._alive = True

    # ------------------------------------------------------------- plumbing
    def _send(self, cmd: str) -> None:
        with self._write_lock:
            if self.proc.poll() is None:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()

    def _readline(self) -> str:
        line = self.proc.stdout.readline()
        return line.rstrip() if line else ""

    def _read_until(self, prefix: str) -> str:
        while self._alive:
            line = self._readline()
            if not line and self.proc.poll() is not None:
                return ""
            if line.startswith(prefix):
                return line
        return ""

    # -------------------------------------------------------------- public
    def submit(self, kind: str, **kw) -> None:
        self.requests.put((kind, kw))

    def interrupt(self) -> None:
        """Ask a running search to finish now (safe from the GUI thread)."""
        self._send("stop")

    def shutdown(self) -> None:
        self._alive = False
        self.requests.put(("quit", {}))

    # ---------------------------------------------------------------- loop
    def run(self) -> None:
        self._send("uci")
        self._read_until("uciok")

        while self._alive:
            kind, kw = self.requests.get()
            try:
                if kind == "quit":
                    break
                if kind == "newgame":
                    self._send("ucinewgame")
                elif kind == "option":
                    self._send(f"setoption name {kw['name']} value {kw['value']}")
                elif kind == "refresh":
                    self._refresh(kw["moves"])
                elif kind == "go":
                    self._go(kw["moves"], kw["movetime"])
                elif kind == "learn":
                    self._learn(kw["moves"], kw["result"])
            except Exception as exc:  # never let the worker die silently
                self.out.put(("error", str(exc)))

        try:
            self._send("quit")
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()

    def _position(self, moves) -> None:
        cmd = "position startpos"
        if moves:
            cmd += " moves " + " ".join(moves)
        self._send(cmd)

    def _refresh(self, moves) -> None:
        self._position(moves)

        self._send("d")
        fen = ""
        while True:
            line = self._readline()
            if not line and self.proc.poll() is not None:
                break
            if line.startswith("Fen:"):
                fen = line[4:].strip()
            if line.startswith("Key:"):
                break

        self._send("legal")
        legal = set(self._read_until("legal").split()[1:])

        self._send("status")
        parts = self._read_until("status").split()
        status = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}

        # The evaluation breakdown for the position now on the board. It
        # rides along with the rest of the state so the explanation and the
        # board can never be showing different positions, and it costs
        # nothing: explain does no search.
        self._send("explain")
        explain = []
        while True:
            line = self._readline()
            if not line and self.proc.poll() is not None:
                break
            explain.append(line.strip())
            if line.startswith("actual"):
                break

        self.out.put(("state", {"fen": fen, "legal": legal, "status": status,
                                "moves": list(moves), "explain": explain}))

    def _learn(self, moves, result: str) -> None:
        """Fold a finished game into the engine's opening book."""
        self._position(moves)
        self._send(f"learn {result}")
        self.out.put(("learned", self._read_until("info string")))

    def _go(self, moves, movetime: int) -> None:
        self._position(moves)
        self._send(f"go movetime {movetime}")
        while True:
            line = self._readline()
            if not line and self.proc.poll() is not None:
                self.out.put(("bestmove", "0000"))
                return
            if line.startswith("info "):
                self.out.put(("info", line))
            elif line.startswith("bestmove"):
                parts = line.split()
                self.out.put(("bestmove", parts[1] if len(parts) > 1 else "0000"))
                return


# ==========================================================================
# Board rendering + interaction
# ==========================================================================
class SimorghGUI:
    def __init__(self, root: tk.Tk, engine_path: str,
                 persian: bool = False):
        self.persian = persian
        self.terms = TERMS_FA if persian else TERMS_EN
        self.root = root
        self.root.title("Simorgh")
        self.root.configure(bg=BG)

        self.events: queue.Queue = queue.Queue()
        self.engine = EngineWorker(engine_path, self.events)
        self.engine.start()

        self.glyph_font = pick_font(GLYPH_FONTS)
        self.ui_font = pick_font(["Segoe UI Variable Text", "Segoe UI", "Arial"])
        self.mono_font = pick_font(["JetBrains Mono", "Cascadia Mono",
                                    "Consolas", "Courier New"])

        self.moves: list[str] = []
        self.board: list[list[str | None]] = [[None] * 8 for _ in range(8)]
        self.legal: set[str] = set()
        self.status: dict = {}
        self.flipped = False
        self.selected: tuple[int, int] | None = None
        self.last_move: str | None = None
        self.thinking = False
        self.human_color = "w"
        self.pending_promotion: list[str] | None = None
        self.game_over = False
        self.learned = False

        self._pump_job = None
        self._build_ui()
        self._apply_strength()
        self.refresh()
        self._pump_job = self.root.after(30, self._pump)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=BG, padx=16, pady=16)
        outer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(outer, width=BOARD_PX + 2 * MARGIN,
                                height=BOARD_PX + 2 * MARGIN, bg=SURFACE,
                                highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, rowspan=2, sticky="n")
        self.canvas.bind("<Button-1>", self.on_click)

        side = tk.Frame(outer, bg=BG, padx=16)
        side.grid(row=0, column=1, sticky="n")

        tk.Label(side, text="SIMORGH", bg=BG, fg=ACCENT,
                 font=(self.ui_font, 20, "bold")).pack(anchor="w")
        tk.Label(side, text="UCI chess engine", bg=BG, fg=MUTED,
                 font=(self.ui_font, 10)).pack(anchor="w", pady=(0, 14))

        # ---- controls
        controls = tk.Frame(side, bg=SURFACE, padx=12, pady=12,
                            highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill=tk.X)

        tk.Label(controls, text="STRENGTH", bg=SURFACE, fg=MUTED,
                 font=(self.ui_font, 9, "bold")).pack(anchor="w")
        self.strength_var = tk.StringVar(value=STRENGTHS[2][0])
        option = tk.OptionMenu(controls, self.strength_var,
                               *[name for name, _ in STRENGTHS],
                               command=lambda _v: self._apply_strength())
        option.config(bg=SURFACE_2, fg=FG, activebackground=ACCENT_DIM,
                      activeforeground=FG, highlightthickness=0, bd=0,
                      font=(self.ui_font, 10), width=18, anchor="w")
        option["menu"].config(bg=SURFACE_2, fg=FG, activebackground=ACCENT_DIM,
                              font=(self.ui_font, 10))
        option.pack(fill=tk.X, pady=(4, 10))

        tk.Label(controls, text="THINKING TIME", bg=SURFACE, fg=MUTED,
                 font=(self.ui_font, 9, "bold")).pack(anchor="w")
        self.time_var = tk.IntVar(value=1000)
        scale = tk.Scale(controls, from_=100, to=5000, resolution=100,
                         orient=tk.HORIZONTAL, variable=self.time_var,
                         bg=ACCENT, fg=FG, troughcolor=BORDER,
                         highlightthickness=0, bd=0, sliderrelief="flat",
                         showvalue=True, font=(self.ui_font, 8),
                         activebackground=ACCENT)
        scale.pack(fill=tk.X, pady=(2, 8))

        for text, cmd in (("New game (you play White)",
                           lambda: self.new_game("w")),
                          ("New game (you play Black)",
                           lambda: self.new_game("b")),
                          ("Undo", self.undo),
                          ("Flip board", self.flip)):
            self._button(controls, text, cmd).pack(fill=tk.X, pady=2)

        # ---- engine output
        info = tk.Frame(side, bg=SURFACE, padx=12, pady=12,
                        highlightbackground=BORDER, highlightthickness=1)
        info.pack(fill=tk.X, pady=(12, 0))
        tk.Label(info, text="ENGINE", bg=SURFACE, fg=MUTED,
                 font=(self.ui_font, 9, "bold")).pack(anchor="w")
        self.eval_label = tk.Label(info, text="--", bg=SURFACE, fg=FG,
                                   font=(self.mono_font, 22, "bold"))
        self.eval_label.pack(anchor="w")
        self.depth_label = tk.Label(info, text="", bg=SURFACE, fg=FG_DIM,
                                    font=(self.ui_font, 10), justify="left",
                                    anchor="w")
        self.depth_label.pack(anchor="w")
        self.pv_label = tk.Label(info, text="", bg=SURFACE, fg=MUTED,
                                 font=(self.mono_font, 9), wraplength=250,
                                 justify="left", anchor="w")
        self.pv_label.pack(fill=tk.X, pady=(6, 0))

        # ---- why the evaluation says what it says
        why = tk.Frame(side, bg=SURFACE, padx=12, pady=12,
                       highlightbackground=BORDER, highlightthickness=1)
        why.pack(fill=tk.X, pady=(12, 0))
        tk.Label(why, text="چرا" if self.persian else "WHY", bg=SURFACE,
                 fg=MUTED, font=(self.ui_font, 9, "bold")).pack(anchor="w")
        # One row per reason, and the number lives in its own widget. Tk
        # shapes Persian correctly but reorders mixed runs, and it does not
        # honour the Unicode isolate characters that would normally pin a
        # number in place -- it draws them as empty boxes. Keeping each
        # widget's text in a single direction sidesteps that entirely, and
        # aligns the numbers into a column in English too.
        self.why_body = tk.Frame(why, bg=SURFACE)
        self.why_body.pack(fill=tk.X, pady=(4, 0))
        self.why_body.columnconfigure(1, weight=1)
        side_a = "e" if self.persian else "w"
        self.why_rows = []
        for r in range(5):
            value = tk.Label(self.why_body, text="", bg=SURFACE, fg=FG_DIM,
                             font=(self.mono_font, 9), anchor="e", width=6)
            name = tk.Label(self.why_body, text="", bg=SURFACE, fg=FG_DIM,
                            font=(self.ui_font, 9), anchor=side_a,
                            justify="right" if self.persian else "left",
                            wraplength=185)
            value.grid(row=r, column=0, sticky="e", padx=(0, 8))
            name.grid(row=r, column=1, sticky=side_a)
            self.why_rows.append((value, name))
        self.why_note = tk.Label(why, text="", bg=SURFACE, fg=MUTED,
                                 font=(self.ui_font, 9), anchor=side_a)
        self.why_note.pack(fill=tk.X)

        # ---- move list
        movebox = tk.Frame(side, bg=SURFACE, padx=12, pady=12,
                           highlightbackground=BORDER, highlightthickness=1)
        movebox.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        tk.Label(movebox, text="MOVES", bg=SURFACE, fg=MUTED,
                 font=(self.ui_font, 9, "bold")).pack(anchor="w")
        self.move_text = tk.Text(movebox, height=6, width=28, bg=SURFACE_2,
                                 fg=FG_DIM, font=(self.mono_font, 10), bd=0,
                                 highlightthickness=0, state=tk.DISABLED,
                                 wrap="word", padx=8, pady=6)
        self.move_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.book_label = tk.Label(movebox, text="", bg=SURFACE, fg=MUTED,
                                   font=(self.ui_font, 9), wraplength=250,
                                   justify="left", anchor="w")
        self.book_label.pack(fill=tk.X, pady=(6, 0))

        self.status_label = tk.Label(outer, text="", bg=BG, fg=FG_DIM,
                                     font=(self.ui_font, 11), anchor="w")
        self.status_label.grid(row=1, column=1, sticky="sw", padx=16)

    def _button(self, parent, text, command) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=SURFACE_2,
                         fg=FG_DIM, activebackground=ACCENT_DIM,
                         activeforeground=FG, relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         font=(self.ui_font, 10), cursor="hand2", pady=4)

    # ------------------------------------------------------------- drawing
    def square_to_xy(self, rank: int, file: int) -> tuple[int, int]:
        """rank 0 = rank 8. Returns the top-left pixel of the square."""
        r, f = (7 - rank, 7 - file) if self.flipped else (rank, file)
        return MARGIN + f * CELL, MARGIN + r * CELL

    def xy_to_square(self, x: int, y: int) -> tuple[int, int] | None:
        f = (x - MARGIN) // CELL
        r = (y - MARGIN) // CELL
        if not (0 <= r < 8 and 0 <= f < 8):
            return None
        r, f = int(r), int(f)
        return (7 - r, 7 - f) if self.flipped else (r, f)

    def name_of(self, rank: int, file: int) -> str:
        return FILES[file] + str(8 - rank)

    def draw(self) -> None:
        self.canvas.delete("all")
        targets = self._selected_targets()

        for rank in range(8):
            for file in range(8):
                x, y = self.square_to_xy(rank, file)
                fill = LIGHT_SQ if (rank + file) % 2 == 0 else DARK_SQ
                name = self.name_of(rank, file)

                if self.last_move and name in (self.last_move[:2],
                                               self.last_move[2:4]):
                    fill = LAST_SQ
                if self.selected == (rank, file):
                    fill = SEL_SQ

                self.canvas.create_rectangle(x, y, x + CELL, y + CELL,
                                             fill=fill, outline="")

                if name in targets:
                    cx, cy = x + CELL / 2, y + CELL / 2
                    if self.board[rank][file]:
                        self.canvas.create_oval(x + 3, y + 3, x + CELL - 3,
                                                y + CELL - 3, outline=ACCENT,
                                                width=4)
                    else:
                        self.canvas.create_oval(cx - 9, cy - 9, cx + 9, cy + 9,
                                                fill=ACCENT, outline="")

        self._draw_check()
        self._draw_pieces()
        self._draw_coords()
        if self.pending_promotion:
            self._draw_promotion()

    def _draw_pieces(self) -> None:
        for rank in range(8):
            for file in range(8):
                piece = self.board[rank][file]
                if not piece:
                    continue
                x, y = self.square_to_xy(rank, file)
                cx, cy = x + CELL / 2, y + CELL / 2
                glyph = GLYPHS[piece.lower()]
                white = piece.isupper()
                fill = "#f7fafc" if white else "#10161d"
                edge = "#10161d" if white else "#cbd5e0"
                self.canvas.create_text(cx, cy, text=glyph, fill=edge,
                                        font=(self.glyph_font,
                                              int(CELL * 0.80)))
                self.canvas.create_text(cx, cy, text=glyph, fill=fill,
                                        font=(self.glyph_font,
                                              int(CELL * 0.72)))

    def _draw_check(self) -> None:
        if self.status.get("incheck") != "1":
            return
        stm = self.status.get("stm", "w")
        king = "K" if stm == "w" else "k"
        for rank in range(8):
            for file in range(8):
                if self.board[rank][file] == king:
                    x, y = self.square_to_xy(rank, file)
                    self.canvas.create_rectangle(x, y, x + CELL, y + CELL,
                                                 outline=DANGER, width=4)

    def _draw_coords(self) -> None:
        font = (self.ui_font, 9, "bold")
        for file in range(8):
            x, _ = self.square_to_xy(0, file)
            self.canvas.create_text(x + CELL / 2, MARGIN + BOARD_PX + 11,
                                    text=FILES[file], fill=MUTED, font=font)
        for rank in range(8):
            _, y = self.square_to_xy(rank, 0)
            self.canvas.create_text(MARGIN - 12, y + CELL / 2,
                                    text=str(8 - rank), fill=MUTED, font=font)

    def _draw_promotion(self) -> None:
        moves = self.pending_promotion
        target = moves[0][2:4]
        rank, file = 8 - int(target[1]), FILES.index(target[0])
        x, y = self.square_to_xy(rank, file)
        x = min(max(MARGIN, x - CELL * 1.5), MARGIN + BOARD_PX - 4 * CELL)
        self.canvas.create_rectangle(x - 3, y - 3, x + 4 * CELL + 3,
                                     y + CELL + 3, fill=SURFACE,
                                     outline=ACCENT, width=2)
        white = self.status.get("stm") == "w"
        for i, mv in enumerate(moves):
            cx = x + i * CELL + CELL / 2
            self.canvas.create_text(cx, y + CELL / 2, text=GLYPHS[mv[4]],
                                    fill="#f7fafc" if white else "#10161d",
                                    font=(self.glyph_font, int(CELL * 0.66)))

    def _selected_targets(self) -> set[str]:
        if not self.selected:
            return set()
        origin = self.name_of(*self.selected)
        return {mv[2:4] for mv in self.legal if mv.startswith(origin)}

    # --------------------------------------------------------------- input
    def on_click(self, event: tk.Event) -> None:
        if self.pending_promotion:
            self._promotion_click(event.x, event.y)
            return
        if self.thinking or self.game_over:
            return
        if self.status.get("stm") != self.human_color:
            return

        square = self.xy_to_square(event.x, event.y)
        if square is None:
            return
        name = self.name_of(*square)

        if self.selected:
            origin = self.name_of(*self.selected)
            candidates = sorted(mv for mv in self.legal
                                if mv.startswith(origin) and mv[2:4] == name)
            if len(candidates) > 1:          # promotion
                self.pending_promotion = candidates
                self.selected = None
                self.draw()
                return
            if candidates:
                self.selected = None
                self.play(candidates[0])
                return

        piece = self.board[square[0]][square[1]]
        if piece and (piece.isupper() == (self.human_color == "w")):
            self.selected = square
        else:
            self.selected = None
        self.draw()

    def _promotion_click(self, x: int, y: int) -> None:
        moves = self.pending_promotion
        target = moves[0][2:4]
        rank, file = 8 - int(target[1]), FILES.index(target[0])
        px, py = self.square_to_xy(rank, file)
        px = min(max(MARGIN, px - CELL * 1.5), MARGIN + BOARD_PX - 4 * CELL)
        if not (px <= x <= px + 4 * CELL and py <= y <= py + CELL):
            self.pending_promotion = None
            self.draw()
            return
        index = int((x - px) // CELL)
        chosen = moves[index] if 0 <= index < len(moves) else None
        self.pending_promotion = None
        if chosen:
            self.play(chosen)
        else:
            self.draw()

    # ---------------------------------------------------------------- game
    def play(self, move: str) -> None:
        self.moves.append(move)
        self.last_move = move
        self.refresh()

    def refresh(self) -> None:
        self.engine.submit("refresh", moves=list(self.moves))

    def new_game(self, human_color: str) -> None:
        self.engine.interrupt()
        self.moves.clear()
        self.selected = None
        self.last_move = None
        self.game_over = False
        self.learned = False
        self.thinking = False
        self.human_color = human_color
        self.flipped = human_color == "b"
        self.engine.submit("newgame")
        self._set_eval("--", "", "")
        self.refresh()

    def undo(self) -> None:
        if self.thinking or not self.moves:
            return
        # Take back a full move so it is the human's turn again.
        del self.moves[-(2 if len(self.moves) >= 2 else 1):]
        self.selected = None
        self.last_move = self.moves[-1] if self.moves else None
        self.game_over = False
        self.learned = False
        self.refresh()

    def flip(self) -> None:
        self.flipped = not self.flipped
        self.draw()

    def _apply_strength(self) -> None:
        label = self.strength_var.get()
        elo = dict(STRENGTHS)[label]
        if elo is None:
            self.engine.submit("option", name="UCI_LimitStrength", value="false")
        else:
            self.engine.submit("option", name="UCI_LimitStrength", value="true")
            self.engine.submit("option", name="UCI_Elo", value=str(elo))

    def _maybe_engine_move(self) -> None:
        if self.game_over or self.thinking:
            return
        if self.status.get("stm") == self.human_color:
            return
        self.thinking = True
        self._set_status("Simorgh is thinking...", WARN)
        self.engine.submit("go", moves=list(self.moves),
                           movetime=int(self.time_var.get()))

    # -------------------------------------------------------------- events
    def _pump(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "state":
                    self._on_state(payload)
                elif kind == "info":
                    self._on_info(payload)
                elif kind == "learned":
                    self._on_learned(payload)
                elif kind == "bestmove":
                    self._on_bestmove(payload)
                elif kind == "error":
                    self._set_status(f"engine error: {payload}", DANGER)
        except queue.Empty:
            pass
        self._pump_job = self.root.after(30, self._pump)

    def _on_state(self, payload: dict) -> None:
        self.legal = payload["legal"]
        self.status = payload["status"]
        self._parse_fen(payload["fen"])
        self._render_explain(payload.get("explain", []))
        self._render_moves()
        self.draw()

        legal_count = int(self.status.get("legal", "0"))
        in_check = self.status.get("incheck") == "1"
        stm = self.status.get("stm", "w")

        if legal_count == 0:
            self.game_over = True
            if in_check:
                winner = "Black" if stm == "w" else "White"
                self._set_status(f"Checkmate - {winner} wins", OK)
                self._learn_game("0-1" if stm == "w" else "1-0")
            else:
                self._set_status("Stalemate - draw", FG_DIM)
                self._learn_game("1/2-1/2")
            return
        if int(self.status.get("halfmove", "0")) >= 100:
            self.game_over = True
            self._set_status("Draw by the fifty-move rule", FG_DIM)
            self._learn_game("1/2-1/2")
            return

        self.game_over = False
        self.learned = False
        if in_check:
            self._set_status("Check", DANGER)
        elif stm == self.human_color:
            self._set_status("Your move", FG_DIM)

        self._maybe_engine_move()

    def _render_explain(self, lines: list[str]) -> None:
        """Show the largest few reasons the evaluation reads as it does.

        The engine hands back every term; the panel is small, so only the
        ones big enough to matter are shown. Terms are from White's point
        of view, which is also how the score above them is displayed, so
        the signs agree.
        """
        terms, white = [], None
        for line in lines:
            p = line.split()
            if not p:
                continue
            if p[0] == "term":
                where = " ".join(p[p.index("on") + 1:]) if "on" in p else ""
                terms.append((p[1], int(p[2]), where))
            elif p[0] == "white":
                white = int(p[1])

        big = [] if white is None else sorted(
            (t for t in terms if abs(t[1]) >= 5), key=lambda t: -abs(t[1]))[:5]

        for i, (value_w, name_w) in enumerate(self.why_rows):
            if i >= len(big):
                value_w.config(text="")
                name_w.config(text="")
                continue
            name, value, where = big[i]
            value_w.config(text=f"{value / 100:+.2f}",
                           fg=OK if value > 0 else DANGER)
            label = self.terms.get(name, name)
            if self.persian:
                label = tk_rtl(label)
            place = squares(where, self.persian)
            name_w.config(text=f"{label} ({place})" if place else label)

        if white is not None and not big:
            self.why_note.config(
                text="ÙÙØ§Ø²ÙÙ Ø¨Ø±ÙØ±Ø§Ø± Ø§Ø³Øª"
                     if self.persian else "nothing decisive yet")
        else:
            self.why_note.config(text="")

    def _learn_game(self, result: str) -> None:
        """Send the finished game to the book, once per game."""
        if self.learned or not self.moves:
            return
        self.learned = True
        self.engine.submit("learn", moves=list(self.moves), result=result)

    def _on_learned(self, message: str) -> None:
        # "info string learned 24 plies, book now 312 positions from 18 games"
        text = message.replace("info string ", "").strip()
        if text:
            self._set_book(text)

    def _on_info(self, line: str) -> None:
        parts = line.split()

        def after(key, cast=str):
            return cast(parts[parts.index(key) + 1]) if key in parts else None

        depth = after("depth", int)
        nps = after("nps", int)

        score = ""
        if "score" in parts:
            i = parts.index("score")
            kind, value = parts[i + 1], int(parts[i + 2])
            if kind == "cp":
                # Always shown from White's point of view, like a GUI would.
                cp = value if self.status.get("stm") == "w" else -value
                score = f"{cp / 100:+.2f}"
            else:
                mate = value if self.status.get("stm") == "w" else -value
                score = f"M{mate}"

        pv = " ".join(parts[parts.index("pv") + 1:]) if "pv" in parts else ""
        # "depth 13" means nothing to a player who has not written an
        # engine. Say what it buys: how far ahead the engine is looking.
        detail = ""
        if depth:
            full, half = divmod(depth, 2)
            if half:
                ahead = f"{full}.5" if self.persian else f"{full}½"
            else:
                ahead = str(full)
            detail = (tk_rtl(f"عمق {depth} - {ahead} حرکت جلوتر را می‌بیند")
                      if self.persian
                      else f"depth {depth} - sees {ahead} moves ahead")
        if nps:
            detail += ("\n" if detail else "")
            detail += (f"{nps / 1e6:.1f}M پوزیشن در ثانیه" if self.persian
                       else f"{nps / 1e6:.1f}M positions/second")
        self._set_eval(score or "--", detail, pv)

    def _on_bestmove(self, move: str) -> None:
        self.thinking = False
        if move == "0000" or self.game_over:
            self.refresh()
            return
        self.moves.append(move)
        self.last_move = move
        self.refresh()

    # ------------------------------------------------------------- helpers
    def _parse_fen(self, fen: str) -> None:
        self.board = [[None] * 8 for _ in range(8)]
        if not fen:
            return
        placement = fen.split()[0]
        for rank, row in enumerate(placement.split("/")[:8]):
            file = 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                elif file < 8:
                    self.board[rank][file] = ch
                    file += 1

    def _render_moves(self) -> None:
        pairs = []
        for i in range(0, len(self.moves), 2):
            number = i // 2 + 1
            white = self.moves[i]
            black = self.moves[i + 1] if i + 1 < len(self.moves) else ""
            pairs.append(f"{number:2d}. {white:<6}{black}")
        self.move_text.config(state=tk.NORMAL)
        self.move_text.delete("1.0", tk.END)
        self.move_text.insert("1.0", "\n".join(pairs))
        self.move_text.see(tk.END)
        self.move_text.config(state=tk.DISABLED)

    def _set_eval(self, score: str, detail: str, pv: str) -> None:
        color = FG
        if score.startswith("+"):
            color = OK
        elif score.startswith("-"):
            color = DANGER
        elif score.startswith("M"):
            color = ACCENT
        self.eval_label.config(text=score, fg=color)
        self.depth_label.config(text=detail)
        self.pv_label.config(text=pv)

    def _set_book(self, text: str) -> None:
        self.book_label.config(text=text)

    def _set_status(self, text: str, color: str = FG_DIM) -> None:
        self.status_label.config(text=text, fg=color)

    def on_close(self) -> None:
        if self._pump_job is not None:
            try:
                self.root.after_cancel(self._pump_job)
            except Exception:
                pass
            self._pump_job = None
        self.engine.interrupt()
        self.engine.shutdown()
        self.root.after(120, self.root.destroy)


def main() -> None:
    ap = argparse.ArgumentParser(description="graphical front end for Simorgh")
    ap.add_argument("--engine", default=None, help="path to the binary")
    ap.add_argument("--persian", action="store_true",
                    help="label the explanation panel in Persian")
    args = ap.parse_args()

    root = tk.Tk()
    SimorghGUI(root, args.engine or find_engine(), args.persian)
    root.mainloop()


if __name__ == "__main__":
    main()
