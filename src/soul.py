"""Soul: photogrammetry without the pipeline. Five posters about what it feels like, not how it works.

Many eyes on one thing; walking around it; guesses settling into a shape; the side nobody looked at;
a hill remembered from above. Still every mark is computed, by the line printed under it.

witness. circle. become. unseen. land.

Run:  uv run --no-project --with fonttools --with brotli python src/soul.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from epic import BOX, furniture, mix, path_d, ramp  # noqa: E402
from posters import CODE_Y, M, code_rule, fit  # noqa: E402

SERIES = "soul"
DARK_MARK = (P.blue_60, 0.3, P.blue_40)
LIGHT_MARK = (P.blue_20, 1, P.blue_60)


# --- a little 3D --------------------------------------------------------------
def view(p, yaw: float, pitch: float, dist: float):
    """Turn the world by yaw (about z) then pitch (about x), and project with a pinhole at `dist`.
    Returns (u, v, depth): u right, v up, depth > 0 away from the eye."""
    x, y, z = p
    x, y = x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw)
    y, z = y * math.cos(pitch) - z * math.sin(pitch), y * math.sin(pitch) + z * math.cos(pitch)
    d = dist + y  # the eye sits at y = -dist, looking along +y
    return x * dist / d, z * dist / d, d


def fibonacci(n: int):
    """n directions spread evenly over the unit sphere."""
    g = math.pi * (3 - math.sqrt(5))
    for k in range(n):
        z = 1 - 2 * (k + 0.5) / n
        r = math.sqrt(1 - z * z)
        yield (r * math.cos(g * k), r * math.sin(g * k), z)


def stone(seed: int):
    """A smooth pebble: the unit sphere pushed in and out by a few low harmonics."""
    rng = random.Random(seed)
    waves = [(rng.uniform(0.04, 0.11), rng.randint(1, 3), rng.randint(1, 3), rng.uniform(0, 6.3)) for _ in range(5)]

    def radius(d):
        th, ph = math.atan2(d[1], d[0]), math.acos(max(-1, min(1, d[2])))
        return 1 + sum(a * math.sin(m * th + s) * math.sin(n * ph + s) for a, m, n, s in waves)

    def at(d, sx=1.25, sz=0.82):
        r = radius(d)
        return (d[0] * r * sx, d[1] * r, d[2] * r * sz)

    def normal(d, e=1e-3):  # finite differences on the surface around direction d
        p = at(d)
        t1 = (-d[1], d[0], 0) if abs(d[2]) < 0.9 else (0, -d[2], d[1])
        n1 = math.hypot(*t1)
        t1 = tuple(c / n1 for c in t1)
        t2 = (d[1] * t1[2] - d[2] * t1[1], d[2] * t1[0] - d[0] * t1[2], d[0] * t1[1] - d[1] * t1[0])

        def nudge(t):
            q = tuple(a + e * b for a, b in zip(d, t))
            nq = math.hypot(*q)
            return at(tuple(c / nq for c in q))

        a, b = nudge(t1), nudge(t2)
        u = tuple(x - y for x, y in zip(a, p))
        v = tuple(x - y for x, y in zip(b, p))
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.hypot(*n)
        n = tuple(c / ln for c in n)
        return n if sum(a * b for a, b in zip(n, p)) > 0 else tuple(-c for c in n)

    return at, normal


def sees(cam, p, n, cos_min=0.15) -> bool:
    """A camera sees a surface point when the point faces it."""
    v = tuple(c - q for c, q in zip(cam, p))
    lv = math.hypot(*v)
    return sum(a * b for a, b in zip(n, v)) / lv > cos_min


# ----------------------------------------------------------------------------
def witness() -> Svg:
    """96 cameras on a dome around one stone. Each draws its sight lines to the points it can see;
    the stone appears where the lines pile up."""
    svg = Svg(P.black)
    rng = random.Random(3)
    at, normal = stone(11)
    dirs = list(fibonacci(2600))
    surf = [(at(d), normal(d)) for d in dirs]

    cams = []
    for ring, (elev, n) in enumerate([(6, 40), (30, 32), (56, 24)]):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * ring) / n
            e = math.radians(elev)
            cams.append((3.5 * math.cos(e) * math.cos(a), 3.5 * math.cos(e) * math.sin(a), 3.5 * math.sin(e) - 0.3))

    yaw, pitch, dist = 0.35, -0.42, 11.0
    V = lambda p: view(p, yaw, pitch, dist)  # noqa: E731
    pv = [V(p) for p, _ in surf]
    cv = [V(c) for c in cams]
    to = fit([(u, v) for u, v, _ in cv + pv], BOX, pad=26)

    # sight lines: each camera to a dozen of the points it can see, far cameras first
    rays = []
    for ci, c in enumerate(cams):
        seen = [i for i, (p, n) in enumerate(surf) if sees(c, p, n, 0.35)]
        for i in rng.sample(seen, min(14, len(seen))):
            rays.append((cv[ci][2], ci, i))
    rays.sort(reverse=True)
    dmin, dmax = min(c[2] for c in cv), max(c[2] for c in cv)
    for d, ci, i in rays:
        t = (dmax - d) / (dmax - dmin)
        a, b = to(cv[ci][:2]), to(pv[i][:2])
        svg.line(*a, *b, mix(P.blue, P.lavender, t), 0.5, stroke_opacity=f"{0.18 + 0.32 * t:.2f}")

    # the stone: how many cameras agree on each point sets its light
    votes = [sum(sees(c, p, n) for c in cams) for p, n in surf]
    vmax = max(votes)
    order = sorted(range(len(surf)), key=lambda i: -pv[i][2])
    pmin, pmax = min(q[2] for q in pv), max(q[2] for q in pv)
    for i in order:
        near = (pmax - pv[i][2]) / (pmax - pmin)
        glow = votes[i] / vmax
        svg.circle(*to(pv[i][:2]), 1.1 + 1.6 * near, ramp([P.blue_80, P.lavender, P.cream], 0.25 + 0.75 * glow * (0.4 + 0.6 * near)),
                   opacity=f"{0.35 + 0.65 * near:.2f}")

    # the eyes
    for c in sorted(cv, key=lambda q: -q[2]):
        near = (dmax - c[2]) / (dmax - dmin)
        x, y = to(c[:2])
        cx, cy = to((0, 0))
        svg.triangle(x, y, 7 + 7 * near, mix(P.blue_60, P.cream, near), math.atan2(cy - y, cx - x))

    furniture(svg, "witness.", f"{len(cams)} eyes · one stone · it is real where they agree",
              P.white, P.blue_40, DARK_MARK)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "stone = [p for p in points if agree(eyes, p)]", "py", 22, dark=True)
    return svg


# ----------------------------------------------------------------------------
def circle() -> Svg:
    """A walk around something, climbing as it goes: 150 photographs, every one turned to the middle.
    The subject is never drawn; it's the place all the frames face."""
    svg = Svg(P.white)
    yaw, pitch, dist = 0.2, -0.32, 9.0
    V = lambda p: view(p, yaw, pitch, dist)  # noqa: E731
    N, turns, R = 220, 4.5, 2.6
    shots = []
    for k in range(N):
        t = k / (N - 1)
        a = 2 * math.pi * turns * t
        r = R * (1 - 0.18 * t)
        h = -1.5 + 3.0 * t
        shots.append((r * math.cos(a), r * math.sin(a), h, a))

    walk = [V((x, y, h)) for x, y, h, _ in shots]
    frames = []
    for x, y, h, a in shots:
        # the photograph: a small 3:2 rectangle just in front of the camera, facing the axis
        fx, fy = -math.cos(a), -math.sin(a)  # forward, toward the middle
        tilt = math.atan2(-h * 0.6, math.hypot(x, y))
        f = (fx * math.cos(tilt), fy * math.cos(tilt), math.sin(tilt))
        rx, ry = -fy, fx  # right
        up = (f[1] * ry * 0 - f[2] * ry, f[2] * rx - f[0] * 0, f[0] * ry - f[1] * rx)
        c = (x + 0.12 * f[0], y + 0.12 * f[1], h + 0.12 * f[2])
        w2, h2 = 0.12, 0.08
        quad = [(c[0] + sx * w2 * rx + sy * h2 * up[0], c[1] + sx * w2 * ry + sy * h2 * up[1], c[2] + sy * h2 * up[2])
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        q = [V(p) for p in quad]
        frames.append((sum(p[2] for p in q) / 4, q, (x, y, h), None))
    allp = [(u, v) for u, v, _ in walk] + [(u, v) for _, q, _, _ in frames for u, v, _ in q]
    to = fit(allp, BOX, pad=30)

    ds = [f[0] for f in frames]
    dmin, dmax = min(ds), max(ds)
    centre = to(V((0, 0, 0))[:2])

    # a few lines of sight, very faint, so the empty middle has a pull
    for k, (_, q, cam, _) in enumerate(frames):
        if k % 7 == 0:
            a = to(V(cam)[:2])
            target = to(V((0, 0, cam[2] * 0.4))[:2])
            svg.line(*a, *target, P.blue_20, 0.8)
    # the walk itself
    svg.polyline([to(p[:2]) for p in walk], P.teal_60, 1.2, stroke_dasharray="2 5")
    # the photographs, far ones first, each paper-white so nearer ones cover farther ones
    for d, q, _, _ in sorted(frames, key=lambda f: -f[0]):
        near = (dmax - d) / (dmax - dmin)
        svg.poly([to(p[:2]) for p in q], P.white, stroke=ramp([P.blue_20, P.lavender, P.blue], near),
                 stroke_width=f"{0.8 + 1.4 * near:.2f}", stroke_linejoin="round")
    svg.circle(*centre, 4, P.teal)

    furniture(svg, "circle.", f"{N} photographs · you never shoot the thing, you walk around it",
              P.blue, P.black_60, LIGHT_MARK)
    code_rule(svg)
    svg.code(M, CODE_Y, "for a in angles: shoot(look_at(subject, from_=a))", "py", 22)
    return svg


# ----------------------------------------------------------------------------
def become() -> Svg:
    """A seashell's points start as wild guesses and settle, step by step, onto the surface they belong to."""
    svg = Svg(P.blue)
    rng = random.Random(5)

    def shell(u, v, a=0.22, b=1.15, c=0.1, n=2.0):
        k = 1 - v / (2 * math.pi)
        x = a * k * (1 + math.cos(u)) * math.cos(n * v) + c * math.cos(n * v)
        y = a * k * (1 + math.cos(u)) * math.sin(n * v) + c * math.sin(n * v)
        z = b * v / (2 * math.pi) + a * k * math.sin(u)
        return x, y, z - 0.55

    truth = []
    while len(truth) < 3600:
        u, v = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
        if rng.random() < (1 - v / (2 * math.pi)) * 0.85 + 0.15:  # same density over a surface that narrows
            truth.append(shell(u, v))

    yaw, pitch, dist = 0.9, -0.22, 6.0
    V = lambda p: view(p, yaw, pitch, dist)  # noqa: E731
    steps = 14
    trails = []
    for p in truth:
        e = [rng.gauss(0, 0.32) for _ in range(3)]
        tr = []
        for k in range(steps + 1):
            s = 0.72 ** k  # each step keeps 72 % of the error
            sw = 0.9 * (1 - s)  # and the error turns as it shrinks, so the guesses swirl in
            ex = e[0] * math.cos(sw) - e[1] * math.sin(sw)
            ey = e[0] * math.sin(sw) + e[1] * math.cos(sw)
            tr.append(V((p[0] + s * ex, p[1] + s * ey, p[2] + s * e[2])))
        trails.append(tr)

    to = fit([tr[-1][:2] for tr in trails], BOX, pad=150)
    svg.clip_begin(0, BOX[1] - 30, svg.w, BOX[3] - BOX[1] + 60)
    for tr in trails[::2]:
        svg.add(f'<path d="{path_d([to(q[:2]) for q in tr])}" fill="none" stroke="{P.white}" '
                f'stroke-width="0.6" stroke-opacity="0.16" stroke-linecap="round"/>')
    for tr in trails[1::6]:  # where some of them started: loose dots far from the shell
        svg.circle(*to(tr[0][:2]), 1.4, P.lavender_60, opacity="0.5")
    ends = sorted((tr[-1] for tr in trails), key=lambda q: -q[2])
    dmin, dmax = min(q[2] for q in ends), max(q[2] for q in ends)
    for q in ends:
        near = (dmax - q[2]) / (dmax - dmin)
        svg.circle(*to(q[:2]), 1.2 + 1.5 * near, mix(P.lavender_60, P.cream, near), opacity=f"{0.5 + 0.5 * near:.2f}")
    svg.clip_end()

    furniture(svg, "become.", f"{len(truth)} guesses · each step a little less wrong",
              P.white, P.blue_20, (P.lavender, 0.45, P.white))
    code_rule(svg, P.cream)
    svg.code(M, CODE_Y, "points -= lr * grad(reprojection_error, points)", "py", 22, dark=True)
    return svg


# ----------------------------------------------------------------------------
def unseen() -> Svg:
    """Cameras only ever stood above the stone. Seen from below, its underside thins to nothing."""
    svg = Svg(P.black)
    at, normal = stone(29)
    cams = []
    for elev, n in [(34, 28), (54, 20), (74, 10)]:
        for k in range(n):
            a = 2 * math.pi * k / n
            e = math.radians(elev)
            cams.append((4.0 * math.cos(e) * math.cos(a), 4.0 * math.cos(e) * math.sin(a), 4.0 * math.sin(e)))

    rng = random.Random(4)
    yaw, pitch, dist = -0.5, -0.5, 7.5  # a low eye, looking up at the side no one photographed
    V = lambda p: view(p, yaw, pitch, dist)  # noqa: E731
    pts = []
    for d in fibonacci(9000):
        p, n = at(d), normal(d)
        k = sum(sees(c, p, n) for c in cams)
        if rng.random() < min(1.0, (k / 6) ** 1.5):  # fewer witnesses, fainter belief
            pts.append((V(p), k))
    kmax = max(k for _, k in pts)
    kmin = min(k for _, k in pts)
    to = fit([q[:2] for q, _ in pts], (BOX[0] + 60, BOX[1] + 40, BOX[2] - 60, BOX[3] - 10), pad=10)
    pts.sort(key=lambda t: -t[0][2])
    dmin, dmax = min(q[2] for q, _ in pts), max(q[2] for q, _ in pts)
    for q, k in pts:
        near = (dmax - q[2]) / (dmax - dmin)
        t = (k - kmin) / (kmax - kmin)
        svg.circle(*to(q[:2]), 1.0 + 1.3 * near, ramp([P.blue_60, P.lavender, P.lavender_60, P.cream], t),
                   opacity=f"{0.45 + 0.55 * near:.2f}")

    furniture(svg, "unseen.", "every photo was taken from above · what no one looked at was never there",
              P.white, P.blue_40, DARK_MARK)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "keep = random() < (seen_by(p) / 6) ** 1.5", "py", 22, dark=True)
    return svg


