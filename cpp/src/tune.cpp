#include "tune.h"
#include "evaluate.h"
#include "position.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>

namespace {

struct Sample {
    Position pos;
    double result;  // 1.0 white win, 0.5 draw, 0.0 black win
};

std::vector<Sample> samples;

// White-relative static evaluation. evaluate() returns the score from the
// side to move's point of view, so flip it for Black.
int white_eval(const Position& pos) {
    const int e = evaluate(pos);
    return pos.side_to_move() == WHITE ? e : -e;
}

double sigmoid(double score, double k) {
    return 1.0 / (1.0 + std::pow(10.0, -k * score / 400.0));
}

double mean_error(double k) {
    double total = 0.0;
    for (const Sample& s : samples) {
        const double diff = s.result - sigmoid(white_eval(s.pos), k);
        total += diff * diff;
    }
    return samples.empty() ? 0.0 : total / double(samples.size());
}

// Fit the scaling constant that maps centipawns onto win probability.
double fit_k() {
    double best = 1.0, bestErr = mean_error(1.0);
    for (double k = 0.2; k <= 3.0; k += 0.1) {
        const double err = mean_error(k);
        if (err < bestErr) { bestErr = err; best = k; }
    }
    // Refine around the coarse winner.
    for (double k = best - 0.1; k <= best + 0.1; k += 0.01) {
        if (k <= 0) continue;
        const double err = mean_error(k);
        if (err < bestErr) { bestErr = err; best = k; }
    }
    return best;
}

// Index of the same square mirrored about the vertical axis, or -1 for
// material parameters which have no mirror.
int mirror_of(int index) {
    if (index < 5) return -1;
    const int rest = index - 5;
    const int table = rest / 64;
    const int square = rest % 64;
    const int rank = square / 8;
    const int file = square % 8;
    return 5 + table * 64 + rank * 8 + (7 - file);
}

// Parameters that must not move.
bool frozen(int index, Tune::Scope scope) {
    const bool isMaterial = index < 5;

    // Tune only the left half of each table; the right half follows.
    if (Tune::MIRROR_PST && !isMaterial) {
        const int square = (index - 5) % 64;
        if (square % 8 >= 4) return true;
    }

    if (scope == Tune::Scope::Material && !isMaterial) return true;
    if (scope == Tune::Scope::Pst && isMaterial) return true;

    // Pawn value anchors the whole centipawn scale; if it drifts, every
    // other weight drifts with it and the numbers stop meaning anything.
    if (index == 0) return true;

    // Pawn PST ranks 1 and 8: a pawn can never stand there, so these
    // entries are unreachable and tuning them is wasted work.
    const int rest = index - 5;
    if (rest >= 0 && rest < 64) {
        const int square = rest % 64;
        if (square < 8 || square >= 56) return true;
    }
    return false;
}

bool load_samples(const std::string& path, std::string& error) {
    std::ifstream in(path);
    if (!in) { error = "cannot open " + path; return false; }

    samples.clear();
    std::string line;
    size_t bad = 0;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        const size_t sep = line.rfind(';');
        if (sep == std::string::npos) { ++bad; continue; }

        const std::string fen = line.substr(0, sep);
        const std::string tail = line.substr(sep + 1);

        double result;
        if (tail == "1-0") result = 1.0;
        else if (tail == "0-1") result = 0.0;
        else if (tail == "1/2-1/2" || tail == "0.5") result = 0.5;
        else {
            try { result = std::stod(tail); }
            catch (...) { ++bad; continue; }
        }

        Sample s;
        s.pos.set(fen);
        s.result = result;
        samples.push_back(std::move(s));
    }

    if (samples.empty()) {
        error = "no usable positions in " + path;
        return false;
    }
    if (bad) std::cout << "info string skipped " << bad << " malformed lines\n";
    return true;
}

}

namespace Tune {

Scope parse_scope(const std::string& text, bool& ok) {
    ok = true;
    if (text.empty() || text == "all") return Scope::All;
    if (text == "material") return Scope::Material;
    if (text == "pst") return Scope::Pst;
    ok = false;
    return Scope::All;
}

const char* scope_name(Scope scope) {
    switch (scope) {
        case Scope::Material: return "material";
        case Scope::Pst:      return "pst";
        default:              return "all";
    }
}

Result run(const std::string& dataPath, const std::string& outPath,
           int maxPasses, Scope scope) {
    Result r;
    if (!load_samples(dataPath, r.message)) return r;

    r.positions = samples.size();
    init_eval();

    r.k = fit_k();
    r.startError = mean_error(r.k);
    double best = r.startError;

    const int count = Eval::param_count();
    for (int i = 0; i < count; ++i)
        if (!frozen(i, scope)) ++r.tunable;

    std::cout << "info string tuning " << r.tunable << " of " << count
              << " parameters (scope " << scope_name(scope) << ") over "
              << r.positions << " positions" << std::endl;

    // Coordinate descent, coarse steps first. Each parameter is nudged and
    // kept only if the whole-dataset error actually falls, so a pass can
    // never leave the weights worse than it found them.
    for (int step : {16, 8, 4, 2, 1}) {
        bool improvedThisStep = true;
        int passes = 0;
        while (improvedThisStep && passes < maxPasses) {
            improvedThisStep = false;
            ++passes;

            for (int i = 0; i < count; ++i) {
                if (frozen(i, scope)) continue;

                const int twin = Tune::MIRROR_PST ? mirror_of(i) : -1;
                const bool paired = twin >= 0 && twin != i;

                int& p = Eval::param(i);
                const int original = p;
                const int originalTwin = paired ? Eval::param(twin) : 0;

                const auto set = [&](int value) {
                    p = value;
                    if (paired) Eval::param(twin) = value;
                    init_eval();
                };

                set(original + step);
                double err = mean_error(r.k);
                if (err < best) {
                    best = err;
                    ++r.changed;
                    improvedThisStep = true;
                    continue;
                }

                set(original - step);
                err = mean_error(r.k);
                if (err < best) {
                    best = err;
                    ++r.changed;
                    improvedThisStep = true;
                    continue;
                }

                // Neither direction helped: put both squares back.
                p = original;
                if (paired) Eval::param(twin) = originalTwin;
                init_eval();
            }
            std::cout << "info string tune step " << step << " pass " << passes
                      << " error " << best << std::endl;
        }
    }

    r.endError = best;
    init_eval();

    if (!Eval::save_weights(outPath)) {
        r.message = "could not write " + outPath;
        return r;
    }

    r.ok = true;
    return r;
}

}
