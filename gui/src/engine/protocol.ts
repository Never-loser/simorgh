import type { Explain, Status, Term, Color, EngineInfo, Opening, BookMove } from "./types";

/** Parse the `Fen: ...` line out of the engine's `d` output. */
export function parseFen(lines: string[]): string {
  for (const l of lines) {
    const m = l.match(/^Fen:\s*(.+)/i);
    if (m) return m[1].trim();
  }
  return "";
}

/** `legal e2e4 e7e5 ...` -> Set of UCI moves. */
export function parseLegal(line: string): Set<string> {
  const parts = line.trim().split(/\s+/);
  return new Set(parts[0] === "legal" ? parts.slice(1) : parts);
}

/** `san e2e4 e4 g1f3 Nf3 ...` -> Map UCI -> SAN. */
export function parseSan(line: string): Map<string, string> {
  const p = line.trim().split(/\s+/).slice(1);
  const out = new Map<string, string>();
  for (let i = 0; i + 1 < p.length; i += 2) out.set(p[i], p[i + 1]);
  return out;
}

/**
 * The `opening` block:
 *   opening eco B90 ply 10 exact 1
 *   opening name Sicilian Defense: Najdorf Variation
 *   opening fa دفاع سیسیلی
 *   opening end
 * or the single line `opening none`.
 */
export function parseOpening(lines: string[]): Opening | null {
  const out: Opening = { eco: "", name: "", fa: "", ply: 0, exact: false };
  for (const raw of lines) {
    const l = raw.trim();
    if (l === "opening none") return null;
    if (l.startsWith("opening eco ")) {
      const p = l.split(/\s+/);
      out.eco = p[2] ?? "";
      out.ply = Number(p[p.indexOf("ply") + 1] ?? 0);
      out.exact = p[p.indexOf("exact") + 1] === "1";
    } else if (l.startsWith("opening name ")) {
      out.name = l.slice("opening name ".length);
    } else if (l.startsWith("opening fa ")) {
      out.fa = l.slice("opening fa ".length);
    }
  }
  return out.eco ? out : null;
}

/**
 * `book e2e4 games 36881 w 13170 d 13636 l 10075 score 0.54 san e4` lines.
 * The engine counts wins for the side that played the move; the explorer
 * shows White and Black, so the counts are turned round for Black's moves.
 */
export function parseBook(lines: string[], stm: Color): BookMove[] {
  const out: BookMove[] = [];
  for (const raw of lines) {
    const p = raw.trim().split(/\s+/);
    if (p[0] !== "book" || p.length < 3 || p[1] === "end" || p[1] === "none") continue;
    const kv: Record<string, string> = {};
    for (let i = 2; i + 1 < p.length; i += 2) kv[p[i]] = p[i + 1];
    const w = Number(kv.w ?? 0), d = Number(kv.d ?? 0), l = Number(kv.l ?? 0);
    out.push({
      uci: p[1],
      san: kv.san ?? p[1],
      games: Number(kv.games ?? w + d + l),
      white: stm === "w" ? w : l,
      draws: d,
      black: stm === "w" ? l : w,
    });
  }
  return out.sort((a, b) => b.games - a.games);
}

/** `status incheck 0 legal 20 halfmove 0 stm b` -> Status. */
export function parseStatus(line: string): Status {
  const p = line.trim().split(/\s+/);
  const kv: Record<string, string> = {};
  for (let i = 1; i + 1 < p.length; i += 2) kv[p[i]] = p[i + 1];
  return {
    incheck: kv.incheck === "1",
    legal: Number(kv.legal ?? 0),
    halfmove: Number(kv.halfmove ?? 0),
    stm: (kv.stm as Color) ?? "w",
  };
}

/**
 * Parse the `explain` block. Faithful to the engine's machine-readable lines:
 *   explain phase 24/24 stm b
 *   term placement.pawn 40
 *   term bishop.pair 0 mg 0 eg 0 on white black
 *   white 40
 *   score -40
 *   actual -40
 */
export function parseExplain(lines: string[]): Explain | null {
  const out: Explain = {
    phase: 0, phaseMax: 24, stm: "w", terms: [], white: 0, score: 0, actual: 0,
  };
  let seen = false;
  for (const raw of lines) {
    const l = raw.trim();
    if (!l) continue;
    const p = l.split(/\s+/);
    if (p[0] === "explain") {
      seen = true;
      const ph = (p[2] ?? "0/24").split("/");
      out.phase = Number(ph[0]);
      out.phaseMax = Number(ph[1] ?? 24);
      const si = p.indexOf("stm");
      if (si >= 0) out.stm = p[si + 1] as Color;
    } else if (p[0] === "term") {
      const term: Term = { name: p[1], cp: Number(p[2]) };
      const mg = p.indexOf("mg");
      if (mg >= 0) term.mg = Number(p[mg + 1]);
      const eg = p.indexOf("eg");
      if (eg >= 0) term.eg = Number(p[eg + 1]);
      const on = p.indexOf("on");
      if (on >= 0) term.detail = p.slice(on + 1).join(" ");
      out.terms.push(term);
    } else if (p[0] === "white") {
      out.white = Number(p[1]);
    } else if (p[0] === "score") {
      out.score = Number(p[1]);
    } else if (p[0] === "actual") {
      out.actual = Number(p[1]);
    }
  }
  return seen ? out : null;
}

/** Parse a UCI `info ...` line for depth / score / pv. */
export function parseInfo(line: string): EngineInfo {
  const info: EngineInfo = { raw: line };
  const p = line.trim().split(/\s+/);
  for (let i = 0; i < p.length; i++) {
    if (p[i] === "depth") info.depth = Number(p[i + 1]);
    else if (p[i] === "nps") info.nps = Number(p[i + 1]);
    else if (p[i] === "score") {
      if (p[i + 1] === "cp") info.scoreCp = Number(p[i + 2]);
      else if (p[i + 1] === "mate") info.scoreMate = Number(p[i + 2]);
    } else if (p[i] === "pv") {
      info.pv = p.slice(i + 1);
      break;
    }
  }
  return info;
}

/** Expand FEN board field into an 8x8 array [rank8..rank1][fileA..fileH]. */
export function fenToBoard(fen: string): (string | null)[][] {
  const board: (string | null)[][] = [];
  const rows = (fen.split(/\s+/)[0] || "8/8/8/8/8/8/8/8").split("/");
  for (const row of rows) {
    const rank: (string | null)[] = [];
    for (const ch of row) {
      if (/\d/.test(ch)) for (let i = 0; i < Number(ch); i++) rank.push(null);
      else rank.push(ch);
    }
    while (rank.length < 8) rank.push(null);
    board.push(rank);
  }
  while (board.length < 8) board.push(Array(8).fill(null));
  return board;
}

export const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];
/** square index (0=a8 .. 63=h1) -> algebraic, and back. */
export function sq(file: number, rank: number): string {
  return FILES[file] + (8 - rank);
}
