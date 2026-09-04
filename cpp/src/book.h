#pragma once

#include "position.h"

#include <cstdint>
#include <string>
#include <vector>

// --------------------------------------------------------------------------
// A learned opening book.
//
// Nothing is pre-seeded: the book starts empty and every finished game adds
// to it. For each position it stores, per move, how that move worked out
// *for the side that played it* (wins / draws / losses). Later games prefer
// moves with a good record and stop trusting moves that keep losing.
//
// The safety property that matters: the book can only pick a move it has
// enough evidence for, and if every known move in a position scores badly
// it declines and lets the search decide. So playing more games can add
// knowledge but cannot make the engine play a line it has learned is bad.
// --------------------------------------------------------------------------
namespace Book {

// Pack a move the same way the book stores it.
uint16_t pack_move(const Move& m);

struct Entry {
    uint16_t move = 0;   // packed as in search.cpp: from | to<<6 | promo<<12
    uint32_t wins = 0;   // from the perspective of the side to move
    uint32_t draws = 0;
    uint32_t losses = 0;

    uint32_t games() const { return wins + draws + losses; }
    double score() const {   // 1.0 = always won, 0.0 = always lost
        const uint32_t n = games();
        return n ? (wins + 0.5 * draws) / n : 0.5;
    }
};

// One ply of a finished game: the position before the move, and the move.
struct Ply {
    uint64_t key;
    uint16_t move;
    Color mover;
};

bool load(const std::string& path);
bool save(const std::string& path);
void clear();

// Number of distinct positions currently known.
size_t position_count();
size_t total_games();

// Best book move for `pos`, or false if the book declines to choose.
// `legal` must be the legal moves of `pos`; the returned move is always one
// of them.
bool probe(const Position& pos, const std::vector<Move>& legal, Move& out,
           int randomness);

// All known moves for a position, best first (for the `book` command).
std::vector<Entry> entries_for(uint64_t key);

// Fold a finished game into the book. `result` is +1 white win, 0 draw,
// -1 black win.
void learn(const std::vector<Ply>& plies, int result);

// Only positions at or before this ply are stored/played. Openings are
// where a small book helps; storing whole games would bloat it with
// positions that never repeat.
void set_max_ply(int plies);
int max_ply();

// A move needs at least this many games before the book will play it.
void set_min_games(int games);
int min_games();

}
