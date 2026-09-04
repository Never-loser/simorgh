import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle


def find_engine():
    root = Path(__file__).resolve().parents[1]
    for cand in [root / 'cpp' / 'build' / 'simorgh.exe',
                 root / 'cpp' / 'build' / 'simorgh']:
        if cand.exists():
            return str(cand)
    sys.exit('engine binary not found')


class Player:
    def __init__(self, exe):
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def send(self, cmd):
        self.p.stdin.write(cmd + '\n')
        self.p.stdin.flush()

    def read_until(self, prefix):
        while True:
            line = self.p.stdout.readline()
            if not line:
                return ''
            if line.startswith(prefix):
                return line.rstrip()

    def choose(self, moves, depth):
        cmd = 'position startpos'
        if moves:
            cmd += ' moves ' + ' '.join(moves)
        self.send(cmd)
        self.send(f'go depth {depth}')
        return self.read_until('bestmove ').split()[1]

    def current_fen(self, moves):
        cmd = 'position startpos'
        if moves:
            cmd += ' moves ' + ' '.join(moves)
        self.send(cmd)
        self.send('d')
        fen = ''
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            if line.startswith('Fen: '):
                fen = line[5:].strip()
            if line.startswith('Key:'):
                break
        return fen

    def quit(self):
        self.send('quit')
        self.p.wait()


def play_game(white, black, max_plies):
    moves = []
    seen = {}
    players = {'w': white, 'b': black}

    for ply in range(max_plies):
        side = 'w' if ply % 2 == 0 else 'b'
        mv = players[side].choose(moves, players[side].depth)

        if mv == '0000':
            fen = players[side].current_fen(moves)
            st = oracle.parse_fen(fen)
            checked = oracle.attacked(st, oracle.king_sq(st, st.side),
                                      'b' if st.side == 'w' else 'w')
            winner = 'b' if side == 'w' else 'w'
            return ('checkmate' if checked else 'stalemate', winner if checked else None,
                    len(moves))

        moves.append(mv)

        fen = players[side].current_fen(moves)
        parts = fen.split()
        if int(parts[4]) >= 100:
            return ('fifty-move', None, len(moves))
        key = ' '.join(parts[:4])
        seen[key] = seen.get(key, 0) + 1
        if seen[key] >= 3:
            return ('repetition', None, len(moves))

    return ('ply-limit', None, max_plies)


def main():
    ap = argparse.ArgumentParser(description='match Simorgh against itself at two depths')
    ap.add_argument('--games', type=int, default=4)
    ap.add_argument('--strong', type=int, default=6)
    ap.add_argument('--weak', type=int, default=2)
    ap.add_argument('--max-plies', type=int, default=240)
    ap.add_argument('--engine', default=None)
    args = ap.parse_args()

    path = args.engine or find_engine()
    strong = Player(path)
    strong.depth = args.strong
    weak = Player(path)
    weak.depth = args.weak

    try:
        strong.send('uci')
        strong.read_until('uciok')
        weak.send('uci')
        weak.read_until('uciok')

        strong_pts = weak_pts = draws = 0
        for g in range(args.games):
            strong_white = g % 2 == 0
            white, black = (strong, weak) if strong_white else (weak, strong)
            reason, winner, plies = play_game(white, black, args.max_plies)

            tag = 'draw'
            if winner:
                strong_won = (winner == 'w') == strong_white
                if strong_won:
                    strong_pts += 1
                    tag = 'STRONG wins'
                else:
                    weak_pts += 1
                    tag = 'weak wins'
            else:
                draws += 1
            print(f'game {g + 1}: {reason} in {plies} plies -> {tag}')

        print(f'\nfinal score  strong(d{args.strong}) {strong_pts}'
              f'  -  {draws}  -  {weak_pts} weak(d{args.weak})')
    finally:
        strong.quit()
        weak.quit()


if __name__ == '__main__':
    main()
