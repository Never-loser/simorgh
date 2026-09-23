#include "openings.h"

#include "movegen.h"
#include "notation.h"
#include "position.h"

#include <fstream>
#include <functional>
#include <sstream>
#include <unordered_map>
#include <vector>

namespace Openings {

namespace {

std::vector<Name> names;
std::unordered_map<uint64_t, size_t> byKey;

// Plays a UCI move the same way `position ... moves` does: it must match one
// of the generated moves and be legal.
bool play(Position& pos, const std::string& uci) {
    MoveList ml;
    generate_moves(pos, ml);
    for (int i = 0; i < ml.count; ++i) {
        if (move_to_uci(ml.moves[i]) == uci && is_legal(pos, ml.moves[i])) {
            pos.do_move(ml.moves[i]);
            return true;
        }
    }
    return false;
}

}

uint64_t key_of(const Position& pos) {
    std::istringstream fen(pos.fen());
    std::string board, stm, castling;
    fen >> board >> stm >> castling;
    return std::hash<std::string>{}(board + ' ' + stm + ' ' + castling);
}

size_t load(const std::string& path, size_t& rejected) {
    names.clear();
    byKey.clear();
    rejected = 0;

    std::ifstream in(path);
    if (!in) return 0;

    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty() || line[0] == '#') continue;

        std::vector<std::string> cols;
        std::istringstream ls(line);
        std::string col;
        while (std::getline(ls, col, '\t')) cols.push_back(col);
        if (cols.size() < 4) { ++rejected; continue; }

        Position pos;
        pos.set(START_FEN);
        std::istringstream moves(cols[3]);
        std::string uci;
        bool ok = true;
        while (ok && moves >> uci) ok = play(pos, uci);
        if (!ok) { ++rejected; continue; }

        // Two lines can reach one position; the first one listed keeps it.
        const uint64_t key = key_of(pos);
        if (byKey.count(key)) continue;
        byKey.emplace(key, names.size());
        names.push_back({cols[0], cols[1], cols[2]});
    }
    return names.size();
}

size_t count() { return names.size(); }

const Name* find(uint64_t key) {
    const auto it = byKey.find(key);
    return it == byKey.end() ? nullptr : &names[it->second];
}

}
