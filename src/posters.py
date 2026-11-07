"""Seven minimal robotics posters, each drawn from the maths or code it shows.

Run:  uv run --no-project --with fonttools --with brotli python src/posters.py
"""

from __future__ import annotations

import heapq
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import CANVAS, P, Svg  # noqa: E402

W, H, M = CANVAS.width, CANVAS.height, CANVAS.margin
ART = (M, 270, W - M, 1000)  # x0, y0, x1, y1 of the drawing area
CODE_Y = 1092


def fit(points, box=ART, pad=20, max_scale=None):
    """Return a function mapping model coords (y up) into the box, preserving aspect."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    bw, bh = box[2] - box[0] - 2 * pad, box[3] - box[1] - 2 * pad
    s = min(bw / max(x1 - x0, 1e-9), bh / max(y1 - y0, 1e-9))
    if max_scale:
        s = min(s, max_scale)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    return lambda p: (cx + (p[0] - mx) * s, cy - (p[1] - my) * s)


def code_rule(svg: Svg, color=P.blue):
    svg.rect(M, CODE_Y - 52, 56, 5, color)


# ----------------------------------------------------------------------------
def reach() -> Svg:
    """Forward kinematics of a 3-link arm: ghost poses and the end-effector trace."""
    svg = Svg(P.white)
    L = [1.0, 0.82, 0.5]

    def q(t):
        return (1.2 + 0.32 * math.sin(t), -0.95 + 0.55 * math.sin(2 * t + 0.6), -0.7 + 0.5 * math.sin(2 * t + 1.9))

    def chain(qs):
        x = y = a = 0.0
        out = [(0.0, 0.0)]
        for qi, li in zip(qs, L):
            a += qi
            x, y = x + li * math.cos(a), y + li * math.sin(a)
            out.append((x, y))
        return out

    ts = [2 * math.pi * k / 720 for k in range(721)]
    trace = [chain(q(t))[-1] for t in ts]
    ghosts = [chain(q(2 * math.pi * k / 28)) for k in range(28)]
    allp = trace + [p for g in ghosts for p in g] + [(0, -0.25)]
    f = fit(allp, pad=40)

    for g in ghosts:
        svg.polyline([f(p) for p in g], P.blue_20, 3)
    svg.polyline([f(p) for p in trace], P.teal, 4)

    pose = chain(q(0.9))
    base = f((0, 0))
    svg.triangle(base[0], base[1] + 30, 120, P.black, -math.pi / 2)
    widths = [26, 20, 14]
    for i in range(3):
        a, b = f(pose[i]), f(pose[i + 1])
        svg.line(*a, *b, P.blue, widths[i], stroke_linecap="round")
    for i, p in enumerate(pose[:-1]):
        svg.circle(*f(p), [17, 13, 10][i], P.white, stroke=P.black, stroke_width=4)
    # gripper
    ee, wrist = f(pose[-1]), f(pose[-2])
    ang = math.atan2(ee[1] - wrist[1], ee[0] - wrist[0])
    for s in (-1, 1):
        a2 = ang + s * 0.55
        svg.line(*ee, ee[0] + 30 * math.cos(a2), ee[1] + 30 * math.sin(a2), P.black, 6, stroke_linecap="round")
    svg.circle(*ee, 7, P.teal)

    svg.frame("reach.", "forward kinematics · 3-DoF arm")
    code_rule(svg)
    svg.code(M, CODE_Y, """
def fk(q, L):
    x = y = a = 0.0
    for qi, li in zip(q, L):
        a += qi
        x, y = x + li*cos(a), y + li*sin(a)
    return x, y""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def _ray_segment(o, d, a, b):
    (ox, oy), (dx, dy), (ax, ay), (bx, by) = o, d, a, b
    ex, ey = bx - ax, by - ay
    den = dx * ey - dy * ex
    if abs(den) < 1e-12:
        return None
    t = ((ax - ox) * ey - (ay - oy) * ex) / den
    u = ((ax - ox) * dy - (ay - oy) * dx) / den
    return t if t > 1e-9 and 0 <= u <= 1 else None


def _ray_circle(o, d, c, r):
    fx, fy = o[0] - c[0], o[1] - c[1]
    b = fx * d[0] + fy * d[1]
    disc = b * b - (fx * fx + fy * fy - r * r)
    if disc < 0:
        return None
    t = -b - math.sqrt(disc)
    return t if t > 1e-9 else None


