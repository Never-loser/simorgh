import type { Explain, Status, Term, Color, EngineInfo } from "./types";

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
