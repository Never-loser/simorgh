# Simorgh

A UCI chess engine in C++17, with a Tkinter front end and a small set of
Python tools for testing and strength calibration.

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build

python python/gui.py          # graphical board
python python/play.py         # terminal board
```

The GUI is the intended way to play. It never implements chess rules of its
own: it asks the engine for the position (`d`), the legal moves (`legal`)
and the game state (`status`), so the board on screen and the engine's idea
of the game cannot drift apart.

---

## What this pass fixed

### The engine never moved

`go` with no arguments was treated as `go infinite`:

```cpp
if (!(iss >> sub)) sub = "infinite";   // uci.cpp, old handle_go
```

The default-depth fallback below it was skipped whenever `infinite` was set,
and `stop` could not interrupt anything because the command loop was blocked
*inside* `handle_go`. So a bare `go` searched forever and never printed
`bestmove` — and a bare `go` is exactly what `play.py` sent. The engine's own
play script could never get a move out of it.

Now: any unbounded request gets a real ceiling (2 s by default), `wtime`/
`btime` drive proper time management with a soft and a hard limit, and the
search runs on its own thread so `stop` works and the engine keeps answering
`isready` while it thinks.

Two smaller bugs fell out of fixing that one:

- **Time wrapped every ~25 days.** `startTime_` stored milliseconds since
  the epoch in an `int`. That value needs 41 bits, so it truncated, and a
  search could believe it was out of time the moment it started.
- **Searches could be abandoned before producing a move.** A `stop` (or a
  GUI sending a second `go`) arriving in the first milliseconds left the
  engine returning whatever move happened to be first in the list. It now
  always finishes at least one iteration.

### It was slow

Two causes, both fixed:

- **The transposition table was wiped at the start of every search.** Every
  move in a game began from zero knowledge, and it memset 48 MB to get
  there. The table is now aged with a generation counter and only cleared on
  `ucinewgame`.
- **No late move reductions.** Quiet moves late in the ordered list are now
  searched shallower first and only re-searched if they beat alpha. This is
  the single biggest node saving in the search.

Aspiration windows were added on top, and the history heuristic is now
decayed between moves rather than zeroed.

| | before | after |
|---|---|---|
| `bench 8` | 13,403,102 nodes / 3410 ms | **4,291,077 nodes / 1408 ms** |
| `bench 9` | 39,708,120 nodes / 9472 ms | **8,728,536 nodes / 2809 ms** |
| startpos, depth 10 | 4,716,050 nodes | **630,269 nodes** |
| startpos, 2 s | depth 11 | **depth 13** |

Move generation was already correct and is unchanged — `perft` still matches
the reference exactly (4,865,609 from the start position at depth 5;
4,085,603 from Kiwipete at depth 4).

### There were no graphics

There was no GUI at all. `play.py` was a terminal REPL whose own `--help`
still described the engine as a "random mover". `python/gui.py` is the new
front end: a drawn board with piece glyphs, legal-move dots, last-move and
check highlights, a promotion picker, a live evaluation readout with depth
and nodes/second, a move list, board flipping, undo, and a strength
selector. All engine traffic runs on a worker thread, so the window stays
responsive while the engine thinks.

### There was no strength limiting

`setoption` was ignored entirely (`else if (cmd == "setoption") continue;`),
so there was no way to ask for a weaker opponent. The engine now supports:

| option | type | default | meaning |
|---|---|---|---|
| `UCI_LimitStrength` | check | `false` | enable the rating cap |
| `UCI_Elo` | spin 800–2800 | `1200` | target rating |
| `Skill Level` | spin 0–20 | `20` | classic 0–20 knob |
| `Clear Hash` | button | | empty the transposition table |

---

## Strength calibration

**The gaps below are measured. The absolute numbers are not.**

`python/calibrate.py` plays the engine against itself and converts the score
to an Elo difference. Two problems had to be fixed before the numbers meant
anything:

1. **The engine was deterministic.** `rng_` was seeded with a fixed
   constant, so every process played the identical game and a "20-game
   match" was one game replayed twenty times. It now seeds from
   `std::random_device`.
2. **Every game started from the same position.** Matches now begin with a
   few random legal plies (`--opening-plies`), replayed once with each
   colour, so the two settings meet the same positions from both sides.

With that in place, each extra ply of search was worth (20 games per rung,
randomised openings):

| rung | result | Elo gain |
|---|---|---|
| depth 2 vs 1 | +8 =9 −3 | +89 |
| depth 3 vs 2 | +8 =11 −1 | +127 |
| depth 4 vs 3 | +9 =9 −2 | +127 |
| depth 5 vs 4 | +10 =10 −0 | +191 |
| depth 6 vs 5 | +7 =10 −3 | +70 |
| depth 7 vs 6 | +7 =11 −2 | +89 |

`UCI_Elo` maps onto that ladder, anchored at **depth 1 = 800 Elo**. That
anchor is an assumption — nothing here was played against an opponent of
known rating, because none was available on this machine. So a request for
1200 reliably gives you something ~340 Elo stronger than the weakest
setting, but whether that point is really 1200 on a human scale is
unverified. To check it properly, play the engine against a rated engine or
on a rating site and shift the `LADDER` table in `uci.cpp` accordingly.

Rungs above depth 7 are extrapolated at the last measured gap, and are
marked as such in the code. At normal thinking times the clock usually stops
the search before those caps bind.

Reproduce any of this with:

```bash
python python/calibrate.py --by-depth --games 20 --levels 4 --reference 3 --seed 42
python python/calibrate.py --games 20 --levels 1200 --reference 1000
```

---

## Learning from play

The engine gets stronger the more it plays, in two independent ways. Both
start from nothing: there is no shipped opening book and no pretrained
weights.

### The opening book

Every finished game is folded into `data/book.txt`, recording for each
position how each move worked out **for the side that played it**. Later
games prefer moves with a good record.

Two rules keep this from backfiring:

- a move must have been seen at least `Book Min Games` times (default 3)
  before the book will play it, and the score used is the lower bound of a
  Wilson interval, so one lucky win does not promote a move;
- if every move the book knows in a position scores badly, the book
  declines and the search decides instead.

So more games can add knowledge, but cannot push the engine back into a
line it has learned loses. Games played in the GUI count too -- the front
end sends `learn` when a game ends.

### Feeding it real games

Self-play is a weak teacher: the engine can only learn openings it was
already good enough to find. Importing real games fixes that.

```
python python/importpgn.py games.pgn
python python/importpgn.py "pgn/*.pgn" --min-elo 2400 --positions
```

PGN is in algebraic notation ("Nf3") and the engine speaks UCI ("g1f3").
The importer converts between them using the engine's own legal-move list,
so a move is only accepted if the engine agrees it is legal -- which makes
this a strict PGN validator as well as an importer. Castling, en passant,
promotion and under-disambiguated moves are all handled; an ambiguous move
is refused rather than guessed at.

| flag | effect |
|---|---|
| `--min-elo N` | skip games where either player is rated below N |
| `--positions` | also append labelled positions for evaluation tuning |
| `--draws` | keep drawn games (skipped by default; they dominate GM databases and teach the book little) |
| `--book-depth N` | plies of each game stored in the book (default 20) |
| `--book PATH` | write to a different book file instead of the live one |
| `--max-games N` | stop after N games |

Remember the book still needs `Book Min Games` (default 3) sightings of a
move before it will play it, so a handful of games changes nothing --
import thousands.

### The evaluation weights

`data/positions.txt` collects positions from played games, each labelled
with that game's result. Before tuning, `quietfilter.py` keeps only the
*quiet* ones -- positions where the static evaluation already agrees with
the quiescence score, so nothing is hanging. Texel tuning fits the static
evaluation, so a position with a piece en prise is off by a piece and
would just be fitted as noise. On the first 126-game dataset this removed
24% of the positions. The `tune` command fits the 453
evaluation weights (5 material values and 7 piece-square tables) so the
static evaluation predicts those results, Texel style.

Only the four free material values are fitted by default. Fitting all 453
parameters needs far more games than a first run produces -- positions from
one game all carry that game's result, so 126 games supply roughly 126
independent labels, not 11,000. Pass `--scope all` once the dataset is
large enough.

**Tuning output is never trusted on its own.** Lower tuning error means the
evaluation predicts past results better; it does not mean the engine plays
better. Measured here: fitting all 453 parameters on 126 games cut the
tuning error by 26% and lost the resulting match 4-63, about -330 Elo. The
gate caught it and the weights were discarded. So every candidate has to
win a match against the weights currently in use before it is installed:

```
python python/learn.py --games 200 --gate-games 200
```

That runs one round: self-play, tune, gate match, and promotion only if
the candidate wins with 95% confidence. A rejected round is normal and
costs nothing -- the opening book still grew, and the positions carry over,
so the next round tunes on more data.

The pawn value is pinned at 100 so the centipawn scale cannot drift, and
the unreachable pawn-table squares (ranks 1 and 8) are excluded.

Run the pieces individually if you prefer:

```
python python/selfplay.py --games 200      # play, grow the book, log positions
python python/gate.py --games 200          # judge a candidate, add --promote
```

`weights load|save|reset` and `book` are available at the UCI prompt for
inspecting what has been learned.

### What it is worth so far

Measured on this machine, from a 126-game dataset:

| candidate | parameters fitted | match result | Elo |
|---|---|---|---|
| all weights, unfiltered positions | 453 | +4 =13 -63 | -328 |
| material only, unfiltered | 4 | +6 =70 -24 | -63 |
| material only, quiet positions | 4 | +12 =67 -21 | -31 |

All three were rejected, so the engine still runs on its built-in weights.
Each methodology fix roughly halved the damage, but nothing has beaten the
hand-written tables yet -- those are standard published piece-square values
and they encode a lot of chess knowledge. Texel tuning normally needs tens
of thousands of games to beat them, so expect several long training runs
before a candidate passes, and treat a rejection as the gate doing its job.

The opening book was measured the same way, playing it against the same
engine with the book switched off (`python python/bookmatch.py`):

| | games | result | Elo |
|---|---|---|---|
| book vs no book | 100 | +14 =74 -12 | +6.9 |

The 95% interval is [0.460, 0.560] in score terms, which straddles 0.5, so
this is **not yet a measurable improvement** either. That is what a book of
2,393 entries learned from 126 games should look like: it covers only the
first few moves, both sides are otherwise the same engine, and an opening
edge is worth little at 50ms a move. The book is safe by construction --
it plays only with enough evidence and declines lines it has learned lose
-- but "safe" is not the same as "proven to help", and at this sample size
it is not proven.

So: the machinery is built and tested, and nothing has made the engine
stronger yet. Both mechanisms need far more games than one session can
produce.

### Checking it still works

```
python python/selftest.py
```

Verifies move generation against known perft counts, that mirrored
positions evaluate identically, that the book plays only with enough
evidence and declines lines it has learned lose, and that a finished GUI
game reaches the book exactly once.

## What this optimisation pass changed

Every change below was measured by playing the new build against the old
one. Nothing was kept on the strength of it sounding like an improvement.

### Kept, and proven at 95% confidence

| change | effect |
|---|---|
| futility + reverse futility pruning | **+65 Elo** (200 games, +57 =123 -20) |
| material values tuned on grandmaster games | **+28 Elo** (321 games, +86 =175 -60) |

### Kept, positive but inside the noise

Delta pruning (+26), SEE pruning of losing captures (+20), tapered king
evaluation (+19), pawn structure (+9), late move pruning (+2), bishop pair
(+27 over a single 105-game batch). Each was measured and none lost
strength; none reached the 95% bar on its own.

### Reverted after measuring

| change | why |
|---|---|
| lazy move ordering | skipped scoring at only 2.7% of nodes; no time difference |
| table-driven LMR | exactly 0.0 Elo over 200 games |
| tuning all 453 eval parameters | **-62 Elo** |
| the same with mirror symmetry (220 parameters) | **-47 Elo** |
| mobility | implemented and tested, never measured -- so not kept |

The piece-square tuning results are the clearest signal in the table: the
fewer free parameters, the better the outcome (453 → -62, 220 → -47,
4 → +28). Roughly four thousand independent game results cannot support
hundreds of parameters, and the hand-written tables already encode a lot of
chess. That line of work was stopped rather than pushed further.

### Speed

`bench 9` went from about 2620ms to about 630ms, roughly 4x, with move
generation still matching known perft counts exactly.

### Bugs found along the way

- The engine segfaulted on *any* file I/O: it resolved `libstdc++-6.dll`
  from whatever was first on PATH. Fixed by linking the runtime statically,
  which also makes the binary standalone.
- Paths containing a space were truncated at the space.
- `evaluate()` was asymmetric: it chose the endgame king table inside the
  colour loop, so White was judged with Black's material still counted as
  zero. Five of eleven mirrored positions disagreed, by up to 80cp.
- Undoing a null move by making a second one does not undo it: the
  en-passant square stayed cleared, so the rest of that node could not
  generate en passant captures.
- SEE's roll-back loop skipped the single-recapture case -- exactly the
  case that turns a winning-looking capture into a losing one.
- The opening book learned survivorship bias from grandmaster games: 1.h3
  scored 94% off 55 games because strong players only play it against
  weaker opponents. Book selection is now popularity-driven with a
  losing-line veto.
- Bulk PGN import rewrote the entire book after every game, which is
  quadratic over tens of thousands of games.

### Where this stopped, and why

The remaining hand-crafted evaluation ideas (mobility, king safety) are
each worth perhaps 10-30 Elo. Proving a 30 Elo change at this noise level
needs roughly 500 games. The match harness leaks engine processes when a
run is interrupted -- each one holds about 90MB -- so successive runs died
progressively earlier, eventually after 13 games. At that point the
bottleneck was measurement, not ideas, and grinding more changes through an
unreliable harness would only have produced guesses.

Fixing that leak is the prerequisite for any further tuning work. The next
real step up in strength after that is a neural evaluation, which is a
different project rather than another increment on this one.

## Explaining a move

Every strong engine tells you a position is worth +0.47. None of them can
tell you *which* +0.47, because they evaluate with a neural network whose
weights carry no human meaning. Simorgh's evaluation is hand-written, so it
decomposes into named terms:

```
python python/explain.py --fen "8/5p2/4k3/8/2P5/1P6/P4PPP/4K3 w - - 0 1"
```

```
  evaluation: +5.49 from White's point of view
  phase:      endgame (0/24)   to move: white

  reasons, largest first:
     +5.00  pawn material  (6 v 1)
     +0.80  passed pawns  (white: a2, h2, b3, c4)
     -0.60  king placement
     +0.15  pawn placement
     +0.14  isolated pawns  (black: f7)
