"""Photogrammetry posters: drone photos to a map, one concept per poster, one folder per pipeline step.

Minimal like vision.py: one word, one drawing, one formula. The steps follow the pipeline in
github.com/ibadrather/photogrammetry: ingest → select → extract → sfm → georef → dense → dsm → ortho.
Numbers are from its Brighton Beach sample run (18 photos, DJI Phantom 3, 45 m up) unless a poster says
simulated. Every drawing is computed from the formula printed under it.

ingest:   join. manifest. early.
select:   footprint. overlap. gsd. thin.
extract:  gop. jpeg. shrink.
sfm:      keypoint. descriptor. ratio. pairs. ransac. islands. grow. track. reproject. bundle. robust.
          gauge. focal. invert. dome. priors.
georef:   helmert. residual. offset. hinge. enu. utm. datum. float.
dense:    undistort. views. depth. ncc. propagate. baseline. agree. mirror.
dsm:      median. spacing. spike. fill. corner. ndsm. nmad.
ortho:    backward. lean. slant. ghost. seams. gain. blend. true.

Run:  uv run --no-project --with fonttools --with brotli python src/photogrammetry.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from drone import missing_glyphs  # noqa: E402
from posters import CODE_Y, M, W, code_rule  # noqa: E402
from sensors import arrow  # noqa: E402
from vision import dim, ellipse, gray, label, mix  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "photogrammetry"
CX, CY = W / 2, 640  # centre of the drawing


# ============================================================================
# shared furniture
# ============================================================================
def cam(svg: Svg, x, y, w=56, plane=P.lavender_60, ink=P.black, r=8, gap=18, up=False):
    """A camera seen from the side: its centre, and its image plane between it and the scene (below, or above)."""
    yp = y - gap if up else y + gap
    svg.line(x - w / 2, yp, x + w / 2, yp, plane, 4, stroke_linecap="round")
    svg.circle(x, y, r, ink)


def ground(svg: Svg, y, x0=M + 20, x1=W - M - 20, ink=P.black, width=2):
    svg.line(x0, y, x1, y, ink, width)


def run(svg: Svg, title, kicker, src, dark=False, size=22):
    """Title, kicker, the code rule and the code: the same furniture on every poster."""
    svg.frame(title, kicker, dark=dark, title_fill=P.white if dark else None)
    code_rule(svg, P.lavender if dark else P.blue)
    svg.code(M, CODE_Y, src, "py", size, dark=dark)
    return svg


def lerp(a, b, t):
    return a + (b - a) * t


def ramp(t: float) -> str:
    """A sequential brand ramp, 0 = Cornflower Blue, 1 = pale lavender."""
    t = max(0.0, min(1.0, t))
    return mix(P.blue, P.lavender, t / 0.5) if t < 0.5 else mix(P.lavender, P.lavender_20, (t - 0.5) / 0.5)


# ============================================================================
# 1 ingest
# ============================================================================
def join() -> Svg:
    """The frame table: media and manifest joined one to one; every mismatch is listed, not the first."""
    svg = Svg(P.white)
    images = ["0011", "0012", "0013", "0014", "0015", "0016"]
    pos = {k: (-91.99456 + 0.00011 * i, 46.84261 - 0.00004 * i, 39.8 + 0.3 * (i % 3))
           for i, k in enumerate(["0011", "0012", "0013", "0014", "0015", "0016", "0018"])}
    manifest = {k: pos[k] for k in ("0011", "0012", "0014", "0016", "0018")} | {"0013": None}
    keys = sorted(set(images) | set(manifest))
    lx, tw, th, rx, y0, dy = 130, 232, 58, 708, 330, 92

    svg.text(lx, y0 - 46, "images/", "code", 20, P.black)
    svg.text(rx - 10, y0 - 46, "manifest.geojson", "code", 20, P.black)
    for i, k in enumerate(keys):
        y = y0 + i * dy
        has_img, has_feat = k in images, k in manifest
        if has_img:
            svg.rect(lx, y, tw, th, P.lavender_20, rx=6, stroke=P.blue if not has_feat else P.lavender, stroke_width=3 if not has_feat else 1.5)
            label(svg, lx + tw / 2, y + th / 2 + 7, f"DJI_{k}.JPG", P.black, size=19)
        else:
            svg.rect(lx, y, tw, th, "none", rx=6, stroke=P.blue, stroke_width=2, stroke_dasharray="6 6")
            label(svg, lx + tw / 2, y + th / 2 + 7, "no image", P.blue, size=19)
        cy = y + th / 2
        if has_feat:
            g = manifest[k]
            if g is None:
                svg.circle(rx, cy, 9, P.white, stroke=P.teal, stroke_width=3)
                label(svg, rx + 26, cy + 6, "null  (no fix: allowed)", P.black_60, "start", 17)
            else:
                svg.circle(rx, cy, 10, P.teal, **({"stroke": P.blue, "stroke_width": 4} if not has_img else {}))
                label(svg, rx + 26, cy + 6, f"{g[0]:.4f}, {g[1]:.4f}, {g[2]:.1f}", P.black_60, "start", 17)
        else:
            svg.circle(rx, cy, 9, "none", stroke=P.blue, stroke_width=2, stroke_dasharray="4 4")
            label(svg, rx + 26, cy + 6, "no feature", P.blue, "start", 17)
        if has_img and has_feat:
            svg.line(lx + tw + 8, cy, rx - 18, cy, P.teal, 2.5, stroke_linecap="round")

    return run(svg, "join.", "one frame, one position · one to one", """
errors = set(images) ^ set(manifest)    # every mismatch, at once""")


def manifest() -> Svg:
    """The manifest: one GeoJSON Point per frame, the flight seen from above before anything runs."""
    svg = Svg(P.cream)
    rng = random.Random(3)
    n, strips = 6, 3
    xs = [220 + 640 * i / (n - 1) for i in range(n)]
    pts = []
    for s in range(strips):
        row = xs if s % 2 == 0 else xs[::-1]
        pts += [(x + rng.uniform(-10, 10), 430 + 180 * s + rng.uniform(-8, 8)) for x in row]
    svg.polyline(pts, P.black_20, 2, stroke_dasharray="2 9")
    dropout = 9
    for i, (x, y) in enumerate(pts):
        if i == dropout:
            svg.circle(x, y, 11, P.cream, stroke=P.teal, stroke_width=3)
        else:
            svg.circle(x, y, 11, P.teal)
    x, y = pts[0]
    svg.circle(x, y, 20, "none", stroke=P.blue, stroke_width=3)
    label(svg, x, y - 38, "DJI_0018.JPG", P.blue, size=18)
    x, y = pts[dropout]
    label(svg, x, y + 46, "GPS dropout · null", P.black_60, size=17)
    ax, ay = 150, 950
    arrow(svg, (ax, ay), (ax + 90, ay), P.black_60, 2.5, 14)
    arrow(svg, (ax, ay), (ax, ay - 90), P.black_60, 2.5, 14)
    label(svg, ax + 104, ay + 6, "lon", P.black_60, "start", 17)
    label(svg, ax, ay - 104, "lat", P.black_60, size=17)
    label(svg, W - M - 20, ay + 6, f"{len(pts)} photos · one Point each", P.black_60, "end", 17)

    return run(svg, "manifest.", "where each frame was · before anything runs", """
"geometry": {"type": "Point", "coordinates": [lon, lat, alt]}
"geometry": null        # allowed: a GPS dropout""")


def early() -> Svg:
    """Fail fast: a bad dataset stops in a second at step 1, with every problem listed at once."""
    svg = Svg(P.black)
    steps = ["ingest", "select", "extract", "sfm", "georef", "dense", "dsm", "ortho"]
    x0, x1, y = 150, 930, 500
    xs = [lerp(x0, x1, i / (len(steps) - 1)) for i in range(len(steps))]
    svg.line(xs[0], y, xs[-1], y, P.black_80, 2, stroke_dasharray="3 9")
    for i, (x, s) in enumerate(zip(xs, steps)):
        if i == 0:
            svg.circle(x, y, 16, P.lavender)
        else:
            svg.circle(x, y, 9, P.black, stroke=P.black_80, stroke_width=2)
        label(svg, x, y + 46, s, P.white if i == 0 else P.black_60, size=17)
    label(svg, xs[0], y - 40, "1 s", P.lavender, size=19)
    label(svg, xs[-1], y - 40, "≈ 5 min", P.black_60, size=19)

    bx, by = 150, 650
    svg.rect(bx - 2, by, 4, 300, P.lavender)
    svg.text(bx + 30, by + 24, "3 problems, one run", "code", 21, P.lavender)
    errs = [("DJI_0015.JPG", "no feature in the manifest"),
            ("DJI_0018.JPG", "a feature, but no image"),
            ("DJI_0021.JPG", "camera 'fc300x' not in cameras")]
    for k, (a, b) in enumerate(errs):
        yy = by + 100 + 72 * k
        svg.text(bx + 30, yy, a, "code", 19, P.white)
        svg.text(bx + 230, yy, b, "codel", 19, P.black_60)

    return run(svg, "early.", "fail fast · every problem at once", """
if errors:
    raise StepError(errors)    # all of them, before anything is written""", dark=True)


# ============================================================================
# 2 select
# ============================================================================
PH3 = {"f": 3.61, "sw": 6.17, "ss": 3.47, "iw": 4000, "H": 45.0}  # DJI Phantom 3: focal and sensor in mm, image px, height m


def footprint() -> Svg:
    """Similar triangles: the ground a nadir frame sees is to the height what the sensor is to the focal length."""
    svg = Svg(P.white)
    f, s, H = PH3["f"], PH3["ss"], PH3["H"]
    Wm = H * s / f
    c, Hd, fd = (CX, 420), 470, 112
    k = Hd / H
    Wd, sd = Wm * k, fd * s / f
    gy, sy = c[1] + Hd, c[1] - fd
    svg.poly([c, (CX - Wd / 2, gy), (CX + Wd / 2, gy)], P.lavender_20, stroke=P.lavender, stroke_width=2, stroke_linejoin="round")
    svg.poly([c, (CX - sd / 2, sy), (CX + sd / 2, sy)], P.blue_20, stroke=P.blue_40, stroke_width=2, stroke_linejoin="round")
    ground(svg, gy, 130, 950)
    svg.line(CX - Wd / 2, gy, CX + Wd / 2, gy, P.teal, 7, stroke_linecap="round")
    svg.line(CX - sd / 2, sy, CX + sd / 2, sy, P.blue, 7, stroke_linecap="round")
    svg.circle(*c, 9, P.black)
    rx = CX + Wd / 2 + 70
    dim(svg, (rx, c[1]), (rx, gy), f"H  {H:.0f} m")
    dim(svg, (CX + 80, sy), (CX + 80, c[1]), f"f  {f} mm")
    dim(svg, (CX - Wd / 2, gy + 50), (CX + Wd / 2, gy + 50), f"W  {Wm:.0f} m", P.teal)
    label(svg, CX, sy - 22, f"s  {s} mm", P.blue, size=20)

    return run(svg, "footprint.", "what one frame sees · similar triangles", f"""
W = H * s / f      # {H:.0f} m × {s} / {f} = {Wm:.0f} m on the ground""")


def overlap() -> Svg:
    """Keep a frame once its overlap with the last kept one drops to 80 %: 1 − d / W."""
    svg = Svg(P.white)
    Wd, step, n, target = 400, 16, 32, 0.8
    xs = [290 + step * i for i in range(n)]
    kept, last = [0], 0
    for i in range(1, n):
        if 1 - (xs[i] - xs[last]) / Wd <= target + 1e-9 or i == n - 1:
            kept.append(i)
            last = i
    ty = 400
    svg.line(xs[0] - 30, ty, xs[-1] + 30, ty, P.black_20, 2)
    for i, x in enumerate(xs):
        svg.circle(x, ty, 8 if i in kept else 4, P.blue if i in kept else P.black_20)
    label(svg, xs[0] - 30, ty - 30, "video frames, in order", P.black_60, "start", 17)
    by, bh, gap = 470, 26, 52
    a, b = xs[kept[1]] - Wd / 2, xs[kept[0]] + Wd / 2
    svg.rect(a, by - 12, b - a, gap + bh + 24, P.blue_20, rx=6)
    for r, i in enumerate(kept):
        svg.rect(xs[i] - Wd / 2, by + r * gap, Wd, bh, P.lavender_20, rx=5, stroke=P.lavender, stroke_width=2)
        svg.line(xs[i], ty + 12, xs[i], by + r * gap, P.blue_40, 1.2, stroke_dasharray="3 5")
    label(svg, a - 14, by + (gap + bh) / 2 + 8, f"{1 - (xs[kept[1]] - xs[0]) / Wd:.0%}".replace("%", " %"), P.blue, "end", 22)
    dim(svg, (xs[kept[0]], ty - 70), (xs[kept[1]], ty - 70), "")
    label(svg, (xs[0] + xs[kept[1]]) / 2, ty - 86, "d", P.black_60, size=20)
    yb = by + (len(kept) - 1) * gap
    dim(svg, (xs[kept[-1]] - Wd / 2, yb + 70), (xs[kept[-1]] + Wd / 2, yb + 70), "W  footprint")
    label(svg, 84 + 20, yb + bh - 4, f"{len(kept)} of {n} kept", P.black_60, "start", 17)

    return run(svg, "overlap.", "keep a frame once the view has moved on", """
if 1 - d / W <= 0.8:     # d: distance to the last kept frame
    keep(frame)""")


def gsd() -> Svg:
    """Ground sample distance: one pixel's rays fan out to one cell on the ground, H·sw / (f·iw) across."""
    svg = Svg(P.cream)
    H, f, sw, iw = PH3["H"], PH3["f"], PH3["sw"], PH3["iw"]
    g = H * sw / (f * iw)
    c, fd, Hd, npx, pw = (CX, 400), 90, 480, 10, 16
    mag = Hd / fd
    sy, gy = c[1] - fd, c[1] + Hd
    edges = [CX - npx * pw / 2 + i * pw for i in range(npx + 1)]

    def on_ground(x):
        return CX - (x - CX) * mag

    hi = 3
    a, b = edges[hi], edges[hi + 1]
    svg.poly([(a, sy), (b, sy), (on_ground(b), gy), (on_ground(a), gy)], P.lavender_20)
    for x in edges:
        w = 2 if x in (a, b) else 1
        svg.line(x, sy, on_ground(x), gy, P.blue if x in (a, b) else P.lavender_60, w)
    for i in range(npx):
        svg.rect(edges[i], sy - 14, pw, 14, P.blue if i == hi else P.white, stroke=P.blue_40, stroke_width=1)
    ground(svg, gy, 120, 960)
    for x in edges:
        svg.line(on_ground(x), gy - 8, on_ground(x), gy + 8, P.black, 1.5)
    svg.line(on_ground(b), gy, on_ground(a), gy, P.teal, 8)
    svg.circle(*c, 8, P.black)
    label(svg, (on_ground(a) + on_ground(b)) / 2, gy + 44, f"{g * 100:.1f} cm", P.teal, size=22)
    label(svg, CX, sy - 34, f"one pixel · {sw / iw * 1000:.2f} µm", P.blue, size=19)
    dim(svg, (CX + 410, c[1]), (CX + 410, gy), f"H  {H:.0f} m")

    return run(svg, "gsd.", "one pixel on the ground · how sharp the map can be", f"""
gsd = H * sw / (f * iw)    # 45 × 6.17 / (3.61 × 4000) = {g * 100:.1f} cm""")


