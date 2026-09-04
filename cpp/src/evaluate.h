#pragma once

#include "position.h"

#include <string>

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