```

Drop `--english` for Persian. `--best` also searches and shows the move it
would play.

The engine side is the UCI command `explain`, which prints one
machine-readable line per term so a front end can render it in any
language. The decomposition is **exact**: the terms sum to exactly what
`evaluate()` returns. That is not free -- tapering divides once at the end,
so tapering each term separately truncates several times instead, and the
few centipawns of difference are reported as their own `rounding` term
rather than silently absorbed into a neighbour. An explanation that only
roughly matches the number the engine searched on would be worse than none.

`selftest.py` checks that on ~1,400 positions from random games: the terms
must sum to the total, the total must equal `evaluate()`, and every term
must fire somewhere in the corpus, so no term goes untested.

## Measuring strength

Everything the project measures against itself is *relative*. For a number
on an outside scale you need an outside opponent.

### Against a reference engine

```
python python/vsengine.py --opponent tools/stockfish.exe     --opponent-elo 2400 --games 200
```

Sets the opponent to a fixed strength with UCI_LimitStrength, plays a
colour-balanced match, and converts the score to an Elo difference from
the opponent's nominal rating. Simorgh's own book is off by default so the
result measures the engine.

Measured here, 100ms per move, book off, against Stockfish 18:

| opponent set to | result | score | implied |
|---|---|---|---|
| 1320 | +40 =0 -0 | 100% | (no estimate possible) |
| 1800 | +26 =1 -3 | 88.3% | 2152 |
| 2100 | +21 =3 -6 | 75.0% | 2291 |
| 2400 | +82 =48 -70 | 53.0% | **2421** (95% CI 2379-2464) |

**Read that last column with care.** The three anchors disagree by about
260 points about the same engine. If Simorgh had a single true rating they
would agree; they do not, because Stockfish's `UCI_Elo` scale is not
linear in real Elo. The +-42 interval on the 2400 row is only sampling
error and does not include that. The honest summary is "somewhere around
2200-2400 against limited Stockfish at 100ms", and more games would not
narrow it, because the uncertainty is in the anchor rather than the sample.

This also means Simorgh's own `UCI_Elo` labels are nominal. The ladder in
`uci.cpp` measures the gaps between its depths but assumes 800 for depth
one, and that assumption is clearly too low.

### On Lichess

```
python python/lichessbot.py --book
```

The only way to get a rating that is comparable with anything else: the
engine plays rated games against real opponents and Lichess maintains a
Glicko-2 rating for it.

Setup, once, by hand:

1. create a Lichess account that has **never played a rated game**;
2. make a token at `lichess.org/account/oauth/token/create` with the
   `bot:play` scope, and put it in `LICHESS_TOKEN` or in
   `data/lichess_token.txt` (gitignored -- never commit it);
3. `python python/lichessbot.py --upgrade` -- **permanent**, the account
   can never be a human account again;
4. `python python/lichessbot.py --book` and leave it running.

It accepts standard-chess challenges inside the configured clock range,
declines everything else with a reason, and hands the real clock to the
engine so its own time management applies.

## Engine

Bitboard move generation, verified with `perft`. Iterative deepening with
principal-variation search, a transposition table, killer moves, a history
heuristic, null-move pruning, late move reductions, check extensions,
aspiration windows and a quiescence search. Evaluation is material plus
piece-square tables, and its weights are loadable and tunable rather than
compiled in.

Beyond the standard UCI commands, the engine understands `d` (print the
board and FEN), `legal` (list legal moves), `status` (check / legal-move
count / halfmove clock / side to move), `eval` (static evaluation),
`go perft N`, `bench [depth]`, and the learning commands `learn <result>`,
`book`, `tune <positions> [out] [passes]` and `weights load|save|reset`.

Paths given to these commands may contain spaces; quote them if other
arguments follow.

## Layout

```
cpp/src/
  bitboard.*    attack tables
  position.*    board state, make/unmake, Zobrist keys
  movegen.*     move generation and perft
  evaluate.*    material + piece-square tables, loadable weights
  book.*        learned opening book
  tune.*        Texel evaluation tuning
  search.*      iterative deepening, PVS, TT, LMR, quiescence
  uci.*         protocol, time management, strength options
python/
  gui.py        Tkinter front end
  play.py       terminal front end
  quietfilter.py  drop positions with something hanging before tuning
  importpgn.py  load real games (PGN) into the book and tuning data
  bookmatch.py  measures the opening book against no book
  vsengine.py   strength against an external UCI engine
  lichessbot.py plays rated games on Lichess for a real rating
  selftest.py   perft, eval symmetry, book behaviour, GUI learning hook
  learn.py      one training round: play, tune, gate, promote
  selfplay.py   self-play games -> opening book + labelled positions
  gate.py       promotion match; refuses weights that do not win
  calibrate.py  self-play strength measurement
  sim_match.py  depth-vs-depth self-play
  oracle.py     independent Python move generator
  perft_check.py, diffwalk.py   movegen cross-checks
```

## License

Copyright (C) 2026 Never-loser

Simorgh is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version. See [LICENSE](LICENSE) for the full text.

The same licence most open-source engines use, Stockfish among them:
anyone may take this code and build on it, provided what they publish
stays open in turn.
