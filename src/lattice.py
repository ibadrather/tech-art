"""Lattice: twenty robots and pictures, coloured one triangle at a time.

build.'s method as a series. A triangular lattice is laid over the paper and a scene (a stack of
shapes, first match wins) says what colour each triangle's centroid gets. Nothing is drawn but
triangles: the shapes only decide colours.

hi. scan. rover. quad. weld. pup. dive. sweep. hexa. crawl.
launch. lander. heart. owl. chip. gear. glitch. pals. bloom. astro.

Run:  uv run --no-project --with fonttools --with brotli python src/lattice.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from posters import ART, CODE_Y, M, W, code_rule  # noqa: E402

SERIES = "lattice"
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
def hi() -> Svg:
    """A humanoid waving: one arm down, one arm up, motion arcs by the hand."""
    sc = Scene(3)
    sc.add(circle(540, 292, 18), P.teal).add(capsule(540, 300, 540, 342, 6), P.black)
    for ex in (488, 592):
        sc.add(circle(ex + 8, 420, 13), P.black).add(circle(ex, 414, 32), P.white)
    sc.add(rect(495, 452, 585, 482), P.teal)
    sc.add(rrect(420, 340, 660, 500, 40), BODY)
    sc.add(rect(510, 500, 570, 532), P.black_80)
    sc.add(circle(835, 315, 32), P.black_80).add(circle(355, 745, 30), P.black_80)
    sc.add(circle(395, 555, 28), P.black).add(circle(685, 555, 28), P.black).add(circle(790, 455, 22), P.teal)
    sc.add(capsule(685, 555, 790, 455, 24), P.blue_80).add(capsule(790, 455, 830, 335, 22), P.blue_80)
    sc.add(capsule(395, 555, 360, 730, 24), P.blue_80)
    sc.add(circle(540, 625, 40), P.teal).add(rect(470, 685, 610, 725), P.lavender_60)
    sc.add(rrect(410, 530, 670, 770, 34), BODY)
    sc.add(rrect(425, 925, 530, 965, 14), P.black).add(rrect(550, 925, 655, 965, 14), P.black)
    sc.add(rect(450, 770, 520, 930), P.blue_80).add(rect(560, 770, 630, 930), P.blue_80)
    sc.add(ring(835, 315, 72, 94, -95, 15), P.lavender).add(ring(835, 315, 118, 138, -95, 15), P.lavender_60)
    return poster("hi.", "{n} triangles, one wave", sc, """
