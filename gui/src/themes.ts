// The themes both apps offer. This file is the source of truth: the Android
// app's Themes.kt carries the same values, key for key, so a theme picked on
// one looks the same on the other.
//
// A theme changes the interface and the board together. Piece colours are
// not themed -- white pieces stay white and black pieces stay dark, because
// that is which side a piece is on, not decoration.

export type ThemeId = "night" | "day" | "wood" | "turquoise" | "tournament";

export interface Theme {
  id: ThemeId;
  name: { fa: string; en: string };
  scheme: "dark" | "light";
  tokens: Record<string, string>;
}

// Token names map straight onto the CSS custom properties in style.css.
export const THEMES: Theme[] = [
  {
    id: "night",
    name: { fa: "شب", en: "Night" },
    scheme: "dark",
    tokens: {
      "bg": "#0d1017", "bg-2": "#0a0d13",
      "surface": "#151a22", "surface-2": "#1b212b", "surface-3": "#222a35",
      "border": "#29323f", "border-soft": "#202834",
      "accent": "#6aa5ff", "accent-dim": "#2b4a7a", "accent-glow": "rgba(106, 165, 255, 0.25)",
      "on-accent": "#ffffff", "on-accent-dim": "#eaf2ff",
      "fg": "#eaf0f7", "fg-dim": "#a7b4c3", "muted": "#6b7a8c",
      "ok": "#56d364", "warn": "#e3b341", "danger": "#f2685c",
      "white-side": "#eef1f4", "black-side": "#63c187",
      "pos-text": "#dfe6ee", "neg-text": "#63c187",
      "light-sq": "#b6c0cc", "dark-sq": "#55708c",
      "coord-on-light": "#4a5a6b", "coord-on-dark": "#cdd8e2",
      "sel": "rgba(106, 165, 255, 0.55)", "last": "rgba(227, 179, 65, 0.38)",
      "check": "rgba(242, 104, 92, 0.75)",
    },
  },
  {
    id: "day",
    name: { fa: "روز", en: "Day" },
    scheme: "light",
    tokens: {
      "bg": "#f3f4f6", "bg-2": "#e7e9ed",
      "surface": "#ffffff", "surface-2": "#f4f5f8", "surface-3": "#eceef2",
      "border": "#d6dae1", "border-soft": "#e4e7ec",
      "accent": "#2f6fdb", "accent-dim": "#d9e6fc", "accent-glow": "rgba(47, 111, 219, 0.18)",
      "on-accent": "#ffffff", "on-accent-dim": "#12356f",
      "fg": "#16202c", "fg-dim": "#3f4b59", "muted": "#7a8595",
      "ok": "#1f9d4c", "warn": "#b7791f", "danger": "#d64535",
      // The eval bar keeps a dark trough in every theme, so White's share
      // stays pale here too; only text needs to darken on a light page.
      "white-side": "#f7f8fa", "black-side": "#2f9e6a",
      "pos-text": "#243040", "neg-text": "#1f8f5a",
      "light-sq": "#e3e8ee", "dark-sq": "#8ba0b8",
      "coord-on-light": "#6b7a8c", "coord-on-dark": "#f3f6f9",
      "sel": "rgba(47, 111, 219, 0.45)", "last": "rgba(227, 179, 65, 0.45)",
      "check": "rgba(214, 69, 53, 0.7)",
    },
  },
  {
    id: "wood",
    name: { fa: "چوب", en: "Wood" },
    scheme: "dark",
    tokens: {
      "bg": "#16110d", "bg-2": "#110d0a",
      "surface": "#1f1812", "surface-2": "#271f17", "surface-3": "#30261c",
      "border": "#3d3024", "border-soft": "#2e241b",
      "accent": "#d9a05b", "accent-dim": "#5a3f22", "accent-glow": "rgba(217, 160, 91, 0.25)",
      "on-accent": "#1f1407", "on-accent-dim": "#fbeedd",
      "fg": "#f3ebe0", "fg-dim": "#c4b4a0", "muted": "#8a7862",
      "ok": "#7fbf6a", "warn": "#e0b04f", "danger": "#e36b52",
      "white-side": "#f5eee4", "black-side": "#7fbf6a",
      "pos-text": "#efe6d9", "neg-text": "#7fbf6a",
      "light-sq": "#f0d9b5", "dark-sq": "#b58863",
      "coord-on-light": "#8a6440", "coord-on-dark": "#f0d9b5",
      "sel": "rgba(217, 160, 91, 0.6)", "last": "rgba(205, 210, 106, 0.55)",
      "check": "rgba(227, 107, 82, 0.75)",
    },
  },
  {
    // Lapis and turquoise, the palette of Persian tilework -- where the name
    // Simorgh comes from.
    id: "turquoise",
    name: { fa: "فیروزه", en: "Turquoise" },
    scheme: "dark",
    tokens: {
      "bg": "#0a1420", "bg-2": "#07101a",
      "surface": "#0f1d2c", "surface-2": "#142537", "surface-3": "#1a2e43",
      "border": "#22405a", "border-soft": "#1a3248",
      "accent": "#3cc6c4", "accent-dim": "#13545e", "accent-glow": "rgba(60, 198, 196, 0.25)",
      "on-accent": "#052629", "on-accent-dim": "#e8f9f9",
      "fg": "#e8f4f5", "fg-dim": "#a3c2c8", "muted": "#6b8f99",
      "ok": "#4fd1a5", "warn": "#e8c15a", "danger": "#ef6b5b",
      "white-side": "#eef7f8", "black-side": "#3cc6c4",
      "pos-text": "#e6f2f3", "neg-text": "#3cc6c4",
      "light-sq": "#e6ddc6", "dark-sq": "#2a7f8c",
      "coord-on-light": "#2a6b76", "coord-on-dark": "#e6ddc6",
      "sel": "rgba(232, 193, 90, 0.55)", "last": "rgba(232, 193, 90, 0.35)",
      "check": "rgba(239, 107, 91, 0.75)",
    },
  },
  {
    id: "tournament",
    name: { fa: "مسابقه", en: "Tournament" },
    scheme: "dark",
    tokens: {
      "bg": "#111311", "bg-2": "#0c0e0c",
      "surface": "#191c19", "surface-2": "#202420", "surface-3": "#282d28",
      "border": "#323832", "border-soft": "#262b26",
      "accent": "#8bc34a", "accent-dim": "#3b5a22", "accent-glow": "rgba(139, 195, 74, 0.25)",
      "on-accent": "#15230a", "on-accent-dim": "#f1f8e8",
      "fg": "#eef2ea", "fg-dim": "#b3bdaa", "muted": "#7a8672",
      "ok": "#8bc34a", "warn": "#e0b44f", "danger": "#e5655a",
      "white-side": "#f2f4ee", "black-side": "#8bc34a",
      "pos-text": "#eaeee6", "neg-text": "#8bc34a",
      "light-sq": "#eeeed2", "dark-sq": "#769656",
      "coord-on-light": "#769656", "coord-on-dark": "#eeeed2",
      "sel": "rgba(246, 246, 105, 0.6)", "last": "rgba(246, 246, 105, 0.45)",
      "check": "rgba(229, 101, 90, 0.75)",
    },
  },
];

const KEY = "simorgh.theme";

export function savedTheme(): ThemeId {
  try {
    const v = localStorage.getItem(KEY) as ThemeId | null;
    if (v && THEMES.some((t) => t.id === v)) return v;
  } catch {
    /* storage unavailable: fall through to the default */
  }
  return "night";
}

/** Writes a theme's tokens onto :root, which every component reads through var(). */
export function applyTheme(id: ThemeId): void {
  const theme = THEMES.find((t) => t.id === id) ?? THEMES[0];
  const root = document.documentElement;
  for (const [k, v] of Object.entries(theme.tokens)) root.style.setProperty(`--${k}`, v);
  root.style.setProperty("color-scheme", theme.scheme);
  root.dataset.theme = theme.id;
  try {
    localStorage.setItem(KEY, theme.id);
  } catch {
    /* not persisting is fine; the theme still applies for this session */
  }
}
