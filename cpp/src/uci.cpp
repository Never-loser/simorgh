#include "uci.h"
#include "book.h"
#include "evaluate.h"
#include "movegen.h"
#include "notation.h"
#include "position.h"
#include "search.h"
#include "stats.h"
#include "tune.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace {

Position pos;
Search searcher;
std::vector<uint64_t> gameKeys;
std::thread searchThread;

// Every ply of the current game, so `learn` can fold the finished result
// back into the book.
std::vector<Book::Ply> gamePlies;

bool ownBook = true;
// Bulk import wrote the whole book after every game, which is quadratic
// over tens of thousands of games. Importers turn this off and call
// `booksave` once at the end.
bool bookAutosave = true;
int bookRandomness = 25;
std::string bookPath = "data/book.txt";
std::string weightsPath = "data/weights.txt";

// Strength options. Defaults are full strength; the GUI asks for a limit.
bool limitStrength = false;
int uciElo = 1200;
int skillLevel = SKILL_MAX;

// Bare `go` used to mean "infinite", so the engine searched forever and
// never printed a bestmove - which is exactly what play.py sent. Any
// unbounded request now still gets a hard ceiling.
constexpr int DEFAULT_MOVETIME = 2000;

// Nominal rating of each search depth, measured with
// `python/calibrate.py --by-depth` (20 games per rung, randomised
// openings): each extra ply was worth +89, +127, +127, +191, +70, +89 Elo.
// Those *gaps* are measured; the 800 anchor for depth 1 is an assumption,
// so treat the absolute numbers as nominal. See the README.
struct Rung { int elo; int depth; };
constexpr Rung LADDER[] = {
    // Measured rungs.
    {800, 1}, {889, 2}, {1016, 3}, {1143, 4},
    {1334, 5}, {1404, 6}, {1493, 7},
    // Extrapolated at the last measured gap (+89 Elo per ply). These are
    // guesses, not measurements; at normal thinking times the clock usually
    // stops the search before these caps bind anyway.
    {1582, 8}, {1671, 9}, {1760, 10}, {1849, 11}, {1938, 12},
};

// Depth cap for a target rating; 0 means "no cap, the clock decides".
int depth_for_elo(int elo) {
    int depth = 0;
    for (const Rung& rung : LADDER)
        if (elo >= rung.elo) depth = rung.depth;
    return elo > LADDER[sizeof(LADDER) / sizeof(Rung) - 1].elo ? 0 : depth;
}

// A little randomness so the same position does not always give the same
// game. Fades out as the requested strength rises.
int noise_for_elo(int elo) {
    return std::clamp((1600 - elo) / 12, 0, 66);
}

int requested_elo() {
    // `Skill Level` is the classic 0-20 knob; express it on the same scale.
    const int fromSkill = 800 + skillLevel * 100;
    if (!limitStrength) return fromSkill;
    return std::min(fromSkill, uciElo);
}

void reset_startpos() {
    pos.set(START_FEN);
    gameKeys.clear();
    gamePlies.clear();
}

void stop_search() {
    searcher.request_stop();
    if (searchThread.joinable()) searchThread.join();
    searcher.clear_stop();
}

void print_position() {
    std::cout << "\n";
    for (int r = 7; r >= 0; --r) {
        std::cout << "  +---+---+---+---+---+---+---+---+\n";
        std::cout << (r + 1) << " ";
        for (int f = 0; f < 8; ++f) {
            const Square s = make_square(f, r);
            const PieceType pt = pos.piece_on(s);
            char c = '.';
            if (pt != NO_PIECE_TYPE)
                c = piece_type_to_char(pt, (pos.pieces(WHITE, pt) & square_bb(s)) ? WHITE : BLACK);
            std::cout << "| " << c << ' ';
        }
        std::cout << "|\n";
    }
    std::cout << "  +---+---+---+---+---+---+---+---+\n    a   b   c   d   e   f   g   h\n";
    std::cout << "Fen: " << pos.fen() << "\n";
    std::cout << "Key: " << std::hex << pos.key() << std::dec << "\n" << std::endl;
}

