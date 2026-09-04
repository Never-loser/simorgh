"""Measure what the learned opening book is worth, in Elo.

Plays the engine with its book against the same engine with the book
switched off. Both sides are otherwise identical, so the difference is the
book and nothing else.

    python python/bookmatch.py --games 100

Unlike the evaluation weights, the book needs no promotion gate -- it can
only play a move it has enough evidence for, and declines when everything
it knows in a position scores badly. This script is here to quantify the
benefit, not to decide whether to keep it.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate import elo, play_game  # noqa: E402
from selfplay import Engine, find_engine, random_opening  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--movetime", type=int, default=50)
    ap.add_argument("--max-plies", type=int, default=140)
    ap.add_argument("--opening-plies", type=int, default=0,
                    help="random plies before play; 0 lets the book start "
                         "from move one, which is where it knows most")
    ap.add_argument("--engine", default=None)
    args = ap.parse_args()

    path = args.engine or find_engine()
    with_book = Engine(path, own_book=True)
    without = Engine(path, own_book=False)
    ref = Engine(path, own_book=False)

    wins = draws = losses = 0
    outcomes: list[float] = []
    pairs = max(1, args.games // 2)

    try:
        for pair in range(1, pairs + 1):
            opening = (random_opening(ref, args.opening_plies)
                       if args.opening_plies else [])
            for book_is_white in (True, False):
                white, black = ((with_book, without) if book_is_white
                                else (without, with_book))
                result = play_game(white, black, ref, args.movetime,
                                   args.max_plies, opening)
                if result == "1/2-1/2":
                    draws += 1
                    outcomes.append(0.5)
                else:
                    book_won = (result == "1-0") == book_is_white
                    wins += book_won
                    losses += not book_won
                    outcomes.append(1.0 if book_won else 0.0)
            score = sum(outcomes) / len(outcomes)
            print(f"pair {pair:3d}/{pairs}  +{wins} ={draws} -{losses}  "
                  f"score {score:.3f}", flush=True)
    finally:
        for eng in (with_book, without, ref):
            eng.quit()

    played = len(outcomes)
    score = sum(outcomes) / played
    mean = score
    var = (sum((x - mean) ** 2 for x in outcomes) / (played - 1)
           if played > 1 else 0.25)
    se = math.sqrt(var / played)
    lower, upper = score - 1.96 * se, score + 1.96 * se

    print()
    print(f"  games   {played}")
    print(f"  W/D/L   +{wins} ={draws} -{losses}")
    print(f"  score   {score:.4f}   95% CI [{lower:.4f}, {upper:.4f}]")
    print(f"  Elo     {elo(score):+.1f}")
    print()
    if lower > 0.5:
        print("The book is a measurable improvement.")
    elif upper < 0.5:
        print("The book is measurably WORSE -- that should not be possible; "
              "check book.cpp's decline rule.")
    else:
        print("No significant difference yet at this sample size. The book "
              "only covers the first few moves, so its effect is small "
              "until it has seen many more games.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
