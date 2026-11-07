"""Mosaic: five pictures, coloured one triangle at a time.

The brand cover's method. A triangular lattice is laid over the paper and a scene (a stack of
shapes, first match wins) says what colour each triangle's centroid gets. Nothing is drawn but
triangles: the shapes only decide colours.

build. sweep. gear. heart. launch.

Run:  uv run --no-project --with fonttools --with brotli python src/mosaic.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from posters import ART, CODE_Y, M, W, code_rule  # noqa: E402

SERIES = "mosaic"
CX = W / 2
GAP = "gap"  # a fill that leaves the triangle empty and stops the shapes below it


# --- shapes: predicates (x, y) -> bool in page coordinates (y down, angles in degrees, 0 = right, 90 = down)
def circle(cx, cy, r):
    return lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def ring(cx, cy, r0, r1, a0=None, a1=None):
    def f(x, y):
        if not r0 <= math.hypot(x - cx, y - cy) <= r1:
            return False
        return a0 is None or (math.degrees(math.atan2(y - cy, x - cx)) - a0) % 360 <= (a1 - a0) % 360
    return f


def ellipse(cx, cy, rx, ry, deg=0.0):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))

    def f(x, y):
        dx, dy = x - cx, y - cy
        u, v = dx * c + dy * s, -dx * s + dy * c
        return (u / rx) ** 2 + (v / ry) ** 2 <= 1
    return f


def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x <= x1 and y0 <= y <= y1


def rrect(x0, y0, x1, y1, r):
    def f(x, y):
        qx = max(x0 + r - x, 0, x - (x1 - r))
        qy = max(y0 + r - y, 0, y - (y1 - r))
        return x0 <= x <= x1 and y0 <= y <= y1 and qx * qx + qy * qy <= r * r
    return f


def capsule(x0, y0, x1, y1, r):
    """Everything within r of the segment (x0, y0)-(x1, y1)."""
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy or 1e-9

    def f(x, y):
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        return (x - x0 - t * dx) ** 2 + (y - y0 - t * dy) ** 2 <= r * r
    return f


def path(points, r):
    segs = [capsule(*a, *b, r) for a, b in zip(points, points[1:])]
    return lambda x, y: any(s(x, y) for s in segs)


def polygon(points):
    def f(x, y):
        inside = False
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
        return inside
    return f


def heart_shape(cx, cy, s):
    """(x² + y² − 1)³ − x²y³ ≤ 0, scaled by s and centred on (cx, cy)."""
    def f(x, y):
        u, v = (x - cx) / s, (cy - y) / s + 0.1
        return (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0
    return f


def turned(shape, cx, cy, a):
    """shape drawn about (cx, cy) pointing up, turned by a radians (clockwise on the page)."""
    c, s = math.cos(a), math.sin(a)

    def f(x, y):
        dx, dy = x - cx, y - cy
        return shape(cx + dx * c + dy * s, cy - dx * s + dy * c)
    return f


def minus(a, b):
    return lambda x, y: a(x, y) and not b(x, y)


def anywhere(x, y):
    return True


# --- fills ---------------------------------------------------------------------
def mottle(main, alt, p=0.22):
    return lambda x, y, rng: alt if rng.random() < p else main


def pick(*cols):
    return lambda x, y, rng: rng.choice(cols)


class Scene:
    """Shapes stacked front to back; a triangle takes the fill of the first shape it falls in."""

    def __init__(self, seed=3):
        self.layers = []
        self.rng = random.Random(seed)

    def add(self, shape, fill):
        self.layers.append((shape, fill))
        return self

    def __call__(self, x, y):
        for shape, fill in self.layers:
            if shape(x, y):
                c = fill(x, y, self.rng) if callable(fill) else fill
                if c is not None:
                    return c
        return None


# --- background scatter --------------------------------------------------------
def halo(cx=CX, cy=640, base=0.42, fall=1100, squash=1.25):
    tints = [P.blue_20, P.lavender_20, P.lavender_60, P.blue_20]

    def f(x, y, rng):
        if rng.random() < max(0.0, base - math.hypot(x - cx, (y - cy) * squash) / fall):
            return rng.choice(tints)
    return f


def stars(p=0.035):
    tints = [P.black_80, P.black_80, P.black_80, P.blue_80, P.lavender_60, P.white]

    def f(x, y, rng):
        if rng.random() < p:
            return rng.choice(tints)
    return f


# --- the lattice ---------------------------------------------------------------
def lattice(svg: Svg, scene: Scene, s=30, bg=P.white, scatter=None) -> int:
    """Fill the drawing area with triangles of side s; return how many the scene coloured."""
    h = s * math.sqrt(3) / 2
    y_top = ART[1] - 10
    n = 0
    for r in range(int((ART[3] + 40 - y_top) / h)):
        for c in range(-2, int(W / (s / 2)) + 2):
            x, y = c * s / 2, y_top + r * h
            if (r + c) % 2 == 0:
                tri = [(x, y + h), (x + s / 2, y), (x + s, y + h)]
            else:
                tri = [(x, y), (x + s, y), (x + s / 2, y + h)]
            gx, gy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
            if not (M - 20 < gx < W - M + 20):
                continue
            col = scene(gx, gy)
            if col is None and scatter:
                col = scatter(gx, gy, scene.rng)
            elif col not in (None, GAP, bg):
                n += 1
            if col and col != GAP:
                svg.poly(tri, col, stroke=bg, stroke_width=1.2, stroke_linejoin="round")
    return n


def poster(title, kicker, scene, code, lang="py", s=30, dark=False, scatter="auto") -> Svg:
    bg = P.black if dark else P.white
    if scatter == "auto":
        scatter = stars() if dark else halo()
    svg = Svg(bg)
    n = lattice(svg, scene, s, bg, scatter)
    svg.frame(title, kicker.format(n=n), dark=dark)
    code_rule(svg, P.lavender if dark else P.blue)
    svg.code(M, CODE_Y, code, lang, 22, dark=dark)
    return svg


BODY = mottle(P.blue, P.blue_80)




# ----------------------------------------------------------------------------
def build() -> Svg:
    """A robot face built from the lattice, like the brand book cover."""
    cx, cy = CX, 660
    sc = Scene(3)
    for sx in (-1, 1):
        ex, ey = cx + sx * 112, cy - 40
        sc.add(circle(ex + 12, ey + 6, 24), P.black).add(circle(ex, ey, 58), P.white)
    sc.add(lambda x, y: abs(math.hypot(x - cx, y - cy - 10) - 118) < 15 and y > cy + 70, P.teal)
    sc.add(rrect(cx - 240, cy - 190, cx + 240, cy + 185, 64), lambda x, y, rng: P.blue if rng.random() < 0.78 else P.blue_80)
    sc.add(rect(cx - 10, cy - 300, cx + 10, cy - 185), P.black).add(circle(cx, cy - 318, 34), P.teal)
    sc.add(lambda x, y: 240 < abs(x - cx) < 290 and abs(y - cy + 10) < 60, P.black)
    sc.add(rect(cx - 90, cy + 185, cx + 90, cy + 250), P.black_80)
    return poster("build.", "triangles all the way down", sc, """