robot.arm("right").wave(times=3)
print("hi.")""")


def scan() -> Svg:
    """A one-eyed robot sweeps a lidar fan; only the wall inside the fan lights up."""
    ex, ey, half = 395, 600, 22

    def ang(x, y):
        return math.degrees(math.atan2(y - ey, x - ex))

    def wall(y):
        return 850 + 50 * math.sin((y - 600) / 70)

    sc = Scene(5)
    sc.add(circle(ex, ey, 26), P.teal).add(rrect(200, 560, 430, 640, 38), P.black)
    sc.add(circle(260, 405, 18), P.teal).add(capsule(260, 420, 260, 480, 6), P.black)
    sc.add(rrect(170, 480, 450, 780, 60), BODY)
    for wx in (225, 310, 395):
        sc.add(circle(wx, 825, 24), P.black_60)
    sc.add(rrect(180, 790, 440, 860, 34), P.black_80)
    sc.add(lambda x, y: abs(ang(x, y)) <= half and abs(x - wall(y)) <= 17, P.teal)
    sc.add(lambda x, y: abs(ang(x, y)) <= half and 455 < x < wall(y) - 17,
           lambda x, y, rng: P.lavender_20 if int((ang(x, y) + half) // 5) % 2 else P.blue_20)
    sc.add(lambda x, y: abs(x - wall(y)) <= 17 and 320 < y < 960, P.black_20)
    return poster("scan.", "only what the beam touches", sc,
                  "hits = [raycast(pose, a) for a in fov]", scatter=None)


def rover() -> Svg:
    """A six-wheeled rocker-bogie rover with a mast camera, on sand."""
    sc = Scene(7)
    sc.add(rrect(380, 395, 500, 445, 14), P.teal).add(capsule(430, 445, 430, 575, 9), P.black)
    sc.add(capsule(680, 560, 680, 575, 6), P.black).add(ellipse(680, 535, 52, 20), P.blue_40)
    sc.add(rrect(290, 575, 790, 608, 8), P.black_80)
    sc.add(rrect(330, 610, 750, 730, 24), BODY)
    for wx in (360, 540, 720):
        sc.add(circle(wx, 860, 16), P.blue_20)
    for wx in (360, 540, 720):
        sc.add(circle(wx, 860, 50), P.black)
    sc.add(circle(450, 735, 14), P.teal).add(circle(620, 795, 14), P.teal)
    sc.add(capsule(450, 735, 360, 860, 10), P.black_80).add(capsule(450, 735, 620, 795, 10), P.black_80)
    sc.add(capsule(620, 795, 540, 860, 10), P.black_80).add(capsule(620, 795, 720, 860, 10), P.black_80)
    sc.add(ellipse(870, 930, 44, 26), P.black_60).add(ellipse(190, 940, 30, 20), P.black_60)
    sc.add(lambda x, y: 912 < y < 995, lambda x, y, rng: rng.choice([P.teal_20, P.teal_20, P.lavender_20, None]))
    return poster("rover.", "six wheels, one rocker-bogie", sc,
                  "rover.drive(v=0.04, w=0.0)  # 4 cm/s, slow and sure", scatter=halo(cy=700, base=0.3))


def quad() -> Svg:
    """A quadcopter from above: four rotor discs, each blade at its own angle."""
    cx, cy, d = 540, 630, 175
    sc = Scene(11)
    motors = [(cx - d, cy - d, 20), (cx + d, cy - d, 75), (cx - d, cy + d, -40), (cx + d, cy + d, 130)]
    for mx, my, a in motors:
        sc.add(circle(mx, my, 24), P.teal if my < cy else P.black)
    for mx, my, a in motors:
        c, s = 88 * math.cos(math.radians(a)), 88 * math.sin(math.radians(a))
        sc.add(capsule(mx - c, my - s, mx + c, my + s, 11), P.blue_60)
    sc.add(rrect(510, 515, 570, 560, 10), P.teal)
    sc.add(rrect(470, 560, 610, 700, 30), BODY)
    for mx, my, _ in motors:
        sc.add(capsule(cx, cy, mx, my, 14), P.black_80)
    for mx, my, _ in motors:
        sc.add(circle(mx, my, 100), P.lavender_20)
    return poster("quad.", "four rotors, one mixer", sc, "m = mix @ [thrust, roll, pitch, yaw]")


def weld() -> Svg:
    """An industrial arm at work: a spark of triangles where the torch meets the seam."""
    sc = Scene(13)
    sx, sy = 775, 805
    sc.add(circle(720, 660, 26), P.black).add(capsule(720, 660, 770, 780, 13), P.black_80)

    def spark(x, y, rng):
        d = math.hypot(x - sx, y - sy)
        if d < 34:
            return P.lavender
        if rng.random() < (1 - d / 120) * 0.75:
            return rng.choice([P.teal, P.lavender_60, P.lavender, P.teal_60])
    sc.add(circle(sx, sy, 120), spark)
    sc.add(circle(470, 560, 34), P.teal).add(capsule(470, 560, 720, 660, 28), mottle(P.blue_80, P.blue))
    sc.add(circle(370, 820, 38), P.teal).add(capsule(370, 820, 470, 560, 32), BODY)
    sc.add(rrect(310, 830, 430, 905, 20), P.black_80).add(rrect(270, 905, 470, 960, 12), P.black)
    sc.add(rect(600, 845, 960, 905), lambda x, y, rng: P.teal_60 if x < sx and y < 872 else P.black_60)
    return poster("weld.", "a seam, one point at a time", sc, """