def thin() -> Svg:
    """Video has far more frames than overlap needs: keep one every 7.7 m and the pairs drop from ~10⁶ to 465."""
    svg = Svg(P.black)
    secs, fps, v, H = 46, 30, 5.0, 40.0
    n = secs * fps
    Wm = H * PH3["ss"] / PH3["f"]
    kept, last = [0], 0
    for i in range(1, n):
        if (i - last) * v / fps >= (1 - 0.8) * Wm or i == n - 1:
            kept.append(i)
            last = i
    x0, y0, sp = 152, 340, 17
    ks = set(kept)
    for i in range(n):
        col, row = divmod(i, fps)
        x, y = x0 + col * sp, y0 + row * sp
        if i in ks:
            svg.circle(x, y, 6.5, P.lavender)
        else:
            svg.circle(x, y, 2.6, P.black_80)
    yb = y0 + fps * sp + 10
    for t in range(0, secs + 1, 10):
        label(svg, x0 + t * sp, yb + 22, f"{t} s", P.black_60, size=16)
    label(svg, x0 - 24, y0 + 6, "↓ 30", P.black_60, "end", 15)
    svg.text(x0, yb + 84, f"{n} frames", "code", 22, P.white)
    svg.text(x0 + 220, yb + 84, f"{len(kept)} kept", "code", 22, P.lavender)
    label(svg, x0, yb + 120, f"{secs} s at {v:.0f} m/s, {H:.0f} m up · 80 % overlap", P.black_60, "start", 16)
    pa, pb = n * (n - 1) // 2, len(kept) * (len(kept) - 1) // 2

    return run(svg, "thin.", "30 frames a second · mostly the same picture", f"""
n * (n - 1) / 2     # {n} frames: {pa:,} pairs · {len(kept)} kept: {pb}""".replace(",", " "), dark=True)


