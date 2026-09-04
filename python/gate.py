"""Decide whether a candidate weight set is actually an improvement.

Lower tuning error does not mean better play: the tuner optimises how well
the static evaluation predicts game results, which is a proxy, not the
goal. So nothing the tuner produces is ever used directly. This script
plays the candidate against the current weights and promotes it only if it
scores better by a margin the sample size actually supports.

    python python/gate.py --games 200 --movetime 100

Both sides run with the opening book disabled, so the match measures the
evaluation change and nothing else. Colours alternate and each opening is
played twice, once from each side, so an unbalanced opening cannot favour
either engine.
"""
from __future__ import annotations

import argparse
import math

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from selfplay import Engine, ROOT, find_engine, random_opening  # noqa: E402

CURRENT = ROOT / "data" / "weights.txt"
CANDIDATE = ROOT / "data" / "weights.candidate.txt"


def configure(eng: Engine, weights: Path | None) -> None:
    """Point one engine at a weight set. None means built-in defaults."""
    eng.set_option("OwnBook", "false")
    if weights is None:
        eng.send("weights reset")
    else:
        # Quoted: the engine runs with ROOT as its cwd, but the path
        # may still be absolute and contain spaces.
        eng.send(f'weights load "{weights.as_posix()}"')
        reply = eng.read_until("weights ")
        if not reply.startswith("weights loaded"):
            sys.exit(f"could not load {weights}: {reply}")


def play_game(white: Engine, black: Engine, ref: Engine, movetime: int,
              max_plies: int, opening: list[str]) -> str:
    """One game. `ref` is used only for rules queries, never to move."""
    moves = list(opening)
    seen: dict[str, int] = {}

    while True:
        st = ref.status(moves)
        if int(st["legal"]) == 0:
            if st["incheck"] == "1":
                return "0-1" if st["stm"] == "w" else "1-0"
            return "1/2-1/2"
        if int(st["halfmove"]) >= 100 or len(moves) >= max_plies:
            return "1/2-1/2"

        board_key = " ".join(ref.fen(moves).split()[:4])
        seen[board_key] = seen.get(board_key, 0) + 1
        if seen[board_key] >= 3:
            return "1/2-1/2"

        mover = white if st["stm"] == "w" else black
        mv = mover.bestmove(moves, movetime)
        if not mv or mv == "0000":
            return "1/2-1/2"
        moves.append(mv)


def elo(score: float) -> float:
    if score <= 0.0:
        return float("-inf")
    if score >= 1.0:
        return float("inf")
    return -400.0 * math.log10(1.0 / score - 1.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=200,
                    help="played in colour-reversed pairs, so rounded to even")
    ap.add_argument("--movetime", type=int, default=100)
    ap.add_argument("--max-plies", type=int, default=200)
    ap.add_argument("--opening-plies", type=int, default=4)
    ap.add_argument("--candidate", default=str(CANDIDATE))
    ap.add_argument("--baseline", default=str(CURRENT),
                    help="weights to beat; falls back to built-in defaults")
    ap.add_argument("--promote", action="store_true",
                    help="overwrite the baseline if the candidate passes")
    ap.add_argument("--engine", default=None)
    args = ap.parse_args()

    candidate = Path(args.candidate)
    if not candidate.exists():
        sys.exit(f"no candidate weights at {candidate} -- run tune first")
    baseline = Path(args.baseline)
    baseline_arg = baseline if baseline.exists() else None

    path = args.engine or find_engine()
    a = Engine(path, own_book=False)   # candidate
    b = Engine(path, own_book=False)   # baseline
    ref = Engine(path, own_book=False)  # rules oracle only
    configure(a, candidate)
    configure(b, baseline_arg)

    wins = draws = losses = 0
    outcomes: list[float] = []
    aborted = False
    pairs = max(1, args.games // 2)

    try:
        for pair in range(1, pairs + 1):
            opening = random_opening(ref, args.opening_plies)
            for candidate_is_white in (True, False):
                white, black = (a, b) if candidate_is_white else (b, a)
                try:
                    result = play_game(white, black, ref, args.movetime,
                                       args.max_plies, opening)
                except OSError as exc:
                    # An engine process died. Losing the whole match over a
                    # transient failure throws away everything played so
                    # far, so stop cleanly and report the partial result.
                    print(f"engine stopped responding ({exc}); "
                          f"reporting the {len(outcomes)} games played",
                          flush=True)
                    aborted = True
                    break

                if result == "1/2-1/2":
                    draws += 1
                    outcomes.append(0.5)
                else:
                    white_won = result == "1-0"
                    candidate_won = white_won == candidate_is_white
                    if candidate_won:
                        wins += 1
                        outcomes.append(1.0)
                    else:
                        losses += 1
                        outcomes.append(0.0)

            if aborted:
                break
            played = len(outcomes)
            score = sum(outcomes) / played
            print(f"pair {pair:3d}/{pairs}  +{wins} ={draws} -{losses}  "
                  f"score {score:.3f}", flush=True)
    finally:
        for eng in (a, b, ref):
            eng.quit()

    played = len(outcomes)
    if played == 0:
        print("no games completed")
        return 1
    score = sum(outcomes) / played
    # Sample standard error over the actual per-game results, so draws are
    # handled properly rather than assumed away.
    if played > 1:
        mean = score
        var = sum((x - mean) ** 2 for x in outcomes) / (played - 1)
        se = math.sqrt(var / played)
    else:
        se = 0.5
    lower = score - 1.96 * se

    print()
    print(f"  games      {played}")
    print(f"  W/D/L      +{wins} ={draws} -{losses}")
    print(f"  score      {score:.4f}  (95% lower bound {lower:.4f})")
    print(f"  Elo        {elo(score):+.1f}"
          f"   lower bound {elo(lower) if lower > 0 else float('-inf'):+.1f}")

    passed = lower > 0.5
    print()
    if passed:
        print("PASS: the candidate is better than the baseline at 95% "
              "confidence.")
    else:
        print("REJECT: not enough evidence the candidate is better. "
              "Keeping the current weights.")
        print("        (more games would narrow the interval; a score at or "
              "below 0.5 means the tuning did not help)")

    if passed and args.promote:
        baseline.parent.mkdir(parents=True, exist_ok=True)
        if baseline.exists():
            backup = baseline.with_suffix(".previous.txt")
            shutil.copy2(baseline, backup)
            print(f"        previous weights kept at {backup}")
        shutil.copy2(candidate, baseline)
        print(f"PROMOTED: {candidate} -> {baseline}")
    elif passed:
        print("        re-run with --promote to install these weights.")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
