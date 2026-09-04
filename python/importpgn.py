"""Feed real games (PGN) into the engine's learned book and tuning data.

    python python/importpgn.py games.pgn
    python python/importpgn.py *.pgn --min-elo 2400 --positions

Grandmaster games are far better training material than the engine's own
self-play: the opening lines are genuinely good and the results reflect
strong play, so the book learns openings worth repeating instead of
whatever a mid-strength engine stumbled into.

PGN uses standard algebraic notation ("Nf3"), the engine speaks UCI
("g1f3"). This converts between them using the engine's own legal-move
list, so a move is only accepted if the engine agrees it is legal --
which also makes this a decent PGN validator.

No third-party libraries: the SAN parser and the board updates are here.
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from selfplay import Engine, find_engine  # noqa: E402

FILES = "abcdefgh"

# Castling, or piece/pawn move with optional disambiguation and promotion.
SAN_RE = re.compile(
    r"^(?P<piece>[KQRBN])?"
    r"(?P<fromfile>[a-h])?(?P<fromrank>[1-8])?"
    r"(?P<capture>x)?"
    r"(?P<tofile>[a-h])(?P<torank>[1-8])"
    r"(?:=(?P<promo>[QRBN]))?$"
)

RESULTS = {"1-0", "0-1", "1/2-1/2"}


# ==========================================================================
# Board tracking
# ==========================================================================
def start_board() -> dict[str, str]:
    board: dict[str, str] = {}
    back = "RNBQKBNR"
    for i, f in enumerate(FILES):
        board[f + "1"] = "w" + back[i]
        board[f + "2"] = "wP"
        board[f + "7"] = "bP"
        board[f + "8"] = "b" + back[i]
    return board


def apply_uci(board: dict[str, str], uci: str) -> None:
    """Update the board for a UCI move, including castling and en passant."""
    src, dst = uci[:2], uci[2:4]
    promo = uci[4:5]
    piece = board.pop(src, None)
    if piece is None:
        return

    # En passant: a pawn moving diagonally onto an empty square captures
    # the pawn that sits beside it, not on it.
    if piece[1] == "P" and src[0] != dst[0] and dst not in board:
        board.pop(dst[0] + src[1], None)

    if promo:
        piece = piece[0] + promo.upper()
    board[dst] = piece

    # Castling: the rook moves too.
    if piece[1] == "K" and abs(FILES.index(src[0]) - FILES.index(dst[0])) == 2:
        rank = src[1]
        if dst[0] == "g":
            rook = board.pop("h" + rank, None)
            if rook:
                board["f" + rank] = rook
        elif dst[0] == "c":
            rook = board.pop("a" + rank, None)
            if rook:
                board["d" + rank] = rook


# ==========================================================================
# SAN -> UCI
# ==========================================================================
def san_to_uci(san: str, board: dict[str, str], legal: list[str],
               color: str) -> str | None:
    """Which legal UCI move does this SAN token mean? None if no match."""
    token = san.rstrip("+#!?").replace("0-0-0", "O-O-O").replace("0-0", "O-O")

    if token in ("O-O", "O-O-O"):
        rank = "1" if color == "w" else "8"
        target = ("g" if token == "O-O" else "c") + rank
        king = "e" + rank
        return king + target if king + target in legal else None

    m = SAN_RE.match(token)
    if not m:
        return None

    piece = (m.group("piece") or "P")
    dest = m.group("tofile") + m.group("torank")
    promo = (m.group("promo") or "").lower()

    matches = []
    for uci in legal:
        if uci[2:4] != dest:
            continue
        if (uci[4:5] or "") != promo:
            continue
        moving = board.get(uci[:2])
        if not moving or moving[0] != color or moving[1] != piece:
            continue
        if m.group("fromfile") and uci[0] != m.group("fromfile"):
            continue
        if m.group("fromrank") and uci[1] != m.group("fromrank"):
            continue
        matches.append(uci)

    # Exactly one match is the normal case. More than one means the PGN was
    # under-disambiguated; taking the first would silently corrupt the game,
    # so refuse it instead.
    return matches[0] if len(matches) == 1 else None


# ==========================================================================
# PGN reading
# ==========================================================================
def strip_movetext(text: str) -> str:
    text = re.sub(r"\{[^}]*\}", " ", text)      # comments
    text = re.sub(r";[^\n]*", " ", text)        # rest-of-line comments
    text = re.sub(r"\$\d+", " ", text)          # NAGs
    # Recursive variations.
    while "(" in text:
        new = re.sub(r"\([^()]*\)", " ", text)
        if new == text:
            break
        text = new
    return text


def read_games(path: Path):
    """Yield (headers, [san moves], result) per game."""
    headers: dict[str, str] = {}
    movetext: list[str] = []

    def finish():
        if not movetext:
            return None
        text = strip_movetext(" ".join(movetext))
        tokens = text.split()
        moves, result = [], headers.get("Result", "*")
        for tok in tokens:
            if tok in RESULTS or tok == "*":
                result = tok
                continue
            tok = re.sub(r"^\d+\.+", "", tok)   # "12." or "12..."
            if tok and not tok.isdigit():
                moves.append(tok)
        return dict(headers), moves, result

    with path.open(encoding="utf-8", errors="replace") as fh:
        in_moves = False
        for line in fh:
            line = line.strip()
            if line.startswith("["):
                if in_moves:
                    game = finish()
                    if game:
                        yield game
                    headers, movetext, in_moves = {}, [], False
                m = re.match(r'\[(\w+)\s+"(.*)"\]', line)
                if m:
                    headers[m.group(1)] = m.group(2)
            elif line:
                in_moves = True
                movetext.append(line)

    game = finish()
    if game:
        yield game


# ==========================================================================
# Import
# ==========================================================================
def elo_of(headers: dict[str, str]) -> int:
    values = []
    for key in ("WhiteElo", "BlackElo"):
        try:
            values.append(int(headers.get(key, "")))
        except ValueError:
            pass
    return min(values) if values else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pgn", nargs="+", help="PGN files (globs allowed)")
    ap.add_argument("--min-elo", type=int, default=0,
                    help="skip games where either player is rated below this "
                         "(games with no rating headers are kept)")
    ap.add_argument("--max-games", type=int, default=0, help="0 = no limit")
    ap.add_argument("--book-depth", type=int, default=20,
                    help="plies of each game to store in the book")
    ap.add_argument("--positions", action="store_true",
                    help="also append labelled positions for tuning")
    ap.add_argument("--data", default=str(ROOT / "data" / "positions.txt"))
    ap.add_argument("--skip-plies", type=int, default=8,
                    help="opening plies excluded from the tuning data")
    ap.add_argument("--draws", action="store_true",
                    help="import drawn games too (default: skip them, they "
                         "teach the book little and dominate GM databases)")
    ap.add_argument("--book", default=None,
                    help="book file to write (default: the engine's own "
                         "data/book.txt). Useful for building a separate "
                         "book without touching the live one.")
    ap.add_argument("--engine", default=None)
    args = ap.parse_args()

    paths: list[Path] = []
    for pattern in args.pgn:
        matched = [Path(p) for p in glob.glob(pattern)]
        if not matched and Path(pattern).exists():
            matched = [Path(pattern)]
        paths.extend(matched)
    if not paths:
        sys.exit("no PGN files matched")

    eng = Engine(args.engine or find_engine())
    eng.send(f"setoption name Book Depth value {args.book_depth}")
    # Saving the whole book after every game is quadratic over a large
    # import; write it once at the end instead.
    eng.send("setoption name Book Autosave value false")
    if args.book:
        # Setting Book File also loads it, so an existing book is extended
        # rather than replaced.
        Path(args.book).parent.mkdir(parents=True, exist_ok=True)
        eng.send(f"setoption name Book File value {args.book}")

    data_file = None
    if args.positions:
        data_path = Path(args.data)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_file = data_path.open("a", encoding="utf-8")

    imported = skipped_elo = skipped_draw = rejected = 0
    positions_written = 0

    try:
        for path in paths:
            print(f"\n{path}", flush=True)
            for headers, sans, result in read_games(path):
                if args.max_games and imported >= args.max_games:
                    break
                if result not in RESULTS:
                    rejected += 1
                    continue
                if not args.draws and result == "1/2-1/2":
                    skipped_draw += 1
                    continue
                if args.min_elo and 0 < elo_of(headers) < args.min_elo:
                    skipped_elo += 1
                    continue

                board = start_board()
                moves: list[str] = []
                ok = True
                for ply, san in enumerate(sans):
                    color = "w" if ply % 2 == 0 else "b"
                    legal = eng.legal(moves)
                    uci = san_to_uci(san, board, legal, color)
                    if uci is None:
                        white = headers.get("White", "?")
                        black = headers.get("Black", "?")
                        print(f"  skipped {white}-{black}: cannot read "
                              f"'{san}' at ply {ply + 1}", flush=True)
                        ok = False
                        break
                    apply_uci(board, uci)
                    moves.append(uci)

                if not ok or not moves:
                    rejected += 1
                    continue

                eng.learn(moves, result)
                imported += 1

                if data_file:
                    for ply in range(args.skip_plies, len(moves)):
                        prefix = moves[:ply]
                        st = eng.status(prefix)
                        if st["incheck"] == "1":
                            continue
                        data_file.write(f"{eng.fen(prefix)};{result}\n")
                        positions_written += 1

                if imported % 25 == 0:
                    print(f"  {imported} games imported", flush=True)
            if args.max_games and imported >= args.max_games:
                break
    finally:
        if data_file:
            data_file.close()
        if imported:
            eng.send("booksave")
            print(eng.read_until("book s"), flush=True)
        eng.quit()

    print(f"\nimported        {imported}")
    if skipped_draw:
        print(f"skipped draws   {skipped_draw}  (use --draws to keep them)")
    if skipped_elo:
        print(f"below min-elo   {skipped_elo}")
    if rejected:
        print(f"unreadable      {rejected}")
    if args.positions:
        print(f"positions       {positions_written} appended to {args.data}")
    print("\nThe book is updated. Check a line with:")
    print("  python python/bookmatch.py --games 100")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
