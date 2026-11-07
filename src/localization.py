"""Localization posters: "where am I?", answered a different way on each one.

Ground:     particles. align. close. banana.
Aerial:     fuse. flow. rtk. spread.
Underwater: listen. beams. contour. bend.

Run:  uv run --no-project --with fonttools --with brotli python src/localization.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from posters import CODE_Y, M, W, code_rule, fit  # noqa: E402
from robots import bisect, mix  # noqa: E402
from sensors import arrow  # noqa: E402


def path(svg: Svg, segs, stroke, width=1.5, **kw) -> None:
    """Many separate segments [(a, b), ...] or polylines as one <path>."""
    d = []
    for s in segs:
        d.append("M" + " L".join(f"{_fmt(x)} {_fmt(y)}" for x, y in s))
    kw.setdefault("stroke_linecap", "round")
    kw.setdefault("stroke_linejoin", "round")
    attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    svg.add(f'<path d="{" ".join(d)}" fill="none" stroke="{stroke}" stroke-width="{_fmt(width)}"{attrs}/>')


def tag(svg: Svg, x, y, s, font, size, fill, anchor="start", bg=P.white, pad=5) -> None:
    """Text on a small backing rectangle, so lines behind it don't run through the letters."""
    w = 0.6 * size * len(s) if font.startswith("code") else 0.5 * size * len(s)
    x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
    svg.rect(x0 - pad, y - size * 0.8 - pad / 2, w + 2 * pad, size + pad, bg, rx=4)
    svg.text(x, y, s, font, size, fill, anchor)


def ellipse(mu, cov, k=2.0, n=96):
    """Points on the k-sigma ellipse of a 2x2 covariance."""
    a, b, c = cov[0][0], cov[0][1], cov[1][1]
    tr, det = a + c, a * c - b * b
    l1 = tr / 2 + math.sqrt(max(tr * tr / 4 - det, 0))
    l2 = tr / 2 - math.sqrt(max(tr * tr / 4 - det, 0))
    ang = 0.5 * math.atan2(2 * b, a - c)
    out = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        x, y = k * math.sqrt(l1) * math.cos(t), k * math.sqrt(max(l2, 0)) * math.sin(t)
        out.append((mu[0] + x * math.cos(ang) - y * math.sin(ang), mu[1] + x * math.sin(ang) + y * math.cos(ang)))
    return out


def mean_cov(ps):
    n = len(ps)
    mx, my = sum(p[0] for p in ps) / n, sum(p[1] for p in ps) / n
    sxx = sum((p[0] - mx) ** 2 for p in ps) / n
    syy = sum((p[1] - my) ** 2 for p in ps) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in ps) / n
    return (mx, my), [[sxx, sxy], [sxy, syy]]


# ============================================================================
# ground
# ============================================================================
def particles() -> Svg:
    """Monte Carlo localization in a corridor with three doors: a uniform cloud, three guesses, then one."""
    svg = Svg(P.white)
    rng = random.Random(7)
    L, doors, N = 10.0, [1.2, 3.4, 7.6], 420

    def p_door(x):
        if x < 0 or x > L:
            return 0.0
        d = min(abs(x - c) for c in doors)
        return 0.06 + math.exp(-0.5 * (d / 0.22) ** 2)

    def p_wall(x):
        return 0.0 if x < 0 or x > L else 1.06 - p_door(x) + 0.06

    def sense(xs, f):
        w = [f(x) for x in xs]
        return rng.choices(xs, weights=w, k=len(xs))

    def move(xs, u):
        return [x + u + rng.gauss(0, 0.06 * abs(u) + 0.04) for x in xs]

    xs = [rng.uniform(0, L) for _ in range(N)]
    truth = 1.2
    rows = [("start · it could be anywhere", list(xs), truth)]
    xs = sense(xs, p_door)
    rows.append(("sense: a door", list(xs), truth))
    xs, truth = move(xs, 2.2), truth + 2.2
    rows.append(("move 2.2 m", list(xs), truth))
    xs = sense(xs, p_door)
    rows.append(("sense: a door, again", list(xs), truth))
    xs, truth = move(xs, 2.1), truth + 2.1
    xs = sense(xs, p_wall)
    rows.append(("move 2.1 m · sense: wall", list(xs), truth))

    x0, x1 = M, W - M

    def gx(x):
        return x0 + (x1 - x0) * x / L

    y, step = 300, 140
    for k, (label, ps, tr) in enumerate(rows):
        yb = y + 78  # corridor floor line
        svg.text(x0, y, f"{k}", "code", 16, P.blue)
        svg.text(x0 + 24, y, label, "diag", 19, P.black)
        for c in doors:
            svg.rect(gx(c - 0.35), yb - 8, gx(c + 0.35) - gx(c - 0.35), 16, P.lavender_20)
        svg.line(x0, yb, x1, yb, P.black_20, 2)
        # density: a smoothed histogram above the floor
        bins = 200
        h = [0.0] * bins
        for p in ps:
            if 0 <= p <= L:
                for j in range(bins):
                    xc = L * (j + 0.5) / bins
                    h[j] += math.exp(-0.5 * ((xc - p) / 0.12) ** 2)
        hmax = max(h) if k else max(h) * 4
        curve = [(gx(L * (j + 0.5) / bins), yb - 12 - 50 * v / hmax) for j, v in enumerate(h)]
        svg.poly([(gx(0), yb - 12)] + curve + [(gx(L), yb - 12)], P.blue_20)
        svg.polyline(curve, P.blue, 2.5)
        for p in ps:
            if 0 <= p <= L:
                svg.circle(gx(p), yb + 12 + rng.uniform(0, 14), 2.2, P.blue_80, opacity="0.55")
        svg.triangle(gx(tr), yb + 42, 15, P.teal, -math.pi / 2)
        y += step
    svg.triangle(x1 - 56, 295, 14, P.teal, -math.pi / 2)
    svg.text(x1, 300, "robot", "codel", 14, P.teal, "end")
    svg.rect(x1 - 158, 288, 22, 14, P.lavender_20)
    svg.text(x1 - 130, 300, "door", "codel", 14, P.black_60)

    svg.frame("particles.", f"monte carlo localization · {N} guesses · one corridor")
    code_rule(svg)
    svg.code(M, CODE_Y, """
w  = p_sense(z, world_map, x)          # how well each guess explains z
x  = x[choice(N, N, p=w / w.sum())]    # resample: more copies of good ones
x += u + randn(N) * sigma_u            # move every guess, with noise""", "py", 20)
    return svg


def _room():
    outline = [(0, 0), (5, 0), (5, 1.5), (6.5, 1.5), (6.5, 4), (2, 4), (2, 3), (0, 3), (0, 0)]
    return outline


def _sample(poly, step, phase, rng, noise):
    pts = []
    for a, b in zip(poly, poly[1:]):
        n = math.dist(a, b)
        s = phase
        while s < n:
            t = s / n
            pts.append((a[0] + (b[0] - a[0]) * t + rng.gauss(0, noise), a[1] + (b[1] - a[1]) * t + rng.gauss(0, noise)))
            s += step
    for k in range(int(2 * math.pi * 0.45 / step)):  # a pillar
        t = 2 * math.pi * k / int(2 * math.pi * 0.45 / step) + phase
        pts.append((3.6 + 0.45 * math.cos(t), 2.0 + 0.45 * math.sin(t)))
    return pts


