"""Mechanisms: the classic linkages and drives, each drawn with the path it makes.

One mechanism, one pose in bold, the trajectory it traces, one line of maths. Every curve is
computed from the linkage, never drawn by hand.

couple. copy. straight. slide. yoke. index. lift. roll.

Run:  uv run --no-project --with fonttools --with brotli python src/mechanisms.py [name ...]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from posters import CODE_Y, M, W, code_rule, fit  # noqa: E402

SERIES = "mechanisms"
TAU = 2 * math.pi


# --- helpers ------------------------------------------------------------------
def meet(a, ra, b, rb, side=1):
    """Where circle (a, ra) crosses circle (b, rb); `side` picks the left (+1) or right (-1) crossing."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy)
    x = (ra * ra - rb * rb + d * d) / (2 * d)
    h = math.sqrt(max(0.0, ra * ra - x * x))
    ux, uy = dx / d, dy / d
    return (a[0] + x * ux - side * h * uy, a[1] + x * uy + side * h * ux)


def add(a, b, k=1.0):
    return (a[0] + k * b[0], a[1] + k * b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def polar(r, a, c=(0.0, 0.0)):
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def link(svg, a, b, col=P.blue, w=12):
    svg.line(*a, *b, col, w, stroke_linecap="round")


def joint(svg, p, r=10, ink=P.black, fill=P.white):
    svg.circle(*p, r, fill, stroke=ink, stroke_width=4)


def ground(svg, p, size=58, fill=P.black):
    """A fixed pivot: a solid triangle under the joint."""
    svg.triangle(p[0], p[1] + size * 0.45, size, fill, -math.pi / 2)


def dashed_circle(svg, c, r, col=P.black_20, w=2):
    svg.circle(*c, r, "none", stroke=col, stroke_width=w, stroke_dasharray="6 9")


def finish(svg, title, kicker, code, dark=False, rule=P.blue):
    svg.frame(title, kicker, dark=dark, title_fill=P.white if dark else None)
    code_rule(svg, rule)
    svg.code(M, CODE_Y, code, "py", 22, dark=dark)
    return svg


# ----------------------------------------------------------------------------
def couple() -> Svg:
    """Hoeken's four-bar: the coupler, stretched to twice its length, draws a D with a flat side."""
    svg = Svg(P.white)
    A, D = (0.0, 0.0), (2.0, 0.0)
    crank, coupler, rocker = 1.0, 2.5, 2.5

    def pose(t):
        B = polar(crank, t, A)
        C = meet(B, coupler, D, rocker, 1)
        return B, C, add(B, sub(C, B), 2.0)  # the foot sits at twice the coupler length

    ts = [TAU * k / 720 for k in range(721)]
    curve = [pose(t)[2] for t in ts]
    every = [p for t in ts[::6] for p in pose(t)] + [polar(crank, t) for t in ts[::6]]
    f = fit(every + [(0, -0.4), (D[0], -0.4)], pad=30)

    dashed_circle(svg, f(A), crank * (f((1, 0))[0] - f((0, 0))[0]))
    for k in range(12):
        B, C, Pt = pose(TAU * k / 12 + 0.2)
        svg.polyline([f(A), f(B), f(Pt)], P.blue_20, 2)
        svg.line(*f(C), *f(D), P.blue_20, 2)
    svg.polyline([f(p) for p in curve], P.teal, 5)

    B, C, Pt = pose(1.1)
    link(svg, f(A), f(B), P.blue, 14)
    link(svg, f(B), f(Pt), P.blue, 14)
    link(svg, f(C), f(D), P.blue_80, 11)
    for g in (A, D):
        ground(svg, f(g))
    for p in (A, B, C, D):
        joint(svg, f(p))
    svg.circle(*f(Pt), 12, P.teal)
    return finish(svg, "couple.", "four-bar linkage · the crank draws a circle, the coupler draws a D",
                  "C = meet(B, coupler, D, rocker)   # where two circles cross")


def copy() -> Svg:
    """Pantograph: trace a small star, the pen draws it twice the size."""
    svg = Svg(P.cream)
    a, b = 1.7, 1.5
    O = (0.0, 0.0)

    def star(c, R, n=5):
        out = []
        for k in range(2 * n + 1):
            r = R if k % 2 == 0 else R * 0.42
            ang = math.pi / 2 + math.pi * k / n
            out.append(polar(r, ang, c))
        return out

    def pose(T):
        d = math.hypot(*T)
        ua = math.atan2(T[1], T[0]) + math.acos((a * a + d * d - b * b) / (2 * a * d))
        u = polar(1, ua)
        w = sub(T, (a * u[0], a * u[1]))
        w = (w[0] / b, w[1] / b)
        A, E = add(O, u, a), add(O, u, 2 * a)
        return A, E, add(E, w, b), add(E, w, 2 * b)  # A, E, C, pen

    small = star((1.55, 0.55), 0.36)
    big = [(2 * x, 2 * y) for x, y in small]
    poses = [pose(T) for T in small]
    f = fit(big + [O, (0, -0.4)] + [p for q in poses for p in q], pad=30)

    svg.polyline([f(p) for p in small], P.blue_40, 3)
    svg.polyline([f(p) for p in big], P.teal, 5)

    T = small[3]
    A, E, C, Pn = pose(T)
    link(svg, f(O), f(E), P.blue, 14)
    link(svg, f(E), f(Pn), P.blue, 14)
    link(svg, f(A), f(T), P.blue_80, 9)
    link(svg, f(T), f(C), P.blue_80, 9)
    ground(svg, f(O))
    for p in (O, A, E, C):
        joint(svg, f(p))
    svg.circle(*f(T), 10, P.black)
    svg.circle(*f(Pn), 12, P.teal)
    for c, R, label, col in (((1.55, 0.55), 0.36, "trace", P.black_60), ((3.1, 1.1), 0.72, "draw", P.teal)):
        x, y = f((c[0], c[1] - R * 0.42))
        svg.text(x, y + 74, label, "codel", 18, col, "middle")
    return finish(svg, "copy.", "pantograph · trace once, draw it twice the size",
                  "pen = pivot + 2 * (tracer - pivot)")


def straight() -> Svg:
    """Peaucellier–Lipkin: a point on a turning crank, inverted onto an exact straight line."""
    svg = Svg(P.white)
    r, L, s = 1.0, 3.0, 1.3
    O, O2 = (0.0, 0.0), (r, 0.0)

    def pose(phi):
        Q = polar(r, phi, O2)
        A = meet(O, L, Q, s, 1)
        B = meet(O, L, Q, s, -1)
        return Q, A, B, (A[0] + B[0] - Q[0], A[1] + B[1] - Q[1])

    lim = math.radians(58)
    phis = [-lim + 2 * lim * k / 200 for k in range(201)]
    track = [pose(p)[3] for p in phis]
    ghosts = [pose(-lim + 2 * lim * k / 8) for k in range(9)]
    f = fit(track + [O, (-0.3, -0.35)] + [p for g in ghosts for p in g], pad=30)
    px = f((1, 0))[0] - f((0, 0))[0]

    dashed_circle(svg, f(O2), r * px)
    svg.polyline([f(pose(p)[0]) for p in phis], P.black_60, 3)
    for Q, A, B, Pt in ghosts:
        svg.polyline([f(A), f(O), f(B)], P.blue_20, 2)
        svg.poly([f(A), f(Q), f(B), f(Pt)], "none", stroke=P.blue_20, stroke_width=2)
    svg.polyline([f(p) for p in track], P.teal, 5)

    Q, A, B, Pt = pose(math.radians(34))
    link(svg, f(O), f(A), P.blue, 13)
    link(svg, f(O), f(B), P.blue, 13)
    for u, v in ((A, Q), (Q, B), (B, Pt), (Pt, A)):
        link(svg, f(u), f(v), P.blue_80, 9)
    link(svg, f(O2), f(Q), P.black, 11)
    for g in (O, O2):
        ground(svg, f(g))
    for p in (O, O2, A, B, Q):
        joint(svg, f(p))
    svg.circle(*f(Pt), 12, P.teal)
    return finish(svg, "straight.", "Peaucellier–Lipkin · an exact straight line from parts that only turn",
                  "OP * OQ == L**2 - s**2   # a circle through O -> a line")


def slide() -> Svg:
    """Slider-crank: equal turns of the crank, unequal steps of the piston."""
    svg = Svg(P.white)
    r, l = 1.0, 2.7

    def pin(t):
        return polar(r, t)

    def wrist(t):
        return (r * math.cos(t) + math.sqrt(l * l - (r * math.sin(t)) ** 2), 0.0)

    n = 24
    ts = [TAU * k / n for k in range(n)]
    f = fit([(-1.1, -1.1), (l + r + 0.45, 1.1)], pad=10)
    px = f((1, 0))[0] - f((0, 0))[0]
    c = f((0, 0))

    dashed_circle(svg, c, r * px)
    for t in ts:
        svg.line(*f(pin(t)), *f(wrist(t)), P.blue_20, 2)
    y_top, y_bot = c[1] - 0.3 * px, c[1] + 0.3 * px
    x_lo, x_hi = f((l - r - 0.3, 0))[0], f((l + r + 0.45, 0))[0]
    svg.line(x_lo, y_top, x_hi, y_top, P.black_20, 3)
    svg.line(x_lo, y_bot, x_hi, y_bot, P.black_20, 3)
    for t in ts:
        svg.circle(*f(pin(t)), 6, P.teal)
        x = f(wrist(t))[0]
        svg.line(x, y_bot + 24, x, y_bot + 54, P.teal, 3)

    t = math.radians(52)
    w = f(wrist(t))
    svg.rect(w[0] - 0.08 * px, y_top + 5, 0.5 * px, y_bot - y_top - 10, P.black, rx=8)
    link(svg, f(pin(t)), w, P.blue, 12)
    link(svg, c, f(pin(t)), P.blue, 15)
    ground(svg, c)
    joint(svg, c)
    joint(svg, f(pin(t)))
    joint(svg, w, 9)
    svg.text(f((l + r + 0.45, 0))[0], y_bot + 92, "bunched at the ends, spread in the middle", "codel", 17, P.black_60, "end")
    return finish(svg, "slide.", "slider-crank · 24 equal turns, 24 unequal strokes",
                  "x = r*cos(θ) + sqrt(l**2 - (r*sin(θ))**2)")


def yoke() -> Svg:
    """Scotch yoke: a pin on a circle, read from the side, is a pure sine."""
    svg = Svg(P.black)
    R = 150
    cx, cy = M + 40 + R, 640
    th = math.radians(38)
    pin = polar(R, -th, (cx, cy))  # page y is down, so -θ turns counter-clockwise
    y = pin[1]

    dashed_circle(svg, (cx, cy), R, P.black_80, 2)
    # the wave: the pen sits at x0 and the paper runs right, so older samples sit further right
    x0, x1 = cx + R + 150, W - M
    k = (x1 - x0) / (2 * TAU)
    wave = [(x0 + k * u, cy - R * math.sin(th - u)) for u in (2 * TAU * i / 400 for i in range(401))]
    svg.line(x0, cy, x1, cy, P.black_80, 2)
    svg.polyline(wave, P.teal_60, 4)

    # a fixed vertical track; the yoke rod rides up and down inside it
    for sx in (-16, 16):
        svg.line(cx + sx, cy - 2 * R - 20, cx + sx, cy + 2 * R + 20, P.black_80, 3)
    svg.line(cx, y - R - 60, cx, y + R + 60, P.lavender, 10, stroke_linecap="round")
    # the yoke: a horizontal slot riding at the pin's height
    sw, sh = 2 * R + 60, 34
    svg.rect(cx - sw / 2, y - sh / 2, sw, sh, "none", stroke=P.lavender, stroke_width=8, rx=17)
    link(svg, (cx + sw / 2, y), (x0, y), P.lavender, 6)
    link(svg, (cx, cy), pin, P.white, 12)
    joint(svg, (cx, cy), 10, P.white, P.black)
    svg.circle(*pin, 11, P.white)
    svg.circle(x0, y, 10, P.teal_60)
    return finish(svg, "yoke.", "scotch yoke · a circle, read from the side",
                  "y = r * sin(ω * t)   # exactly one harmonic, nothing else", dark=True, rule=P.lavender)


def index() -> Svg:
    """Geneva drive: the pin turns the wheel a quarter, then the disc locks it still."""
    svg = Svg(P.white)
    c = 330.0
    a = b = c / math.sqrt(2)
    G = (M + 60 + b, 525.0)
    D = (G[0] + c, G[1])
    slot_w, rl = 34.0, 160.0

    th = math.pi + 0.24  # drive angle, pin inside a slot
    pin = polar(a, th, D)
    phi = math.atan2(pin[1] - G[1], pin[0] - G[0]) - math.pi / 4

    r_in = c - a - slot_w / 2
    slots = "".join(
        f'<rect x="{_fmt(G[0] + r_in)}" y="{_fmt(G[1] - slot_w / 2)}" width="{_fmt(b + 20 - r_in)}" height="{_fmt(slot_w)}" '
        f'rx="{_fmt(slot_w / 2)}" fill="black" transform="rotate({_fmt(math.degrees(phi + math.pi / 4 + k * math.pi / 2))} '
        f'{_fmt(G[0])} {_fmt(G[1])})"/>'
        for k in range(4)
    )
    cuts = "".join(
        f'<circle cx="{_fmt(q[0])}" cy="{_fmt(q[1])}" r="{_fmt(rl + 6)}" fill="black"/>'
        for q in (polar(c, phi + k * math.pi / 2, G) for k in range(4))
    )
    svg.add(f'<mask id="geneva"><circle cx="{_fmt(G[0])}" cy="{_fmt(G[1])}" r="{_fmt(b)}" fill="white"/>{slots}{cuts}</mask>')
    svg.add(f'<circle cx="{_fmt(G[0])}" cy="{_fmt(G[1])}" r="{_fmt(b)}" fill="{P.blue}" mask="url(#geneva)"/>')

    hole = polar(c, th, D)
    svg.add(
        f'<mask id="lock"><circle cx="{_fmt(D[0])}" cy="{_fmt(D[1])}" r="{_fmt(rl)}" fill="white"/>'
        f'<circle cx="{_fmt(hole[0])}" cy="{_fmt(hole[1])}" r="{_fmt(b + 8)}" fill="black"/></mask>'
    )
    dashed_circle(svg, D, a)
    svg.add(f'<circle cx="{_fmt(D[0])}" cy="{_fmt(D[1])}" r="{_fmt(rl)}" fill="{P.black}" mask="url(#lock)"/>')
    link(svg, D, pin, P.black, 30)
    svg.circle(*pin, 12, P.teal)
    joint(svg, G, 12)
    joint(svg, D, 12)

    # output angle against input turns: a staircase
    def out(t):  # t in drive turns -> wheel quarter turns
        k, f = divmod(t, 1.0)
        al = (f - 0.5) * TAU
        if abs(al) > math.pi / 4:
            return k + (0.0 if al < 0 else 1.0)
        return k + 0.5 + math.atan2(math.sin(al), math.sqrt(2) - math.cos(al)) / (math.pi / 2)

    x0, x1, yb, ht = M + 4, W - M - 4, 950, 150
    turns = 4
    svg.line(x0, yb, x1, yb, P.black_20, 2)
    for k in range(turns + 1):
        x = x0 + (x1 - x0) * k / turns
        svg.line(x, yb, x, yb + 12, P.black_20, 2)
    steps = [(x0 + (x1 - x0) * i / 800, yb - ht * out(turns * i / 800) / turns) for i in range(801)]
    svg.polyline(steps, P.teal, 4)
    svg.text(x1, yb + 38, "drive turns", "codel", 17, P.black_60, "end")
    svg.text(x0, yb - ht - 14, "wheel", "codel", 17, P.black_60)
    return finish(svg, "index.", "geneva drive · turn a quarter, then hold still",
                  "φ = atan2(sin(α), sqrt(2) - cos(α))   # 4 slots: 90°, then rest")


def lift() -> Svg:
    """Cam: the follower's motion s(θ), wrapped around a circle."""
    svg = Svg(P.cream)
    r0, h = 110.0, 105.0
    cx, cy = W / 2, 605.0

    def s(th):  # rise 0-120°, dwell to 180°, return to 300°, dwell
        d = math.degrees(th) % 360

        def cyc(x):
            return x - math.sin(TAU * x) / TAU

        if d < 120:
            return h * cyc(d / 120)
        if d < 180:
            return h
        if d < 300:
            return h * (1 - cyc((d - 180) / 120))
        return 0.0

    psi = math.radians(30)  # cam turned this far, counter-clockwise on the page

    # the follower looks along page-up; with the cam turned by psi it touches cam angle th_c
    th_c = (math.pi / 2 - psi) % TAU
    profile = [polar(r0 + s(t), -(t + psi), (cx, cy)) for t in (TAU * i / 360 for i in range(361))]
    tip = (cx, cy - r0 - s(th_c))

    dashed_circle(svg, (cx, cy), r0, P.black_20)
    svg.poly(profile, P.blue)
    svg.circle(cx, cy, 14, P.cream)
    # the follower: a rod through a guide, resting on the cam
    top = 280
    for gy in (top + 8, top + 52):
        svg.rect(cx - 34, gy, 20, 32, P.black_20, rx=4)
        svg.rect(cx + 14, gy, 20, 32, P.black_20, rx=4)
    svg.line(cx, tip[1] - 4, cx, top, P.black, 14, stroke_linecap="round")
    svg.triangle(cx, tip[1] - 6, 22, P.black, math.pi / 2)
    svg.circle(*tip, 7, P.teal)

    # the same s(θ), unwrapped: base circle at the bottom line, same pixels per mm
    x0, x1, yb = M + 4, W - M - 4, 950
    svg.line(x0, yb, x1, yb, P.black_20, 2)
    curve = [(x0 + (x1 - x0) * i / 360, yb - s(math.radians(i))) for i in range(361)]
    svg.polyline(curve, P.teal, 4)
    xn = x0 + (x1 - x0) * math.degrees(th_c) / 360
    svg.line(xn, yb, xn, yb - s(th_c), P.black_60, 2, stroke_dasharray="4 6")
    svg.circle(xn, yb - s(th_c), 8, P.teal)
    for d, label in ((60, "rise"), (150, "dwell"), (240, "return"), (330, "dwell")):
        svg.text(x0 + (x1 - x0) * d / 360, yb + 36, label, "codel", 17, P.black_60, "middle")
    return finish(svg, "lift.", "cam · the motion, wrapped around a circle",
                  "s = h * (x - sin(2*pi*x) / (2*pi))   # cycloidal rise")


def roll() -> Svg:
    """Planetary gear: a pen on the planet, rolling inside the ring."""
    svg = Svg(P.black)
    R, r, d = 5.0, 3.0, 2.2
    S = 76.0
    cx, cy = W / 2, 630.0

    def pen(t):
        return (cx + S * ((R - r) * math.cos(t) + d * math.cos((R - r) / r * t)),
                cy - S * ((R - r) * math.sin(t) - d * math.sin((R - r) / r * t)))

    n_ring, n_planet = 50, 30
    for k in range(n_ring):
        a = TAU * k / n_ring
        svg.line(*polar(R * S, a, (cx, cy)), *polar(R * S - 14, a, (cx, cy)), P.black_80, 4)
    svg.circle(cx, cy, R * S + 6, "none", stroke=P.black_80, stroke_width=4)

    trace = [pen(TAU * 3 * i / 1500) for i in range(1501)]
    svg.polyline(trace, P.teal_60, 3)

    t = 0.55
    pc = (cx + S * (R - r) * math.cos(t), cy - S * (R - r) * math.sin(t))
    spin = -(R - r) / r * t
    for k in range(n_planet):
        a = -(spin + TAU * k / n_planet)
        svg.line(*polar(r * S - 14, a, pc), *polar(r * S, a, pc), P.lavender, 4)
    svg.circle(*pc, r * S - 14, "none", stroke=P.lavender, stroke_width=3)
    link(svg, (cx, cy), pc, P.black_60, 10)
    link(svg, pc, pen(t), P.white, 8)
    joint(svg, (cx, cy), 10, P.white, P.black)
    joint(svg, pc, 10, P.white, P.black)
    svg.circle(*pen(t), 12, P.teal_60)
    return finish(svg, "roll.", "planetary gear · 50-tooth ring, 30-tooth planet, a pen on the planet",
                  "pen = (R-r) * exp(1j*t) + d * exp(-1j * (R-r)/r * t)", dark=True, rule=P.lavender)


POSTERS = [couple, copy, straight, slide, yoke, index, lift, roll]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, SERIES)
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
