#include "movegen.h"
#include "stats.h"
#include "notation.h"

#include <iostream>

namespace {

template <Color Us, bool CapturesOnly>
void generate_pawn_moves(const Position& pos, MoveList& ml) {
    constexpr Direction Push = Us == WHITE ? NORTH : SOUTH;
    constexpr Direction CapRight = Us == WHITE ? NORTH_EAST : SOUTH_EAST;
    constexpr Direction CapLeft = Us == WHITE ? NORTH_WEST : SOUTH_WEST;
    constexpr int PromoRank = Us == WHITE ? 7 : 0;
    constexpr Bitboard StartRank = Us == WHITE ? RANK_2_BB : RANK_7_BB;
    // Pawns that could promote by pushing.
    constexpr Bitboard PromoFrom = Us == WHITE ? RANK_7_BB : RANK_2_BB;

    const Color Them = ~Us;
    const Bitboard pawns = pos.pieces(Us, PAWN);
    const Bitboard emptySquares = ~pos.occupancy();
    const Bitboard enemies = pos.pieces(Them);

    // In captures-only mode only the pawns that can promote are pushed;
    // every other quiet push is skipped without being enumerated.
    Bitboard b = shift(Push, CapturesOnly ? (pawns & PromoFrom) : pawns)
               & emptySquares;
    while (b) {
        const Square to = pop_lsb(b);
        const Square from = to - Push;
        if (rank_of(to) == PromoRank) {
            ml.add(make_promotion(from, to, QUEEN));
            ml.add(make_promotion(from, to, ROOK));
            ml.add(make_promotion(from, to, BISHOP));
            ml.add(make_promotion(from, to, KNIGHT));
        } else if constexpr (!CapturesOnly) {
            ml.add(make_move(from, to));
        }
    }

    if constexpr (!CapturesOnly) {
        b = shift(Push, shift(Push, pawns & StartRank) & emptySquares) & emptySquares;
        while (b) {
            const Square to = pop_lsb(b);
            ml.add(make_double_push(to - Push - Push, to));
        }
    }

    for (Direction capDir : {CapLeft, CapRight}) {
        Bitboard targets = shift(capDir, pawns) & enemies;
        while (targets) {
            const Square to = pop_lsb(targets);
            const Square from = to - capDir;
            const PieceType captured = pos.piece_on(to);
            if (rank_of(to) == PromoRank) {
                ml.add(make_promotion(from, to, QUEEN, captured));
                ml.add(make_promotion(from, to, ROOK, captured));
                ml.add(make_promotion(from, to, BISHOP, captured));
                ml.add(make_promotion(from, to, KNIGHT, captured));
            } else {
                ml.add(make_move(from, to, captured));
            }
        }
    }

    if (pos.ep_square() != SQ_NONE) {
        const Square ep = pos.ep_square();
        Bitboard attackers = Bitboards::pawnAttacks[Them][ep] & pawns;
        while (attackers) ml.add(make_en_passant(pop_lsb(attackers), ep));
    }
}

template <Color Us, bool CapturesOnly>
void generate_piece_moves(const Position& pos, MoveList& ml) {
    const Bitboard own = pos.pieces(Us);
    const Bitboard occ = pos.occupancy();
    const Bitboard enemies = pos.pieces(~Us);

    auto emit = [&](Square from, Bitboard attacks) {
        attacks &= CapturesOnly ? enemies : ~own;
        while (attacks) {
            const Square to = pop_lsb(attacks);
            ml.add(make_move(from, to, pos.piece_on(to)));
        }
    };

    Bitboard b = pos.pieces(Us, KNIGHT);
    while (b) {
        const Square from = pop_lsb(b);
        emit(from, Bitboards::knightAttacks[from]);
    }

    b = pos.pieces(Us, BISHOP);
    while (b) {
        const Square from = pop_lsb(b);
        emit(from, Bitboards::bishop_attacks(from, occ));
    }

    b = pos.pieces(Us, ROOK);
    while (b) {
        const Square from = pop_lsb(b);
        emit(from, Bitboards::rook_attacks(from, occ));
    }

    b = pos.pieces(Us, QUEEN);
    while (b) {
        const Square from = pop_lsb(b);
        emit(from, Bitboards::queen_attacks(from, occ));
    }

    b = pos.pieces(Us, KING);
    while (b) {
        const Square from = pop_lsb(b);
        emit(from, Bitboards::kingAttacks[from]);
    }
}

template <Color Us>
void generate_castle_moves(const Position& pos, MoveList& ml) {
    constexpr Color Them = ~Us;
    constexpr CastlingRights KingSide = Us == WHITE ? WHITE_OO : BLACK_OO;
    constexpr CastlingRights QueenSide = Us == WHITE ? WHITE_OOO : BLACK_OOO;

    if ((pos.castling_rights() & (KingSide | QueenSide)) == NO_CASTLING) return;

    const Square kingFrom = Us == WHITE ? SQ_E1 : SQ_E8;
    const Bitboard occ = pos.occupancy();
    const CastlingRights cr = pos.castling_rights();

    if ((cr & KingSide)
        && !(occ & (square_bb(Square(kingFrom + 1)) | square_bb(Square(kingFrom + 2))))
        && !pos.attacked_by(Them, kingFrom)
        && !pos.attacked_by(Them, Square(kingFrom + 1))
        && !pos.attacked_by(Them, Square(kingFrom + 2)))
        ml.add(make_castle(kingFrom, Us == WHITE ? SQ_G1 : SQ_G8));

    if ((cr & QueenSide)
        && !(occ & (square_bb(Square(kingFrom - 1)) | square_bb(Square(kingFrom - 2)) | square_bb(Square(kingFrom - 3))))
        && !pos.attacked_by(Them, kingFrom)
        && !pos.attacked_by(Them, Square(kingFrom - 1))
        && !pos.attacked_by(Them, Square(kingFrom - 2)))
        ml.add(make_castle(kingFrom, Us == WHITE ? SQ_C1 : SQ_C8));
}

template <Color Us, bool CapturesOnly>
void generate_all(const Position& pos, MoveList& ml) {
    generate_pawn_moves<Us, CapturesOnly>(pos, ml);
    generate_piece_moves<Us, CapturesOnly>(pos, ml);
    // Castling is never a capture.
    if constexpr (!CapturesOnly) generate_castle_moves<Us>(pos, ml);
}

bool leaves_king_in_check(const Position& next) {
    return next.attacked_by(next.side_to_move(), next.king_square(~next.side_to_move()));
}

}

