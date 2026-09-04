#pragma once

#include "types.h"

using Bitboard = uint64_t;

constexpr Bitboard FILE_A_BB = 0x0101010101010101ULL;
constexpr Bitboard FILE_B_BB = 0x0202020202020202ULL;
constexpr Bitboard FILE_C_BB = 0x0404040404040404ULL;
constexpr Bitboard FILE_D_BB = 0x0808080808080808ULL;
constexpr Bitboard FILE_E_BB = 0x1010101010101010ULL;
constexpr Bitboard FILE_F_BB = 0x2020202020202020ULL;
constexpr Bitboard FILE_G_BB = 0x4040404040404040ULL;
constexpr Bitboard FILE_H_BB = 0x8080808080808080ULL;

constexpr Bitboard RANK_1_BB = 0x00000000000000FFULL;
constexpr Bitboard RANK_2_BB = 0x000000000000FF00ULL;
constexpr Bitboard RANK_3_BB = 0x0000000000FF0000ULL;
constexpr Bitboard RANK_4_BB = 0x00000000FF000000ULL;
constexpr Bitboard RANK_5_BB = 0x000000FF00000000ULL;
constexpr Bitboard RANK_6_BB = 0x0000FF0000000000ULL;
constexpr Bitboard RANK_7_BB = 0x00FF000000000000ULL;
constexpr Bitboard RANK_8_BB = 0xFF00000000000000ULL;

constexpr Bitboard square_bb(Square s) { return 1ULL << s; }

#if defined(_MSC_VER)
#include <intrin.h>
inline int lsb(Bitboard b) { unsigned long i; _BitScanForward64(&i, b); return int(i); }
inline int msb(Bitboard b) { unsigned long i; _BitScanReverse64(&i, b); return int(i); }
#else
inline int lsb(Bitboard b) { return __builtin_ctzll(b); }
inline int msb(Bitboard b) { return 63 ^ __builtin_clzll(b); }
#endif

inline int popcount(Bitboard b) {
#if defined(_MSC_VER)
    return int(__popcnt64(b));
#else
    return __builtin_popcountll(b);
#endif
}

inline Square pop_lsb(Bitboard& b) { const Square s = Square(lsb(b)); b &= b - 1; return s; }

inline Bitboard shift(Direction d, Bitboard b) {
    switch (d) {
        case NORTH:      return b << 8;
        case SOUTH:      return b >> 8;
        case EAST:       return (b & ~FILE_H_BB) << 1;
        case WEST:       return (b & ~FILE_A_BB) >> 1;
        case NORTH_EAST: return (b & ~FILE_H_BB) << 9;
        case NORTH_WEST: return (b & ~FILE_A_BB) << 7;
        case SOUTH_EAST: return (b & ~FILE_H_BB) >> 7;
        case SOUTH_WEST: return (b & ~FILE_A_BB) >> 9;
    }
    return 0;
}

namespace Bitboards {
    enum RayDir { RD_N, RD_E, RD_S, RD_W, RD_NE, RD_NW, RD_SE, RD_SW, RD_NB };

    extern Bitboard knightAttacks[SQUARE_NB];
    extern Bitboard kingAttacks[SQUARE_NB];
    extern Bitboard pawnAttacks[COLOR_NB][SQUARE_NB];
    extern Bitboard rays[RD_NB][SQUARE_NB];
    extern bool rayPositive[RD_NB];

    void init();

    Bitboard slide_ray(int dir, Square s, Bitboard occupied);
    Bitboard rook_attacks(Square s, Bitboard occupied);
    Bitboard bishop_attacks(Square s, Bitboard occupied);
    Bitboard queen_attacks(Square s, Bitboard occupied);
}
