"""Checks that the engine still does what it is supposed to.

    python python/selftest.py

Covers move generation (perft), evaluation symmetry, the learned opening
book's accept/decline behaviour, and that a finished GUI game reaches the
book exactly once. Exits non-zero if anything fails, so it is usable as a
pre-commit gate.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from selfplay import find_engine  # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if not ok:
        FAILURES.append(label)
    mark = "OK  " if ok else "FAIL"
    print(f"  {mark}  {label}{'   ' + detail if detail else ''}", flush=True)


def talk(commands: list[str], cwd: Path | None = None,
         timeout: int = 300) -> str:
    proc = subprocess.run([find_engine()],
                          input="\n".join(commands) + "\nquit\n",
                          capture_output=True, text=True, timeout=timeout,
                          cwd=str(cwd or ROOT))
    return proc.stdout


# ==========================================================================
# Move generation
# ==========================================================================
def test_perft() -> None:
    print("\nmove generation")
    cases = [
        ("startpos", None, 5, 4865609),
        ("fen", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R "
                "w KQkq - 0 1", 4, 4085603),
        ("fen", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 5, 674624),
        ("fen", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 "
                "w kq - 0 1", 4, 422333),
    ]
    for kind, fen, depth, expected in cases:
        pos = "position startpos" if kind == "startpos" else f"position fen {fen}"
        out = talk([pos, f"go perft {depth}"])
        nodes = None
        for line in out.splitlines():
            if line.startswith("nodes "):
                nodes = int(line.split()[1])
        label = f"perft({depth}) = {expected}"
        check(label, nodes == expected, f"got {nodes}")


# ==========================================================================
# Evaluation
# ==========================================================================
def mirror(fen: str) -> str:
    parts = fen.split()
    rows = parts[0].split("/")
    board = "/".join("".join(c.lower() if c.isupper() else c.upper()
                             for c in row) for row in reversed(rows))
    stm = "b" if parts[1] == "w" else "w"
    castle = parts[2]
    if castle != "-":
        castle = "".join(sorted(c.lower() if c.isupper() else c.upper()
                                for c in castle))
    ep = parts[3]
    if ep != "-":
        ep = ep[0] + str(9 - int(ep[1]))
    return " ".join([board, stm, castle, ep] + parts[4:])


EVAL_FENS = [
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1",
    # Straddles the endgame material threshold: White has only a knight,
    # Black a queen and rook. Evaluating the two kings under different
    # endgame flags used to make these asymmetric.
    "r2qk3/8/8/6N1/8/8/8/6K1 w - - 0 1",
    "8/8/8/4k3/6n1/8/8/R2Q2K1 w - - 0 1",
    "8/8/8/4k3/6n1/8/8/R2Q2K1 b - - 0 1",
]


def evals(fens: list[str]) -> list[int]:
    cmds = []
    for f in fens:
        cmds += [f"position fen {f}", "eval"]
    out = talk(cmds)
    return [int(l.split()[1]) for l in out.splitlines() if l.startswith("eval ")]


def test_eval_symmetry() -> None:
    print("\nevaluation")
    a = evals(EVAL_FENS)
    b = evals([mirror(f) for f in EVAL_FENS])
    if len(a) != len(EVAL_FENS) or len(b) != len(EVAL_FENS):
        check("engine answered every eval", False,
              f"got {len(a)}/{len(b)} of {len(EVAL_FENS)}")
        return
    bad = [f for f, x, y in zip(EVAL_FENS, a, b) if x != y]
    check("mirrored positions evaluate identically", not bad,
          f"{len(bad)} asymmetric" if bad else "")


# ==========================================================================
# Learned book
# ==========================================================================
def test_book() -> None:
    print("\nlearned opening book")
    sandbox = Path(tempfile.mkdtemp(prefix="simorgh-book-"))
    try:
        (sandbox / "data").mkdir()
        game = "position startpos moves e2e4 e7e5"

        # Below the evidence threshold the book must stay quiet.
        out = talk([game, "learn 1-0", game, "learn 1-0",
                    "position startpos", "book"], cwd=sandbox)
        check("two games is below the min-games threshold",
              "book e2e4 games 2" in out, "")

        out = talk(["position startpos", "go depth 4"], cwd=sandbox)
        check("book does not play on thin evidence",
              "book move" not in out)

        # A third game crosses it.
        out = talk([game, "learn 1-0", "position startpos", "go depth 4"],
                   cwd=sandbox)
        check("book plays a move once it has evidence",
              "book move" in out and "bestmove e2e4" in out)

        # Black's only known reply lost every time, so the book must decline.
        out = talk(["position startpos moves e2e4", "go depth 4"], cwd=sandbox)
        check("book declines a line it has learned loses",
              "book move" not in out and "bestmove " in out)

        # Persistence across processes.
        out = talk(["position startpos", "book"], cwd=sandbox)
        check("book survives a restart", "book e2e4 games 3" in out)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


# ==========================================================================
# Weights
# ==========================================================================
def test_weights_roundtrip() -> None:
    print("\nevaluation weights")
    sandbox = Path(tempfile.mkdtemp(prefix="simorgh w spaces-"))
    try:
        target = sandbox / "weights.txt"
        out = talk([f'weights save "{target.as_posix()}"',
                    f'weights load "{target.as_posix()}"'])
        check("save/load round-trips through a path containing spaces",
              "weights saved" in out and "weights loaded" in out)
        check("weights file is written", target.exists())
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


# ==========================================================================
# GUI wiring
# ==========================================================================
def test_gui_learning() -> None:
    print("\nGUI learning hook")
    try:
        import tkinter as tk
    except ImportError:
        check("tkinter available", False, "skipped")
        return

    os.chdir(ROOT)
    import gui as G

    root = tk.Tk()
    root.withdraw()
    app = G.SimorghGUI(root, find_engine())

    import time

    def pump(ms=200):
        end = time.time() + ms / 1000.0
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    pump(1200)

    submitted: list[tuple] = []
    real = app.engine.submit

    def spy(kind, **kw):
        submitted.append((kind, kw))
        if kind != "learn":       # never touch the real book from a test
            real(kind, **kw)

    app.engine.submit = spy

    mate_fen = "R5k1/5ppp/8/8/8/8/8/6K1 b - - 1 1"
    mate_status = {"incheck": "1", "legal": "0", "halfmove": "1", "stm": "b"}

    def feed(fen, status):
        app._on_state({"fen": fen, "legal": set(), "status": status,
                       "moves": []})
        pump(80)

    app.human_color = "b"
    app.thinking = False

    app.moves, app.learned = [], False
    feed(mate_fen, mate_status)
    check("a game with no moves is not learned",
          not any(k == "learn" for k, _ in submitted))

    submitted.clear()
    app.moves = ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]
    app.learned = False
    feed(mate_fen, mate_status)
    learns = [kw for k, kw in submitted if k == "learn"]
    check("checkmate submits exactly one learn", len(learns) == 1,
          f"got {len(learns)}")
    if learns:
        check("mated Black means White won", learns[0]["result"] == "1-0",
              learns[0]["result"])
        check("every ply is sent", len(learns[0]["moves"]) == 7)

    submitted.clear()
    feed(mate_fen, mate_status)
    feed(mate_fen, mate_status)
    check("refreshing does not learn the game twice",
          not any(k == "learn" for k, _ in submitted))

    submitted.clear()
    app.moves, app.learned = ["e2e4", "e7e5"], False
    feed("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
         {"incheck": "0", "legal": "0", "halfmove": "0", "stm": "b"})
    learns = [kw for k, kw in submitted if k == "learn"]
    check("stalemate is learned as a draw",
          len(learns) == 1 and learns[0]["result"] == "1/2-1/2", str(learns))

    app.learned = True
    app.new_game("w")
    pump(200)
    check("a new game re-arms learning", app.learned is False)

    app.on_close()   # this already tears the Tk root down
    pump(300)


# ==========================================================================
# PGN import
# ==========================================================================
SAMPLE_PGN = """[Event "mate"]
[White "A"]
[Black "B"]
[WhiteElo "2500"]
[BlackElo "2450"]
[Result "1-0"]

