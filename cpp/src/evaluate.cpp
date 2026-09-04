#include "evaluate.h"
#include "stats.h"

#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

// ---------------------------------------------------------------- defaults
// The hand-written starting point. reset_weights() restores these, and the
// tuner always starts from whatever is currently loaded.
constexpr int DEF_MATERIAL[5] = {100, 320, 330, 500, 900};

constexpr int DEF_PAWN[64] = {
      0,  0,  0,  0,  0,  0,  0,  0,
     50, 50, 50, 50, 50, 50, 50, 50,
     10, 10, 20, 30, 30, 20, 10, 10,
      5,  5, 10, 25, 25, 10,  5,  5,
      0,  0,  0, 20, 20,  0,  0,  0,
      5, -5,-10,  0,  0,-10, -5,  5,
      5, 10, 10,-20,-20, 10, 10,  5,
      0,  0,  0,  0,  0,  0,  0,  0
};

constexpr int DEF_KNIGHT[64] = {
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
};

constexpr int DEF_BISHOP[64] = {
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
};

constexpr int DEF_ROOK[64] = {
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0
};

constexpr int DEF_QUEEN[64] = {
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
};

constexpr int DEF_KING_MG[64] = {
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
};

constexpr int DEF_KING_EG[64] = {
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
};

// Game phase, on the usual 0..24 scale: 24 is a full opening board, 0 is
// a bare-kings endgame. Used to blend the king tables rather than snapping
// between them.
constexpr int PHASE_KNIGHT = 1;
constexpr int PHASE_BISHOP = 1;
constexpr int PHASE_ROOK = 2;
constexpr int PHASE_QUEEN = 4;
constexpr int PHASE_MAX = 2 * (2 * PHASE_KNIGHT + 2 * PHASE_BISHOP
                               + 2 * PHASE_ROOK + PHASE_QUEEN);

// ---- pawn structure ------------------------------------------------------
// Passed pawn bonus by the rank it stands on, from its own point of view
// (index 0 and 7 are unreachable). Tapered: in the endgame a runner is
// often the whole game, in the middlegame it is one factor among many.
constexpr int PASSED_MG[8] = {0, 5, 10, 20, 35, 60, 100, 0};
constexpr int PASSED_EG[8] = {0, 10, 20, 40, 70, 110, 170, 0};

// Two bishops cover both square colours, which is worth more than the sum
// of the pieces. Long-standing chess knowledge that the piece-square
// tables cannot express, because they score each piece independently.
constexpr int BISHOP_PAIR_MG = 30;
constexpr int BISHOP_PAIR_EG = 50;

constexpr int DOUBLED_PENALTY = 12;
constexpr int ISOLATED_PENALTY = 14;

// Files adjacent to each file, and everything ahead of a square on its own
// and neighbouring files -- the region that must be empty of enemy pawns
// for a pawn to be passed.
Bitboard adjacentFiles[8];
Bitboard passedMask[COLOR_NB][SQUARE_NB];
Bitboard fileMask[8];

struct PawnMaskInit {
    PawnMaskInit() {
        constexpr Bitboard files[8] = {FILE_A_BB, FILE_B_BB, FILE_C_BB,
                                       FILE_D_BB, FILE_E_BB, FILE_F_BB,
                                       FILE_G_BB, FILE_H_BB};
        for (int f = 0; f < 8; ++f) {
            fileMask[f] = files[f];
            adjacentFiles[f] = 0;
            if (f > 0) adjacentFiles[f] |= files[f - 1];
            if (f < 7) adjacentFiles[f] |= files[f + 1];
        }
        for (int s = 0; s < SQUARE_NB; ++s) {
            const int f = s & 7;
            const int r = s >> 3;
            const Bitboard span = fileMask[f] | adjacentFiles[f];
            Bitboard ahead = 0, behind = 0;
            for (int rr = r + 1; rr < 8; ++rr) ahead |= RANK_1_BB << (8 * rr);
            for (int rr = r - 1; rr >= 0; --rr) behind |= RANK_1_BB << (8 * rr);
            passedMask[WHITE][s] = span & ahead;
            passedMask[BLACK][s] = span & behind;
        }
    }
} pawnMaskInit;

