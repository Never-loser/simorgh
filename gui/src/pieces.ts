// A cohesive flat piece set authored as inline SVG on a 45x45 board (the
// Cburnett canvas size). Each entry is the inner markup; the colour comes from
// `currentColor` (white = light fill, black = dark fill) with a contrasting
// stroke applied by the wrapper, so one shape serves both sides.

export type PieceType = "p" | "n" | "b" | "r" | "q" | "k";

const BASE = `<ellipse cx="22.5" cy="39.5" rx="13" ry="3.2"/>`;

export const PIECES: Record<PieceType, string> = {
  // Pawn — round head, tapered body, footed base.
  p: `
    ${BASE}
    <path d="M22.5 8.5c3.2 0 5.8 2.6 5.8 5.8 0 2.1-1.1 3.9-2.8 4.9 2.6 1.6 4.5 4.6 4.5 8.9 0 3-1 5.5-2.3 8.4h-10.4c-1.3-2.9-2.3-5.4-2.3-8.4 0-4.3 1.9-7.3 4.5-8.9-1.7-1-2.8-2.8-2.8-4.9 0-3.2 2.6-5.8 5.8-5.8z"/>
    <path d="M12.5 36.5c0-2.5 4.5-3.5 10-3.5s10 1 10 3.5z"/>`,

  // Rook — battlement top, tapered tower, footed base.
  r: `
    ${BASE}
    <path d="M12 36.5c0-2 4.7-3 10.5-3s10.5 1 10.5 3z"/>
    <path d="M14.5 33.5l-1.3-14h18.6l-1.3 14z"/>
    <path d="M12.5 20v-8h4v3h3.5v-3h5v3h3.5v-3h4v8z"/>`,

  // Bishop — mitre with a top ball, slit, bell body.
  b: `
    ${BASE}
    <circle cx="22.5" cy="7" r="2.4"/>
    <path d="M22.5 9.2c4.6 0 7.7 4.1 7.7 8.4 0 2.4-1 4.4-2.6 6h-10.2c-1.6-1.6-2.6-3.6-2.6-6 0-4.3 3.1-8.4 7.7-8.4z"/>
    <path d="M14.5 24.5h16c1.6 2.8 2.5 5.7 2.5 8.5-3.2 1.4-7 2-10.5 2s-7.3-.6-10.5-2c0-2.8.9-5.7 2.5-8.5z"/>
    <path d="M22.5 12.5v9M18.5 17h8" stroke-width="1.4" fill="none"/>`,

  // Knight — stylised horse head facing left.
  n: `
    ${BASE}
    <path d="M13.5 36.5c-.5-3 .3-6 2-8.4 1.9-2.6 4-3.9 4-6.6l-3.8 3.9-2.7-2 6.2-8.1c-1.4-.8-3.1-.2-4.6.9l-1.2-2.6 3.6-3 .5-2.9 2.6 1 2.2-2.6c4.9.2 10.9 3.4 12 12.1.8 6.2.3 12-1 18.8z"/>
    <circle cx="16.6" cy="15.4" r="1.1" fill="#000" stroke="none"/>`,

  // Queen — five-point crown with balls, bell body.
  q: `
    ${BASE}
    <circle cx="8" cy="12" r="2.2"/><circle cx="15.2" cy="9" r="2.2"/>
    <circle cx="22.5" cy="8" r="2.4"/><circle cx="29.8" cy="9" r="2.2"/>
    <circle cx="37" cy="12" r="2.2"/>
    <path d="M8 13.5l2.7 12.5h23.6L37 13.5l-5.3 8.5-4-11.5-5.2 12-5.2-12-4 11.5z"/>
    <path d="M10.5 26h24c1.6 2.6 2.4 5.2 2.4 7.8-3.7 1.5-8.4 2.2-14.4 2.2s-10.7-.7-14.4-2.2c0-2.6.8-5.2 2.4-7.8z"/>`,

  // King — cross, crown band, bell body.
  k: `
    ${BASE}
    <path d="M22.5 4v7M19 7.5h7" stroke-width="2.2"/>
    <path d="M22.5 12c3.6 0 6.3 2.7 6.3 6 0 1.9-.9 3.6-2.3 4.7h-8c-1.4-1.1-2.3-2.8-2.3-4.7 0-3.3 2.7-6 6.3-6z"/>
    <path d="M12 25c3.2-2.3 6.9-2 10.5.4 3.6-2.4 7.3-2.7 10.5-.4 1.7 2.6 2.5 5.4 2.5 8.4-3.9 1.6-8.5 2.4-13 2.4s-9.1-.8-13-2.4c0-3 .8-5.8 2.5-8.4z"/>`,
};

export const START_HINT = PIECES; // re-export convenience
