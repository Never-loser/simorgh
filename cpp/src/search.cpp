#include "search.h"
#include "evaluate.h"
#include "movegen.h"
#include "notation.h"
#include "stats.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iostream>

namespace {

constexpr int INF = 32000;

// Delta pruning margin, in centipawns. A capture is only searched if the
// material it wins, plus this much slack for positional compensation,
// could still reach alpha.
constexpr int DELTA_MARGIN = 200;

// How far above beta the static evaluation has to be, per ply of remaining
// depth, before the node is assumed to be a cutoff.
constexpr int REVERSE_FUTILITY_MARGIN = 80;
constexpr int REVERSE_FUTILITY_MAX_DEPTH = 6;

// How far below alpha a position may be before its quiet moves near the
// leaves are considered hopeless. Indexed by remaining depth.
constexpr int FUTILITY_MARGIN[4] = {0, 120, 240, 380};
constexpr int FUTILITY_MAX_DEPTH = 3;

// Late move pruning: near the leaves, once this many quiet moves have been
// tried without raising alpha, the rest are not worth looking at.
constexpr int LMP_MAX_DEPTH = 4;
inline int lmp_limit(int depth) { return 3 + depth * depth; }

// Late move reductions, indexed by [remaining depth][move number]. Built
// from the usual log formula: reduce more the deeper the search and the
// later the move, but smoothly rather than in three steps.
constexpr int LMR_MAX_DEPTH = 64;
constexpr int LMR_MAX_MOVES = 64;
int LMR_TABLE[LMR_MAX_DEPTH][LMR_MAX_MOVES];

struct LmrTableInit {
    LmrTableInit() {
        for (int d = 0; d < LMR_MAX_DEPTH; ++d)
            for (int m = 0; m < LMR_MAX_MOVES; ++m)
                LMR_TABLE[d][m] =
                    d < 3 || m < 3
                        ? 0
                        : int(0.75 + std::log(double(d)) * std::log(double(m))
                                     / 2.25);
    }
} lmrTableInit;
constexpr int MATE = 31000;
constexpr int MATE_BOUND = MATE - 256;

enum { FLAG_NONE = 0, FLAG_EXACT, FLAG_LOWER, FLAG_UPPER };

int64_t now_ms() {
    // Milliseconds since the epoch needs 41 bits; truncating this to int
    // (as the previous version did) wraps every ~25 days and can make the
    // engine believe it is out of time the moment a search starts.
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

uint16_t pack_move(const Move& m) {
    const uint16_t promo = m.promo == NO_PIECE_TYPE ? uint16_t(0) : uint16_t(m.promo);
    return uint16_t(m.from | (m.to << 6) | (promo << 12));
}

Move unpack_move(uint16_t packed) {
    Move m;
    m.from = packed & 63;
    m.to = (packed >> 6) & 63;
    m.promo = (packed >> 12) & 7;
    if (m.promo == 0) m.promo = NO_PIECE_TYPE;
    return m;
}

// Static exchange evaluation: material won or lost if both sides keep
// capturing on the destination square, always with their least valuable
// attacker. Positive means the capture wins material.
int see(const Position& pos, const Move& m) {
    const Square to = Square(m.to);
    const Square from = Square(m.from);

    int gain[32];
    int depth = 0;

    const PieceType firstVictim =
        m.isEnPassant        ? PAWN
      : m.capturedPlus1 != 0 ? PieceType(m.capturedPlus1 - 1)
                             : NO_PIECE_TYPE;
    gain[0] = firstVictim == NO_PIECE_TYPE ? 0 : PIECE_VALUE[firstVictim];

    PieceType onSquare = pos.piece_on(from);
    if (onSquare == NO_PIECE_TYPE) return 0;
    // A promotion arrives on the square as the promoted piece.
    if (m.promo != NO_PIECE_TYPE) {
        gain[0] += PIECE_VALUE[m.promo] - PIECE_VALUE[PAWN];
        onSquare = PieceType(m.promo);
    }

    Bitboard occ = pos.occupancy() ^ square_bb(from);
    if (m.isEnPassant)
        occ ^= square_bb(Square(to + (pos.side_to_move() == WHITE ? SOUTH : NORTH)));

    Bitboard attackers = pos.attackers_to(to, occ) & occ;
    Color side = ~pos.side_to_move();

    while (true) {
        // Cheapest attacker of the side to move, if any.
        Bitboard mine = attackers & pos.pieces(side);
        if (!mine) break;

        PieceType attacker = NO_PIECE_TYPE;
        Bitboard piece = 0;
        for (int pt = PAWN; pt <= KING; ++pt) {
            const Bitboard candidates = mine & pos.pieces(side, PieceType(pt));
            if (candidates) {
                attacker = PieceType(pt);
                piece = candidates & (~candidates + 1);  // lowest set bit
                break;
            }
        }
        if (attacker == NO_PIECE_TYPE) break;

        ++depth;
        gain[depth] = PIECE_VALUE[onSquare] - gain[depth - 1];
        // Once the running score cannot be turned around, stop early.
        if (std::max(-gain[depth - 1], gain[depth]) < 0) break;

        onSquare = attacker;
        occ ^= piece;
        // Removing a piece can reveal a slider behind it.
        attackers = pos.attackers_to(to, occ) & occ;
        side = ~side;

        if (depth >= 31) break;
    }

    // Roll the speculative gains back up: at each step the side to move
    // would only continue the exchange if doing so beats standing pat.
    // This must run when depth == 1 too -- a single recapture is exactly
    // the case that turns a winning-looking capture into a losing one.
    while (depth > 0) {
        gain[depth - 1] = -std::max(-gain[depth - 1], gain[depth]);
        --depth;
    }
    return gain[0];
}

bool is_capture_like(const Move& m) {
    return m.capturedPlus1 != 0 || m.isEnPassant || m.promo != NO_PIECE_TYPE;
}

int capture_score(const Position& pos, const Move& m) {
    if (!is_capture_like(m)) return 0;
    const int victimValue = m.isEnPassant ? PIECE_VALUE[PAWN] : PIECE_VALUE[m.capturedPlus1 - 1];
    const PieceType attacker = pos.piece_on(Square(m.from));
    const int attackerValue = attacker == NO_PIECE_TYPE ? 0 : PIECE_VALUE[attacker];
    int s = victimValue * 16 - attackerValue + 1'000'000;
    if (m.promo != NO_PIECE_TYPE) s += 2'000'000;
    return s;
}

}

void Search::clear() {
    if (!tt_.empty()) std::fill(tt_.begin(), tt_.end(), TTEntry{});
    generation_ = 0;
    for (auto& row : killers_) { row[0] = Move{}; row[1] = Move{}; }
    std::fill(&history_[0][0][0],
              &history_[0][0][0] + COLOR_NB * PIECE_TYPE_NB * SQUARE_NB, 0);
}

bool Search::time_exceeded() {
    if (stopped_) return true;
    // Never abort before one full iteration has produced a move, or an
    // early `stop` (or a GUI sending a second `go`) leaves us returning
    // whatever move happened to be first in the list.
    if (!haveResult_) return false;
    if (stopRequested_.load(std::memory_order_relaxed)) { stopped_ = true; return true; }
    if ((nodes_ & 2047) != 0) return false;
    if (timeLimit_ <= 0) return false;
    if (now_ms() - startTime_ >= timeLimit_) stopped_ = true;
    return stopped_;
}

void Search::tt_store(uint64_t key, int depth, int score, uint8_t flag, const Move& best, int ply) {
    TTEntry& e = tt_[key & (TT_SIZE - 1)];

    // Depth-preferred replacement, but anything from an older search is
    // always replaceable. This is what lets the table survive between the
    // moves of a game instead of being wiped each time.
    if (e.key == key && e.gen == generation_ && e.depth > depth)
        return;

    e.key = key;
    e.depth = int8_t(depth);
    e.flag = flag;
    e.best = pack_move(best);
    e.gen = generation_;
    int32_t s = score;
    if (s > MATE_BOUND) s += ply;
    else if (s < -MATE_BOUND) s -= ply;
    e.score = s;
}

const Search::TTEntry* Search::tt_probe(uint64_t key) const {
    const TTEntry& e = tt_[key & (TT_SIZE - 1)];
    return e.key == key ? &e : nullptr;
}

int Search::qsearch(Position& pos, int alpha, int beta, int ply) {
    STAT_INC(qsearchNodes);
    ++nodes_;
    if (time_exceeded()) return alpha;

    const bool inCheck = pos.checkers_exist();
    int best = -INF;

    if (!inCheck) {
        best = evaluate(pos);
        if (best >= beta) return best;
        if (best > alpha) alpha = best;
    }

    if (ply >= MAX_PLY - 1) return inCheck ? evaluate(pos) : alpha;

    // Out of check we only need noisy moves, and generating just those is
    // far cheaper than generating everything and discarding 85% of it.
    // In check we need every evasion, quiet ones included.
    MoveList ml;
    if (inCheck) generate_moves(pos, ml);
    else generate_captures(pos, ml);

    int scores[MoveList::MAX];
    Move ordered[MoveList::MAX];
    int n = 0;
    for (int i = 0; i < ml.count; ++i) {
        STAT_INC(movesScored);
        scores[n] = capture_score(pos, ml.moves[i]);
        ordered[n] = ml.moves[i];
        ++n;
    }

    bool anyLegal = false;

    for (int k = 0; k < n; ++k) {
        int bi = k;
        for (int j = k + 1; j < n; ++j) {
            STAT_INC(sortComparisons);
            if (scores[j] > scores[bi]) bi = j;
        }
        std::swap(scores[k], scores[bi]);
        std::swap(ordered[k], ordered[bi]);

        // Skip captures that simply lose material. Move ordering puts
        // QxP ahead of everything by victim value even when the pawn is
        // defended; SEE is what notices that the exchange loses a queen.
        if (!inCheck && ordered[k].promo == NO_PIECE_TYPE
            && see(pos, ordered[k]) < 0) {
            STAT_INC(seePruned);
            continue;
        }

        // Delta pruning. Out of check, `best` is the stand-pat score: what
        // we are already guaranteed without capturing at all. If that plus
        // everything this capture could possibly win still falls short of
        // alpha, the capture cannot matter. Never prune while in check --
        // there we are searching evasions, not optional captures.
        if (!inCheck && best > -INF) {
            const Move& m = ordered[k];
            const int victim =
                m.isEnPassant       ? PIECE_VALUE[PAWN]
              : m.capturedPlus1 != 0 ? PIECE_VALUE[m.capturedPlus1 - 1]
                                     : 0;
            const int promoted = m.promo != NO_PIECE_TYPE
                               ? PIECE_VALUE[m.promo] - PIECE_VALUE[PAWN]
                               : 0;
            if (best + victim + promoted + DELTA_MARGIN < alpha) {
                STAT_INC(deltaPruned);
                continue;
            }
        }

        StateInfo st;
        pos.do_move(ordered[k], st);
        if (pos.attacked_by(pos.side_to_move(),
                            pos.king_square(~pos.side_to_move()))) {
            pos.undo_move(ordered[k], st);
            continue;
        }
        anyLegal = true;

        const int score = -qsearch(pos, -beta, -alpha, ply + 1);
        pos.undo_move(ordered[k], st);
        if (stopped_) break;
        if (score > best) best = score;
        if (score > alpha) alpha = score;
        if (alpha >= beta) break;
    }

    if (inCheck && !anyLegal) return -MATE + ply;
    return best;
}

int Search::negamax(Position& pos, int depth, int alpha, int beta, int ply) {
    STAT_INC(negamaxNodes);
    ++nodes_;
    if (time_exceeded()) return alpha;

    const bool inCheckAtEntry = pos.checkers_exist();
    if (inCheckAtEntry && ply < MAX_PLY - 2) ++depth;

    if (depth <= 0 || ply >= MAX_PLY - 1)
        return qsearch(pos, alpha, beta, ply);

    keys_.push_back(pos.key());

    const uint64_t key = pos.key();

    if (ply > 0 && pos.halfmove_clock() >= 100) { keys_.pop_back(); return 0; }
    for (int i = int(keys_.size()) - 3; i >= 0 && i >= int(keys_.size()) - 1 - pos.halfmove_clock(); i -= 2) {
        STAT_INC(repetitionSteps);
        if (keys_[i] == key) { keys_.pop_back(); return 0; }
    }

    Move ttMove{};
    bool hasTtMove = false;
    if (const TTEntry* e = tt_probe(key)) {
        hasTtMove = true;
        ttMove = unpack_move(e->best);

        if (e->depth >= depth && ply > 0) {
            int s = e->score;
            if (s > MATE_BOUND) s -= ply;
            else if (s < -MATE_BOUND) s += ply;
            if (e->flag == FLAG_EXACT
                || (e->flag == FLAG_LOWER && s >= beta)
                || (e->flag == FLAG_UPPER && s <= alpha)) {
                keys_.pop_back();
                return s;
            }
        }
    }

    const bool isPvNode = beta - alpha > 1;

    // Static evaluation of this node, used by both prunings below. Not
    // meaningful while in check, where the side to move may be forced into
    // anything, so it is not computed there.
    const int staticEval = inCheckAtEntry ? 0 : evaluate(pos);

    // Reverse futility (a "static null move"): being this far ahead means
    // even a passive move should hold beta.
    if (!isPvNode && !inCheckAtEntry
        && depth <= REVERSE_FUTILITY_MAX_DEPTH
        && std::abs(beta) < MATE_BOUND
        && staticEval - REVERSE_FUTILITY_MARGIN * depth >= beta) {
        STAT_INC(reverseFutilityPruned);
        keys_.pop_back();
        return staticEval;
    }

    if (!isPvNode && !inCheckAtEntry && depth >= 3
        && pos.has_non_pawn_material(pos.side_to_move())) {
        // Making a second null move does not undo the first: the
        // en-passant square stays cleared and the halfmove clock advances
        // twice, so the rest of this node lost its en passant captures.
        StateInfo nullState;
        pos.do_null_move(nullState);
        const int score = -negamax(pos, depth - 3, -beta, -beta + 1, ply + 1);
        pos.undo_null_move(nullState);
        if (stopped_) { keys_.pop_back(); return alpha; }
        if (score >= beta) { keys_.pop_back(); return beta; }
    }

    MoveList ml;
    generate_moves(pos, ml);

    int scores[MoveList::MAX];
    for (int i = 0; i < ml.count; ++i) {
        STAT_INC(movesScored);
        const Move& m = ml.moves[i];
        int s;
        if (hasTtMove && m.from == ttMove.from && m.to == ttMove.to && m.promo == ttMove.promo)
            s = 10'000'000;
        else if (is_capture_like(m))
            s = capture_score(pos, m);
        else if (m == killers_[ply][0])
            s = 900'000;
        else if (m == killers_[ply][1])
            s = 800'000;
        else {
            const PieceType mover = pos.piece_on(Square(m.from));
            s = history_[pos.side_to_move()][mover == NO_PIECE_TYPE ? PAWN : mover][m.to];
        }
        scores[i] = s;
    }

    int best = -INF;
    int quietsSearched = 0;
    Move bestMove{};
    uint8_t flag = FLAG_UPPER;
    const Color us = pos.side_to_move();
    bool foundLegal = false;
    int searched = 0;

    for (int k = 0; k < ml.count; ++k) {
        int bi = k;
        for (int j = k + 1; j < ml.count; ++j) {
            STAT_INC(sortComparisons);
            if (scores[j] > scores[bi]) bi = j;
        }
        std::swap(scores[k], scores[bi]);
        std::swap(ml.moves[k], ml.moves[bi]);

        const Move move = ml.moves[k];

        // Late move pruning: enough quiet moves have already failed here
        // that the ordering is unlikely to be hiding a good one further
        // down the list.
        if (!isPvNode && !inCheckAtEntry && foundLegal
            && depth <= LMP_MAX_DEPTH
            && !is_capture_like(move)
            && std::abs(alpha) < MATE_BOUND
            && quietsSearched >= lmp_limit(depth)) {
            STAT_INC(latePruned);
            continue;
        }

        // Futility: near the leaves, a quiet move from a position already
        // far below alpha is not going to rescue it. Never applied to the
        // first move, so every node still searches something.
        if (!isPvNode && !inCheckAtEntry && foundLegal
            && depth <= FUTILITY_MAX_DEPTH
            && !is_capture_like(move)
            && std::abs(alpha) < MATE_BOUND
            && staticEval + FUTILITY_MARGIN[depth] <= alpha) {
            STAT_INC(futilityPruned);
            continue;
        }

        StateInfo st;
        pos.do_move(move, st);
        if (pos.attacked_by(pos.side_to_move(),
                            pos.king_square(~pos.side_to_move()))) {
            pos.undo_move(move, st);
            continue;
        }
        foundLegal = true;
        STAT_INC(movesSearched);
        if (!is_capture_like(move)) ++quietsSearched;

        const int newDepth = depth - 1;
        int score;

        if (searched == 0) {
            score = -negamax(pos, newDepth, -beta, -alpha, ply + 1);
        } else {
            // Late move reductions: quiet moves this far down the ordered
            // list are rarely best, so search them shallower first and only
            // re-search at full depth if one surprises us. This is the
            // single biggest node saving in the whole search.
            int reduction = 0;
            if (depth >= 3 && searched >= 3 && !is_capture_like(move)
                && !inCheckAtEntry && !pos.checkers_exist()) {
                reduction = 1;
                if (searched >= 6) ++reduction;
                if (depth >= 6 && searched >= 12) ++reduction;
                if (isPvNode && reduction > 0) --reduction;
                reduction = std::min(reduction, newDepth - 1);
                if (reduction < 0) reduction = 0;
            }

            score = -negamax(pos, newDepth - reduction, -alpha - 1, -alpha, ply + 1);
            if (!stopped_ && reduction > 0 && score > alpha)
                score = -negamax(pos, newDepth, -alpha - 1, -alpha, ply + 1);
            if (!stopped_ && score > alpha && score < beta)
                score = -negamax(pos, newDepth, -beta, -alpha, ply + 1);
        }
        pos.undo_move(move, st);
        if (stopped_) break;
        ++searched;

        if (score > best) {
            best = score;
            bestMove = move;
            if (score > alpha) {
                alpha = score;
                flag = FLAG_EXACT;
                if (alpha >= beta) {
                    flag = FLAG_LOWER;
                    if (!is_capture_like(bestMove)) {
                        if (!(killers_[ply][0] == bestMove)) {
                            killers_[ply][1] = killers_[ply][0];
                            killers_[ply][0] = bestMove;
                        }
                        const PieceType mover = pos.piece_on(Square(bestMove.from));
                        history_[us][mover == NO_PIECE_TYPE ? PAWN : mover][bestMove.to]
                            += depth * depth;
                    }
                    break;
                }
            }
        }
    }

    keys_.pop_back();

    if (!foundLegal)
        return inCheckAtEntry ? -MATE + ply : 0;

    if (!stopped_)
        tt_store(key, depth, best, flag, bestMove, ply);
    return best;
}

int Search::search_root(const Position& root, std::vector<RootMove>& moves,
                        int depth, int alpha, int beta, Move& bestMove,
                        bool fullWindow) {
    int best = -INF;
    bestMove = Move{};

    for (size_t k = 0; k < moves.size(); ++k) {
        Position next = root;
        next.do_move(moves[k].move);

        int score;
        if (fullWindow) {
            // Weakened play needs every root move to carry a real score.
            // With the usual null-window scout, moves that fail low come
            // back with a bound pinned near alpha rather than their true
            // value, so adding noise to those numbers picked almost
            // uniformly at random - the "1200" setting played like a random
            // mover and lost to "1000".
            score = -negamax(next, depth - 1, -beta, -alpha, 1);
        } else if (k == 0) {
            score = -negamax(next, depth - 1, -beta, -alpha, 1);
        } else {
            score = -negamax(next, depth - 1, -alpha - 1, -alpha, 1);
            if (!stopped_ && score > alpha && score < beta)
                score = -negamax(next, depth - 1, -beta, -alpha, 1);
        }

        if (stopped_) break;
        moves[k].score = score;

        if (score > best) {
            best = score;
            bestMove = moves[k].move;
            // Raising alpha would turn the remaining full-window searches
            // back into bounded ones.
            if (score > alpha && !fullWindow) alpha = score;
        }
    }
    return best;
}

Move Search::pick_noisy_move(const std::vector<RootMove>& moves, int noise) {
    if (moves.empty()) return Move{};
    if (noise <= 0) return moves[0].move;

    // Give every root move a random bonus and take the winner, so close
    // calls go either way and one position does not always produce the same
    // game. Strength itself comes from the depth cap, not from this.
    std::uniform_int_distribution<int> spread(0, noise);

    int bestValue = -INF;
    Move best = moves[0].move;
    for (const RootMove& rm : moves) {
        if (rm.score <= -INF / 2) continue;  // never actually searched
        const int value = rm.score + spread(rng_);
        if (value > bestValue) {
            bestValue = value;
            best = rm.move;
        }
    }
    return best;
}

int Search::static_exchange(const Position& pos, const Move& m) {
    return see(pos, m);
}

int Search::quiet_score(const Position& root) {
    if (tt_.empty()) tt_.resize(TT_SIZE);
    nodes_ = 0;
    stopped_ = false;
    timeLimit_ = 0;
    keys_.clear();
    Position pos = root;
    return qsearch(pos, -INF, INF, 0);
}

SearchInfo Search::run(const Position& root, const SearchLimits& limits,
                       const std::vector<uint64_t>& gameKeys) {
    if (tt_.empty()) tt_.resize(TT_SIZE);
    ++generation_;  // ages the table instead of clearing it

    for (auto& row : killers_) { row[0] = Move{}; row[1] = Move{}; }
    // Decay rather than erase: move ordering from the previous move is
    // still broadly useful.
    for (int c = 0; c < COLOR_NB; ++c)
        for (int p = 0; p < PIECE_TYPE_NB; ++p)
            for (int s = 0; s < SQUARE_NB; ++s)
                history_[c][p][s] /= 2;

    nodes_ = 0;
    stopped_ = false;
    haveResult_ = false;
    startTime_ = now_ms();
    timeLimit_ = limits.infinite ? 0 : limits.movetime;
    keys_ = gameKeys;

    // uci.cpp has already converted the requested strength into a depth
    // cap; here we only need to know whether to add move-choice noise.
    const int noise = std::max(0, limits.noise);
    const int maxDepth = limits.depth;

    SearchInfo info;
    info.best = Move{};

    MoveList rootMoves;
    generate_moves(root, rootMoves);

    std::vector<RootMove> legal;
    for (int i = 0; i < rootMoves.count; ++i) {
        Position probe = root;
        probe.do_move(rootMoves.moves[i]);
        if (!probe.attacked_by(probe.side_to_move(), probe.king_square(~probe.side_to_move())))
            legal.push_back({rootMoves.moves[i], -INF});
    }

    if (legal.empty()) {
        info.score = root.checkers_exist() ? -MATE : 0;
        info.nodes = nodes_;
        return info;
    }

    // One legal move: play it without burning the clock.
    if (legal.size() == 1) {
        info.best = legal[0].move;
        info.depth = 1;
        info.nodes = nodes_;
        std::cout << "info depth 1 score cp 0 nodes 0 time 0 pv "
                  << move_to_uci(info.best) << std::endl;
        return info;
    }

    std::vector<RootMove> completed;
    int prevScore = 0;

    for (int depth = 1; depth <= maxDepth; ++depth) {
        int alpha = -INF, beta = INF, delta = 24;

        // Aspiration windows: re-searching a narrow window around the last
        // score prunes far more than starting from (-INF, INF) each time.
        // Skipped for weakened play, where every root score must stay
        // meaningful for pick_noisy_move.
        const bool aspirate = depth >= 4 && noise == 0
                              && std::abs(prevScore) < MATE_BOUND;
        if (aspirate) {
            alpha = prevScore - delta;
            beta = prevScore + delta;
        }

        Move iterBest{};
        int iterScore = 0;

        while (true) {
            iterScore = search_root(root, legal, depth, alpha, beta, iterBest,
                                    noise > 0);
            if (stopped_) break;

            if (aspirate && iterScore <= alpha) {
                beta = (alpha + beta) / 2;
                alpha = std::max(-INF, iterScore - delta);
                delta += delta / 2;
            } else if (aspirate && iterScore >= beta) {
                beta = std::min(INF, iterScore + delta);
                delta += delta / 2;
            } else {
                break;
            }
        }

        if (stopped_ && info.depth > 0) break;  // keep the last full iteration

        if (iterBest == Move{}) {
            size_t bi = 0;
            for (size_t k = 1; k < legal.size(); ++k)
                if (legal[k].score > legal[bi].score) bi = k;
            iterBest = legal[bi].move;
            iterScore = legal[bi].score;
        }

        prevScore = iterScore;
        haveResult_ = true;
        info.best = iterBest;
        info.score = iterScore;
        info.depth = depth;
        info.nodes = nodes_;
        completed = legal;

        // Best move first, rest by score - the ordering for the next
        // iteration, and what makes aspiration windows pay off.
        for (size_t k = 0; k < legal.size(); ++k)
            if (legal[k].move == iterBest) { std::swap(legal[0], legal[k]); break; }
        for (size_t k = 1; k < legal.size(); ++k) {
            size_t bi = k;
            for (size_t j = k + 1; j < legal.size(); ++j)
                if (legal[j].score > legal[bi].score) bi = j;
            std::swap(legal[k], legal[bi]);
        }

        std::vector<Move> pv;
        Position walk = root;
        tt_store(walk.key(), depth, info.score, FLAG_EXACT, iterBest, 0);
        for (int d = 0; d < depth * 2 + 8; ++d) {
            const TTEntry* e = tt_probe(walk.key());
            if (!e) break;
            const Move m = unpack_move(e->best);
            bool applied = false;
            MoveList all;
            generate_moves(walk, all);
            for (int i = 0; i < all.count && !applied; ++i) {
                if (all.moves[i].from == m.from && all.moves[i].to == m.to
                    && all.moves[i].promo == m.promo) {
                    Position nxt = walk;
                    nxt.do_move(all.moves[i]);
                    if (!nxt.attacked_by(nxt.side_to_move(),
                                         nxt.king_square(~nxt.side_to_move()))) {
                        walk = nxt;
                        applied = true;
                    }
                }
            }
            if (!applied) break;
            pv.push_back(m);
        }
        info.pv = pv;

        const int64_t ms = now_ms() - startTime_;
        const std::string scoreStr =
            info.score > MATE_BOUND ? "mate " + std::to_string((MATE - info.score + 1) / 2)
          : info.score < -MATE_BOUND ? "mate -" + std::to_string((MATE + info.score) / 2)
          : "cp " + std::to_string(info.score);

        std::cout << "info depth " << depth << " score " << scoreStr
                  << " nodes " << nodes_ << " time " << ms
                  << " nps " << (ms > 0 ? nodes_ * 1000 / uint64_t(ms) : 0) << " pv";
        for (const Move& m : pv) std::cout << ' ' << move_to_uci(m);
        std::cout << std::endl;

        if (stopped_) break;
        if (depth >= 2 && std::abs(info.score) > MATE_BOUND) break;

        // Do not start an iteration we almost certainly cannot finish.
        if (limits.softtime > 0 && now_ms() - startTime_ >= limits.softtime) break;
    }

    if (noise > 0 && !completed.empty())
        info.best = pick_noisy_move(completed, noise);

    return info;
}
