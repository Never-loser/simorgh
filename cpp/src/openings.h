#pragma once

#include <cstdint>
#include <string>

class Position;

// --------------------------------------------------------------------------
// Opening names.
//
// The table (data/openings.tsv) lists named lines as moves from the start.
// Loading replays each one and remembers the position it ends in, so a name
// is found by position, not by move order: a game that transposes into the
// Queen's Gambit Declined is named as one, however it got there.
// --------------------------------------------------------------------------
namespace Openings {

struct Name {
    std::string eco;    // "B90"
    std::string name;   // "Sicilian Defense: Najdorf Variation"
    std::string fa;     // Persian name of the family: "دفاع سیسیلی"
};

// Returns the number of lines loaded; 0 if the file is missing. Lines whose
// moves do not replay are skipped and counted in `rejected`.
size_t load(const std::string& path, size_t& rejected);
size_t count();

// What names are looked up by: the pieces, the side to move and the
// castling rights. Not the en-passant square -- the engine's own hash
// includes it after every double push, so 1.d4 Nf6 2.c4 e6 3.Nf3 and
// 1.Nf3 Nf6 2.c4 e6 3.d4 would otherwise be different positions.
uint64_t key_of(const Position& pos);

// The name of exactly this position (by key_of), or nullptr.
const Name* find(uint64_t key);

}
