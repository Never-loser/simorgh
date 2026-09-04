#include "book.h"
#include "notation.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <random>
#include <sstream>
#include <unordered_map>

namespace {

std::unordered_map<uint64_t, std::vector<Book::Entry>> table;
size_t gamesLearned = 0;
int maxPly = 20;      // 10 moves each side
int minGames = 3;     // evidence needed before the book will play a move

// A move must account for at least this fraction of the games recorded in
// a position. Without it the book chases rare sidelines: in a database of
// grandmaster games the offbeat first moves have huge win rates purely
// because they get played against weaker opponents.
constexpr double MIN_SHARE = 0.02;

// ...and it must not be a move the book has watched lose. This is what
// keeps the "never walks back into a losing line" property.
constexpr double SCORE_FLOOR = 0.34;

std::mt19937 rng(unsigned(
    std::chrono::steady_clock::now().time_since_epoch().count()));

uint16_t pack_impl(const Move& m) {
    const uint16_t promo = m.promo == NO_PIECE_TYPE ? uint16_t(0) : uint16_t(m.promo);
    return uint16_t(m.from | (m.to << 6) | (promo << 12));
}

// Lower bound of a Wilson score interval. A move that won its only game
// scores 1.0 raw but has almost no evidence; this pulls it back toward 0.5
// until the sample supports it, so the book prefers "known good" over
// "lucky once".
double confidence(const Book::Entry& e) {
    const double n = double(e.games());
    if (n <= 0) return 0.0;
    const double p = e.score();
    const double z = 1.64;  // ~90%
    const double denom = 1.0 + z * z / n;
    const double centre = p + z * z / (2 * n);
    const double margin = z * std::sqrt(p * (1 - p) / n + z * z / (4 * n * n));
    return (centre - margin) / denom;
}

}

namespace Book {

uint16_t pack_move(const Move& m) { return pack_impl(m); }

void clear() {
    table.clear();
    gamesLearned = 0;
}

size_t position_count() { return table.size(); }
size_t total_games() { return gamesLearned; }

void set_max_ply(int plies) { maxPly = std::max(0, plies); }
int max_ply() { return maxPly; }
void set_min_games(int games) { minGames = std::max(1, games); }
int min_games() { return minGames; }

std::vector<Entry> entries_for(uint64_t key) {
    const auto it = table.find(key);
    if (it == table.end()) return {};
    std::vector<Entry> out = it->second;
    std::sort(out.begin(), out.end(), [](const Entry& a, const Entry& b) {
        return confidence(a) > confidence(b);
    });
    return out;
}

bool probe(const Position& pos, const std::vector<Move>& legal, Move& out,
           int randomness) {
    const auto it = table.find(pos.key());
    if (it == table.end()) return false;

    // Keep only entries that are legal here and have enough evidence.
    struct Candidate { Move move; double games; double score; };
    std::vector<Candidate> candidates;
    double totalGames = 0.0;

    for (const Entry& e : it->second) {
        if (int(e.games()) < minGames) continue;
        for (const Move& m : legal) {
            if (pack_impl(m) != e.move) continue;
            candidates.push_back({m, double(e.games()), confidence(e)});
            totalGames += double(e.games());
            break;
        }
    }

    if (candidates.empty() || totalGames <= 0.0) return false;

    // Popularity decides, not win rate. Win rate only measures the move
    // when both sides are of similar strength, which is true of self-play
    // and false of a grandmaster database: there the rare moves score
    // highest because they are played against weaker opponents.
    //
    // The score is still used, but only as a veto: a move the book has
    // watched lose is dropped however often it appears.
    std::vector<Candidate> shortlist;
    for (const Candidate& c : candidates) {
        if (c.games / totalGames < MIN_SHARE) continue;
        if (c.score < SCORE_FLOOR) continue;
        shortlist.push_back(c);
    }

    if (shortlist.empty()) return false;
    if (shortlist.size() == 1) {
        out = shortlist[0].move;
        return true;
    }

    // `randomness` (0..100) decides how much weight the less popular of the
    // surviving moves keep, so games vary instead of always following the
    // single most fashionable line. At 0 the most played move always wins.
    std::sort(shortlist.begin(), shortlist.end(),
              [](const Candidate& a, const Candidate& b) {
                  return a.games > b.games;
              });
    if (randomness <= 0) {
        out = shortlist[0].move;
        return true;
    }

    const double spread = std::max(0.05, randomness / 100.0);
    double total = 0.0;
    std::vector<double> weights;
    weights.reserve(shortlist.size());
    for (const Candidate& c : shortlist) {
        // spread == 1 keeps the raw frequencies; smaller values sharpen
        // the distribution toward the main line.
        const double w = std::pow(c.games / totalGames, 1.0 / spread);
        weights.push_back(w);
        total += w;
    }

    std::uniform_real_distribution<double> pick(0.0, total);
    double roll = pick(rng);
    for (size_t i = 0; i < shortlist.size(); ++i) {
        roll -= weights[i];
        if (roll <= 0.0) { out = shortlist[i].move; return true; }
    }
    out = shortlist[0].move;
    return true;
}

void learn(const std::vector<Ply>& plies, int result) {
    ++gamesLearned;
    for (size_t i = 0; i < plies.size(); ++i) {
        if (int(i) >= maxPly) break;
        const Ply& p = plies[i];

        // Translate the game result into this mover's point of view.
        int outcome = result;                    // +1 white, 0 draw, -1 black
        if (p.mover == BLACK) outcome = -outcome;

        auto& moves = table[p.key];
        Entry* slot = nullptr;
        for (Entry& e : moves)
            if (e.move == p.move) { slot = &e; break; }
        if (!slot) {
            moves.push_back(Entry{p.move, 0, 0, 0});
            slot = &moves.back();
        }
        if (outcome > 0) ++slot->wins;
        else if (outcome < 0) ++slot->losses;
        else ++slot->draws;
    }
}

bool save(const std::string& path) {
    std::ofstream out(path);
    if (!out) return false;
    out << "# simorgh learned book v1\n";
    out << "# games " << gamesLearned << "\n";
    out << "# key move wins draws losses\n";
    for (const auto& [key, moves] : table)
        for (const Entry& e : moves)
            out << std::hex << key << std::dec << ' ' << e.move << ' '
                << e.wins << ' ' << e.draws << ' ' << e.losses << '\n';
    return bool(out);
}

bool load(const std::string& path) {
    std::ifstream in(path);
    if (!in) return false;

    table.clear();
    gamesLearned = 0;

    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        if (line[0] == '#') {
            std::istringstream head(line.substr(1));
            std::string tag;
            if ((head >> tag) && tag == "games") head >> gamesLearned;
            continue;
        }
        std::istringstream iss(line);
        uint64_t key = 0;
        Entry e;
        unsigned move = 0;
        if (!(iss >> std::hex >> key >> std::dec >> move >> e.wins >> e.draws
                  >> e.losses))
            continue;  // skip malformed rows rather than losing the book
        e.move = uint16_t(move);
        table[key].push_back(e);
    }
    return true;
}

}
