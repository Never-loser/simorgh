"""Say *why* Simorgh evaluates a position the way it does, in Persian.

    python python/explain.py --fen "8/5p2/4k3/8/2P5/1P6/P4PPP/4K3 w - - 0 1"
    python python/explain.py --moves e2e4 e7e5 g1f3 --best

Every other engine can tell you a position is worth +0.47. None of the
strong ones can tell you which +0.47, because they evaluate with a neural
network whose weights have no human meaning. Simorgh's evaluation is
hand-written, so it decomposes into named terms, and this renders those
terms as sentences.

The engine does the arithmetic and prints machine-readable term lines; the
translation lives here. That keeps UCI output ASCII and protocol-clean, and
means a second language is a dictionary rather than an engine change.
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from selfplay import find_engine  # noqa: E402

# Persian labels. Anything the engine emits that is missing here falls back
# to its raw name, so adding an eval term degrades to English rather than
# vanishing from the explanation.
FA = {
    "material.pawn": "برتری پیاده",
    "material.knight": "برتری اسب",
    "material.bishop": "برتری فیل",
    "material.rook": "برتری رخ",
    "material.queen": "برتری وزیر",
    "placement.pawn": "جای‌گیری پیاده‌ها",
    "placement.knight": "جای‌گیری اسب‌ها",
    "placement.bishop": "جای‌گیری فیل‌ها",
    "placement.rook": "جای‌گیری رخ‌ها",
    "placement.queen": "جای‌گیری وزیر",
    "king.placement": "موقعیت شاه",
    "pawns.passed": "پیاده گذشته",
    "pawns.isolated": "پیاده منزوی",
    "pawns.doubled": "پیاده دوتایی",
    "bishop.pair": "جفت فیل",
    "rounding": "گِردکردن (تقسیم صحیح در تناسب مرحله)",
}

EN = {
    "material.pawn": "pawn material", "material.knight": "knight material",
    "material.bishop": "bishop material", "material.rook": "rook material",
    "material.queen": "queen material",
    "placement.pawn": "pawn placement", "placement.knight": "knight placement",
    "placement.bishop": "bishop placement", "placement.rook": "rook placement",
    "placement.queen": "queen placement",
    "king.placement": "king placement", "pawns.passed": "passed pawns",
    "pawns.isolated": "isolated pawns", "pawns.doubled": "doubled pawns",
    "bishop.pair": "bishop pair", "rounding": "tapering rounding",
}

WHITE_FA, BLACK_FA = "سفید", "سیاه"


def squares(detail: str, fa: bool) -> str:
    """Render "wa2 wh2 bf7" as a readable list, grouped by colour."""
    if not detail:
        return ""
    # Material details are a count comparison ("6v1"), not squares.
    m = re.fullmatch(r"(\d+)v(\d+)", detail)
    if m:
        a, b = m.group(1), m.group(2)
        return (f"{a} در برابر {b}" if fa else f"{a} v {b}")

    white, black = [], []
    for tok in detail.split():
        if tok in ("white", "black"):
            (white if tok == "white" else black).append("")
            continue
        if tok and tok[0] in "wb":
            (white if tok[0] == "w" else black).append(tok[1:])
        else:
            white.append(tok)

    parts = []
    for side, items in ((WHITE_FA if fa else "white", white),
                        (BLACK_FA if fa else "black", black)):
        if not items:
            continue
        named = [x for x in items if x]
        parts.append(f"{side}: {', '.join(named)}" if named else side)
    return " / ".join(parts)


def pawns(cp: int) -> str:
    return f"{cp/100:+.2f}"


def run(cmds: list[str]) -> str:
    proc = subprocess.run([find_engine()],
                          input="\n".join(cmds) + "\nquit\n",
                          capture_output=True, text=True, timeout=120,
                          cwd=str(ROOT))
    return proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fen", default=None)
    ap.add_argument("--moves", nargs="*", default=None,
                    help="UCI moves from the start position")
    ap.add_argument("--best", action="store_true",
                    help="also search, and show the move it would play")
    ap.add_argument("--movetime", type=int, default=1000)
    ap.add_argument("--all", action="store_true",
                    help="list every term, not just the ones that matter")
    ap.add_argument("--english", action="store_true")
    args = ap.parse_args()
    fa = not args.english

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    if args.fen:
        setpos = f"position fen {args.fen}"
    elif args.moves:
        setpos = "position startpos moves " + " ".join(args.moves)
    else:
        setpos = "position startpos"

    cmds = [setpos, "explain"]
    if args.best:
        cmds.append(f"go movetime {args.movetime}")
    out = run(cmds)

    terms, phase, white, total, actual, best = [], (0, 1), None, None, None, None
    for line in out.splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "explain":
            a, b = p[2].split("/")
            phase = (int(a), int(b))
        elif p[0] == "term":
            detail = " ".join(p[p.index("on") + 1:]) if "on" in p else ""
            terms.append((p[1], int(p[2]), detail))
        elif p[0] == "white":
            white = int(p[1])
        elif p[0] == "score":
            total = int(p[1])
        elif p[0] == "actual":
            actual = int(p[1])
        elif p[0] == "bestmove":
            best = p[1]

    if total is None or actual is None or white is None:
        print(out or "(engine said nothing)")
        return 1
    # The engine reports both numbers so this can be checked here rather
    # than trusted. If they ever differ the explanation is wrong, and
    # saying so is more useful than printing a confident breakdown.
    if total != actual:
        print(f"!! breakdown {total} != evaluate() {actual} -- "
              f"the explanation is out of date with the evaluation")
        return 1

    pct = 100 * phase[0] // phase[1] if phase[1] else 0
    if fa:
        stage = ("میانه‌بازی" if pct >= 70 else
                 "آخربازی" if pct <= 30 else "میانه به آخربازی")
        who = WHITE_FA if white > 0 else BLACK_FA
        turn = BLACK_FA if total != white else WHITE_FA
        print()
        print(f"  ارزیابی: {pawns(abs(white))} پیاده به سود {who}"
              if white else "  ارزیابی: برابر")
        print(f"  مرحله:   {stage} ({phase[0]}/{phase[1]})   نوبت: {turn}")
        print()
        print("  دلیل‌ها، به ترتیب اهمیت:")
    else:
        stage = ("middlegame" if pct >= 70 else
                 "endgame" if pct <= 30 else "middle to endgame")
        turn = "black" if total != white else "white"
        print(f"\n  evaluation: {pawns(white)} from White's point of view")
        print(f"  phase:      {stage} ({phase[0]}/{phase[1]})   to move: {turn}\n")
        print("  reasons, largest first:")

    shown = [t for t in terms if args.all or abs(t[1]) >= 5]
    shown.sort(key=lambda t: -abs(t[1]))
    if not shown:
        print("    " + ("هیچ عامل قابل‌توجهی — پوزیشن متعادل است."
                        if fa else "nothing significant; the position is balanced."))
    for name, value, detail in shown:
        label = (FA if fa else EN).get(name, name)
        where = squares(detail, fa)
        line = f"    {pawns(value):>6}  {label}"
        if where:
            line += f"  ({where})"
        print(line)

    print()
    if best:
        print(("  حرکت پیشنهادی: " if fa else "  best move: ") + best)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
