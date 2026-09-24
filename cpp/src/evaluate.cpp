#include "evaluate.h"
#include "notation.h"
#include "stats.h"

#include <algorithm>
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

// ---- mobility ------------------------------------------------------------
// How many squares a piece can actually use. The piece-square tables know
// that a bishop is usually well placed on c4; they cannot see that this
// bishop on c4 is hemmed in by its own pawns. Mobility can.
//
// Counted per knight, bishop, rook and queen: the squares it attacks that
// hold no piece of its own and are not covered by an enemy pawn (a square
// a pawn guards is not somewhere a piece can really go). Scored per square
// relative to what such a piece typically has, so an ordinary piece adds
// nothing, an active one gains and a buried one loses. The per-square
// weights are tuned; the typical counts are not.
constexpr int DEF_MOB_MG[4] = {4, 5, 2, 1};  // knight, bishop, rook, queen
constexpr int DEF_MOB_EG[4] = {4, 5, 4, 2};
constexpr int MOB_TYPICAL[4] = {4, 7, 7, 14};

// ---- king safety ---------------------------------------------------------
// Two things, both middlegame only: in an endgame the king is a fighting
// piece and hiding it is a mistake.
//
// The pawn shield: the king's own pawns on its file and the two beside it.
// A pawn one square ahead of the king is worth most, two squares ahead
// less. A file there with no pawn of the king's own side is a hole, and
// worse still when the enemy has no pawn on it either: that is an open
// file for enemy rooks, pointed at the king.
constexpr int DEF_SHIELD[4] = {12, 6, 10, 15};  // near, far, semi-open, open

// The attack: every enemy knight, bishop, rook and queen that reaches the
// squares around the king adds weight for each of those squares. One
// attacker is rarely dangerous and several together are, so once there
// are at least two the penalty grows with the square of the total weight
// rather than in proportion to it -- the usual shape of a king hunt.
constexpr int DEF_ATTACK[5] = {2, 2, 3, 5, 30};  // knight, bishop, rook, queen; scale
constexpr int ATTACK_CAP = 600;

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

// Pawn structure, split into the three effects that make it up. Keeping
// them separate here rather than accumulating one number is what lets
// explain() name them; pawn_structure() below just sums them, so the two
// views can never disagree about what the evaluation actually did.
struct PawnTerms {
    int passedMg = 0, passedEg = 0;
    int isolatedMg = 0, isolatedEg = 0;
    int doubledMg = 0, doubledEg = 0;
    std::string passedOn, isolatedOn, doubledOn;
};

void append_square(std::string& list, Color c, Square s) {
    if (!list.empty()) list += ' ';
    list += (c == WHITE ? 'w' : 'b');
    list += square_to_uci(s);
}

// From White's point of view. `detail` fills in the square lists, which is
// wasted work during search and so is off by default.
void pawn_structure_detail(const Position& pos, PawnTerms& t, bool detail) {
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
                t.passedMg += sign * PASSED_MG[rank];
                t.passedEg += sign * PASSED_EG[rank];
                if (detail) append_square(t.passedOn, c, s);
            }
            if (!(adjacentFiles[f] & ours)) {
                t.isolatedMg -= sign * ISOLATED_PENALTY;
                t.isolatedEg -= sign * ISOLATED_PENALTY;
                if (detail) append_square(t.isolatedOn, c, s);
            }
        }

        for (int f = 0; f < 8; ++f) {
            const int count = popcount(ours & fileMask[f]);
            if (count > 1) {
                t.doubledMg -= sign * DOUBLED_PENALTY * (count - 1);
                t.doubledEg -= sign * DOUBLED_PENALTY * (count - 1);
                if (detail) {
                    if (!t.doubledOn.empty()) t.doubledOn += ' ';
                    t.doubledOn += (c == WHITE ? 'w' : 'b');
                    t.doubledOn += char('a' + f);
                    if (count > 2) t.doubledOn += 'x' + std::to_string(count);
                }
            }
        }
    }
}

