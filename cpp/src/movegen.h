#pragma once

#include "position.h"

struct MoveList {
    static constexpr int MAX = 256;

    Move moves[MAX];
    int count = 0;

    void add(const Move& m) { moves[count++] = m; }
};

void generate_moves(const Position& pos, MoveList& ml);

// Captures, en passant and promotions only -- what quiescence searches.
// Matches is_capture_like() in search.cpp; anything it would skip is never
// generated here in the first place.
void generate_captures(const Position& pos, MoveList& ml);
bool is_legal(const Position& pos, const Move& m);
uint64_t perft(const Position& pos, int depth);
uint64_t perft_divide(const Position& pos, int depth);
