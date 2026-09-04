#pragma once

#include "types.h"
#include <string>

std::string square_to_uci(Square s);
std::string move_to_uci(const Move& m);
Square uci_square(const std::string& s);
char piece_type_to_char(PieceType pt, Color c);
PieceType char_to_piece_type(char c);
