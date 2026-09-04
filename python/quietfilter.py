"""Keep only the quiet positions from a tuning dataset.

Texel tuning fits the *static* evaluation to game results, so it is only
meaningful on positions where the static evaluation is the whole story. In
a position with a hanging piece the static score is wrong by a piece and
the tuner ends up fitting the weights to that noise.

A position is quiet when its static evaluation and its quiescence score
agree: nothing can be won or lost by a forcing capture sequence.

    python python/quietfilter.py data/positions.txt data/positions.quiet.txt
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from selfplay import find_engine  # noqa: E402

# Each batch is one engine process, so a small batch means hundreds of
# process launches on a large dataset.
BATCH = 2000


def probe(engine: str, fens: list[str]) -> list[tuple[int, int]]:
    """Return (static, quiescence) for each FEN, in order."""
    cmds = []
    for fen in fens:
        cmds += [f"position fen {fen}", "eval", "qeval"]
    cmds.append("quit")
    out = subprocess.run([engine], input="\n".join(cmds) + "\n",
                         capture_output=True, text=True, timeout=600,
                         cwd=str(ROOT)).stdout

    statics: list[int] = []
    quiets: list[int] = []
    for line in out.splitlines():
        if line.startswith("eval "):
            statics.append(int(line.split()[1]))
        elif line.startswith("qeval "):
            quiets.append(int(line.split()[1]))
    if len(statics) != len(fens) or len(quiets) != len(fens):
        sys.exit(f"engine returned {len(statics)}/{len(quiets)} scores for "
                 f"{len(fens)} positions")
    return list(zip(statics, quiets))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default=str(ROOT / "data" / "positions.txt"))
    ap.add_argument("dest", nargs="?",
                    default=str(ROOT / "data" / "positions.quiet.txt"))
    ap.add_argument("--tolerance", type=int, default=0,
                    help="centipawns of disagreement still counted as quiet")
    args = ap.parse_args()

    source, dest = Path(args.source), Path(args.dest)
    if not source.exists():
        sys.exit(f"no dataset at {source}")

    rows = [line.rstrip("\n") for line in
            source.open(encoding="utf-8") if line.strip()
            and not line.startswith("#")]
    engine = find_engine()

    kept = 0
    with dest.open("w", encoding="utf-8") as out:
        for start in range(0, len(rows), BATCH):
            chunk = rows[start:start + BATCH]
            fens = [r.rsplit(";", 1)[0] for r in chunk]
            for row, (static, quiet) in zip(chunk, probe(engine, fens)):
                if abs(static - quiet) <= args.tolerance:
                    out.write(row + "\n")
                    kept += 1
            print(f"  {min(start + BATCH, len(rows))}/{len(rows)} scanned, "
                  f"{kept} quiet", flush=True)

    share = kept / len(rows) * 100 if rows else 0.0
    print(f"\nkept {kept} of {len(rows)} positions ({share:.1f}%) -> {dest}")
    if kept < 2000:
        print("note: that is a thin dataset; play more games before tuning "
              "anything beyond material values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
