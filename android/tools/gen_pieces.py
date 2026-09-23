"""Generate the twelve piece drawables in app/src/main/res/drawable from the
desktop app's gui/src/pieces.ts, so both apps draw the same piece set.
Run from android/:  python tools/gen_pieces.py
"""
import io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "gui", "src", "pieces.ts")
RES = os.path.join(HERE, "..", "app", "src", "main", "res", "drawable")

# Fill and outline per side, as the desktop's Piece.vue draws them.
SIDES = {"w": ("#F7FAFC", "#20262E"), "b": ("#2A313A", "#0A0D11")}

def attrs(tag):
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))

def ellipse(cx, cy, rx, ry):
    cx, cy, rx, ry = map(float, (cx, cy, rx, ry))
    return (f"M{cx-rx:.2f},{cy:.2f} a{rx:.2f},{ry:.2f} 0 1,0 {2*rx:.2f},0 "
            f"a{rx:.2f},{ry:.2f} 0 1,0 {-2*rx:.2f},0 Z")

def convert(markup, base, fill, outline):
    out = []
    for tag in re.findall(r"<(?:path|circle|ellipse)\b[^>]*/?>", markup.replace("${BASE}", base)):
        a = attrs(tag)
        d = (a["d"] if tag.startswith("<path") else
             ellipse(a["cx"], a["cy"], a["r"], a["r"]) if tag.startswith("<circle") else
             ellipse(a["cx"], a["cy"], a["rx"], a["ry"]))
        is_base = tag.startswith("<ellipse") and 'cy="39.5"' in tag
        f = a.get("fill", "currentColor"); st = a.get("stroke", outline)
        if is_base: f, st = "#47000000", "none"          # the soft shadow under a piece
        elif f == "currentColor": f = fill
        elif f == "#000": f = "#FF000000"
        line = f'    <path android:pathData="{d}"'
        # A stroke-only shape has no fillColor; "none" is not a colour to aapt.
        if f != "none": line += f' android:fillColor="{f}"'
        if st != "none":
            line += (f'\n        android:strokeColor="{st}" android:strokeWidth="{a.get("stroke-width", "1.3")}"'
                     f'\n        android:strokeLineCap="round" android:strokeLineJoin="round"')
        out.append(line + " />")
    return "\n".join(out)

s = io.open(SRC, encoding="utf-8").read()
base = re.search(r"const BASE = `(.*?)`;", s, re.S).group(1)
pieces = dict(re.findall(r"^  ([pnbrqk]): `(.*?)`,", s, re.S | re.M))
assert len(pieces) == 6, sorted(pieces)
for side, (fill, outline) in SIDES.items():
    for p, markup in pieces.items():
        xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
               "<!-- Generated from the desktop app's pieces.ts so both apps share one\n"
               "     piece set. Edit the source there, then regenerate. -->\n"
               '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
               '    android:width="45dp" android:height="45dp"\n'
               '    android:viewportWidth="45" android:viewportHeight="45">\n'
               f'{convert(markup, base, fill, outline)}\n</vector>\n')
        io.open(os.path.join(RES, f"piece_{side}_{p}.xml"), "w", encoding="utf-8").write(xml)
print("wrote 12 piece drawables")