for p in seam:
    arm.move_l(p, speed=0.01)""")


def pup() -> Svg:
    """A quadruped robot dog, side on: near legs in ink, far legs in grey."""
    sc = Scene(17)
    sc.add(circle(790, 495, 16), P.teal)
    sc.add(polygon([(720, 455), (745, 385), (772, 455)]), P.black_80)
    sc.add(rrect(810, 505, 880, 555, 14), P.blue_80).add(rrect(700, 450, 840, 560, 30), P.blue_80)
    sc.add(capsule(690, 590, 740, 530, 28), P.blue_80)
    sc.add(rrect(470, 520, 560, 560, 10), P.teal)

    def leg(hx, hy, near):
        kx, ky, fx, fy = hx - 45, hy + 120, hx + 5, hy + 240
        ink = (P.black, P.black_80, P.teal) if near else (P.black_20, P.black_20, P.black_20)
        sc.add(circle(kx, ky, 20), ink[2]).add(circle(fx, fy, 17), ink[0])
        sc.add(capsule(hx, hy, kx, ky, 16), ink[1]).add(capsule(kx, ky, fx, fy, 12), ink[0])

    leg(410, 670, True)
    leg(670, 670, True)
    sc.add(circle(410, 660, 26), P.black).add(circle(670, 660, 26), P.black)
    sc.add(rrect(350, 560, 720, 690, 44), BODY)
    sc.add(capsule(355, 590, 300, 515, 8), P.black_80)
    leg(450, 670, False)
    leg(710, 670, False)
    return poster("pup.", "four legs, twelve motors", sc, 'gait = "trot"  # FL+RR, then FR+RL')


def dive() -> Svg:
    """An underwater robot with its own light, bubbles rising off the stern."""
    sc = Scene(19)
    sc.add(circle(720, 640, 26), P.black).add(ring(720, 640, 26, 54), P.teal)
    sc.add(rrect(470, 500, 590, 560, 20), P.blue_80)
    sc.add(circle(250, 650, 20), P.black).add(capsule(232, 575, 232, 725, 10), P.black_80)
    sc.add(lambda x, y: ellipse(520, 650, 270, 110)(x, y) and 690 < y < 722, P.teal_60)
    sc.add(ellipse(520, 650, 270, 110), BODY)
    sc.add(polygon([(780, 640), (1000, 535), (1000, 765)]), mottle(P.lavender_20, P.blue_20, 0.35))
    sc.add(circle(310, 505, 20), P.lavender_60).add(circle(275, 430, 26), P.lavender_20).add(circle(320, 345, 32), P.lavender_20)
    sc.add(capsule(860, 950, 880, 845, 10), P.teal_60).add(capsule(905, 950, 895, 870, 10), P.teal)
    sc.add(capsule(170, 950, 190, 880, 10), P.teal_60)
    sc.add(lambda x, y: 930 < y < 995, mottle(P.black_20, P.teal_20, 0.4))
    return poster("dive.", "40 m down, its own light", sc,
                  "sub.hold_depth(z=-40.0)  # metres, PID on the thrusters", scatter=halo(base=0.2))


def sweep() -> Svg:
    """A robot vacuum from above, inside the Archimedean spiral it cleans along."""
    cx, cy, r0, pitch, turns = 540, 640, 230, 56, 3.6
    sc = Scene(23)
    sc.add(ring(cx, cy, 150, 182, 200, 340), P.black)
    sc.add(circle(cx, 560, 32), P.black_80).add(circle(cx, 665, 34), P.teal)
    sc.add(circle(cx, cy, 182), BODY)

    def spiral(x, y, rng):
        d = math.hypot(x - cx, y - cy)
        a = math.atan2(y - cy, x - cx) / (2 * math.pi) % 1
        t = (d - r0) / pitch - a
        k = round(t)
        if 0 <= k + a <= turns and abs(t - k) * pitch < 11 and y < 1000:
            return [P.blue_40, P.lavender_60, P.lavender_20, P.lavender_20][min(int(k), 3)]
    sc.add(anywhere, spiral)
    return poster("sweep.", "every square metre, once", sc, "r = r0 + pitch * theta / (2 * pi)", scatter=None)


def hexa() -> Svg:
    """A hexapod from above in a tripod gait: three feet down (ink), three swinging (light)."""
    cx, cy = 540, 650
    sc = Scene(29)
    sc.add(circle(515, 432, 16), P.teal).add(circle(565, 432, 16), P.teal)
    sc.add(circle(cx, 450, 62), P.blue_80)
    sc.add(rrect(490, 580, 590, 720, 20), P.black_80)
    sc.add(ellipse(cx, cy, 120, 190), BODY)
    rows = [(540, (230, -70), (320, -160)), (650, (245, -20), (365, 40)), (760, (230, 40), (320, 160))]
    down = {(-1, 0), (1, 1), (-1, 2)}  # L1, R2, L3
    for i, (hy, knee, foot) in enumerate(rows):
        for side in (-1, 1):
            hx = cx + side * 105
            kx, ky = cx + side * knee[0], hy + knee[1]
            fx, fy = cx + side * foot[0], hy + foot[1]
            a, b = (P.black_80, P.black) if (side, i) in down else (P.blue_40, P.blue_40)
            sc.add(circle(kx, ky, 20), P.teal).add(circle(fx, fy, 16), b)
            sc.add(capsule(hx, hy, kx, ky, 14), a).add(capsule(kx, ky, fx, fy, 10), b)
    return poster("hexa.", "three feet down, three in the air", sc,
                  'tripod = [("L1", "R2", "L3"), ("R1", "L2", "R3")]')


def crawl() -> Svg:
    """A tracked robot with a camera mast and a gripper arm."""
    sc = Scene(31)
    sc.add(rrect(320, 450, 420, 505, 14), P.teal).add(capsule(370, 505, 370, 640, 8), P.black)
    sc.add(capsule(880, 520, 935, 485, 8), P.black).add(capsule(880, 520, 935, 565, 8), P.black)
    sc.add(circle(760, 470, 20), P.teal).add(circle(660, 620, 24), P.black)
    sc.add(capsule(760, 470, 880, 520, 12), P.black_80).add(capsule(660, 620, 760, 470, 14), P.black_80)
    sc.add(rrect(300, 640, 780, 790, 20), BODY)
    for wx, r in ((310, 44), (770, 44)):
        sc.add(circle(wx, 850, 14), P.blue_20).add(circle(wx, 850, r), P.black_80)
    for wx in (440, 540, 640):
        sc.add(circle(wx, 862, 24), P.black_60)
    sc.add(rrect(250, 790, 830, 910, 60), P.black)
    sc.add(lambda x, y: 925 < y < 960, lambda x, y, rng: P.black_20 if rng.random() < 0.5 else None)
    return poster("crawl.", "skid steer: two tracks, one turn", sc, "v_l, v_r = v - w * B / 2, v + w * B / 2")


def launch() -> Svg:
    """A rocket lifting off a pad of smoke."""
    sc = Scene(37)
    sc.add(circle(540, 545, 24), P.teal).add(circle(540, 545, 44), P.blue)
    sc.add(polygon([(470, 452), (610, 452), (540, 300)]), P.blue)
    sc.add(rect(470, 700, 610, 730), P.blue)
    sc.add(rrect(470, 440, 610, 790, 16), mottle(P.cream, P.white, 0.15))
    sc.add(polygon([(470, 670), (395, 825), (470, 790)]), P.blue).add(polygon([(610, 670), (685, 825), (610, 790)]), P.blue)
    sc.add(rect(500, 790, 580, 818), P.black_60)
    sc.add(polygon([(522, 818), (558, 818), (540, 905)]), P.teal)
    sc.add(polygon([(505, 818), (575, 818), (540, 965)]), P.lavender)
    for (x, y, r) in ((380, 975, 62), (290, 995, 44), (700, 975, 62), (790, 995, 44), (540, 1015, 52)):
        sc.add(circle(x, y, r), mottle(P.black_80, P.black_60, 0.3))
    return poster("launch.", "T plus 0", sc, """