1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0

[Event "castling both sides"]
[White "C"]
[Black "D"]
[Result "0-1"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5
7. Bb3 d6 8. c3 O-O 0-1

[Event "disambiguation, comments, variations, NAGs"]
[White "E"]
[Black "F"]
[Result "1-0"]

1. d4 d5 2. Nf3 Nf6 3. Nbd2 c5 {a comment} 4. c3 Nc6 (4... e6 5. e3) 5. e3 $1 e6 1-0

[Event "a draw"]
[White "G"]
[Black "H"]
[Result "1/2-1/2"]

1. e4 e5 2. Nf3 Nf6 1/2-1/2
"""


def test_san_parser() -> None:
    """The cases that would silently corrupt a game if they went wrong."""
    print("\nSAN parsing")
    import importpgn as I

    # Promotion picks the right piece, not just the right square.
    board = {"a7": "wP", "e1": "wK", "e8": "bK"}
    legal = ["a7a8q", "a7a8r", "a7a8b", "a7a8n"]
    check("promotion to a queen", I.san_to_uci("a8=Q", board, legal, "w") == "a7a8q")
    check("underpromotion to a knight",
          I.san_to_uci("a8=N", board, legal, "w") == "a7a8n")

    # Castling on both sides and for both colours.
    check("O-O is a king move",
          I.san_to_uci("O-O", {"e1": "wK"}, ["e1g1"], "w") == "e1g1")
    check("O-O-O is a king move",
          I.san_to_uci("O-O-O", {"e1": "wK"}, ["e1c1"], "w") == "e1c1")
    check("black O-O uses rank 8",
          I.san_to_uci("O-O", {"e8": "bK"}, ["e8g8"], "b") == "e8g8")
    check("0-0 is accepted as O-O",
          I.san_to_uci("0-0", {"e1": "wK"}, ["e1g1"], "w") == "e1g1")

    # Two knights can reach d2: an undisambiguated "Nd2" is ambiguous and
    # must be refused rather than guessed at.
    knights = {"b1": "wN", "f3": "wN"}
    both = ["b1d2", "f3d2"]
    check("ambiguous move is refused",
          I.san_to_uci("Nd2", knights, both, "w") is None)
    check("file disambiguation", I.san_to_uci("Nbd2", knights, both, "w") == "b1d2")
    check("the other file", I.san_to_uci("Nfd2", knights, both, "w") == "f3d2")

    rooks = {"a1": "wR", "a5": "wR"}
    check("rank disambiguation",
          I.san_to_uci("R1a3", rooks, ["a1a3", "a5a3"], "w") == "a1a3")

    # A pawn capture names the source file only.
    check("pawn capture",
          I.san_to_uci("exd5", {"e4": "wP"}, ["e4d5"], "w") == "e4d5")
    # Check and mate marks are decoration.
    check("mate mark is ignored",
          I.san_to_uci("Qxf7#", {"h5": "wQ"}, ["h5f7"], "w") == "h5f7")

    # En passant must remove the pawn beside the destination, not on it.
    board = {"e5": "wP", "d5": "bP"}
    I.apply_uci(board, "e5d6")
    check("en passant removes the captured pawn",
          board.get("d5") is None and board.get("d6") == "wP", str(board))

    # Castling moves the rook too.
    board = {"e1": "wK", "h1": "wR"}
    I.apply_uci(board, "e1g1")
    check("castling moves the rook",
          board.get("f1") == "wR" and board.get("g1") == "wK", str(board))


def test_pgn_import() -> None:
    print("\nPGN import")
    sandbox = Path(tempfile.mkdtemp(prefix="simorgh-pgn-"))
    try:
        pgn = sandbox / "games.pgn"
        pgn.write_text(SAMPLE_PGN, encoding="utf-8")
        book = sandbox / "book.txt"

        proc = subprocess.run(
            [sys.executable, "python/importpgn.py", str(pgn),
             "--book", str(book)],
            capture_output=True, text=True, timeout=300, cwd=str(ROOT))
        out = proc.stdout

        check("three decisive games imported", "imported        3" in out,
              out.strip().splitlines()[-1:] and "")
        check("the draw is skipped by default", "skipped draws   1" in out)
        check("nothing failed to parse", "unreadable" not in out)
        check("a separate book file is written", book.exists())

        # Every move was accepted, so the engine agreed each was legal.
        check("no move was rejected as illegal", "cannot read" not in out)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


# ==========================================================================
# Static exchange evaluation
# ==========================================================================
def test_see() -> None:
    """SEE decides which captures quiescence skips, so a wrong answer
    silently throws away good moves. These are all hand-checkable."""
    print("\nstatic exchange evaluation")
    cases = [
        # (fen, move, expected, what it is)
        ("7k/8/8/3p4/8/8/8/3R3K w - - 0 1", "d1d5", 100,
         "rook takes an undefended pawn"),
        ("7k/8/2p5/3p4/8/8/8/3R3K w - - 0 1", "d1d5", -400,
         "rook takes a pawn defended by a pawn"),
        ("3q3k/8/8/3p4/8/8/8/3R3K w - - 0 1", "d1d5", -400,
         "rook takes a pawn defended by a queen"),
        ("6k1/8/8/3q4/4P3/8/8/6K1 w - - 0 1", "e4d5", 900,
         "pawn takes an undefended queen"),
        ("6k1/5b2/8/3q4/4P3/8/8/6K1 w - - 0 1", "e4d5", 800,
         "pawn takes a queen defended by a bishop"),
        ("7k/8/8/8/8/8/6p1/7K w - - 0 1", "h1g2", 100,
         "king takes an undefended pawn"),
    ]
    cmds = []
    for fen, move, _, _ in cases:
        cmds += [f"position fen {fen}", f"see {move}"]
    out = talk(cmds)
    values = [l.split()[2] for l in out.splitlines() if l.startswith("see ")]

    if len(values) != len(cases):
        check("engine answered every see query", False,
              f"got {len(values)} of {len(cases)}")
        return
    for (fen, move, expected, label), got in zip(cases, values):
        ok = got != "illegal" and int(got) == expected
        check(label, ok, f"{move} -> {got}, expected {expected}")


# ==========================================================================
# Pawn structure and game phase
# ==========================================================================
def engine_rook_value() -> int:
    """The rook's material value as the engine currently has it."""
    sandbox = Path(tempfile.mkdtemp(prefix="simorgh-w-"))
    try:
        target = sandbox / "w.txt"
        talk([f'weights save "{target.as_posix()}"'])
        for line in target.read_text(encoding="utf-8").splitlines():
            if line.startswith("material"):
                # pawn, knight, bishop, rook, queen
                return int(line.split()[4])
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    return 500


def test_pawn_structure() -> None:
    """These terms are invisible in normal play until they are wrong, so
    each one is pinned to a pair of positions that isolates it."""
    print("\npawn structure")

    def ev(fen: str) -> int:
        out = talk([f"position fen {fen}", "eval"])
        for line in out.splitlines():
            if line.startswith("eval "):
                return int(line.split()[1])
        return 0

    free = ev("7k/8/8/P7/8/8/8/7K w - - 0 1")
    blocked = ev("7k/8/1p6/P7/8/8/8/7K w - - 0 1")
    check("a free passed pawn beats a blocked one", free > blocked + 100,
          f"{free} vs {blocked}")

    connected = ev("7k/8/8/8/8/8/PP6/7K w - - 0 1")
    doubled = ev("7k/8/8/8/8/P7/P7/7K w - - 0 1")
    check("doubled pawns score worse than connected ones",
          doubled < connected, f"{doubled} vs {connected}")

    isolated = ev("7k/8/8/8/8/8/P1P5/7K w - - 0 1")
    check("isolated pawns are penalised", isolated < connected,
          f"{isolated} vs {connected}")

    # The old evaluation switched king tables at a hard material threshold,
    # so losing a rook could cost far more than a rook. The rook's value is
    # read from the engine rather than hard-coded: tuning changes it, and a
    # test that pins it would fail for the wrong reason.
    rook_value = engine_rook_value()
    with_rook = ev("4k3/8/8/8/8/8/8/3QR1K1 w - - 0 1")
    without = ev("4k3/8/8/8/8/8/8/3Q2K1 w - - 0 1")
    drop = with_rook - without
    slack = 40
    check("losing a rook costs about a rook, not more",
          abs(drop - rook_value) <= slack,
          f"drop {drop}, rook is worth {rook_value}")


# ==========================================================================
# Explainable evaluation
# ==========================================================================
def parse_explain(block: list[str]) -> dict:
    """Turn one `explain` response into {terms, white, score, actual}."""
    out = {"terms": [], "white": None, "score": None, "actual": None,
           "phase": None}
    for line in block:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "explain":
            out["phase"] = parts[2]
        elif parts[0] == "term":
            out["terms"].append((parts[1], int(parts[2])))
        elif parts[0] in ("white", "score", "actual"):
            out[parts[0]] = int(parts[1])
    return out


def test_explain() -> None:
    """The breakdown must reconstruct evaluate() exactly, not approximately.

    A decomposition that is merely close is worse than none: it reads as an
    explanation while quietly disagreeing with the number the engine
    actually searched on. So every position is checked twice -- the terms
    must sum to the reported total, and that total must equal what
    evaluate() returned for the same position.
    """
    from selfplay import Engine, find_engine  # noqa: E402

    eng = Engine(find_engine(), own_book=False)
    fens: list[str] = []
    try:
        import random
        rng = random.Random(20260904)
        for _ in range(40):
            moves: list[str] = []
            for _ply in range(random.Random(rng.random()).randint(4, 60)):
                legal = eng.legal(moves)
                if not legal:
                    break
                moves.append(rng.choice(legal))
                fens.append(eng.fen(moves))
    finally:
        eng.quit()

    # De-duplicate but keep enough breadth to hit every term.
    fens = list(dict.fromkeys(fens))
    cmds = []
    for f in fens:
        cmds += [f"position fen {f}", "explain"]
    lines = talk(cmds).splitlines()

    blocks: list[list[str]] = []
    for line in lines:
        if line.startswith("explain "):
            blocks.append([])
        if blocks:
            blocks[-1].append(line)

    check("explain answers every position",
          len(blocks) == len(fens),
          f"{len(blocks)} answers for {len(fens)} positions")
    if len(blocks) != len(fens):
        return

    sum_bad = total_bad = sign_bad = 0
    seen_terms: set[str] = set()
    for fen, block in zip(fens, blocks):
        b = parse_explain(block)
        seen_terms.update(name for name, _ in b["terms"])
        if sum(v for _, v in b["terms"]) != b["white"]:
            sum_bad += 1
        if b["score"] != b["actual"]:
            total_bad += 1
        # White's point of view, flipped for the side to move.
        stm_black = fen.split()[1] == "b"
        if b["score"] != (-b["white"] if stm_black else b["white"]):
            sign_bad += 1

    check(f"explain terms sum to the total ({len(fens)} positions)",
          sum_bad == 0, f"{sum_bad} positions disagree")
    check("explain total equals evaluate()", total_bad == 0,
          f"{total_bad} positions disagree")
    check("explain flips sign for the side to move", sign_bad == 0,
          f"{sign_bad} positions disagree")

    # A term that never fires is a term nobody has ever tested.
    expected = {"material.pawn", "placement.pawn", "king.placement",
                "pawns.passed", "pawns.isolated", "pawns.doubled",
                "bishop.pair", "rounding"}
    missing = expected - seen_terms
    check("every eval term appears somewhere in the corpus",
          not missing, f"never seen: {sorted(missing)}")


def main() -> int:
    print(f"engine: {find_engine()}")
    test_perft()
    test_eval_symmetry()
    test_see()
    test_pawn_structure()
    test_explain()
    test_book()
    test_weights_roundtrip()
    test_san_parser()
    test_pgn_import()
    test_gui_learning()

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
