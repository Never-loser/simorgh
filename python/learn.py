"""One training round: play, tune, prove it helped, keep it or throw it away.

    python python/learn.py --games 200 --gate-games 200

Each round does five things:

  1. self-play games, which grow the opening book immediately and write
     labelled positions to data/positions.txt;
  2. the dataset is filtered down to quiet positions -- ones where the
     static evaluation already agrees with the quiescence score, so
     nothing is hanging;
  3. Texel tuning of the evaluation weights. By default only the four free
     material values are fitted: a first training run cannot support all
     453 parameters (use --scope all once you have thousands of games);
  4. a gate match, candidate against the weights currently in use;
  5. promotion -- but only if the candidate actually won the match.

Step 4 is the point. Tuning error always goes down; playing strength does
not necessarily follow, especially early on when a few hundred games
cannot support 453 parameters. A rejected round is a normal outcome, not a
failure: the book still improved, the positions are still on disk, and the
next round tunes on a bigger dataset.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DATA = ROOT / "data"


def run(cmd: list[str], label: str) -> int:
    print(f"\n{'=' * 68}\n== {label}\n{'=' * 68}", flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def engine_path() -> Path:
    for cand in [ROOT / "cpp" / "build" / "simorgh.exe",
                 ROOT / "cpp" / "build" / "simorgh"]:
        if cand.exists():
            return cand
    sys.exit("engine binary not found; build the cpp project first")


def tune(data: Path, out: Path, passes: int, scope: str) -> bool:
    exe = engine_path()
    script = f'tune "{data.as_posix()}" "{out.as_posix()}" {passes} {scope}\nquit\n'
    print(f"\n{'=' * 68}\n== 3/5 tuning evaluation weights\n{'=' * 68}",
          flush=True)
    proc = subprocess.run([str(exe)], input=script, capture_output=True,
                          text=True, cwd=str(ROOT))
    ok = False
    for line in proc.stdout.splitlines():
        if line.startswith("info string tune") or line.startswith("tune "):
            print(line, flush=True)
        if line.startswith("tune ok"):
            ok = True
    if not ok:
        print("tuning failed:", proc.stdout.strip().splitlines()[-1:] or proc.stderr)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=200,
                    help="self-play games this round")
    ap.add_argument("--movetime", type=int, default=60)
    ap.add_argument("--gate-games", type=int, default=200,
                    help="games in the promotion match")
    ap.add_argument("--gate-movetime", type=int, default=60)
    ap.add_argument("--passes", type=int, default=6,
                    help="max tuner passes per step size")
    ap.add_argument("--scope", choices=["material", "all", "pst"],
                    default="material",
                    help="which weights to fit. 'material' is 4 parameters "
                         "and is the safe default; 'all' is 453 and needs "
                         "far more games before it stops overfitting")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--skip-tuning", action="store_true",
                    help="only grow the opening book")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    positions = DATA / "positions.txt"
    candidate = DATA / "weights.candidate.txt"

    for rnd in range(1, args.rounds + 1):
        print(f"\n########## round {rnd}/{args.rounds} ##########", flush=True)

        rc = run([PY, "python/selfplay.py",
                  "--games", str(args.games),
                  "--movetime", str(args.movetime)],
                 f"1/5 self-play: {args.games} games (grows the book)")
        if rc != 0:
            return rc

        if args.skip_tuning:
            print("\nskipping tuning; the opening book was still updated.")
            continue

        if not positions.exists():
            print("no position data was produced; stopping.")
            return 1

        # Texel tuning is only valid where the static evaluation is the
        # whole story, so drop positions with something hanging first.
        quiet = DATA / "positions.quiet.txt"
        rc = run([PY, "python/quietfilter.py", str(positions), str(quiet)],
                 "2/5 filtering to quiet positions")
        if rc != 0 or not quiet.exists():
            return 1

        if not tune(quiet, candidate, args.passes, args.scope):
            return 1

        rc = run([PY, "python/gate.py",
                  "--games", str(args.gate_games),
                  "--movetime", str(args.gate_movetime),
                  "--promote"],
                 f"4/5 gate match: candidate vs current ({args.gate_games} games)")

        print(f"\n{'=' * 68}")
        if rc == 0:
            print("== 5/5 promoted: the engine is measurably stronger.")
        else:
            print("== 5/5 rejected: weights unchanged. The book still grew,")
            print("==      and the data carries over to the next round.")
        print("=" * 68, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
