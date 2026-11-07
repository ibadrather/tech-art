"""Vision posters: the first things to know about cameras and computer vision.

Minimal like minimal.py: one word, one drawing, one formula, lots of empty paper. Every drawing is
computed from the formula printed under it (rays are intersected, grids are projected, pixels are
sampled), so the pictures are right, not just pretty.

Camera:    pinhole. lens. zoom. intrinsic. distort. fisheye.
Shutter:   rolling. global. expose. blur.
Geometry:  ray. size. pose. disparity. vanish. homography. epipolar.
Image:     pixel. bayer. edge.

Run:  uv run --no-project --with fonttools --with brotli python src/vision.py [name ...]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from drone import missing_glyphs  # noqa: E402
from posters import CODE_Y, M, W, code_rule, fit  # noqa: E402
from sensors import arrow  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "vision"
CX, CY = W / 2, 640  # centre of the drawing


# ============================================================================
# shared furniture
# ============================================================================
def label(svg: Svg, x, y, s, fill=P.black_60, anchor="middle", size=20):
    svg.text(x, y, s, "codel", size, fill, anchor)


def dim(svg: Svg, a, b, s, fill=P.black_60, tick=10):
    """A dimension line from a to b (horizontal or vertical) with end ticks and a label beside it."""
    svg.line(*a, *b, fill, 1.5)
    horiz = abs(b[1] - a[1]) < abs(b[0] - a[0])
    for p in (a, b):
        if horiz:
            svg.line(p[0], p[1] - tick, p[0], p[1] + tick, fill, 1.5)
        else:
            svg.line(p[0] - tick, p[1], p[0] + tick, p[1], fill, 1.5)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if horiz:
        label(svg, mx, my + 34, s, fill)
    else:
        label(svg, mx + 22, my + 7, s, fill, "start")


def ellipse(svg: Svg, cx, cy, rx, ry, fill, **kw):
    attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    svg.add(f'<ellipse cx="{_fmt(cx)}" cy="{_fmt(cy)}" rx="{_fmt(rx)}" ry="{_fmt(ry)}" fill="{fill}"{attrs}/>')


def mix(a: str, b: str, t: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def gray(v: float) -> str:
    """0..255 as a grey between Rich Black and white."""
    return mix(P.black, P.white, max(0.0, min(1.0, v / 255)))


# small 3-vector helpers
def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, s):
    return tuple(x * s for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


# ============================================================================
# camera
# ============================================================================
def pinhole() -> Svg:
    """A camera is a box with a hole: rays cross at the hole and land upside down, scaled by f / Z."""
    svg = Svg(P.white)
    hole, f, Z = (600, CY), 250, 400
    ox, sx = hole[0] - Z, hole[0] + f
    top, base = -200, 90  # object tip and foot, relative to the axis (page y, up is negative)

    def img(dy):  # x = -f X / Z: through the hole, flipped
        return CY - dy * f / Z

    svg.line(ox - 50, CY, sx + 60, CY, P.black_20, 1.5, stroke_dasharray="6 8")
    for dy in (top, base):
        svg.line(ox, CY + dy, sx, img(dy), P.lavender_60, 2)
    svg.rect(hole[0] - 7, 380, 14, CY - 9 - 380, P.black)
    svg.rect(hole[0] - 7, CY + 9, 14, 900 - CY - 9, P.black)
    svg.rect(sx + 8, 470, 6, 340, P.lavender_60)  # the screen at the back of the box
    arrow(svg, (ox, CY + base), (ox, CY + top), P.blue, 8, 34)
    arrow(svg, (sx, img(base)), (sx, img(top)), P.teal, 6, 26)
    label(svg, ox - 34, CY + top / 2 + 8, "X", P.blue, "end", 26)
    label(svg, sx + 40, img(top) / 2 + CY / 2 + 8, "x", P.teal, "start", 26)
    dim(svg, (ox, 950), (hole[0], 950), "Z")
    dim(svg, (hole[0], 950), (sx, 950), "f")

    svg.frame("pinhole.", "one hole, one picture · upside down")
    code_rule(svg)
    svg.code(M, CODE_Y, """
x = f * X / Z      # farther away, smaller
y = f * Y / Z      # the hole flips it over""", "py", 22)
    return svg