while altitude < orbit:
    throttle(1.0)""", dark=True)


def lander() -> Svg:
    """A lunar lander on grey ground, Earth over the horizon."""
    sc = Scene(41)
    sc.add(ellipse(812, 365, 26, 18), P.teal).add(ellipse(852, 405, 20, 12), P.teal).add(circle(830, 380, 62), P.blue)
    sc.add(circle(625, 495, 14), P.cream).add(capsule(585, 560, 622, 500, 4), P.cream)
    sc.add(circle(510, 600, 16), P.black)
    sc.add(rrect(470, 560, 610, 652, 28), mottle(P.cream, P.white, 0.15))
    sc.add(polygon([(515, 740), (565, 740), (585, 785), (495, 785)]), P.black_60)
    sc.add(rect(450, 652, 630, 740), mottle(P.teal, P.teal_60, 0.3))
    sc.add(rrect(345, 855, 415, 882, 8), P.cream).add(rrect(665, 855, 735, 882, 8), P.cream)
    sc.add(capsule(460, 700, 380, 862, 7), P.cream).add(capsule(620, 700, 700, 862, 7), P.cream)
    sc.add(capsule(460, 740, 380, 862, 5), P.black_60).add(capsule(620, 740, 700, 862, 5), P.black_60)
    sc.add(ellipse(230, 940, 85, 26), P.black_60).add(ellipse(820, 925, 62, 20), P.black)
    sc.add(lambda x, y: y >= 885 + 12 * math.sin(x / 60), mottle(P.black_80, P.black_60, 0.3))
    return poster("lander.", "1.62 m/s² and no air", sc,
                  "a = (thrust - m * g_moon) / m  # g_moon = 1.62", dark=True)


def heart() -> Svg:
    """The heart curve, a heartbeat line running through it."""
    sc = Scene(43)
    beat = path([(110, 640), (370, 640), (410, 600), (445, 640), (500, 640), (530, 470),
                 (570, 810), (605, 640), (660, 640), (700, 605), (740, 640), (970, 640)], 13)
    inside = heart_shape(540, 640, 220)
    sc.add(beat, P.teal)
    sc.add(inside, BODY)
    return poster("heart.", "(x² + y² − 1)³ − x²y³ ≤ 0", sc, "inside = (x*x + y*y - 1)**3 - x*x * y**3 <= 0")


def owl() -> Svg:
    """A robot owl on a branch: two lens eyes, ear tufts and a chevron belly."""
    sc = Scene(47)
    for ex in (470, 610):
        sc.add(circle(ex + 4, 546, 20), P.black).add(circle(ex, 540, 40), P.teal).add(ring(ex, 540, 40, 62), P.black_80)
    sc.add(polygon([(518, 598), (562, 598), (540, 655)]), P.lavender)
    sc.add(polygon([(395, 440), (415, 325), (485, 420)]), P.blue_80).add(polygon([(685, 440), (665, 325), (595, 420)]), P.blue_80)
    sc.add(circle(490, 925, 18), P.teal).add(circle(590, 925, 18), P.teal)
    sc.add(capsule(220, 945, 860, 945, 14), P.black_80)
    sc.add(ellipse(540, 775, 110, 135),
           lambda x, y, rng: P.lavender_20 if int((y - 0.6 * abs(x - 540)) // 34) % 2 else P.blue_20)
    sc.add(ellipse(540, 680, 200, 250), BODY)
    sc.add(ellipse(345, 710, 55, 170, 12), P.blue_80).add(ellipse(735, 710, 55, 170, -12), P.blue_80)
    return poster("owl.", "two lenses, awake at night", sc, """
