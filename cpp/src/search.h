#pragma once

#include "position.h"

#include <atomic>
#include <cstdint>
#include <random>
#include <vector>

constexpr int SKILL_MAX = 20;

struct SearchLimits {
    int depth = 64;
    int movetime = 0;      // hard cap in ms
    int softtime = 0;      // stop starting new iterations past this
    bool infinite = false;
    // Centipawns of random spread added to root move scores. 0 = always
    // play the best move found. The depth cap (`depth`) is the primary
    // strength control; this only adds variety and small mistakes.
    int noise = 0;
};

struct SearchInfo {
    Move best;
    int score = 0;
    int depth = 0;
    uint64_t nodes = 0;
    std::vector<Move> pv;
};

class Search {
public:
    SearchInfo run(const Position& root, const SearchLimits& limits,
                   const std::vector<uint64_t>& gameKeys);

    // Quiescence score for a position, from the side to move's point of
    // view. Texel tuning is only valid on positions where nothing is
    // hanging; comparing this against the static evaluation is how a
    // position is judged quiet.
    int quiet_score(const Position& root);

    // Exposed for testing: static exchange evaluation of one move.
    static int static_exchange(const Position& pos, const Move& m);

    // Asked from another thread while run() is working.
    void request_stop() { stopRequested_.store(true, std::memory_order_relaxed); }
    void clear_stop() { stopRequested_.store(false, std::memory_order_relaxed); }

    // Wipe the transposition table; used on ucinewgame, never between the
    // moves of one game - keeping it is most of the speed-up.
    void clear();

private:
    int qsearch(Position& pos, int alpha, int beta, int ply);
    int negamax(Position& pos, int depth, int alpha, int beta, int ply);
    bool time_exceeded();

    struct RootMove {
        Move move;
        int score = 0;
    };

    int search_root(const Position& root, std::vector<RootMove>& moves,
                    int depth, int alpha, int beta, Move& bestMove,
                    bool fullWindow = false);
    Move pick_noisy_move(const std::vector<RootMove>& moves, int noise);

    struct TTEntry {
        uint64_t key = 0;
        int32_t score = 0;
        uint16_t best = 0;
        int8_t depth = -1;
        int8_t flag = 0;
        uint8_t gen = 0;
    };

    static constexpr int MAX_PLY = 128;
    static constexpr uint64_t TT_SIZE = 1ULL << 21;

    std::vector<TTEntry> tt_;
    uint8_t generation_ = 0;
    Move killers_[MAX_PLY][2] = {};
    int history_[COLOR_NB][PIECE_TYPE_NB][SQUARE_NB] = {};
    uint64_t nodes_ = 0;
    int64_t startTime_ = 0;
    int timeLimit_ = 0;
    bool stopped_ = false;
    bool haveResult_ = false;  // depth 1 finished: safe to abort now
    std::atomic<bool> stopRequested_{false};
    std::vector<uint64_t> keys_;
    // Seeded from the OS: a fixed seed made every process play the
    // identical game, which both wrecked calibration and made the
    // weakened levels dully repetitive to play against.
    std::mt19937 rng_{std::random_device{}()};

    void tt_store(uint64_t key, int depth, int score, uint8_t flag, const Move& best, int ply);
    const TTEntry* tt_probe(uint64_t key) const;
};
