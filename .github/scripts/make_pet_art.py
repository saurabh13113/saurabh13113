#!/usr/bin/env python3
"""Generate the animated pixel-art cat SVGs (idle / happy / sleepy).

Usage: python make_pet_art.py [output_dir]   (default: pet)

Edit the palette or sprite below and re-run to restyle the cat. Output is plain
SVG with CSS animations, which GitHub plays inside <img> tags (no JavaScript).
"""
import os
import sys

U = 10  # one sprite pixel = 10 SVG units
COLS, ROWS = 32, 20  # scene size in sprite pixels (320 x 200)
CAT_X, CAT_Y = 8, 3  # where the 16x16 cat sits in the scene

PAL = {
    "W": "#e6f0ff",  # fur
    "S": "#b9cbe8",  # fur shade
    "P": "#f4a6c0",  # ears, nose, blush
    "B": "#58a6ff",  # collar (site accent blue)
    "K": "#1c1c22",  # eyes, mouth
    "Y": "#ffca28",  # collar tag, kibble
    "R": "#ff6b9d",  # hearts
    "Z": "#cfe3ff",  # sleepy Zs, stars
    "M": "#f2e6b1",  # moon
    "G": "#a371f7",  # yarn
    "F": "#2b3a67",  # floor
}

BODY = [
    "................",
    "..WW........WW..",
    ".WPPW......WPPW.",
    ".WPPWWWWWWWWPPW.",
    ".WWWWWWWWWWWWWS.",
    ".WWWWWWWWWWWWWS.",
    ".WWWWWWWWWWWWWS.",
    ".WWWWWWWWWWWWWS.",
    ".WWWWWWWWWWWWWS.",
    ".WWWWWWWWWWWWWS.",
    "..WWWWWWWWWWWS..",
    "..BBBBBBBBBBBB..",
    "..WWWWYYWWWWWS..",
    ".WWWWWWWWWWWWWS.",
    ".WWWWWWWWWWWWWS.",
    ".WWWW..WW..WWWS.",
]

# Each overlay is a list of (x, y, colour-key) in sprite coordinates.
EYES_OPEN = [(3, 6, "K"), (4, 6, "K"), (3, 7, "B"), (4, 7, "B"),
             (11, 6, "K"), (12, 6, "K"), (11, 7, "B"), (12, 7, "B")]
EYES_CLOSED = [(3, 7, "K"), (4, 7, "K"), (11, 7, "K"), (12, 7, "K")]
EYES_HAPPY = [(3, 7, "K"), (4, 6, "K"), (5, 7, "K"), (10, 7, "K"), (11, 6, "K"), (12, 7, "K")]
BLUSH = [(2, 8, "P"), (3, 8, "P"), (12, 8, "P"), (13, 8, "P")]
FACE = [(7, 8, "P"), (8, 8, "P"), (6, 9, "K"), (7, 10, "K"), (8, 10, "K"), (9, 9, "K"),
        (0, 8, "S"), (15, 8, "S")]  # nose, smile, whiskers

# Tail is drawn in scene coordinates (right of the cat), two frames.
TAIL_UP = [(23, 17, "W"), (24, 16, "W"), (24, 15, "W"), (25, 14, "W"), (25, 13, "W")]
TAIL_DOWN = [(23, 17, "W"), (24, 17, "W"), (25, 16, "W"), (25, 15, "W"), (26, 15, "S")]

HEART = [".R.R.", "RRRRR", ".RRR.", "..R.."]
ZEE = ["ZZZ", "..Z", ".Z.", "Z..", "ZZZ"]


def rect(x, y, key, extra=""):
    return (f'<rect x="{x * U}" y="{y * U}" width="{U}" height="{U}" '
            f'fill="{PAL[key]}"{extra}/>')


def cells(points, dx=0, dy=0):
    return "".join(rect(x + dx, y + dy, k) for x, y, k in points)


def glyph(rows, x, y):
    out = []
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                out.append(rect(x + i, y + j, ch))
    return "".join(out)


def body():
    pts = [(i, j, ch) for j, row in enumerate(BODY) for i, ch in enumerate(row) if ch != "."]
    return cells(pts, CAT_X, CAT_Y)