def align() -> Svg:
    """ICP: two laser scans of one room, paired point to nearest point and re-fit until they sit on each other."""
    svg = Svg(P.black)
    rng = random.Random(4)
    ref = _sample(_room(), 0.16, 0.0, rng, 0.015)
    src0 = _sample(_room(), 0.16, 0.08, rng, 0.015)
    th, tx, ty = math.radians(-24), 1.3, 0.9
    cx, cy = 3.2, 2.0
    src0 = [(cx + (x - cx) * math.cos(th) - (y - cy) * math.sin(th) + tx,
             cy + (x - cx) * math.sin(th) + (y - cy) * math.cos(th) + ty) for x, y in src0]

    def nearest(p):
        return min(ref, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2)

    def fit_rigid(a, b):
        ax, ay = sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a)
        bx, by = sum(p[0] for p in b) / len(b), sum(p[1] for p in b) / len(b)
        s = c = 0.0
        for (x1, y1), (x2, y2) in zip(a, b):
            x1, y1, x2, y2 = x1 - ax, y1 - ay, x2 - bx, y2 - by
            s += x1 * y2 - y1 * x2
            c += x1 * x2 + y1 * y2
        r = math.atan2(s, c)
        return r, bx - (ax * math.cos(r) - ay * math.sin(r)), by - (ax * math.sin(r) + ay * math.cos(r))

    iters, errs, src = [src0], [], src0
    pairs0 = None
    for it in range(30):
        tgt = [nearest(p) for p in src]
        if pairs0 is None:
            pairs0 = tgt
        errs.append(math.sqrt(sum(math.dist(p, q) ** 2 for p, q in zip(src, tgt)) / len(src)))
        r, ox, oy = fit_rigid(src, tgt)
        src = [(x * math.cos(r) - y * math.sin(r) + ox, x * math.sin(r) + y * math.cos(r) + oy) for x, y in src]
        iters.append(src)

    fm = fit(ref + src0, (M, 290, W - M, 790), pad=10)
    for p, q in zip(src0, pairs0):
        svg.line(*fm(p), *fm(q), P.black_80, 1)
    for k, it in enumerate([1, 2, 3, 5, 8]):
        col = mix(P.black_80, P.lavender, 0.25 + 0.12 * k)
        for p in iters[it]:
            svg.circle(*fm(p), 1.8, col)
    for p in src0:
        svg.circle(*fm(p), 3, "none", stroke=P.lavender, stroke_width=1.5)
    for p in ref:
        svg.circle(*fm(p), 4.5, P.teal_60)
    for p in iters[-1]:
        svg.circle(*fm(p), 2.2, P.lavender)
    a = fm(src0[0])
    svg.text(a[0] + 4, a[1] + 34, "new scan", "codel", 15, P.lavender)
    b = fm((0, 3))
    svg.text(b[0] - 4, b[1] - 18, "map scan", "codel", 15, P.teal_60)

    # rms against iteration
    x0, x1, yb, yt = M + 60, W - M, 980, 850
    n = 15
    emax = errs[0]
    for i in range(n):
        xx = x0 + (x1 - x0) * (i + 0.5) / n
        hh = (yb - yt) * errs[i] / emax
        svg.rect(xx - 14, yb - hh, 28, hh, P.lavender if i else P.blue_60)
    svg.line(x0, yb, x1, yb, P.blue_40, 1.5)
    svg.text(x0 - 14, yb - 4, "rms", "codel", 14, P.blue_40, "end")
    svg.text(x0 + (x1 - x0) * 0.5 / n, yt - 12, f"{errs[0]:.2f} m", "code", 15, P.white, "middle")
    svg.text(x0 + (x1 - x0) * (n - 0.5) / n, yb - 18, f"{errs[n - 1] * 100:.0f} mm", "code", 15, P.white, "middle")
    svg.text(x1, yb + 28, f"iterations 1…{n}", "codel", 14, P.blue_40, "end")

    svg.frame("align.", "scan matching · iterative closest point · 2D lidar", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
for it in range(30):
    j = nearest(ref, src)            # pair each point with its closest
    R, t = rigid_fit(src, ref[j])    # best rotation + shift for those pairs
    src = src @ R.T + t              # move, re-pair, repeat""", "py", 20, dark=True)
    return svg


def close() -> Svg:
    """Loop closure: odometry around a square doesn't come back to the start; one 'seen this before' fixes all of it."""
    svg = Svg(P.cream)
    rng = random.Random(11)
    side, ds, nturn = 12.0, 0.5, 6
    steps = []  # (ds, dtheta) truth
    for _ in range(4):
        steps += [(ds, 0.0)] * int(side / ds - nturn)
        steps += [(ds * 0.6, math.pi / 2 / nturn)] * nturn
    N = len(steps)

    def integrate(st, th0=0.0):
        x, y, th = 0.0, 0.0, th0
        out = [(x, y)]
        for d, dt in st:
            th += dt / 2
            x, y = x + d * math.cos(th), y + d * math.sin(th)
            th += dt / 2
            out.append((x, y))
        return out

    truth = integrate(steps)
    odo = [(d * 1.02 + rng.gauss(0, 0.01), dt + 0.0055 + rng.gauss(0, 0.004)) for d, dt in steps]
    raw = integrate(odo)
    turn_err = 2 * math.pi - sum(dt for _, dt in odo)
    fixed_steps = [(d, dt + turn_err / N) for d, dt in odo]
    fx = integrate(fixed_steps)
    gx_, gy_ = fx[-1][0] - fx[0][0], fx[-1][1] - fx[0][1]
    fixed = [(x - gx_ * i / N, y - gy_ * i / N) for i, (x, y) in enumerate(fx)]

    fm = fit(truth + raw + fixed, (M, 290, W - M, 990), pad=24)
    svg.polyline([fm(p) for p in truth], P.black_60, 2, stroke_dasharray="2 8")
    for i in range(0, N + 1, 4):
        svg.line(*fm(raw[i]), *fm(fixed[i]), P.black_20, 1.2)
    svg.polyline([fm(p) for p in raw], P.lavender, 3)
    for i in range(0, N + 1, 4):
        svg.circle(*fm(raw[i]), 4, P.cream, stroke=P.lavender, stroke_width=2)
    svg.polyline([fm(p) for p in fixed], P.blue, 4)
    for i in range(0, N + 1, 4):
        svg.circle(*fm(fixed[i]), 5.5, P.blue)
    a, b = fm(raw[-1]), fm(raw[0])
    svg.line(*a, *b, P.teal, 3.5, stroke_dasharray="8 7")
    svg.circle(*a, 9, "none", stroke=P.teal, stroke_width=3)
    gap = math.dist(raw[-1], raw[0])
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    svg.text(a[0] + 22, a[1] + 8, "loop closure", "code", 18, P.teal)
    svg.text(a[0] + 22, a[1] + 32, f"“I've been here” · gap {gap:.1f} m", "codel", 15, P.black_80)
    s = fm((0, 0))
    svg.text(s[0] - 14, s[1] + 34, "start", "codel", 15, P.black_80, "end")
    ctr = fm((side / 2, side / 2))
    svg.text(ctr[0], ctr[1] - 30, "odometry", "code", 18, P.lavender, "middle")
    svg.text(ctr[0], ctr[1], "after the graph is solved", "code", 18, P.blue, "middle")
    svg.text(ctr[0], ctr[1] + 30, "truth", "codel", 16, P.black_60, "middle")
    _ = mid

    svg.frame("close.", f"pose graph · {N} odometry edges + 1 loop edge")
    code_rule(svg)
    svg.code(M, CODE_Y, """
# odometry edges i → i+1, plus one loop edge: last pose == first pose
dth += (2*pi - sum(dth)) / N               # spread the heading error
p    = integrate(ds, cumsum(dth))          # re-integrate the path
p   -= outer(arange(N+1) / N, p[-1] - p[0])   # then spread the gap""", "py", 20)
    return svg


def banana() -> Svg:
    """Wheel odometry with an unsure heading: the cloud bends into an arc, and its Gaussian mean sits off the arc."""
    svg = Svg(P.black)
    rng = random.Random(5)
    N, s_th0, s_step, s_d = 360, math.radians(24), math.radians(0.6), 0.015
    dists = [1, 2, 3, 4, 5]
    clouds = {d: [] for d in dists}
    for _ in range(N):
        x = y = 0.0
        th = rng.gauss(0, s_th0)
        d = 0.0
        for k in range(50):
            step = 0.1 * (1 + rng.gauss(0, s_d * 3))
            th += rng.gauss(0, s_step)
            x, y = x + step * math.cos(th), y + step * math.sin(th)
            d += 0.1
            if (k + 1) % 10 == 0:
                clouds[round(d)].append((x, y))

    fm = fit([(-0.5, -3.9), (5.4, 3.9)], (M, 310, W - M, 930), pad=0)
    o = fm((0, 0))
    for r in dists:
        svg.arc(o[0], o[1], r * (fm((1, 0))[0] - o[0]), math.radians(-62), math.radians(62), P.black_80, 1.5,
                stroke_dasharray="2 7")
    for k, d in enumerate(dists):
        col = mix(P.blue_60, P.lavender, k / 4)
        for p in clouds[d]:
            svg.circle(*fm(p), 2.4, col, opacity="0.8")
        lab = fm((d * math.cos(math.radians(66)), d * math.sin(math.radians(66))))
        svg.text(lab[0], lab[1], f"{d} m", "codel", 15, P.blue_40, "middle")
    mu, cov = mean_cov(clouds[5])
    svg.polyline([fm(p) for p in ellipse(mu, cov, 2)], P.teal_60, 3)
    m = fm(mu)
    svg.line(m[0] - 10, m[1] - 10, m[0] + 10, m[1] + 10, P.white, 3)
    svg.line(m[0] - 10, m[1] + 10, m[0] + 10, m[1] - 10, P.white, 3)
    tag(svg, m[0] - 22, m[1] + 6, "mean", "code", 17, P.white, "end", bg=P.black)
    e_top = fm((mu[0], mu[1] + 2 * math.sqrt(cov[1][1])))
    svg.text(e_top[0], e_top[1] - 16, "the gaussian's 2σ", "codel", 15, P.teal_60, "middle")
    svg.triangle(o[0], o[1], 34, P.white, 0)
    svg.text(o[0] - 4, o[1] + 46, f"start · heading ±{math.degrees(s_th0):.0f}°", "codel", 15, P.blue_40)
    svg.text(W - M, 985, "the robot is on the arc; the mean is not", "codel", 16, P.white, "end")

    svg.frame("banana.", "wheel odometry · heading uncertainty bends the cloud", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
th = th0 + randn(N) * sigma_th           # not sure which way it faces
x, y = d * cos(th), d * sin(th)          # drive d metres: an arc, not a blob
mu, S = mean(x, y), cov(x, y)            # an EKF keeps only these two:
                                         # its mean is where the robot isn't""", "py", 20, dark=True)
    return svg


# ============================================================================
# aerial
# ============================================================================
def fuse() -> Svg:
    """GPS + IMU Kalman filter: predict with the IMU at 100 Hz, correct with GPS at 1 Hz. The error, over time."""
    svg = Svg(P.black)
    rng = random.Random(2)
    dt, T, bias, s_acc, s_gps = 0.01, 12.0, 0.18, 0.25, 1.4
    q = 0.32  # accel noise the filter assumes (covers the bias it doesn't model)
    n = int(T / dt)
    p = v = 0.0  # truth
    xi = [0.0, 0.0]  # imu-only
    xk = [0.0, 0.0]  # filter
    Pk = [[1.0, 0.0], [0.0, 0.2]]
    ts, e_imu, e_kf, sd, gps = [], [], [], [], []
    for i in range(1, n + 1):
        t = i * dt
        a = 1.2 * math.sin(0.7 * t) + 0.6 * math.cos(1.9 * t)
        p, v = p + v * dt + 0.5 * a * dt * dt, v + a * dt
        am = a + bias + rng.gauss(0, s_acc)
        for x in (xi, xk):
            x[0], x[1] = x[0] + x[1] * dt + 0.5 * am * dt * dt, x[1] + am * dt
        F = [[1, dt], [0, 1]]
        FP = [[F[0][0] * Pk[0][0] + F[0][1] * Pk[1][0], F[0][0] * Pk[0][1] + F[0][1] * Pk[1][1]],
              [Pk[1][0], Pk[1][1]]]
        Pk = [[FP[0][0] + FP[0][1] * dt, FP[0][1]], [FP[1][0] + FP[1][1] * dt, FP[1][1]]]
        Pk[0][0] += q * q * dt**3 / 3
        Pk[0][1] += q * q * dt**2 / 2
        Pk[1][0] += q * q * dt**2 / 2
        Pk[1][1] += q * q * dt
        if i % 100 == 0:  # GPS
            z = p + rng.gauss(0, s_gps)
            gps.append((t, z - p))
            S = Pk[0][0] + s_gps**2
            K = [Pk[0][0] / S, Pk[1][0] / S]
            r = z - xk[0]
            xk = [xk[0] + K[0] * r, xk[1] + K[1] * r]
            Pk = [[(1 - K[0]) * Pk[0][0], (1 - K[0]) * Pk[0][1]],
                  [Pk[1][0] - K[1] * Pk[0][0], Pk[1][1] - K[1] * Pk[0][1]]]
        ts.append(t)
        e_imu.append(xi[0] - p)
        e_kf.append(xk[0] - p)
        sd.append(math.sqrt(Pk[0][0]))

    x0, x1, yc, ys, lim = M + 60, W - M, 630, 52, 6.0

    def gx(t):
        return x0 + (x1 - x0) * t / T

    def gy(e):
        return yc - ys * e

    svg.clip_begin(x0, gy(lim), x1 - x0, 2 * lim * ys)
    for e in range(-6, 7, 2):
        svg.line(x0, gy(e), x1, gy(e), P.black_80, 1)
    up = [(gx(t), gy(e + 2 * s)) for t, e, s in zip(ts, e_kf, sd)]
    dn = [(gx(t), gy(e - 2 * s)) for t, e, s in zip(ts, e_kf, sd)]
    svg.poly([(gx(0), gy(2))] + up + dn[::-1] + [(gx(0), gy(-2))], P.blue, opacity="0.3")
    svg.polyline(up, P.blue_60, 1.5)
    svg.polyline(dn, P.blue_60, 1.5)
    svg.polyline([(gx(t), gy(e)) for t, e in zip(ts, e_imu)], P.teal_60, 3.5)
    svg.polyline([(gx(0), gy(0))] + [(gx(t), gy(e)) for t, e in zip(ts, e_kf)], P.white, 3)
    for t, e in gps:
        svg.circle(gx(t), gy(e), 7, P.black, stroke=P.white, stroke_width=2.5)
    svg.clip_end()
    for e in range(-6, 7, 2):
        svg.text(x0 - 14, gy(e) + 5, f"{e:+d}" if e else "0", "codel", 14, P.blue_40, "end")
    svg.text(x0 - 14, gy(lim) - 18, "error, m", "codel", 14, P.blue_40)
    for t in range(0, 13, 2):
        svg.text(gx(t), gy(-lim) + 32, f"{t} s", "codel", 14, P.blue_40, "middle")
    i_exit = next(i for i, e in enumerate(e_imu) if e > lim - 0.3)
    svg.text(gx(ts[i_exit]) + 14, gy(lim) + 34, "imu alone", "code", 17, P.teal_60)
    svg.text(gx(ts[i_exit]) + 14, gy(lim) + 58, "½·bias·t²", "codel", 15, P.teal_60)
    svg.text(gx(9.5), gy(-4.4), "filter · ±2σ band", "code", 17, P.lavender, "middle")
    svg.text(gx(1.0) + 16, gy(gps[0][1]) + 6, "gps", "code", 17, P.white)

    svg.frame("fuse.", "drone · kalman filter · imu 100 Hz + gps 1 Hz", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
x = F @ x + B * a_imu;  P = F @ P @ F.T + Q      # every 10 ms: σ grows
if gps:                                          # every second:
    K  = P @ H.T / (H @ P @ H.T + R)             #   how much to trust it
    x += K @ (z - H @ x);  P = (I - K @ H) @ P   #   σ snaps back""", "py", 18, dark=True)
    return svg


def flow() -> Svg:
    """Optical flow: a down-facing camera measures v / h. Same picture at 2 m and 6 m, so it needs the height."""
    svg = Svg(P.cream)
    rng = random.Random(9)
    omega, dt = 0.5, 0.6

    # the camera's view: identical for both drones
    ix, iy, isz = W / 2 - 150, 300, 300
    svg.rect(ix, iy, isz, isz, P.white, rx=10, stroke=P.black, stroke_width=2)
    svg.clip_begin(ix, iy, isz, isz)
    shift = 88
    for _ in range(46):
        px, py = rng.uniform(ix + 10, ix + isz + shift), rng.uniform(iy + 10, iy + isz - 10)
        svg.circle(px, py, rng.uniform(3, 7), P.black_20)
    svg.clip_end()
    for gx_ in range(3):
        for gy_ in range(3):
            cx, cy = ix + 60 + gx_ * 90, iy + 60 + gy_ * 90
            arrow(svg, (cx + 28, cy), (cx - 28, cy), P.blue, 3.5, 16)
    svg.text(ix + isz + 20, iy + 24, "what both cameras see", "codel", 15, P.black_60)
    svg.text(ix + isz + 20, iy + 52, f"{omega} rad/s", "code", 20, P.blue)
    svg.text(ix - 20, iy + isz - 30, "flying →", "codel", 15, P.black_60, "end")
    svg.text(ix - 20, iy + isz - 8, "ground slides ←", "codel", 15, P.black_60, "end")

    # side view: v = omega * h
    yg, k = 975, 52  # ground line, px per metre
    svg.line(M, yg, W - M, yg, P.black, 2.5)
    for _ in range(70):
        svg.rect(rng.uniform(M, W - M - 6), yg + 6, rng.uniform(3, 12), 4, P.black_20)
    for h, cx, col in [(2.0, 290, P.teal), (6.0, 640, P.blue)]:
        v = omega * h
        y = yg - k * h
        dx = k * v * dt
        gpt = (cx + dx / 2 + 6, yg)
        for xx, ghost in [(cx, True), (cx + dx, False)]:
            svg.line(xx, y + 14, gpt[0], gpt[1], col, 1.6, stroke_dasharray="4 6" if ghost else "1 0",
                     opacity="0.6" if ghost else "1")
        half = math.radians(20)
        svg.poly([(cx + dx, y + 14), (cx + dx - k * h * math.tan(half), yg), (cx + dx + k * h * math.tan(half), yg)],
                 col, opacity="0.08")
        for xx, op in [(cx, "0.35"), (cx + dx, "1")]:
            svg.rect(xx - 34, y - 6, 68, 12, col, rx=6, opacity=op)
            svg.rect(xx - 7, y + 6, 14, 10, P.black, opacity=op)
        a0 = math.atan2(gpt[0] - cx, yg - y - 14)
        a1 = math.atan2(gpt[0] - cx - dx, yg - y - 14)
        ra = min(120, 0.55 * (yg - y))
        svg.arc(gpt[0], gpt[1], ra, -math.pi / 2 - a0, -math.pi / 2 - a1, col, 4, stroke_linecap="round")
        lx = gpt[0] + (cx + dx - gpt[0]) * ra / (yg - y - 14) + 14
        svg.text(lx, gpt[1] - ra + 12, f"{omega * dt:.1f} rad", "code", 15, col)
        arrow(svg, (cx + dx + 46, y), (cx + dx + 46 + 70, y), col, 3.5, 16)
        svg.text(cx + dx + 46, y - 18, f"v = {v:.0f} m/s", "code", 18, col)
        svg.text(cx - 46, y + 6, f"h = {h:.0f} m", "codel", 15, P.black_80, "end")
    svg.text(W - M, yg - 22, f"Δt = {dt} s", "codel", 15, P.black_60, "end")

    svg.frame("flow.", "drone · optical flow + rangefinder · v = ω h")
    code_rule(svg)
    svg.code(M, CODE_Y, """
flow  = (dx_px / dt) / f_px        # pixels per second → rad/s
flow -= gyro_rate                  # minus what's just the drone rotating
v     = flow * h_range             # the same flow is 1 m/s at 2 m, 3 at 6""", "py", 20)
    return svg


def rtk() -> Svg:
    """RTK: carrier phase is a ruler with 19 cm ticks and no numbers. Three satellites agree on one crossing."""
    svg = Svg(P.white)
    rng = random.Random(3)
    lam = 0.1903
    angs = [math.radians(a) for a in (78, 146, 17)]
    us = [(math.cos(a), math.sin(a)) for a in angs]
    true = (0.31, -0.42)
    phis = [((u[0] * true[0] + u[1] * true[1]) / lam + rng.gauss(0, 0.012)) % 1 for u in us]
    R = 1.0

    box = (M, 280, W - M, 990)
    fm = fit([(-1.15, -1.15), (1.15, 1.15)], box, pad=0)
    s = fm((1, 0))[0] - fm((0, 0))[0]
    cols = [P.blue_40, P.teal_60, P.lavender_60]
    c0 = fm((0, 0))
    svg.clip_begin(c0[0] - 1.15 * s, c0[1] - 1.15 * s, 2.3 * s, 2.3 * s)
    for u, ph, col in zip(us, phis, cols):
        segs = []
        for n in range(-12, 13):
            d = (n + ph) * lam
            base = (u[0] * d, u[1] * d)
            a = (base[0] - u[1] * 2, base[1] + u[0] * 2)
            b = (base[0] + u[1] * 2, base[1] - u[0] * 2)
            segs.append([fm(a), fm(b)])
        path(svg, segs, col, 1.6)
    svg.clip_end()
    svg.circle(*c0, R * s, "none", stroke=P.black, stroke_width=2, stroke_dasharray="3 7")

    cands = []
    u1, u2, u3 = us
    det = u1[0] * u2[1] - u1[1] * u2[0]
    for n1 in range(-12, 13):
        for n2 in range(-12, 13):
            d1, d2 = (n1 + phis[0]) * lam, (n2 + phis[1]) * lam
            x = (d1 * u2[1] - d2 * u1[1]) / det
            y = (u1[0] * d2 - u2[0] * d1) / det
            if math.hypot(x, y) < R:
                r3 = (((u3[0] * x + u3[1] * y) / lam - phis[2] + 0.5) % 1 - 0.5) * lam
                cands.append(((x, y), abs(r3)))
    best = min(cands, key=lambda c: c[1])
    for (x, y), r in cands:
        good = 1 - min(r / (lam / 2), 1)
        svg.circle(*fm((x, y)), 2.5 + 6 * good**3, mix(P.black_20, P.blue, good**2))
    b = fm(best[0])
    svg.circle(*b, 22, "none", stroke=P.blue, stroke_width=4)
    tag(svg, b[0] + 34, b[1] - 8, "fix", "code", 22, P.blue)
    tag(svg, b[0] + 34, b[1] + 20, f"{math.dist(best[0], true) * 1000:.0f} mm from truth", "codel", 15, P.black_80)
    tag(svg, c0[0] + R * s * 0.72, c0[1] + R * s * 0.72 + 30, "code fix ±1 m", "codel", 15, P.black_60)
    tag(svg, c0[0] - 1.15 * s + 4, c0[1] - 1.15 * s + 22, f"{len(cands)} places where sat 1 and sat 2 agree",
        "codel", 15, P.black_60)
    tag(svg, c0[0] - 1.15 * s + 4, c0[1] - 1.15 * s + 46, "the bigger the dot, the better sat 3 agrees",
        "codel", 15, P.black_60)
    for u, col, name in zip(us, [P.blue, P.teal, P.lavender], ["sat 1", "sat 2", "sat 3"]):
        e = fm((u[0] * 1.08, u[1] * 1.08))
        st = fm((u[0] * 0.88, u[1] * 0.88))
        arrow(svg, st, e, col, 3, 14)
        tag(svg, e[0] + 10 * u[0], e[1] - 10 * u[1] - 8, name, "code", 16, col, "middle")

    svg.frame("rtk.", f"drone · carrier phase · λ = {lam * 100:.0f} cm · integer ambiguity")
    code_rule(svg)
    svg.code(M, CODE_Y, """
r = (N + phi) * lam                 # phase gives the fraction; N is unknown
cands = crossings(sat1, sat2)       # every integer pair inside the code fix
fix = min(cands, key=lambda c: resid(sat3, c))   # one fits all three
# get N right and the error drops from a metre to a centimetre""", "py", 19)
    return svg


def spread() -> Svg:
    """Dilution of precision: same ranging error, three skies. Close-together satellites smear the fix."""
    svg = Svg(P.cream)
    sigma = 20  # px: the same range error everywhere
    rows = [("spread out", 90), ("closer", 40), ("bunched", 12)]
    y0, rh = 300, 230
    for k, (name, sep) in enumerate(rows):
        yc = y0 + k * rh + 100
        # sky: a half dome with two satellites
        sx, sr = M + 110, 96
        svg.arc(sx, yc + 40, sr, math.pi, 2 * math.pi, P.black_20, 2)
        svg.line(sx - sr - 12, yc + 40, sx + sr + 12, yc + 40, P.black, 2)
        els = [90 - sep / 2, 90 + sep / 2]
        us = []
        for e in els:
            a = math.radians(e)
            p = (sx + sr * math.cos(a), yc + 40 - sr * math.sin(a))
            svg.line(sx, yc + 40, *p, P.black_60, 1.5, stroke_dasharray="2 6")
            svg.circle(*p, 9, P.blue)
            us.append((math.cos(a), -math.sin(a)))
        svg.rect(sx - 8, yc + 32, 16, 16, P.black)
        svg.text(sx, yc + 82, f"{name} · {sep}° apart", "codel", 15, P.black_80, "middle")

        # where the two range bands overlap
        cx = (M + 270 + W - M) / 2
        svg.clip_begin(M + 260, yc - rh / 2 + 6, W - 2 * M - 260, rh - 12)
        for u, col in zip(us, [P.teal_60, P.lavender_60]):
            for off in (-sigma, sigma):
                a = (cx + u[0] * off - u[1] * 600, yc + u[1] * off + u[0] * 600)
                b = (cx + u[0] * off + u[1] * 600, yc + u[1] * off - u[0] * 600)
                svg.line(*a, *b, col, 2)
            band = [(cx + u[0] * o - u[1] * t, yc + u[1] * o + u[0] * t) for o, t in
                    [(-sigma, -600), (sigma, -600), (sigma, 600), (-sigma, 600)]]
            svg.poly(band, col, opacity="0.18")
        u1, u2 = us
        det = u1[0] * u2[1] - u1[1] * u2[0]
        corners = []
        for d1, d2 in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            d1, d2 = d1 * sigma, d2 * sigma
            corners.append((cx + (d1 * u2[1] - d2 * u1[1]) / det, yc + (u1[0] * d2 - u2[0] * d1) / det))
        svg.poly(corners, P.blue)
        svg.clip_end()
        # 2D DOP with a known clock: sqrt(trace((H^T H)^-1))
        a, b_, c = sum(u[0] ** 2 for u in us), sum(u[0] * u[1] for u in us), sum(u[1] ** 2 for u in us)
        dop = math.sqrt((a + c) / (a * c - b_ * b_))
        svg.text(W - M, yc - rh / 2 + 34, f"DOP {dop:.1f}", "code", 22, P.black, "end")
        if k < 2:
            svg.line(M, yc + rh / 2 + 2, W - M, yc + rh / 2 + 2, P.black_20, 1)
    svg.text(W - M, y0 + 3 * rh + 4, "bands: ±σ in range to each satellite", "codel", 15, P.black_60, "end")

    svg.frame("spread.", "drone · gnss geometry · dilution of precision")
    code_rule(svg)
    svg.code(M, CODE_Y, """
H   = [unit(sat - rx) for sat in sats]    # direction to each satellite
Q   = inv(H.T @ H)                         # range error → position error
dop = sqrt(trace(Q))                       # same σ, very different fixes""", "py", 20)
    return svg


# ============================================================================
# underwater
# ============================================================================
def listen() -> Svg:
    """Passive acoustic positioning: one ping, three hydrophones. Each arrival-time difference is a hyperbola."""
    svg = Svg(P.cream)
    A, B, C, src = (500, 650), (2650, 1000), (1250, 2650), (1700, 1550)
    fm = fit([(0, 200), (3100, 3000)], (M, 290, W - M, 1000), pad=0)
    sc = fm((1, 0))[0] - fm((0, 0))[0]
    box = (M, 290, W - 2 * M, 710)

    def hyper(F1, F2, dd):
        """|p - F2| - |p - F1| = dd."""
        cx, cy = (F1[0] + F2[0]) / 2, (F1[1] + F2[1]) / 2
        c = math.dist(F1, F2) / 2
        ex, ey = (F2[0] - F1[0]) / (2 * c), (F2[1] - F1[1]) / (2 * c)
        a = dd / 2
        b = math.sqrt(max(c * c - a * a, 1e-6))
        out = []
        for i in range(-200, 201):
            t = 4.0 * i / 200
            X, Y = -a * math.cosh(t), b * math.sinh(t)
            out.append(fm((cx + ex * X - ey * Y, cy + ey * X + ex * Y)))
        return out

    def ddiff(F1, F2, p=src):
        return math.dist(p, F2) - math.dist(p, F1)

    svg.clip_begin(*box)
    for r in range(150, 4000, 220):
        svg.circle(*fm(src), r * sc, "none", stroke=P.black_20, stroke_width=1.2)
    for F2, col in [(B, P.blue_40), (C, P.teal_60)]:
        c2 = math.dist(A, F2)
        segs = [hyper(A, F2, k) for k in [c2 * j / 8 for j in range(-7, 8)]]
        path(svg, segs, col, 1.3)
    for F2, col in [(B, P.blue), (C, P.teal)]:
        svg.polyline(hyper(A, F2, ddiff(A, F2)), col, 4)
    svg.clip_end()

    for name, h, dx, dy in [("A", A, -18, 30), ("B", B, 18, 30), ("C", C, 18, -16)]:
        p = fm(h)
        svg.triangle(p[0], p[1], 26, P.black, -math.pi / 2)
        svg.text(p[0] + dx, p[1] + dy, name, "code", 20, P.black, "end" if dx < 0 else "start")
        t = math.dist(h, src) / 1500
        svg.text(p[0] + dx, p[1] + dy + 22, f"{t * 1000:.0f} ms", "codel", 15, P.black_60, "end" if dx < 0 else "start")
    s = fm(src)
    svg.circle(*s, 13, P.cream, stroke=P.black, stroke_width=3)
    svg.circle(*s, 5, P.black)
    svg.text(s[0] + 22, s[1] - 18, "ping", "code", 18, P.black)
    p1 = fm((2900, 2300))
    svg.text(W - M, 312, f"B − A: {ddiff(A, B) / 1500 * 1000:+.0f} ms", "code", 17, P.blue, "end")
    svg.text(W - M, 338, f"C − A: {ddiff(A, C) / 1500 * 1000:+.0f} ms", "code", 17, P.teal, "end")
    _ = p1

    svg.frame("listen.", "underwater · time difference of arrival · c ≈ 1500 m/s")
    code_rule(svg)
    svg.code(M, CODE_Y, """
# a pinger calls once; the hydrophones hear it at different times
dd_AB = c * (t_B - t_A)                # → a hyperbola with foci A and B
dd_AC = c * (t_C - t_A)                # → another, with foci A and C
p = solve(|p-B| - |p-A| == dd_AB,  |p-C| - |p-A| == dd_AC)""", "py", 19)
    return svg


def beams() -> Svg:
    """Doppler velocity log: four beams at 30°, each echo comes back at a slightly different pitch."""
    svg = Svg(P.white)
    f0, c, alpha = 600e3, 1500.0, math.radians(30)
    v = (1.2, 0.3, -0.05)  # forward, starboard, up (m/s)
    sa, ca = math.sin(alpha), math.cos(alpha)
    beams_ = [("fore", (sa, 0, -ca), P.blue), ("aft", (-sa, 0, -ca), P.teal),
              ("stbd", (0, sa, -ca), P.lavender), ("port", (0, -sa, -ca), P.lavender_60)]
    shifts = [2 * f0 / c * sum(a * b for a, b in zip(v, bv)) for _, bv, _ in beams_]

    ax, ay, yf = W / 2 - 40, 400, 800
    alt = yf - ay - 20
    reach = alt * math.tan(alpha)
    # seafloor
    rng = random.Random(1)
    floor = [(x, yf + 8 * math.sin(x / 47) + 5 * math.sin(x / 13 + 1)) for x in range(M, W - M + 1, 6)]
    svg.poly(floor + [(W - M, yf + 40), (M, yf + 40)], P.lavender_20)
    svg.polyline(floor, P.black, 2.5)
    for _ in range(30):
        x = rng.uniform(M + 10, W - M - 10)
        svg.circle(x, yf + 22 + rng.uniform(-4, 8), rng.uniform(2, 4), P.lavender_60)
    for (name, bv, col), df in zip(beams_[:2], shifts[:2]):
        ex = ax + bv[0] / sa * reach
        svg.poly([(ax, ay + 20), (ex - 22, yf), (ex + 22, yf)], col, opacity="0.18")
        svg.line(ax, ay + 20, ex, yf, col, 3)
        for r in (0.35, 0.55, 0.75):  # pings travelling down the beam
            px, py = ax + (ex - ax) * r, ay + 20 + (yf - ay - 20) * r
            svg.arc(px, py, 14, math.atan2(yf - ay, ex - ax) - 0.8, math.atan2(yf - ay, ex - ax) + 0.8, col, 3)
        svg.text(ex, yf + 70, name, "code", 18, col, "middle")
        svg.text(ex, yf + 94, f"{df:+.0f} Hz", "codel", 15, P.black_80, "middle")
    svg.line(ax, ay + 20, ax, yf, P.lavender, 2, stroke_dasharray="3 6")
    svg.text(ax + 12, yf - 30, "stbd / port: into and out of the page", "codel", 14, P.black_60)
    # the vehicle
    svg.add(f'<rect x="{ax - 170}" y="{ay - 26}" width="300" height="52" rx="26" fill="{P.black}"/>')
    svg.poly([(ax + 130, ay - 26), (ax + 130, ay + 26), (ax + 190, ay)], P.black)
    svg.poly([(ax - 170, ay), (ax - 200, ay - 30), (ax - 200, ay + 30)], P.black)
    svg.rect(ax - 18, ay + 18, 36, 12, P.blue)
    arrow(svg, (ax + 200, ay), (ax + 290, ay), P.blue, 4, 20)
    svg.text(ax + 210, ay - 18, f"{v[0]} m/s", "code", 18, P.blue)
    svg.text(ax - 210, ay - 40, f"altitude {alt / 16:.0f} m", "codel", 15, P.black_60)

    # top view of the four footprints
    tx, ty, tr = W - M - 70, 300, 52
    svg.circle(tx, ty, tr + 22, "none", stroke=P.black_20, stroke_width=1.5)
    for (name, bv, col) in beams_:
        px, py = tx + bv[0] / sa * tr, ty - bv[1] / sa * tr
        svg.circle(px, py, 10, col)
    svg.rect(tx - 9, ty - 4, 18, 8, P.black, rx=4)
    svg.text(tx, ty + tr + 50, "from above", "codel", 14, P.black_60, "middle")

    # echo spectra, all four on one axis
    x0, x1, yb = M + 40, W - M - 40, 990

    def fx(df):
        return (x0 + x1) / 2 + (x1 - x0) / 2 * df / 700

    svg.line(x0, yb, x1, yb, P.black, 2)
    svg.line(fx(0), yb + 6, fx(0), yb - 92, P.black_60, 1.5, stroke_dasharray="2 6")
    svg.text(fx(0), yb + 26, "f₀ = 600 kHz", "codel", 14, P.black_60, "middle")
    for (name, _, col), df in zip(beams_, shifts):
        pk = [(fx(df + d), yb - 80 * math.exp(-0.5 * (d / 28) ** 2)) for d in range(-110, 111, 4)]
        svg.poly(pk, col, opacity="0.85")
    svg.text(x0, yb - 70, "echo spectra", "codel", 14, P.black_60)

    svg.frame("beams.", "AUV · doppler velocity log · four beams at 30°")
    code_rule(svg)
    svg.code(M, CODE_Y, """
b  = beam_unit_vectors(30)            # 4 × 3: fore, aft, stbd, port
df = 2 * f0 / c * b @ v               # each echo's shift: speed along that beam
v  = lstsq(2 * f0 / c * b, df)        # 4 equations, 3 unknowns, one spare
# v over the seafloor, integrated: dead reckoning that drifts ~0.2 %""", "py", 19)
    return svg


def _contours(grid, xs, ys, level):
    """Marching squares: segments of grid == level."""
    segs = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            v = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            p = [(xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])]
            cut = []
            for k in range(4):
                a, b = v[k], v[(k + 1) % 4]
                if (a < level) != (b < level):
                    t = (level - a) / (b - a)
                    pa, pb = p[k], p[(k + 1) % 4]
                    cut.append((pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t))
            if len(cut) == 2:
                segs.append(cut)
            elif len(cut) == 4:
                segs += [cut[:2], cut[2:]]
    return segs


def contour() -> Svg:
    """Terrain-relative navigation: a strip of measured depths, slid over the chart until it fits."""
    svg = Svg(P.black)
    rng = random.Random(8)
    bumps = [(180, 120, 70, -14), (420, 330, 90, 18), (650, 160, 60, -16), (760, 380, 80, 12),
             (300, 400, 50, -10), (520, 80, 45, 9), (90, 300, 60, 11), (870, 120, 55, 8)]

    def depth(x, y):
        d = 140 - 0.02 * x + 0.03 * y
        for bx, by, s, hgt in bumps:
            d -= hgt * math.exp(-((x - bx) ** 2 + (y - by) ** 2) / (2 * s * s))
        return d

    X, Y, h = 900, 480, 6
    xs = [i * h for i in range(X // h + 1)]
    ys = [j * h for j in range(Y // h + 1)]
    grid = [[depth(x, y) for x in xs] for y in ys]
    box = (M, 290, W - M, 780)
    fm = fit([(0, 0), (X, Y)], box, pad=0)

    lo, hi = math.floor(min(min(r) for r in grid)), math.ceil(max(max(r) for r in grid))
    for lev in range(lo - lo % 2, hi + 1, 2):
        segs = [[fm(a), fm(b)] for a, b in _contours(grid, xs, ys, lev)]
        major = lev % 10 == 0
        path(svg, segs, P.blue_60 if major else P.blue_80, 1.8 if major else 1, opacity="1" if major else "0.6")

    truth = [(120 + 4.5 * i, 210 + 70 * math.sin(i / 22)) for i in range(120)]
    meas = [depth(*p) + rng.gauss(0, 0.4) for p in truth]
    off = (34, -26)
    dr = [(x + off[0] + 0.12 * i, y + off[1] + 0.05 * i) for i, (x, y) in enumerate(truth)]

    def mse(o):
        return sum((depth(x + o[0], y + o[1]) - z) ** 2 for (x, y), z in zip(dr, meas)) / len(meas)

    win, st = 50, 10
    cands = [(dx, dy) for dx in range(-win, win + 1, st) for dy in range(-win, win + 1, st)]
    scores = {o: mse(o) for o in cands}
    best = min(scores, key=scores.get)
    s0 = scores[best]
    fixed = [(x + best[0], y + best[1]) for x, y in dr]

    px_m = fm((1, 0))[0] - fm((0, 0))[0]
    for o in cands:
        like = math.exp(-(scores[o] - s0) / 4.0)
        p = fm((dr[0][0] + o[0], dr[0][1] + o[1]))
        svg.rect(p[0] - st * px_m / 2, p[1] - st * px_m / 2, st * px_m, st * px_m, mix(P.black, P.lavender, like ** 0.5),
                 stroke=P.black, stroke_width=1)
    svg.polyline([fm(p) for p in truth], P.black_60, 2, stroke_dasharray="2 7")
    svg.polyline([fm(p) for p in dr], P.lavender, 3, stroke_dasharray="9 7")
    svg.polyline([fm(p) for p in fixed], P.white, 3.5)
    e = fm(dr[-1])
    tag(svg, e[0] + 16, e[1] + 22, "dead reckoning", "code", 16, P.lavender, bg=P.black)
    f = fm(fixed[-1])
    tag(svg, f[0] + 16, f[1] - 8, "matched", "code", 16, P.white, bg=P.black)
    s = fm(dr[0])
    tag(svg, s[0], s[1] - win * px_m - 12, f"search ±{win} m", "codel", 14, P.blue_40, "middle", bg=P.black)
    svg.text(W - M, 812, f"chart · 2 m contours · {X} × {Y} m", "codel", 14, P.blue_40, "end")

    # depth profiles along the track
    x0, x1, yt, yb = M + 60, W - M, 850, 985
    prof_dr = [depth(*p) for p in dr]
    prof_fx = [depth(*p) for p in fixed]
    allv = meas + prof_dr + prof_fx
    zmin, zmax = min(allv), max(allv)

    def gp(i, z):
        return x0 + (x1 - x0) * i / (len(meas) - 1), yt + (yb - yt) * (z - zmin) / (zmax - zmin)

    svg.polyline([gp(i, z) for i, z in enumerate(prof_dr)], P.lavender, 2.5, stroke_dasharray="6 6")
    svg.polyline([gp(i, z) for i, z in enumerate(prof_fx)], P.white, 2.5)
    for i, z in enumerate(meas):
        if i % 3 == 0:
            svg.circle(*gp(i, z), 3.5, P.teal_60)
    svg.text(x0 - 14, yt + 10, "depth", "codel", 14, P.blue_40, "end")
    svg.text(x0 - 14, yt + 30, "below", "codel", 14, P.blue_40, "end")
    svg.text(x0 - 14, yb, "track", "codel", 14, P.blue_40, "end")
    svg.text(x1, yb + 30, "• measured   — chart under the match   - - chart under DR", "codel", 14, P.blue_40, "end")

    svg.frame("contour.", "AUV · terrain-relative navigation · bathymetry match", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
z = altimeter + depth_sensor              # seafloor depth under the track
for o in window(±50 m):                    # slide the track over the chart
    cost[o] = mean((chart(track + o) - z)**2)
fix = track + argmin(cost)                 # where the hills line up""", "py", 19, dark=True)
    return svg


def bend() -> Svg:
    """Sound-speed refraction: acoustic rays bend toward slow water, so a range is not a straight line."""
    svg = Svg(P.white)
    zmax, xmax = 5000.0, 60000.0
    z1, Bw, eps = 1300.0, 1300.0, 0.00737

    def c(z):
        eta = 2 * (z - z1) / Bw
        return 1500 * (1 + eps * (eta - 1 + math.exp(-eta)))

    def dc(z):
        eta = 2 * (z - z1) / Bw
        return 1500 * eps * (1 - math.exp(-eta)) * 2 / Bw

    def trace(z0, th0, ds=60.0, xend=xmax):
        x, z, th, t = 0.0, z0, th0, 0.0
        out = [(x, z)]
        while x < xend:
            th += -math.cos(th) * dc(z) / c(z) * ds
            x += math.cos(th) * ds
            z += math.sin(th) * ds
            t += ds / c(z)
            if z < 0:
                z, th = -z, -th
            if z > zmax:
                z, th = 2 * zmax - z, -th
            out.append((x, z))
        return out, t

    px0, px1, py0, py1 = M + 170, W - M, 300, 980

    def g(p):
        return px0 + (px1 - px0) * p[0] / xmax, py0 + (py1 - py0) * p[1] / zmax

    # c(z) panel
    cx0, cx1 = M, M + 130
    cmin, cmax = 1485, 1555

    def gc(cc, z):
        return cx0 + (cx1 - cx0) * (cc - cmin) / (cmax - cmin), py0 + (py1 - py0) * z / zmax

    svg.line(cx0, py0, cx0, py1, P.black_20, 1.5)
    svg.polyline([gc(c(z), z) for z in range(0, int(zmax) + 1, 50)], P.blue, 3.5)
    svg.text(cx0, py0 - 16, "sound speed", "codel", 14, P.black_60)
    svg.text(gc(c(z1), z1)[0] + 10, gc(c(z1), z1)[1] + 5, "slowest", "codel", 13, P.blue)
    for z in range(0, 5001, 1000):
        svg.text(cx0 - 8, py0 + (py1 - py0) * z / zmax + 5, f"{z // 1000} km", "codel", 13, P.black_60, "end")
    svg.text(gc(cmin, 0)[0], py1 + 26, f"{cmin}", "codel", 13, P.black_60)
    svg.text(gc(cmax, 0)[0], py1 + 26, f"{cmax} m/s", "codel", 13, P.black_60, "end")

    svg.rect(px0, py0, px1 - px0, py1 - py0, P.lavender_20)
    svg.clip_begin(px0, py0, px1 - px0, py1 - py0)
    zs = 1000.0
    for k in range(-14, 15):
        ray, _ = trace(zs, math.radians(k * 1.1))
        svg.polyline([g(p) for p in ray[::4]], P.blue_40, 1.4)
    svg.clip_end()

    target = (42000.0, 2400.0)
    best = None
    for k in range(-1600, 1601):
        th = math.radians(k * 0.01)
        ray, t = trace(zs, th, 60.0, target[0])
        miss = abs(ray[-1][1] - target[1])
        if best is None or miss < best[0]:
            best = (miss, th, ray, t)
    _, th_e, ray_e, t_e = best
    straight = math.dist((0, zs), target)
    est = 1500 * t_e
    svg.polyline([g((0, zs)), g(target)], P.black, 2.5, stroke_dasharray="6 7")
    svg.polyline([g(p) for p in ray_e], P.blue, 4.5)
    s, tg = g((0, zs)), g(target)
    svg.circle(*s, 9, P.black)
    svg.text(s[0] + 14, s[1] - 14, "AUV", "code", 17, P.black)
    svg.triangle(tg[0], tg[1], 22, P.teal, -math.pi / 2)
    svg.text(tg[0] + 16, tg[1] + 32, "beacon", "code", 17, P.teal)
    svg.text(px1 - 14, py1 - 70, f"travel time {t_e:.2f} s", "code", 17, P.black, "end")
    svg.text(px1 - 14, py1 - 44, f"× 1500 m/s = {est / 1000:.2f} km", "codel", 15, P.black_80, "end")
    svg.text(px1 - 14, py1 - 20, f"straight line {straight / 1000:.2f} km · off by {abs(est - straight):.0f} m",
             "codel", 15, P.black_80, "end")
    for xk in range(0, 61, 20):
        svg.text(px0 + (px1 - px0) * xk / 60, py1 + 26, f"{xk} km", "codel", 13, P.black_60,
                 "start" if xk == 0 else "end" if xk == 60 else "middle")

    svg.frame("bend.", "underwater · acoustic ray tracing · sound speed profile")
    code_rule(svg)
    svg.code(M, CODE_Y, """
# Snell, continuously: cos(theta) / c(z) is constant along a ray
theta += -cos(theta) * dc_dz(z) / c(z) * ds   # bends toward slow water
t     += ds / c(z)                            # time along the curve
r_est  = 1500 * t      # assume straight + constant c: the range is off""", "py", 19)
    return svg


FAMILIES = {"ground": [particles, align, close, banana], "aerial": [fuse, flow, rtk, spread],
            "underwater": [listen, beams, contour, bend]}
OUT = Path(__file__).resolve().parents[1] / "out/localization"

if __name__ == "__main__":
    names = set(sys.argv[1:])
    for family, fns in FAMILIES.items():
        for fn in fns:
            if names and fn.__name__ not in names:
                continue
            out = OUT / family / f"{fn.__name__}.svg"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(fn().render())
            print(out.relative_to(OUT.parents[1]), f"{out.stat().st_size // 1024} KB")