def lens() -> Svg:
    """Thin lens: three rays from one point meet again at one point, and 1/f = 1/u + 1/v says where."""
    svg = Svg(P.cream)
    f, u, h = 150, 330, 150
    v = 1 / (1 / f - 1 / u)
    hi = h * v / u  # image height, inverted
    L = CX
    ox, ix = L - u, L + v
    tip, itip = (ox, CY - h), (ix, CY + hi)

    svg.line(110, CY, 970, CY, P.black_20, 1.5, stroke_dasharray="6 8")
    ellipse(svg, L, CY, 24, 250, P.lavender_20, stroke=P.lavender, stroke_width=3)
    ray = dict(stroke_linecap="round")
    svg.polyline([tip, (L, CY - h), itip], P.blue_40, 2.5, **ray)  # parallel in, through F out
    svg.line(*tip, *itip, P.blue_40, 2.5, **ray)  # straight through the centre
    y_hit = CY - h + h / (u - f) * u  # through F in, parallel out
    svg.polyline([tip, (L, y_hit), itip], P.blue_40, 2.5, **ray)
    for fx in (L - f, L + f):
        svg.circle(fx, CY, 7, P.black)
        label(svg, fx, CY + 38, "F", P.black, size=22)
    arrow(svg, (ox, CY), tip, P.blue, 7, 30)
    arrow(svg, (ix, CY), itip, P.teal, 6, 26)
    dim(svg, (ox, 930), (L, 930), "u")
    dim(svg, (L, 930), (ix, 930), "v")

    svg.frame("lens.", "a thin lens · sharp at one distance")
    code_rule(svg)
    svg.code(M, CODE_Y, """
1/f = 1/u + 1/v    # object at u, sharp image at v""", "py", 22)
    return svg


def zoom() -> Svg:
    """Field of view: the same sensor behind a 24 mm and an 85 mm lens."""
    svg = Svg(P.white)
    apex, R, w = (CX, 950), 600, 36.0

    def wedge(fl, fill, **kw):
        half = math.atan(w / (2 * fl))
        arc = [(apex[0] + R * math.sin(a), apex[1] - R * math.cos(a))
               for a in (-half + 2 * half * k / 60 for k in range(61))]
        svg.poly([apex] + arc, fill, **kw)
        return math.degrees(2 * half)

    wide = wedge(24, P.lavender_20, stroke=P.lavender, stroke_width=3, stroke_linejoin="round")
    tele = wedge(85, P.blue)
    svg.rect(apex[0] - 46, apex[1] - 4, 92, 50, P.black, rx=8)
    label(svg, CX - 178, 600, "24 mm", P.lavender, size=24)
    label(svg, CX - 178, 634, f"{wide:.0f}°", P.lavender, size=24)
    label(svg, CX, apex[1] - R - 54, f"85 mm · {tele:.0f}°", P.blue, size=24)

    svg.frame("zoom.", "field of view · longer lens, narrower view")
    code_rule(svg)
    svg.code(M, CODE_Y, """
fov = 2 * atan(w / (2 * f))   # w: sensor width, 36 mm here""", "py", 22)
    return svg