void handle_setoption(std::istringstream& iss) {
    std::string tok, name, value;
    iss >> tok;                       // "name"
    while (iss >> tok && tok != "value") {
        if (!name.empty()) name += ' ';
        name += tok;
    }
    while (iss >> tok) {
        if (!value.empty()) value += ' ';
        value += tok;
    }

    auto as_int = [&](int fallback) {
        try { return std::stoi(value); } catch (...) { return fallback; }
    };

    if (name == "Skill Level") skillLevel = std::clamp(as_int(SKILL_MAX), 0, SKILL_MAX);
    else if (name == "UCI_Elo") uciElo = std::clamp(as_int(1200), 800, 2800);
    else if (name == "UCI_LimitStrength") limitStrength = (value == "true");
    else if (name == "Clear Hash") searcher.clear();
    else if (name == "OwnBook") ownBook = (value == "true");
    else if (name == "Book Autosave") bookAutosave = (value == "true");
    else if (name == "Book Randomness") bookRandomness = std::clamp(as_int(25), 0, 100);
    else if (name == "Book Depth") Book::set_max_ply(std::max(0, as_int(20)));
    else if (name == "Book Min Games") Book::set_min_games(std::max(1, as_int(3)));
    else if (name == "Book File") {
        // Switching book files replaces the book in memory. Without
        // the clear, pointing at a path that does not exist yet left
        // the previously loaded book in place and silently merged it
        // into the new file on the next save.
        bookPath = value;
        Book::clear();
        Book::load(bookPath);
    }
    // (setoption already keeps the whole remainder of the line as `value`,
    // so a Book File path with spaces survives.)
}

// Read one path argument. `iss >> path` stops at the first space, which
// silently truncates any path containing one ("D:/Default Project/..." ->
// "D:/Default"). Quoted paths are accepted so a path with spaces can be
// passed unambiguously even when more arguments follow.
std::string read_path(std::istringstream& iss) {
    iss >> std::ws;
    if (iss.peek() == '"') {
        iss.get();
        std::string path;
        std::getline(iss, path, '"');
        return path;
    }
    std::string token;
    iss >> token;
    return token;
}

void handle_position(std::istringstream& iss) {
    std::string tok;
    iss >> tok;

    if (tok == "startpos") {
        reset_startpos();
        iss >> tok;
    } else if (tok == "fen") {
        std::string fen, part;
        while (iss >> part && part != "moves") fen += part + ' ';
        gameKeys.clear();
        gamePlies.clear();
        pos.set(fen);
    }

    while (iss >> tok) {
        MoveList ml;
        generate_moves(pos, ml);

        bool applied = false;
        for (int i = 0; i < ml.count && !applied; ++i) {
            if (move_to_uci(ml.moves[i]) == tok) {
                gameKeys.push_back(pos.key());
                gamePlies.push_back({pos.key(), Book::pack_move(ml.moves[i]),
                                     pos.side_to_move()});
                pos.do_move(ml.moves[i]);
                applied = true;
            }
        }
        if (!applied) std::cerr << "illegal or unknown move: " << tok << "\n";
    }
}

