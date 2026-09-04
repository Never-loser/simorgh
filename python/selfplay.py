"""Play Simorgh against itself, then feed the results back into the engine.

Two things come out of every game:

  * the game result is folded into the learned opening book (`learn`), so
    the engine stops repeating openings that lose;
  * the quiet positions are written to a dataset labelled with the result,
    which python/tune.py turns into new evaluation weights.

    python python/selfplay.py --games 50 --movetime 100

Positions from the first few plies are skipped (they are book moves, not
evaluation evidence) as are positions where the side to move is in check,
because the static evaluation is meaningless there.
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "positions.txt"


def find_engine() -> str:
    for cand in [ROOT / "cpp" / "build" / "simorgh.exe",
                 ROOT / "cpp" / "build" / "simorgh"]:
        if cand.exists():
            return str(cand)
    sys.exit("engine binary not found; build the cpp project first")


class Engine:
    def __init__(self, path: str, own_book: bool = True):
        self.p = subprocess.Popen(
            [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
            cwd=str(ROOT))
        self.send("uci")
        self.read_until("uciok")
        self.set_option("OwnBook", "true" if own_book else "false")

    def send(self, cmd: str) -> None:
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def set_option(self, name: str, value: str) -> None:
        self.send(f"setoption name {name} value {value}")

    def read_until(self, prefix: str) -> str:
        while True:
            line = self.p.stdout.readline()
            if not line:
                return ""
            line = line.rstrip()
            if line.startswith(prefix):
                return line

    def position(self, moves: list[str]) -> None:
        cmd = "position startpos"
        if moves:
            cmd += " moves " + " ".join(moves)
        self.send(cmd)

    def status(self, moves: list[str]) -> dict:
        self.position(moves)
        self.send("status")
        parts = self.read_until("status ").split()
        return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}

    def fen(self, moves: list[str]) -> str:
        self.position(moves)
        self.send("d")
        fen = ""
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            if line.startswith("Fen:"):
                fen = line.split(":", 1)[1].strip()
            if line.startswith("Key:"):
                break
        return fen

    def legal(self, moves: list[str]) -> list[str]:
        self.position(moves)
        self.send("legal")
        return self.read_until("legal").split()[1:]

    def bestmove(self, moves: list[str], movetime: int) -> str:
        self.position(moves)
        self.send(f"go movetime {movetime}")
        line = self.read_until("bestmove ")
        parts = line.split()
        if len(parts) < 2:
            # read_until returns "" when the pipe closes, i.e. the engine
            # died. Say so plainly instead of an IndexError three frames up.
            raise OSError("engine closed the connection while thinking")
        return parts[1]

    def learn(self, moves: list[str], result: str) -> str:
        self.position(moves)
        self.send(f"learn {result}")
        return self.read_until("info string")

    def quit(self) -> None:
        try:
            self.send("quit")
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def play_game(eng: Engine, movetime: int, max_plies: int,
              opening: list[str]) -> tuple[str, list[str], list[tuple[str, int]]]:
    """Returns (result, moves, [(fen, ply), ...]) for one game."""
    moves = list(opening)
    positions: list[tuple[str, int]] = []
    seen: dict[str, int] = {}

    while True:
        st = eng.status(moves)
        legal = int(st["legal"])
        in_check = st["incheck"] == "1"

        if legal == 0:
            if in_check:
                # Side to move is mated; the other side won.
                return ("0-1" if st["stm"] == "w" else "1-0", moves, positions)
            return ("1/2-1/2", moves, positions)

        if int(st["halfmove"]) >= 100:
            return ("1/2-1/2", moves, positions)

        fen = eng.fen(moves)
        # Threefold repetition, tracked on the position part of the FEN.
        board_key = " ".join(fen.split()[:4])
        seen[board_key] = seen.get(board_key, 0) + 1
        if seen[board_key] >= 3:
            return ("1/2-1/2", moves, positions)

        if len(moves) >= max_plies:
            return ("1/2-1/2", moves, positions)

        # Quiet, past-the-opening positions are the useful tuning evidence.
        if not in_check and len(moves) >= 8:
            positions.append((fen, len(moves)))

        mv = eng.bestmove(moves, movetime)
        if mv == "0000" or not mv:
            return ("1/2-1/2", moves, positions)
        moves.append(mv)


def random_opening(eng: Engine, plies: int) -> list[str]:
    moves: list[str] = []
    for _ in range(plies):
        legal = eng.legal(moves)
        if not legal:
            return moves[:-1] if moves else []
        moves.append(random.choice(legal))
    return moves


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--movetime", type=int, default=100,
                    help="milliseconds per move")
    ap.add_argument("--max-plies", type=int, default=240)
    ap.add_argument("--opening-plies", type=int, default=4,
                    help="random plies to start each game, for variety")
    ap.add_argument("--data", default=str(DEFAULT_DATA),
                    help="where to append labelled positions")
    ap.add_argument("--no-learn", action="store_true",
                    help="do not update the opening book")
    ap.add_argument("--engine", default=None)
    args = ap.parse_args()

    eng = Engine(args.engine or find_engine())
    data_path = Path(args.data)
    data_path.parent.mkdir(parents=True, exist_ok=True)

    tally = {"1-0": 0, "0-1": 0, "1/2-1/2": 0}
    written = 0

    try:
        with open(data_path, "a", encoding="utf-8") as out:
            for game in range(1, args.games + 1):
                opening = random_opening(eng, args.opening_plies)
                result, moves, positions = play_game(
                    eng, args.movetime, args.max_plies, opening)
                tally[result] += 1

                for fen, _ply in positions:
                    out.write(f"{fen};{result}\n")
                    written += 1
                out.flush()

                if not args.no_learn:
                    eng.learn(moves, result)

                print(f"game {game:3d}/{args.games}  {result:8s} "
                      f"{len(moves):3d} plies  {len(positions):3d} positions",
                      flush=True)
    finally:
        eng.quit()

    print(f"\nresults: +{tally['1-0']} ={tally['1/2-1/2']} -{tally['0-1']}")
    print(f"wrote {written} positions to {data_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
