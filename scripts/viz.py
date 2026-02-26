#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
"""
Polyomino Packing Visualizer — Light / Bright Theme
Usage:
    uv run viz.py <input.in> <output.out> [--cell N] [--out packing.png] [--no-labels]

Output format expected (Xi Yi Ri Fi):
    Line 1: W H
    Then n lines: Xi Yi Ri Fi
        Ri in {0,1,2,3} = clockwise 90° rotations
        Fi in {0,1}     = reflect across y-axis (before rotation)
"""

import sys
import argparse
import random

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required:  uv pip install pillow  or  pip install pillow")


# ──────────────────────────────────────────────
# Geometry
# ──────────────────────────────────────────────

def rot90cw(x, y, r):
    r &= 3
    if r == 0: return  x,  y
    if r == 1: return  y, -x
    if r == 2: return -x, -y
    return -y,  x


def apply_transform(cells, X, Y, R, F):
    result = []
    for (x, y) in cells:
        if F:
            x = -x
        x, y = rot90cw(x, y, R)
        result.append((x + X, y + Y))
    return result


# ──────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────

def parse_input(text):
    tok = text.split()
    i = 0
    n = int(tok[i]); i += 1
    shapes = []
    for _ in range(n):
        k = int(tok[i]); i += 1
        cells = []
        for _ in range(k):
            x, y = int(tok[i]), int(tok[i + 1]); i += 2
            cells.append((x, y))
        shapes.append(cells)
    return shapes


def parse_output(text, n):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    W, H = map(int, lines[0].split())
    if len(lines) - 1 < n:
        raise ValueError(f"Expected {n} transform lines, got {len(lines) - 1}.")
    transforms = []
    for i in range(1, n + 1):
        parts = lines[i].split()
        X, Y, R, F = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        transforms.append((X, Y, R, F))
    return W, H, transforms


# ──────────────────────────────────────────────
# Colors (adjacency-aware, bright saturated palette)
# ──────────────────────────────────────────────

