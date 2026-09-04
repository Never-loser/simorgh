#include "position.h"
#include "stats.h"
#include "notation.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <iterator>
#include <sstream>
#include <random>

namespace {

uint64_t zPiece[COLOR_NB][PIECE_TYPE_NB][SQUARE_NB];
uint64_t zSide = 0;
uint64_t zCastling[16] = {};
uint64_t zEpFile[8] = {};
bool zInit = false;

void zobrist_init() {
    if (zInit) return;
    std::mt19937_64 rng(0x87C37B91114253D5ULL);
    for (int c = 0; c < COLOR_NB; ++c)
        for (int p = 0; p < PIECE_TYPE_NB; ++p)
            for (int s = 0; s < SQUARE_NB; ++s)
                zPiece[c][p][s] = rng();
    zSide = rng();
    for (int i = 0; i < 16; ++i) zCastling[i] = rng();
    for (int i = 0; i < 8; ++i) zEpFile[i] = rng();
    zInit = true;
}

const std::array<CastlingRights, SQUARE_NB> castleMask = [] {
    std::array<CastlingRights, SQUARE_NB> m{};
    m.fill(ANY_CASTLING);
    m[SQ_A1] = CastlingRights(ANY_CASTLING & ~WHITE_OOO);
    m[SQ_H1] = CastlingRights(ANY_CASTLING & ~WHITE_OO);
    m[SQ_E1] = CastlingRights(ANY_CASTLING & ~(WHITE_OO | WHITE_OOO));
    m[SQ_A8] = CastlingRights(ANY_CASTLING & ~BLACK_OOO);
    m[SQ_H8] = CastlingRights(ANY_CASTLING & ~BLACK_OO);
    m[SQ_E8] = CastlingRights(ANY_CASTLING & ~(BLACK_OO | BLACK_OOO));
    return m;
}();

}

Position::Position() {
    std::fill(std::begin(board), std::end(board), uint8_t(NO_PIECE_TYPE));
}

void Position::add_piece(Color c, PieceType pt, Square s) {
    const Bitboard b = square_bb(s);
    pieceBB[c][pt] |= b;
    colorOcc[c] |= b;
    occupied |= b;
    board[s] = uint8_t(pt);
}

void Position::remove_piece(Color c, PieceType pt, Square s) {
    const Bitboard b = square_bb(s);
    pieceBB[c][pt] ^= b;
    colorOcc[c] ^= b;
    occupied ^= b;
    board[s] = uint8_t(NO_PIECE_TYPE);
}

void Position::relocate_piece(Color c, PieceType pt, Square from, Square to) {
    const Bitboard fromTo = square_bb(from) ^ square_bb(to);
    pieceBB[c][pt] ^= fromTo;
    colorOcc[c] ^= fromTo;
    occupied ^= fromTo;
    board[to] = uint8_t(pt);
    board[from] = uint8_t(NO_PIECE_TYPE);
}

void Position::set(const std::string& fenStr) {
    zobrist_init();
    *this = Position();

    std::istringstream ss(fenStr);
    std::string placement, sideToken, castleToken, epToken;
    ss >> placement >> sideToken >> castleToken >> epToken;
    ss >> halfmoveClock >> fullmoveNumber;

    int f = 0, r = 7;
    for (char c : placement) {
        if (c == '/') { --r; f = 0; }
        else if (c >= '1' && c <= '8') f += c - '0';
        else {
            const Color col = std::isupper(uint8_t(c)) ? WHITE : BLACK;
            add_piece(col, char_to_piece_type(c), make_square(f, r));
            ++f;
        }
    }

    sideToMove = sideToken == "b" ? BLACK : WHITE;

    for (char c : castleToken) {
        if (c == 'K') castling |= WHITE_OO;
        else if (c == 'Q') castling |= WHITE_OOO;
        else if (c == 'k') castling |= BLACK_OO;
        else if (c == 'q') castling |= BLACK_OOO;
    }

    if (epToken.size() >= 2) epSquare = uci_square(epToken);

    hash = 0;
    for (int c = 0; c < COLOR_NB; ++c)
        for (int p = 0; p < PIECE_TYPE_NB; ++p) {
            Bitboard b = pieceBB[c][p];
            while (b) hash ^= zPiece[c][p][pop_lsb(b)];
        }
    if (sideToMove == BLACK) hash ^= zSide;
    if (castling != NO_CASTLING) hash ^= zCastling[castling];
    if (epSquare != SQ_NONE) hash ^= zEpFile[file_of(epSquare)];
}