void handle_go(std::istringstream& iss) {
    stop_search();

    std::string sub;
    const bool bare = !(iss >> sub);

    if (!bare && sub == "perft") {
        int depth = 1;
        iss >> depth;
        const auto t0 = std::chrono::steady_clock::now();
        const uint64_t total = perft_divide(pos, depth);
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - t0).count();
        std::cout << "nodes " << total << " time " << ms << "ms" << std::endl;
        return;
    }

    SearchLimits limits;
    int wtime = 0, btime = 0, winc = 0, binc = 0, movestogo = 0;
    bool haveTime = false, haveDepth = false;

    if (!bare) {
        std::string tok = sub;
        do {
            if (tok == "depth") { iss >> limits.depth; haveDepth = true; }
            else if (tok == "movetime") iss >> limits.movetime;
            else if (tok == "wtime") { iss >> wtime; haveTime = true; }
            else if (tok == "btime") { iss >> btime; haveTime = true; }
            else if (tok == "winc") iss >> winc;
            else if (tok == "binc") iss >> binc;
            else if (tok == "movestogo") iss >> movestogo;
            else if (tok == "infinite") limits.infinite = true;
        } while (iss >> tok);
    }

    if (haveTime && limits.movetime <= 0) {
        const int ownTime = pos.side_to_move() == WHITE ? wtime : btime;
        const int ownInc = pos.side_to_move() == WHITE ? winc : binc;
        const int slices = movestogo > 0 ? std::min(movestogo, 40) : 30;
        // Soft limit ends iterations early; hard limit is the real ceiling,
        // always leaving a margin so we never flag.
        limits.softtime = std::max(20, ownTime / slices + ownInc / 2);
        limits.movetime = std::min(limits.softtime * 3, std::max(30, ownTime - 50));
        limits.infinite = false;
    } else if (!limits.infinite && !haveDepth && limits.movetime <= 0) {
        limits.movetime = DEFAULT_MOVETIME;
    }

    if (limits.movetime < 0) limits.movetime = 0;

    const int elo = requested_elo();
    if (limitStrength || skillLevel < SKILL_MAX) {
        const int cap = depth_for_elo(elo);
        if (cap > 0 && (!haveDepth || cap < limits.depth))
            limits.depth = cap;
        limits.noise = noise_for_elo(elo);
    }

    // A book hit answers instantly and costs no search time at all.
    if (ownBook && !limits.infinite) {
        MoveList bookList;
        generate_moves(pos, bookList);
        std::vector<Move> legalMoves;
        for (int i = 0; i < bookList.count; ++i)
            if (is_legal(pos, bookList.moves[i]))
                legalMoves.push_back(bookList.moves[i]);

        Move bookMove;
        if (!legalMoves.empty()
            && Book::probe(pos, legalMoves, bookMove, bookRandomness)) {
            std::cout << "info string book move (" << Book::position_count()
                      << " positions learned)" << std::endl;
            std::cout << "bestmove " << move_to_uci(bookMove) << std::endl;
            return;
        }
    }

    const Position snapshot = pos;
    const std::vector<uint64_t> keys = gameKeys;

    searcher.clear_stop();
    searchThread = std::thread([snapshot, keys, limits]() {
        const SearchInfo result = searcher.run(snapshot, limits, keys);
        std::cout << "bestmove "
                  << (result.best == Move{} ? std::string("0000")
                                            : move_to_uci(result.best))
                  << std::endl;
    });
}

void handle_bench(std::istringstream& iss) {
    static const char* BENCH_FENS[] = {
        START_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"
    };

    int depth = 8;
    iss >> depth;

    uint64_t totalNodes = 0;
    const auto t0 = std::chrono::steady_clock::now();

    searcher.clear();
    for (const char* fen : BENCH_FENS) {
        Position p;
        p.set(fen);
        SearchLimits limits;
        limits.depth = depth;
        totalNodes += searcher.run(p, limits, {}).nodes;
    }

    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - t0).count();

    std::cout << "bench depth " << depth << " nodes " << totalNodes
              << " time " << ms << "ms"
              << " nps " << (ms > 0 ? totalNodes * 1000 / uint64_t(ms) : 0)
              << std::endl;
}

}

