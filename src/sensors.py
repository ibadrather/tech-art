"""Eight sensor posters, each drawn from the maths or code it shows.

Run:  uv run --no-project --with fonttools --with brotli python src/sensors.py
"""

from __future__ import annotations

import cmath
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from posters import ART, CODE_Y, M, W, code_rule, fit  # noqa: E402


def arrow(svg: Svg, a, b, color, width=3, head=16):
    """A line from a to b with a triangular head at b."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    tip = (b[0] - head * 0.45 * math.cos(ang), b[1] - head * 0.45 * math.sin(ang))
    svg.line(*a, *tip, color, width, stroke_linecap="round")
    svg.triangle(*tip, head, color, ang)


# ----------------------------------------------------------------------------
def feel() -> Svg:
    """IMU tilt: a drifting gyro, a noisy accelerometer and the complementary filter that trusts each where it's good."""
    svg = Svg(P.white)
    rng = random.Random(5)
    dt, T, alpha, bias = 0.01, 12.0, 0.98, 2.4

    def truth(t):
        return 28 * math.sin(0.55 * t) + 10 * math.sin(1.9 * t + 0.8) - 10 * math.sin(0.8)

    def rate(t):
        return 28 * 0.55 * math.cos(0.55 * t) + 10 * 1.9 * math.cos(1.9 * t + 0.8)

    th_g = th_f = 0.0
    accel, gyro, fused = [], [], []
    for k in range(int(T / dt)):
        t = k * dt
        g = rate(t) + bias + rng.gauss(0, 1.5)  # deg/s, with a constant bias
        a = truth(t) + rng.gauss(0, 6.0)  # deg, from atan2 of the gravity vector
        th_g += g * dt
        th_f = alpha * (th_f + g * dt) + (1 - alpha) * a
        accel.append((t, a))
        gyro.append((t, th_g))
        fused.append((t, th_f))

    x0, x1, ymid, s = M + 10, W - M - 10, 640, 5.2

    def px(t, v):
        return x0 + (x1 - x0) * t / T, ymid - v * s

    svg.line(x0, ymid, x1, ymid, P.black, 2, stroke_dasharray="10 10")
    svg.text(x1, ymid - 14, "0°", "code", 18, P.black, "end")
    svg.polyline([px(t, v) for t, v in accel[::3]], P.blue_40, 1.6)
    svg.polyline([px(t, v) for t, v in gyro], P.lavender, 4)
    svg.polyline([px(t, v) for t, v in fused], P.teal, 7)

    ly = 970
    for i, (col, h, label) in enumerate([(P.teal, 9, "fused  α = 0.98"), (P.lavender, 7, "gyro ∫ω dt  drifts"), (P.blue_40, 4, "accel  noisy")]):
        xx = x0 + i * 300
        svg.rect(xx, ly - 6, 28, h, col)
        svg.text(xx + 40, ly + 2, label, "codel", 15, P.black_80)

    svg.frame("feel.", "IMU · complementary filter · gyro + accel")
    code_rule(svg)
    svg.code(M, CODE_Y, """
def tilt(angle, gyro, accel, dt, a=0.98):
    # gyro for the short term, gravity for the long term
    return a*(angle + gyro*dt) + (1 - a)*accel""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def ping() -> Svg:
    """Ultrasonic ranging: wavefronts out, echoes back, and the time between them."""
    svg = Svg(P.black)
    cy = 500
    bx = M + 10
    # the sensor board, facing right: transmitter above, receiver below
    svg.rect(bx, cy - 100, 46, 200, P.blue, rx=6)
    tx, rx_ = (bx + 46, cy - 46), (bx + 46, cy + 46)
    for c in (tx, rx_):
        svg.circle(*c, 30, P.black, stroke=P.blue_40, stroke_width=4)
        svg.circle(*c, 10, P.blue_40)
    svg.text(bx + 23, cy + 136, "trig", "codel", 15, P.lavender, "middle")
    wall_x = W - M - 30
    svg.rect(wall_x, cy - 170, 16, 340, P.lavender)

    spread = math.radians(17)
    step = 34
    reach = wall_x - tx[0]
    img = (2 * wall_x - tx[0], cy)  # the echo from a flat wall looks like it comes from the mirror image
    for k in range(1, int(reach / step) + 1):
        r = k * step
        svg.arc(*tx, r, -spread, spread, P.lavender, 3, opacity=f"{1 - 0.6 * r / reach:.2f}")
        rr = (img[0] - wall_x) + r - step / 2
        if img[0] - rr > tx[0] + 10:
            ang = math.asin(min(1, (170 * r / reach + 40) / rr))
            svg.arc(*img, rr, math.pi - ang, math.pi + ang, P.teal_60, 2.5, opacity=f"{0.35 + 0.6 * r / reach:.2f}")

    # the two pins on a scope: the burst out, the echo back after Δt = 2d / c
    c_air, d = 343.0, 1.0
    dt_echo = 2 * d / c_air  # s
    t_max = 7.0e-3
    xa, xb = M + 70, W - M

    def tx_t(t):
        return xa + (xb - xa) * t / t_max

    def burst(t, t0, amp, decay):
        if t < t0:
            return 0.0
        u = t - t0
        env = min(u / 0.05e-3, 1.0) * math.exp(-max(0.0, u - 0.2e-3) / decay) if u < 0.2e-3 + 6 * decay else 0.0
        return amp * env * math.sin(2 * math.pi * 40e3 * u)

    ys = (790, 910)
    svg.text(M, ys[0] + 6, "out", "codel", 16, P.lavender)
    svg.text(M, ys[1] + 6, "echo", "codel", 16, P.teal_60)
    for y0, t0, amp, dec, col in [(ys[0], 0.0, 34, 0.02e-3, P.lavender), (ys[1], dt_echo, 22, 0.12e-3, P.teal_60)]:
        n = 2400
        svg.polyline([(tx_t(t_max * i / n), y0 - burst(t_max * i / n, t0, amp, dec)) for i in range(n + 1)], col, 1.6)
    xe = tx_t(dt_echo)
    svg.line(tx_t(0), ys[0] + 46, tx_t(0), ys[1] + 40, P.blue, 1.5, stroke_dasharray="3 6")
    svg.line(xe, ys[1] - 40, xe, ys[1] + 40, P.blue, 1.5, stroke_dasharray="3 6")
    arrow(svg, (tx_t(0) + 4, ys[1] + 40), (xe - 2, ys[1] + 40), P.blue, 2, 12)
    svg.text((tx_t(0) + xe) / 2, ys[1] + 70, f"Δt = {dt_echo * 1e3:.2f} ms  →  d = cΔt/2 = {d:.2f} m", "code", 17, P.white, "middle")

    svg.frame("ping.", "ultrasonic · 40 kHz · time of flight", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
// out and back, so halve it
float us   = pulseIn(ECHO, HIGH);          // echo width, µs
float d_m  = 343.0f * (us / 1e6f) / 2.0f;  // speed of sound
float d_cm = us / 58.0f;                   // the folklore version""", "cpp", 20, dark=True)
    return svg


