import sys

KNIGHT_DELTAS = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
KING_DELTAS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
ROOK_DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]
BISHOP_DIRS = [(1, 1), (-1, 1), (1, -1), (-1, -1)]


def sq_name(s):
    return chr(ord('a') + s % 8) + str(s // 8 + 1)


def name_sq(n):
    return (int(n[1]) - 1) * 8 + (ord(n[0]) - ord('a'))


class State:
    def __init__(self):
        self.board = ['.'] * 64
        self.side = 'w'
        self.castling = ''
        self.ep = -1
        self.halfmove = 0
        self.fullmove = 1


def parse_fen(fen):
    st = State()
    parts = fen.split()
    rows = parts[0].split('/')
    for r in range(8):
        f = 0
        for ch in rows[7 - r]:
            if ch.isdigit():
                f += int(ch)
            else:
                st.board[r * 8 + f] = ch
                f += 1
    st.side = parts[1]
    st.castling = '' if parts[2] == '-' else parts[2]
    st.ep = -1 if len(parts) < 4 or parts[3] == '-' else name_sq(parts[3])
    if len(parts) > 4:
        st.halfmove = int(parts[4])
    if len(parts) > 5:
        st.fullmove = int(parts[5])
    return st


def color_of(piece):
    return 'w' if piece.isupper() else 'b'


def attacked(st, s, by):
    board = st.board
    f0, r0 = s % 8, s // 8
    pawn = 'P' if by == 'w' else 'p'
    pr = r0 - 1 if by == 'w' else r0 + 1
    if 0 <= pr < 8:
        for df in (-1, 1):
            nf = f0 + df
            if 0 <= nf < 8 and board[pr * 8 + nf] == pawn:
                return True
    knight = 'N' if by == 'w' else 'n'
    for df, dr in KNIGHT_DELTAS:
        nf, nr = f0 + df, r0 + dr
        if 0 <= nf < 8 and 0 <= nr < 8 and board[nr * 8 + nf] == knight:
            return True
    king = 'K' if by == 'w' else 'k'
    for df, dr in KING_DELTAS:
        nf, nr = f0 + df, r0 + dr
        if 0 <= nf < 8 and 0 <= nr < 8 and board[nr * 8 + nf] == king:
            return True
    rookq = ('R', 'Q') if by == 'w' else ('r', 'q')
    for df, dr in ROOK_DIRS:
        nf, nr = f0 + df, r0 + dr
        while 0 <= nf < 8 and 0 <= nr < 8:
            p = board[nr * 8 + nf]
            if p != '.':
                if p in rookq:
                    return True
                break
            nf += df
            nr += dr
    bishopq = ('B', 'Q') if by == 'w' else ('b', 'q')
    for df, dr in BISHOP_DIRS:
        nf, nr = f0 + df, r0 + dr
        while 0 <= nf < 8 and 0 <= nr < 8:
            p = board[nr * 8 + nf]
            if p != '.':
                if p in bishopq:
                    return True
                break
            nf += df
            nr += dr
    return False


def king_sq(st, color):
    k = 'K' if color == 'w' else 'k'
    return st.board.index(k)


def gen_pseudo(st):
    moves = []
    board = st.board
    us = st.side
    them = 'b' if us == 'w' else 'w'
    own = str.isupper if us == 'w' else str.islower
    enemy = str.islower if us == 'w' else str.isupper

    def add(f, t, promo=None, flags=None):
        moves.append((f, t, promo, flags))

    for s in range(64):
        p = board[s]
        if p == '.' or not own(p):
            continue
        f0, r0 = s % 8, s // 8
        pt = p.upper()

        if pt == 'P':
            dr = 1 if us == 'w' else -1
            promo_rank = 7 if us == 'w' else 0
            start_rank = 1 if us == 'w' else 6
            t = s + dr * 8
            if board[t] == '.':
                if t // 8 == promo_rank:
                    for pp in 'QRBN':
                        add(s, t, pp)
                else:
                    add(s, t)
                if r0 == start_rank:
                    t2 = s + dr * 16
                    if board[t2] == '.':
                        add(s, t2, None, 'dbl')
            for df in (-1, 1):
                nf = f0 + df
                if not (0 <= nf < 8):
                    continue
                t = s + dr * 8 + df
                tp = board[t]
                if tp != '.' and enemy(tp):
                    if t // 8 == promo_rank:
                        for pp in 'QRBN':
                            add(s, t, pp)
                    else:
                        add(s, t)
                elif t == st.ep:
                    add(s, t, None, 'ep')

        elif pt == 'N':
            for df, drr in KNIGHT_DELTAS:
                nf, nr = f0 + df, r0 + drr
                if 0 <= nf < 8 and 0 <= nr < 8:
                    tp = board[nr * 8 + nf]
                    if tp == '.' or enemy(tp):
                        add(s, nr * 8 + nf)

        elif pt == 'K':
            for df, drr in KING_DELTAS:
                nf, nr = f0 + df, r0 + drr
                if 0 <= nf < 8 and 0 <= nr < 8:
                    tp = board[nr * 8 + nf]
                    if tp == '.' or enemy(tp):
                        add(s, nr * 8 + nf)

        else:
            dirs = []
            if pt in 'RQ':
                dirs += ROOK_DIRS
            if pt in 'BQ':
                dirs += BISHOP_DIRS
            for df, drr in dirs:
                nf, nr = f0 + df, r0 + drr
                while 0 <= nf < 8 and 0 <= nr < 8:
                    t = nr * 8 + nf
                    tp = board[t]
                    if tp == '.':
                        add(s, t)
                    else:
                        if enemy(tp):
                            add(s, t)
                        break
                    nf += df
                    nr += drr

    back = 7 if us == 'w' else 0
    home = 0 if us == 'w' else 56
    ks_right = 'K' if us == 'w' else 'k'
    qs_right = 'Q' if us == 'w' else 'q'
    king_from = home + 4
    if board[king_from] == ('K' if us == 'w' else 'k'):
        if ks_right in st.castling \
           and board[home + 5] == '.' and board[home + 6] == '.' \
           and board[home + 7] == ('R' if us == 'w' else 'r') \
           and not attacked(st, king_from, them) \
           and not attacked(st, home + 5, them) \
           and not attacked(st, home + 6, them):
            add(king_from, home + 6, None, 'castle')
        if qs_right in st.castling \
           and board[home + 1] == '.' and board[home + 2] == '.' and board[home + 3] == '.' \
           and board[home] == ('R' if us == 'w' else 'r') \
           and not attacked(st, king_from, them) \
           and not attacked(st, home + 3, them) \
           and not attacked(st, home + 2, them):
            add(king_from, home + 2, None, 'castle')

    return moves


ROOK_HOME = {'K': 63, 'Q': 56, 'k': 7, 'q': 0}
RIGHT_AT = {60: 'KQ', 63: 'K', 56: 'Q', 4: 'KQ', 7: 'k', 0: 'q', 3: 'kq'}


def make(st, mv):
    f, t, promo, flag = mv
    ns = State()
    ns.board = st.board[:]
    ns.side = st.side
    ns.castling = st.castling
    ns.ep = -1
    ns.halfmove = st.halfmove
    ns.fullmove = st.fullmove

    board = ns.board
    piece = board[f]
    us = ns.side

    captured = board[t]
    if flag == 'ep':
        cap_sq = t - 8 if us == 'w' else t + 8
        captured = board[cap_sq]
        board[cap_sq] = '.'
    elif flag == 'castle':
        if t % 8 == 6:
            board[t - 1] = board[t + 1]
            board[t + 1] = '.'
        else:
            board[t + 1] = board[t - 2]
            board[t - 2] = '.'

    board[t] = promo if promo is not None and us == 'w' else (
        promo.lower() if promo is not None else piece)
    board[f] = '.'

    for sq, rights in ((f, RIGHT_AT.get(f)), (t, RIGHT_AT.get(t))):
        if rights:
            for ch in rights:
                ns.castling = ns.castling.replace(ch, '')

    if flag == 'dbl':
        ns.ep = (f + t) // 2
    if piece in 'Pp' or captured != '.':
        ns.halfmove = 0
    else:
        ns.halfmove += 1
    if us == 'b':
        ns.fullmove += 1
    ns.side = 'b' if us == 'w' else 'w'
    return ns


def to_fen(st):
    rows = []
    for r in range(7, -1, -1):
        row = ''
        empty = 0
        for f in range(8):
            p = st.board[r * 8 + f]
            if p == '.':
                empty += 1
            else:
                if empty:
                    row += str(empty)
                    empty = 0
                row += p
        if empty:
            row += str(empty)
        rows.append(row)
    ep = '-' if st.ep < 0 else sq_name(st.ep)
    return ' '.join(['/'.join(rows), st.side, st.castling or '-', ep,
                     str(st.halfmove), str(st.fullmove)])


def legal_moves(st):
    them = 'b' if st.side == 'w' else 'w'
    out = []
    for mv in gen_pseudo(st):
        ns = make(st, mv)
        if not attacked(ns, king_sq(ns, st.side), them):
            out.append(mv)
    return out


def perft(st, depth):
    if depth == 0:
        return 1
    total = 0
    for mv in legal_moves(st):
        total += 1 if depth == 1 else perft(make(st, mv), depth - 1)
    return total


if __name__ == '__main__':
    fen = sys.argv[1]
    depth = int(sys.argv[2])
    st = parse_fen(fen)
    total = 0
    results = []
    for mv in legal_moves(st):
        cnt = 1 if depth == 1 else perft(make(st, mv), depth - 1)
        results.append((sq_name(mv[0]) + sq_name(mv[1]), cnt))
        total += cnt
    for m, c in sorted(results):
        print(f"{m}: {c}")
    print(f"nodes {total}")
