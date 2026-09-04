#include "notation.h"

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