// Returns the middlegame and endgame pawn-structure scores from White's
// point of view.
void pawn_structure(const Position& pos, int& mg, int& eg) {
    mg = eg = 0;
    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;
        const Bitboard ours = pos.pieces(c, PAWN);
        const Bitboard theirs = pos.pieces(~c, PAWN);

        Bitboard b = ours;
        while (b) {
            const Square s = pop_lsb(b);
            const int f = int(s) & 7;
            // Rank counted from this colour's own side of the board.
            const int rank = c == WHITE ? (int(s) >> 3) : 7 - (int(s) >> 3);

            if (!(passedMask[c][s] & theirs)) {
                mg += sign * PASSED_MG[rank];
                eg += sign * PASSED_EG[rank];
            }
            if (!(adjacentFiles[f] & ours)) {
                mg -= sign * ISOLATED_PENALTY;
                eg -= sign * ISOLATED_PENALTY;
            }
        }

        for (int f = 0; f < 8; ++f) {
            const int count = popcount(ours & fileMask[f]);
            if (count > 1) {
                mg -= sign * DOUBLED_PENALTY * (count - 1);
                eg -= sign * DOUBLED_PENALTY * (count - 1);
            }
        }
    }
}

// ------------------------------------------------------------ live weights
int MATERIAL_W[5];
int PST_W[7][64];  // pawn, knight, bishop, rook, queen, king_mg, king_eg

enum { PST_PAWN_I, PST_KNIGHT_I, PST_BISHOP_I, PST_ROOK_I, PST_QUEEN_I,
       PST_KING_MG_I, PST_KING_EG_I, PST_COUNT };

const char* GROUP_NAMES[PST_COUNT] = {
    "pst_pawn", "pst_knight", "pst_bishop", "pst_rook", "pst_queen",
    "pst_king_mg", "pst_king_eg"
};

const int* DEFAULT_PST[PST_COUNT] = {
    DEF_PAWN, DEF_KNIGHT, DEF_BISHOP, DEF_ROOK, DEF_QUEEN,
    DEF_KING_MG, DEF_KING_EG
};

// Derived table, rebuilt by init_eval() from the live weights above.
int piecePst[COLOR_NB][PIECE_TYPE_NB][SQUARE_NB];

bool weightsInitialised = false;

void ensure_defaults() {
    if (weightsInitialised) return;
    Eval::reset_weights();
}

// Flat parameter layout: 5 material values, then 7 * 64 PST entries.
constexpr int MATERIAL_PARAMS = 5;
constexpr int TOTAL_PARAMS = MATERIAL_PARAMS + PST_COUNT * 64;

int mirrored_index(Color c, Square s) {
    const int f = int(s) & 7;
    const int r = int(s) >> 3;
    return c == WHITE ? (7 - r) * 8 + f : r * 8 + f;
}

}

