"""Play Simorgh against itself at different strength settings.

The engine's UCI_Elo numbers are only a mapping onto its Skill Level; this
script measures what that mapping actually buys, by playing each setting
against a reference and converting the score to an Elo difference.

    python python/calibrate.py --games 20 --movetime 100

Note this measures *relative* strength only. Anchoring the numbers to real
Elo needs games against an engine of known rating (or a rated site); see
the README.
"""
from __future__ import annotations

import argparse
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_engine() -> str:
    for cand in [ROOT / 'cpp' / 'build' / 'simorgh.exe',
                 ROOT / 'cpp' / 'build' / 'simorgh']:
        if cand.exists():
            return str(cand)
    sys.exit('engine binary not found; build the cpp project first')


class Engine:
    """One UCI process, configured for a given strength."""

    def __init__(self, path: str, elo: int | None = None,
                 depth: int | None = None):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True,
                                  bufsize=1)
        self.elo = elo
        self.depth = depth
        self.send('uci')
        self.read_until('uciok')
        if elo is not None:
            self.send('setoption name UCI_LimitStrength value true')
            self.send(f'setoption name UCI_Elo value {elo}')
        self.send('ucinewgame')
        self.sync()

    def send(self, cmd: str) -> None:
        self.p.stdin.write(cmd + '\n')
        self.p.stdin.flush()

    def read_until(self, prefix: str) -> str:
        while True:
            line = self.p.stdout.readline()
            if not line:
                return ''
            if line.startswith(prefix):
                return line.rstrip()

    def sync(self) -> None:
        self.send('isready')
        self.read_until('readyok')

    def status(self, moves: list[str]) -> dict:
        self.set_position(moves)
        self.send('status')
        parts = self.read_until('status').split()
        return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}

    def set_position(self, moves: list[str]) -> None:
        cmd = 'position startpos'
        if moves:
            cmd += ' moves ' + ' '.join(moves)
        self.send(cmd)

    def bestmove(self, moves: list[str], movetime: int) -> str:
        self.set_position(moves)
        # A fixed depth isolates search strength from machine speed, which
        # is what the depth ladder needs to measure.
        if self.depth is not None:
            self.send(f'go depth {self.depth}')
        else:
            self.send(f'go movetime {movetime}')
        line = self.read_until('bestmove ')
        return line.split()[1] if line else '0000'

    def quit(self) -> None:
        try:
            self.send('quit')
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def random_opening(engine: Engine, plies: int) -> list[str]:
    """A short random but legal opening line.

    Without this every game between the same two settings is byte-for-byte
    identical - the engine is deterministic at full skill - so a "12 game"
    match was really one game replayed twelve times.
    """
    moves: list[str] = []
    for _ in range(plies):
        engine.set_position(moves)
        engine.send('legal')
        legal = engine.read_until('legal').split()[1:]
        if not legal:
            return moves[:-2]  # backed into a finished game; step back
        moves.append(random.choice(legal))
    return moves


def play_game(white: Engine, black: Engine, movetime: int,
              max_plies: int, opening: list[str] | None = None) -> str:
    """Return '1-0', '0-1' or '1/2-1/2'."""
    moves: list[str] = list(opening or [])
    referee = white  # any engine can answer `status`

    for ply in range(len(moves), max_plies):
        info = referee.status(moves)
        if int(info['legal']) == 0:
            if info['incheck'] == '1':
                # Side to move is mated; the other side won.
                return '0-1' if info['stm'] == 'w' else '1-0'
            return '1/2-1/2'          # stalemate
        if int(info['halfmove']) >= 100:
            return '1/2-1/2'          # fifty-move rule

        mover = white if len(moves) % 2 == 0 else black
        mv = mover.bestmove(moves, movetime)
        if mv == '0000':
            return '1/2-1/2'
        moves.append(mv)

    return '1/2-1/2'                  # adjudicated: hit the ply cap


def elo_diff(score: float, games: int) -> str:
    if games == 0:
        return 'n/a'
    if score <= 0.0:
        return '< -800'
    if score >= 1.0:
        return '> +800'
    return f'{-400 * math.log10(1 / score - 1):+.0f}'


def match(path: str, spec_a, spec_b, games: int, movetime: int,
          max_plies: int, by_depth: bool = False,
          opening_plies: int = 6) -> tuple[int, int, int]:
    def build(spec):
        return Engine(path, depth=spec) if by_depth else Engine(path, elo=spec)

    wins = draws = losses = 0
    opening: list[str] = []
    for game in range(games):
        a = build(spec_a)
        b = build(spec_b)
        # A fresh opening every second game, then the same one again with
        # the colours swapped, so both settings get each position.
        if game % 2 == 0:
            opening = random_opening(a, opening_plies)
        white, black = (a, b) if game % 2 == 0 else (b, a)
        result = play_game(white, black, movetime, max_plies, opening)
        a.quit()
        b.quit()

        if result == '1/2-1/2':
            draws += 1
        else:
            winner = white if result == '1-0' else black
            if winner is a:
                wins += 1
            else:
                losses += 1
        print(f'    game {game + 1}/{games}: {result}', flush=True)
    return wins, draws, losses


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--games', type=int, default=10,
                    help='games per pairing (even number keeps colours fair)')
    ap.add_argument('--movetime', type=int, default=100, help='ms per move')
    ap.add_argument('--max-plies', type=int, default=200)
    ap.add_argument('--reference', type=int, default=None,
                    help='Elo of the opponent every level plays (default: '
                         'unlimited strength)')
    ap.add_argument('--levels', type=int, nargs='+',
                    default=[800, 1000, 1200, 1400, 1600, 2000])
    ap.add_argument('--opening-plies', type=int, default=6,
                    help='random legal plies played before the engines take '
                         'over, to give each game a different starting point')
    ap.add_argument('--by-depth', action='store_true',
                    help='treat --levels and --reference as fixed search '
                         'depths instead of Elo settings')
    ap.add_argument('--seed', type=int, default=None,
                    help='seed for the random openings, for reproducibility')
    ap.add_argument('--engine', default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    path = args.engine or find_engine()
    unit = 'depth' if args.by_depth else 'Elo'
    ref_name = ('unlimited' if args.reference is None
                else f'{unit} {args.reference}')
    print(f'reference opponent: {ref_name}, {args.movetime}ms/move, '
          f'{args.games} games per level\n')

    rows = []
    for level in args.levels:
        print(f'  {unit} {level} vs {ref_name}:', flush=True)
        wins, draws, losses = match(path, level, args.reference, args.games,
                                    args.movetime, args.max_plies,
                                    by_depth=args.by_depth,
                                    opening_plies=args.opening_plies)
        played = wins + draws + losses
        score = (wins + 0.5 * draws) / played if played else 0.0
        rows.append((level, wins, draws, losses, score))
        print(f'    -> +{wins} ={draws} -{losses}  '
              f'score {score:.1%}  Elo {elo_diff(score, played)}\n', flush=True)

    print('\n  setting |  W  D  L | score | Elo vs ' + ref_name)
    print('  --------+----------+-------+-------------')
    for level, wins, draws, losses, score in rows:
        print(f'  {level:7d} | {wins:2d} {draws:2d} {losses:2d} | '
              f'{score:5.1%} | {elo_diff(score, wins + draws + losses)}')


if __name__ == '__main__':
    main()
