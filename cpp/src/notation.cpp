#include "notation.h"

#include "movegen.h"
#include "position.h"

#include <cctype>

std::string square_to_uci(Square s) {
    return std::string{char('a' + file_of(s)), char('1' + rank_of(s))};
}

Square uci_square(const std::string& s) {
    return make_square(s[0] - 'a', s[1] - '1');
}

std::string move_to_uci(const Move& m) {
    std::string str = square_to_uci(Square(m.from)) + square_to_uci(Square(m.to));
    if (m.promo != NO_PIECE_TYPE) {
        static const char promoChars[PIECE_TYPE_NB] = {' ', 'n', 'b', 'r', 'q', ' '};
        str += promoChars[m.promo];
    }
    return str;
}

char piece_type_to_char(PieceType pt, Color c) {
    static const char whiteChars[PIECE_TYPE_NB] = {'P', 'N', 'B', 'R', 'Q', 'K'};
    static const char blackChars[PIECE_TYPE_NB] = {'p', 'n', 'b', 'r', 'q', 'k'};
    return c == WHITE ? whiteChars[pt] : blackChars[pt];
}

PieceType char_to_piece_type(char c) {
    switch (std::tolower(uint8_t(c))) {
        case 'p': return PAWN;
        case 'n': return KNIGHT;
        case 'b': return BISHOP;
        case 'r': return ROOK;
        case 'q': return QUEEN;
        case 'k': return KING;
        default: return NO_PIECE_TYPE;
    }
}

std::string move_to_san(const Position& pos, const Move& m) {
    const Square from = Square(m.from), to = Square(m.to);
    const PieceType pt = pos.piece_on(from);
    std::string san;

    MoveList ml;
    generate_moves(pos, ml);

    if (m.isCastle) {
        san = file_of(to) > file_of(from) ? "O-O" : "O-O-O";
    } else {
        const bool capture = m.isEnPassant || pos.piece_on(to) != NO_PIECE_TYPE;
        if (pt == PAWN) {
            if (capture) san += char('a' + file_of(from));
        } else {
            san += "NBRQK"[pt - KNIGHT];
            // Name the file, else the rank, else both -- only as much as
            // it takes to tell this piece from another of its kind that
            // could also go to `to`.
            bool clash = false, sameFile = false, sameRank = false;
            for (int i = 0; i < ml.count; ++i) {
                const Move& o = ml.moves[i];
                if (o.to != m.to || o.from == m.from) continue;
                if (pos.piece_on(Square(o.from)) != pt || !is_legal(pos, o)) continue;
                clash = true;
                if (file_of(Square(o.from)) == file_of(from)) sameFile = true;
                if (rank_of(Square(o.from)) == rank_of(from)) sameRank = true;
            }
            if (clash) {
                if (!sameFile) san += char('a' + file_of(from));
                else if (!sameRank) san += char('1' + rank_of(from));
                else san += square_to_uci(from);
            }
        }
        if (capture) san += 'x';
        san += square_to_uci(to);
        if (m.promo != NO_PIECE_TYPE) {
            san += '=';
            san += "NBRQ"[m.promo - KNIGHT];
        }
    }

    Position after = pos;
    after.do_move(m);
    if (after.checkers_exist()) {
        MoveList replies;
        generate_moves(after, replies);
        bool escape = false;
        for (int i = 0; i < replies.count && !escape; ++i)
            escape = is_legal(after, replies.moves[i]);
        san += escape ? '+' : '#';
    }
    return san;
}