# ----------------------------------------------------------------------------
def count() -> Svg:
    """Quadrature encoder: a slotted disc, two square waves a quarter-slot apart, and the count they decode to."""
    svg = Svg(P.cream)
    slots = 20
    cx, cy, R = W / 2, 455, 150
    svg.circle(cx, cy, R, P.blue)
    pitch = 2 * math.pi / slots
    for k in range(slots):
        a0, a1 = k * pitch, k * pitch + pitch / 2
        ring = [(cx + r * math.cos(a0 + (a1 - a0) * i / 8), cy + r * math.sin(a0 + (a1 - a0) * i / 8)) for r in (112,) for i in range(9)]
        ring += [(cx + r * math.cos(a1 - (a1 - a0) * i / 8), cy + r * math.sin(a1 - (a1 - a0) * i / 8)) for r in (138,) for i in range(9)]
        svg.poly(ring, P.cream)
    svg.circle(cx, cy, 38, P.cream)
    svg.circle(cx, cy, 14, P.black)
    # read heads a (k + 1/4) pitch apart: that quarter is what tells direction
    for name, off in (("A", -0.625), ("B", 0.625)):
        a = -math.pi / 2 + off * pitch
        hx, hy = cx + 125 * math.cos(a), cy + 125 * math.sin(a)
        svg.circle(hx, hy, 9, P.black)
        svg.text(cx + 175 * math.cos(a), cy + 175 * math.sin(a) + 8, name, "code", 22, P.black, "middle")

    lut = [0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0]
    n = 6000
    x0, x1 = M + 70, W - M
    A, B, C = [], [], []
    state = c = 0
    edges = []
    for i in range(n + 1):
        t = i / n
        phi = 5.5 * math.sin(math.pi * t)  # disc position, in slots: forward, then back
        a = int((phi % 1) < 0.5)
        b = int(((phi - 0.25) % 1) < 0.5)
        state = ((state << 2) | (a << 1) | b) & 15
        if i and lut[state]:
            edges.append(x0 + (x1 - x0) * t)
        c += lut[state] if i else 0
        A.append(a)
        B.append(b)
        C.append(c)

    def square(vals, ymid, amp):
        out = []
        for i, v in enumerate(vals):
            x = x0 + (x1 - x0) * i / n
            y = ymid - amp * (v - 0.5) * 2
            if out and out[-1][1] != y:
                out.append((x, out[-1][1]))
            out.append((x, y))
        return out

    ya, yb, yc0, yc1 = 670, 770, 975, 850
    for x in edges:
        svg.line(x, ya - 40, x, yb + 40, P.black_20, 1)
    svg.polyline(square(A, ya, 26), P.blue, 4, stroke_linecap="butt", stroke_linejoin="miter")
    svg.polyline(square(B, yb, 26), P.teal, 4, stroke_linecap="butt", stroke_linejoin="miter")
    cmax = max(C)
    stair = []
    for i, v in enumerate(C):
        x = x0 + (x1 - x0) * i / n
        y = yc0 + (yc1 - yc0) * v / cmax
        if stair and stair[-1][1] != y:
            stair.append((x, stair[-1][1]))
        stair.append((x, y))
    svg.polyline(stair, P.lavender, 3, stroke_linejoin="miter")
    peak = C.index(cmax)
    svg.text(x0 + (x1 - x0) * peak / n, yc1 - 16, f"+{cmax}", "code", 18, P.black, "middle")
    for label, y in (("A", ya), ("B", yb), ("n", (yc0 + yc1) / 2)):
        svg.text(M, y + 7, label, "code", 20, P.black_60)

    svg.frame("count.", f"quadrature encoder · {slots} slots · ×4 decoding")
    code_rule(svg)
    svg.code(M, CODE_Y, """
// two square waves, 90° apart: their order is the direction
static const int lut[16] = {0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
state = ((state << 2) | (a << 1) | b) & 15;
count += lut[state];""", "cpp", 19)
    return svg


