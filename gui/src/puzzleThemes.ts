// Names for the puzzle themes kept by python/puzzles.py, in both languages.
import type { Lang } from "./i18n";

const THEMES: Record<string, [string, string]> = {
  mate: ["مات", "Mate"],
  mateIn1: ["مات در ۱", "Mate in 1"],
  mateIn2: ["مات در ۲", "Mate in 2"],
  mateIn3: ["مات در ۳", "Mate in 3"],
  fork: ["چنگال", "Fork"],
  pin: ["میخ", "Pin"],
  skewer: ["سیخ", "Skewer"],
  hangingPiece: ["مهره‌ی بی‌دفاع", "Hanging piece"],
  discoveredAttack: ["حمله‌ی بازشونده", "Discovered attack"],
  doubleCheck: ["کیش دوگانه", "Double check"],
  sacrifice: ["قربانی", "Sacrifice"],
  deflection: ["منحرف کردن", "Deflection"],
  attraction: ["کشاندن", "Attraction"],
  backRankMate: ["مات ردیف آخر", "Back-rank mate"],
  smotheredMate: ["مات خفه", "Smothered mate"],
  promotion: ["ارتقا", "Promotion"],
  trappedPiece: ["مهره‌ی به‌دام‌افتاده", "Trapped piece"],
  xRayAttack: ["حمله‌ی اشعه‌ی ایکس", "X-ray attack"],
  zugzwang: ["زوگزوانگ", "Zugzwang"],
  quietMove: ["حرکت آرام", "Quiet move"],
  defensiveMove: ["حرکت دفاعی", "Defensive move"],
  kingsideAttack: ["حمله در جناح شاه", "Kingside attack"],
  interference: ["مداخله", "Interference"],
  clearance: ["خالی کردن خانه", "Clearance"],
  intermezzo: ["حرکت میانی", "Intermezzo"],
  capturingDefender: ["گرفتن مدافع", "Capturing the defender"],
  exposedKing: ["شاه بی‌پناه", "Exposed king"],
  advancedPawn: ["پیاده‌ی پیشرفته", "Advanced pawn"],
  endgame: ["آخربازی", "Endgame"],
  middlegame: ["وسط‌بازی", "Middlegame"],
  opening: ["گشایش", "Opening"],
  rookEndgame: ["آخربازی رخ", "Rook endgame"],
  pawnEndgame: ["آخربازی پیاده", "Pawn endgame"],
};

export function themeLabel(id: string, lang: Lang): string {
  const t = THEMES[id];
  return t ? t[lang === "fa" ? 0 : 1] : id;
}