namespace Eval {

void reset_weights() {
    std::memcpy(MATERIAL_W, DEF_MATERIAL, sizeof(MATERIAL_W));
    for (int t = 0; t < PST_COUNT; ++t)
        std::memcpy(PST_W[t], DEFAULT_PST[t], sizeof(PST_W[t]));
    weightsInitialised = true;
}

int param_count() { return TOTAL_PARAMS; }

int& param(int index) {
    ensure_defaults();
    if (index < MATERIAL_PARAMS) return MATERIAL_W[index];
    const int rest = index - MATERIAL_PARAMS;
    return PST_W[rest / 64][rest % 64];
}

const char* param_group(int index) {
    if (index < MATERIAL_PARAMS) return "material";
    return GROUP_NAMES[(index - MATERIAL_PARAMS) / 64];
}

bool save_weights(const std::string& path) {
    ensure_defaults();
    std::ofstream out(path);
    if (!out) return false;
    out << "# simorgh evaluation weights v1\n";
    out << "material";
    for (int i = 0; i < MATERIAL_PARAMS; ++i) out << ' ' << MATERIAL_W[i];
    out << '\n';
    for (int t = 0; t < PST_COUNT; ++t) {
        out << GROUP_NAMES[t];
        for (int s = 0; s < 64; ++s) out << ' ' << PST_W[t][s];
        out << '\n';
    }
    return bool(out);
}

bool load_weights(const std::string& path) {
    std::ifstream in(path);
    if (!in) return false;

    // Load into a scratch copy so a malformed file cannot leave the engine
    // running on half-applied weights.
    int material[MATERIAL_PARAMS];
    int pst[PST_COUNT][64];
    std::memcpy(material, DEF_MATERIAL, sizeof(material));
    for (int t = 0; t < PST_COUNT; ++t)
        std::memcpy(pst[t], DEFAULT_PST[t], sizeof(pst[t]));

    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream iss(line);
        std::string name;
        iss >> name;

        if (name == "material") {
            for (int i = 0; i < MATERIAL_PARAMS; ++i)
                if (!(iss >> material[i])) return false;
            continue;
        }
        int table = -1;
        for (int t = 0; t < PST_COUNT; ++t)
            if (name == GROUP_NAMES[t]) table = t;
        if (table < 0) continue;  // unknown key: ignore, keep the default
        for (int s = 0; s < 64; ++s)
            if (!(iss >> pst[table][s])) return false;
    }

    std::memcpy(MATERIAL_W, material, sizeof(MATERIAL_W));
    for (int t = 0; t < PST_COUNT; ++t)
        std::memcpy(PST_W[t], pst[t], sizeof(PST_W[t]));
    weightsInitialised = true;
    init_eval();
    return true;
}

}

void init_eval() {
    ensure_defaults();
    for (int c = 0; c < COLOR_NB; ++c)
        for (int pt = 0; pt < PIECE_TYPE_NB; ++pt)
            for (int s = 0; s < SQUARE_NB; ++s)
                piecePst[c][pt][s] =
                    pt == KING ? 0
                               : PST_W[pt][mirrored_index(Color(c), Square(s))];
}

int evaluate(const Position& pos) {
    STAT_INC(evaluateCalls);
    int score = 0;
    int phase = 0;

    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;

        for (int pt = PAWN; pt <= QUEEN; ++pt) {
            Bitboard b = pos.pieces(Color(c), PieceType(pt));
            const int count = popcount(b);
            score += sign * MATERIAL_W[pt] * count;
            while (b) score += sign * piecePst[c][pt][pop_lsb(b)];

            switch (pt) {
                case KNIGHT: phase += PHASE_KNIGHT * count; break;
                case BISHOP: phase += PHASE_BISHOP * count; break;
                case ROOK:   phase += PHASE_ROOK * count;   break;
                case QUEEN:  phase += PHASE_QUEEN * count;  break;
                default: break;
            }
        }
    }

    // Promotions can push the phase above a normal starting board.
    if (phase > PHASE_MAX) phase = PHASE_MAX;

    // Blend the two king tables by phase instead of switching at a
    // threshold, so trading a piece cannot move the king's score by 60
    // centipawns on its own. Pawn structure is tapered the same way.
    int mgScore = 0, egScore = 0;
    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;
        const int visual = mirrored_index(c, pos.king_square(c));
        mgScore += sign * PST_W[PST_KING_MG_I][visual];
        egScore += sign * PST_W[PST_KING_EG_I][visual];
    }

    int pawnMg = 0, pawnEg = 0;
    pawn_structure(pos, pawnMg, pawnEg);
    mgScore += pawnMg;
    egScore += pawnEg;

    for (Color c : {WHITE, BLACK}) {
        if (popcount(pos.pieces(c, BISHOP)) >= 2) {
            const int sign = c == WHITE ? 1 : -1;
            mgScore += sign * BISHOP_PAIR_MG;
            egScore += sign * BISHOP_PAIR_EG;
        }
    }

    score += (mgScore * phase + egScore * (PHASE_MAX - phase)) / PHASE_MAX;

    return pos.side_to_move() == WHITE ? score : -score;
}