# ----------------------------------------------------------------------------
def project() -> Svg:
    """Pinhole camera: a cube, its rays to the optical centre, and the picture they leave on the image plane."""
    svg = Svg(P.white)
    f, pw, ph = 2.4, 2.0, 1.5  # focal length and image-plane size (camera frame: x right, y down, z forward)

    def rot(p, yaw, pitch):
        x, y, z = p
        x, z = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)
        y, z = y * math.cos(pitch) - z * math.sin(pitch), y * math.sin(pitch) + z * math.cos(pitch)
        return x, y, z

    centre, size = (0.4, -0.2, 5.0), 1.5
    corners = [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    cube = []
    for c in corners:
        q = rot(tuple(v * size / 2 for v in c), 0.6, 0.45)
        cube.append(tuple(q[i] + centre[i] for i in range(3)))
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if sum(a != b for a, b in zip(corners[i], corners[j])) == 1]

    def proj(p):  # the whole model: u = f X / Z, v = f Y / Z (in plane units)
        return (f * p[0] / p[2], f * p[1] / p[2], f)

    img = [proj(p) for p in cube]
    plane = [(-pw / 2, -ph / 2, f), (pw / 2, -ph / 2, f), (pw / 2, ph / 2, f), (-pw / 2, ph / 2, f)]

    def view(p):  # how we, the viewer, look at the scene: from above and to one side
        x, y, z = p
        yaw, pitch = math.radians(58), math.radians(34)
        x1 = x * math.cos(yaw) + z * math.sin(yaw)
        z1 = -x * math.sin(yaw) + z * math.cos(yaw)
        y2 = y * math.cos(pitch) - z1 * math.sin(pitch)
        return (x1, -y2)

    allp = [view(p) for p in cube + plane + [(0, 0, 0), (0, 0, 7.2)]]
    fm = fit(allp, pad=30)

    def pg(p):
        return fm(view(p))

    svg.line(*pg((0, 0, 0)), *pg((0, 0, 7.2)), P.black_60, 1.5, stroke_dasharray="6 8")
    for c in plane:
        svg.line(*pg((0, 0, 0)), *pg(c), P.black, 1.5)
    svg.poly([pg(c) for c in plane], P.lavender_20, stroke=P.lavender, stroke_width=2.5, stroke_linejoin="round")
    for k in range(1, 8):  # pixel grid
        a, b = (-pw / 2 + pw * k / 8, -ph / 2, f), (-pw / 2 + pw * k / 8, ph / 2, f)
        svg.line(*pg(a), *pg(b), P.lavender_60, 1)
    for k in range(1, 6):
        a, b = (-pw / 2, -ph / 2 + ph * k / 6, f), (pw / 2, -ph / 2 + ph * k / 6, f)
        svg.line(*pg(a), *pg(b), P.lavender_60, 1)
    for p in cube:
        svg.line(*pg((0, 0, 0)), *pg(p), P.blue_40, 1.5)
    for i, j in edges:
        svg.line(*pg(img[i]), *pg(img[j]), P.teal, 3, stroke_linecap="round")
    for p in img:
        svg.circle(*pg(p), 4, P.teal)
    for i, j in edges:
        svg.line(*pg(cube[i]), *pg(cube[j]), P.blue, 5, stroke_linecap="round")
    for p in cube:
        svg.circle(*pg(p), 6, P.white, stroke=P.blue, stroke_width=3)
    o = pg((0, 0, 0))
    svg.circle(*o, 9, P.black)
    svg.text(o[0] - 4, o[1] + 40, "pinhole", "codel", 15, P.black_60, "middle")
    pc = pg((pw / 2, ph / 2, f))
    svg.text(pc[0] + 10, pc[1] + 26, f"z = f = {f:g}", "codel", 15, P.black_60)

    svg.frame("project.", "pinhole camera · 3D in, 2D out")
    code_rule(svg)
    svg.code(M, CODE_Y, """
def project(X, Y, Z, fx, fy, cx, cy):
    u = fx * X / Z + cx
    v = fy * Y / Z + cy
    return u, v        # Z is gone: depth is what you lose""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def orient() -> Svg:
    """Magnetometer calibration: a lopsided ellipse of raw readings, recentred and rescaled into a circle."""
    svg = Svg(P.black)
    rng = random.Random(9)
    off_true, scale_true = (0.95, 0.55), (1.45, 0.92)
    raw = []
    for k in range(380):
        psi = 2 * math.pi * k / 380 + 0.15 * math.sin(3 * k / 380 * 2 * math.pi)
        raw.append((off_true[0] + scale_true[0] * math.cos(psi) + rng.gauss(0, 0.025),
                    off_true[1] + scale_true[1] * math.sin(psi) + rng.gauss(0, 0.025)))
    xs, ys = [p[0] for p in raw], [p[1] for p in raw]
    off = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
    sc = ((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2)
    cal = [((x - off[0]) / sc[0], (y - off[1]) / sc[1]) for x, y in raw]

    fm = fit(raw + cal + [(-1.25, 0), (0, -1.25)], pad=30)
    o = fm((0, 0))
    span = 400
    svg.line(o[0] - span, o[1], o[0] + span * 1.4, o[1], P.blue, 1.5, stroke_dasharray="2 8")
    svg.line(o[0], o[1] + span * 0.75, o[0], o[1] - span, P.blue, 1.5, stroke_dasharray="2 8")
    for (a, b) in list(zip(raw, cal))[::14]:
        svg.line(*fm(a), *fm(b), P.white, 1, opacity="0.18")
    for p in raw:
        svg.circle(*fm(p), 3, P.lavender)
    for p in cal:
        svg.circle(*fm(p), 3, P.teal_60)
    arrow(svg, o, fm(off), P.white, 2.5, 16)
    svg.text(*(v + d for v, d in zip(fm((off[0] / 2, off[1] / 2)), (14, -14))), "offset", "codel", 16, P.white)

    i = 128  # one reading, followed through
    a, b = fm(raw[i]), fm(cal[i])
    psi = math.atan2(cal[i][1], cal[i][0])
    svg.line(*o, *b, P.white, 2.5)
    rr = 70
    svg.arc(*o, rr, 0, -psi, P.white, 2)
    svg.text(o[0] + rr * 1.35 * math.cos(-psi / 2), o[1] + rr * 1.35 * math.sin(-psi / 2) + 6, "ψ", "code", 20, P.white, "middle")
    svg.circle(*a, 8, P.lavender, stroke=P.black, stroke_width=3)
    svg.circle(*b, 8, P.teal_60, stroke=P.black, stroke_width=3)
    svg.triangle(*o, 34, P.blue, -math.pi / 2)
    rx = fm((off[0] + sc[0], off[1] - sc[1] * 0.9))
    svg.text(rx[0] - 6, rx[1] + 40, "raw", "code", 18, P.lavender, "end")
    cx_ = fm((-0.78, -0.86))
    svg.text(cx_[0] - 12, cx_[1] + 26, "calibrated", "code", 18, P.teal_60, "end")

    svg.frame("orient.", "magnetometer · hard + soft iron · min/max", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
off   = (hi + lo) / 2          # hard iron: recentre
scale = (hi - lo) / 2          # soft iron: make it round
x, y  = (raw - off) / scale
heading = atan2(y, x)""", "py", 21, dark=True)
    return svg


