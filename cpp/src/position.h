#pragma once

#include "types.h"
#include "bitboard.h"

inline constexpr const char* START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

// Everything a move destroys that cannot be recovered from the move
// itself. The Move already carries the captured piece, so this is the rest.
struct StateInfo {
    uint64_t hash = 0;
    CastlingRights castling = NO_CASTLING;
    Square epSquare = SQ_NONE;
    int halfmoveClock = 0;
    int fullmoveNumber = 1;
};

class Position {
public:
    Position();

    void set(const std::string& fenStr);
    std::string fen() const;
    void do_move(const Move& m);
    void do_null_move();

    // Make/unmake. The search uses these instead of copying the position
    // at every node.
    void do_move(const Move& m, StateInfo& st);
    void undo_move(const Move& m, const StateInfo& st);
    void do_null_move(StateInfo& st);
    void undo_null_move(const StateInfo& st);

    Bitboard pieces(PieceType pt) const { return pieceBB[WHITE][pt] | pieceBB[BLACK][pt]; }
    Bitboard pieces(Color c) const { return colorOcc[c]; }
    Bitboard pieces(Color c, PieceType pt) const { return pieceBB[c][pt]; }
    Bitboard occupancy() const { return occupied; }

    PieceType piece_on(Square s) const { return PieceType(board[s]); }
    Color side_to_move() const { return sideToMove; }
    Square ep_square() const { return epSquare; }
    CastlingRights castling_rights() const { return castling; }
    int halfmove_clock() const { return halfmoveClock; }
    int fullmove_number() const { return fullmoveNumber; }
    uint64_t key() const { return hash; }

    Square king_square(Color c) const { return Square(lsb(pieceBB[c][KING])); }

    bool attacked_by(Color c, Square s) const;

    // Every piece of either colour attacking `s`, given an occupancy that
    // the caller may have already stripped pieces out of. SEE needs this
    // to walk a capture sequence.
    Bitboard attackers_to(Square s, Bitboard occ) const;
    bool checkers_exist() const { return attacked_by(~sideToMove, king_square(sideToMove)); }
    bool has_non_pawn_material(Color c) const {
        return (colorOcc[c] ^ pieceBB[c][PAWN] ^ pieceBB[c][KING]) != 0;
    }

private:
    void add_piece(Color c, PieceType pt, Square s);
    void remove_piece(Color c, PieceType pt, Square s);
    void relocate_piece(Color c, PieceType pt, Square from, Square to);

    Bitboard pieceBB[COLOR_NB][PIECE_TYPE_NB] = {};
    Bitboard colorOcc[COLOR_NB] = {};
    Bitboard occupied = 0;
    uint8_t board[SQUARE_NB] = {};
    Color sideToMove = WHITE;
    CastlingRights castling = NO_CASTLING;
    Square epSquare = SQ_NONE;
    int halfmoveClock = 0;
    int fullmoveNumber = 1;
    uint64_t hash = 0;
};
