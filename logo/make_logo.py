"""Draws the Simorgh logo and writes every file that carries it.

The mark is a bird with raised wings and a crested, hooked-beak head, with a
king standing in front of it: gold on near-black, two colours, no gradients.
It is built from a few large shapes so it still reads as a launcher icon at
48px; the fine detail (feather separations, the eye) is cut out of those
shapes rather than drawn on top, and simply disappears when small.

    python logo/make_logo.py

writes

    logo/simorgh-icon.svg          the mark on its rounded dark square
    logo/simorgh-mark.svg          the mark alone, on a transparent background
    gui/src-tauri/app-icon.svg     source for `tauri icon`
    gui/public/simorgh.svg         the desktop app's favicon and header logo
    android/.../ic_launcher_foreground.xml, ic_launcher_background.xml

The PNG icons (Tauri's icons/ and Android's mipmap-*/) are rasterised from
simorgh-icon.svg; see README.md in this folder.
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BG = "#0f0d0a"
GOLD = "#e2b766"


def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def P(p):
    return f"{f(p[0])},{f(p[1])}"


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def mirror_pt(p, cx=256):
    return (2 * cx - p[0], p[1])


# ---- wings -----------------------------------------------------------------
# Feather tips along the left wing's outer edge, top to bottom. The right
# wing is the mirror image.
TIPS = [(104, 34), (64, 84), (42, 140), (34, 198), (40, 256), (60, 308),
        (94, 352), (138, 386)]
SHOULDER = (228, 246)
BODY_LOW = (226, 352)
HUB = (214, 250)  # the feather separations all aim here
NOTCH_DEPTH = 0.26


def wing(mirror):
    m = mirror_pt if mirror else (lambda p: p)
    tips = [m(p) for p in TIPS]
    hub = m(HUB)
    d = [f"M{P(m(SHOULDER))}",
         # leading edge, bowing in towards the head
         f"C{P(m((214, 160)))} {P(m((150, 70)))} {P(tips[0])}"]
    notches = []
    for a, b in zip(tips, tips[1:]):
        n = lerp(lerp(a, b, 0.5), hub, NOTCH_DEPTH)
        notches.append(n)
        # each feather's edges bow outward, away from the hub
        qa = lerp(lerp(a, n, 0.5), hub, -0.10)
        qb = lerp(lerp(n, b, 0.5), hub, -0.12)
        d.append(f"Q{P(qa)} {P(n)} Q{P(qb)} {P(b)}")
    last, low = tips[-1], m(BODY_LOW)
    d.append(f"Q{P(lerp(lerp(last, low, 0.5), hub, -0.08))} {P(low)}Z")
    cuts = " ".join(f"M{P(n)} L{P(lerp(n, hub, 0.6))}" for n in notches)
    return " ".join(d), cuts


# ---- head ------------------------------------------------------------------
HEAD = ("M214,262 C206,220 214,176 232,146 C240,130 236,114 238,100 "
        "C242,76 264,62 288,64 C306,66 320,76 326,92 "
        "C344,96 358,112 360,134 C352,126 342,122 334,122 "
        "C334,128 328,132 320,132 C306,134 298,144 296,158 "
        "C294,190 304,228 298,262Z")
EYE = "M290,88 Q301,81 310,90 Q299,97 290,88Z"


def plume(root, tip, width, bend):
    """A pointed leaf from root to tip, bowed `bend` to one side."""
    (rx, ry), (tx, ty) = root, tip
    L = math.hypot(tx - rx, ty - ry)
    nx, ny = -(ty - ry) / L, (tx - rx) / L
    mx, my = (rx + tx) / 2 + nx * bend, (ry + ty) / 2 + ny * bend
    a = (mx + nx * width, my + ny * width)
    b = (mx - nx * width, my - ny * width)
    return f"M{P(root)} Q{P(a)} {P(tip)} Q{P(b)} {P(root)}Z"


CREST = [plume((262, 78), (214, 10), 15, 16),
         plume((250, 92), (176, 44), 15, 14),
         plume((242, 110), (162, 98), 13, 8)]

# ---- king ------------------------------------------------------------------
# A Staunton king, drawn around x=0 from the top of its cross, 254 tall.
KING = ("M-8,0 h16 v14 h14 v15 h-14 v9 "
        "C24,40 38,44 38,56 C38,68 28,76 20,80 h8 v14 h-12 "
        "C16,130 26,166 40,192 h12 v17 h-6 C52,218 68,226 70,240 v14 H-70 v-14 "
        "C-68,226 -52,218 -46,209 h-6 v-17 h12 "
        "C-26,166 -16,130 -16,94 h-12 v-14 h8 "
        "C-28,76 -38,68 -38,56 C-38,44 -24,40 -8,38 v-9 h-14 v-15 h14Z")
KING_AT = (256, 214, 0.9)  # x, top, scale


# ---- the mark as layers ----------------------------------------------------
# Each layer is (path, ink, stroke width or None, transform or None). "gold"
# is the mark; "cut" is a gap in it -- painted with the background on an
# opaque icon, punched out as transparency in the stand-alone mark. A shape
# with a cut outline is listed as its cut stroke first, then its fill: that
# is what separates the head from the wings and the king from everything.
def layers():
    out = []
    for mirror in (False, True):
        d, cuts = wing(mirror)
        out.append((d, "gold", None, None))
        out.append((cuts, "cut", 6, None))
    for d in CREST + [HEAD]:
        out.append((d, "cut", 7, None))
        out.append((d, "gold", None, None))
    out.append((EYE, "gold-cut", None, None))
    out.append((KING, "cut", 12 / KING_AT[2], KING_AT))
    out.append((KING, "gold", None, KING_AT))
    return out


def svg_layer(d, ink, stroke, tf, colours):
    fill_c, cut_c = colours
    t = f' transform="translate({tf[0]},{tf[1]}) scale({tf[2]})"' if tf else ""
    if ink == "gold":
        return f'<path{t} d="{d}" fill="{fill_c}"/>'
    if ink == "gold-cut":  # a filled hole, like the eye
        return f'<path{t} d="{d}" fill="{cut_c}"/>'
    return (f'<path{t} d="{d}" fill="none" stroke="{cut_c}" stroke-width="{f(stroke)}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def icon_svg(inset=0.88, rx=112):
    s = inset
    o = [f'<g transform="translate({f(256 * (1 - s))},{f(256 * (1 - s))}) scale({s})">']
    o += [svg_layer(*L, (GOLD, BG)) for L in layers()]
    o.append("</g>")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">'
            f'<rect width="512" height="512" rx="{rx}" fill="{BG}"/>' + "".join(o) + "</svg>\n")


def mark_svg():
    # Cuts become real transparency: the layers are drawn into a mask, white
    # for the mark and black for the gaps, and the gold shows through it.
    body = "".join(svg_layer(*L, ("#fff", "#000")) for L in layers())
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">'
            '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">'
            f'<rect width="512" height="512" fill="#000"/>{body}</mask>'
            f'<rect width="512" height="512" fill="{GOLD}" mask="url(#m)"/></svg>\n')


def android_colour(hex_rgb):
    return "#FF" + hex_rgb[1:].upper()


def android_foreground():
    # An adaptive icon is 108dp and a launcher mask may keep only the middle
    # 66dp circle, so the 512 mark is scaled into that safe zone.
    scale = 66 / 512 * 0.98
    off = (108 - 512 * scale) / 2
    rows = []
    for d, ink, stroke, tf in layers():
        if ink == "gold":
            attrs = f'android:fillColor="{android_colour(GOLD)}"'
        elif ink == "gold-cut":
            attrs = f'android:fillColor="{android_colour(BG)}"'
        else:
            attrs = (f'android:strokeColor="{android_colour(BG)}" android:strokeWidth="{f(stroke)}" '
                     'android:strokeLineCap="round" android:strokeLineJoin="round"')
        path = f'<path android:pathData="{d}" {attrs} />'
        if tf:
            path = (f'<group android:translateX="{tf[0]}" android:translateY="{tf[1]}" '
                    f'android:scaleX="{tf[2]}" android:scaleY="{tf[2]}">{path}</group>')
        rows.append("        " + path)
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            "<!-- Generated by logo/make_logo.py; edit that, not this. -->\n"
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="108dp" android:height="108dp"\n'
            '    android:viewportWidth="108" android:viewportHeight="108">\n'
            f'    <group android:translateX="{f(off)}" android:translateY="{f(off)}"\n'
            f'        android:scaleX="{scale:.5f}" android:scaleY="{scale:.5f}">\n'
            + "\n".join(rows) + "\n    </group>\n</vector>\n")


def android_background():
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            "<!-- Generated by logo/make_logo.py; edit that, not this. -->\n"
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="108dp" android:height="108dp"\n'
            '    android:viewportWidth="108" android:viewportHeight="108">\n'
            f'    <path android:pathData="M0,0 h108 v108 h-108 z" android:fillColor="{android_colour(BG)}" />\n'
            "</vector>\n")


def write(rel, text):
    p = ROOT / rel
    p.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", rel)


if __name__ == "__main__":
    icon = icon_svg()
    write("logo/simorgh-icon.svg", icon)
    write("logo/simorgh-mark.svg", mark_svg())
    write("gui/src-tauri/app-icon.svg", icon)
    write("gui/public/simorgh.svg", icon)
    res = "android/app/src/main/res/drawable/"
    write(res + "ic_launcher_foreground.xml", android_foreground())
    write(res + "ic_launcher_background.xml", android_background())
