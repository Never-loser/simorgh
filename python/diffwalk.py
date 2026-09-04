import subprocess
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
import oracle


class Engine:
    def __init__(self, exe):
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)

    def send(self, cmd):
        self.p.stdin.write(cmd + '\n')
        self.p.stdin.flush()

    def divide(self, fen, depth):
        self.send(f'position fen {fen}')
        self.send(f'go perft {depth}')
        out = {}
        while True:
            line = self.p.stdout.readline().strip()
            if line.startswith('nodes'):
                break
            if ': ' in line:
                mv, cnt = line.split(': ')
                out[mv] = int(cnt)
        return out

    def quit(self):
        self.send('quit')
        self.p.wait()


def oracle_divide(fen, depth):
    st = oracle.parse_fen(fen)
    out = {}
    total = 0
    for mv in oracle.legal_moves(st):
        name = oracle.sq_name(mv[0]) + oracle.sq_name(mv[1])
        cnt = 1 if depth == 1 else oracle.perft(oracle.make(st, mv), depth - 1)
        out[name] = cnt
        total += cnt
    return out, total


def walk(eng, fen, depth, path):
    eng_out = eng.divide(fen, depth)
    ora_out, ora_total = oracle_divide(fen, depth)

    bad = {}
    for m, c in ora_out.items():
        e = eng_out.get(m)
        if e != c:
            bad[m] = (e, c)
    extra = [m for m in eng_out if m not in ora_out]

    if not bad and not extra:
        return True

    print(f'\nDIVERGENCE at {" ".join(path) or "(root)"}')
    print(f'FEN: {fen}')
    for m, (e, o) in sorted(bad.items()):
        e_str = e if e is not None else 'ABSENT'
        print(f'  {m}: engine={e_str} oracle={o}')
    for m in sorted(extra):
        print(f'  {m}: engine={eng_out[m]} oracle=ABSENT')

    if depth <= 1:
        st = oracle.parse_fen(fen)
        print('oracle moves:', ' '.join(
            oracle.sq_name(a) + oracle.sq_name(b) + (p or '').lower()
            for a, b, p, fl in oracle.legal_moves(st)))
        return False

    for m in sorted(set(list(bad.keys()) + extra)):
        st = oracle.parse_fen(fen)
        target = None
        for mv in oracle.legal_moves(st):
            if oracle.sq_name(mv[0]) + oracle.sq_name(mv[1]) == m[:4]:
                target = oracle.make(st, mv)
                break
        if target is None:
            continue
        walk(eng, oracle.to_fen(target), depth - 1, path + [m[:4]])
        break
    return False


if __name__ == '__main__':
    exe = sys.argv[1]
    fen = sys.argv[2] if len(sys.argv) > 2 else \
        'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    depth = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    eng = Engine(exe)
    try:
        walk(eng, fen, depth, [])
    finally:
        eng.quit()
