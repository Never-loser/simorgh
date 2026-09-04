#pragma once

#include <string>

// --------------------------------------------------------------------------
// Texel-style evaluation tuning.
//
// Reads "FEN;result" lines (result 1.0 = White won, 0.5 = draw, 0.0 = Black
// won), then adjusts the evaluation weights so the static evaluation
// predicts those results as closely as possible.
//
// This only produces a *candidate* weight set. Whether it is actually an
// improvement is decided by python/gate.py, which plays the candidate
// against the current weights and refuses to promote it unless it scores
// better. Tuning error going down does not by itself mean the engine plays
// better, so nothing here is trusted on its own.
// --------------------------------------------------------------------------
namespace Tune {

struct Result {
    bool ok = false;
    size_t positions = 0;
    double k = 0.0;
    double startError = 0.0;
    double endError = 0.0;
    int changed = 0;
    int tunable = 0;
    std::string message;
};

// Which weights the tuner is allowed to move.
//
// "all" is 453 parameters. That needs far more games than a first training
// run produces: positions from one game share its result, so a few hundred
// games carry only a few hundred independent labels and the piece-square
// tables end up memorising rather than generalising. "material" fits only
// the four free piece values, which a small dataset can actually support.
enum class Scope { All, Material, Pst };

// Piece-square tables are tied to their left-right mirror while tuning, so
// a4 and h4 always move together. Halves the free parameters and enforces
// a symmetry the game actually has.
constexpr bool MIRROR_PST = true;

Scope parse_scope(const std::string& text, bool& ok);
const char* scope_name(Scope scope);

Result run(const std::string& dataPath, const std::string& outPath,
           int maxPasses, Scope scope = Scope::All);

}
