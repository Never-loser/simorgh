// The coach: judges a move by what it cost, and says why in the terms the
// evaluation is made of.
//
// A move is judged by the win chance it gave away, not by centipawns: going
// from +8 to +6 is still winning, going from +1 to -1 is not, and the same
// two pawns mean very different things. The curve and the thresholds are
// the ones Lichess uses for its own game reports.
//
// The "why" compares where the engine's best line leads with where the move
// played leads, a few plies on so that exchanges have finished, and names
// the evaluation terms that came out worse. It is the same breakdown the
// evaluation panel shows, so the reason given is the reason the engine
// actually has.

import type { Engine } from "./engine/engine";
import type { Color, Explain } from "./engine/types";

export type Verdict = "best" | "good" | "inaccuracy" | "mistake" | "blunder";

/** One `analysis` line. `cp` is from the side to move's point of view. */
export interface Analysis {
  depth: number;
  cp: number; // a forced mate is folded in as +-(10000 - moves)
  mate: number | null; // moves to mate, negative when being mated
  best: string;
  pv: string[];
}

export interface MoveReview {
  ply: number; // index of the move in the game
  uci: string;
  san: string;
  mover: Color;
  verdict: Verdict;
  before: number; // White's view, best play from the position before
  after: number; // White's view, after the move played
  loss: number; // win chance given away by the mover, 0..100
  best: string; // what the engine would have played
  bestSan: string;
  reply: string | null; // the engine's answer to the move played
  replySan: string | null;
  why: { name: string; cp: number }[] | null; // from the mover's view; filled on demand
  bestPv: string[];
  playedPv: string[]; // the line after the move played
}

export function parseAnalysis(line: string): Analysis | null {
  const p = line.trim().split(/\s+/);
  if (p[0] !== "analysis" || p[1] === "none") return null;
  const at = (k: string) => p.indexOf(k);
  const kind = p[at("score") + 1];
  const value = Number(p[at("score") + 2]);
  const mate = kind === "mate" ? value : null;
  const cp = mate === null ? value : mate > 0 ? 10000 - mate : -10000 - mate;
  const pvAt = at("pv");
  return {
    depth: Number(p[at("depth") + 1]),
    cp,
    mate,
    best: p[at("best") + 1],
    pv: pvAt >= 0 ? p.slice(pvAt + 1) : [],
  };
}

/** Win chance in percent for a centipawn score (Lichess's curve). */
export function winChance(cp: number): number {
  const c = Math.max(-1000, Math.min(1000, cp));
  return 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * c)) - 1);
}

export function classify(loss: number, isBest: boolean): Verdict {
  if (isBest) return "best";
  if (loss >= 30) return "blunder";
  if (loss >= 20) return "mistake";
  if (loss >= 10) return "inaccuracy";
  return "good";
}

/** The annotation a verdict earns in a move list. */
export function glyph(v: Verdict | undefined): string {
  return v === "blunder" ? "??" : v === "mistake" ? "?" : v === "inaccuracy" ? "?!" : "";
}

/** Accuracy from the mean win chance lost per move (Lichess's formula). */
export function accuracy(losses: number[]): number | null {
  if (!losses.length) return null;
  const mean = losses.reduce((a, b) => a + b, 0) / losses.length;
  return Math.max(0, Math.min(100, 103.1668 * Math.exp(-0.04354 * mean) - 3.1669));
}

/**
 * Judge one move from two analyses: of the position it was played in, and
 * of the position it led to (null when the move ended the game).
 */
export function judge(
  ply: number,
  uci: string,
  san: string,
  bestSan: string,
  replySan: string | null,
  before: Analysis,
  after: Analysis | null,
  afterGameEnd: number | null // mover's view when the move ended the game: 10000 mate, 0 draw
): MoveReview {
  const mover: Color = ply % 2 === 0 ? "w" : "b";
  const sign = mover === "w" ? 1 : -1;
  const isBest = uci === before.best;
  const bestCp = before.cp; // mover's view
  const playedCp = after ? -after.cp : afterGameEnd ?? bestCp;
  // A move as good as the engine's own choice loses nothing, even if the
  // two searches happen to disagree by a few centipawns.
  const loss = isBest ? 0 : Math.max(0, winChance(bestCp) - winChance(playedCp));
  return {
    ply, uci, san, mover,
    verdict: classify(loss, isBest),
    before: sign * bestCp,
    after: sign * playedCp,
    loss,
    best: before.best,
    bestSan,
    reply: after?.best ?? null,
    replySan,
    why: null,
    bestPv: before.pv,
    playedPv: after?.pv ?? [],
  };
}

const PLIES_AHEAD = 4;

/**
 * Why a move was worse than the best one: the evaluation terms that differ
 * most between the end of the best line and the end of the line played,
 * from the mover's view, worst first.
 */
export async function explainWhy(engine: Engine, line: string[], r: MoveReview): Promise<{ name: string; cp: number }[]> {
  const bestEnd = [...line, ...r.bestPv.slice(0, PLIES_AHEAD)];
  const playedEnd = [...line, r.uci, ...r.playedPv.slice(0, PLIES_AHEAD - 1)];
  const a: Explain | null = await engine.explainAt(bestEnd);
  const b: Explain | null = await engine.explainAt(playedEnd);
  if (!a || !b) return [];
  const sign = r.mover === "w" ? 1 : -1;
  const names = new Set([...a.terms, ...b.terms].map((t) => t.name));
  const get = (e: Explain, n: string) => e.terms.find((t) => t.name === n)?.cp ?? 0;
  return [...names]
    .filter((n) => n !== "rounding")
    .map((n) => ({ name: n, cp: sign * (get(b, n) - get(a, n)) }))
    .filter((t) => t.cp <= -10)
    .sort((x, y) => x.cp - y.cp)
    .slice(0, 3);
}

export interface GameReview {
  plies: MoveReview[];
  evals: number[]; // White's view of each position, from the start to the end
}

/**
 * Judge every move of a game: one analysis per position, each move judged
 * from the analyses on either side of it. `onProgress` gets the number of
 * positions done out of the total.
 */
export async function reviewGame(
  engine: Engine,
  moves: string[],
  sans: string[],
  movetime: number,
  onProgress: (done: number, total: number) => void
): Promise<GameReview> {
  const total = moves.length + 1;
  const found: (Analysis | null)[] = [];
  const bestSans: string[] = [];
  for (let i = 0; i < total; i++) {
    const line = moves.slice(0, i);
    const a = await engine.analyse(line, movetime);
    found.push(a);
    bestSans.push(a ? (await engine.sanMap(line)).get(a.best) ?? a.best : "");
    onProgress(i + 1, total);
  }

  // The final position has no analysis when the game ended in it: a mate
  // is decided, a stalemate is level.
  const last = found[total - 1];
  let endForMover: number | null = null;
  if (!last) {
    const st = await engine.snapshot(moves);
    endForMover = st.status.incheck ? 10000 : 0;
  }

  const evals = found.map((a, i) => {
    const sign = i % 2 === 0 ? 1 : -1; // side to move after i plies
    if (a) return sign * a.cp;
    return endForMover === null ? 0 : -sign * endForMover;
  });

  const plies: MoveReview[] = [];
  for (let i = 0; i < moves.length; i++) {
    const before = found[i];
    if (!before) break;
    const after = found[i + 1];
    const replySan = after ? bestSans[i + 1] || after.best : null;
    const end = after ? null : endForMover;
    plies.push(judge(i, moves[i], sans[i], bestSans[i], replySan, before, after, end));
  }
  return { plies, evals };
}
