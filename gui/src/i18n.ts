// Two languages, kept as plain dictionaries. The evaluation-term labels are
// ported verbatim from python/explain.py so the desktop app and the engine's
// own explainer speak with one voice.

export type Lang = "fa" | "en";

export const TERM_FA: Record<string, string> = {
  "material.pawn": "برتری پیاده",
  "material.knight": "برتری اسب",
  "material.bishop": "برتری فیل",
  "material.rook": "برتری رخ",
  "material.queen": "برتری وزیر",
  "placement.pawn": "جای‌گیری پیاده‌ها",
  "placement.knight": "جای‌گیری اسب‌ها",
  "placement.bishop": "جای‌گیری فیل‌ها",
  "placement.rook": "جای‌گیری رخ‌ها",
  "placement.queen": "جای‌گیری وزیر",
  "king.placement": "موقعیت شاه",
  "pawns.passed": "پیاده گذشته",
  "pawns.isolated": "پیاده منزوی",
  "pawns.doubled": "پیاده دوتایی",
  "bishop.pair": "جفت فیل",
  rounding: "گِردکردن (تناسب مرحله)",
};

export const TERM_EN: Record<string, string> = {
  "material.pawn": "pawn material",
  "material.knight": "knight material",
  "material.bishop": "bishop material",
  "material.rook": "rook material",
  "material.queen": "queen material",
  "placement.pawn": "pawn placement",
  "placement.knight": "knight placement",
  "placement.bishop": "bishop placement",
  "placement.rook": "rook placement",
  "placement.queen": "queen placement",
  "king.placement": "king placement",
  "pawns.passed": "passed pawns",
  "pawns.isolated": "isolated pawns",
  "pawns.doubled": "doubled pawns",
  "bishop.pair": "bishop pair",
  rounding: "tapering rounding",
};

export function termLabel(name: string, lang: Lang): string {
  const d = lang === "fa" ? TERM_FA : TERM_EN;
  return d[name] ?? name;
}

export type UIStrings = Record<string, string>;

const UI: Record<Lang, UIStrings> = {
  fa: {
    appTitle: "سیمرغ",
    subtitle: "موتور شطرنجی که ارزیابی‌اش را توضیح می‌دهد",
    newGame: "بازی جدید",
    playAs: "بازی با",
    white: "سفید",
    black: "سیاه",
    strength: "قدرت حریف",
    undo: "برگشت",
    flip: "چرخاندن تخته",
    lang: "English",
    thinking: "در حال فکر کردن…",
    yourMove: "نوبت شماست",
    engineMove: "نوبت موتور",
    checkmate: "مات",
    stalemate: "پات",
    check: "کیش",
    draw: "مساوی",
    whiteWins: "سفید برد",
    blackWins: "سیاه برد",
    evaluation: "چرا این ارزیابی؟",
    evalHint: "جمع همه‌ی جمله‌ها دقیقاً همان عددی است که موتور روی آن حساب می‌کند.",
    total: "جمع کل",
    engineScore: "امتیاز موتور",
    matches: "مطابقت دارد",
    moves: "حرکت‌ها",
    favoursWhite: "به سود سفید",
    favoursBlack: "به سود سیاه",
    balanced: "متعادل",
    connecting: "در حال اتصال به موتور…",
    noEngine: "موتور در دسترس نیست. پل توسعه را اجرا کنید: node dev/engine-bridge.mjs",
    promote: "به چه مهره‌ای ارتقا یابد؟",
    depth: "عمق",
    pawnUnit: "پیاده",
  },
  en: {
    appTitle: "Simorgh",
    subtitle: "the chess engine that explains its evaluation",
    newGame: "New game",
    playAs: "Play as",
    white: "White",
    black: "Black",
    strength: "Opponent strength",
    undo: "Undo",
    flip: "Flip board",
    lang: "فارسی",
    thinking: "Thinking…",
    yourMove: "Your move",
    engineMove: "Engine to move",
    checkmate: "Checkmate",
    stalemate: "Stalemate",
    check: "Check",
    draw: "Draw",
    whiteWins: "White wins",
    blackWins: "Black wins",
    evaluation: "Why this evaluation?",
    evalHint: "Every term sums to exactly the number the engine searched on.",
    total: "Total",
    engineScore: "Engine score",
    matches: "matches",
    moves: "Moves",
    favoursWhite: "favours White",
    favoursBlack: "favours Black",
    balanced: "balanced",
    connecting: "Connecting to engine…",
    noEngine: "Engine unavailable. Start the dev bridge: node dev/engine-bridge.mjs",
    promote: "Promote to?",
    depth: "depth",
    pawnUnit: "pawns",
  },
};

export function t(lang: Lang): UIStrings {
  return UI[lang];
}