void generate_moves(const Position& pos, MoveList& ml) {
    STAT_INC(generateMoves);
    if (pos.side_to_move() == WHITE) generate_all<WHITE, false>(pos, ml);
    else generate_all<BLACK, false>(pos, ml);
}

void generate_captures(const Position& pos, MoveList& ml) {
    STAT_INC(generateCaptures);
    if (pos.side_to_move() == WHITE) generate_all<WHITE, true>(pos, ml);
    else generate_all<BLACK, true>(pos, ml);
}

bool is_legal(const Position& pos, const Move& m) {
    Position next = pos;
    next.do_move(m);
    return !leaves_king_in_check(next);
}

uint64_t perft(const Position& pos, int depth) {
    if (depth <= 0) return 1;

    MoveList ml;
    generate_moves(pos, ml);

    uint64_t nodes = 0;
    for (int i = 0; i < ml.count; ++i) {
        Position next = pos;
        next.do_move(ml.moves[i]);
        if (leaves_king_in_check(next)) continue;
        nodes += depth == 1 ? 1 : perft(next, depth - 1);
    }
    return nodes;
}

uint64_t perft_divide(const Position& pos, int depth) {
    MoveList ml;
    generate_moves(pos, ml);

    uint64_t total = 0;
    for (int i = 0; i < ml.count; ++i) {
        Position next = pos;
        next.do_move(ml.moves[i]);
        if (leaves_king_in_check(next)) continue;
        const uint64_t count = depth <= 1 ? 1 : perft(next, depth - 1);
        std::cout << move_to_uci(ml.moves[i]) << ": " << count << "\n";
        total += count;
    }
    return total;
}
