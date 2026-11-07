"""Epic: five big, dense posters. One word, one simulation run to the edges of the paper, one line of code.

The opposite of the minimal set: instead of one mark on empty paper, thousands of marks, every one
of them computed. Same palette, same furniture, same rule: the drawing is the output of the code
printed under it.

chaos. explore. field. swarm. descend.

Run:  uv run --no-project --with fonttools --with brotli python src/epic.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from posters import CODE_Y, M, W, code_rule, fit  # noqa: E402

SERIES = "epic"
BOX = (M, 262, W - M, 1004)  # the drawing area, a little taller than ART


def mix(a: str, b: str, t: float) -> str:
    """Blend two #rrggbb colours: t = 0 gives a, t = 1 gives b."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def ramp(stops, t: float) -> str:
    """Blend along several colours, t in [0, 1]."""
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return mix(stops[i], stops[i + 1], t - i)


def furniture(svg: Svg, title: str, kicker: str, title_fill: str, kicker_fill: str, marker: tuple) -> None:
    """artkit's frame() with the colours passed in, so the blue poster can carry it too."""
    svg.text(M, M + 70, title, "head", 92, title_fill, letter_spacing="-2")
    svg.text(M + 4, M + 118, kicker, "codel", 20, kicker_fill)
    t = 150
    tri, op, mark = marker
    svg.poly([(svg.w, svg.h - t * 0.95), (svg.w, svg.h), (svg.w - t * 1.1, svg.h)], tri, opacity=op)
    svg.logo_mark(svg.w - 62, svg.h - 44, 30, mark)


def path_d(points) -> str:
    return "M" + "L".join(f"{_fmt(x)},{_fmt(y)}" for x, y in points)


# ----------------------------------------------------------------------------
def chaos() -> Svg:
    """The Lorenz system: three equations, 48 000 RK4 steps, a path that never crosses itself or repeats."""
    svg = Svg(P.black)
    s, r, b = 10.0, 28.0, 8 / 3

    def f(p):
        x, y, z = p
        return (s * (y - x), x * (r - z) - y, x * y - b * z)

    def rk4(p, h):
        k1 = f(p)
        k2 = f(tuple(pi + h / 2 * ki for pi, ki in zip(p, k1)))
        k3 = f(tuple(pi + h / 2 * ki for pi, ki in zip(p, k2)))
        k4 = f(tuple(pi + h * ki for pi, ki in zip(p, k3)))
        return tuple(pi + h / 6 * (a + 2 * bb + 2 * c + d) for pi, a, bb, c, d in zip(p, k1, k2, k3, k4))

    p, h = (0.1, 0.0, 0.0), 0.004
    for _ in range(2000):  # let it fall onto the attractor first
        p = rk4(p, h)
    pts = []
    for k in range(48000):
        p = rk4(p, h)
        if k % 2 == 0:
            pts.append(p)
    proj = [(x, z) for x, y, z in pts]  # the classic x–z view: two wings
    to = fit(proj, BOX, pad=6)
    page = [to(q) for q in proj]

    chunk = 240
    n = len(page) // chunk
    stops = [P.blue, P.blue_80, P.lavender, P.lavender_60, P.cream]
    for i in range(n):
        seg = page[i * chunk:(i + 1) * chunk + 1]
        svg.add(f'<path d="{path_d(seg)}" fill="none" stroke="{ramp(stops, i / (n - 1))}" '
                f'stroke-width="0.8" stroke-opacity="0.85" stroke-linejoin="round"/>')
    svg.circle(*page[-1], 5, P.cream)

    furniture(svg, "chaos.", "lorenz · σ = 10, ρ = 28, β = 8/3 · never the same loop twice",
              P.white, P.blue_40, (P.blue_60, 0.3, P.blue_40))
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "dx, dy, dz = s*(y - x), x*(r - z) - y, x*y - b*z", "py", 22, dark=True)
    return svg


