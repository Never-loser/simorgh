// Shapes that mirror exactly what the Simorgh engine prints. The GUI never
// implements chess rules: it asks the engine for the board, the legal moves,
// the status and the evaluation, so the two can never disagree.

export type Color = "w" | "b";

export interface Status {
  incheck: boolean;
  legal: number;
  halfmove: number;
  stm: Color;
}

/** One line of `explain`, e.g. `term placement.pawn 40 mg 0 eg 0 on white black`. */
export interface Term {
  name: string; // e.g. "placement.pawn"
  cp: number; // centipawn contribution, + favours White
  mg?: number;
  eg?: number;
  detail?: string; // raw square/side detail after "on"
}

export interface Explain {
  phase: number; // 0..24
  phaseMax: number;
  stm: Color;
  terms: Term[];
  white: number; // White's summed advantage (cp)
  score: number; // from side-to-move perspective
  actual: number; // engine evaluate(), must equal score
}

/** `opening eco B90 ply 10 exact 1` + name/fa lines. */
export interface Opening {
  eco: string; // "B90"
  name: string; // "Sicilian Defense: Najdorf Variation"
  fa: string; // Persian family name: "دفاع سیسیلی"
  ply: number; // the ply at which the game reached the named position
  exact: boolean; // the current position itself is named
}

/** One `book` line, turned from the mover's view into White/Black. */
export interface BookMove {
  uci: string;
  san: string;
  games: number;
  white: number; // games White won
  draws: number;
  black: number; // games Black won
}

export interface GameState {
  fen: string;
  legal: Set<string>; // UCI moves, e.g. "e2e4", "e7e8q"
  san: Map<string, string>; // UCI -> SAN for every legal move
  status: Status;
  moves: string[]; // move history (UCI)
  explain: Explain | null;
  opening: Opening | null;
  book: BookMove[]; // most played first
}

export interface EngineInfo {
  depth?: number;
  scoreCp?: number;
  scoreMate?: number;
  pv?: string[];
  nps?: number;
  raw: string;
}