// Returns the middlegame and endgame pawn-structure scores from White's
// point of view.
void pawn_structure(const Position& pos, int& mg, int& eg) {
    PawnTerms t;
    pawn_structure_detail(pos, t, false);
    mg = t.passedMg + t.isolatedMg + t.doubledMg;
    eg = t.passedEg + t.isolatedEg + t.doubledEg;
}

// ------------------------------------------------------------ live weights
int MATERIAL_W[5];
int PST_W[7][64];  // pawn, knight, bishop, rook, queen, king_mg, king_eg
int MOB_W[2][4];   // [mg, eg][knight, bishop, rook, queen], per square
int SHIELD_W[4];   // near, far, semi-open, open
int ATTACK_W[5];   // knight, bishop, rook, queen weights; then the scale

// Mobility per piece type, middlegame and endgame, from White's point of
// view. Shared by evaluate() and explain(), like the pawn terms, so the two
// cannot disagree.
//
// The same pass also collects the attack on each king, since it already
// has every piece's reach in hand: counting attackers costs one more AND
// per piece rather than a second walk over the board.
struct MobilityTerms {
    int mg[4] = {0, 0, 0, 0};
    int eg[4] = {0, 0, 0, 0};
    int attackWeight[COLOR_NB] = {0, 0};  // against that colour's king
    int attackers[COLOR_NB] = {0, 0};
};

// The squares around a king, and one more rank towards the enemy, which is
// where an attack on a castled king actually lands.
Bitboard king_zone(const Position& pos, Color c) {
    const Square k = pos.king_square(c);
    const Bitboard ring = Bitboards::kingAttacks[k] | square_bb(k);
    return ring | (c == WHITE ? shift(NORTH, ring) : shift(SOUTH, ring));
}

void mobility(const Position& pos, MobilityTerms& t) {
    const Bitboard occupied = pos.occupancy();
    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;
        const Bitboard theirZone = king_zone(pos, ~c);
        const Bitboard theirPawns = pos.pieces(~c, PAWN);
        const Bitboard pawnGuarded = c == WHITE
            ? shift(SOUTH_EAST, theirPawns) | shift(SOUTH_WEST, theirPawns)
            : shift(NORTH_EAST, theirPawns) | shift(NORTH_WEST, theirPawns);
        const Bitboard usable = ~pos.pieces(c) & ~pawnGuarded;

        for (int i = 0; i < 4; ++i) {
            const PieceType pt = PieceType(KNIGHT + i);
            Bitboard b = pos.pieces(c, pt);
            while (b) {
                const Square s = pop_lsb(b);
                const Bitboard reach =
                    pt == KNIGHT ? Bitboards::knightAttacks[s]
                  : pt == BISHOP ? Bitboards::bishop_attacks(s, occupied)
                  : pt == ROOK   ? Bitboards::rook_attacks(s, occupied)
                                 : Bitboards::queen_attacks(s, occupied);
                const int beyond = popcount(reach & usable) - MOB_TYPICAL[i];
                t.mg[i] += sign * MOB_W[0][i] * beyond;
                t.eg[i] += sign * MOB_W[1][i] * beyond;

                if (const Bitboard hits = reach & theirZone) {
                    t.attackWeight[~c] += ATTACK_W[i] * popcount(hits);
                    ++t.attackers[~c];
                }
            }
        }
    }
}