if lux < 5:
    mode = "night_vision"
""")


def chip() -> Svg:
    """A microcontroller: a die, 24 pins, and traces out to vias."""
    x0, y0, x1, y1 = 370, 470, 710, 810
    cxp, cyp = (x0 + x1) / 2, (y0 + y1) / 2
    sc = Scene(53)
    sc.add(circle(410, 510, 14), P.black_60)
    sc.add(rrect(450, 550, 630, 730, 10), BODY)
    sc.add(rrect(x0, y0, x1, y1, 18), P.black)
    rng = random.Random(5)
    for k in range(6):
        o = -130 + k * 52
        # (pin start, outward direction, sideways direction) for each side
        for (px, py), (dx, dy), (sx, sy) in (((cxp + o, y0), (0, -1), (1, 0)), ((cxp + o, y1), (0, 1), (1, 0)),
                                           ((x0, cyp + o), (-1, 0), (0, 1)), ((x1, cyp + o), (1, 0), (0, 1))):
            sc.add(rect(min(px, px + dx * 46) - (11 if dx == 0 else 0), min(py, py + dy * 46) - (11 if dy == 0 else 0),
                        max(px, px + dx * 46) + (11 if dx == 0 else 0), max(py, py + dy * 46) + (11 if dy == 0 else 0)),
                   P.black_60)
            a = (px + dx * 46, py + dy * 46)
            l1 = rng.choice([30, 60, 90])
            b = (a[0] + dx * l1, a[1] + dy * l1)
            bend = math.copysign(1, o) * rng.choice([0, 40, 70])
            c = (b[0] + dx * 60 + sx * bend, b[1] + dy * 60 + sy * bend)
            c = (min(max(c[0], 130), 950), min(max(c[1], 300), 990))
            sc.layers.insert(0, (circle(*c, 17), P.teal))
            sc.add(path([a, b, c], 9), P.lavender_60)
    return poster("chip.", "24 pins, one die", sc, "*GPIOA_ODR |= (1u << 5);  // LED on", "cpp")


def gear() -> Svg:
    """Two meshing spur gears, 12 teeth turning 8: the profiles are a clamped cosine."""
    m = 16  # pitch radius per tooth
    (n1, n2), beta = (12, 8), math.radians(-45)
    c1 = (450, 710)
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

    def spokes(c, r0, r1, k):
        def f(x, y):
            d = math.hypot(x - c[0], y - c[1])
            a = math.atan2(y - c[1], x - c[0])
            frac = (a * k / (2 * math.pi)) % 1
            off = min(frac, 1 - frac) * 2 * math.pi / k * d  # arc distance to the nearest spoke
            return r0 <= d <= r1 and off > 26
        return f

    sc = Scene(59)
    sc.add(circle(*c1, 46), P.white).add(spokes(c1, 92, 148, 4), P.white).add(circle(*c1, 92), P.blue_80)
    sc.add(circle(*c2, 30), P.white)
    sc.add(toothed(c1, n1, ph1), BODY)
    sc.add(toothed(c2, n2, ph2), mottle(P.teal, P.teal_60, 0.15))
    return poster("gear.", "12 teeth turn 8", sc, "ratio = 12 / 8  # the small one turns 1.5 times", s=26)


def glitch() -> Svg:
    """A robot face, some rows of the lattice read late: shifted, with a colour fringe."""
    face = Scene(61)
    face.add(circle(540, 340, 20), P.teal).add(capsule(540, 350, 540, 420, 6), P.black)
    for ex in (450, 630):
        face.add(circle(ex + 14, 572, 22), P.black).add(circle(ex, 560, 52), P.white)
    face.add(rect(440, 700, 640, 732), P.teal)
    face.add(rrect(310, 600, 340, 690, 8), P.black).add(rrect(740, 600, 770, 690, 8), P.black)
    face.add(rrect(330, 420, 750, 800, 60), BODY)
    face.add(rect(470, 800, 610, 870), P.black_80)
    shift = {4: 75, 5: 75, 9: -55, 12: 120, 13: -35, 19: 45}
    dead = {16}

    def glitched(x, y, rng):
        band = int((y - 270) // 26)
        sh = shift.get(band, 0)
        if band in dead and rrect(330, 420, 750, 800, 60)(x, y):
            return P.black if rng.random() < 0.7 else None
        col = face(x + sh, y)
        if col or not sh:
            return col
        if face(x + sh - 30, y):
            return P.lavender
        if face(x + sh + 30, y):
            return P.teal_60
    sc = Scene(61).add(anywhere, glitched)
    sc.rng = face.rng
    return poster("glitch.", "same face, some rows late", sc, "row = np.roll(row, randint(-3, 3))")


def pals() -> Svg:
    """A tall robot holding the hand of a small round one, a heart between them."""
    sc = Scene(67)
    sc.add(heart_shape(565, 440, 52), P.lavender)
    sc.add(circle(380, 362, 16), P.teal).add(capsule(380, 372, 380, 420, 5), P.black)
    sc.add(circle(345, 495, 22), P.teal).add(circle(415, 495, 22), P.teal)
    sc.add(rrect(290, 420, 470, 570, 30), BODY)
    sc.add(rect(355, 570, 405, 592), P.black_80)
    sc.add(circle(605, 795, 24), P.black_80)
    sc.add(capsule(495, 620, 600, 785, 20), P.blue_80).add(capsule(262, 615, 232, 780, 20), P.blue_80)
    sc.add(circle(225, 795, 24), P.black_80)
    sc.add(rrect(270, 590, 490, 820, 30), BODY)
    sc.add(rrect(285, 925, 375, 962, 10), P.black).add(rrect(390, 925, 480, 962, 10), P.black)
    sc.add(rect(300, 820, 360, 930), P.blue_80).add(rect(400, 820, 460, 930), P.blue_80)
    sc.add(circle(725, 642, 14), P.lavender).add(capsule(705, 715, 722, 652, 5), P.black)
    sc.add(circle(722, 788, 18), P.black).add(circle(715, 785, 38), P.white)
    sc.add(capsule(635, 812, 612, 800, 14), P.teal_60)
    sc.add(circle(650, 905, 24), P.black).add(circle(760, 905, 24), P.black)
    sc.add(circle(705, 805, 100), mottle(P.teal, P.teal_60, 0.18))
    return poster("pals.", "one tall, one round, one hand", sc, 'team = [Robot("big"), Robot("small")]')


def bloom() -> Svg:
    """A robot head used as a flower pot, its eyes turned up at what grew."""
    fx, fy = 540, 375
    sc = Scene(71)
    sc.add(circle(fx, fy, 26), P.blue)
    for k in range(6):
        a = math.radians(k * 60 - 90)
        sc.add(circle(fx + 56 * math.cos(a), fy + 56 * math.sin(a), 34), P.lavender if k % 2 else P.lavender_60)
    sc.add(ellipse(490, 545, 50, 20, -30), P.teal_60).add(ellipse(592, 505, 50, 20, 30), P.teal_60)
    sc.add(capsule(540, 420, 540, 640, 11), P.teal)
    sc.add(rect(410, 630, 670, 662), P.black_80)
    for ex in (470, 610):
        sc.add(circle(ex + 6, 702, 15), P.black).add(circle(ex, 722, 34), P.white)
    sc.add(ring(540, 765, 38, 54, 25, 155), P.teal)
    sc.add(rrect(380, 640, 700, 860, 40), BODY)
    sc.add(rrect(430, 860, 650, 935, 16), P.black_80)
    return poster("bloom.", "it waters, it waits", sc, """
