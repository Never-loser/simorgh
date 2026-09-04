#include "stats.h"

#ifdef SIMORGH_STATS

#include <iostream>

namespace Stats {

uint64_t attackedBy = 0;
uint64_t generateMoves = 0;
uint64_t generateCaptures = 0;
uint64_t doMove = 0;
uint64_t undoMove = 0;
uint64_t evaluateCalls = 0;
uint64_t negamaxNodes = 0;
uint64_t qsearchNodes = 0;
uint64_t movesScored = 0;
uint64_t sortComparisons = 0;
uint64_t repetitionSteps = 0;
uint64_t movesSearched = 0;
uint64_t deltaPruned = 0;
uint64_t seePruned = 0;
uint64_t futilityPruned = 0;
uint64_t reverseFutilityPruned = 0;
uint64_t latePruned = 0;

void reset() {
    attackedBy = generateMoves = generateCaptures = doMove = undoMove = 0;
    evaluateCalls = negamaxNodes = qsearchNodes = 0;
    movesScored = sortComparisons = repetitionSteps = movesSearched = 0;
    deltaPruned = seePruned = 0;
    futilityPruned = reverseFutilityPruned = latePruned = 0;
}

void print() {
    std::cout << "stats"
              << " negamax " << negamaxNodes
              << " qsearch " << qsearchNodes
              << " genmoves " << generateMoves
              << " gencaptures " << generateCaptures
              << " attackedby " << attackedBy
              << " domove " << doMove
              << " undomove " << undoMove
              << " evaluate " << evaluateCalls
              << " scored " << movesScored
              << " sortcmp " << sortComparisons
              << " repsteps " << repetitionSteps
              << " searched " << movesSearched
              << " deltapruned " << deltaPruned
              << " seepruned " << seePruned
              << " futility " << futilityPruned
              << " revfutility " << reverseFutilityPruned
              << " latepruned " << latePruned
              << std::endl;
}

}

#endif