class Robot:
    def __init__(self):
        self.mood = "curious"
        self.parts = [Sensor(), Brain(), Motor()]""", s=34, scatter=halo(cy=cy))


def sweep() -> Svg:
    """A robot vacuum partway out along the spiral it cleans: the path behind it, nothing ahead."""
    cx, cy, pitch = CX, 630, 66
    th0, th_end = 2 * math.pi * 0.7, 2 * math.pi * 4.5
    tones = [P.lavender_20, P.lavender_60, P.blue_40, P.blue_60, P.blue_80]

    def r_of(th):
        return pitch * th / (2 * math.pi)

    rx, ry = cx + r_of(th_end) * math.cos(th_end), cy + r_of(th_end) * math.sin(th_end)
    hx, hy = math.cos(th_end) * pitch / (2 * math.pi) - r_of(th_end) * math.sin(th_end), \
        math.sin(th_end) * pitch / (2 * math.pi) + r_of(th_end) * math.cos(th_end)
    head = math.atan2(hx, -hy)  # direction of travel, as a turn from "up"

    def swept(x, y, rng):
        d, a = math.hypot(x - cx, y - cy), math.atan2(y - cy, x - cx) % (2 * math.pi)
        k = round((2 * math.pi * d / pitch - a) / (2 * math.pi))
        th = a + 2 * math.pi * k
        if th0 <= th <= th_end and abs(r_of(th) - d) < 0.34 * pitch:
            return tones[min(int((th - th0) / (th_end - th0) * len(tones)), len(tones) - 1)]

    sc = Scene(23)
    sc.add(turned(circle(rx, ry - 20, 14), rx, ry, head), P.teal)
    sc.add(turned(ring(rx, ry, 40, 56, 205, 335), rx, ry, head), P.black)
    sc.add(circle(rx, ry, 56), BODY)
    sc.add(anywhere, swept)
    return poster("sweep.", "every square metre, once", sc,
                  "r = pitch * theta / (2 * pi)  # one turn, one robot wider", s=24, scatter=None)


def gear() -> Svg:
    """Two meshing spur gears, 12 teeth turning 8: the profiles are a clamped cosine."""
    m = 16  # pitch radius per tooth
    (n1, n2), beta = (12, 8), math.radians(-45)
    c1 = (470, 700)
    c2 = (c1[0] + (n1 + n2) * m * math.cos(beta), c1[1] + (n1 + n2) * m * math.sin(beta))
    ph1 = -n1 * beta
    ph2 = math.pi - n2 * (beta + math.pi)

    def toothed(c, n, ph):
        R = n * m

        def f(x, y):
            a = math.atan2(y - c[1], x - c[0])
            r = R + 17 * max(-1.0, min(1.0, 1.6 * math.cos(n * a + ph)))
            return math.hypot(x - c[0], y - c[1]) <= r
        return f

    sc = Scene(59)
    sc.add(circle(*c1, 44), GAP).add(circle(*c2, 30), GAP)
    sc.add(toothed(c1, n1, ph1), BODY)
    sc.add(toothed(c2, n2, ph2), mottle(P.teal, P.teal_60, 0.15))
    return poster("gear.", "12 teeth turn 8", sc, "ratio = 12 / 8  # the small one turns 1.5 times",
                  s=22, scatter=None)


def heart() -> Svg:
    """The heart curve, a heartbeat running through it."""
    beat = path([(84, 650), (360, 650), (400, 612), (440, 650), (490, 650), (525, 470),
                 (570, 830), (610, 650), (665, 650), (705, 615), (745, 650), (996, 650)], 11)
    inside = heart_shape(540, 650, 230)
    sc = Scene(43)
    sc.add(beat, P.teal)
    sc.add(inside, BODY)
    return poster("heart.", "(x² + y² − 1)³ − x²y³ ≤ 0", sc,
                  "inside = (x*x + y*y - 1)**3 - x*x * y**3 <= 0", s=22, scatter=None)


def launch() -> Svg:
    """A rocket climbing off the Earth's curve, the Moon ahead of it."""
    ec, R = (CX, 1620), 720             # the Earth: its top at y = 900, the curve shows across the page
    cx = CX
    limb = ec[1] - R

    def plume(x, y, rng):  # exhaust from the nozzle down to the ground: wider and thinner as it falls
        if not 830 < y < limb:
            return None
        t = (y - 830) / (limb - 830)
        if abs(x - cx) > 14 + 60 * t or rng.random() < 0.15 + 0.7 * t:
            return None
        return P.lavender if t < 0.3 else rng.choice([P.lavender_60, P.blue_80])

    sc = Scene(37)
    sc.add(circle(cx, 520, 24), P.teal).add(circle(cx, 520, 42), P.blue)
    sc.add(polygon([(cx - 66, 452), (cx + 66, 452), (cx, 300)]), P.blue)
    sc.add(rect(cx - 66, 660, cx + 66, 684), P.blue)
    sc.add(rrect(cx - 66, 440, cx + 66, 740, 14), mottle(P.cream, P.white, 0.12))
    sc.add(polygon([(cx - 66, 620), (cx - 130, 772), (cx - 66, 740)]), P.blue)
    sc.add(polygon([(cx + 66, 620), (cx + 130, 772), (cx + 66, 740)]), P.blue)
    sc.add(rect(cx - 34, 740, cx + 34, 764), P.black_60)
    sc.add(polygon([(cx - 18, 764), (cx + 18, 764), (cx, 812)]), P.cream)
    sc.add(polygon([(cx - 34, 764), (cx + 34, 764), (cx, 852)]), P.lavender)
    sc.add(minus(circle(850, 370, 72), circle(882, 350, 62)), P.cream)
    sc.add(anywhere, plume)
    sc.add(ring(*ec, R, R + 16), P.lavender_60)
    earth = circle(*ec, R)
    for land in (ellipse(330, 990, 120, 50, -12), ellipse(760, 1000, 90, 40, 15)):
        sc.add(lambda x, y, land=land: land(x, y) and earth(x, y), mottle(P.teal, P.teal_60, 0.25))
    sc.add(earth, mottle(P.blue, P.blue_80, 0.22))
    return poster("launch.", "{n} triangles to orbit", sc, """
while altitude < orbit:
    throttle(1.0)""", s=26, dark=True, scatter=stars(0.02))


POSTERS = [build, sweep, gear, heart, launch]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, SERIES)
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