// Pawn shield and king attack, middlegame only, from White's point of view.
void king_safety(const Position& pos, const MobilityTerms& m,
                 int& shieldMg, int& attackMg) {
    shieldMg = attackMg = 0;
    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;
        const Square k = pos.king_square(c);
        const int kf = int(k) & 7;
        const int kr = int(k) >> 3;
        const int ahead = c == WHITE ? 1 : -1;
        const Bitboard ours = pos.pieces(c, PAWN);
        const Bitboard theirs = pos.pieces(~c, PAWN);

        int shield = 0;
        for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); ++f) {
            const Bitboard onFile = ours & fileMask[f];
            const int r1 = kr + ahead, r2 = kr + 2 * ahead;
            if (r1 >= 0 && r1 < 8 && (onFile & square_bb(Square(r1 * 8 + f))))
                shield += SHIELD_W[0];
            else if (r2 >= 0 && r2 < 8 && (onFile & square_bb(Square(r2 * 8 + f))))
                shield += SHIELD_W[1];
            if (!onFile) {
                shield -= SHIELD_W[2];
                if (!(theirs & fileMask[f])) shield -= SHIELD_W[3];
            }
        }
        shieldMg += sign * shield;

        if (m.attackers[c] >= 2) {
            const int w = m.attackWeight[c];
            attackMg -= sign * std::min(ATTACK_CAP, w * w * ATTACK_W[4] / 100);
        }
    }
}

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

// Flat parameter layout: 5 material values, then 7 * 64 PST entries, then
// the 4 middlegame and 4 endgame mobility weights.
constexpr int MATERIAL_PARAMS = 5;
constexpr int PST_PARAMS = PST_COUNT * 64;
constexpr int MOBILITY_PARAMS = 8;
constexpr int SHIELD_PARAMS = 4;
constexpr int ATTACK_PARAMS = 5;
constexpr int TOTAL_PARAMS = MATERIAL_PARAMS + PST_PARAMS + MOBILITY_PARAMS
                           + SHIELD_PARAMS + ATTACK_PARAMS;

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
    std::memcpy(MOB_W[0], DEF_MOB_MG, sizeof(MOB_W[0]));
    std::memcpy(MOB_W[1], DEF_MOB_EG, sizeof(MOB_W[1]));
    std::memcpy(SHIELD_W, DEF_SHIELD, sizeof(SHIELD_W));
    std::memcpy(ATTACK_W, DEF_ATTACK, sizeof(ATTACK_W));
    weightsInitialised = true;
}

int param_count() { return TOTAL_PARAMS; }

int& param(int index) {
    ensure_defaults();
    if (index < MATERIAL_PARAMS) return MATERIAL_W[index];
    const int rest = index - MATERIAL_PARAMS;
    if (rest < PST_PARAMS) return PST_W[rest / 64][rest % 64];
    const int mob = rest - PST_PARAMS;
    if (mob < MOBILITY_PARAMS) return MOB_W[mob / 4][mob % 4];
    const int king = mob - MOBILITY_PARAMS;
    if (king < SHIELD_PARAMS) return SHIELD_W[king];
    return ATTACK_W[king - SHIELD_PARAMS];
}

