#pragma once

#include "types.h"
#include <string>

class Position;

std::string square_to_uci(Square s);
std::string move_to_uci(const Move& m);
Square uci_square(const std::string& s);
char piece_type_to_char(PieceType pt, Color c);
PieceType char_to_piece_type(char c);

// Standard algebraic notation ("Nf3", "exd5", "O-O", "e8=Q+") for a legal
// move in `pos`. For display only; the protocol itself stays in UCI.
std::string move_to_san(const Position& pos, const Move& m);
