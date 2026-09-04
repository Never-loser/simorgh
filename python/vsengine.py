"""Measure Simorgh's strength against an external UCI engine.

Everything else in this project measures Simorgh against itself, which can
only ever give a *relative* number. To put a rating on it you need an
opponent whose strength is already known:

    python python/vsengine.py --opponent tools/stockfish.exe \\
        --opponent-elo 1500 --games 200

The opponent is set to a fixed strength with UCI_LimitStrength/UCI_Elo,
Simorgh's score against it is converted to an Elo difference, and that is
added to the opponent's nominal rating.

Read the result as a ballpark, not a measurement. It inherits whatever
error is in the opponent's own calibration: Stockfish's UCI_Elo is tuned
against human ratings at longer time controls, so it is approximate, and
at fast time controls it tends to be stronger than the number suggests.
A real rating needs games against many rated opponents -- a Lichess bot
account is the honest way to get one.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from selfplay import Engine, find_engine, random_opening  # noqa: E402


class UciEngine:
    """A minimal UCI client for an arbitrary engine."""

    def __init__(self, path: str, name: str):
        self.name = name
        # Run from the project root, not the binary's own folder. A Simorgh
        # build loads data/weights.txt relative to its working directory, so
        # starting it elsewhere silently gives it the built-in defaults --
        # which would make a weights comparison measure the wrong thing.
        self.p = subprocess.Popen(
            [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
            cwd=str(ROOT))
        self.send("uci")
        self.read_until("uciok")
        self.send("isready")
        self.read_until("readyok")

    def send(self, cmd: str) -> None:
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def set_option(self, name: str, value) -> None:
        self.send(f"setoption name {name} value {value}")

    def read_until(self, prefix: str) -> str:
        while True:
            line = self.p.stdout.readline()
            if not line:
                return ""
            line = line.rstrip()
            if line.startswith(prefix):
                return line

    def bestmove(self, moves: list[str], movetime: int) -> str:
        cmd = "position startpos"
        if moves:
            cmd += " moves " + " ".join(moves)
        self.send(cmd)
        self.send(f"go movetime {movetime}")
        line = self.read_until("bestmove")
        parts = line.split()
        return parts[1] if len(parts) > 1 else ""

    def new_game(self) -> None:
        self.send("ucinewgame")
        self.send("isready")
        self.read_until("readyok")

    def quit(self) -> None:
        try:
            self.send("quit")
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def limit_strength(eng: UciEngine, elo: int) -> bool:
    """Ask the opponent to play at `elo`. False if it has no such option."""
    eng.send("uci")
    options: dict[str, str] = {}
    while True:
        line = eng.p.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if line.startswith("option name "):
            rest = line[len("option name "):]
            name = rest.split(" type ")[0]
            options[name] = rest
        if line == "uciok":
            break

    if "UCI_LimitStrength" not in options or "UCI_Elo" not in options:
        return False

    # Respect the engine's own advertised bounds.
    spec = options["UCI_Elo"]
    low, high = 1320, 3200
    for key, target in (("min ", "low"), ("max ", "high")):
        if key in spec:
            try:
                value = int(spec.split(key)[1].split()[0])
                if target == "low":
                    low = value
                else:
                    high = value
            except (IndexError, ValueError):
                pass

    clamped = max(low, min(high, elo))
    eng.set_option("UCI_LimitStrength", "true")
    eng.set_option("UCI_Elo", clamped)
    eng.send("isready")
    eng.read_until("readyok")
    if clamped != elo:
        print(f"  note: {eng.name} clamps UCI_Elo to [{low}, {high}]; "
              f"using {clamped}", flush=True)
    return True


def play_game(white, black, ref: Engine, movetime: int, max_plies: int,
              opening: list[str]) -> str:
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
        # An illegal move from either side ends the game against the
        # offender rather than corrupting the match.
        if mv not in ref.legal(moves):
            print(f"  {getattr(mover, 'name', '?')} played the illegal move "
                  f"{mv}; forfeiting that game", flush=True)
            return "0-1" if st["stm"] == "w" else "1-0"
        moves.append(mv)


def elo_diff(score: float) -> float:
    if score <= 0.0:
        return float("-inf")
    if score >= 1.0:
        return float("inf")
    return -400.0 * math.log10(1.0 / score - 1.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--opponent", required=True, help="path to a UCI engine")
    ap.add_argument("--opponent-elo", type=int, default=1500,
                    help="strength to set the opponent to, and the rating "
                         "the result is anchored on")
    ap.add_argument("--games", type=int, default=200,
                    help="played in colour-reversed pairs")
    ap.add_argument("--movetime", type=int, default=100)
    ap.add_argument("--max-plies", type=int, default=200)
    ap.add_argument("--opening-plies", type=int, default=4,
                    help="random plies to start each pair, for variety")
    ap.add_argument("--book", action="store_true",
                    help="let Simorgh use its opening book (off by default, "
                         "so the number reflects the engine itself)")
    ap.add_argument("--engine", default=None, help="path to Simorgh")
    args = ap.parse_args()

    opponent_path = Path(args.opponent)
    if not opponent_path.exists():
        sys.exit(f"no engine at {opponent_path}")

    simorgh_path = args.engine or find_engine()
    us = UciEngine(simorgh_path, "Simorgh")
    them = UciEngine(str(opponent_path), opponent_path.stem)
    ref = Engine(simorgh_path, own_book=False)  # rules oracle only

    us.set_option("OwnBook", "true" if args.book else "false")

    if not limit_strength(them, args.opponent_elo):
        print(f"warning: {them.name} has no UCI_LimitStrength/UCI_Elo, so it "
              f"will play at full strength.\n"
              f"         The anchor of {args.opponent_elo} will be wrong.",
              flush=True)

    wins = draws = losses = 0
    outcomes: list[float] = []
    aborted = False
    pairs = max(1, args.games // 2)

    print(f"\nSimorgh vs {them.name} @ nominal {args.opponent_elo} Elo, "
          f"{args.movetime}ms/move, book {'on' if args.book else 'off'}\n",
          flush=True)

    try:
        for pair in range(1, pairs + 1):
            opening = (random_opening(ref, args.opening_plies)
                       if args.opening_plies else [])
            for we_are_white in (True, False):
                us.new_game()
                them.new_game()
                white, black = (us, them) if we_are_white else (them, us)
                try:
                    result = play_game(white, black, ref, args.movetime,
                                       args.max_plies, opening)
                except OSError as exc:
                    # An engine process died. Report what was played rather
                    # than losing the whole match to a transient failure.
                    print(f"engine stopped responding ({exc}); reporting "
                          f"the {len(outcomes)} games played", flush=True)
                    aborted = True
                    break
                if result == "1/2-1/2":
                    draws += 1
                    outcomes.append(0.5)
                else:
                    we_won = (result == "1-0") == we_are_white
                    wins += we_won
                    losses += not we_won
                    outcomes.append(1.0 if we_won else 0.0)

            if aborted:
                break
            score = sum(outcomes) / len(outcomes)
            print(f"pair {pair:3d}/{pairs}  +{wins} ={draws} -{losses}  "
                  f"score {score:.3f}", flush=True)
    finally:
        for eng in (us, them):
            eng.quit()
        ref.quit()

    played = len(outcomes)
    if played == 0:
        print("no games completed")
        return 1
    score = sum(outcomes) / played
    if played > 1:
        var = sum((x - score) ** 2 for x in outcomes) / (played - 1)
        se = math.sqrt(var / played)
    else:
        se = 0.5
    low, high = score - 1.96 * se, score + 1.96 * se

    diff = elo_diff(score)
    print()
    print(f"  games        {played}")
    print(f"  W/D/L        +{wins} ={draws} -{losses}")
    print(f"  score        {score:.4f}   95% CI [{low:.4f}, {high:.4f}]")
    print(f"  Elo diff     {diff:+.1f}")
    print()
    print(f"  ESTIMATE     {args.opponent_elo + diff:.0f} Elo")
    if 0.0 < low and high < 1.0:
        print(f"               95% range "
              f"{args.opponent_elo + elo_diff(low):.0f} to "
              f"{args.opponent_elo + elo_diff(high):.0f}")
    print()
    if score > 0.85 or score < 0.15:
        print("  The match was lopsided, so the estimate is unreliable --")
        print("  re-run with --opponent-elo closer to the result above.")
    print("  Anchored on the opponent's own calibration, which is itself")
    print("  approximate. Treat this as a ballpark, not a rating.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
