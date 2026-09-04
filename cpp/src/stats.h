#pragma once

// Call counters for working out where search time actually goes.
//
// gprof on MinGW records neither samples nor call counts here, so instead
// the engine counts how often each hot function runs, and a separate
// microbenchmark measures what one call costs. counts x cost gives the
// attribution, without the timing overhead that would distort it.
//
// Compiled out entirely unless SIMORGH_STATS is defined, so the release
// build is untouched.

#ifdef SIMORGH_STATS

#include <cstdint>

namespace Stats {

extern uint64_t attackedBy;
extern uint64_t generateMoves;
extern uint64_t generateCaptures;
extern uint64_t doMove;
extern uint64_t undoMove;
extern uint64_t evaluateCalls;
extern uint64_t negamaxNodes;
extern uint64_t qsearchNodes;
extern uint64_t movesScored;      // moves given an ordering score
extern uint64_t sortComparisons;  // inner-loop steps of the selection sort
extern uint64_t repetitionSteps;  // entries walked looking for a repetition
extern uint64_t movesSearched;
extern uint64_t deltaPruned;
extern uint64_t seePruned;
extern uint64_t futilityPruned;
extern uint64_t reverseFutilityPruned;
extern uint64_t latePruned;    // moves actually recursed into

void reset();
void print();

}

#define STAT_INC(counter) (++Stats::counter)

#else

#define STAT_INC(counter) ((void)0)

#endif