def _hsl_to_rgb8(h, s, l):
    """h in [0,360), s and l in [0,1] → (r,g,b) each in [0,255]."""
    h /= 360.0
    if s == 0:
        v = int(l * 255)
        return (v, v, v)
    def _h2(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    return (
        round(_h2(p, q, h + 1/3) * 255),
        round(_h2(p, q, h)       * 255),
        round(_h2(p, q, h - 1/3) * 255),
    )


def _hue_dist(a, b):
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def assign_colors(n, adjacency, seed_hue=None):
    if seed_hue is None:
        seed_hue = random.uniform(0, 360)
    GOLDEN  = 137.508
    MIN_GAP = 36
    # Lightness tiers — bright but not washed out, matching the screenshot palette
    LIGHTS  = [58, 50, 66]   # % — three tiers for adjacent-piece separation
    SAT     = 82             # % saturation

    hues, lights = {}, {}
    order = sorted(range(1, n + 1), key=lambda x: -len(adjacency.get(x, set())))
    for idx, pid in enumerate(order):
        h = (seed_hue + idx * GOLDEN) % 360
        for _ in range(720):
            if all(
                _hue_dist(h, hues[nb]) >= MIN_GAP
                for nb in adjacency.get(pid, set())
                if nb in hues
            ):
                break
            h = (h + GOLDEN) % 360
        hues[pid] = h
        used_L = {lights[nb] for nb in adjacency.get(pid, set()) if nb in lights}
        lights[pid] = next((L for L in LIGHTS if L not in used_L), LIGHTS[0])

    return {
        pid: _hsl_to_rgb8(hues.get(pid, 0), SAT / 100, lights.get(pid, LIGHTS[0]) / 100)
        for pid in range(1, n + 1)
    }


# ──────────────────────────────────────────────
# Font helper
# ──────────────────────────────────────────────

def _load_font(size):
    for path in [
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


# ──────────────────────────────────────────────
# Main rendering
# ──────────────────────────────────────────────

def visualize(input_text, output_text, cell_size=10, out_path="packing.png",
              draw_labels=True, seed=None):
    shapes = parse_input(input_text)
    n = len(shapes)
    W, H, transforms = parse_output(output_text, n)

    # Apply transforms → build per-piece cell lists
    piece_cells: dict[int, list[tuple[int, int]]] = {}
    for i, (cells, (X, Y, R, F)) in enumerate(zip(shapes, transforms)):
        pid = i + 1
        piece_cells[pid] = apply_transform(cells, X, Y, R, F)

    # Build adjacency
    occ: dict[tuple[int, int], int] = {}
    for pid, cells in piece_cells.items():
        for cell in cells:
            occ[cell] = pid
    adjacency: dict[int, set[int]] = {pid: set() for pid in piece_cells}
    for (x, y), a in occ.items():
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = occ.get((x + dx, y + dy))
            if b and b != a:
                adjacency[a].add(b)
                adjacency[b].add(a)

    colors = assign_colors(n, adjacency, seed_hue=float(seed) if seed is not None else None)

    # Stats
    total_cells = sum(len(c) for c in piece_cells.values())
    fill_ratio  = total_cells / (W * H) if W * H else 0

    # ── Layout ───────────────────────────────────
    BAR_H = 24
    PAD   = max(6, cell_size)
    IW    = W * cell_size + PAD * 2
    IH    = BAR_H + H * cell_size + PAD * 2
    OX    = PAD
    OY    = BAR_H + PAD

    img = Image.new("RGB", (IW, IH), (255, 255, 255))
    d   = ImageDraw.Draw(img)

    # ── Fill-ratio bar ────────────────────────────
    d.rectangle([0, 0, IW - 1, BAR_H - 1], fill=(245, 245, 245))
    bar_w = round(IW * fill_ratio)
    if bar_w > 0:
        d.rectangle([0, 0, bar_w - 1, BAR_H - 1], fill=(240, 152, 42))
    d.line([(0, BAR_H - 1), (IW - 1, BAR_H - 1)], fill=(210, 210, 210), width=1)

    bar_font = _load_font(13)
    pct_text = f"{fill_ratio:.0%}"
    bb = bar_font.getbbox(pct_text)
    tx = IW - (bb[2] - bb[0]) - 6
    ty = (BAR_H - (bb[3] - bb[1])) // 2 - bb[1]
    d.text((tx, ty), pct_text, font=bar_font, fill=(60, 35, 5))

    # ── Piece cells ───────────────────────────────
    GAP = 1   # white gap in pixels on each side of a cell
    for pid, cells in piece_cells.items():
        r, g, b = colors[pid]
        for (gx, gy) in cells:
            if not (0 <= gx < W and 0 <= gy < H):
                continue
            cx = OX + gx * cell_size
            cy = OY + gy * cell_size
            d.rectangle(
                [cx + GAP, cy + GAP, cx + cell_size - GAP - 1, cy + cell_size - GAP - 1],
                fill=(r, g, b)
            )

    # ── Outer border ──────────────────────────────
    d.rectangle(
        [OX, OY, OX + W * cell_size, OY + H * cell_size],
        outline=(190, 190, 190), width=1
    )

    # ── Piece ID labels ───────────────────────────
    if draw_labels and cell_size >= 12:
        font_size = max(7, int(cell_size * 0.50))
        font = _load_font(font_size)
        cell_set_map = {pid: set(map(tuple, cells)) for pid, cells in piece_cells.items()}

        for pid, cells in piece_cells.items():
            if not cells:
                continue
            # Pick most-interior cell for the label
            cs = cell_set_map[pid]
            best, best_sc = cells[0], -1
            for (x, y) in cells:
                sc = sum(
                    1 for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if (x + dx, y + dy) in cs
                )
                if sc > best_sc:
                    best_sc, best = sc, (x, y)

            gx, gy = best
            if not (0 <= gx < W and 0 <= gy < H):
                continue
            cx = OX + gx * cell_size
            cy = OY + gy * cell_size

            label = str(pid)
            r, g, b = colors[pid]
            # Perceived luminance → choose contrasting text colour
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            text_col = (25, 25, 25) if lum > 140 else (255, 255, 255)

            bb  = font.getbbox(label)
            tw  = bb[2] - bb[0]
            th  = bb[3] - bb[1]
            # Centre inside the coloured area (minus gap)
            inner = cell_size - GAP * 2
            tx = cx + GAP + (inner - tw) // 2 - bb[0]
            ty = cy + GAP + (inner - th) // 2 - bb[1]
            d.text((tx, ty), label, font=font, fill=text_col)

    img.save(out_path)
    print(f"Saved {out_path}  ({IW}×{IH} px, cell={cell_size}px, {W}×{H} grid, fill={fill_ratio:.1%})")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Visualize polyomino packing output as a bright/colourful PNG."
    )
    ap.add_argument("input",  help="Input file (polyomino definitions)")
    ap.add_argument("output", help="Output file (Xi Yi Ri Fi transforms)")
    ap.add_argument("--cell", type=int, default=10,
                    help="Cell size in pixels (default: 10)")
    ap.add_argument("--out",  default="packing.png",
                    help="Output PNG path (default: packing.png)")
    ap.add_argument("--no-labels", action="store_true",
                    help="Suppress piece ID labels")
    ap.add_argument("--seed", type=int, default=None,
                    help="Random seed for colour hue start")
    args = ap.parse_args()

    with open(args.input)  as f: inp = f.read()
    with open(args.output) as f: out = f.read()

    visualize(
        inp, out,
        cell_size=args.cell,
        out_path=args.out,
        draw_labels=not args.no_labels,
        seed=args.seed,
    )