# ----------------------------------------------------------------------------
def locate() -> Svg:
    """2D trilateration: range rings from four beacons and Gauss–Newton walking from a guess to the fix."""
    svg = Svg(P.cream)
    rng = random.Random(4)
    sats = [(-5.2, 3.3), (4.9, 3.6), (5.6, -2.6), (-5.4, -2.9)]
    truth = (0.6, 0.2)
    sigma = 0.12
    rho = [math.dist(s, truth) + rng.gauss(0, sigma) for s in sats]

    p = (-3.4, -1.6)
    path = [p]
    for _ in range(6):  # Gauss–Newton on the range residuals
        JtJ = [[0.0, 0.0], [0.0, 0.0]]
        Jtr = [0.0, 0.0]
        for s, r_meas in zip(sats, rho):
            d = math.dist(p, s)
            j = ((p[0] - s[0]) / d, (p[1] - s[1]) / d)
            r = d - r_meas
            for a in range(2):
                Jtr[a] += j[a] * r
                for b in range(2):
                    JtJ[a][b] += j[a] * j[b]
        det = JtJ[0][0] * JtJ[1][1] - JtJ[0][1] * JtJ[1][0]
        dx = (JtJ[1][1] * Jtr[0] - JtJ[0][1] * Jtr[1]) / det
        dy = (-JtJ[1][0] * Jtr[0] + JtJ[0][0] * Jtr[1]) / det
        p = (p[0] - dx, p[1] - dy)
        path.append(p)

    box = (M, 280, W - M, 1000)
    fm = fit([(-6.2, -3.9), (6.2, 4.6)], box, pad=0)
    s = fm((1, 0))[0] - fm((0, 0))[0]
    cols = [P.blue, P.teal, P.lavender, P.blue_80]
    svg.clip_begin(box[0], box[1], box[2] - box[0], box[3] - box[1])
    for sat, r, col in zip(sats, rho, cols):
        c = fm(sat)
        svg.circle(*c, r * s, "none", stroke=col, stroke_width=f"{2 * 3 * sigma * s:.1f}", opacity="0.16")
        svg.circle(*c, r * s, "none", stroke=col, stroke_width=2)
    svg.clip_end()
    for sat, col in zip(sats, cols):
        c = fm(sat)
        svg.rect(c[0] - 34, c[1] - 5, 22, 10, col)
        svg.rect(c[0] + 12, c[1] - 5, 22, 10, col)
        svg.line(c[0] - 12, c[1], c[0] + 12, c[1], P.black, 2)
        svg.poly([(c[0], c[1] - 12), (c[0] + 12, c[1]), (c[0], c[1] + 12), (c[0] - 12, c[1])], P.black)
    pts_ = [fm(q) for q in path]
    svg.polyline(pts_, P.black, 2.5, stroke_dasharray="1 7")
    for q in pts_[:-1]:
        svg.circle(*q, 5, P.black)
    svg.text(pts_[0][0] - 12, pts_[0][1] + 30, "guess", "codel", 16, P.black_80)
    fx = pts_[-1]
    svg.circle(*fx, 22, "none", stroke=P.black, stroke_width=2.5)
    svg.circle(*fx, 9, P.black)
    svg.text(fx[0] + 34, fx[1] - 16, f"fix  ±{math.dist(path[-1], truth):.2f}", "code", 17, P.black)

    svg.frame("locate.", "trilateration · 4 beacons · Gauss–Newton")
    code_rule(svg)
    svg.code(M, CODE_Y, """
for _ in range(6):                    # Gauss–Newton
    d = norm(S - p, axis=1)           # predicted ranges
    J = (p - S) / d[:, None]
    p = p - lstsq(J, d - rho)[0]      # step against the residual""", "py", 21)
    return svg