const char* param_group(int index) {
    if (index < MATERIAL_PARAMS) return "material";
    const int rest = index - MATERIAL_PARAMS;
    if (rest < PST_PARAMS) return GROUP_NAMES[rest / 64];
    const int mob = rest - PST_PARAMS;
    if (mob < MOBILITY_PARAMS) return mob < 4 ? "mobility_mg" : "mobility_eg";
    return mob - MOBILITY_PARAMS < SHIELD_PARAMS ? "king_shield" : "king_attack";
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
    out << "mobility_mg";
    for (int i = 0; i < 4; ++i) out << ' ' << MOB_W[0][i];
    out << "\nmobility_eg";
    for (int i = 0; i < 4; ++i) out << ' ' << MOB_W[1][i];
    out << "\nking_shield";
    for (int i = 0; i < SHIELD_PARAMS; ++i) out << ' ' << SHIELD_W[i];
    out << "\nking_attack";
    for (int i = 0; i < ATTACK_PARAMS; ++i) out << ' ' << ATTACK_W[i];
    out << '\n';
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
    // A weights file from before mobility existed has no such lines and
    // simply gets the defaults for them.
    int mob[2][4];
    std::memcpy(mob[0], DEF_MOB_MG, sizeof(mob[0]));
    std::memcpy(mob[1], DEF_MOB_EG, sizeof(mob[1]));
    int shieldW[SHIELD_PARAMS], attackW[ATTACK_PARAMS];
    std::memcpy(shieldW, DEF_SHIELD, sizeof(shieldW));
    std::memcpy(attackW, DEF_ATTACK, sizeof(attackW));

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
        if (name == "mobility_mg" || name == "mobility_eg") {
            int* row = mob[name == "mobility_mg" ? 0 : 1];
            for (int i = 0; i < 4; ++i)
                if (!(iss >> row[i])) return false;
            continue;
        }
        if (name == "king_shield") {
            for (int i = 0; i < SHIELD_PARAMS; ++i)
                if (!(iss >> shieldW[i])) return false;
            continue;
        }
        if (name == "king_attack") {
            for (int i = 0; i < ATTACK_PARAMS; ++i)
                if (!(iss >> attackW[i])) return false;
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
    std::memcpy(MOB_W, mob, sizeof(MOB_W));
    std::memcpy(SHIELD_W, shieldW, sizeof(SHIELD_W));
    std::memcpy(ATTACK_W, attackW, sizeof(ATTACK_W));
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

    MobilityTerms mob;
    mobility(pos, mob);
    for (int i = 0; i < 4; ++i) {
        mgScore += mob.mg[i];
        egScore += mob.eg[i];
    }

    int shieldMg, attackMg;
    king_safety(pos, mob, shieldMg, attackMg);
    mgScore += shieldMg + attackMg;

    score += (mgScore * phase + egScore * (PHASE_MAX - phase)) / PHASE_MAX;

    return pos.side_to_move() == WHITE ? score : -score;
}

namespace Eval {

// Mirrors evaluate() term by term. Any change to evaluate() that is not
// made here too will show up immediately as a nonzero mismatch in the
// `evalexplain` self-test, which is the point of keeping the two adjacent.
Breakdown explain(const Position& pos) {
    ensure_defaults();

    static const char* PIECE_NAME[5] = {
        "pawn", "knight", "bishop", "rook", "queen"
    };

    Breakdown bd;
    bd.phaseMax = PHASE_MAX;

    // ---------------------------------------------------------- untapered
    int phase = 0;
    int material[5] = {0, 0, 0, 0, 0};
    int placement[5] = {0, 0, 0, 0, 0};
    int count[COLOR_NB][5] = {{0}};

    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;
        for (int pt = PAWN; pt <= QUEEN; ++pt) {
            Bitboard b = pos.pieces(Color(c), PieceType(pt));
            const int n = popcount(b);
            count[c][pt] = n;
            material[pt] += sign * MATERIAL_W[pt] * n;
            while (b) placement[pt] += sign * piecePst[c][pt][pop_lsb(b)];

            switch (pt) {
                case KNIGHT: phase += PHASE_KNIGHT * n; break;
                case BISHOP: phase += PHASE_BISHOP * n; break;
                case ROOK:   phase += PHASE_ROOK * n;   break;
                case QUEEN:  phase += PHASE_QUEEN * n;  break;
                default: break;
            }
        }
    }
    if (phase > PHASE_MAX) phase = PHASE_MAX;
    bd.phase = phase;

    int untapered = 0;
    auto flat = [&](const std::string& name, int v, const std::string& detail) {
        untapered += v;
        if (v == 0 && detail.empty()) return;  // silent when it says nothing
        Term t;
        t.name = name;
        t.detail = detail;
        t.value = v;
        bd.terms.push_back(t);
    };

    for (int pt = PAWN; pt <= QUEEN; ++pt) {
        std::string counts;
        if (count[WHITE][pt] != count[BLACK][pt])
            counts = std::to_string(count[WHITE][pt]) + "v" +
                     std::to_string(count[BLACK][pt]);
        flat(std::string("material.") + PIECE_NAME[pt], material[pt], counts);
    }
    for (int pt = PAWN; pt <= QUEEN; ++pt)
        flat(std::string("placement.") + PIECE_NAME[pt], placement[pt], "");

    // ------------------------------------------------------------ tapered
    int kingMg = 0, kingEg = 0;
    for (Color c : {WHITE, BLACK}) {
        const int sign = c == WHITE ? 1 : -1;
        const int visual = mirrored_index(c, pos.king_square(c));
        kingMg += sign * PST_W[PST_KING_MG_I][visual];
        kingEg += sign * PST_W[PST_KING_EG_I][visual];
    }

    PawnTerms pawns;
    pawn_structure_detail(pos, pawns, true);

    int pairMg = 0, pairEg = 0;
    std::string pairOn;
    for (Color c : {WHITE, BLACK}) {
        if (popcount(pos.pieces(c, BISHOP)) >= 2) {
            const int sign = c == WHITE ? 1 : -1;
            pairMg += sign * BISHOP_PAIR_MG;
            pairEg += sign * BISHOP_PAIR_EG;
            if (!pairOn.empty()) pairOn += ' ';
            pairOn += (c == WHITE ? "white" : "black");
        }
    }

    auto taper = [&](int mg, int eg) {
        return (mg * phase + eg * (PHASE_MAX - phase)) / PHASE_MAX;
    };

    int mgTotal = 0, egTotal = 0, taperedParts = 0;
    auto blend = [&](const std::string& name, int mg, int eg,
                     const std::string& detail) {
        mgTotal += mg;
        egTotal += eg;
        const int v = taper(mg, eg);
        taperedParts += v;
        if (mg == 0 && eg == 0 && detail.empty()) return;
        Term t;
        t.name = name;
        t.detail = detail;
        t.mg = mg;
        t.eg = eg;
        t.value = v;
        t.tapered = true;
        bd.terms.push_back(t);
    };

    blend("king.placement", kingMg, kingEg, "");
    blend("pawns.passed", pawns.passedMg, pawns.passedEg, pawns.passedOn);
    blend("pawns.isolated", pawns.isolatedMg, pawns.isolatedEg,
          pawns.isolatedOn);
    blend("pawns.doubled", pawns.doubledMg, pawns.doubledEg, pawns.doubledOn);
    blend("bishop.pair", pairMg, pairEg, pairOn);

    static const char* MOBILITY_NAME[4] = {
        "mobility.knight", "mobility.bishop", "mobility.rook", "mobility.queen"
    };
    MobilityTerms mob;
    mobility(pos, mob);
    for (int i = 0; i < 4; ++i)
        blend(MOBILITY_NAME[i], mob.mg[i], mob.eg[i], "");

    int shieldMg, attackMg;
    king_safety(pos, mob, shieldMg, attackMg);
    blend("king.shield", shieldMg, 0, "");
    std::string attackOn;
    for (Color c : {WHITE, BLACK})
        if (mob.attackers[c] >= 2) {
            if (!attackOn.empty()) attackOn += ' ';
            attackOn += c == WHITE ? "white" : "black";
        }
    blend("king.attack", attackMg, 0, attackOn);

    // evaluate() tapers the *sum*, once. Tapering each term on its own and
    // adding them up truncates several times instead, so the two differ by
    // a few centipawns. Report that gap as its own term rather than
    // quietly fudging a term to make the column add up.
    const int taperedTotal = taper(mgTotal, egTotal);
    const int residue = taperedTotal - taperedParts;
    if (residue != 0) {
        Term t;
        t.name = "rounding";
        t.detail = "tapering truncation";
        t.value = residue;
        bd.terms.push_back(t);
    }

    bd.white = untapered + taperedTotal;
    bd.sideToMove = pos.side_to_move() == WHITE ? bd.white : -bd.white;
    return bd;
}

}
