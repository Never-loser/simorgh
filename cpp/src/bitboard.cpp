#include "bitboard.h"

namespace Bitboards {

Bitboard knightAttacks[SQUARE_NB];
Bitboard kingAttacks[SQUARE_NB];
Bitboard pawnAttacks[COLOR_NB][SQUARE_NB];
Bitboard rays[RD_NB][SQUARE_NB];
bool rayPositive[RD_NB];

namespace {

constexpr int KNIGHT_DELTAS[8][2] = {{1,2},{2,1},{2,-1},{1,-2},{-1,-2},{-2,-1},{-2,1},{-1,2}};
constexpr int KING_DELTAS[8][2] = {{0,1},{1,1},{1,0},{1,-1},{0,-1},{-1,-1},{-1,0},{-1,1}};
constexpr int RAY_DELTAS[RD_NB][2] = {{0,1},{1,0},{0,-1},{-1,0},{1,1},{-1,1},{1,-1},{-1,-1}};

constexpr Direction DIR_OF_RAY[RD_NB] = {NORTH, EAST, SOUTH, WEST, NORTH_EAST, NORTH_WEST, SOUTH_EAST, SOUTH_WEST};

}

void init() {
    for (int s = 0; s < SQUARE_NB; ++s) {
        const int f = s & 7;
        const int r = s >> 3;

        Bitboard n = 0, k = 0;
        for (const auto& d : KNIGHT_DELTAS) {
            const int nf = f + d[0], nr = r + d[1];
            if (nf >= 0 && nf < 8 && nr >= 0 && nr < 8) n |= square_bb(make_square(nf, nr));
        }
        for (const auto& d : KING_DELTAS) {
            const int nf = f + d[0], nr = r + d[1];
            if (nf >= 0 && nf < 8 && nr >= 0 && nr < 8) k |= square_bb(make_square(nf, nr));
        }
        knightAttacks[s] = n;
        kingAttacks[s] = k;

        pawnAttacks[WHITE][s] = 0;
        pawnAttacks[BLACK][s] = 0;
        if (f > 0 && r < 7) pawnAttacks[WHITE][s] |= square_bb(make_square(f - 1, r + 1));
        if (f < 7 && r < 7) pawnAttacks[WHITE][s] |= square_bb(make_square(f + 1, r + 1));
        if (f > 0 && r > 0) pawnAttacks[BLACK][s] |= square_bb(make_square(f - 1, r - 1));
        if (f < 7 && r > 0) pawnAttacks[BLACK][s] |= square_bb(make_square(f + 1, r - 1));

        for (int dir = 0; dir < RD_NB; ++dir) {
            Bitboard rayB = 0;
            int cf = f + RAY_DELTAS[dir][0];
            int cr = r + RAY_DELTAS[dir][1];
            while (cf >= 0 && cf < 8 && cr >= 0 && cr < 8) {
                rayB |= square_bb(make_square(cf, cr));
                cf += RAY_DELTAS[dir][0];
                cr += RAY_DELTAS[dir][1];
            }
            rays[dir][s] = rayB;
        }
    }

    for (int dir = 0; dir < RD_NB; ++dir)
        rayPositive[dir] = DIR_OF_RAY[dir] > 0;
}

Bitboard slide_ray(int dir, Square s, Bitboard occupied) {
    Bitboard attacks = rays[dir][s];
    const Bitboard blockers = attacks & occupied;
    if (blockers) {
        const int blockerSq = rayPositive[dir] ? lsb(blockers) : msb(blockers);
        attacks ^= rays[dir][blockerSq];
    }
    return attacks;
}

Bitboard rook_attacks(Square s, Bitboard occupied) {
    return slide_ray(RD_N, s, occupied) | slide_ray(RD_E, s, occupied)
         | slide_ray(RD_S, s, occupied) | slide_ray(RD_W, s, occupied);
}

Bitboard bishop_attacks(Square s, Bitboard occupied) {
    return slide_ray(RD_NE, s, occupied) | slide_ray(RD_NW, s, occupied)
         | slide_ray(RD_SE, s, occupied) | slide_ray(RD_SW, s, occupied);
}

Bitboard queen_attacks(Square s, Bitboard occupied) {
    return rook_attacks(s, occupied) | bishop_attacks(s, occupied);
}

}