namespace UCI {

void loop() {
    reset_startpos();

    if (Eval::load_weights(weightsPath))
        std::cout << "info string loaded weights from " << weightsPath
                  << std::endl;
    if (Book::load(bookPath))
        std::cout << "info string book " << Book::position_count()
                  << " positions from " << Book::total_games() << " games"
                  << std::endl;

    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        if (cmd == "uci") {
            std::cout << "id name Simorgh 0.2.0\n"
                         "id author EPN\n"
                         "option name Skill Level type spin default 20 min 0 max 20\n"
                         "option name UCI_LimitStrength type check default false\n"
                         "option name UCI_Elo type spin default 1200 min 800 max 2800\n"
                         "option name Clear Hash type button\n"
                         "option name OwnBook type check default true\n"
                         "option name Book Autosave type check default true\n"
                         "option name Book Randomness type spin default 25 min 0 max 100\n"
                         "option name Book Depth type spin default 20 min 0 max 80\n"
                         "option name Book Min Games type spin default 3 min 1 max 50\n"
                         "uciok" << std::endl;
        } else if (cmd == "isready") {
            std::cout << "readyok" << std::endl;
        } else if (cmd == "setoption") {
            handle_setoption(iss);
        } else if (cmd == "ucinewgame") {
            stop_search();
            searcher.clear();
            reset_startpos();
        } else if (cmd == "position") {
            stop_search();
            handle_position(iss);
        } else if (cmd == "go") {
            handle_go(iss);
        } else if (cmd == "bench") {
            stop_search();
            handle_bench(iss);
        } else if (cmd == "d") {
            print_position();
        } else if (cmd == "explain") {
            // Machine-readable on purpose: one term per line, so a front end
            // can render it in any language without parsing prose. The
            // engine states the numbers; python/explain.py turns them into
            // Persian sentences.
            const Eval::Breakdown bd = Eval::explain(pos);
            std::cout << "explain phase " << bd.phase << '/' << bd.phaseMax
                      << " stm " << (pos.side_to_move() == WHITE ? 'w' : 'b')
                      << '\n';
            for (const Eval::Term& t : bd.terms) {
                std::cout << "term " << t.name << ' ' << t.value;
                if (t.tapered)
                    std::cout << " mg " << t.mg << " eg " << t.eg;
                if (!t.detail.empty()) std::cout << " on " << t.detail;
                std::cout << '\n';
            }
            std::cout << "white " << bd.white
                      << "\nscore " << bd.sideToMove
                      << "\nactual " << evaluate(pos) << std::endl;
        } else if (cmd == "legal") {
            MoveList ml;
            generate_moves(pos, ml);
            std::cout << "legal";
            for (int i = 0; i < ml.count; ++i)
                if (is_legal(pos, ml.moves[i]))
                    std::cout << ' ' << move_to_uci(ml.moves[i]);
            std::cout << std::endl;
        } else if (cmd == "status") {
            // Everything a front end needs to name the game state without
            // reimplementing move generation: legal move count plus whether
            // the side to move is in check.
            MoveList ml;
            generate_moves(pos, ml);
            int legalCount = 0;
            for (int i = 0; i < ml.count; ++i)
                if (is_legal(pos, ml.moves[i])) ++legalCount;
            std::cout << "status incheck " << (pos.checkers_exist() ? 1 : 0)
                      << " legal " << legalCount
                      << " halfmove " << pos.halfmove_clock()
                      << " stm " << (pos.side_to_move() == WHITE ? 'w' : 'b')
                      << std::endl;
        } else if (cmd == "learn") {
            // learn 1-0 | 0-1 | 1/2-1/2  -- fold the finished game into the
            // book. The front end calls this when a game ends.
            std::string result;
            iss >> result;
            int outcome = 2;
            if (result == "1-0") outcome = 1;
            else if (result == "0-1") outcome = -1;
            else if (result == "1/2-1/2" || result == "draw") outcome = 0;

            if (outcome == 2) {
                std::cout << "info string learn needs 1-0, 0-1 or 1/2-1/2"
                          << std::endl;
            } else if (gamePlies.empty()) {
                std::cout << "info string nothing to learn: no moves played"
                          << std::endl;
            } else {
                Book::learn(gamePlies, outcome);
                const bool saved = !bookAutosave || Book::save(bookPath);
                std::cout << "info string learned " << gamePlies.size()
                          << " plies, book now " << Book::position_count()
                          << " positions from " << Book::total_games()
                          << " games"
                          << (saved ? "" : " (WARNING: could not write "
                                           "the book file)")
                          << std::endl;
            }
        } else if (cmd == "booksave") {
            std::cout << (Book::save(bookPath) ? "book saved "
                                               : "book save failed ")
                      << bookPath << " (" << Book::position_count()
                      << " positions from " << Book::total_games()
                      << " games)" << std::endl;
        } else if (cmd == "book") {
            // What the book knows about the current position.
            const std::vector<Book::Entry> found = Book::entries_for(pos.key());
            if (found.empty()) {
                std::cout << "book none" << std::endl;
            } else {
                MoveList ml;
                generate_moves(pos, ml);
                for (const Book::Entry& e : found) {
                    for (int i = 0; i < ml.count; ++i) {
                        if (Book::pack_move(ml.moves[i]) != e.move) continue;
                        std::cout << "book " << move_to_uci(ml.moves[i])
                                  << " games " << e.games()
                                  << " w " << e.wins << " d " << e.draws
                                  << " l " << e.losses
                                  << " score " << e.score() << std::endl;
                        break;
                    }
                }
                std::cout << "book end" << std::endl;
            }
        } else if (cmd == "tune") {
            // tune <positions-file> [output-weights] [max-passes]
            std::string data = read_path(iss);
            std::string out = read_path(iss);
            if (out.empty()) out = "data/weights.candidate.txt";
            int passes = 6;
            if (!(iss >> passes)) passes = 6;
            std::string scopeText;
            iss >> scopeText;
            bool scopeOk = true;
            const Tune::Scope scope = Tune::parse_scope(scopeText, scopeOk);
            if (data.empty()) {
                std::cout << "info string usage: tune <positions> [out] "
                             "[passes] [all|material|pst]" << std::endl;
            } else {
            if (!scopeOk) {
                std::cout << "info string unknown scope '" << scopeText
                          << "'; use all, material or pst" << std::endl;
            } else {
                const Tune::Result r = Tune::run(data, out, passes, scope);
                if (!r.ok) {
                    std::cout << "tune failed: " << r.message << std::endl;
                } else {
                    std::cout << "tune ok positions " << r.positions
                              << " scope " << Tune::scope_name(scope)
                              << " params " << r.tunable
                              << " k " << r.k
                              << " error " << r.startError << " -> "
                              << r.endError
                              << " changes " << r.changed
                              << " wrote " << out << std::endl;
                }
                }
            }
        } else if (cmd == "weights") {
            std::string action;
            iss >> action;
            std::string path = read_path(iss);
            // Unquoted trailing text is still a path: keep the whole rest.
            std::string extra;
            std::getline(iss, extra);
            if (!extra.empty() && !path.empty() && path.back() != '"') {
                while (!extra.empty() && extra.front() == ' ') extra.erase(0, 1);
                while (!extra.empty() && extra.back() == ' ') extra.pop_back();
                if (!extra.empty()) path += " " + extra;
            }
            if (action == "load") {
                const std::string p = path.empty() ? weightsPath : path;
                std::cout << (Eval::load_weights(p) ? "weights loaded "
                                                    : "weights load failed ")
                          << p << std::endl;
            } else if (action == "save") {
                const std::string p = path.empty() ? weightsPath : path;
                std::cout << (Eval::save_weights(p) ? "weights saved "
                                                    : "weights save failed ")
                          << p << std::endl;
            } else if (action == "reset") {
                Eval::reset_weights();
                init_eval();
                std::cout << "weights reset to defaults" << std::endl;
            } else {
                std::cout << "info string usage: weights load|save|reset [path]"
                          << std::endl;
            }
        } else if (cmd == "costs") {
#ifdef SIMORGH_STATS
            // Time each hot function on the current position. A volatile
            // sink keeps the optimiser from deleting the work.
            int iterations = 200000;
            iss >> iterations;
            volatile uint64_t sink = 0;
            const auto now = []() {
                return std::chrono::steady_clock::now();
            };
            const auto ns = [](auto a, auto b, int n) {
                return double(std::chrono::duration_cast<
                    std::chrono::nanoseconds>(b - a).count()) / n;
            };

            MoveList ml;
            generate_moves(pos, ml);
            const Color us = pos.side_to_move();
            const Square ksq = pos.king_square(us);

            auto t0 = now();
            for (int i = 0; i < iterations; ++i)
                sink += pos.attacked_by(~us, ksq);
            auto t1 = now();
            const double attackedNs = ns(t0, t1, iterations);

            t0 = now();
            for (int i = 0; i < iterations; ++i) {
                MoveList tmp;
                generate_moves(pos, tmp);
                sink += tmp.count;
            }
            t1 = now();
            const double genNs = ns(t0, t1, iterations);

            t0 = now();
            for (int i = 0; i < iterations; ++i) {
                MoveList tmp;
                generate_captures(pos, tmp);
                sink += tmp.count;
            }
            t1 = now();
            const double capNs = ns(t0, t1, iterations);

            t0 = now();
            for (int i = 0; i < iterations; ++i) {
                StateInfo st;
                const Move& m = ml.moves[i % ml.count];
                pos.do_move(m, st);
                sink += pos.key();
                pos.undo_move(m, st);
            }
            t1 = now();
            const double moveNs = ns(t0, t1, iterations);

            t0 = now();
            for (int i = 0; i < iterations; ++i)
                sink += evaluate(pos);
            t1 = now();
            const double evalNs = ns(t0, t1, iterations);

            std::cout << "costs ns_per_call"
                      << " attacked_by " << attackedNs
                      << " generate_moves " << genNs
                      << " generate_captures " << capNs
                      << " do+undo_move " << moveNs
                      << " evaluate " << evalNs
                      << " (sink " << sink << ")" << std::endl;
#else
            std::cout << "costs needs -DSIMORGH_STATS" << std::endl;
#endif
        } else if (cmd == "stats") {
#ifdef SIMORGH_STATS
            Stats::print();
#else
            std::cout << "stats not compiled in (build with -DSIMORGH_STATS)"
                      << std::endl;
#endif
        } else if (cmd == "statsreset") {
#ifdef SIMORGH_STATS
            Stats::reset();
#endif
            std::cout << "stats reset" << std::endl;
        } else if (cmd == "see") {
            // see <uci-move> -- static exchange value of that move.
            std::string want;
            iss >> want;
            MoveList ml;
            generate_moves(pos, ml);
            bool found = false;
            for (int i = 0; i < ml.count && !found; ++i) {
                if (move_to_uci(ml.moves[i]) != want) continue;
                found = true;
                std::cout << "see " << want << " "
                          << Search::static_exchange(pos, ml.moves[i])
                          << std::endl;
            }
            if (!found) std::cout << "see " << want << " illegal" << std::endl;
        } else if (cmd == "eval") {
            std::cout << "eval " << evaluate(pos) << std::endl;
        } else if (cmd == "qeval") {
            // Static evaluation and quiescence score agree exactly when
            // there is nothing to capture; that is the test for whether a
            // position belongs in the tuning set.
            std::cout << "qeval " << searcher.quiet_score(pos) << std::endl;
        } else if (cmd == "stop") {
            // The search thread prints its own bestmove when it unwinds.
            stop_search();
        } else if (cmd == "quit") {
            stop_search();
            break;
        }
    }

    // Reaching here means stdin closed (EOF) rather than an explicit
    // `quit`. A search already in flight should be allowed to finish and
    // print its bestmove - cancelling it here made every piped one-shot
    // invocation return a depth-1 move.
    if (searchThread.joinable()) searchThread.join();
}

}
