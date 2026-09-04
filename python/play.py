import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_engine():
    for cand in [ROOT / 'cpp' / 'build' / 'simorgh.exe',
                 ROOT / 'cpp' / 'build' / 'simorgh']:
        if cand.exists():
            return str(cand)
    sys.exit('engine binary not found; build the cpp project first')


class Engine:
    def __init__(self, path):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.moves = []

    def send(self, cmd):
        self.p.stdin.write(cmd + '\n')
        self.p.stdin.flush()

    def read_until(self, prefix):
        while True:
            line = self.p.stdout.readline()
            if not line:
                return ''
            line = line.rstrip()
            if line.startswith(prefix):
                return line

    def position(self, moves):
        cmd = 'position startpos'
        if moves:
            cmd += ' moves ' + ' '.join(moves)
        self.send(cmd)

    def board(self):
        self.position(self.moves)
        self.send('d')
        lines = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            lines.append(line.rstrip())
            if line.startswith('Key:'):
                break
        return '\n'.join(lines)

    def legal(self):
        self.position(self.moves)
        self.send('legal')
        line = self.read_until('legal')
        return set(line.split()[1:])

    def bestmove(self, movetime=1000):
        self.position(self.moves)
        # Always send an explicit limit. A bare `go` used to mean "search
        # forever", so this script hung here waiting for a bestmove that
        # never came.
        self.send(f'go movetime {movetime}')
        return self.read_until('bestmove ').split()[1]

    def quit(self):
        self.send('quit')
        self.p.wait()


def main():
    ap = argparse.ArgumentParser(
        description='play a game against Simorgh in the terminal '
                    '(see gui.py for the graphical version)')
    ap.add_argument('--black', action='store_true', help='you play black; engine starts')
    ap.add_argument('--engine', default=None, help='path to simorgh binary')
    ap.add_argument('--movetime', type=int, default=1000,
                    help='engine thinking time per move, in ms')
    ap.add_argument('--elo', type=int, default=None,
                    help='limit engine strength to roughly this rating')
    args = ap.parse_args()

    eng = Engine(args.engine or find_engine())
    if args.elo is not None:
        eng.send('setoption name UCI_LimitStrength value true')
        eng.send(f'setoption name UCI_Elo value {args.elo}')
    human = 'b' if args.black else 'w'

    print('Simorgh -- enter moves in UCI notation (e2e4), or: undo | new | quit')

    try:
        while True:
            print()
            print(eng.board())

            side = 'w' if len(eng.moves) % 2 == 0 else 'b'

            legal = eng.legal()
            if not legal:
                print('\nGame over.')
                break

            if side == human:
                raw = input(f'\n[{side}] your move: ').strip().lower()
                if not raw:
                    continue
                if raw == 'quit':
                    break
                if raw == 'new':
                    eng.moves = []
                    continue
                if raw == 'undo':
                    n = 2 if len(eng.moves) >= 2 else 1
                    del eng.moves[-n:]
                    continue
                if raw not in legal:
                    print(f'illegal move: {raw}')
                    continue
                eng.moves.append(raw)
            else:
                mv = eng.bestmove(args.movetime)
                if mv == '0000':
                    print('\nGame over.')
                    break
                print(f'\nengine plays: {mv}')
                eng.moves.append(mv)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        eng.quit()


if __name__ == '__main__':
    main()