def see() -> Svg:
    """A 2D lidar scan: only what the robot perceives is drawn, never the room itself."""
    svg = Svg(P.black)
    rng = random.Random(7)
    room = [(-4.2, -3.0), (4.6, -3.0), (4.6, 1.2), (2.2, 1.2), (2.2, 3.6), (-4.2, 3.6)]
    segs = list(zip(room, room[1:] + room[:1]))
    box = [(-2.9, 1.4), (-1.7, 1.4), (-1.7, 2.3), (-2.9, 2.3)]
    segs += list(zip(box, box[1:] + box[:1]))
    circles = [((2.1, -1.6), 0.45), ((-2.4, -1.5), 0.32), ((0.7, 2.1), 0.28)]
    robot = (0.0, 0.0)

    hits = []
    n = 540
    for k in range(n):
        th = 2 * math.pi * k / n
        d = (math.cos(th), math.sin(th))
        ts = [_ray_segment(robot, d, a, b) for a, b in segs] + [_ray_circle(robot, d, c, r) for c, r in circles]
        t = min(x for x in ts if x is not None)
        t *= 1 + rng.gauss(0, 0.006)
        hits.append((robot[0] + t * d[0], robot[1] + t * d[1], t))

    f = fit([(h[0], h[1]) for h in hits], (M, 290, W - M, 1010), pad=10)
    rc = f(robot)
    for rr in (1.5, 3.0, 4.5):
        s = f((rr, 0))[0] - rc[0]
        svg.circle(*rc, s, "none", stroke=P.blue, stroke_width=1.5, stroke_dasharray="2 8", opacity=0.7)
    for i, (x, y, t) in enumerate(hits):
        if i % 6 == 0:
            svg.line(*rc, *f((x, y)), P.blue, 1, opacity=0.35)
    for x, y, t in hits:
        col = P.teal_60 if t < 2.0 else P.lavender
        svg.circle(*f((x, y)), 3, col)
    svg.triangle(rc[0], rc[1], 46, P.blue, -math.pi / 2)
    svg.circle(*rc, 5, P.white)

    svg.frame("see.", "laser scan · 540 rays · nothing but points", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
for (int i = 0; i < n; ++i) {
    const double th = 2.0 * M_PI * i / n;
    const double r  = ranges[i];
    cloud.emplace_back(r * std::cos(th), r * std::sin(th));
}""", "cpp", 20, dark=True)
    return svg


# ----------------------------------------------------------------------------
def settle() -> Svg:
    """Closed-loop step responses of one plant under three PID tunings."""
    svg = Svg(P.cream)

    def simulate(kp, ki, kd, T=10.0, dt=0.002):
        y = v = integ = 0.0
        e_prev = 1.0
        out = []
        for k in range(int(T / dt)):
            e = 1.0 - y
            integ += e * dt
            d = (e - e_prev) / dt
            e_prev = e
            u = kp * e + ki * integ + kd * d
            a = (u - 0.6 * v) / 1.0  # mass 1, damping 0.6
            v += a * dt
            y += v * dt
            if k % 10 == 0:
                out.append((k * dt, y))
        return out

    x0, x1, y0, y1 = M + 10, W - M - 120, 900, 360  # y of value 0 and of value 1.6
    def px(t, v, T=10.0):
        return x0 + (x1 - x0) * t / T, y0 + (y1 - y0) * v / 1.6

    svg.line(x0, y0, x1, y0, P.black, 3)
    sp = px(0, 1.0)[1]
    svg.line(x0, sp, x1, sp, P.black, 2, stroke_dasharray="10 10")
    svg.text(x1 + 18, sp + 7, "r = 1", "code", 20, P.black)

    curves = [
        (simulate(9.0, 2.5, 0.2), P.lavender, 4, "kp=9  ki=2.5  kd=0.2"),
        (simulate(1.2, 0.3, 2.4), P.blue_40, 4, "kp=1.2 ki=0.3  kd=2.4"),
        (simulate(5.0, 1.5, 2.6), P.teal, 7, "kp=5  ki=1.5  kd=2.6"),
    ]
    for pts_, col, w, _ in curves:
        svg.polyline([px(t, v) for t, v in pts_], col, w)
    lx, ly = x0, 970
    for i, (_, col, w, label) in enumerate([curves[2], curves[0], curves[1]]):
        y = ly + i * 0
        xx = lx + i * 290
        svg.rect(xx, y - 6, 28, 7 if col != P.teal else 9, col)
        svg.text(xx + 40, y + 2, label, "codel", 15, P.black_80)

    svg.frame("settle.", "PID · closed-loop step response")
    code_rule(svg)
    svg.code(M, CODE_Y, """
e = r - y
i += e * dt
d = (e - e_prev) / dt
u = kp*e + ki*i + kd*d   # one line, every robot""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def hello() -> Svg:
    """Two languages, one robot: a diagonal split like the brand's triangles."""
    svg = Svg(P.black)
    svg.poly([(0, 0), (W, 0), (0, H)], P.blue)
    svg.text(M, 360, ">>>", "code", 24, P.lavender_60)
    svg.code(M, 430, 'print("hello, robot")', "py", 44, dark=True)
    svg.text(M, 496, "# python", "codel", 20, P.blue_40)

    x = 400
    svg.text(x, 860, "// c++", "codel", 20, P.black_60)
    svg.code(x, 920, r'''
#include <iostream>

int main() {
    std::cout << "hello, robot\n";
}''', "cpp", 24, dark=True)
    svg.rect(x + 22, 920 + 4 * 24 * 1.55 - 22, 13, 27, P.teal)  # cursor after the brace
    svg.frame("hello.", "two languages, one robot", dark=True, title_fill=P.white)
    return svg


# ----------------------------------------------------------------------------
def build() -> Svg:
    """A robot face built from a triangular lattice, like the brand book cover."""
    svg = Svg(P.white)
    rng = random.Random(3)
    s = 34
    h = s * math.sqrt(3) / 2
    cx, cy = W / 2, 660

    def in_rrect(x, y, x0, y0, x1, y1, r):
        qx = max(x0 + r - x, 0, x - (x1 - r))
        qy = max(y0 + r - y, 0, y - (y1 - r))
        return x0 <= x <= x1 and y0 <= y <= y1 and qx * qx + qy * qy <= r * r

    def colour(gx, gy):
        dx, dy = gx - cx, gy - cy
        for sx in (-1, 1):
            ex, ey = cx + sx * 112, cy - 40
            d = math.hypot(gx - ex, gy - ey)
            if math.hypot(gx - ex - 12, gy - ey - 6) < 24:
                return P.black
            if d < 58:
                return P.white
        smile = math.hypot(dx, gy - (cy + 10))
        if abs(smile - 118) < 15 and gy > cy + 70:
            return P.teal
        if in_rrect(gx, gy, cx - 240, cy - 190, cx + 240, cy + 185, 64):
            return P.blue if rng.random() < 0.78 else P.blue_80
        if abs(dx) < 10 and cy - 300 < gy < cy - 185:
            return P.black
        if math.hypot(dx, gy - (cy - 318)) < 34:
            return P.teal
        if 240 < abs(dx) < 290 and abs(dy + 10) < 60:
            return P.black
        if cy + 185 < gy < cy + 250 and abs(dx) < 90:
            return P.black_80
        dist = math.hypot(dx, dy * 1.25)
        if rng.random() < max(0.0, 0.42 - dist / 1100):
            return rng.choice([P.blue_20, P.lavender_20, P.lavender_60, P.blue_20])
        return None

    rows = int((ART[3] + 40 - ART[1]) / h)
    for r in range(rows):
        for c in range(-2, int(W / (s / 2)) + 2):
            up = (r + c) % 2 == 0
            x, y = c * s / 2, ART[1] - 10 + r * h
            tri = [(x, y + h), (x + s / 2, y), (x + s, y + h)] if up else [(x, y), (x + s, y), (x + s / 2, y + h)]
            gx, gy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
            if not (M - 20 < gx < W - M + 20):
                continue
            col = colour(gx, gy)
            if col:
                svg.poly(tri, col, stroke=P.white, stroke_width=1.2, stroke_linejoin="round")

    svg.frame("build.", "triangles all the way down")
    code_rule(svg)
    svg.code(M, CODE_Y, """
class Robot:
    def __init__(self):
        self.mood = "curious"
        self.parts = [Sensor(), Brain(), Motor()]""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def drive() -> Svg:
    """A differential-drive robot following a wandering path: two wheel tracks and its poses."""
    svg = Svg(P.cream)
    Lw = 0.22
    x = y = 0.0
    th = 0.3
    dt = 0.01
    path, left, right, poses = [], [], [], []
    for k in range(int(26 / dt)):
        t = k * dt
        v_l = 1.0 - 0.85 * math.sin(0.62 * t) * 0.4 - 0.25 * math.sin(0.23 * t + 0.4)
        v_r = 1.0 + 0.85 * math.sin(0.62 * t) * 0.4 + 0.25 * math.sin(0.23 * t + 0.4)
        v, w = (v_r + v_l) / 2, (v_r - v_l) / Lw
        x += v * math.cos(th) * dt
        y += v * math.sin(th) * dt
        th += w * dt
        nx, ny = -math.sin(th), math.cos(th)
        path.append((x, y))
        left.append((x + nx * Lw / 2, y + ny * Lw / 2))
        right.append((x - nx * Lw / 2, y - ny * Lw / 2))
        if k % 110 == 0:
            poses.append((x, y, th))

    f = fit(left + right, pad=30)
    svg.polyline([f(p) for p in left], P.blue, 2.5)
    svg.polyline([f(p) for p in right], P.teal, 2.5)
    for i, (px_, py_, th_) in enumerate(poses[1:], 1):
        c = f((px_, py_))
        svg.triangle(*c, 30, P.black if i < len(poses) - 1 else P.blue, -th_, opacity=1)
    last = f(path[-1])
    svg.triangle(*last, 52, P.blue, -th)

    svg.frame("drive.", "differential drive · two wheels, one path")
    code_rule(svg)
    svg.code(M, CODE_Y, """
def diff_drive(v_l, v_r, L):
    v = (v_r + v_l) / 2      # forward speed
    ω = (v_r - v_l) / L      # turn rate
    return v, ω""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def plan() -> Svg:
    """A* on an occupancy grid: obstacles, the explored set fading by order, and the path."""
    svg = Svg(P.white)
    cols, rows, cs = 25, 21, 33
    ox = (W - cols * cs) / 2
    oy = 290
    rng = random.Random(11)
    occ = [[False] * cols for _ in range(rows)]

    def wall(c0, r0, c1, r1):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                occ[r][c] = True

    wall(5, 0, 5, 13)
    wall(11, 6, 11, 20)
    wall(17, 0, 17, 9)
    wall(17, 13, 23, 13)
    wall(1, 17, 7, 17)
    for _ in range(14):
        occ[rng.randrange(rows)][rng.randrange(cols)] = True
    start, goal = (19, 1), (1, 23)  # (row, col)
    occ[start[0]][start[1]] = occ[goal[0]][goal[1]] = False

    def hfn(a):
        dr, dc = abs(a[0] - goal[0]), abs(a[1] - goal[1])
        return max(dr, dc) + (math.sqrt(2) - 1) * min(dr, dc)

    g = {start: 0.0}
    came = {}
    order = []
    open_ = [(hfn(start), start)]
    closed = set()
    while open_:
        _, n = heapq.heappop(open_)
        if n in closed:
            continue
        closed.add(n)
        order.append(n)
        if n == goal:
            break
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not dr and not dc:
                    continue
                m = (n[0] + dr, n[1] + dc)
                if not (0 <= m[0] < rows and 0 <= m[1] < cols) or occ[m[0]][m[1]]:
                    continue
                if dr and dc and (occ[n[0] + dr][n[1]] or occ[n[0]][n[1] + dc]):
                    continue
                ng = g[n] + (math.sqrt(2) if dr and dc else 1)
                if ng < g.get(m, 1e9):
                    g[m], came[m] = ng, n
                    heapq.heappush(open_, (ng + hfn(m), m))
    path = [goal]
    while path[-1] in came:
        path.append(came[path[-1]])

    def center(n):
        return ox + n[1] * cs + cs / 2, oy + n[0] * cs + cs / 2

    for r in range(rows):
        for c in range(cols):
            x, y = ox + c * cs, oy + r * cs
            if occ[r][c]:
                svg.rect(x + 1, y + 1, cs - 2, cs - 2, P.black)
            else:
                svg.circle(x + cs / 2, y + cs / 2, 1.6, P.black_20)
    for i, n in enumerate(order):
        x, y = ox + n[1] * cs, oy + n[0] * cs
        op = 0.12 + 0.75 * (1 - i / len(order)) ** 2
        svg.rect(x + 7, y + 7, cs - 14, cs - 14, P.lavender, opacity=f"{op:.2f}")
    svg.polyline([center(n) for n in path], P.teal, 8)
    svg.triangle(*center(start), 34, P.blue, -math.pi / 2)
    svg.circle(*center(goal), 12, P.blue)
    svg.circle(*center(goal), 20, "none", stroke=P.blue, stroke_width=3)

    svg.frame("plan.", "A* on an occupancy grid")
    code_rule(svg)
    svg.code(M, CODE_Y, """
while open_set:
    f, node = heapq.heappop(open_set)
    if node == goal:
        return reconstruct(came_from, node)
    expand(node)""", "py", 21)
    return svg


POSTERS = [reach, see, settle, hello, build, drive, plan]

if __name__ == "__main__":
    for fn in POSTERS:
        out = fn().save(fn.__name__, "core")
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