std::string Position::fen() const {
    std::string out;
    for (int r = 7; r >= 0; --r) {
        int empties = 0;
        for (int f = 0; f < 8; ++f) {
            const Square s = make_square(f, r);
            const PieceType pt = piece_on(s);
            if (pt == NO_PIECE_TYPE) { ++empties; continue; }
            if (empties) { out += char('0' + empties); empties = 0; }
            const Color c = (colorOcc[WHITE] & square_bb(s)) ? WHITE : BLACK;
            out += piece_type_to_char(pt, c);
        }
        if (empties) out += char('0' + empties);
        if (r > 0) out += '/';
    }
    out += sideToMove == WHITE ? " w " : " b ";
    if (castling == NO_CASTLING) out += '-';
    else {
        if (castling & WHITE_OO) out += 'K';
        if (castling & WHITE_OOO) out += 'Q';
        if (castling & BLACK_OO) out += 'k';
        if (castling & BLACK_OOO) out += 'q';
    }
    out += ' ';
    out += epSquare == SQ_NONE ? "-" : square_to_uci(epSquare);
    out += ' ' + std::to_string(halfmoveClock) + ' ' + std::to_string(fullmoveNumber);
    return out;
}

Bitboard Position::attackers_to(Square s, Bitboard occ) const {
    return (Bitboards::pawnAttacks[BLACK][s] & pieceBB[WHITE][PAWN])
         | (Bitboards::pawnAttacks[WHITE][s] & pieceBB[BLACK][PAWN])
         | (Bitboards::knightAttacks[s]
            & (pieceBB[WHITE][KNIGHT] | pieceBB[BLACK][KNIGHT]))
         | (Bitboards::kingAttacks[s]
            & (pieceBB[WHITE][KING] | pieceBB[BLACK][KING]))
         | (Bitboards::rook_attacks(s, occ)
            & (pieceBB[WHITE][ROOK] | pieceBB[BLACK][ROOK]
               | pieceBB[WHITE][QUEEN] | pieceBB[BLACK][QUEEN]))
         | (Bitboards::bishop_attacks(s, occ)
            & (pieceBB[WHITE][BISHOP] | pieceBB[BLACK][BISHOP]
               | pieceBB[WHITE][QUEEN] | pieceBB[BLACK][QUEEN]));
}

bool Position::attacked_by(Color c, Square s) const {
    STAT_INC(attackedBy);
    if (Bitboards::pawnAttacks[~c][s] & pieceBB[c][PAWN]) return true;
    if (Bitboards::knightAttacks[s] & pieceBB[c][KNIGHT]) return true;
    if (Bitboards::kingAttacks[s] & pieceBB[c][KING]) return true;
    if (Bitboards::rook_attacks(s, occupied) & (pieceBB[c][ROOK] | pieceBB[c][QUEEN])) return true;
    if (Bitboards::bishop_attacks(s, occupied) & (pieceBB[c][BISHOP] | pieceBB[c][QUEEN])) return true;
    return false;
}

void Position::do_move(const Move& m, StateInfo& st) {
    st.hash = hash;
    st.castling = castling;
    st.epSquare = epSquare;
    st.halfmoveClock = halfmoveClock;
    st.fullmoveNumber = fullmoveNumber;
    do_move(m);
}