# ----------------------------------------------------------------------------
def triangulate() -> Svg:
    """Stereo depth: two cameras' pixel rays cross in a lattice whose cells grow with distance."""
    svg = Svg(P.white)
    Bl, f, half, npx = 1.0, 0.35, 0.25, 15
    cams = [(-Bl / 2, 0.0), (Bl / 2, 0.0)]
    box = (M, 280, W - M, 1000)
    fm = fit([(-4.6, -0.55), (4.6, 6.9)], box, pad=0)
    zfar = 12.0
    svg.clip_begin(box[0], box[1], box[2] - box[0], box[3] - box[1])
    for (cx, cz), col in zip(cams, (P.blue, P.teal)):
        for i in range(-npx, npx + 1):
            u = half * i / npx
            end = (cx + u * zfar / f, zfar)
            svg.line(*fm((cx, cz)), *fm(end), col, 1, opacity="0.42")
    svg.clip_end()

    target = (0.95, 3.9)
    xl = f * (target[0] - cams[0][0]) / target[1]
    xr = f * (target[0] - cams[1][0]) / target[1]
    d = xl - xr
    Z = f * Bl / d
    zline = fm((0, Z))[1]
    svg.line(box[0], zline, box[2], zline, P.black, 1.5, stroke_dasharray="6 8")
    svg.text(box[0], zline - 14, f"Z = f·B/d = {Z:.2f}", "code", 17, P.black)
    for (cx, cz), x_img in zip(cams, (xl, xr)):
        svg.line(*fm((cx, cz)), *fm(target), P.black, 3)
        svg.line(*fm((cx - half, f)), *fm((cx + half, f)), P.lavender, 6, stroke_linecap="round")
        svg.circle(*fm((cx + x_img, f)), 6, P.blue)
        c = fm((cx, cz))
        svg.triangle(c[0], c[1] + 10, 46, P.black, -math.pi / 2)
    svg.circle(*fm(target), 13, P.blue)
    svg.circle(*fm(target), 22, "none", stroke=P.blue, stroke_width=3)
    yb = fm((0, 0))[1] + 48
    l, r = fm(cams[0])[0], fm(cams[1])[0]
    svg.line(l, yb, r, yb, P.black, 2)
    for xx in (l, r):
        svg.line(xx, yb - 8, xx, yb + 8, P.black, 2)
    svg.text((l + r) / 2, yb + 30, "B", "code", 18, P.black, "middle")

    svg.frame("triangulate.", "stereo · depth from disparity")
    code_rule(svg)
    svg.code(M, CODE_Y, """
def depth(x_left, x_right, f, B):
    d = x_left - x_right       # disparity, px
    return f * B / d           # far away, d → 0, Z blows up""", "py", 21)
    return svg


SENSORS = [feel, ping, count, project, orient, locate, triangulate]

if __name__ == "__main__":
    for fn in SENSORS:
        out = fn().save(fn.__name__, "sensors")
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