# ============================================================================
# 3 extract
# ============================================================================
def gop() -> Svg:
    """Video stores few complete frames; reaching a frame means decoding from the keyframe before it. One pass beats seeking."""
    svg = Svg(P.white)
    n, g, pw, bw = 24, 8, 36, 30
    x0, base = 108, 470
    sel = [2, 3, 4, 10, 13, 14, 15]
    for i in range(n):
        x = x0 + i * pw
        if i % g == 0:
            svg.rect(x, base - 110, bw, 110, P.blue, rx=4)
            label(svg, x + bw / 2, base - 18, "I", P.white, size=18)
        else:
            svg.rect(x, base - 52, bw, 52, P.lavender_60, rx=4)
        if i in sel:
            svg.circle(x + bw / 2, base + 22, 7, P.teal)
    label(svg, x0, base - 130, "keyframe: a whole picture", P.blue, "start", 17)
    label(svg, x0 + 1 * pw, base - 70, "only what changed", P.lavender, "start", 17)

    def bar(a, b, y, fill):
        svg.rect(x0 + a * pw, y, (b - a + 1) * pw - (pw - bw), 14, fill, rx=7)

    y = 590
    seek = sum(s - g * (s // g) + 1 for s in sel)
    svg.text(x0, y - 22, f"frame by frame:  {seek} decoded", "codel", 19, P.black_60)
    for k, s in enumerate(sel):
        bar(g * (s // g), s, y + k * 24, P.lavender_60)
    y2 = y + len(sel) * 24 + 70
    svg.text(x0, y2 - 22, f"one pass:  {max(sel) + 1} decoded", "code", 19, P.teal)
    bar(0, max(sel), y2, P.teal)

    return run(svg, "gop.", "most frames are only changes · decode once", """
ffmpeg -i video.mp4 \\
  -vf "select='between(n,2,4)+eq(n,10)+between(n,13,15)'" %06d.jpg""", size=21)


def _dct8(block):
    def c(u):
        return math.sqrt(0.5) if u == 0 else 1.0

    return [[0.25 * c(u) * c(v) * sum(block[y][x] * math.cos((2 * x + 1) * u * math.pi / 16) * math.cos((2 * y + 1) * v * math.pi / 16)
                                       for y in range(8) for x in range(8)) for u in range(8)] for v in range(8)]


def _idct8(F):
    def c(u):
        return math.sqrt(0.5) if u == 0 else 1.0

    return [[0.25 * sum(c(u) * c(v) * F[v][u] * math.cos((2 * x + 1) * u * math.pi / 16) * math.cos((2 * y + 1) * v * math.pi / 16)
                        for v in range(8) for u in range(8)) for x in range(8)] for y in range(8)]


Q50 = [[16, 11, 10, 16, 24, 40, 51, 61], [12, 12, 14, 19, 26, 58, 60, 55], [14, 13, 16, 24, 40, 57, 69, 56],
       [14, 17, 22, 29, 51, 87, 80, 62], [18, 22, 37, 56, 68, 109, 103, 77], [24, 35, 55, 64, 81, 104, 113, 92],
       [49, 64, 78, 87, 103, 121, 120, 101], [72, 92, 95, 98, 112, 100, 103, 99]]


def jpeg() -> Svg:
    """JPEG on one 8×8 block: DCT, divide by the quality's table, round. High frequencies, fine detail, go first."""
    svg = Svg(P.cream)
    rng = random.Random(11)
    block = [[128 + 55 * math.sin(1.9 * x + 0.8 * y) + 35 * math.sin(0.6 * x - 2.5 * y) + rng.uniform(-22, 22)
              for x in range(8)] for y in range(8)]
    F = _dct8([[v - 128 for v in r] for r in block])
    cs = 32
    for col, q in enumerate((95, 25)):
        scale = 5000 / q if q < 50 else 200 - 2 * q
        Qs = [[max(1, (Q50[v][u] * scale + 50) // 100) for u in range(8)] for v in range(8)]
        Fq = [[round(F[v][u] / Qs[v][u]) for u in range(8)] for v in range(8)]
        rec = _idct8([[Fq[v][u] * Qs[v][u] for u in range(8)] for v in range(8)])
        kept = sum(1 for r in Fq for z in r if z)
        x0 = 170 + col * 460
        label(svg, x0 + 4 * cs, 300, f"quality {q}", P.black, size=22)
        for y in range(8):
            for x in range(8):
                svg.rect(x0 + x * cs, 330 + y * cs, cs, cs, gray(max(0, min(255, rec[y][x] + 128))))
        svg.rect(x0, 330, 8 * cs, 8 * cs, "none", stroke=P.black, stroke_width=1.5)
        y1 = 640
        for v in range(8):
            for u in range(8):
                cx, cy = x0 + u * cs + cs / 2, y1 + v * cs + cs / 2
                if Fq[v][u]:
                    s = min(cs - 6, 10 + 4 * math.log2(1 + abs(Fq[v][u] * Qs[v][u])))
                    svg.rect(cx - s / 2, cy - s / 2, s, s, P.blue, rx=3)
                else:
                    svg.circle(cx, cy, 2.5, P.black_20)
        label(svg, x0 + 4 * cs, y1 + 8 * cs + 40, f"{kept} of 64 kept", P.blue, size=19)
    label(svg, 170 - 18, 330 + 4 * cs, "pixels", P.black_60, "end", 16)
    label(svg, 170 - 18, 640 + 4 * cs, "DCT", P.black_60, "end", 16)
    label(svg, 170, 640 - 14, "coarse", P.black_60, "start", 15)
    label(svg, 170 + 8 * cs, 640 + 8 * cs + 16, "fine", P.black_60, "end", 15)

    return run(svg, "jpeg.", "8 × 8 blocks · fine detail goes first", """
img.save(path, "JPEG", quality=95)     # matching works on fine detail
""")


def shrink() -> Svg:
    """Scale every image down until its longer side is 1920 px: a quarter of the pixels, the same picture."""
    svg = Svg(P.white)
    w, h, cap = 4000, 2250, 1920
    s = cap / max(w, h)
    k = 0.2
    x0, y0 = 140, 380
    svg.rect(x0, y0, w * k, h * k, P.lavender_20, rx=4, stroke=P.lavender, stroke_width=2)
    svg.rect(x0, y0, w * s * k, h * s * k, P.blue_20, rx=4, stroke=P.blue, stroke_width=3)
    label(svg, x0, y0 - 24, f"{w} × {h} · {w * h / 1e6:.1f} MP", P.lavender, "start", 21)
    label(svg, x0 + 24, y0 + 48, f"{round(w * s)} × {round(h * s)}", P.blue, "start", 21)
    label(svg, x0 + 24, y0 + 80, f"{w * h * s * s / 1e6:.1f} MP", P.blue, "start", 21)
    label(svg, x0 + w * k - 24, y0 + h * k - 28, f"{1 / (s * s):.1f}× fewer pixels to match", P.black_60, "end", 19)
    f0 = 3.61 / 6.17 * w
    label(svg, x0, y0 + h * k + 70, f"the focal length scales with it:  {f0:.0f} px → {f0 * s:.0f} px", P.black_60, "start", 19)

    return run(svg, "shrink.", "fewer pixels, the same picture", f"""
s = 1920 / max(w, h)     # {s:.2f} · aspect kept · Lanczos · EXIF kept""")


# ============================================================================
# 4 sfm
# ============================================================================
def fit_similarity(src, dst):
    """2D Umeyama with complex numbers: the scale + rotation z and shift that best map src onto dst."""
    a = [complex(*p) for p in src]
    b = [complex(*p) for p in dst]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    z = sum((x - ma).conjugate() * (y - mb) for x, y in zip(a, b)) / sum(abs(x - ma) ** 2 for x in a)

    def apply(p):
        q = z * (complex(*p) - ma) + mb
        return q.real, q.imag

    return apply, z


def keypoint() -> Svg:
    """SIFT finds blobs at every scale; a circle per keypoint, its radius the scale, its tick the orientation."""
    svg = Svg(P.black)
    rng = random.Random(8)
    x0, x1, y0, y1, shore = 120, 960, 300, 960, 700
    svg.rect(shore, y0, x1 - shore, y1 - y0, mix(P.black, P.blue, 0.16), rx=6)
    for k in range(7):
        y = y0 + 40 + k * 90
        svg.polyline([(shore + 30 + t * 8, y + 5 * math.sin(t / 2.2 + k)) for t in range(27)], mix(P.black, P.blue, 0.3), 1.5)
    blobs = []
    while len(blobs) < 30:
        r = math.exp(rng.uniform(math.log(6), math.log(38)))
        x, y = rng.uniform(x0 + 1.6 * r, shore - 1.6 * r - 10), rng.uniform(y0 + 1.6 * r, y1 - 1.6 * r)
        if all(math.hypot(x - bx, y - by) > 1.5 * (r + br) for bx, by, br in blobs):
            blobs.append((x, y, r))
    for x, y, r in blobs:
        svg.circle(x, y, r, mix(P.black, P.white, rng.uniform(0.18, 0.4)))
    for x, y, r in blobs:
        a = rng.uniform(0, 2 * math.pi)
        R = 1.6 * r
        svg.circle(x, y, R, "none", stroke=P.lavender, stroke_width=2)
        svg.line(x, y, x + R * math.cos(a), y + R * math.sin(a), P.lavender, 2)
    label(svg, (shore + x1) / 2, (y0 + y1) / 2 + 8, "sea", P.blue_40, size=22)
    label(svg, (shore + x1) / 2, (y0 + y1) / 2 + 40, "no keypoints", P.blue_40, size=17)
    label(svg, x0, y1 + 34, f"{len(blobs)} keypoints, {min(b[2] for b in blobs):.0f} to {max(b[2] for b in blobs):.0f} px", P.black_60, "start", 17)

    return run(svg, "keypoint.", "distinctive spots, found at every scale", """
sift = cv2.SIFT_create()
kps, desc = sift.detectAndCompute(img, None)    # thousands per image""", dark=True)


def descriptor() -> Svg:
    """SIFT's descriptor: gradients of a 16×16 patch, binned into 4×4 cells of 8 directions, 128 numbers."""
    svg = Svg(P.white)

    def I(x, y):
        return 1 / (1 + math.exp(-0.9 * ((x - 7.5) + 0.6 * (y - 9)))) * 0.75 + 0.18 * math.sin(0.8 * y) * (x < 8)

    n, ps, x0, y0 = 16, 20, 130, 480
    for y in range(n):
        for x in range(n):
            svg.rect(x0 + x * ps, y0 + y * ps, ps, ps, gray(40 + 200 * I(x, y)))
    for k in range(5):
        svg.line(x0 + k * 80, y0, x0 + k * 80, y0 + 320, P.blue, 2)
        svg.line(x0, y0 + k * 80, x0 + 320, y0 + k * 80, P.blue, 2)
    hist = [[[0.0] * 8 for _ in range(4)] for _ in range(4)]
    for y in range(n):
        for x in range(n):
            gx = I(x + 0.5, y) - I(x - 0.5, y)
            gy = I(x, y + 0.5) - I(x, y - 0.5)
            m = math.hypot(gx, gy) * math.exp(-((x - 7.5) ** 2 + (y - 7.5) ** 2) / (2 * 8 ** 2))
            b = int(((math.atan2(gy, gx) % (2 * math.pi)) / (2 * math.pi)) * 8 + 0.5) % 8
            hist[y // 4][x // 4][b] += m
    top = max(v for r in hist for c in r for v in c)
    hx0, cs = 560, 96
    for cy in range(4):
        for cx in range(4):
            ox, oy = hx0 + cx * cs + cs / 2, y0 - 8 + cy * cs + cs / 2 - 32
            svg.rect(ox - cs / 2 + 3, oy - cs / 2 + 3, cs - 6, cs - 6, P.blue_20 if (cx + cy) % 2 else P.lavender_20, rx=6)
            for b, v in enumerate(hist[cy][cx]):
                L = 42 * v / top
                if L > 1.5:
                    a = b * math.pi / 4
                    svg.line(ox, oy, ox + L * math.cos(a), oy + L * math.sin(a), P.blue, 3, stroke_linecap="round")
            svg.circle(ox, oy, 3, P.blue)
    arrow(svg, (x0 + 340, y0 + 160), (hx0 - 20, y0 + 160), P.black_20, 2.5, 14)
    label(svg, x0 + 160, y0 - 24, "16 × 16 pixels", P.black_60, size=18)
    label(svg, hx0 + 2 * cs, y0 - 8 + 4 * cs - 32 + 40, "4 × 4 cells × 8 directions", P.black_60, size=18)

    return run(svg, "descriptor.", "a patch, summed up in 128 numbers", """
desc.shape == (128,)     # gradient directions, cell by cell""")


def ratio() -> Svg:
    """Lowe's ratio test: keep a match only when the best candidate is clearly better than the second best."""
    svg = Svg(P.cream)
    rows = [("a corner of a rock", [0.21, 0.52, 0.58, 0.66, 0.71, 0.78, 0.86]),
            ("a window on a facade", [0.31, 0.33, 0.36, 0.61, 0.69, 0.75, 0.9])]
    x0, x1 = 160, 920
    for k, (name, ds) in enumerate(rows):
        y = 470 + k * 300
        d1, d2 = ds[0], ds[1]
        r = d1 / d2
        ok = r < 0.8
        svg.text(x0, y - 70, name, "code", 20, P.black)
        svg.line(x0, y, x1, y, P.black_20, 2)
        for t in (0, 0.5, 1):
            svg.line(lerp(x0, x1, t), y - 6, lerp(x0, x1, t), y + 6, P.black_20, 2)
            label(svg, lerp(x0, x1, t), y + 34, f"{t:g}", P.black_60, size=15)
        for d in ds[2:]:
            svg.circle(lerp(x0, x1, d), y, 8, P.black_20)
        svg.circle(lerp(x0, x1, d2), y, 11, P.cream, stroke=P.lavender, stroke_width=3)
        svg.circle(lerp(x0, x1, d1), y, 12, P.blue)
        label(svg, lerp(x0, x1, d1), y - 26, "d1", P.blue, size=17)
        label(svg, lerp(x0, x1, d2) + (14 if not ok else 0), y - 26, "d2", P.lavender, size=17)
        verdict = f"d1 / d2 = {r:.2f}  ·  {'keep' if ok else 'drop'}"
        label(svg, x1, y - 70 + 2, verdict, P.teal if ok else P.black_60, "end", 19)
    label(svg, x0, 470 + 300 + 80, "descriptor distance to every candidate in the other image", P.black_60, "start", 16)

    return run(svg, "ratio.", "the best must clearly beat the second best", """
keep = d1 < 0.8 * d2     # Lowe 2004 · drops lookalikes""")


def pairs() -> Svg:
    """Which images to match: all pairs, the next few in capture order, or the ones whose positions are close."""
    svg = Svg(P.white)
    n2 = 8
    order = [(i, 0) for i in range(n2)] + [(n2 - 1 - i, 1) for i in range(n2)]

    def place(c, s, cy):
        return 220 + 640 * c / (n2 - 1), cy - 40 + 80 * s

    rows = [("exhaustive", lambda i, j, a, b: True),
            ("sequential · next 3", lambda i, j, a, b: abs(i - j) <= 3),
            ("spatial · close in position", lambda i, j, a, b: math.dist(a, b) <= 130)]
    for k, (name, keep) in enumerate(rows):
        cy = 420 + 215 * k
        p = [place(c, s, cy) for c, s in order]
        e = [(i, j) for i in range(len(p)) for j in range(i + 1, len(p)) if keep(i, j, p[i], p[j])]
        for i, j in e:
            svg.line(*p[i], *p[j], P.lavender_60, 1.3)
        for q in p:
            svg.circle(*q, 7, P.black)
        svg.text(M + 20, cy - 78, name, "codel", 18, P.black_60)
        svg.text(W - M - 20, cy - 78, f"{len(e)} pairs", "code", 18, P.blue, "end")

    return run(svg, "pairs.", "who to match with whom", """
n * (n - 1) / 2     # 100 images: 4 950 pairs · 1 000: 499 500""")


def ransac() -> Svg:
    """RANSAC: fit a model to a minimal random sample, count the matches that agree, repeat, keep the best."""
    svg = Svg(P.black)
    rng = random.Random(4)
    pts = [(x, 0.55 * x + 0.18 + rng.gauss(0, 0.018), True) for x in (rng.uniform(0.05, 0.95) for _ in range(40))]
    pts += [(rng.uniform(0, 1), rng.uniform(0, 1), False) for _ in range(26)]
    w, k, p = 40 / 66, 2, 0.99
    N = math.ceil(math.log(1 - p) / math.log(1 - w ** k))
    N8 = math.ceil(math.log(1 - p) / math.log(1 - 0.6 ** 8))
    t = 0.045

    def g(x, y):
        return 140 + 800 * x, 960 - 640 * y

    best = None
    tries = []
    for _ in range(N):
        a, b = rng.sample(pts, 2)
        if abs(b[0] - a[0]) < 1e-6:
            continue
        m = (b[1] - a[1]) / (b[0] - a[0])
        c = a[1] - m * a[0]
        n_in = sum(abs(q[1] - (m * q[0] + c)) / math.sqrt(1 + m * m) < t for q in pts)
        tries.append((m, c))
        if best is None or n_in > best[0]:
            best = (n_in, m, c, a, b)
    svg.clip_begin(140, 320, 800, 640)
    for m, c in tries:
        svg.line(*g(-0.1, m * -0.1 + c), *g(1.1, m * 1.1 + c), P.black_80, 1.5)
    n_in, m, c, a, b = best
    off = t * math.sqrt(1 + m * m)
    svg.poly([g(-0.1, m * -0.1 + c - off), g(1.1, m * 1.1 + c - off), g(1.1, m * 1.1 + c + off), g(-0.1, m * -0.1 + c + off)],
             P.lavender, opacity=0.18)
    svg.line(*g(-0.1, m * -0.1 + c), *g(1.1, m * 1.1 + c), P.lavender, 3)
    svg.clip_end()
    for x, y, _inl in pts:
        agrees = abs(y - (m * x + c)) / math.sqrt(1 + m * m) < t
        if agrees:
            svg.circle(*g(x, y), 6, P.teal_60)
        else:
            svg.circle(*g(x, y), 5, "none", stroke=P.black_60, stroke_width=2)
    for q in (a, b):
        svg.circle(*g(q[0], q[1]), 12, "none", stroke=P.white, stroke_width=2.5)
    label(svg, 140, 1000, f"{len(tries)} tries · the best: {n_in} of {len(pts)} agree", P.black_60, "start", 17)

    return run(svg, "ransac.", "fit a tiny sample, count who agrees, repeat", f"""
N = log(1 - p) / log(1 - w**k)    # tries to be {p:.0%} sure
# w {w:.1f} inliers · a line, k 2: {N} · an F-matrix, k 8: {N8}""".replace("%", " %"), dark=True)


def islands() -> Svg:
    """The view graph: verified pairs are edges; a textureless band cuts it, and the flight becomes two models."""
    svg = Svg(P.cream)
    cols, rows, band = 8, 4, 4

    def g(c, r):
        return 170 + 105 * c, 380 + 150 * r

    svg.rect(g(band, 0)[0] - 46, 320, 92, 570, P.lavender_20, rx=8)
    label(svg, g(band, 0)[0], 310, "sea", P.lavender, size=18)
    nodes = [(c, r) for c in range(cols) for r in range(rows)]
    edges = [(a, b) for a in nodes for b in nodes if a < b and max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1
             and band not in (a[0], b[0])]
    comp, cid = {}, 0
    for nd in nodes:
        if nd in comp or nd[0] == band:
            continue
        stack = [nd]
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp[u] = cid
            stack += [b if a == u else a for a, b in edges if u in (a, b)]
        cid += 1
    sizes = [sum(1 for v in comp.values() if v == i) for i in range(cid)]
    col = [P.blue, P.teal]
    for a, b in edges:
        svg.line(*g(*a), *g(*b), col[comp[a]], 2, opacity=0.45)
    for nd in nodes:
        if nd[0] == band:
            svg.circle(*g(*nd), 9, P.cream, stroke=P.lavender, stroke_width=2.5)
        else:
            svg.circle(*g(*nd), 10, col[comp[nd]])
    label(svg, g(1.5, 0)[0], 950, f"model 0 · {sizes[0]} images", P.blue, size=19)
    label(svg, g(6, 0)[0], 950, f"model 1 · {sizes[1]}", P.teal, size=19)
    label(svg, g(band, 0)[0], 950, f"{rows} lost", P.lavender, size=17)

    return run(svg, "islands.", "a gap in the matches · two models, not one", """
models = connected_components(view_graph)    # keep the largest""")


def grow() -> Svg:
    """Incremental mapping: start from two images, add the one that sees the most known points, triangulate, repeat."""
    svg = Svg(P.white)
    rng = random.Random(6)
    n = 10
    xs = [150 + 87 * i for i in range(n)]
    seq = [4, 5, 6, 3, 7, 2, 8, 1, 9, 0]
    order = {c: k for k, c in enumerate(seq)}
    pts = []
    for _ in range(44):
        x = rng.uniform(140, 940)
        pts.append((x, 820 + 34 * math.sin(x / 95) + rng.uniform(-14, 14)))
    for x, y in pts:
        seen = sorted(order[c] for c in range(n) if abs(xs[c] - x) < 190)
        step = seen[1] if len(seen) > 1 else 9
        if step == 1:
            for c in (4, 5):
                svg.line(xs[c], 440, x, y, P.lavender_20, 1.5)
        svg.circle(x, y, 6, ramp(step / (n - 1) * 0.9))
    for c in range(n):
        k = order[c]
        cam(svg, xs[c], 420, 40, ramp(k / (n - 1) * 0.9), ramp(k / (n - 1) * 0.9), 9)
        label(svg, xs[c], 380, str(k + 1), ramp(k / (n - 1) * 0.9), size=20)
    dim(svg, (xs[4], 330), (xs[5], 330), "")
    label(svg, (xs[4] + xs[5]) / 2, 316, "start", P.blue, size=17)
    label(svg, 140, 960, "points coloured by the step that triangulated them", P.black_60, "start", 16)

    return run(svg, "grow.", "start from two, add one image at a time", """
pose = cv2.solvePnPRansac(X, x, K, dist)    # next image, from known points
new = cv2.triangulatePoints(P1, P2, x1, x2)   # then its new points""", size=20)


def track() -> Svg:
    """A track: one physical point followed across images; its length is how many saw it."""
    svg = Svg(P.cream)
    n, fw, fh, y0 = 6, 128, 86, 640
    X = (CX, 340)
    fr = [(110 + 148 * i, y0) for i in range(n)]
    dots = [(fx + fw * (0.86 - 0.14 * i), fy + fh * (0.42 + 0.06 * math.sin(i))) for i, (fx, fy) in enumerate(fr)]
    for d in dots:
        svg.line(*X, *d, P.lavender_60, 1.5)
    for i, (fx, fy) in enumerate(fr):
        svg.rect(fx, fy, fw, fh, P.white, rx=4, stroke=P.black_20, stroke_width=2)
        label(svg, fx + fw / 2, fy + fh + 30, f"DJI_00{18 + i}", P.black_60, size=15)
    short = [(fr[0][0] + fw * 0.3, y0 + fh * 0.78), (fr[1][0] + fw * 0.16, y0 + fh * 0.8)]
    svg.polyline(dots, P.blue, 3, stroke_dasharray="1 7")
    svg.polyline(short, P.lavender, 2.5, stroke_dasharray="1 7")
    for d in dots:
        svg.circle(*d, 7, P.blue)
    for d in short:
        svg.circle(*d, 5, P.lavender)
    svg.circle(*X, 14, P.blue)
    label(svg, X[0] + 28, X[1] + 8, "X", P.blue, "start", 26)
    label(svg, CX, y0 + fh + 100, f"length {n}", P.blue, size=22)
    label(svg, fr[0][0], y0 + fh + 100, "length 2", P.lavender, "start", 18)
    label(svg, CX, y0 + fh + 140, "Brighton Beach: mean 4.1", P.black_60, size=17)

    return run(svg, "track.", "one point, followed through many photos", """
len(track)      # how many images saw it · 4–10+ healthy, below 3 weak""")


def reproject() -> Svg:
    """The one constraint of SfM: a 3D point, projected through a camera, must land where it was seen."""
    svg = Svg(P.white)
    X = (560, 360)
    cams = [(290, 880), (790, 880)]
    py = 880 - 80
    obs_off = [0, 30]
    for (cx, cy), off in zip(cams, obs_off):
        t = (py - cy) / (X[1] - cy)
        u = cx + (X[0] - cx) * t
        o = u + off
        svg.line(cx - 90, py, cx + 90, py, P.lavender_60, 4, stroke_linecap="round")
        svg.line(cx, cy, *X, P.blue_40, 2)
        if off:
            k = (300 - cy) / (py - cy)
            svg.line(cx, cy, cx + (o - cx) * k, 300, P.teal, 2, stroke_dasharray="6 6")
            svg.line(u, py - 22, o, py - 22, P.blue, 3)
            for xx in (u, o):
                svg.line(xx, py - 30, xx, py - 14, P.blue, 2)
            label(svg, (u + o) / 2, py - 36, "e", P.blue, size=24)
            label(svg, o + 18, py + 34, "observed", P.teal, "start", 17)
            label(svg, u - 10, py + 34, "projected", P.blue, "end", 17)
            svg.circle(u, py, 7, P.white, stroke=P.blue, stroke_width=3)
        svg.circle(o, py, 7, P.teal)
        svg.circle(cx, cy, 9, P.black)
    svg.circle(*X, 14, P.blue)
    label(svg, X[0] - 28, X[1] + 8, "X", P.blue, "end", 26)

    return run(svg, "reproject.", "a point must land where it was seen", """
e = observed - project(K, R, t, X)    # pixels · make every e small""")


def bundle() -> Svg:
    """Bundle adjustment: all cameras, all points, every ray at once, in one least-squares problem."""
    svg = Svg(P.black)
    rng = random.Random(2)
    cams = [(180 + 144 * i, 390 + rng.uniform(-14, 14)) for i in range(6)]
    pts = []
    for i in range(15):
        x = 160 + 760 * i / 14 + rng.uniform(-14, 14)
        pts.append((x, 860 + 36 * math.sin(x / 120) + rng.uniform(-18, 18)))
    rays = [(c, p) for c in cams for p in pts if abs(c[0] - p[0]) < 300]
    for c, p in rays:
        svg.line(*c, *p, P.lavender, 1.3, opacity=0.55)
    for p in pts:
        svg.circle(*p, 7, P.teal_60)
    for c in cams:
        svg.circle(*c, 9, P.white)
    label(svg, CX, 980, f"{len(cams)} cameras · {len(pts)} points · {len(rays)} rays · one problem", P.black_60, size=17)

    return run(svg, "bundle.", "every camera, every point, at once", """
minimise Σ ρ(|x_ij - π(K, R_i, t_i, X_j)|²)
# poses, points and the lens, together · solved by Ceres""", dark=True)


def robust() -> Svg:
    """A robust loss: squared error lets one bad match dominate; log(1 + r²) caps what it can cost."""
    svg = Svg(P.cream)
    x0, x1, yb, yt, rmax, cmax = 160, 920, 900, 340, 6, 12

    def g(r, c):
        return lerp(x0, x1, (r + rmax) / (2 * rmax)), yb - (yb - yt) * c / cmax

    svg.line(x0, yb, x1, yb, P.black, 2)
    svg.line(CX, yb, CX, yt - 10, P.black_20, 1.5)
    for r in range(-rmax, rmax + 1, 2):
        label(svg, g(r, 0)[0], yb + 32, f"{r}", P.black_60, size=15)
    sq = [g(r / 10, (r / 10) ** 2) for r in range(-35, 36)]
    svg.polyline(sq, P.lavender, 3, stroke_dasharray="8 7")
    ca = [g(r / 10, math.log(1 + (r / 10) ** 2)) for r in range(-60, 61)]
    svg.polyline(ca, P.blue, 4)
    ro = 5
    svg.circle(*g(ro, math.log(1 + ro * ro)), 9, P.blue)
    svg.line(*g(ro, math.log(1 + ro * ro)), g(ro, 0)[0], yb, P.black_20, 1.5, stroke_dasharray="4 5")
    arrow(svg, g(ro, 9.6), g(ro, 11.8), P.lavender, 3, 16)
    label(svg, g(ro, 0)[0] + 20, g(0, 10.4)[1], f"r² = {ro * ro}", P.lavender, "start", 19)
    label(svg, g(ro, 0)[0] - 16, g(0, math.log(1 + ro * ro))[1] - 26, f"a bad match: {math.log(1 + ro * ro):.1f}", P.blue, "end", 19)
    label(svg, g(-3.4, 0)[0], g(0, 11.6)[1], "r²", P.lavender, "end", 20)
    label(svg, g(-4.4, 0)[0], g(0, 4.4)[1], "log(1 + r²)", P.blue, "middle", 20)
    label(svg, x1, yb + 70, "reprojection error r, px", P.black_60, "end", 16)

    return run(svg, "robust.", "one bad match shouldn't win the argument", f"""
rho = log(1 + r**2)     # Cauchy: a 5 px outlier costs {math.log(1 + 25):.1f}, not 25""")


def gauge() -> Svg:
    """The gauge: shift, turn or scale the whole reconstruction and it explains the images exactly as well."""
    svg = Svg(P.white)
    cams = [(-1.5 + 0.75 * i, 1.0) for i in range(5)]
    terr = [(-1.8 + 0.45 * i, -0.9 + 0.18 * math.sin(i * 1.3)) for i in range(9)]
    copies = [((300, 480), 110, 0, P.blue, "× 1"), ((790, 430), 70, -0.5, P.lavender, "× 0.6"),
              ((610, 790), 135, 0.2, P.teal, "× 1.3")]
    for (ox, oy), s, a, col, name in copies:
        def T(p, ox=ox, oy=oy, s=s, a=a):
            x, y = p
            return ox + s * (x * math.cos(a) - y * math.sin(a)), oy - s * (x * math.sin(a) + y * math.cos(a))

        for c in cams:
            for q in terr:
                if abs(c[0] - q[0]) < 0.8:
                    svg.line(*T(c), *T(q), col, 1, opacity=0.35)
        svg.polyline([T(q) for q in terr], col, 2.5)
        for q in terr:
            svg.circle(*T(q), 4, col)
        for c in cams:
            svg.circle(*T(c), 7, col)
        tx, ty = T((2.1, 0))
        label(svg, tx + 8, ty + 6, name, col, "start", 19)
    label(svg, M + 20, 990, "same images · same reprojection error", P.black_60, "start", 18)

    return run(svg, "gauge.", "shape yes · size and place no", """
X2 = s * R @ X + t     # 7 numbers the images can't fix""")


def focal() -> Svg:
    """The focal length in pixels: a guess from the manifest, refined by bundle adjustment, and how far it moved."""
    svg = Svg(P.cream)
    fmm, smm, wpx = 3.61, 6.17, 4000
    guess, refined = fmm / smm * wpx, 2794.90
    sx0, sw = CX - 220, 440
    sy = 330
    fy = sy + sw * fmm / smm
    svg.poly([(sx0, sy), (sx0 + sw, sy), (CX, fy)], P.lavender_20, stroke=P.lavender, stroke_width=2, stroke_linejoin="round")
    svg.line(sx0, sy, sx0 + sw, sy, P.blue, 7, stroke_linecap="round")
    svg.circle(CX, fy, 9, P.black)
    for mm in range(7):
        x = sx0 + sw * mm / smm
        svg.line(x, sy - 16, x, sy - 6, P.black_60, 1.5)
        if mm % 2 == 0:
            label(svg, x, sy - 26, f"{mm} mm", P.black_60, size=14)
    for px in range(0, wpx + 1, 1000):
        x = sx0 + sw * px / wpx
        svg.line(x, sy + 6, x, sy + 16, P.blue, 1.5)
        label(svg, x, sy + 38, f"{px}", P.blue, size=14)
    dim(svg, (sx0 + sw + 50, sy), (sx0 + sw + 50, fy), f"{fmm} mm")
    label(svg, sx0 + sw + 72, (sy + fy) / 2 + 36, f"= {guess:.0f} px", P.blue, "start", 20)

    lo, hi, y = 2000, 3000, 860
    x0, x1 = 160, 920

    def gx(v):
        return lerp(x0, x1, (v - lo) / (hi - lo))

    svg.rect(gx(guess * 0.95), y - 26, gx(guess * 1.05) - gx(guess * 0.95), 52, P.lavender_20, rx=6)
    svg.line(x0, y, x1, y, P.black, 2)
    for v in range(lo, hi + 1, 250):
        svg.line(gx(v), y - 6, gx(v), y + 6, P.black, 1.5)
        label(svg, gx(v), y + 34, f"{v}", P.black_60, size=14)
    svg.circle(gx(guess), y, 10, P.lavender)
    svg.circle(gx(refined), y, 11, P.blue)
    label(svg, gx(guess), y - 42, f"guess {guess:.0f}", P.lavender, size=18)
    label(svg, gx(refined), y - 42, f"refined {refined:.0f}", P.blue, size=18)
    label(svg, (gx(guess) + gx(refined)) / 2, y + 84, f"{refined / guess - 1:+.1%} · warns above 5 %".replace("%", " %", 1), P.black_60, size=17)

    return run(svg, "focal.", "focal length, in pixels · a guess that BA refines", f"""
f_px = f_mm / sensor_mm * width_px    # 3.61 / 6.17 × 4000 = {guess:.0f}""")


def invert() -> Svg:
    """One pose, two ways to write it: world-to-camera (R, t) or camera-to-world (Rᵀ, C = −Rᵀt)."""
    svg = Svg(P.white)
    O = (230, 850)
    C = (760, 450)
    a = math.radians(118)  # the camera's z (forward) direction, page coords
    z = (math.cos(a), math.sin(a))
    x = (-z[1], z[0])
    arrow(svg, O, (O[0] + 130, O[1]), P.black, 3, 16)
    arrow(svg, O, (O[0], O[1] - 130), P.black, 3, 16)
    label(svg, O[0] + 146, O[1] + 7, "x", P.black, "start", 20)
    label(svg, O[0], O[1] - 146, "z", P.black, size=20)
    label(svg, O[0] - 16, O[1] + 34, "world", P.black_60, "start", 17)
    fr = [(C[0] + 90 * z[0] + s * 60 * x[0], C[1] + 90 * z[1] + s * 60 * x[1]) for s in (-1, 1)]
    svg.poly([C, *fr], P.lavender_20, stroke=P.lavender, stroke_width=2, stroke_linejoin="round")
    arrow(svg, C, (C[0] + 120 * z[0], C[1] + 120 * z[1]), P.teal, 3, 16)
    arrow(svg, C, (C[0] + 90 * x[0], C[1] + 90 * x[1]), P.teal, 3, 16)
    label(svg, C[0] + 140 * z[0] - 14, C[1] + 140 * z[1] + 8, "z", P.teal, "end", 20)
    label(svg, C[0] + 110 * x[0] + 6, C[1] + 110 * x[1] + 8, "x", P.teal, "start", 20)
    svg.circle(*C, 9, P.black)
    arrow(svg, (O[0] + 14, O[1] - 10), (C[0] - 14, C[1] + 10), P.blue, 3, 18)
    mx, my = (O[0] + C[0]) / 2, (O[1] + C[1]) / 2
    label(svg, mx + 20, my + 40, "C = -R.T @ t", P.blue, "start", 20)
    label(svg, mx + 20, my + 66, "camera-to-world: our poses.json", P.black_60, "start", 16)
    label(svg, C[0] + 30, C[1] - 40, "X_cam = R @ X + t", P.teal, "start", 20)
    label(svg, C[0] + 30, C[1] - 14, "world-to-camera: COLMAP", P.black_60, "start", 16)

    return run(svg, "invert.", "one pose, two ways to write it · the classic bug", """
R_c, C = R.T, -R.T @ t     # COLMAP's (R, t) → camera-to-world""")


def dome() -> Svg:
    """Doming: flat ground, camera straight down, free self-calibration: a bowl with a perfect reprojection error."""
    svg = Svg(P.black)
    x0, x1, gy, rise = 140, 940, 820, 130

    def bowl(x):
        return gy - rise * ((x - CX) / ((x1 - x0) / 2)) ** 2

    svg.line(x0, gy, x1, gy, P.black_60, 2, stroke_dasharray="7 8")
    svg.polyline([(x, bowl(x)) for x in range(x0, x1 + 1, 8)], P.lavender, 4)
    rng = random.Random(5)
    for _ in range(46):
        x = rng.uniform(x0 + 10, x1 - 10)
        svg.circle(x, bowl(x) - rng.uniform(2, 10), 3.5, P.lavender_60)
    for i in range(9):
        x = 180 + 90 * i
        y = bowl(x) - 360
        svg.line(x, y, x, bowl(x) - 18, P.black_80, 1.5, stroke_dasharray="3 6")
        svg.circle(x, y, 8, P.white)
    label(svg, x1, gy + 34, "true ground: flat", P.black_60, "end", 17)
    dim(svg, (x1 + 26, bowl(x1)), (x1 + 26, gy), "", P.lavender)
    label(svg, x1 - 10, bowl(x1) - 22, "metres off", P.lavender, "end", 18)
    label(svg, CX, gy + 90, "reprojection error 0.7 px · looks perfect", P.teal_60, size=18)

    return run(svg, "dome.", "a perfect fit, a bent world", """
# flat ground + straight down: lens and curvature trade off
fix = oblique_views or second_height or gcps or fixed_intrinsics""", dark=True)


def priors() -> Svg:
    """Loose: the images decide the shape, georef fits it after. Tight: GNSS is a weighted prior inside BA."""
    svg = Svg(P.cream)
    rng = random.Random(9)
    n = 9
    gnss = [(170 + 92 * i, rng.gauss(0, 7)) for i in range(n)]
    bent = [(x, 0.00045 * (x - CX) ** 2 - 40) for x, _ in gnss]
    for k, name in enumerate(("loose", "tight")):
        cy = 520 + 300 * k
        if k == 0:
            T, _ = fit_similarity(bent, gnss)
            est = [T(p) for p in bent]
        else:
            est = [(x, 0.15 * b[1] + 0.85 * g[1] + rng.gauss(0, 3)) for (x, g1), b, g in zip(gnss, bent, gnss) for _ in [g1]]
        svg.polyline([(x, cy + y) for x, y in est], P.blue_40, 2)
        for (gx_, gy_), (ex, ey) in zip(gnss, est):
            if k == 1:
                svg.polyline([(gx_ + 5 * ((j % 2) * 2 - 1), cy + lerp(gy_, ey, j / 6)) for j in range(7)], P.teal, 1.5)
            else:
                svg.line(gx_, cy + gy_, ex, cy + ey, P.teal, 2)
            svg.circle(gx_, cy + gy_, 8, P.cream, stroke=P.teal, stroke_width=3)
            svg.circle(ex, cy + ey, 7, P.blue)
        svg.text(M + 20, cy - 110, name, "code", 22, P.black)
        sub_ = "images decide the shape · then a 7-number fit" if k == 0 else "GNSS weighted inside bundle adjustment"
        svg.text(M + 20 + 100, cy - 110, sub_, "codel", 17, P.black_60)
        note = "the residuals bend: a pattern, not noise" if k == 0 else "the bend is pulled out · residuals ≈ noise"
        label(svg, W - M - 20, cy + 90, note, P.teal, "end", 16)
    label(svg, M + 20, 990, "camera", P.blue, "start", 16)
    label(svg, M + 120, 990, "GNSS", P.teal, "start", 16)

    return run(svg, "priors.", "navigation after the solve, or inside it", """
cost += Σ |C_i - gnss_i|² / σ²     # tight · σ_h 3 m, σ_v 5 m by default""")


# ============================================================================
# 5 georef
# ============================================================================
def _flight(rows=3, cols=6, x0=330, x1=900, y0=520, y1=860):
    return [(lerp(x0, x1, c / (cols - 1)), lerp(y0, y1, r / (rows - 1))) for r in range(rows) for c in range(cols)]


def helmert() -> Svg:
    """The 7-parameter similarity: scale, rotate and shift the sfm camera centres onto the GNSS positions."""
    svg = Svg(P.white)
    rng = random.Random(12)
    truth = _flight(x0=390, x1=920)
    gnss = [(x + rng.gauss(0, 5), y + rng.gauss(0, 5)) for x, y in truth]
    z = 0.22 * complex(math.cos(0.75), math.sin(0.75))
    gm = sum(complex(*p) for p in truth) / len(truth)
    sfm = [((z * (complex(*p) - gm)) + complex(220, 400)) for p in truth]
    sfm = [(q.real, q.imag) for q in sfm]
    T, zf = fit_similarity(sfm, gnss)
    fitted = [T(p) for p in sfm]
    order = [i for r in range(3) for i in (range(r * 6, r * 6 + 6) if r % 2 == 0 else range(r * 6 + 5, r * 6 - 1, -1))]
    svg.polyline([sfm[i] for i in order], P.lavender_60, 1.5)
    for p in sfm:
        svg.circle(*p, 4.5, P.lavender)
    label(svg, 220, 316, "sfm · any size, any turn", P.lavender, size=17)
    arrow(svg, (290, 450), (360, 505), P.black_20, 3, 18)
    for g, f in zip(gnss, fitted):
        svg.line(*g, *f, P.blue, 2)
        svg.circle(*g, 11, P.white, stroke=P.teal, stroke_width=3)
        svg.circle(*f, 6, P.blue)
    label(svg, 920, 920, "GNSS", P.teal, "end", 18)
    label(svg, 390, 920, "fitted camera", P.blue, "start", 18)
    label(svg, 655, 980, f"fitted here: scale {abs(zf):.2f}, turn {math.degrees(-math.atan2(zf.imag, zf.real)):.0f}°", P.black_60, size=16)

    return run(svg, "helmert.", "move the model onto the GNSS · 7 numbers", """
y = s * R @ x + t      # 3 shift + 3 turn + 1 scale · Brighton: s = 8.586""")


def residual() -> Svg:
    """Reading the residuals: random noise is healthy; a time offset points along track; doming is a bowl in height."""
    svg = Svg(P.cream)
    rng = random.Random(7)
    kinds = [("random", "σ0 ≈ 1 · healthy"), ("time offset", "along track, flips"), ("doming", "centre down, edges up")]
    for k, (name, sub_) in enumerate(kinds):
        cy = 400 + 225 * k
        svg.text(M + 20, cy - 6, name, "code", 20, P.black)
        svg.text(M + 20, cy + 22, sub_, "codel", 15, P.black_60)
        for r in range(3):
            y = cy - 60 + 60 * r
            d = 1 if r % 2 == 0 else -1
            svg.line(380, y, 920, y, P.black_20, 1.5, stroke_dasharray="2 8")
            for c in range(7):
                x = 380 + 90 * c
                if k == 2:
                    rr = ((x - 650) / 270) ** 2 + ((y - cy) / 60) ** 2 * 0.3
                    dz = (rr - 0.55) * 12
                    if dz > 0:
                        svg.circle(x, y, abs(dz) + 2, P.teal)
                    else:
                        svg.circle(x, y, abs(dz) + 2, P.cream, stroke=P.teal, stroke_width=2.5)
                    continue
                if k == 0:
                    dx, dy = rng.gauss(0, 9), rng.gauss(0, 9)
                else:
                    dx, dy = d * 30 + rng.gauss(0, 3), rng.gauss(0, 3)
                svg.circle(x, y, 4, P.black)
                if math.hypot(dx, dy) > 4:
                    arrow(svg, (x, y), (x + dx, y + dy), P.teal, 2.5, 11)
            if k == 1:
                arrow(svg, (330, y), (330 + 26 * d, y), P.black_20, 2, 10) if d > 0 else arrow(svg, (356, y), (330, y), P.black_20, 2, 10)
    label(svg, 920, 990, "filled: above · ring: below", P.black_60, "end", 15)

    return run(svg, "residual.", "what the fit can't explain is the check", """
along = speed * dt     # 10 m/s × 0.2 s = 2 m · flips each strip""")


def offset() -> Svg:
    """Residuals measure consistency, not accuracy: a common GNSS bias moves the whole model and stays invisible."""
    svg = Svg(P.black)
    rng = random.Random(21)
    k = 14  # px per metre
    truth = _flight(3, 6, 190, 890, 420, 756)
    bias = (3.3 * k, -1.4 * k)
    gnss = [(x + bias[0] + rng.gauss(0, 0.42 * k), y + bias[1] + rng.gauss(0, 0.42 * k)) for x, y in truth]
    T, _ = fit_similarity(truth, gnss)
    fitted = [T(p) for p in truth]
    res = [math.dist(f, g) / k for f, g in zip(fitted, gnss)]
    rms = math.sqrt(sum(r * r for r in res) / len(res))
    for t in truth:
        svg.circle(*t, 10, "none", stroke=P.black_60, stroke_width=2, stroke_dasharray="3 4")
    for f, g in zip(fitted, gnss):
        svg.line(*f, *g, P.lavender, 2)
        svg.circle(*g, 4, P.lavender)
        svg.circle(*f, 7, P.white)
    a = truth[12]
    arrow(svg, (a[0] - 6, a[1] + 34), (fitted[12][0] - 6, fitted[12][1] + 34), P.teal_60, 3, 14)
    label(svg, a[0] - 20, a[1] + 76, f"{math.hypot(*bias) / k:.1f} m · invisible", P.teal_60, "start", 18)
    label(svg, 890, 830, f"residuals {rms:.2f} m rms", P.lavender, "end", 18)
    label(svg, 190, 980, "ring: truth · dot: fitted · small dot: GNSS  (simulated)", P.black_60, "start", 15)

    return run(svg, "offset.", "residuals see the noise, not the bias", """
rms_h = 0.44     # Brighton: the noise, what residuals measure
shift = 3.6      # Brighton: the bias, only a reference could see it""", dark=True)


def hinge() -> Svg:
    """Cameras on one straight line: the fit can't tell the roll about that line, so the model hinges on it."""
    svg = Svg(P.cream)

    def pr(x, y, z):
        return CX + x - 0.5 * y, 430 - 0.95 * z + 0.32 * y

    D, Lx, Ly = 260, 300, 170
    for phi, solid in ((-24, False), (24, False), (0, True)):
        a = math.radians(phi)

        def pl(x, y, a=a):
            return pr(x, y * math.cos(a) + D * math.sin(a), y * math.sin(a) - D * math.cos(a))

        quad = [pl(-Lx, -Ly), pl(Lx, -Ly), pl(Lx, Ly), pl(-Lx, Ly)]
        if solid:
            svg.poly(quad, P.lavender_20, stroke=P.lavender, stroke_width=2, stroke_linejoin="round")
        else:
            svg.poly(quad, "none", stroke=P.lavender_60, stroke_width=2, stroke_dasharray="7 7", stroke_linejoin="round")
    svg.line(*pr(-Lx - 60, 0, 0), *pr(Lx + 60, 0, 0), P.black, 2)
    for i in range(7):
        x = -Lx + i * 2 * Lx / 6
        svg.line(*pr(x, 0, 0), *pr(x, 0, -D), P.black_20, 1.2, stroke_dasharray="3 6")
        svg.circle(*pr(x, 0, 0), 9, P.black)
    c = pr(Lx + 90, 0, 0)
    svg.arc(c[0], c[1], 46, math.radians(-160), math.radians(60), P.blue, 3)
    end = (c[0] + 46 * math.cos(math.radians(60)), c[1] + 46 * math.sin(math.radians(60)))
    svg.triangle(*end, 16, P.blue, math.radians(150))
    label(svg, c[0], c[1] - 66, "roll: free", P.blue, "middle", 19)
    label(svg, CX, 940, "every tilt fits the GNSS equally well", P.black_60, size=17)

    return run(svg, "hinge.", "one straight strip · the model can roll", """
if collinear(cameras): stop     # roll about the line is unknown
# a gentle curve: known, but poorly · warns above 1°""")


def enu() -> Svg:
    """Local east-north-up: a flat frame in metres, tangent to the Earth at the first camera."""
    svg = Svg(P.white)
    lat = 46.84
    c, R = (330, 1080), 600
    a = math.radians(lat)
    O = (c[0] + R * math.cos(a), c[1] - R * math.sin(a))
    up, north = (math.cos(a), -math.sin(a)), (-math.sin(a), -math.cos(a))
    svg.clip_begin(M, 270, W - 2 * M, 740)
    svg.circle(*c, R, P.blue_20, stroke=P.blue_40, stroke_width=2)
    svg.line(*c, c[0] + R + 40, c[1], P.blue_40, 1.5, stroke_dasharray="6 7")
    svg.line(*c, *O, P.blue_40, 1.5, stroke_dasharray="6 7")
    t0 = (O[0] - 330 * north[0], O[1] - 330 * north[1])
    t1 = (O[0] + 330 * north[0], O[1] + 330 * north[1])
    svg.line(*t0, *t1, P.black, 2)
    svg.clip_end()
    label(svg, O[0] - 34, O[1] + 64, f"origin: the first camera, {lat}° N", P.blue, "end", 17)
    arrow(svg, O, (O[0] + 150 * up[0], O[1] + 150 * up[1]), P.teal, 4, 20)
    arrow(svg, O, (O[0] + 150 * north[0], O[1] + 150 * north[1]), P.teal, 4, 20)
    label(svg, O[0] + 172 * up[0] + 6, O[1] + 172 * up[1], "up", P.teal, "start", 20)
    label(svg, O[0] + 160 * north[0] + 34 * up[0], O[1] + 160 * north[1] + 34 * up[1], "north", P.teal, "middle", 20)
    svg.circle(*O, 22, P.white, stroke=P.teal, stroke_width=3)
    svg.circle(*O, 6, P.teal)
    label(svg, O[0] + 36, O[1] + 12, "east, toward you", P.teal, "start", 17)
    km = 111.32 * math.cos(a)
    label(svg, W - M - 20, 980, f"1° of longitude here: {km:.0f} km, not 111", P.black_60, "end", 17)

    return run(svg, "enu.", "flat, in metres, touching the Earth at one point", """
enu = R(lat0, lon0) @ (ecef - ecef0)     # exactly Euclidean: fit here""")


def utm() -> Svg:
    """UTM: 60 zones of 6°; Brighton Beach at −91.99° is zone 15, and the scale factor dips to 0.9996 on its centre line."""
    svg = Svg(P.cream)
    lon = -91.994560
    zone = math.floor((lon + 180) / 6) + 1
    x0, x1, y0, y1 = 120, 960, 330, 450
    zw = (x1 - x0) / 60
    for z in range(1, 61):
        xa = x0 + (z - 1) * zw
        svg.rect(xa + 1, y0, zw - 2, y1 - y0, P.blue if z == zone else (P.lavender_20 if z % 2 else P.blue_20), rx=2)
    for v, s in ((-180, "-180°"), (0, "0°"), (180, "180°")):
        label(svg, x0 + (v + 180) / 360 * (x1 - x0), y1 + 30, s, P.black_60, size=15)
    zx = x0 + (zone - 1) * zw
    label(svg, zx + zw / 2, y0 - 16, str(zone), P.blue, size=20)
    bx0, bx1, by0, by1 = 300, 780, 560, 940
    svg.line(zx, y1, bx0, by0, P.black_20, 1.2)
    svg.line(zx + zw, y1, bx1, by0, P.black_20, 1.2)
    svg.rect(bx0, by0, bx1 - bx0, by1 - by0, P.white, rx=4, stroke=P.blue, stroke_width=2)
    cm = (bx0 + bx1) / 2
    svg.line(cm, by0, cm, by1, P.blue_40, 1.5, stroke_dasharray="6 7")
    Rk = 6371.0
    half = 3 * 111.32 * math.cos(math.radians(46.84))
    ks = []
    for i in range(61):
        xkm = -half + 2 * half * i / 60
        ks.append((xkm, 0.9996 * (1 + xkm ** 2 / (2 * Rk ** 2))))

    def gk(xkm, kv):
        return lerp(bx0, bx1, (xkm + half) / (2 * half)), lerp(by1 - 40, by0 + 60, (kv - 0.9995) / (1.0003 - 0.9995))

    svg.line(*gk(-half, 1.0), *gk(half, 1.0), P.black_20, 1.5)
    label(svg, bx1 + 12, gk(0, 1.0)[1] + 6, "k = 1", P.black_60, "start", 15)
    svg.polyline([gk(*p) for p in ks], P.teal, 3)
    label(svg, cm, gk(0, 0.9996)[1] + 34, "0.9996", P.teal, size=17)
    bp = (lerp(bx0, bx1, (lon + 96) / 6), by0 + 40)
    svg.circle(*bp, 8, P.blue)
    label(svg, bp[0] + 14, bp[1] + 6, "Brighton Beach", P.blue, "start", 16)
    label(svg, bx0, by1 + 30, "-96°", P.black_60, size=15)
    label(svg, bx1, by1 + 30, "-90°", P.black_60, size=15)

    return run(svg, "utm.", "the Earth in 60 flat strips · easting, northing in metres", f"""
zone = floor((lon + 180) / 6) + 1     # -91.99° → {zone} · EPSG:326{zone}""")


def datum() -> Svg:
    """Three zeros for height: the ellipsoid, the geoid (about sea level), the takeoff point. Carried, never mixed."""
    svg = Svg(P.white)
    drone_y, take_y, ell_y, geo_y = 340, 700, 860, 920
    xs = (250, 500, 750)

    def gnd(x):
        return take_y + 22 * math.sin((x - 100) / 160) + (x > 720) * (x - 720) * 0.12

    def geo(x):
        return geo_y + 10 * math.sin(x / 90)

    svg.line(xs[0], drone_y, xs[2], drone_y, P.black_20, 1.5, stroke_dasharray="4 6")
    svg.rect(xs[1] - 34, drone_y - 34, 68, 9, P.black, rx=4)
    for dx in (-30, 30):
        ellipse(svg, xs[1] + dx, drone_y - 40, 22, 4, P.black_60)
    svg.polyline([(x, gnd(x)) for x in range(100, 981, 10)], P.black, 2)
    svg.line(100, ell_y, 980, ell_y, P.lavender, 3)
    svg.polyline([(x, geo(x)) for x in range(100, 981, 10)], P.blue, 3)
    label(svg, 980, ell_y - 12, "ellipsoid: the smooth maths Earth", P.lavender, "end", 15)
    label(svg, 980, geo_y + 40, "geoid: about mean sea level", P.blue, "end", 15)
    svg.circle(xs[0], gnd(xs[0]), 7, P.black)
    label(svg, xs[0] - 16, gnd(xs[0]) - 18, "takeoff", P.black_60, "end", 15)

    def updim(x, ya, s, col, ly, brk=True):
        arrow(svg, (x, ya), (x, drone_y + 4), col, 2.5, 14)
        if brk:
            mid = (ya + drone_y) / 2 + 60
            svg.rect(x - 12, mid - 4, 24, 16, P.white)
            svg.line(x - 9, mid + 4, x + 9, mid - 6, col, 2)
            svg.line(x - 9, mid + 14, x + 9, mid + 4, col, 2)
        label(svg, x + 16, ly, s, col, "start", 17)

    updim(xs[0], gnd(xs[0]), "40 m above takeoff", P.black, 450, brk=False)
    updim(xs[1], geo(xs[1]), "H above the geoid", P.blue, 520)
    updim(xs[2], ell_y, "h above the ellipsoid", P.lavender, 590)
    dim(svg, (840, ell_y), (840, geo(840)), "N = -29 m", P.black_60, 8)

    return run(svg, "datum.", "which zero · three ways to say how high", """
vertical = "relative_takeoff"    # carried through, never converted""")


def float_() -> Svg:
    """float32 has 24 bits of mantissa: at a UTM northing of 5 188 000 m it can only step by half a metre."""
    svg = Svg(P.white)

    def ulp32(v):
        return 2.0 ** (math.floor(math.log2(abs(v))) - 23)

    x0, x1 = 140, 940
    for k, (v0, name, true) in enumerate(((5188000.0, "UTM northing", 5188000.3), (3.6, "sfm frame", 4.6))):
        y = 470 + 300 * k
        u = ulp32(v0)
        span = 2.0
        svg.text(x0, y - 90, name, "code", 20, P.black)

        def gx(v, v0=v0, span=span):
            return lerp(x0, x1, (v - v0) / span)

        if u > span / 400:
            svg.line(x0, y, x1, y, P.black_20, 2)
            n = int(span / u)
            for i in range(n + 1):
                svg.circle(gx(v0 + i * u), y, 8, P.blue)
                label(svg, gx(v0 + i * u), y + 40, f"{v0 + i * u:,.1f}".replace(",", " "), P.black_60, size=14)
            snap = round(true / u) * u
            svg.circle(gx(true), y - 40, 7, P.teal)
            arrow(svg, (gx(true), y - 32), (gx(snap) - 4, y - 12), P.teal, 2, 12)
            label(svg, gx(true), y - 58, f"{true:,.1f}".replace(",", " "), P.teal, size=15)
            label(svg, x1, y - 90 + 2, f"steps of {u} m", P.blue, "end", 18)
        else:
            svg.line(x0, y, x1, y, P.blue, 6, stroke_linecap="round")
            svg.circle(gx(true), y, 8, P.teal)
            label(svg, x1, y - 90 + 2, f"steps of {u:.7f}", P.blue, "end", 18)
            for i in range(3):
                label(svg, gx(v0 + i), y + 40, f"{v0 + i:.1f}", P.black_60, size=14)
    label(svg, x0, 980, "float32 keeps 24 bits: the bigger the number, the bigger the step", P.black_60, "start", 16)

    return run(svg, "float.", "big coordinates need double precision", """
np.float32(5188000.3)     # → 5188000.5 · so the products are float64""")


# ============================================================================
# 6 dense
# ============================================================================
def undistort() -> Svg:
    """Undistort: resample every image into an ideal pinhole with the sfm lens, so patches warp by one homography."""
    svg = Svg(P.cream)
    f, cx, cy, k1, k2, w, h = 2794.90, 2000.0, 1125.0, 0.0112, 0.0355, 4000, 2250
    s, x0, y0, boost = 0.2, 140, 400, 5

    def ideal(u, v):
        xd, yd = (u - cx) / f, (v - cy) / f
        xu, yu = xd, yd
        for _ in range(30):
            r2 = xu * xu + yu * yu
            dd = 1 + k1 * r2 + k2 * r2 * r2
            xu, yu = xd / dd, yd / dd
        return cx + f * xu, cy + f * yu

    svg.rect(x0, y0, w * s, h * s, P.white, rx=4, stroke=P.black_20, stroke_width=2)
    for i in range(9):
        for j in range(5):
            u, v = w * i / 8, h * j / 4
            iu, iv = ideal(u, v)
            a = (x0 + u * s, y0 + v * s)
            b = (a[0] + (iu - u) * s * boost, a[1] + (iv - v) * s * boost)
            svg.circle(*a, 4, P.black_60)
            if math.dist(a, b) > 3:
                arrow(svg, a, b, P.blue, 2.5, 12)
    cu, cv = ideal(0, 0)
    corner = math.hypot(cu, cv)
    label(svg, x0, y0 - 24, f"{w} × {h} · k1 {k1}, k2 {k2} from sfm", P.black_60, "start", 16)
    label(svg, x0 + w * s, y0 + h * s + 40, f"arrows × {boost}", P.black_60, "end", 15)
    label(svg, x0, y0 + h * s + 40, f"a corner pixel moves {corner:.0f} px", P.blue, "start", 18)

    return run(svg, "undistort.", "straight lines first · then a patch warps by one homography", """
pycolmap.undistort_images(out, sparse, images)    # into ideal pinholes, once""", size=21)


def views() -> Svg:
    """View selection: compare each reference image with neighbours at a useful angle: not ~0°, not ≫ 40°."""
    svg = Svg(P.white)
    X, hy = (CX, 900), 380
    H = X[1] - hy
    offs = [-470, -400, -330, -260, -190, -120, -50, 18, 90, 160, 230, 300, 370, 440]
    ang = {o: math.degrees(math.atan(abs(o) / H)) for o in offs}
    ok = [o for o in offs if 3 < ang[o] < 40]
    chosen = set(sorted(ok, key=lambda o: abs(ang[o] - 20))[:8])
    for side in (-1, 1):
        pts = [X] + [(X[0] + side * 300 * math.sin(math.radians(t)), X[1] - 300 * math.cos(math.radians(t))) for t in range(3, 41)]
        svg.poly(pts, P.lavender_20)
    for o in offs:
        col = P.blue if o in chosen else (P.black_20 if ang[o] <= 3 else P.lavender_60)
        svg.line(X[0] + o, hy, *X, col, 2 if o in chosen else 1.5, **({} if o in chosen else {"stroke_dasharray": "4 6"}))
        cam(svg, X[0] + o, hy, 34, col, col if o in chosen else P.white, 8)
        if o not in chosen:
            svg.circle(X[0] + o, hy, 8, P.white, stroke=col, stroke_width=2.5)
    svg.line(X[0], hy, *X, P.black, 2.5)
    cam(svg, X[0], hy, 44, P.black, P.black, 10)
    svg.circle(*X, 10, P.blue)
    label(svg, X[0], hy - 34, "reference", P.black, size=17)
    label(svg, X[0] - 470, hy - 34, f"{ang[-470]:.0f}°", P.lavender, size=16)
    label(svg, X[0] + 440, hy - 34, f"{ang[440]:.0f}°", P.lavender, size=16)
    label(svg, X[0] + 18, hy + 60, f"{ang[18]:.0f}°", P.black_60, size=16)
    label(svg, X[0], 980, f"{len(chosen)} chosen · too close: no depth · too wide: patches no longer alike", P.black_60, size=15)

    return run(svg, "views.", "who to compare with · a useful angle", """
num_views = 8     # source images per reference image""")


def depth() -> Svg:
    """Plane sweep along one ray: every candidate depth lands on one line in the source image; the best NCC wins."""
    svg = Svg(P.white)
    rng = random.Random(3)
    Rc, Sc, py = (260, 900), (790, 900), 900 - 60
    d = (0.42, -1.0)
    nd = math.hypot(*d)
    d = (d[0] / nd, d[1] / nd)
    ts = [180 + 62 * k for k in range(8)]
    kt = 4
    cand = [(Rc[0] + t * d[0], Rc[1] + t * d[1]) for t in ts]
    T = cand[kt]
    svg.polyline([(x, T[1] + 18 * math.sin((x - T[0]) / 70) - 0.05 * (x - T[0])) for x in range(120, 980, 10)], P.black, 2)
    end = (Rc[0] + 640 * d[0], Rc[1] + 640 * d[1])
    svg.line(*Rc, *end, P.black_60, 2)
    svg.line(Sc[0] - 260, py, Sc[0] + 60, py, P.lavender_60, 4, stroke_linecap="round")
    for k, q in enumerate(cand):
        t = (py - Sc[1]) / (q[1] - Sc[1])
        p = (Sc[0] + (q[0] - Sc[0]) * t, py)
        col = P.blue if k == kt else P.lavender_60
        svg.line(*Sc, *q, col, 2 if k == kt else 1.2)
        svg.circle(*q, 9 if k == kt else 6, col)
        svg.circle(*p, 6 if k == kt else 4, col)
    cam(svg, Rc[0], Rc[1], 60, P.black_60, P.black, 9, 60, up=True)
    svg.circle(*Sc, 9, P.black)
    label(svg, Rc[0], Rc[1] + 40, "reference", P.black_60, size=16)
    label(svg, Sc[0], Sc[1] + 40, "source", P.black_60, size=16)
    label(svg, Sc[0] - 100, py - 18, "epipolar line", P.lavender, size=15)
    tex = [sum(math.sin(0.37 * a * i + ph) / a for a, ph in ((1, 0.3), (2.3, 1.1), (4.1, 2.0), (6.7, 0.5))) + rng.gauss(0, 0.1)
           for i in range(200)]

    def ncc_at(shift):
        a, b = tex[90:110], tex[90 + shift:110 + shift]
        ma, mb = sum(a) / 20, sum(b) / 20
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return num / den

    gx0, gx1, gy0, gy1 = 660, 940, 300, 430
    svg.line(gx0, gy1, gx1, gy1, P.black_20, 1.5)
    curve = [(lerp(gx0, gx1, i / 70), lerp(gy1, gy0, (ncc_at(i - 35) + 1) / 2)) for i in range(71)]
    svg.polyline(curve, P.blue, 3)
    label(svg, gx0, gy1 + 26, "depth →", P.black_60, "start", 14)
    label(svg, gx0 - 10, gy0 + 6, "NCC", P.black_60, "end", 14)
    svg.circle(*curve[35], 7, P.blue)

    return run(svg, "depth.", "for every pixel: how far is the surface?", """
depth = argmax(ncc(ref, warp(src, d)) for d in candidates)""")


def ncc() -> Svg:
    """Normalised cross-correlation ignores brightness and contrast: SSD prefers the wrong patch, NCC the right one."""
    svg = Svg(P.cream)
    rng = random.Random(14)
    A = [[rng.uniform(60, 230) for _ in range(5)] for _ in range(5)]
    B = [[0.45 * v + 25 for v in r] for r in A]
    C = [[rng.uniform(80, 200) for _ in range(5)] for _ in range(5)]

    def flat(m):
        return [v for r in m for v in r]

    def nccv(a, b):
        a, b = flat(a), flat(b)
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        return num / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))

    def ssd(a, b):
        return sum((x - y) ** 2 for x, y in zip(flat(a), flat(b)))

    cs, y0 = 44, 420
    for k, (m, name) in enumerate(((A, "reference"), (B, "same, darker"), (C, "another spot"))):
        x0 = 120 + 310 * k
        for j in range(5):
            for i in range(5):
                svg.rect(x0 + i * cs, y0 + j * cs, cs, cs, gray(m[j][i]))
        svg.rect(x0, y0, 5 * cs, 5 * cs, "none", stroke=P.black, stroke_width=1.5)
        label(svg, x0 + 2.5 * cs, y0 - 26, name, P.black, size=18)
        if k:
            n, s_ = nccv(A, m), ssd(A, m)
            right = k == 1
            label(svg, x0 + 2.5 * cs, y0 + 5 * cs + 50, f"NCC {n:.2f}", P.teal if right else P.black_60, size=22)
            label(svg, x0 + 2.5 * cs, y0 + 5 * cs + 86, f"SSD {s_:,.0f}".replace(",", " "), P.black_60, size=16)
    label(svg, CX, 930, "SSD picks the wrong one · NCC sees the same pattern", P.black_60, size=16)

    return run(svg, "ncc.", "alike in pattern, not in brightness", """
ncc = mean((a - a.mean()) * (b - b.mean())) / (a.std() * b.std())""")


def propagate() -> Svg:
    """PatchMatch: random depths everywhere; each pixel tries its neighbours' and keeps what fits better."""
    svg = Svg(P.black)
    rng = random.Random(10)
    n = 14

    def truth(x, y):
        if 3 <= x <= 10 and 2 <= y <= 11:
            return 0.15 + 0.06 * abs(x - 6.5)
        return 0.85 - 0.01 * y

    def cost(x, y, d):
        return abs(d - truth(x, y))

    D = [[rng.random() for _ in range(n)] for _ in range(n)]
    snaps = [[r[:] for r in D]]
    for sweep in range(3):
        fwd = sweep % 2 == 0
        rng_ = range(n) if fwd else range(n - 1, -1, -1)
        for y in rng_:
            for x in rng_:
                nb = [(x - 1, y), (x, y - 1)] if fwd else [(x + 1, y), (x, y + 1)]
                for a, b in nb:
                    if 0 <= a < n and 0 <= b < n and cost(x, y, D[b][a]) < cost(x, y, D[y][x]):
                        D[y][x] = D[b][a]
                r = 0.25
                for _ in range(3):
                    c = min(1, max(0, D[y][x] + rng.uniform(-r, r)))
                    if cost(x, y, c) < cost(x, y, D[y][x]):
                        D[y][x] = c
                    r /= 2
        if sweep in (0, 2):
            snaps.append([r[:] for r in D])
    cs, gap = 18, 48
    x0 = (W - 3 * n * cs - 2 * gap) / 2
    for k, (m, name) in enumerate(zip(snaps, ("random", "1 sweep", "3 sweeps"))):
        ox = x0 + k * (n * cs + gap)
        for y in range(n):
            for x in range(n):
                svg.rect(ox + x * cs + 1, 470 + y * cs + 1, cs - 2, cs - 2, ramp(m[y][x]), rx=2)
        label(svg, ox + n * cs / 2, 470 + n * cs + 44, name, P.white if k == 2 else P.black_60, size=18)
    label(svg, CX, 400, "depth per pixel · a roof on flat ground", P.black_60, size=16)

    return run(svg, "propagate.", "random guesses, spread by the lucky ones", """
for p in pixels:      # sweeping, alternating direction
    plane[p] = best(plane[p], neighbours(p), jitter(plane[p]))""", dark=True)


def baseline() -> Svg:
    """Depth precision: σZ = Z² / (f·B) · σd. A short baseline matches easily but pins the depth down badly."""
    svg = Svg(P.white)
    Z, sig = 470, math.radians(0.8)
    yc = 900
    for k, (cx, B) in enumerate(((300, 90), (780, 300))):
        X = (cx, yc - Z)
        cams = [(cx - B / 2, yc), (cx + B / 2, yc)]

        def edge(c, s, X=X):
            a = math.atan2(X[1] - c[1], X[0] - c[0]) + s
            return c, (math.cos(a), math.sin(a))

        def meet(e1, e2):
            (p, d), (q, e) = e1, e2
            den = d[0] * e[1] - d[1] * e[0]
            t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
            return p[0] + t * d[0], p[1] + t * d[1]

        es = [[edge(c, s) for s in (-sig, sig)] for c in cams]
        quad = [meet(es[0][0], es[1][0]), meet(es[0][0], es[1][1]), meet(es[0][1], es[1][1]), meet(es[0][1], es[1][0])]
        for c in cams:
            svg.line(*c, *X, P.lavender_60, 1.5)
        svg.poly(quad, P.blue, opacity=0.85)
        for c in cams:
            svg.circle(*c, 9, P.black)
        dim(svg, (cams[0][0], yc + 40), (cams[1][0], yc + 40), "")
        label(svg, cx, yc + 76, "B", P.black_60, size=18)
        spread = max(q[1] for q in quad) - min(q[1] for q in quad)
        label(svg, cx, 330, f"depth spread {spread:.0f} px", P.blue, size=17)
    sz = 45 ** 2 / (2794.9 / 2 * 13) * 0.5

    return run(svg, "baseline.", "a wider baseline, a sharper depth", f"""
sigma_z = Z**2 / (f * B) * sigma_d    # 45 m, B 13 m, 0.5 px: {sz * 100:.1f} cm""")


def agree() -> Svg:
    """Fusion: a point survives only where at least min_views depth maps agree on it."""
    svg = Svg(P.cream)
    rng = random.Random(16)
    cams = [(190 + 175 * i, 380) for i in range(5)]

    def surf(x):
        return 820 + 30 * math.sin(x / 140)

    svg.polyline([(x, surf(x)) for x in range(120, 981, 10)], P.black, 2)
    for k, (sx, good) in enumerate(((400, True), (770, False))):
        S = (sx, surf(sx))
        est = []
        for i, c in enumerate(cams):
            dx, dy = S[0] - c[0], S[1] - c[1]
            L = math.hypot(dx, dy)
            if good:
                e = rng.gauss(0, 7) if i != 3 else -120
            else:
                e = [-90, 6, -150, -8, -60][i]
            t = (L + e) / L
            q = (c[0] + dx * t, c[1] + dy * t)
            est.append(q)
            svg.line(*c, *q, P.lavender_60, 1.2, stroke_dasharray="3 6")
        near = [q for q in est if math.dist(q, S) < 22]
        for q in est:
            svg.circle(*q, 6, P.lavender if q in near else P.black_20)
        if len(near) >= 3:
            m = (sum(q[0] for q in near) / len(near), sum(q[1] for q in near) / len(near))
            svg.circle(*m, 26, "none", stroke=P.blue, stroke_width=2.5)
            svg.circle(*m, 9, P.blue)
            label(svg, m[0], m[1] + 70, f"{len(near)} agree · kept", P.blue, size=18)
        else:
            label(svg, S[0], S[1] + 70, f"{len(near)} agree · dropped", P.black_60, size=18)
    for c in cams:
        svg.circle(*c, 9, P.black)

    return run(svg, "agree.", "keep only what several images agree on", """
keep = n_agree >= min_views     # 3 · fusion is the main outlier filter""")


def mirror() -> Svg:
    """Reflections: water mirrors the shore, and the match lands as deep below the surface as the object is tall."""
    svg = Svg(P.black)
    wy, post_x, top_y = 700, 300, 470
    svg.rect(120, wy, 840, 260, mix(P.black, P.blue, 0.22))
    svg.poly([(120, wy), (120, 600), (220, 610), (360, 660), (430, wy)], P.black_80)
    svg.rect(post_x - 7, top_y, 14, 660 - top_y + 4, P.white, rx=4)
    T = (post_x, top_y)
    Tm = (post_x, 2 * wy - top_y)
    Cc = (800, 330)
    t = (wy - Cc[1]) / (Tm[1] - Cc[1])
    Wp = (Cc[0] + (Tm[0] - Cc[0]) * t, wy)
    svg.line(*Cc, *Wp, P.lavender, 2.5)
    svg.line(*Wp, *T, P.lavender, 2.5)
    svg.line(*Wp, *Tm, P.lavender, 2, stroke_dasharray="6 7")
    svg.rect(post_x - 7, wy, 14, Tm[1] - wy, "none", stroke=P.lavender_60, stroke_width=1.5, stroke_dasharray="4 5", rx=4)
    svg.circle(*Tm, 11, "none", stroke=P.lavender, stroke_width=3)
    rng = random.Random(1)
    for _ in range(14):
        svg.circle(rng.uniform(240, 520), rng.uniform(wy + 50, Tm[1] + 10), 3.5, P.lavender_60)
    svg.circle(*Cc, 9, P.white)
    label(svg, Tm[0] + 26, Tm[1] + 6, "matched here", P.lavender, "start", 17)
    label(svg, 960, wy - 16, "water", P.blue_40, "end", 16)
    label(svg, Wp[0] + 18, wy + 34, "light bounces", P.black_60, "start", 15)

    return run(svg, "mirror.", "a reflection has the depth of what it mirrors", """
z = z_water - (z_object - z_water)    # points below the surface""", dark=True)


# ============================================================================
# 7 dsm
# ============================================================================
def _med(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def median() -> Svg:
    """One height per cell: a cross-section of the cloud cut into cells, and why the median beats max, mean and min."""
    svg = Svg(P.white)
    rng = random.Random(5)
    n, cw, x0, gy, roof = 16, 50, 140, 520, 380

    def surf(x):
        return roof if 440 <= x < 640 else gy + 10 * math.sin(x / 80)

    cells = []
    for c in range(n):
        pts = [(x, surf(x) + rng.gauss(0, 5)) for x in (rng.uniform(x0 + c * cw + 4, x0 + (c + 1) * cw - 4) for _ in range(5))]
        if c == 3:
            pts[2] = (pts[2][0], 330)
        cells.append(pts)
    hi = 3
    svg.rect(x0 + hi * cw, 310, cw, 240, P.lavender_20)
    for c in range(n + 1):
        svg.line(x0 + c * cw, 330, x0 + c * cw, 550, P.black_20, 1, stroke_dasharray="2 5")
    for c, pts in enumerate(cells):
        for p in pts:
            svg.circle(*p, 3.5, P.black_60)
        m = _med([p[1] for p in pts])
        svg.line(x0 + c * cw + 3, m, x0 + (c + 1) * cw - 3, m, P.blue, 4, stroke_linecap="round")
    pts = cells[hi]
    ys = [p[1] for p in pts]
    med_y = _med(ys)
    bx0, bx1, by0, by1 = 330, 750, 640, 980
    k = (by1 - 40 - (by0 + 30)) / (med_y - min(ys))

    def zy(y):
        return by1 - 40 - (med_y - y) * k

    svg.line(x0 + hi * cw, 550, bx0, by0, P.black_20, 1.2)
    svg.line(x0 + (hi + 1) * cw, 550, bx1, by0, P.black_20, 1.2)
    svg.rect(bx0, by0, bx1 - bx0, by1 - by0, P.white, rx=4, stroke=P.lavender, stroke_width=2)
    for p in pts:
        svg.circle(bx0 + (p[0] - x0 - hi * cw) / cw * (bx1 - bx0), zy(p[1]), 6, P.black_60)
    lines = [("max", min(ys), P.lavender), ("mean", sum(ys) / len(ys), P.teal), ("median", med_y, P.blue), ("min", max(ys), P.black_60)]
    last = -1e9
    for name, y, col in sorted(lines, key=lambda t: zy(t[1])):
        yy = zy(y)
        svg.line(bx0 + 10, yy, bx1 - 10, yy, col, 3 if name == "median" else 2, **({} if name == "median" else {"stroke_dasharray": "6 6"}))
        ly = max(yy + 6, last + 22)
        label(svg, bx1 + 16, ly, name, col, "start", 18)
        last = ly
    label(svg, bx0 - 16, zy(min(ys)) + 6, "an outlier", P.black_60, "end", 16)

    return run(svg, "median.", "one height per cell", """
z = median(points_in_cell)     # one outlier moves it by nothing""")


def spacing() -> Svg:
    """Cell size against point spacing: below the spacing most cells are empty; past 1.5× coverage stops improving."""
    svg = Svg(P.cream)
    rng = random.Random(19)
    pts = [(i + 0.5 + rng.uniform(-0.38, 0.38), j + 0.5 + rng.uniform(-0.38, 0.38))
           for i in range(6) for j in range(6) if rng.random() > 0.15]
    ps = 50
    for k, cell in enumerate((0.5, 1.0, 1.5, 3.0)):
        ox, oy = 150 + (k % 2) * 450, 310 + (k // 2) * 350
        n = round(6 / cell)
        counts = {}
        for x, y in pts:
            key = (min(n - 1, int(x / cell)), min(n - 1, int(y / cell)))
            counts[key] = counts.get(key, 0) + 1
        for i, j in counts:
            svg.rect(ox + i * cell * ps, oy + j * cell * ps, cell * ps, cell * ps, P.blue_20)
        for i in range(n + 1):
            svg.line(ox + i * cell * ps, oy, ox + i * cell * ps, oy + 6 * ps, P.lavender_60, 1)
            svg.line(ox, oy + i * cell * ps, ox + 6 * ps, oy + i * cell * ps, P.lavender_60, 1)
        svg.rect(ox, oy, 6 * ps, 6 * ps, "none", stroke=P.blue if cell == 1.5 else P.lavender, stroke_width=3 if cell == 1.5 else 1.5)
        for x, y in pts:
            svg.circle(ox + x * ps, oy + y * ps, 3.5, P.black)
        cov = len(counts) / (n * n)
        label(svg, ox, oy + 6 * ps + 30, f"{cell:g} × spacing", P.blue if cell == 1.5 else P.black, "start", 18)
        label(svg, ox + 6 * ps, oy + 6 * ps + 30, f"{cov:.0%} of cells hit".replace("%", " %"), P.black_60, "end", 15)

    return run(svg, "spacing.", "how big a cell · 1.5 × the point spacing", """
cell = round_up(1.5 * spacing)    # to 1, 2, 2.5 or 5: 9.5 cm → 10 cm""")


def spike() -> Svg:
    """Despiking: a cell more than 1 m from all but at most one of its 8 neighbours is noise, not surface."""
    svg = Svg(P.white)
    grids = [("a spike", [[0.2, 0.1, 0.3], [0.2, 4.1, 0.1], [0.2, 0.3, 0.2]]),
             ("a roof corner", [[0.1, 0.2, 0.1], [0.2, 3.0, 3.1], [0.1, 2.9, 3.0]])]
    cs = 100
    for k, (name, g) in enumerate(grids):
        ox, oy = 150 + k * 470, 420
        zc = g[1][1]
        near = sum(abs(zc - g[j][i]) <= 1.0 for j in range(3) for i in range(3) if (i, j) != (1, 1))
        removed = near <= 1
        for j in range(3):
            for i in range(3):
                z = g[j][i]
                fill = mix(P.white, P.blue, min(1, z / 4.5))
                svg.rect(ox + i * cs + 3, oy + j * cs + 3, cs - 6, cs - 6, fill, rx=8)
                if (i, j) != (1, 1) and abs(zc - z) <= 1.0:
                    svg.rect(ox + i * cs + 3, oy + j * cs + 3, cs - 6, cs - 6, "none", rx=8, stroke=P.teal, stroke_width=4)
                label(svg, ox + i * cs + cs / 2, oy + j * cs + cs / 2 + 8, f"{z:.1f}", P.white if z > 2 else P.black, size=22)
        if removed:
            svg.rect(ox + cs + 3, oy + cs + 3, cs - 6, cs - 6, "none", rx=8, stroke=P.black, stroke_width=3, stroke_dasharray="6 5")
        svg.text(ox, oy - 34, name, "code", 21, P.black)
        label(svg, ox, oy + 3 * cs + 46, f"{near} of 8 within 1 m", P.teal, "start", 19)
        label(svg, ox, oy + 3 * cs + 78, "removed" if removed else "kept", P.black if removed else P.blue, "start", 19)

    return run(svg, "spike.", "noise, not surface · all but one neighbour", """
spike = sum(abs(z - n) <= 1.0 for n in neighbours) <= 1""")


def fill() -> Svg:
    """Filling holes by area: small empty patches between points are surface, the sea is not. Fill under 1 m²."""
    svg = Svg(P.cream)
    rng = random.Random(23)
    nx, ny, cs, x0, y0, limit = 44, 30, 18, 144, 340, 25
    empty = set()
    for j in range(ny):
        shore = 9 + 3 * math.sin(j / 4.5) + 1.5 * math.sin(j / 1.7)
        empty |= {(i, j) for i in range(nx) if i < shore}
    for _ in range(9):
        cx_, cy_ = rng.randint(16, nx - 3), rng.randint(2, ny - 3)
        for _ in range(rng.randint(2, 11)):
            empty.add((cx_, cy_))
            cx_ += rng.choice((-1, 0, 1))
            cy_ += rng.choice((-1, 0, 1))
    for j in range(8, 15):
        for i in range(27 + (j % 3 == 0), 34 - (j % 2)):
            empty.add((i, j))
    comp, done = [], set()
    for c in empty:
        if c in done:
            continue
        stack, part = [c], []
        while stack:
            u = stack.pop()
            if u in done or u not in empty:
                continue
            done.add(u)
            part.append(u)
            stack += [(u[0] + 1, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)]
        comp.append(part)
    filled = {c for part in comp if len(part) < limit for c in part}
    for j in range(ny):
        for i in range(nx):
            if (i, j) in filled:
                fc = P.teal
            elif (i, j) in empty:
                continue
            else:
                fc = P.blue_40
            svg.rect(x0 + i * cs + 1, y0 + j * cs + 1, cs - 2, cs - 2, fc, rx=2)
    big = next(p for p in comp if len(p) >= limit and min(c[0] for c in p) > 12)
    bx = sum(c[0] for c in big) / len(big)
    by = sum(c[1] for c in big) / len(big)
    label(svg, x0 + bx * cs + cs / 2, y0 + by * cs + 6, f"{len(big)} cells", P.black_60, size=15)
    label(svg, x0 + 4 * cs, y0 + ny * cs / 2 + 6, "sea", P.blue_40, size=20)
    ly = y0 + ny * cs + 44
    for k, (fc, name) in enumerate(((P.blue_40, "measured"), (P.teal, f"filled: under {limit} cells"), (P.cream, "left empty"))):
        lx = x0 + k * 270
        svg.rect(lx, ly - 16, 20, 20, fc, rx=3, stroke=P.black_20 if fc == P.cream else fc, stroke_width=1.5)
        label(svg, lx + 32, ly, name, P.black_60, "start", 16)

    return run(svg, "fill.", "fill the small holes · admit the big ones", """
if hole.area < fill_area:    # 1 m² · by area, not distance
    fill(hole)               # the sea stays empty""")


def corner() -> Svg:
    """Pixel-is-area: the grid origin is the corner of the top-left cell; a cell's centre is half a cell in."""
    svg = Svg(P.white)
    cs, nx, ny, x0, y0 = 150, 4, 3, 240, 380
    h = cs / 2
    for j in range(ny + 1):
        svg.line(x0 + h, y0 + h + j * cs, x0 + h + nx * cs, y0 + h + j * cs, P.lavender_60, 2, stroke_dasharray="7 7")
    for i in range(nx + 1):
        svg.line(x0 + h + i * cs, y0 + h, x0 + h + i * cs, y0 + h + ny * cs, P.lavender_60, 2, stroke_dasharray="7 7")
    for j in range(ny + 1):
        svg.line(x0, y0 + j * cs, x0 + nx * cs, y0 + j * cs, P.blue, 2.5)
    for i in range(nx + 1):
        svg.line(x0 + i * cs, y0, x0 + i * cs, y0 + ny * cs, P.blue, 2.5)
    for j in range(ny):
        for i in range(nx):
            svg.circle(x0 + h + i * cs, y0 + h + j * cs, 5, P.teal)
    svg.circle(x0, y0, 10, P.blue)
    label(svg, x0 - 14, y0 - 18, "(x0, y0)", P.blue, "end", 19)
    arrow(svg, (x0 + 8, y0 + 8), (x0 + h - 10, y0 + h - 10), P.teal, 2.5, 12)
    label(svg, x0 + h + 14, y0 + h - 16, "centre: + ½ cell", P.teal, "start", 17)
    label(svg, x0 + nx * cs + h, y0 + h + ny * cs + 40, "read as points: everything moves half a cell", P.lavender, "end", 16)

    return run(svg, "corner.", "a cell is a square, not a point", """
x = x0 + (col + 0.5) * res    # pixel-is-area · x0 on a multiple of res""")


def ndsm() -> Svg:
    """DSM: the top of everything. DTM: bare ground. nDSM = DSM − DTM: how tall things are."""
    svg = Svg(P.white)
    xs = list(range(130, 951, 5))

    def dtm(x):
        return 40 * math.sin((x - 130) / 220) + 0.06 * (x - 130)

    def obj(x):
        b = 130 if 300 <= x <= 450 else 0
        if 300 <= x <= 450:
            b += 40 - abs(x - 375) * 40 / 75
        t = 110 * math.exp(-((x - 640) / 42) ** 2)
        c = 22 if 820 <= x <= 860 else 0
        return max(b, t, c)

    base1, base2 = 760, 960
    top = [(x, base1 - 60 - dtm(x) - obj(x)) for x in xs]
    gr = [(x, base1 - 60 - dtm(x)) for x in xs]
    svg.poly(top + gr[::-1], P.lavender_20)
    svg.polyline(gr, P.teal, 3, stroke_dasharray="8 6")
    svg.polyline(top, P.blue, 3)
    svg.poly([(xs[0], base2)] + [(x, base2 - obj(x)) for x in xs] + [(xs[-1], base2)], P.lavender_60)
    svg.line(xs[0], base2, xs[-1], base2, P.black, 2)
    label(svg, 375, base1 - 60 - dtm(375) - obj(375) - 20, "DSM: the top of everything", P.blue, size=17)
    label(svg, 950, gr[-1][1] + 34, "DTM: bare ground", P.teal, "end", 17)
    label(svg, 130, base2 - 150, "nDSM = DSM - DTM", P.black, "start", 18)
    for x, s in ((375, "roof"), (640, "tree"), (840, "car")):
        label(svg, x, base2 + 30, s, P.black_60, size=15)

    return run(svg, "ndsm.", "the cameras only see the top", """
ndsm = dsm - dtm     # how tall things are""")


def nmad() -> Svg:
    """Checking against a reference: remove the median offset, then a robust spread (NMAD) the tails can't pull."""
    svg = Svg(P.cream)
    rng = random.Random(31)
    dz = [rng.gauss(0, 0.19) if rng.random() < 0.9 else rng.choice((-1, 1)) * rng.expovariate(1.6) for _ in range(4000)]
    m = _med(dz)
    nm = 1.4826 * _med([abs(v - m) for v in dz])
    rmse = math.sqrt(sum(v * v for v in dz) / len(dz))
    lo, hi, bw = -1.5, 1.5, 0.05
    nb = round((hi - lo) / bw)
    counts = [0] * nb
    for v in dz:
        if lo <= v < hi:
            counts[int((v - lo) / bw)] += 1
    x0, x1, yb, yt = 140, 940, 900, 340
    top = max(counts)

    def gx(v):
        return lerp(x0, x1, (v - lo) / (hi - lo))

    svg.rect(gx(-rmse), yt - 20, gx(rmse) - gx(-rmse), yb - yt + 20, "none", stroke=P.lavender, stroke_width=2, stroke_dasharray="6 6")
    svg.rect(gx(m - nm), yt - 20, gx(m + nm) - gx(m - nm), yb - yt + 20, P.blue_20)
    for i, c in enumerate(counts):
        hgt = (yb - yt) * c / top
        if hgt > 0.5:
            svg.rect(gx(lo + i * bw) + 1, yb - hgt, gx(bw) - gx(0) - 2, hgt, P.blue, rx=2)
    svg.line(x0, yb, x1, yb, P.black, 2)
    svg.line(gx(m), yt - 30, gx(m), yb, P.black, 1.5)
    for v in (-1.5, -1, -0.5, 0, 0.5, 1, 1.5):
        label(svg, gx(v), yb + 30, f"{v:g} m", P.black_60, size=14)
    label(svg, gx(m + nm) + 10, yt + 10, f"NMAD {nm:.2f} m", P.blue, "start", 18)
    label(svg, gx(rmse) + 10, yt + 44, f"RMSE {rmse:.2f} m", P.lavender, "start", 18)
    label(svg, x0, yb + 70, "DSM - reference, after removing the median offset  (simulated)", P.black_60, "start", 15)

    return run(svg, "nmad.", "a spread the tails can't pull", """
nmad = 1.4826 * median(abs(dz - median(dz)))    # Brighton: 0.19 m""")


# ============================================================================
# 8 ortho
# ============================================================================
def backward() -> Svg:
    """Orthorectification runs the camera backwards: for each map pixel, a height, a projection, a colour."""
    svg = Svg(P.white)
    x0, cw, n, oy = 140, 40, 20, 920
    C, py = (720, 330), 380

    def dsm(x):
        return 640 if 520 <= x <= 640 else 800 + 22 * math.sin(x / 90)

    svg.polyline([(x, dsm(x)) for x in range(x0, x0 + n * cw + 1, 4)], P.black, 2)
    hi = 8
    for i in range(n):
        svg.rect(x0 + i * cw + 1, oy, cw - 2, 30, P.teal if i == hi else P.lavender_20, rx=3)
    px = x0 + hi * cw + cw / 2
    S = (px, dsm(px))
    t = (py - C[1]) / (S[1] - C[1])
    P_ = (C[0] + (S[0] - C[0]) * t, py)
    svg.line(px, oy - 6, *S, P.blue, 2.5, stroke_dasharray="6 6")
    svg.line(*S, *C, P.blue, 2.5)
    svg.line(C[0] - 90, py, C[0] + 90, py, P.lavender_60, 4, stroke_linecap="round")
    svg.rect(P_[0] - 9, py - 9, 18, 18, P.teal, rx=3)
    svg.circle(*S, 8, P.blue)
    svg.circle(*C, 9, P.black)
    for k, (x, y, s) in enumerate(((px - 20, (oy + S[1]) / 2, "height from the DSM"), (lerp(S[0], C[0], 0.45) + 18, lerp(S[1], C[1], 0.45), "project into the photo"),
                                   (P_[0] + 26, py - 26, "take its colour"))):
        label(svg, x, y + 6, f"{k + 1}  {s}", P.blue, "end" if k == 0 else "start", 17)
    label(svg, x0, oy + 64, "the orthophoto: a north-up grid", P.black_60, "start", 16)

    return run(svg, "backward.", "run the camera backwards, pixel by pixel", """
ortho[r, c] = photo[project(K, R, C, (E, N, dsm[r, c]))]""")


def lean() -> Svg:
    """Relief displacement: a camera looks out from one point, so a tall thing's top lands further out than its foot."""
    svg = Svg(P.cream)
    C, gy, fx, h = (330, 320), 860, 600, 230
    H = gy - C[1]
    land = C[0] + (fx - C[0]) * H / (H - h)
    svg.rect(fx, gy - h, 40, h, P.black, rx=3)
    top = (fx + 40, gy - h)
    svg.rect(fx + 40, gy - 6, land - fx - 40, 12, P.lavender_60, rx=3)
    svg.line(*C, fx, gy, P.blue_40, 2)
    svg.line(*C, *top, P.blue, 2.5)
    svg.line(*top, land, gy, P.blue, 2, stroke_dasharray="6 6")
    ground(svg, gy, 130, 950)
    svg.line(C[0], C[1], C[0], gy, P.black_20, 1.5, stroke_dasharray="3 6")
    svg.circle(*C, 9, P.black)
    svg.circle(land, gy, 8, P.blue)
    label(svg, (fx + 40 + land) / 2, gy + 40, "hidden, and the top lands here", P.blue, size=16)
    dim(svg, (C[0] - 60, C[1]), (C[0] - 60, gy), "", P.black_60)
    label(svg, C[0] - 80, (C[1] + gy) / 2 + 7, "H", P.black_60, "end", 20)
    dim(svg, (fx - 34, gy - h), (fx - 34, gy), "", P.black_60)
    label(svg, fx - 54, gy - h / 2 + 7, "h", P.black_60, "end", 20)
    label(svg, C[0], gy + 40, "nadir", P.black_60, size=16)

    return run(svg, "lean.", "a photo is not a map · tall things lean", """
d = r * h / H      # in the photo: taller, or further out, leans more""")


def slant() -> Svg:
    """A height error moves a colour by Δz·tanθ: invisible straight down, large at the edge of a photo."""
    svg = Svg(P.white)
    dzp, gy = 70, 820
    for k, (cx, th) in enumerate(((310, 9), (760, 35))):
        a = math.radians(th)
        L = 470
        top = (cx - L * math.sin(a), gy - L * math.cos(a))
        svg.line(cx - 170, gy, cx + 150, gy, P.black, 2)
        svg.line(cx - 170, gy - dzp, cx + 150, gy - dzp, P.lavender, 2, stroke_dasharray="7 7")
        hit = (cx - dzp * math.tan(a), gy - dzp)
        svg.line(*top, cx, gy, P.blue, 2.5)
        svg.line(top[0], top[1], top[0], gy, P.black_20, 1.5, stroke_dasharray="3 6")
        svg.circle(*top, 9, P.black)
        svg.circle(*hit, 7, P.lavender)
        svg.circle(cx, gy, 7, P.blue)
        svg.line(hit[0], gy + 30, cx, gy + 30, P.teal, 4, stroke_linecap="round")
        label(svg, cx, gy + 70, f"θ {th}° · {10 * math.tan(a):.1f} cm", P.teal, size=20)
        svg.arc(top[0], top[1], 70, math.pi / 2 - a, math.pi / 2, P.black_60, 1.5)
    label(svg, 910, gy - dzp - 16, "DSM, 10 cm too high", P.lavender, "end", 15)

    return run(svg, "slant.", "errors hide straight down", """
dxy = dz * tan(theta)      # so each pixel takes the most nadir photo""")


def ghost() -> Svg:
    """Occlusion: the ground behind a building is hidden from this camera; without a z-buffer it gets the wall's colour."""
    svg = Svg(P.black)
    C, gy, G = (790, 330), 860, (300, 860)
    bx0, bx1, by = 440, 580, 590
    svg.rect(bx0, by, bx1 - bx0, gy - by, P.black_80, rx=3)
    svg.line(130, gy, 950, gy, P.black_60, 2)
    hit = None
    for i in range(1, 2001):
        t = i / 2000
        x, y = C[0] + (G[0] - C[0]) * t, C[1] + (G[1] - C[1]) * t
        if bx0 <= x <= bx1 and by <= y <= gy:
            hit = (x, y, t)
            break
    m = 0.1  # metres per px
    svg.line(*C, hit[0], hit[1], P.lavender, 2.5)
    svg.line(hit[0], hit[1], *G, P.lavender_60, 2, stroke_dasharray="5 7")
    svg.circle(hit[0], hit[1], 8, P.lavender)
    svg.circle(*G, 9, "none", stroke=P.white, stroke_width=2.5)
    svg.circle(*C, 9, P.white)
    near, far = math.dist(C, hit[:2]) * m, math.dist(C, G) * m
    label(svg, G[0], gy + 40, "ground point", P.white, size=17)
    label(svg, hit[0] + 18, hit[1] - 14, f"nearest {near:.0f} m", P.lavender, "start", 17)
    label(svg, G[0], gy + 72, f"{far:.0f} m away: hidden", P.black_60, size=16)
    svg.rect(G[0] - 40, gy - 5, 80, 10, P.black_80, rx=3, stroke=P.lavender_60, stroke_width=1.5, stroke_dasharray="3 3")
    label(svg, G[0], gy + 104, "no test: the wall's colour lands here", P.lavender_60, size=15)

    return run(svg, "ghost.", "don't paint the ground with the wall in front of it", """
hidden = depth > zbuf[v, u] + eps    # something nearer took this pixel""", dark=True)


def _clip(poly, a, b, c):
    """Keep the part of a polygon where a·x + b·y <= c (Sutherland–Hodgman, one half-plane)."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def seams() -> Svg:
    """Each ortho pixel takes the most nadir photo: on flat ground, a Voronoi diagram of the points below the cameras."""
    svg = Svg(P.cream)
    rng = random.Random(17)
    sites = [(190 + 175 * c + rng.uniform(-22, 22) + (r % 2) * 40, 380 + 200 * r + rng.uniform(-20, 20)) for r in range(3) for c in range(5)]
    box = [(130, 310), (950, 310), (950, 960), (130, 960)]
    cells = []
    for i, s in enumerate(sites):
        poly = box
        for j, t in enumerate(sites):
            if i != j:
                a, b = t[0] - s[0], t[1] - s[1]
                poly = _clip(poly, a, b, (t[0] ** 2 - s[0] ** 2 + t[1] ** 2 - s[1] ** 2) / 2)
        cells.append(poly)
    nbr = {i: {j for j in range(len(sites)) if j != i and
               sum(1 for p in cells[i] for q in cells[j] if math.dist(p, q) < 1) >= 2} for i in range(len(sites))}
    pal = [P.blue_20, P.lavender_20, P.teal_20, P.white]
    col = {}
    for i in range(len(sites)):
        used = {col[j] for j in nbr[i] if j in col}
        col[i] = next(c for c in range(4) if c not in used)
    for i, poly in enumerate(cells):
        svg.poly(poly, pal[col[i]], stroke=P.blue, stroke_width=2, stroke_linejoin="round")
    for s in sites:
        svg.circle(*s, 7, P.black)
    label(svg, 950, 995, "dots: straight below each camera · lines: seamlines", P.black_60, "end", 15)

    return run(svg, "seams.", "each pixel from the photo looking straight at it", """
best = argmin(theta)    # Brighton: 9° median, not 23°""")


def gain() -> Svg:
    """Gain compensation: auto exposure makes the same ground differ per photo; one gain each, fitted on the overlaps."""
    svg = Svg(P.white)
    e = [1.59, 1.2, 0.95, 0.8, 0.68, 1.05]
    n = len(e)
    lg = [0.0] * n
    for _ in range(400):
        for i in range(n):
            nb = [j for j in (i - 1, i + 1) if 0 <= j < n]
            lg[i] = sum(lg[j] + math.log(e[j]) - math.log(e[i]) for j in nb) / len(nb)
        mean = sum(lg) / n
        lg = [v - mean for v in lg]
    g = [math.exp(v) for v in lg]
    fw, fh, step, x0 = 230, 130, 128, 140
    for row, y in enumerate((380, 680)):
        for i in range(n):
            v = 150 * e[i] * (g[i] if row else 1)
            svg.rect(x0 + i * step, y + (i % 2) * 18, fw, fh, gray(v), rx=4, stroke=P.white, stroke_width=2, opacity=0.92)
        if row:
            for i in range(n):
                label(svg, x0 + i * step + step / 2, y + fh + 64, f"{g[i]:.2f}", P.blue, size=17)
    label(svg, x0, 350, "as shot: auto exposure", P.black_60, "start", 17)
    label(svg, x0, 650, "after one gain per photo", P.black_60, "start", 17)

    return run(svg, "gain.", "same ground, same brightness", f"""
min Σ (log(g_i * I_i) - log(g_j * I_j))**2    # over every overlap
# mean log g = 0 · gains {min(g):.2f} to {max(g):.2f}""")


def blend() -> Svg:
    """Multi-band blending: cross a seam frequency by frequency, brightness over a wide zone, edges over a pixel."""
    svg = Svg(P.cream)
    x0, x1, sx = 160, 920, 540
    rows = [("no blend: a hard seam", 0)] + [(f"band {k + 1}" + (" · coarse: brightness" if k == 0 else " · fine: edges" if k == 4 else ""),
                                              12 * 2 ** (4 - k)) for k in range(5)]
    for r, (name, wid) in enumerate(rows):
        y = 360 + 108 * r
        svg.text(x0, y - 22, name, "codel", 16, P.black_60 if r == 0 else P.black)
        pts = []
        for x in range(x0, x1 + 1, 4):
            w = (1 if x >= sx else 0) if wid == 0 else 1 / (1 + math.exp(-(x - sx) / (wid / 4)))
            pts.append((x, y + 40 - 40 * w))
        svg.polyline(pts, P.black_60 if r == 0 else P.blue, 3)
        svg.line(x0, y + 40, x1, y + 40, P.black_20, 1)
    svg.line(sx, 320, sx, 360 + 108 * 5 + 50, P.lavender, 1.5, stroke_dasharray="4 6")
    label(svg, x0, 360 + 108 * 5 + 80, "photo A", P.black_60, "start", 16)
    label(svg, x1, 360 + 108 * 5 + 80, "photo B", P.black_60, "end", 16)
    label(svg, sx, 360 + 108 * 5 + 80, "seam", P.lavender, size=16)

    return run(svg, "blend.", "brightness over metres, edges over a pixel", """
out = Σ_k mix(L_k(A), L_k(B), smooth(seam, 2**k))   # Burt & Adelson 1983""", size=21)


def true_() -> Svg:
    """Three orthophotos of one building: on a plane, on bare ground, and the true ortho on the DSM with occlusion."""
    svg = Svg(P.white)
    tw = 250
    for k, (name, sub_) in enumerate((("rectified", "on a plane"), ("classic", "on bare ground"), ("true", "on the DSM, occlusion"))):
        ox, oy = 110 + k * 300, 460
        svg.rect(ox, oy, tw, tw, P.white, stroke=P.black_20, stroke_width=1.5, rx=4)
        fp = (ox + 80, oy + 80, 90, 90)
        lean_ = (26, 30) if k < 2 else (0, 0)
        road = [(ox + 10, oy + 210 + (14 * math.sin(t / 30) if k == 0 else 0)) for t in range(0, tw - 19, 10)]
        road = [(ox + 10 + i * 10, y) for i, (_, y) in enumerate(road)]
        svg.polyline(road, P.black_60, 6)
        svg.rect(*fp, "none", stroke=P.black_60, stroke_width=2, stroke_dasharray="5 5")
        if lean_ != (0, 0):
            x, y, w, h = fp
            dx, dy = lean_
            svg.poly([(x + w, y), (x + w + dx, y + dy), (x + w + dx, y + h + dy), (x + w, y + h)], P.lavender_60)
            svg.poly([(x, y + h), (x + w, y + h), (x + w + dx, y + h + dy), (x + dx, y + h + dy)], P.lavender_60)
        svg.rect(fp[0] + lean_[0], fp[1] + lean_[1], fp[2], fp[3], P.blue, rx=2)
        svg.text(ox, oy - 52, name, "code", 22, P.blue if k == 2 else P.black)
        svg.text(ox, oy - 22, sub_, "codel", 15, P.black_60)
    label(svg, 110, 800, "dashed: the footprint · lavender: walls that shouldn't show", P.black_60, "start", 15)

    return run(svg, "true.", "three orthophotos of one building", """
surface, occlusion = dsm, True    # roofs on their footprints, walls gone""")


# ============================================================================
# registry
# ============================================================================
FAMILIES = {
    "ingest": ["join", "manifest", "early"],
    "select": ["footprint", "overlap", "gsd", "thin"],
    "extract": ["gop", "jpeg", "shrink"],
    "sfm": ["keypoint", "descriptor", "ratio", "pairs", "ransac", "islands", "grow", "track", "reproject", "bundle",
            "robust", "gauge", "focal", "invert", "dome", "priors"],
    "georef": ["helmert", "residual", "offset", "hinge", "enu", "utm", "datum", "float"],
    "dense": ["undistort", "views", "depth", "ncc", "propagate", "baseline", "agree", "mirror"],
    "dsm": ["median", "spacing", "spike", "fill", "corner", "ndsm", "nmad"],
    "ortho": ["backward", "lean", "slant", "ghost", "seams", "gain", "blend", "true"],
}


def main(names: set[str]) -> None:
    for family, fns in FAMILIES.items():
        for name in fns:
            fn = globals().get(name + "_") or globals().get(name)  # float, true: avoid builtins
            if fn is None or (names and name not in names):
                continue
            svg = fn()
            out = OUT / family / f"{name}.svg"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(svg.render())
            bad = missing_glyphs(svg)
            print(out.relative_to(OUT.parents[1]), f"{out.stat().st_size // 1024} KB", "MISSING " + " ".join(bad) if bad else "")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