def intrinsic() -> Svg:
    """The camera matrix K in pixels: focal lengths and the principal point, origin top-left."""
    svg = Svg(P.black)
    x0, y0, w, h = 150, 380, 780, 520
    for k in range(1, 12):
        svg.line(x0 + w * k / 12, y0, x0 + w * k / 12, y0 + h, "#1C1C1C", 1)
    for k in range(1, 8):
        svg.line(x0, y0 + h * k / 8, x0 + w, y0 + h * k / 8, "#1C1C1C", 1)
    svg.rect(x0, y0, w, h, "none", stroke=P.black_60, stroke_width=2)
    arrow(svg, (x0, y0), (x0 + 170, y0), P.teal_60, 5, 24)
    arrow(svg, (x0, y0), (x0, y0 + 170), P.teal_60, 5, 24)
    label(svg, x0 + 160, y0 + 44, "u", P.teal_60, size=24)
    label(svg, x0 + 30, y0 + 168, "v", P.teal_60, "start", 24)
    label(svg, x0 - 12, y0 - 20, "(0, 0)", P.blue_40, "start", 18)

    c = (x0 + w / 2, y0 + h / 2)
    svg.line(c[0], y0, c[0], c[1], P.black_80, 1.5, stroke_dasharray="5 7")
    svg.line(x0, c[1], c[0], c[1], P.black_80, 1.5, stroke_dasharray="5 7")
    label(svg, c[0], y0 - 20, "cx", P.white, size=22)
    label(svg, x0 - 18, c[1] + 8, "cy", P.white, "end", 22)
    svg.circle(*c, 10, P.white)

    p = (c[0] + 230, c[1] - 150)
    svg.line(c[0], c[1], p[0], c[1], P.lavender, 3)
    svg.line(p[0], c[1], *p, P.lavender, 3)
    svg.circle(*p, 12, P.lavender)
    label(svg, (c[0] + p[0]) / 2, c[1] + 36, "fx · X/Z", P.lavender, size=19)
    label(svg, p[0] + 16, (c[1] + p[1]) / 2 + 7, "fy · Y/Z", P.lavender, "start", 19)

    svg.frame("intrinsic.", "the camera matrix · everything in pixels", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
K = [[fx,  0, cx],
     [ 0, fy, cy],      # u = fx·X/Z + cx
     [ 0,  0,  1]]      # v = fy·Y/Z + cy""", "py", 22, dark=True)
    return svg


def distort() -> Svg:
    """Radial distortion: a straight grid pulled into a barrel by k1 r² + k2 r⁴."""
    svg = Svg(P.white)
    k1, k2, s, n = -0.12, -0.012, 300, 8

    def warp(x, y):
        r2 = x * x + y * y
        g = 1 + k1 * r2 + k2 * r2 * r2
        return CX + s * x * g, CY + s * y * g

    ticks = [-1 + 2 * i / n for i in range(n + 1)]
    for t in ticks:
        svg.line(CX + s * t, CY - s, CX + s * t, CY + s, P.lavender_60, 1.5, stroke_dasharray="6 7")
        svg.line(CX - s, CY + s * t, CX + s, CY + s * t, P.lavender_60, 1.5, stroke_dasharray="6 7")
    samp = [-1 + 2 * k / 60 for k in range(61)]
    for t in ticks:
        w = 4 if abs(t) == 1 else 2.5
        svg.polyline([warp(t, q) for q in samp], P.blue, w)
        svg.polyline([warp(q, t) for q in samp], P.blue, w)

    svg.frame("distort.", "real lenses bend straight lines · barrel")
    code_rule(svg)
    svg.code(M, CODE_Y, """
r2  = x*x + y*y
x_d = x * (1 + k1*r2 + k2*r2*r2)    # k1 < 0: barrel""", "py", 22)
    return svg


def fisheye() -> Svg:
    """Where a ray at angle θ lands: f·tan θ runs off to infinity, a fisheye's f·θ doesn't."""
    svg = Svg(P.cream)
    ox, oy, gw, gh, rmax = 190, 900, 700, 520, 3.0

    def g(th_deg, r):
        return ox + gw * th_deg / 90, oy - gh * r / rmax

    for th in (30, 60, 90):
        svg.line(*g(th, 0), *g(th, rmax), P.black_20, 1)
        label(svg, g(th, 0)[0], oy + 36, f"{th}°", size=18)
    for r in (1, 2, 3):
        svg.line(*g(0, r), *g(90, r), P.black_20, 1)
        label(svg, ox - 16, g(0, r)[1] + 6, f"{r}f" if r > 1 else "f", anchor="end", size=18)
    svg.line(ox, oy, ox + gw, oy, P.black, 2)
    svg.line(ox, oy, ox, oy - gh, P.black, 2)
    label(svg, ox - 16, oy + 36, "0", anchor="end", size=18)
    label(svg, ox + gw / 2, oy + 74, "θ  angle off the axis", P.black, size=18)
    label(svg, ox, oy - gh - 22, "r  distance on the sensor", P.black, "start", 18)

    th_max = math.degrees(math.atan(rmax))
    pin = [g(t, math.tan(math.radians(t))) for t in (th_max * k / 80 for k in range(81))]
    svg.polyline(pin, P.lavender, 6)
    arrow(svg, pin[-2], (pin[-1][0] + 3, pin[-1][1] - 26), P.lavender, 6, 24)
    eye = [g(t, math.radians(t)) for t in (90 * k / 80 for k in range(81))]
    svg.polyline(eye, P.teal, 6)
    svg.circle(*eye[-1], 9, P.teal)
    label(svg, pin[-1][0] - 48, pin[-1][1] + 14, "pinhole  f·tan θ", P.lavender, "end", 22)
    label(svg, eye[-1][0] - 4, eye[-1][1] - 26, "fisheye  f·θ", P.teal, "end", 22)

    svg.frame("fisheye.", "two camera models · where a ray lands")
    code_rule(svg)
    svg.code(M, CODE_Y, """
r = f * tan(θ)    # pinhole: 90° lands at infinity
r = f * θ         # fisheye: 180° still fits""", "py", 22)
    return svg


# ============================================================================
# shutter
# ============================================================================
def _readout(rolling: bool) -> Svg:
    """A bar moving right, read row by row (rolling) or all at once (global), with each row's exposure in time."""
    svg = Svg(P.white)
    n, rh, y0 = 12, 40, 400
    fx0, fx1, tx0, tx1 = M, 556, 636, W - M
    step, expo = (21, 104) if rolling else (0, 104)
    bar = P.blue if rolling else P.teal
    label(svg, fx0, y0 - 24, "image", P.black, "start", 18)
    label(svg, tx0, y0 - 24, "time →", P.black, "start", 18)
    for r in range(n):
        y = y0 + r * rh
        svg.rect(fx0, y, fx1 - fx0, rh - 5, P.lavender_20)
        svg.rect(220 + step * 0.8 * r, y, 74, rh - 5, P.black)
        svg.rect(tx0 + 24 + step * r, y + 9, expo, rh - 23, bar, rx=(rh - 23) / 2)
    svg.line(tx0, y0 - 6, tx0, y0 + n * rh, P.black_20, 1.5)
    ylab = y0 + n * rh + 40
    arrow(svg, (220, ylab), (400, ylab), P.black_60, 3, 16)
    label(svg, 420, ylab + 7, "moving", anchor="start", size=18)
    if rolling:
        label(svg, tx1, ylab + 7, "row by row", P.blue, "end", 18)
    else:
        label(svg, tx1, ylab + 7, "all rows together", P.teal, "end", 18)
    return svg


def rolling() -> Svg:
    svg = _readout(True)
    svg.frame("rolling.", "rolling shutter · one row after another")
    code_rule(svg)
    svg.code(M, CODE_Y, """
t_row  = t0 + row * t_line    # each row a little later
x_seen = x + v * t_row        # so a moving bar leans""", "py", 22)
    return svg


def global_() -> Svg:
    svg = _readout(False)
    svg.frame("global.", "global shutter · every row at once")
    code_rule(svg, P.teal)
    svg.code(M, CODE_Y, """
t_row  = t0                   # one instant for all rows
x_seen = x + v * t0           # so the bar stays straight""", "py", 22)
    return svg


def expose() -> Svg:
    """Aperture and shutter time trade one for one: each column lets in the same light."""
    svg = Svg(P.black)
    stops = [1.4, 2, 2.8, 4, 5.6, 8]
    times = [1000, 500, 250, 125, 60, 30]
    xs = [160 + i * 152 for i in range(6)]
    label(svg, M, 410, "aperture  f/N", P.blue_40, "start", 18)
    label(svg, M, 680, "shutter  t", P.blue_40, "start", 18)
    for x, N, t in zip(xs, stops, times):
        svg.circle(x, 510, 66, "none", stroke=P.black_80, stroke_width=3)
        svg.circle(x, 510, 62 * 1.4 / N, P.lavender)
        label(svg, x, 616, f"f/{N:g}", P.white, size=19)
        hgt = 192 * 30 / t
        svg.rect(x - 22, 900 - hgt, 44, hgt, P.teal_60, rx=4)
        label(svg, x, 936, f"1/{t}", P.white, size=19)
    svg.line(M, 970, W - M, 970, P.black_80, 1.5)
    label(svg, CX, 1000, "same light in every column", P.lavender, size=18)

    svg.frame("expose.", "aperture × time · one stop = 2× the light", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
light ~ t / N**2     # halve the area, double the time""", "py", 22, dark=True)
    return svg


def blur() -> Svg:
    """Motion blur: whatever moves while the shutter is open smears by v · t."""
    svg = Svg(P.cream)
    v, sc, x0, r = 12000, 3.0, 170, 26
    arrow(svg, (x0, 400), (x0 + 220, 400), P.teal, 4, 20)
    label(svg, x0 + 240, 407, f"v = {v // 1000} 000 px/s", P.teal, "start", 20)
    for i, t in enumerate((1000, 250, 60)):
        y = 540 + i * 160
        px = v / t
        svg.rect(x0 - r, y - r, px * sc + 2 * r, 2 * r, P.blue, rx=r, opacity=0.85)
        label(svg, x0 - r, y - r - 18, f"t = 1/{t} s", P.black, "start", 18)
        label(svg, x0 + px * sc + r + 18, y + 7, f"{px:.0f} px", P.blue, "start", 20)

    svg.frame("blur.", "motion blur · moving while the shutter is open")
    code_rule(svg)
    svg.code(M, CODE_Y, """
blur_px = v_px * t_exp     # shorter exposure, sharper""", "py", 22)
    return svg


# ============================================================================
# geometry
# ============================================================================
def ray() -> Svg:
    """Back-projection: a pixel is a ray, and every point along it lands on that same pixel."""
    svg = Svg(P.white)
    C, f, dy = (150, 780), 110, -62  # camera centre, focal length, pixel offset on the plane
    k = dy / f
    svg.line(C[0], C[1], 990, C[1], P.black_20, 1.5, stroke_dasharray="6 8")
    end = (995, C[1] + k * (995 - C[0]))
    svg.line(*C, *end, P.blue_40, 3)
    svg.line(C[0] + f, C[1] - 150, C[0] + f, C[1] + 110, P.lavender, 6, stroke_linecap="round")
    px = (C[0] + f, C[1] + dy)
    svg.rect(px[0] - 11, px[1] - 11, 22, 22, P.teal)
    for z in (1, 2, 3, 4):
        x = C[0] + 200 * z
        p = (x, C[1] + k * (x - C[0]))
        svg.circle(*p, 10 + 3 * z, P.blue)
        label(svg, p[0] + 6, p[1] + 52 + 3 * z, f"Z = {z}", size=18)
    svg.circle(*C, 11, P.black)
    label(svg, C[0], C[1] + 50, "camera", size=18)
    label(svg, px[0] - 22, px[1] - 4, "pixel", P.teal, "end", 18)

    svg.frame("ray.", "one pixel, one ray · depth is lost")
    code_rule(svg)
    svg.code(M, CODE_Y, """
d = inv(K) @ [u, v, 1]    # the ray through pixel (u, v)
X = Z * d                 # any Z lands on the same pixel""", "py", 22)
    return svg


def size() -> Svg:
    """Known size, unknown distance: twice as far is half as tall, so Z = f · H / h."""
    svg = Svg(P.cream)
    C, f, H = (140, 680), 110, 230
    near, far = 320, 640
    svg.line(C[0], C[1], C[0] + far + 40, C[1], P.black_20, 1.5, stroke_dasharray="6 8")
    svg.line(C[0] + f, C[1] - 120, C[0] + f, C[1] + 120, P.lavender_60, 4, stroke_linecap="round")
    for Z, col, wdt in ((far, P.lavender, 10), (near, P.blue, 16)):
        x = C[0] + Z
        for s in (-1, 1):
            svg.line(*C, x, C[1] + s * H / 2, col, 1.8)
        svg.rect(x - 22, C[1] - H / 2, 44, H, col, rx=6)
        h = f * H / Z
        svg.line(C[0] + f, C[1] - h / 2, C[0] + f, C[1] + h / 2, col, wdt, stroke_linecap="butt")
    svg.circle(*C, 10, P.black)
    label(svg, C[0] + f, C[1] - 140, "image", P.lavender, size=18)
    dim(svg, (C[0], 880), (C[0] + near, 880), "Z")
    dim(svg, (C[0], 960), (C[0] + far, 960), "2Z")
    dim(svg, (C[0] + far + 70, C[1] - H / 2), (C[0] + far + 70, C[1] + H / 2), "H")

    svg.frame("size.", "twice as far, half as tall")
    code_rule(svg)
    svg.code(M, CODE_Y, """
h = f * H / Z     # size on the sensor
Z = f * H / h     # know H, measure h, get the distance""", "py", 22)
    return svg


def pose() -> Svg:
    """Extrinsics from above: the camera sits t away from the world origin, turned by R."""
    svg = Svg(P.cream)
    O, C = (230, 880), (620, 600)
    th = math.radians(45)  # camera x-axis, measured from world x (page y is down, so this turns clockwise)
    xc = (math.cos(th), math.sin(th))
    zc = (xc[1], -xc[0])  # forward: x is to its right
    L, half = 230, 150
    tip = (C[0] + L * zc[0], C[1] + L * zc[1])
    svg.poly([C, (tip[0] + half * xc[0], tip[1] + half * xc[1]), (tip[0] - half * xc[0], tip[1] - half * xc[1])],
             P.lavender_20, stroke=P.lavender, stroke_width=2.5, stroke_linejoin="round")

    arrow(svg, O, (O[0] + 260, O[1]), P.black, 5, 26)
    arrow(svg, O, (O[0], O[1] - 260), P.black, 5, 26)
    label(svg, O[0] + 290, O[1] + 9, "x", P.black, "start", 26)
    label(svg, O[0], O[1] - 290, "y", P.black, size=26)
    svg.circle(*O, 10, P.black)
    label(svg, O[0] - 20, O[1] + 46, "world", size=18)

    d = (C[0] - O[0], C[1] - O[1])
    n = math.hypot(*d)
    a, b = (O[0] + d[0] * 24 / n, O[1] + d[1] * 24 / n), (C[0] - d[0] * 24 / n, C[1] - d[1] * 24 / n)
    arrow(svg, a, b, P.teal, 4, 22)
    label(svg, (O[0] + C[0]) / 2 + 24, (O[1] + C[1]) / 2 + 34, "t", P.teal, "start", 30)

    svg.line(C[0], C[1], C[0] + 190, C[1], P.black_20, 2, stroke_dasharray="6 8")
    svg.arc(C[0], C[1], 120, 0, th, P.blue, 3)
    label(svg, C[0] + 152 * math.cos(th / 2) + 4, C[1] + 152 * math.sin(th / 2) + 10, "R", P.blue, "start", 30)
    arrow(svg, C, (C[0] + 170 * xc[0], C[1] + 170 * xc[1]), P.blue, 5, 24)
    arrow(svg, C, (C[0] + 170 * zc[0], C[1] + 170 * zc[1]), P.blue, 5, 24)
    label(svg, C[0] + 200 * xc[0] + 8, C[1] + 200 * xc[1] + 14, "x", P.blue, "start", 24)
    label(svg, C[0] + 196 * zc[0] - 6, C[1] + 196 * zc[1] - 10, "z", P.blue, "end", 24)
    svg.circle(*C, 11, P.blue)
    label(svg, C[0] - 24, C[1] + 8, "camera", P.blue, "end", 18)

    svg.frame("pose.", "where the camera is · world to camera")
    code_rule(svg)
    svg.code(M, CODE_Y, """
X_cam = R @ X_world + t     # turn, then shift""", "py", 22)
    return svg


def disparity() -> Svg:
    """Stereo from above: one point, two cameras a baseline apart; its shift between images gives depth."""
    svg = Svg(P.white)
    yc, f, hw = 900, 100, 92
    cams = (360, 720)
    Pt = (600, 400)
    Z = yc - Pt[1]
    hits = []
    for x in cams:
        svg.poly([(x, yc), (x - hw, yc - f), (x + hw, yc - f)], P.lavender_20)
        svg.line(x, yc, x, yc - f - 40, P.black_20, 1.5, stroke_dasharray="5 6")
        svg.line(*Pt, x, yc, P.blue_40, 2.5)
        svg.line(x - hw, yc - f, x + hw, yc - f, P.lavender, 6, stroke_linecap="round")
        hx = x + (Pt[0] - x) * f / Z
        hits.append(hx - x)
        svg.circle(hx, yc - f, 9, P.teal)
        svg.circle(x, yc, 10, P.black)
    label(svg, cams[0] - hw, yc - f - 22, "x_left", P.teal, "start", 18)
    label(svg, cams[1] + hw, yc - f - 22, "x_right", P.teal, "end", 18)
    svg.circle(*Pt, 15, P.blue)
    label(svg, Pt[0] + 30, Pt[1] + 8, "P", P.blue, "start", 26)
    dim(svg, (cams[0], 960), (cams[1], 960), "B")
    dim(svg, (900, Pt[1]), (900, yc), "Z")

    svg.frame("disparity.", "two eyes · the shift tells the depth")
    code_rule(svg)
    svg.code(M, CODE_Y, """
d = x_left - x_right    # disparity, in pixels
Z = f * B / d           # near: big shift · far: small""", "py", 22)
    return svg


def vanish() -> Svg:
    """Perspective: parallel rails and a line of poles all run to one vanishing point on the horizon."""
    svg = Svg(P.black)
    f, h, cx, cy = 520, 1.5, CX, 540

    def proj(x, y, z):  # camera frame: y down, ground at y = h
        return cx + f * x / z, cy + f * y / z

    svg.line(M, cy, W - M, cy, P.black_80, 1.5, stroke_dasharray="6 8")
    zmin = f * h / (985 - cy)
    z = zmin
    while z < 80:  # sleepers every 0.6 m
        a, b = z, z + 0.22
        svg.poly([proj(-1.5, h, a), proj(1.5, h, a), proj(1.5, h, b), proj(-1.5, h, b)], P.black_80)
        z += 0.6
    for x in (-1.1, 1.1):
        svg.line(*proj(x, h, zmin), cx, cy, P.lavender, 4)
    tops = []
    for z in (4.0, 5.6, 7.8, 11, 15.5, 22, 31):
        b, t = proj(3.0, h, z), proj(3.0, h - 3.2, z)
        svg.line(*b, *t, P.teal_60, max(1.5, 26 / z), stroke_linecap="round")
        tops.append(t)
    svg.line(*tops[0], cx, cy, P.teal_60, 1.5, stroke_dasharray="4 8")
    svg.line(*proj(3.0, h, 4.0), cx, cy, P.teal_60, 1.5, stroke_dasharray="4 8")
    svg.circle(cx, cy, 10, P.white)
    label(svg, cx, cy - 32, "vanishing point", P.white, size=18)
    label(svg, M, cy - 16, "horizon", P.blue_40, "start", 18)

    svg.frame("vanish.", "parallel lines meet · at the horizon", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
v = K @ d     # every line with direction d ends at v""", "py", 22, dark=True)
    return svg


def _solve(A, b):
    """Gaussian elimination with partial pivoting."""
    n = len(b)
    A = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        for r in range(n):
            if r != i:
                k = A[r][i] / A[i][i]
                A[r] = [a - k * c for a, c in zip(A[r], A[i])]
    return [A[i][n] / A[i][i] for i in range(n)]


def homography() -> Svg:
    """Plane to plane: a checkerboard seen at an angle and the same board straightened by one 3×3 matrix."""
    svg = Svg(P.white)
    src = [(0, 0), (1, 0), (1, 1), (0, 1)]
    dst = [(200, 470), (440, 500), (480, 830), (110, 790)]  # where the corners land in the photo
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = _solve(A, b) + [1.0]

    def Hp(x, y):
        w = h[6] * x + h[7] * y + h[8]
        return ((h[0] * x + h[1] * y + h[2]) / w, (h[3] * x + h[4] * y + h[5]) / w)

    n, sq, rx, ry = 4, 360, 620, 470
    for i in range(n):
        for j in range(n):
            col = P.blue if (i + j) % 2 == 0 else P.blue_20
            cell = [(i / n, j / n), ((i + 1) / n, j / n), ((i + 1) / n, (j + 1) / n), (i / n, (j + 1) / n)]
            svg.poly([Hp(*c) for c in cell], col)
            svg.poly([(rx + sq * x, ry + sq * y) for x, y in cell], col)
    svg.poly(dst, "none", stroke=P.black, stroke_width=3, stroke_linejoin="round")
    svg.rect(rx, ry, sq, sq, "none", stroke=P.black, stroke_width=3)
    arrow(svg, (500, 650), (588, 650), P.teal, 4, 20)
    label(svg, 544, 630, "H", P.teal, size=28)
    label(svg, 295, 900, "photo", size=18)
    label(svg, rx + sq / 2, 900, "plane", size=18)

    svg.frame("homography.", "plane to plane · one 3×3 matrix")
    code_rule(svg)
    svg.code(M, CODE_Y, """
p = H @ [x, y, 1]                 # 8 numbers, from 4 points
u, v = p[0] / p[2], p[1] / p[2]   # divide by the last one""", "py", 22)
    return svg


def epipolar() -> Svg:
    """Two views: a pixel in the left image is a ray; seen from the right camera, that ray is a line."""
    svg = Svg(P.cream)
    f, hw, hh = 0.9, 0.62, 0.46
    X = (0.15, -0.35, 4.0)
    cams = []
    for cx_, yaw in ((-1.3, math.radians(14)), (1.3, math.radians(-14))):
        c, s = math.cos(yaw), math.sin(yaw)
        Rt = ((c, 0, s), (0, 1, 0), (-s, 0, c))  # camera axes (x, y, z) in world coords
        cams.append(((cx_, 0.0, 0.0), Rt))

    def to_world(cam, u, v):
        C, Rt = cam
        return add(C, add(mul(Rt[0], u), add(mul(Rt[1], v), mul(Rt[2], f))))

    def to_image(cam, Q):
        C, Rt = cam
        q = sub(Q, C)
        x, y, z = dot(q, Rt[0]), dot(q, Rt[1]), dot(q, Rt[2])
        return f * x / z, f * y / z

    a = math.radians(38)

    def view(p):  # look down onto the scene from behind the cameras
        x, y, z = p
        return (x, -(y * math.cos(a) - z * math.sin(a)))

    corners = [[to_world(cam, su * hw, sv * hh) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))] for cam in cams]
    allp = [view(p) for p in [X, cams[0][0], cams[1][0]] + corners[0] + corners[1]]
    fm = fit(allp, box=(M, 330, W - M, 990), pad=50)

    def g(p):
        return fm(view(p))

    C1, C2 = cams[0][0], cams[1][0]
    svg.poly([g(C1), g(C2), g(X)], P.lavender_20)
    svg.line(*g(C1), *g(C2), P.black_60, 1.5, stroke_dasharray="6 8")
    for k, cam in enumerate(cams):
        svg.poly([g(p) for p in corners[k]], P.white, stroke=P.black, stroke_width=2.5, stroke_linejoin="round",
                 opacity=0.92)
    # the ray from the left camera through X, with other depths it could have been
    far = add(C1, mul(sub(X, C1), 1.35))
    svg.line(*g(C1), *g(far), P.blue, 3)
    svg.line(*g(C2), *g(X), P.blue_40, 2.5)
    # its picture in the right image: project two points, clip the line to the image rectangle
    p0, p1 = to_image(cams[1], add(C1, mul(sub(X, C1), 0.35))), to_image(cams[1], add(C1, mul(sub(X, C1), 1.3)))
    d = sub(p1, p0)
    ts = []
    for i, lim in ((0, hw), (1, hh)):
        if abs(d[i]) > 1e-9:
            ts += [(-lim - p0[i]) / d[i], (lim - p0[i]) / d[i]]
    inside = sorted(t for t in ts if all(abs(p0[j] + t * d[j]) <= (hw, hh)[j] + 1e-9 for j in (0, 1)))
    ea, eb = (p0[0] + inside[0] * d[0], p0[1] + inside[0] * d[1]), (p0[0] + inside[-1] * d[0], p0[1] + inside[-1] * d[1])
    svg.line(*g(to_world(cams[1], *ea)), *g(to_world(cams[1], *eb)), P.teal, 4, stroke_linecap="round")
    for s in (0.62, 0.8, 1.25):
        Q = add(C1, mul(sub(X, C1), s))
        q = to_image(cams[1], Q)
        if abs(q[0]) > hw or abs(q[1]) > hh:
            continue
        svg.circle(*g(Q), 7, P.lavender)
        svg.circle(*g(to_world(cams[1], *q)), 6, P.lavender)
    svg.circle(*g(to_world(cams[0], *to_image(cams[0], X))), 9, P.teal)
    svg.circle(*g(to_world(cams[1], *to_image(cams[1], X))), 9, P.teal)
    svg.circle(*g(X), 14, P.blue)
    label(svg, g(X)[0] + 28, g(X)[1] + 8, "X", P.blue, "start", 26)
    for C, name in ((C1, "left"), (C2, "right")):
        svg.circle(*g(C), 9, P.black)
        label(svg, g(C)[0], g(C)[1] + 42, name, size=18)
    lab = g(to_world(cams[1], hw * 0.1, -hh))
    label(svg, lab[0], lab[1] - 22, "epipolar line", P.teal, size=18)

    svg.frame("epipolar.", "the match is on a line · search 1D, not 2D")
    code_rule(svg)
    svg.code(M, CODE_Y, """
x2.T @ F @ x1 == 0     # F: 3×3, the geometry of two views""", "py", 22)
    return svg


# ============================================================================
# image
# ============================================================================
def pixel() -> Svg:
    """An image is a grid of numbers: a dark disc on a light ground, edge pixels part-covered."""
    svg = Svg(P.white)
    n, cs = 10, 70
    x0, y0 = CX - n * cs / 2, 300
    ss = 8
    for j in range(n):
        for i in range(n):
            cov = sum(((i + (a + 0.5) / ss - 5) ** 2 + (j + (b + 0.5) / ss - 5) ** 2) < 3.4 ** 2
                      for a in range(ss) for b in range(ss)) / ss ** 2
            v = round(232 - 210 * cov)
            svg.rect(x0 + i * cs, y0 + j * cs, cs, cs, gray(v))
            svg.text(x0 + i * cs + cs / 2, y0 + j * cs + cs / 2 + 6, str(v), "codel", 16,
                     P.black if v > 128 else P.white, "middle")
    svg.rect(x0, y0, n * cs, n * cs, "none", stroke=P.black, stroke_width=2)
    arrow(svg, (x0, y0 - 26), (x0 + 120, y0 - 26), P.blue, 3, 16)
    label(svg, x0 + 134, y0 - 20, "u", P.blue, "start", 20)
    arrow(svg, (x0 - 26, y0), (x0 - 26, y0 + 120), P.blue, 3, 16)
    label(svg, x0 - 26, y0 + 150, "v", P.blue, size=20)

    svg.frame("pixel.", "an image is a grid of numbers")
    code_rule(svg)
    svg.code(M, CODE_Y, """
img[v, u]     # row v, column u · 0 is black, 255 is white""", "py", 22)
    return svg


def bayer() -> Svg:
    """The Bayer mosaic: each pixel sees one colour, half of them green."""
    svg = Svg(P.black)
    n, cs = 8, 72
    x0, y0 = CX - n * cs / 2, 330
    tile = [["R", "G"], ["G", "B"]]
    cols = {"R": P.lavender, "G": P.teal_60, "B": P.blue_80}
    for j in range(n):
        for i in range(n):
            ch = tile[j % 2][i % 2]
            svg.rect(x0 + i * cs + 3, y0 + j * cs + 3, cs - 6, cs - 6, cols[ch], rx=6)
            svg.text(x0 + i * cs + cs / 2, y0 + j * cs + cs / 2 + 8, ch, "code", 22,
                     P.black if ch != "B" else P.white, "middle")
    svg.rect(x0 + 2 * cs - 3, y0 + 2 * cs - 3, 2 * cs + 6, 2 * cs + 6, "none", stroke=P.white, stroke_width=4, rx=8)
    for k, (ch, pct) in enumerate((("G", "50 %"), ("R", "25 %"), ("B", "25 %"))):
        x = x0 + k * 210
        svg.rect(x, 948, 28, 28, cols[ch], rx=5)
        label(svg, x + 42, 970, f"{ch}  {pct}", P.white, "start", 20)

    svg.frame("bayer.", "colour filter array · RGGB", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
rgb = demosaic(raw)    # one colour per pixel, borrow the other two""", "py", 22, dark=True)
    return svg


def edge() -> Svg:
    """Convolution: slide [-1, 0, 1] along a row of pixels; the output spikes where brightness jumps."""
    svg = Svg(P.cream)
    row = [20] * 7 + [60, 180] + [220] * 7
    n, cs = len(row), 54
    x0 = CX - n * cs / 2
    y1, yk, base = 400, 560, 920

    label(svg, x0, y1 - 22, "pixels", P.black, "start", 18)
    for i, v in enumerate(row):
        svg.rect(x0 + i * cs + 2, y1, cs - 4, cs - 4, gray(v), rx=4, stroke=P.black_20, stroke_width=1.5)
        label(svg, x0 + i * cs + cs / 2, y1 + cs + 26, str(v), size=15)
    at = 7  # kernel centred on pixel 7
    svg.rect(x0 + (at - 1) * cs - 2, y1 - 4, 3 * cs + 4, cs + 4, "none", stroke=P.blue, stroke_width=4, rx=6)
    label(svg, x0, yk - 22, "kernel", P.black, "start", 18)
    for k, w in enumerate((-1, 0, 1)):
        x = x0 + (at - 1 + k) * cs
        svg.rect(x + 2, yk, cs - 4, cs - 4, P.blue if w else P.blue_20, rx=4)
        label(svg, x + cs / 2, yk + cs / 2 + 4, f"{w:+d}" if w else "0", P.white if w else P.blue, size=18)

    out = [row[i + 1] - row[i - 1] if 0 < i < n - 1 else 0 for i in range(n)]
    label(svg, x0, 680, "output", P.black, "start", 18)
    svg.line(x0, base, x0 + n * cs, base, P.black_20, 2)
    for i, g in enumerate(out):
        hgt = g * 1.25
        if hgt:
            svg.rect(x0 + i * cs + 8, base - hgt, cs - 16, hgt, P.teal, rx=4)
        label(svg, x0 + i * cs + cs / 2, base + 30, str(g), P.teal if g else P.black_60, size=15)

    svg.frame("edge.", "convolution · slide a kernel, find the jumps")
    code_rule(svg)
    svg.code(M, CODE_Y, """
g[x] = img[x + 1] - img[x - 1]    # kernel [-1, 0, +1]""", "py", 22)
    return svg


FAMILIES = {
    "camera": ["pinhole", "lens", "zoom", "intrinsic", "distort", "fisheye"],
    "shutter": ["rolling", "global", "expose", "blur"],
    "geometry": ["ray", "size", "pose", "disparity", "vanish", "homography", "epipolar"],
    "image": ["pixel", "bayer", "edge"],
}


def main(names: set[str]) -> None:
    for family, fns in FAMILIES.items():
        for name in fns:
            fn = globals().get(name) or globals().get(name + "_")  # global is a keyword
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
