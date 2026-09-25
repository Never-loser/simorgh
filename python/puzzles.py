"""Builds data/puzzles.tsv, the puzzles both apps set, from Lichess's
puzzle database (CC0: https://database.lichess.org/#puzzles).

About 5.5 million puzzles go in; about 1,500 come out, spread evenly over
ratings 400 to 2800 so there is always something near the player's level.
Only well-established ones are kept: popular with the people who played
them, played at least a thousand times, with a settled rating. Each is
replayed move by move with python-chess before it is written.

    python python/puzzles.py path/to/lichess_db_puzzle.csv.zst

A puzzle's FEN is the position before the opponent's move that sets it up;
its first move is that move, played automatically, and the player finds
the rest.
"""

import csv
import io
import random
import sys
from pathlib import Path

import chess
import zstandard

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "puzzles.tsv"

LOW, HIGH, BAND = 400, 2800, 100
PER_BAND = 62

# The themes the apps name; others are dropped from the file.
THEMES = {
    "mateIn1", "mateIn2", "mateIn3", "mate", "fork", "pin", "skewer", "hangingPiece",
    "discoveredAttack", "doubleCheck", "sacrifice", "deflection", "attraction",
    "backRankMate", "smotheredMate", "promotion", "trappedPiece", "xRayAttack",
    "zugzwang", "quietMove", "defensiveMove", "kingsideAttack", "interference",
    "clearance", "intermezzo", "capturingDefender", "exposedKing", "advancedPawn",
    "endgame", "middlegame", "opening", "rookEndgame", "pawnEndgame",
}


def valid(fen: str, moves: list[str]) -> bool:
    try:
        b = chess.Board(fen)
        for m in moves:
            move = chess.Move.from_uci(m)
            if move not in b.legal_moves:
                return False
            b.push(move)
        return True
    except ValueError:
        return False


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rng = random.Random(20260925)
    bands: dict[int, list] = {}
    seen = kept = 0
    with open(sys.argv[1], "rb") as raw:
        text = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(raw), encoding="utf-8")
        for row in csv.DictReader(text):
            seen += 1
            rating = int(row["Rating"])
            if not (LOW <= rating < HIGH):
                continue
            if int(row["RatingDeviation"]) > 80 or int(row["Popularity"]) < 90 or int(row["NbPlays"]) < 1000:
                continue
            band = rating // BAND
            # Reservoir sampling per band: an even, reproducible pick from
            # all the qualifying puzzles, not just the first ones in the file.
            bucket = bands.setdefault(band, [])
            n = bands.setdefault(-band - 1, [0])
            n[0] += 1
            if len(bucket) < PER_BAND:
                bucket.append(row)
            else:
                j = rng.randrange(n[0])
                if j < PER_BAND:
                    bucket[j] = row

    out = []
    for band in sorted(b for b in bands if b >= 0):
        for row in bands[band]:
            moves = row["Moves"].split()
            if not valid(row["FEN"], moves):
                continue
            themes = [t for t in row["Themes"].split() if t in THEMES]
            out.append((row["PuzzleId"], row["FEN"], " ".join(moves), row["Rating"], " ".join(themes)))
            kept += 1
    out.sort(key=lambda r: int(r[3]))

    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Puzzles from the Lichess puzzle database (CC0), chosen by python/puzzles.py.\n")
        f.write("# id<TAB>fen<TAB>moves (UCI; the first is the opponent's)<TAB>rating<TAB>themes\n")
        for r in out:
            f.write("\t".join(r) + "\n")
    print(f"read {seen} puzzles, wrote {kept} to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