void Position::undo_move(const Move& m, const StateInfo& st) {
    STAT_INC(undoMove);
    // sideToMove currently belongs to the opponent; `us` made the move.
    const Color us = ~sideToMove;
    const Color them = sideToMove;
    const Square from = Square(m.from);
    const Square to = Square(m.to);

    if (m.promo != NO_PIECE_TYPE) {
        remove_piece(us, PieceType(m.promo), to);
        add_piece(us, PAWN, from);
    } else {
        relocate_piece(us, PieceType(board[to]), to, from);
    }

    if (m.isCastle) {
        Square rookFrom, rookTo;
        switch (to) {
            case SQ_G1: rookFrom = SQ_H1; rookTo = SQ_F1; break;
            case SQ_C1: rookFrom = SQ_A1; rookTo = SQ_D1; break;
            case SQ_G8: rookFrom = SQ_H8; rookTo = SQ_F8; break;
            default:    rookFrom = SQ_A8; rookTo = SQ_D8; break;
        }
        relocate_piece(us, ROOK, rookTo, rookFrom);
    }

    if (m.isEnPassant) {
        add_piece(them, PAWN, to + (us == WHITE ? SOUTH : NORTH));
    } else if (m.capturedPlus1 != 0) {
        add_piece(them, PieceType(m.capturedPlus1 - 1), to);
    }

    sideToMove = us;
    hash = st.hash;
    castling = st.castling;
    epSquare = st.epSquare;
    halfmoveClock = st.halfmoveClock;
    fullmoveNumber = st.fullmoveNumber;
}

void Position::do_null_move(StateInfo& st) {
    st.hash = hash;
    st.castling = castling;
    st.epSquare = epSquare;
    st.halfmoveClock = halfmoveClock;
    st.fullmoveNumber = fullmoveNumber;
    do_null_move();
}

void Position::undo_null_move(const StateInfo& st) {
    sideToMove = ~sideToMove;
    hash = st.hash;
    castling = st.castling;
    epSquare = st.epSquare;
    halfmoveClock = st.halfmoveClock;
    fullmoveNumber = st.fullmoveNumber;
}

void Position::do_null_move() {
    if (epSquare != SQ_NONE) hash ^= zEpFile[file_of(epSquare)];
    epSquare = SQ_NONE;
    hash ^= zSide;
    sideToMove = ~sideToMove;
    ++halfmoveClock;
}

void Position::do_move(const Move& m) {
    STAT_INC(doMove);
    const Color us = sideToMove;
    const Color them = ~us;
    const Square from = Square(m.from);
    const Square to = Square(m.to);
    const PieceType pt = PieceType(board[from]);

    hash ^= zPiece[us][pt][from] ^ zSide;

    if (castling != NO_CASTLING) hash ^= zCastling[castling];
    if (epSquare != SQ_NONE) hash ^= zEpFile[file_of(epSquare)];

    const bool isCapture = m.capturedPlus1 != 0;
    halfmoveClock = (pt == PAWN || isCapture || m.isEnPassant) ? 0 : halfmoveClock + 1;
    if (us == BLACK) ++fullmoveNumber;

    if (m.isEnPassant) {
        const Square capsq = to + (us == WHITE ? SOUTH : NORTH);
        remove_piece(them, PAWN, capsq);
        hash ^= zPiece[them][PAWN][capsq];
    } else if (isCapture) {
        const PieceType captured = PieceType(m.capturedPlus1 - 1);
        remove_piece(them, captured, to);
        hash ^= zPiece[them][captured][to];
    }

    Square newEp = SQ_NONE;
    if (m.isDoublePush) newEp = from + (us == WHITE ? NORTH : SOUTH);

    if (m.promo != NO_PIECE_TYPE) {
        remove_piece(us, PAWN, from);
        add_piece(us, PieceType(m.promo), to);
        hash ^= zPiece[us][PieceType(m.promo)][to];
    } else {
        relocate_piece(us, pt, from, to);
        hash ^= zPiece[us][pt][to];
    }

    if (m.isCastle) {
        Square rookFrom, rookTo;
        switch (to) {
            case SQ_G1: rookFrom = SQ_H1; rookTo = SQ_F1; break;
            case SQ_C1: rookFrom = SQ_A1; rookTo = SQ_D1; break;
            case SQ_G8: rookFrom = SQ_H8; rookTo = SQ_F8; break;
            default:    rookFrom = SQ_A8; rookTo = SQ_D8; break;
        }
        relocate_piece(us, ROOK, rookFrom, rookTo);
        hash ^= zPiece[us][ROOK][rookFrom] ^ zPiece[us][ROOK][rookTo];
    }

    castling &= castleMask[from];
    castling &= castleMask[to];

    if (castling != NO_CASTLING) hash ^= zCastling[castling];
    if (newEp != SQ_NONE) hash ^= zEpFile[file_of(newEp)];

    epSquare = newEp;
    sideToMove = them;
}
