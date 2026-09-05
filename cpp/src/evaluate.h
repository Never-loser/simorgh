#pragma once

#include "position.h"

#include <string>
#include <vector>

void init_eval();
int evaluate(const Position& pos);

// Static exchange / move-ordering values. These are *not* tuned: move
// ordering only needs a sane relative scale, and letting the tuner move
// them would change search behaviour rather than evaluation quality.
inline constexpr int PIECE_VALUE[PIECE_TYPE_NB] = {100, 320, 330, 500, 900, 20000};

// --------------------------------------------------------------------------
// Tunable evaluation weights.
//
// These used to be `constexpr`, which meant nothing could ever learn them.
// They are now ordinary globals exposed as a flat parameter vector so the
// Texel tuner can walk them, plus load/save so a tuned set survives a
// restart. Call init_eval() after changing any of them.
// --------------------------------------------------------------------------
namespace Eval {

int param_count();
int& param(int index);              // flat access for the tuner
const char* param_group(int index); // for readable dumps

bool load_weights(const std::string& path);
bool save_weights(const std::string& path);
void reset_weights();               // back to the hand-written defaults

}

// --------------------------------------------------------------------------
// Explainable evaluation.
//
// evaluate() returns a single number. That number is the sum of a fixed set
// of named terms, and this exposes them individually so the engine can say
// *why* it likes a position rather than only by how much.
//
// This is only possible because the evaluation is hand-written. A neural
// evaluation produces one number from weights with no human meaning, so it
// can be accurate but never explain itself. That trade is the whole point
// of keeping this evaluation readable.
//
// The decomposition is exact: the terms below sum to exactly what
// evaluate() returns, including the truncation in the tapering step, which
// is reported as its own `rounding` term rather than hidden.
// --------------------------------------------------------------------------
namespace Eval {

// One named contribution, always from White's point of view: positive
// favours White, whoever is to move.
struct Term {
    std::string name;
    std::string detail;  // squares or files involved, when useful
    int mg = 0;          // before tapering; meaningless unless `tapered`
    int eg = 0;
    int value = 0;       // what this term actually added to the total
    bool tapered = false;
};

struct Breakdown {
    std::vector<Term> terms;
    int phase = 0;       // phaseMax = pure middlegame, 0 = pure endgame
    int phaseMax = 0;
    int white = 0;       // total from White's point of view
    int sideToMove = 0;  // exactly what evaluate() returns
};

Breakdown explain(const Position& pos);

}