# ----------------------------------------------------------------------------
def explore() -> Svg:
    """RRT*: 5000 random samples grow a tree through a slalom of walls; rewiring straightens it."""
    svg = Svg(P.white)
    rng = random.Random(7)
    x0, y0, x1, y1 = BOX
    walls = [  # x, y, w, h: three walls, gaps alternating bottom / top / bottom
        (300, y0, 26, 560), (520, y1 - 560, 26, 560), (740, y0, 26, 560),
    ]
    discs = [(190, 820, 46), (420, 360, 38), (640, 900, 42), (860, 760, 52), (420, 640, 30), (640, 470, 34)]
    start, goal = (x0 + 40, y0 + 60), (x1 - 40, y1 - 60)

    def free(x, y, pad=6):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        for wx, wy, ww, wh in walls:
            if wx - pad <= x <= wx + ww + pad and wy - pad <= y <= wy + wh + pad:
                return False
        return all((x - cx) ** 2 + (y - cy) ** 2 > (cr + pad) ** 2 for cx, cy, cr in discs)

    def clear(a, b):
        d = math.dist(a, b)
        n = max(1, int(d / 3))
        return all(free(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1))

    CELL, STEP, RAD = 30, 20, 46
    nodes, parent, cost, kids = [start], [-1], [0.0], [[]]
    grid: dict = {}

    def put(i):
        x, y = nodes[i]
        grid.setdefault((int(x // CELL), int(y // CELL)), []).append(i)

    def near(p, rad):
        cx, cy, k = int(p[0] // CELL), int(p[1] // CELL), int(rad // CELL) + 1
        return [i for gx in range(cx - k, cx + k + 1) for gy in range(cy - k, cy + k + 1)
                for i in grid.get((gx, gy), ()) if math.dist(nodes[i], p) <= rad]

    def nearest(p):
        for rad in (CELL, 2 * CELL, 4 * CELL, 8 * CELL, 2000):
            c = near(p, rad)
            if c:
                return min(c, key=lambda i: math.dist(nodes[i], p))

    def push_cost(i, delta):
        stack = [i]
        while stack:
            j = stack.pop()
            cost[j] += delta
            stack.extend(kids[j])

    put(0)
    while len(nodes) < 5000:
        q = goal if rng.random() < 0.02 else (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if not free(*q):
            continue
        i = nearest(q)
        d = math.dist(nodes[i], q)
        if d < 1e-6:
            continue
        p = q if d <= STEP else (nodes[i][0] + (q[0] - nodes[i][0]) * STEP / d, nodes[i][1] + (q[1] - nodes[i][1]) * STEP / d)
        if not clear(nodes[i], p):
            continue
        nb = [j for j in near(p, RAD) if clear(nodes[j], p)] or [i]
        best = min(nb, key=lambda j: cost[j] + math.dist(nodes[j], p))
        k = len(nodes)
        nodes.append(p); parent.append(best); cost.append(cost[best] + math.dist(nodes[best], p)); kids.append([])
        kids[best].append(k)
        put(k)
        for j in nb:  # rewire: would going through the new node be cheaper?
            c = cost[k] + math.dist(p, nodes[j])
            if j != best and c < cost[j] - 1e-9:
                kids[parent[j]].remove(j)
                parent[j] = k
                kids[k].append(j)
                push_cost(j, c - cost[j])

    cmax = max(cost)
    bands = 14
    groups = [[] for _ in range(bands)]
    for k in range(1, len(nodes)):
        groups[min(bands - 1, int(cost[k] / cmax * bands))].append((nodes[parent[k]], nodes[k]))
    for g, segs in enumerate(groups):
        if segs:
            d = "".join(f"M{_fmt(a[0])},{_fmt(a[1])}L{_fmt(b[0])},{_fmt(b[1])}" for a, b in segs)
            svg.add(f'<path d="{d}" fill="none" stroke="{ramp([P.blue_80, P.lavender, P.teal_60], g / (bands - 1))}" '
                    f'stroke-width="1.3" stroke-linecap="round"/>')

    for wx, wy, ww, wh in walls:
        svg.rect(wx, wy, ww, wh, P.black)
    for cx, cy, cr in discs:
        svg.circle(cx, cy, cr, P.black)

    end = min((k for k in range(len(nodes)) if math.dist(nodes[k], goal) < 26), key=lambda k: cost[k])
    route = [goal]
    while end != -1:
        route.append(nodes[end])
        end = parent[end]
    svg.polyline(route, P.white, 12)
    svg.polyline(route, P.blue, 6)
    svg.triangle(*start, 34, P.black, angle=-math.pi / 2)
    svg.circle(*goal, 20, "none", stroke=P.teal, stroke_width=5)
    svg.circle(*goal, 8, P.teal)

    furniture(svg, "explore.", "rrt* · 5000 random guesses, one short way through",
              P.blue, P.black_60, (P.blue_20, 1, P.blue_60))
    code_rule(svg)
    svg.code(M, CODE_Y, "x_new = steer(nearest(tree, sample()), step)\nrewire(tree, near(tree, x_new, r))", "py", 22)
    return svg


# ----------------------------------------------------------------------------
def field() -> Svg:
    """A potential field: 150 robots pulled to one goal, pushed off nine obstacles; a few get stuck."""
    svg = Svg(P.cream)
    x0, y0, x1, y1 = BOX
    goal = (760, 420)
    obs = [(300, 470, 54), (520, 360, 40), (470, 640, 70), (690, 640, 46), (250, 800, 38),
           (850, 860, 60), (620, 880, 34), (880, 300, 30), (380, 920, 30)]
    D0, ETA = 70.0, 2600.0

    def grad(x, y):
        dx, dy = x - goal[0], y - goal[1]
        dg = math.hypot(dx, dy) or 1e-9
        gx, gy = dx / dg, dy / dg  # conic attraction: constant pull
        for cx, cy, cr in obs:
            ox, oy = x - cx, y - cy
            dc = math.hypot(ox, oy) or 1e-9
            d = max(dc - cr, 0.5)
            if d < D0:
                k = ETA * (1 / d - 1 / D0) / (d * d)
                gx -= k * ox / dc
                gy -= k * oy / dc
        return gx, gy

    svg.clip_begin(*BOX[:2], BOX[2] - BOX[0], BOX[3] - BOX[1])
    for cx, cy, cr in obs:  # isopotential rings
        for k in range(1, 4):
            svg.circle(cx, cy, cr + k * D0 / 4, "none", stroke=P.lavender_60, stroke_width=1, stroke_opacity=f"{0.6 - k * 0.15:.2f}")
    svg.clip_end()

    starts = []
    per = (2 * (x1 - x0) + 2 * (y1 - y0)) / 160
    t = per / 2
    while t < 2 * (x1 - x0) + 2 * (y1 - y0):
        if t < x1 - x0:
            p = (x0 + t, y1)
        elif t < (x1 - x0) + (y1 - y0):
            p = (x0, y1 - (t - (x1 - x0)))
        elif t < 2 * (x1 - x0) + (y1 - y0):
            p = (x0 + (t - (x1 - x0) - (y1 - y0)), y0)
        else:
            p = (x1, y0 + (t - 2 * (x1 - x0) - (y1 - y0)))
        starts.append(p)
        t += per

    stuck_ends = []
    for i, (x, y) in enumerate(starts):
        tr = [(x, y)]
        stuck = False
        for step in range(1400):
            gx, gy = grad(x, y)
            n = math.hypot(gx, gy)
            if n < 0.05:
                stuck = True
                break
            x, y = x - 3 * gx / n, y - 3 * gy / n
            tr.append((x, y))
            if math.dist((x, y), goal) < 6:
                break
            if step > 120 and math.dist(tr[-120], (x, y)) < 8:
                stuck = True
                break
        else:
            stuck = True
        col = P.black_20 if stuck else ramp([P.teal, P.blue, P.lavender, P.teal], i / len(starts))
        svg.polyline(tr[::2] + [tr[-1]], col, 1.6, stroke_opacity="0.9")
        if stuck:
            stuck_ends.append((x, y))

    for cx, cy, cr in obs:
        svg.circle(cx, cy, cr, P.black)
    for p in stuck_ends:
        svg.circle(*p, 6, P.cream, stroke=P.black_60, stroke_width=2)
    svg.circle(*goal, 22, P.cream, stroke=P.blue, stroke_width=5)
    svg.circle(*goal, 9, P.blue)

    fate = f"{len(stuck_ends)} stuck in a local minimum" if stuck_ends else "every one home"
    furniture(svg, "field.", f"potential field · {len(starts)} starts, {fate}", P.blue, P.black_60, (P.blue_20, 1, P.blue_60))
    code_rule(svg)
    svg.code(M, CODE_Y, "v = -grad(U_goal + sum(U_obstacle))(x)", "py", 22)
    return svg


# ----------------------------------------------------------------------------
def swarm() -> Svg:
    """Boids: separation, alignment, cohesion. 140 agents, no leader, only neighbours."""
    svg = Svg(P.blue)
    rng = random.Random(3)
    x0, y0, x1, y1 = BOX
    N, STEPS, TAIL = 160, 360, 360
    pos = [[rng.uniform(x0, x1), rng.uniform(y0, y1)] for _ in range(N)]
    vel = [[3 * math.cos(a), 3 * math.sin(a)] for a in (rng.uniform(0, 2 * math.pi) for _ in range(N))]
    hist = [[] for _ in range(N)]
    VMAX, R_SEE, R_SEP = 4.2, 70.0, 22.0

    for t in range(STEPS):
        lure = ((x0 + x1) / 2 + 330 * math.sin(t / 52), (y0 + y1) / 2 + 280 * math.sin(t / 37 + 1))  # where food is
        acc = []
        for i in range(N):
            sx = sy = ax = ay = cx = cy = 0.0
            n = 0
            px, py = pos[i]
            for j in range(N):
                if i == j:
                    continue
                dx, dy = pos[j][0] - px, pos[j][1] - py
                d2 = dx * dx + dy * dy
                if d2 < R_SEE * R_SEE:
                    n += 1
                    ax += vel[j][0]; ay += vel[j][1]
                    cx += dx; cy += dy
                    if d2 < R_SEP * R_SEP:
                        sx -= dx / (d2 + 1); sy -= dy / (d2 + 1)
            fx, fy = 14 * sx, 14 * sy
            if n:
                fx += 0.06 * (ax / n - vel[i][0]) + 0.004 * cx / n
                fy += 0.06 * (ay / n - vel[i][1]) + 0.004 * cy / n
            lx, ly = lure[0] - px, lure[1] - py
            ld = math.hypot(lx, ly) or 1
            k = 0.012 if t < 140 else 0.05  # the lure only shows up once the flocks have formed
            fx += k * lx / ld + rng.gauss(0, 0.05); fy += k * ly / ld + rng.gauss(0, 0.05)
            fx += 0.08 * ((px < x0 + 30) - (px > x1 - 30)); fy += 0.08 * ((py < y0 + 30) - (py > y1 - 30))  # walls
            acc.append((fx, fy))
        for i in range(N):
            vel[i][0] += acc[i][0]; vel[i][1] += acc[i][1]
            sp = math.hypot(*vel[i])
            if sp > VMAX:
                vel[i][0] *= VMAX / sp; vel[i][1] *= VMAX / sp
            pos[i][0] += vel[i][0]; pos[i][1] += vel[i][1]
            if t >= STEPS - TAIL:
                hist[i].append(tuple(pos[i]))

    pieces = 9
    svg.clip_begin(x0 - 40, y0 - 40, x1 - x0 + 80, y1 - y0 + 80)
    for i in range(N):
        tr = hist[i]
        L = len(tr) // pieces
        for k in range(pieces):
            seg = tr[k * L:(k + 1) * L + 1:2]
            svg.polyline(seg, P.white, 1.4, stroke_opacity=f"{0.05 + 0.55 * (k / (pieces - 1)) ** 2:.2f}")
    svg.clip_end()
    for i in range(N):
        a = math.atan2(vel[i][1], vel[i][0])
        x, y = pos[i]
        r = 9
        tip = (x + r * math.cos(a), y + r * math.sin(a))
        l = (x + r * math.cos(a + 2.5), y + r * math.sin(a + 2.5))
        rr = (x + r * math.cos(a - 2.5), y + r * math.sin(a - 2.5))
        svg.poly([tip, l, rr], P.cream if i % 9 else P.teal_60)

    furniture(svg, "swarm.", f"boids · {N} agents, three rules, no leader", P.white, P.lavender_20, (P.blue_80, 1, P.blue_40))
    svg.rect(M, CODE_Y - 52, 56, 5, P.cream)
    svg.text(M, CODE_Y, "v += 14*separate + 0.06*align + 0.004*cohere", "code", 22, P.white)
    return svg


# ----------------------------------------------------------------------------
def descend() -> Svg:
    """Gradient descent with momentum on a loss with three valleys: 72 starts, colour by where they end."""
    svg = Svg(P.white)
    rng = random.Random(11)
    wells = [(-1.7, 0.9, 1.25, 0.95), (1.6, 1.1, 1.0, 0.8), (0.3, -1.4, 1.4, 1.05)]  # cx, cy, depth, width

    def loss(x, y):
        v = 0.06 * (x * x + y * y) + 0.05 * math.sin(2.6 * x) * math.cos(2.2 * y)
        for cx, cy, a, s in wells:
            v -= a * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s * s))
        return v

    def grad(x, y, e=1e-4):
        return ((loss(x + e, y) - loss(x - e, y)) / (2 * e), (loss(x, y + e) - loss(x, y - e)) / (2 * e))

    X0, X1, Y0, Y1 = -3.6, 3.6, -2.9, 2.9
    bx0, by0, bx1, by1 = BOX

    def to(p):
        return (bx0 + (p[0] - X0) / (X1 - X0) * (bx1 - bx0), by1 - (p[1] - Y0) / (Y1 - Y0) * (by1 - by0))

    # contours by marching squares
    NX, NY = 190, 156
    gx = [X0 + (X1 - X0) * i / NX for i in range(NX + 1)]
    gy = [Y0 + (Y1 - Y0) * j / NY for j in range(NY + 1)]
    V = [[loss(x, y) for x in gx] for y in gy]
    lo, hi = min(map(min, V)), max(map(max, V))
    levels = 22
    for li in range(levels):
        c = lo + (hi - lo) * (li + 0.5) / levels
        segs = []
        for j in range(NY):
            for i in range(NX):
                corners = [(gx[i], gy[j], V[j][i]), (gx[i + 1], gy[j], V[j][i + 1]),
                           (gx[i + 1], gy[j + 1], V[j + 1][i + 1]), (gx[i], gy[j + 1], V[j + 1][i])]
                cross = []
                for k in range(4):
                    (ax, ay, av), (bx, by, bv) = corners[k], corners[(k + 1) % 4]
                    if (av < c) != (bv < c):
                        u = (c - av) / (bv - av)
                        cross.append(to((ax + (bx - ax) * u, ay + (by - ay) * u)))
                for k in range(0, len(cross) - 1, 2):
                    segs.append((cross[k], cross[k + 1]))
        d = "".join(f"M{_fmt(a[0])},{_fmt(a[1])}L{_fmt(b[0])},{_fmt(b[1])}" for a, b in segs)
        t = li / (levels - 1)
        svg.add(f'<path d="{d}" fill="none" stroke="{ramp([P.blue_60, P.lavender_60, P.black_20], t)}" '
                f'stroke-width="{_fmt(1.6 - 0.8 * t)}"/>')

    cols = [P.blue, P.teal, P.lavender]
    ends = []
    for _ in range(72):
        x, y = rng.uniform(X0 + 0.2, X1 - 0.2), rng.uniform(Y0 + 0.2, Y1 - 0.2)
        vx = vy = 0.0
        tr = [(x, y)]
        for _ in range(500):
            g = grad(x, y)
            vx, vy = 0.9 * vx - 0.05 * g[0], 0.9 * vy - 0.05 * g[1]
            x, y = x + vx, y + vy
            tr.append((x, y))
        k = min(range(3), key=lambda w: (x - wells[w][0]) ** 2 + (y - wells[w][1]) ** 2)
        ends.append((x, y, k))
        page = [to(p) for p in tr[:240]]
        svg.polyline(page, P.white, 4.5)
        svg.polyline(page, cols[k], 2)
        svg.circle(*page[0], 4.5, P.white, stroke=cols[k], stroke_width=2)
    for k in range(3):  # the minimum each colour found
        xs = [(x, y) for x, y, w in ends if w == k]
        if xs:
            m = to((sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs)))
            svg.circle(*m, 13, cols[k], stroke=P.white, stroke_width=4)

    counts = [sum(1 for e in ends if e[2] == k) for k in range(3)]
    furniture(svg, "descend.", f"momentum sgd · 72 starts → three valleys ({counts[0]} · {counts[1]} · {counts[2]})",
              P.blue, P.black_60, (P.blue_20, 1, P.blue_60))
    code_rule(svg)
    svg.code(M, CODE_Y, "v = 0.9*v - lr*grad(loss, w)\nw = w + v", "py", 22)
    return svg


POSTERS = [chaos, explore, field, swarm, descend]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, SERIES)
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