def scene(state):
    happy, sleepy = state == "happy", state == "sleepy"
    bob = {"idle": "1.6s", "happy": "0.8s", "sleepy": "3.2s"}[state]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {COLS * U} {ROWS * U}" '
        f'width="{COLS * U}" height="{ROWS * U}" shape-rendering="crispEdges" role="img" '
        f'aria-label="A pixel-art cat that is {state}">',
        f"<title>A pixel-art cat that is {state}</title>",
        "<style>"
        f".bob{{animation:bob {bob} step-end infinite}}"
        "@keyframes bob{0%{transform:translateY(0)}50%{transform:translateY(5px)}}"
        ".ob{animation:ob 4s step-end infinite}"
        "@keyframes ob{0%{opacity:1}90%{opacity:0}94%{opacity:1}}"
        ".cb{animation:cb 4s step-end infinite}"
        "@keyframes cb{0%{opacity:0}90%{opacity:1}94%{opacity:0}}"
        ".t1{animation:t1 1.6s step-end infinite}@keyframes t1{0%{opacity:1}50%{opacity:0}}"
        ".t2{animation:t2 1.6s step-end infinite}@keyframes t2{0%{opacity:0}50%{opacity:1}}"
        ".rise{animation:rise 2.4s linear infinite}"
        "@keyframes rise{0%{transform:translateY(10px);opacity:0}25%{opacity:1}"
        "100%{transform:translateY(-16px);opacity:0}}"
        ".tw{animation:tw 3s step-end infinite}@keyframes tw{0%{opacity:1}50%{opacity:.25}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        "</style>",
        f'<rect width="{COLS * U}" height="{ROWS * U}" rx="12" fill="#1c1c22"/>',
        f'<rect x="1" y="1" width="{COLS * U - 2}" height="{ROWS * U - 2}" rx="11" '
        f'fill="none" stroke="#2b3a67" stroke-width="2"/>',
        # floor
        f'<rect x="0" y="{(ROWS - 1) * U}" width="{COLS * U}" height="{U}" fill="{PAL["F"]}"/>',
        # moon and stars
        glyph(["MMM", "MMM", "MM."], 27, 2),
        f'<g class="tw">{rect(3, 2, "Z")}{rect(20, 1, "Z")}</g>',
        f'<g class="tw" style="animation-delay:-1.5s">{rect(6, 5, "Z")}{rect(30, 7, "Z")}</g>',
        # yarn ball and kibble bowl
        glyph([".GG.", "GGGG", "GGGG", ".GG."], 3, 15),
        rect(4, 16, "Z"),
        glyph(["Y.Y.", "WWWW", ".WW."], 27, 16),
    ]

    # the cat (inside the bobbing group)
    parts.append('<g class="bob">')
    parts.append(f'<g class="t1">{cells(TAIL_UP)}</g>')
    parts.append(f'<g class="t2" opacity="0">{cells(TAIL_DOWN)}</g>')
    parts.append(body())
    parts.append(cells(FACE, CAT_X, CAT_Y))
    if happy:
        parts.append(cells(EYES_HAPPY, CAT_X, CAT_Y))
        parts.append(cells(BLUSH, CAT_X, CAT_Y))
    elif sleepy:
        parts.append(cells(EYES_CLOSED, CAT_X, CAT_Y))
    else:
        parts.append(f'<g class="ob">{cells(EYES_OPEN, CAT_X, CAT_Y)}</g>')
        parts.append(f'<g class="cb" opacity="0">{cells(EYES_CLOSED, CAT_X, CAT_Y)}</g>')
    parts.append("</g>")

    # floating extras
    if happy:
        for i, (x, y) in enumerate([(11, 0), (17, 0), (22, 1)]):
            parts.append(f'<g class="rise" style="animation-delay:-{i * 0.8}s">'
                         f'{glyph(HEART, x, y)}</g>')
    if sleepy:
        for i, (x, y) in enumerate([(23, 1), (19, 0)]):
            parts.append(f'<g class="rise" style="animation-delay:-{i * 1.2}s">'
                         f'{glyph(ZEE, x, y)}</g>')

    parts.append("</svg>")
    return "".join(parts)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "pet"
    os.makedirs(out, exist_ok=True)
    for state in ("idle", "happy", "sleepy"):
        path = os.path.join(out, f"pixel-{state}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(scene(state))
        print("wrote", path)


if __name__ == "__main__":
    main()