while not plant.bloomed:
    plant.water(ml=50)""")


def astro() -> Svg:
    """A robot in a space helmet, a ringed planet behind."""
    sc = Scene(73)
    sc.add(minus(ellipse(850, 360, 95, 24, -15), ellipse(850, 360, 66, 12, -15)), P.teal)
    sc.add(circle(850, 360, 46), P.lavender)
    sc.add(circle(745, 330, 14), P.teal).add(capsule(690, 440, 742, 340, 6), P.cream)
    visor = ellipse(540, 615, 165, 140)
    sc.add(circle(480, 615, 26), P.teal).add(circle(600, 615, 26), P.teal)
    sc.add(lambda x, y: visor(x, y) and abs((x - 540) + (y - 615) + 95) < 24, P.lavender_60)
    sc.add(visor, mottle(P.blue, P.blue_80, 0.25))
    sc.add(circle(540, 600, 215), mottle(P.cream, P.white, 0.12))
    sc.add(rect(480, 862, 520, 900), P.teal).add(rect(540, 862, 580, 900), P.lavender)
    sc.add(rrect(460, 840, 620, 920, 10), P.black_80)
    sc.add(rrect(330, 800, 750, 985, 60), mottle(P.cream, P.white, 0.12))
    return poster("astro.", "hello from 400 km up", sc, """
if suit.o2 < 0.2:
    return_to(airlock)""", dark=True)


POSTERS = [hi, scan, rover, quad, weld, pup, dive, sweep, hexa, crawl,
           launch, lander, heart, owl, chip, gear, glitch, pals, bloom, astro]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, SERIES)
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
