#pragma once

#include <cstdint>
#include <string>

enum Color : int { WHITE, BLACK, COLOR_NB = 2 };

constexpr Color operator~(Color c) { return Color(int(c) ^ 1); }

enum PieceType : int {
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_TYPE_NB = 6,
    NO_PIECE_TYPE = 7
};

enum Square : int {
    SQ_A1, SQ_B1, SQ_C1, SQ_D1, SQ_E1, SQ_F1, SQ_G1, SQ_H1,
    SQ_A2, SQ_B2, SQ_C2, SQ_D2, SQ_E2, SQ_F2, SQ_G2, SQ_H2,
    SQ_A3, SQ_B3, SQ_C3, SQ_D3, SQ_E3, SQ_F3, SQ_G3, SQ_H3,
    SQ_A4, SQ_B4, SQ_C4, SQ_D4, SQ_E4, SQ_F4, SQ_G4, SQ_H4,
    SQ_A5, SQ_B5, SQ_C5, SQ_D5, SQ_E5, SQ_F5, SQ_G5, SQ_H5,
    SQ_A6, SQ_B6, SQ_C6, SQ_D6, SQ_E6, SQ_F6, SQ_G6, SQ_H6,
    SQ_A7, SQ_B7, SQ_C7, SQ_D7, SQ_E7, SQ_F7, SQ_G7, SQ_H7,
    SQ_A8, SQ_B8, SQ_C8, SQ_D8, SQ_E8, SQ_F8, SQ_G8, SQ_H8,
    SQ_NONE = 64,
    SQUARE_NB = 64
};

constexpr int file_of(Square s) { return s & 7; }
constexpr int rank_of(Square s) { return s >> 3; }
constexpr Square make_square(int f, int r) { return Square(r * 8 + f); }
constexpr Square operator+(Square s, int d) { return Square(int(s) + d); }
constexpr Square operator-(Square s, int d) { return Square(int(s) - d); }

enum Direction : int {
    NORTH = 8, SOUTH = -8, EAST = 1, WEST = -1,
    NORTH_EAST = 9, NORTH_WEST = 7,
    SOUTH_EAST = -7, SOUTH_WEST = -9
};

enum CastlingRights : int {
    NO_CASTLING = 0,
    WHITE_OO = 1,
    WHITE_OOO = 2,
    BLACK_OO = 4,
    BLACK_OOO = 8,
    ANY_CASTLING = 15
};

constexpr CastlingRights operator&(CastlingRights a, CastlingRights b) { return CastlingRights(int(a) & int(b)); }
constexpr CastlingRights operator|(CastlingRights a, CastlingRights b) { return CastlingRights(int(a) | int(b)); }
constexpr CastlingRights& operator&=(CastlingRights& a, CastlingRights b) { a = a & b; return a; }
constexpr CastlingRights& operator|=(CastlingRights& a, CastlingRights b) { a = a | b; return a; }

struct Move {
    uint8_t from = 0;
    uint8_t to = 0;
    uint8_t promo = NO_PIECE_TYPE;
    uint8_t capturedPlus1 = 0;
    bool isEnPassant = false;
    bool isCastle = false;
    bool isDoublePush = false;
};

constexpr bool operator==(const Move& a, const Move& b) {
    return a.from == b.from && a.to == b.to && a.promo == b.promo;
}

constexpr Move make_move(Square from, Square to, PieceType captured = NO_PIECE_TYPE) {
    Move m;
    m.from = uint8_t(from);
    m.to = uint8_t(to);
    m.promo = NO_PIECE_TYPE;
    m.capturedPlus1 = captured == NO_PIECE_TYPE ? uint8_t(0) : uint8_t(captured + 1);
    return m;
}

constexpr Move make_promotion(Square from, Square to, PieceType promo, PieceType captured = NO_PIECE_TYPE) {
    Move m = make_move(from, to, captured);
    m.promo = uint8_t(promo);
    return m;
}

constexpr Move make_en_passant(Square from, Square to) {
    Move m = make_move(from, to);
    m.isEnPassant = true;
    return m;
}

constexpr Move make_castle(Square from, Square to) {
    Move m = make_move(from, to);
    m.isCastle = true;
    return m;
}

constexpr Move make_double_push(Square from, Square to) {
    Move m = make_move(from, to);
    m.isDoublePush = true;
    return m;
}
