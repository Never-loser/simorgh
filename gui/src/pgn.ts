// PGN in and out. Writing is plain formatting. Reading only extracts the
// moves as written; which move each one is -- and whether it is legal at
// all -- is decided by the engine, from its `san` list for each position,
// so the GUI still implements no chess rules of its own.

export interface PgnInfo {
  sans: string[];
  white: string;
  black: string;
  result: string; // "1-0", "0-1", "1/2-1/2" or "*"
  eco?: string;
  opening?: string;
  timeControl?: string; // PGN form, e.g. "300+2"
}

function tag(name: string, value: string): string {
  return `[${name} "${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"]`;
}

export function toPgn(g: PgnInfo, date = new Date()): string {
  const d = `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, "0")}.${String(date.getDate()).padStart(2, "0")}`;
  const tags = [
    tag("Event", "Simorgh game"),
    tag("Site", "Simorgh"),
    tag("Date", d),
    tag("Round", "-"),
    tag("White", g.white),
    tag("Black", g.black),
    tag("Result", g.result),
  ];
  if (g.eco) tags.push(tag("ECO", g.eco));
  if (g.opening) tags.push(tag("Opening", g.opening));
  if (g.timeControl) tags.push(tag("TimeControl", g.timeControl));

  // Movetext, wrapped at 80 columns as the PGN standard asks.
  const words: string[] = [];
  g.sans.forEach((san, i) => {
    if (i % 2 === 0) words.push(`${i / 2 + 1}.`);
    words.push(san);
  });
  words.push(g.result);
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    if (line && line.length + 1 + w.length > 80) {
      lines.push(line);
      line = w;
    } else line = line ? `${line} ${w}` : w;
  }
  if (line) lines.push(line);
  return `${tags.join("\n")}\n\n${lines.join("\n")}\n`;
}

/** The moves of the first game in `text`, as written (SAN), or an error. */
export function readPgnMoves(text: string): { sans: string[] } | { error: "setup" | "empty" } {
  // A game that starts from a set-up position cannot be replayed from the
  // initial position, which is the only start the apps know.
  if (/\[\s*SetUp\s+"1"\s*\]/i.test(text) || /\[\s*FEN\s+"/i.test(text)) return { error: "setup" };

  let body = text
    .split(/\r?\n/)
    .filter((l) => !/^\s*\[.*\]\s*$/.test(l)) // tag pairs
    .map((l) => l.replace(/;.*$/, "")) // rest-of-line comments
    .join(" ")
    .replace(/\{[^}]*\}/g, " ") // brace comments
    .replace(/\$\d+/g, " "); // numeric annotation glyphs

  // Variations nest, so strip them with a depth count, not a regex.
  let depth = 0;
  let flat = "";
  for (const ch of body) {
    if (ch === "(") depth++;
    else if (ch === ")") depth = Math.max(0, depth - 1);
    else if (depth === 0) flat += ch;
  }
  body = flat;

  const sans: string[] = [];
  for (let tok of body.split(/\s+/)) {
    tok = tok.replace(/^\d+\.+/, ""); // "12." "12..." and "12.e4"
    if (!tok) continue;
    if (/^(1-0|0-1|1\/2-1\/2|\*)$/.test(tok)) break; // end of the game
    sans.push(tok);
  }
  return sans.length ? { sans } : { error: "empty" };
}

/**
 * The same move whether written "Nf3+", "Nf3!?", "0-0", "e8Q" or "e8=Q":
 * annotations and check marks are dropped, and the common variants of
 * castling and promotion are brought to one form.
 */
export function normalizeSan(san: string): string {
  return san
    .replace(/[+#!?]+$/g, "")
    .replace(/e\.p\.$/, "")
    .replace(/^0-0-0/, "O-O-O")
    .replace(/^0-0/, "O-O")
    .replace(/([a-h][18])([QRBN])$/, "$1=$2");
}