# ----------------------------------------------------------------------------
def land() -> Svg:
    """A hill flown over in strips. Each photo is a faint square; the contours appear only where
    enough photos overlap to agree on the height."""
    svg = Svg(P.cream)
    rng = random.Random(8)
    x0, y0, x1, y1 = BOX
    y1 += 30
    hills = [(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0.08, 0.22), rng.uniform(0.4, 1.0))
             for _ in range(9)]

    def height(u, v):
        return sum(a * math.exp(-((u - cx) ** 2 + (v - cy) ** 2) / (2 * s * s)) for cx, cy, s, a in hills) \
            + 0.06 * math.sin(9 * u + 3 * v)

    # flight: strips across a field turned 14°, a footprint every few metres, jittered by the wind
    ang = math.radians(14)
    ca, sa = math.cos(ang), math.sin(ang)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    fw, fh = 150, 108
    shots = []
    for i, along in enumerate(range(-5, 6)):
        row = list(range(-7, 8))
        if i % 2:
            row.reverse()
        for j in row:
            if (along, j) in {(5, 7), (5, 6), (-5, -7), (4, 7)}:  # a battery swap: a few missed
                continue
            lx, ly = j * 50 + rng.gauss(0, 4), along * 54 + rng.gauss(0, 4)
            shots.append((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, ang + rng.gauss(0, 0.04)))

    def corners(s):
        x, y, a = s
        c, si = math.cos(a), math.sin(a)
        return [(x + dx * c - dy * si, y + dx * si + dy * c) for dx, dy in ((-fw / 2, -fh / 2), (fw / 2, -fh / 2),
                                                                            (fw / 2, fh / 2), (-fw / 2, fh / 2))]

    def inside(s, px, py):
        x, y, a = s
        dx, dy = px - x, py - y
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        return abs(u) <= fw / 2 and abs(v) <= fh / 2

    svg.clip_begin(0, y0 - 20, svg.w, y1 - y0 + 40)
    for s in shots:
        svg.poly(corners(s), P.teal, fill_opacity="0.035")
    svg.polyline([s[:2] for s in shots], P.teal_60, 1, stroke_dasharray="1 5")

    # how many photos cover each cell of a grid over the page
    G = 6
    nx, ny = int((x1 - x0 + 120) / G), int((y1 - y0 + 60) / G)
    gx0, gy0 = x0 - 60, y0 - 30
    cover = [[0] * (nx + 1) for _ in range(ny + 1)]
    hgt = [[0.0] * (nx + 1) for _ in range(ny + 1)]
    for r in range(ny + 1):
        for c in range(nx + 1):
            px, py = gx0 + c * G, gy0 + r * G
            hgt[r][c] = height((px - gx0) / (nx * G), (py - gy0) / (ny * G))
    for s in shots:
        xs = [p[0] for p in corners(s)]
        ys = [p[1] for p in corners(s)]
        for r in range(max(0, int((min(ys) - gy0) / G)), min(ny, int((max(ys) - gy0) / G) + 1) + 1):
            for c in range(max(0, int((min(xs) - gx0) / G)), min(nx, int((max(xs) - gx0) / G) + 1) + 1):
                if inside(s, gx0 + c * G, gy0 + r * G):
                    cover[r][c] += 1

    # marching squares, one path per contour level and overlap band
    hs = [h for row in hgt for h in row]
    lo, hi = min(hs), max(hs)
    levels = [lo + (hi - lo) * (k + 0.5) / 22 for k in range(22)]
    bands = {2: (P.blue_40, 0.9), 3: (P.blue_80, 1.2), 4: (P.blue, 1.6)}
    for li, L in enumerate(levels):
        segs = {b: [] for b in bands}
        for r in range(ny):
            for c in range(nx):
                q = [(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)]
                vals = [hgt[y][x] for x, y in q]
                cross = []
                for e in range(4):
                    (ax, ay), (bx, by) = q[e], q[(e + 1) % 4]
                    va, vb = vals[e], vals[(e + 1) % 4]
                    if (va - L) * (vb - L) < 0:
                        t = (L - va) / (vb - va)
                        cross.append((gx0 + (ax + t * (bx - ax)) * G, gy0 + (ay + t * (by - ay)) * G))
                if len(cross) < 2:
                    continue
                k = min(cover[r][c], cover[r + 1][c + 1], cover[r][c + 1], cover[r + 1][c])
                if k < 2:
                    continue  # one photo alone can't tell height
                for i in range(0, len(cross) - 1, 2):
                    segs[min(k, 4)].append((cross[i], cross[i + 1]))
        for b, ss in segs.items():
            if not ss:
                continue
            col, wdt = bands[b]
            if li % 5 == 4:
                wdt *= 1.8  # every fifth line a little heavier, as on a map
            d = "".join(f"M{_fmt(a[0])},{_fmt(a[1])}L{_fmt(e[0])},{_fmt(e[1])}" for a, e in ss)
            svg.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{_fmt(wdt)}" stroke-linecap="round"/>')
    for s in shots:
        svg.circle(*s[:2], 1.6, P.teal)
    svg.clip_end()

    furniture(svg, "land.", f"{len(shots)} photos looking down · a hill, remembered where they overlap",
              P.blue, P.black_60, LIGHT_MARK)
    code_rule(svg, P.teal)
    svg.code(M, CODE_Y, "height[x, y] = median(depths(photos_over(x, y)))", "py", 22)
    return svg


POSTERS = [witness, circle, become, unseen, land]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, SERIES)
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
