import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
     {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609}),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
     {1: 48, 2: 2039, 3: 97862, 4: 4085603}),
    ("position3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
     {1: 14, 2: 191, 3: 2812, 4: 43238, 5: 674624}),
    ("position4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
     {1: 6, 2: 264, 3: 9467, 4: 422333}),
    ("position5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
     {1: 44, 2: 1486, 3: 62379, 4: 2103487}),
    ("position6", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
     {1: 46, 2: 2079, 3: 89890, 4: 3894594}),
]


def find_engine():
    for cand in [ROOT / 'cpp' / 'build' / 'simorgh.exe',
                 ROOT / 'cpp' / 'build' / 'simorgh',
                 ROOT / 'cpp' / 'simorgh.exe']:
        if cand.exists():
            return str(cand)
    sys.exit('engine binary not found; build the cpp project first')


class Engine:
    def __init__(self, path):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)

    def send(self, cmd):
        self.p.stdin.write(cmd + '\n')
        self.p.stdin.flush()

    def perft(self, fen, depth):
        self.send(f'position fen {fen}')
        self.send(f'go perft {depth}')
        nodes = None
        while nodes is None:
            line = self.p.stdout.readline().strip()
            if line.startswith('nodes'):
                nodes = int(line.split()[1])
        return nodes

    def quit(self):
        self.send('quit')
        self.p.wait()


def main():
    ap = argparse.ArgumentParser(description='validate Simorgh move generation')
    ap.add_argument('--quick', action='store_true', help='only depths <= 3')
    args = ap.parse_args()

    engine = Engine(find_engine())
    failures = 0
    total_nodes = 0
    t0 = time.perf_counter()

    try:
        for name, fen, table in CASES:
            for depth in sorted(table):
                if args.quick and depth > 3:
                    continue
                expected = table[depth]
                got = engine.perft(fen, depth)
                total_nodes += got
                ok = got == expected
                failures += not ok
                mark = 'PASS' if ok else f'FAIL expected {expected}'
                print(f'{name:<10} d{depth}  {got:>12,}  {mark}')
    finally:
        engine.quit()

    secs = time.perf_counter() - t0
    print(f'\n{"ALL TESTS PASSED" if failures == 0 else f"{failures} FAILURES"}'
          f'  ({total_nodes:,} nodes in {secs:.1f}s)')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
