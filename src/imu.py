"""IMU posters: what's inside an inertial measurement unit, what a better one costs, how it drifts, and how to use it.

Every poster names one problem (issue) and how it's beaten (fix). The drawings are computed:
the MEMS numbers come from spring-mass physics, the drift and fusion plots from simulated sensors.

Sense:  proof. coriolis. sagnac.
Grade:  grades. coast. allan.
Drift:  integrate. leak. warm.
Fuse:   bias. yaw. stance.
Use:    tumble. mount. alias.

Run:  uv run --no-project --with fonttools --with brotli python src/imu.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from drone import ART_TOP, axis_label, brief, missing_glyphs  # noqa: E402
from gps import inv  # noqa: E402
from posters import CODE_Y, M, W, code_rule  # noqa: E402
from sensors import arrow  # noqa: E402

G = 9.81
R_E = 6.371e6
KB, EPS0, C = 1.380649e-23, 8.854e-12, 299792458.0
EARTH = 7.2921e-5  # rad/s
DEG_H = math.pi / 180 / 3600  # 1 °/h in rad/s
LAT = 52.5
W_S = math.sqrt(G / R_E)  # Schuler frequency


# ============================================================================
# shared furniture
# ============================================================================
def lin(v0, v1, p0, p1):
    return lambda v: p0 + (p1 - p0) * (v - v0) / (v1 - v0)


def logm(v0, v1, p0, p1):
    k = (p1 - p0) / math.log(v1 / v0)
    return lambda v: p0 + k * math.log(v / v0)


def ink(dark):
    return P.white if dark else P.black


def rule(dark):
    return P.black_80 if dark else P.black_20


def trace(svg, ts, vs, gx, gy, col, width=2.0, step=1, **kw):
    svg.polyline([(gx(t), gy(v)) for t, v in zip(ts[::step], vs[::step])], col, width, **kw)


def hlines(svg, x0, x1, vals, gy, fmt, dark=False, zero=None):
    for v in vals:
        svg.line(x0, gy(v), x1, gy(v), P.black_60 if v == zero else rule(dark), 1)
        axis_label(svg, x0 - 12, gy(v) + 5, fmt(v), dark, "end", 13)


def xticks(svg, vals, gx, y, fmt, dark=False):
    for v in vals:
        axis_label(svg, gx(v), y, fmt(v), dark, "middle", 13)


def smooth(t, a, b):
    """0 before a, 1 after b, a cosine ramp between."""
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    return 0.5 - 0.5 * math.cos(math.pi * (t - a) / (b - a))


def dsmooth(t, a, b):
    if t <= a or t >= b:
        return 0.0
    return 0.5 * math.pi / (b - a) * math.sin(math.pi * (t - a) / (b - a))


def lstsq(X, Y):
    """Least squares: rows of X, rows of Y -> theta with X @ theta ≈ Y (normal equations)."""
    n, m = len(X[0]), len(Y[0])
    XtX = [[sum(r[i] * r[j] for r in X) for j in range(n)] for i in range(n)]
    XtY = [[sum(r[i] * y[j] for r, y in zip(X, Y)) for j in range(m)] for i in range(n)]
    Q = inv(XtX)
    return [[sum(Q[i][k] * XtY[k][j] for k in range(n)) for j in range(m)] for i in range(n)]


def matvec(A, v):
    return [sum(a * b for a, b in zip(row, v)) for row in A]


# ============================================================================
# sense: what's inside
# ============================================================================
def proof() -> Svg:
    """MEMS accelerometer: a proof mass on springs between comb fingers; the gaps read the acceleration."""
    svg = Svg(P.white)
    m, f0, Q, T = 2e-9, 4000.0, 1.0, 300.0
    w0 = 2 * math.pi * f0
    k = m * w0 ** 2
    x_g = G / w0 ** 2  # metres of travel per g
    d, area, pairs = 2e-6, 150e-6 * 25e-6, 20  # gap, finger overlap (length × depth), finger pairs
    C0 = EPS0 * area * pairs / d
    floor = math.sqrt(4 * KB * T * w0 / (m * Q)) / G  # g/√Hz: Brownian motion of the mass itself

    cy, cell, n, fw, gap, flen, bh = 585, 84, 7, 12, 14, 128, 22
    xs = W / 2 - n * cell / 2 + 8
    s = -9.0  # drawn displacement: the mass lags behind the frame
    a_drawn = abs(s) / gap * d / x_g
    bx0, bx1 = xs - 20, xs + n * cell - 8
    svg.rect(bx0, cy - bh, bx1 - bx0, 2 * bh, "none", stroke=P.black_20, stroke_width=1.5, stroke_dasharray="5 5")
    for i in range(n):
        base = xs + i * cell
        for side in (-1, 1):
            for j, col in ((0, P.blue), (2, P.teal)):
                fx = base + j * (fw + gap)
                ya, yb = cy + side * (bh + 14), cy + side * (bh + 14 + flen)
                svg.rect(fx, min(ya, yb), fw, flen, col, rx=2)
                svg.rect(fx - 4, yb if side > 0 else yb - 18, fw + 8, 18, col, rx=3)
            ya, yb = cy + side * bh, cy + side * (bh + flen)
            svg.rect(base + fw + gap + s, min(ya, yb), fw, flen, P.black, rx=2)
    # springs: meanders from the mass ends to fixed anchors
    for side, end_rest in ((-1, bx0), (1, bx1)):
        e = end_rest + s
        anc = end_rest + side * 92
        nf, top, bot = 6, cy - 58, cy + 58
        xj = [e + (anc - e) * (j + 1) / (nf + 1) for j in range(nf)]
        pts_, cur = [(e, cy), (xj[0], cy), (xj[0], top)], top
        for x in xj[1:]:
            pts_.append((x, cur))
            cur = bot if cur == top else top
            pts_.append((x, cur))
        pts_ += [(xj[-1], cy), (anc, cy)]
        svg.polyline(pts_, P.black_60, 2.5)
        svg.rect(anc - (24 if side < 0 else 0), cy - 40, 24, 80, P.black_60, rx=3)
    svg.rect(bx0 + s, cy - bh, bx1 - bx0, 2 * bh, P.black, rx=4)
    svg.text((bx0 + bx1) / 2 + s, cy + 6, f"proof mass · {m * 1e9:.0f} µg", "code", 16, P.white, "middle")
    top_y = cy - bh - 14 - flen - 18
    svg.text(xs + 6, top_y - 12, "C1", "code", 16, P.blue, "middle")
    svg.text(xs + 2 * (fw + gap) + 6, top_y - 12, "C2", "code", 16, P.teal, "middle")
    axis_label(svg, bx0 - 46, cy + 92, f"spring", anchor="middle")
    axis_label(svg, bx0 - 46, cy + 110, f"k = {k:.2f} N/m", anchor="middle", size=12)
    axis_label(svg, bx1 + 46, cy + 92, "anchor", anchor="middle")
    arrow(svg, (W - M - 150, top_y - 12), (W - M - 60, top_y - 12), P.black, 2.5, 14)
    svg.text(W - M - 160, top_y - 6, "a", "code", 18, P.black, "end")
    axis_label(svg, W - M, cy + bh + 14 + flen + 46, f"the mass lags: drawn as if at {a_drawn:.0f} g", anchor="end")
    axis_label(svg, bx0 - 70, cy + bh + 14 + flen + 46, "fixed fingers in colour; black moves")

    # C1, C2 against acceleration
    x0, x1, y0, y1 = M + 74, 540, 850, 990
    gx = lin(-16, 16, x0, x1)
    cs = [C0 / (1 - g * x_g / d) for g in (-16, 16)] + [C0 / (1 + g * x_g / d) for g in (-16, 16)]
    lo, hi = min(cs) * 0.98, max(cs) * 1.02
    gy = lin(lo * 1e15, hi * 1e15, y1, y0)
    for v in (round(C0 * 1e15 / 20) * 20 - 40, round(C0 * 1e15 / 20) * 20, round(C0 * 1e15 / 20) * 20 + 40):
        svg.line(x0, gy(v), x1, gy(v), P.black_20, 1)
        axis_label(svg, x0 - 10, gy(v) + 5, f"{v:.0f}", anchor="end", size=12)
    gs = [-16 + 32 * i / 100 for i in range(101)]
    trace(svg, gs, [C0 / (1 - g * x_g / d) * 1e15 for g in gs], gx, gy, P.blue, 3)
    trace(svg, gs, [C0 / (1 + g * x_g / d) * 1e15 for g in gs], gx, gy, P.teal, 3)
    svg.line(gx(0), y0, gx(0), y1, P.black_20, 1)
    xticks(svg, (-16, -8, 0, 8, 16), gx, y1 + 20, lambda v: f"{v:+d} g" if v else "0")
    axis_label(svg, x0 - 10, y0 - 14, "fF", anchor="end", size=12)
    svg.text(x1 - 4, gy(C0 / (1 - 16 * x_g / d) * 1e15) + 22, "C1", "code", 15, P.blue, "end")
    svg.text(x1 - 4, gy(C0 / (1 + 16 * x_g / d) * 1e15) - 10, "C2", "code", 15, P.teal, "end")

    tx = 610
    rows = [
        (f"1 g moves it {x_g * 1e9:.1f} nm", f"1/{d / x_g:.0f} of the {d * 1e6:.0f} µm gap"),
        (f"C0 = {C0 * 1e15:.0f} fF", f"{C0 * x_g / d * 1e15:.1f} fF more per g, per side"),
        (f"f0 = {f0 / 1e3:.0f} kHz", "stiffer spring: wider range, less travel"),
        (f"floor {floor * 1e6:.0f} µg/√Hz", "the mass's own thermal jiggle"),
    ]
    for j, (a, b) in enumerate(rows):
        svg.text(tx, 856 + j * 40, a, "code", 16, P.black)
        axis_label(svg, tx, 874 + j * 40, b, size=12)

    svg.frame("proof.", "mems accelerometer · proof mass · differential capacitance")
    brief(svg, "a chip can't feel force, and 1 g moves a tiny mass by nanometres",
          "hang a 2 µg mass on springs between comb fingers: one gap shrinks, one grows")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
x  = m * a / k                       # {x_g * 1e9:.1f} nm per g: f0 = {f0 / 1e3:.0f} kHz
C1 = eps * A / (d - x)               # the gap on one side shrinks...
C2 = eps * A / (d + x)               # ...and the other grows
a  = (C1 - C2) / (C1 + C2) * d * k / m    # = x·k/m: the difference is linear""", "py", 19)
    return svg


def coriolis() -> Svg:
    """MEMS gyro: a mass vibrating in x; rotation pushes it sideways in y, in step with its velocity."""
    svg = Svg(P.cream)
    A, fd, fsn = 10e-6, 20e3, 21e3
    wd, ws = 2 * math.pi * fd, 2 * math.pi * fsn

    def y_amp(rate_dps):
        return 2 * math.radians(rate_dps) * A * wd / (ws ** 2 - wd ** 2)

    # the device: frame, drive springs (x), sense springs (y), mass
    cx, cy = 262, 580

    def meander(p, q, n=7, amp=14):
        (ax, ay), (bx, by) = p, q
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        out = [p]
        for j in range(1, 2 * n):
            t = j / (2 * n)
            off = amp * (1 if j % 2 else -1)
            out.append((ax + ux * L * t - uy * off, ay + uy * L * t + ux * off))
        out.append(q)
        return out

    svg.rect(cx - 170, cy - 170, 340, 340, "none", stroke=P.black_60, stroke_width=2, rx=6)
    for dx, dy in ((-1, 0), (1, 0)):
        svg.polyline(meander((cx + dx * 170, cy), (cx + dx * 62, cy)), P.black, 2.5)
    for dx, dy in ((0, -1), (0, 1)):
        svg.polyline(meander((cx, cy + dy * 170), (cx, cy + dy * 62)), P.blue, 2.5)
    for g in (-34, 34):
        svg.rect(cx - 60 + g, cy - 60, 120, 120, "none", stroke=P.black_20, stroke_width=1.5, stroke_dasharray="5 5", rx=8)
    svg.rect(cx - 60, cy - 60, 120, 120, P.black, rx=8)
    svg.circle(cx, cy, 15, P.cream)
    svg.circle(cx, cy, 5, P.black)
    svg.text(cx, cy - 26, "Ω", "code", 18, P.cream, "middle")
    arrow(svg, (cx - 10, cy + 190), (cx - 100, cy + 190), P.black, 2.5, 14)
    arrow(svg, (cx + 10, cy + 190), (cx + 100, cy + 190), P.black, 2.5, 14)
    arrow(svg, (cx + 205, cy - 10), (cx + 205, cy - 100), P.blue, 2.5, 14)
    arrow(svg, (cx + 205, cy + 10), (cx + 205, cy + 100), P.blue, 2.5, 14)
    svg.text(cx, cy + 218, f"drive: ±{A * 1e6:.0f} µm at {fd / 1e3:.0f} kHz", "code", 15, P.black, "middle")
    svg.text(cx + 222, cy + 6, "sense", "code", 15, P.blue)
    axis_label(svg, cx, cy - 186, "Ω points out of the page", anchor="middle", size=13)

    # trajectory of the mass, sense axis exaggerated
    ox, oy, ax_px, ay_px = 770, 570, 190, 74
    ky = ay_px / y_amp(100)
    kx = ax_px / A
    exag = ky / kx
    svg.line(ox - ax_px - 20, oy, ox + ax_px + 20, oy, P.black_20, 1)
    svg.line(ox, oy - 150, ox, oy + 150, P.black_20, 1)
    for rate, col, dash in ((50, P.lavender, None), (100, P.blue, None)):
        ya = y_amp(rate)
        pts_ = [(ox + kx * A * math.sin(2 * math.pi * i / 160), oy + ky * ya * math.cos(2 * math.pi * i / 160))
                for i in range(161)]
        svg.polyline(pts_, col, 3, **({"stroke_dasharray": dash} if dash else {}))
        # direction: at the middle of the stroke heading +x
        i0 = 0
        p, q = pts_[i0], pts_[i0 + 2]
        svg.triangle(*pts_[i0 + 1], 15, col, math.atan2(q[1] - p[1], q[0] - p[0]))
        svg.text(ox, oy + ky * ya + 22, f"{rate:+d} °/s · {abs(ya) * 1e9:.1f} nm", "code", 15, col, "middle")
    svg.line(ox - ax_px, oy, ox + ax_px, oy, P.black, 3)
    svg.text(ox + ax_px + 6, oy - 10, "0 °/s", "code", 15, P.black)
    axis_label(svg, ox, oy - ay_px - 20, "turn the other way: same ellipse, run backwards", anchor="middle", size=13)
    axis_label(svg, ox - ax_px - 20, oy - 170, f"path of the mass · sense drawn ×{exag:,.0f}".replace(",", " "))

    # time traces: sense peaks where the drive crosses zero
    x0, x1 = M + 130, W - M
    per = 1 / fd
    gx = lin(0, 3 * per, x0, x1)
    ts = [3 * per * i / 600 for i in range(601)]
    rows = [(878, "drive x", f"±{A * 1e6:.0f} µm", [math.sin(wd * t) for t in ts], P.black),
            (962, "sense y", f"±{y_amp(100) * 1e9:.1f} nm", [math.cos(wd * t) for t in ts], P.blue)]
    for k in range(7):
        svg.line(gx(k * per / 2), 836, gx(k * per / 2), 998, P.black_20, 1, stroke_dasharray="3 5")
    for yc, name, amp, vs, col in rows:
        svg.line(x0, yc, x1, yc, P.black_20, 1)
        trace(svg, ts, vs, gx, lambda v, yc=yc: yc - 32 * v, col, 3)
        svg.text(x0 - 16, yc - 2, name, "code", 15, col, "end")
        axis_label(svg, x0 - 16, yc + 16, amp, anchor="end", size=12)
    axis_label(svg, x1, 826, f"100 °/s · {per * 1e6:.0f} µs per cycle: sense peaks where the drive is fastest", anchor="end",
               size=12)

    svg.frame("coriolis.", "mems gyroscope · vibrating mass · coriolis force")
    brief(svg, "no room for a spinning wheel on a chip, and nothing in it turns",
          "keep a mass vibrating: rotation pushes it sideways, in step with its speed")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
x   = A * sin(wd*t)                  # drive: {A * 1e6:.0f} µm at {fd / 1e3:.0f} kHz, on resonance
a_c = -2 * Omega * A*wd * cos(wd*t)  # Coriolis: sideways, follows velocity
y   = a_c / (ws**2 - wd**2)          # sense mode 1 kHz up: {y_amp(100) * 1e9:.1f} nm at 100 °/s
rate = lowpass(y * cos(wd*t))        # demodulate on the drive velocity: Ω""", "py", 19)
    return svg


def sagnac() -> Svg:
    """Fibre-optic gyro: light both ways round a coil; rotation makes one way longer."""
    svg = Svg(P.black)
    L, D, lam = 1000.0, 0.10, 1550e-9
    K = 2 * math.pi * L * D / (lam * C)  # rad of phase per rad/s
    dphi_e = K * EARTH
    dL = dphi_e * lam / (2 * math.pi)
    dphi_n = K * 0.005 * DEG_H

    cx, cy = 290, 585
    for j in range(14):
        svg.circle(cx, cy, 146 + j * 2.4, "none", stroke=P.lavender, stroke_width=1.1, opacity="0.55")
    # clockwise (page) beam outside, counter-clockwise inside
    svg.arc(cx, cy, 200, math.radians(-160), math.radians(-30), P.lavender, 4)
    a = math.radians(-30)
    svg.triangle(cx + 200 * math.cos(a), cy + 200 * math.sin(a), 20, P.lavender, a + math.pi / 2)
    svg.arc(cx, cy, 116, math.radians(-30), math.radians(-150), P.teal_60, 4)
    a = math.radians(-150)
    svg.triangle(cx + 116 * math.cos(a), cy + 116 * math.sin(a), 18, P.teal_60, a - math.pi / 2)
    svg.text(cx + 150, cy - 196, "clockwise", "code", 15, P.lavender)
    svg.text(cx, cy - 78, "the other way", "code", 15, P.teal_60, "middle")
    svg.text(cx, cy + 14, "Ω", "code", 46, P.white, "middle")
    axis_label(svg, cx, cy + 44, f"{L / 1e3:.0f} km of fibre", True, "middle", 13)
    axis_label(svg, cx, cy + 62, f"on a {D * 100:.0f} cm coil", True, "middle", 13)
    # leads, modulator, coupler, source, detector
    yc = cy + 262
    for sx in (-1, 1):
        svg.polyline([(cx + sx * 20, cy + 178), (cx + sx * 20, yc - 20), (cx, yc - 6)], P.blue_40, 2)
    svg.rect(cx + 6, cy + 205, 30, 26, P.lavender, rx=3)
    svg.text(cx + 44, cy + 223, "phase mod", "codel", 13, P.blue_40)
    svg.rect(cx - 44, yc - 6, 88, 26, P.black_80, rx=4)
    svg.text(cx, yc + 12, "coupler", "codel", 13, P.white, "middle")
    for sx, name in ((-1, "laser 1550 nm"), (1, "detector")):
        bx = cx + sx * 150
        svg.polyline([(cx + sx * 44, yc + 7), (bx, yc + 7), (bx, yc + 52)], P.blue_40, 2)
        svg.rect(bx - 78, yc + 52, 156, 32, P.black_80, rx=4)
        svg.text(bx, yc + 73, name, "code", 14, P.white, "middle")

    # the fringe: I = ½(1 + cos Δφ), read at ±π/2
    x0, x1, y0, y1 = 590, W - M, 410, 650
    gx = lin(-1.6 * math.pi, 1.6 * math.pi, x0, x1)
    gy = lin(0, 1, y1, y0)
    svg.line(x0, y1, x1, y1, P.black_80, 1.5)
    ph = [-1.6 * math.pi + 3.2 * math.pi * i / 300 for i in range(301)]
    trace(svg, ph, [0.5 * (1 + math.cos(p)) for p in ph], gx, gy, P.white, 2.5)
    for v, lab in ((-math.pi, "−π"), (-math.pi / 2, "−π/2"), (0, "0"), (math.pi / 2, "π/2"), (math.pi, "π")):
        svg.line(gx(v), y1, gx(v), y1 + 6, P.blue_40, 1)
        axis_label(svg, gx(v), y1 + 24, lab, True, "middle", 13)
    shift = 0.28
    for side, col in ((-1, P.teal_60), (1, P.lavender)):
        p0 = side * math.pi / 2
        p1 = p0 + shift
        svg.circle(gx(p0), gy(0.5 * (1 + math.cos(p0))), 7, "none", stroke=col, stroke_width=2)
        svg.circle(gx(p1), gy(0.5 * (1 + math.cos(p1))), 7, col)
        svg.line(gx(p1), gy(0.5 * (1 + math.cos(p1))), gx(p1), y1, col, 1, stroke_dasharray="3 4")
    tag_y = gy(1) - 14
    axis_label(svg, gx(0), tag_y, "at rest the fringe is flat: no slope", True, "middle", 13)
    axis_label(svg, x1, y1 + 50, f"read at ±π/2, where it's steepest · shift drawn ×{shift / dphi_e:,.0f}".replace(",", " "),
               True, "end", 12)
    axis_label(svg, x0, y0 - 40, "detector: ½(1 + cos Δφ)", True)

    rows = [
        (f"Δφ = {K:.2f} rad per rad/s", "2π·L·D / (λ·c): more fibre, more phase"),
        (f"the Earth, 15.04 °/h: {dphi_e * 1e6:.0f} µrad", f"one beam goes {dL * 1e12:.0f} pm further"),
        (f"0.005 °/h: {dphi_n * 1e9:.0f} nrad", "what navigation grade has to see"),
        ("no moving parts", "ring laser gyros use the same effect"),
    ]
    for j, (a_, b_) in enumerate(rows):
        svg.text(x0, 760 + j * 58, a_, "code", 17, P.white)
        axis_label(svg, x0, 782 + j * 58, b_, True, size=13)

    svg.frame("sagnac.", "fibre-optic gyroscope · sagnac effect · interferometer", dark=True, title_fill=P.white)
    brief(svg, "a vibrating mass can't hold 0.01 °/h for hours; ships and aircraft need it",
          "send light both ways round 1 km of fibre: turning makes one way longer", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, f"""
dphi = 2*pi * L * D * Omega / (lam * c)   # {K:.2f} rad per rad/s
I = I0/2 * (1 + cos(dphi + mod))          # flat at 0: modulate to ±pi/2
rate = (I(+pi/2) - I(-pi/2)) / I0         # = sin(dphi): signed and steep
# the Earth's 15 °/h moves it {dphi_e * 1e6:.0f} µrad; light goes {dL * 1e12:.0f} pm further""", "py", 19, dark=True)
    return svg


# ============================================================================
# grade: what you get for the money
# ============================================================================
GRADES = [  # name, gyro bias (°/h) range, price ($) range, uses, technology, accel bias (m/s²) for coast.
    ("consumer", (5, 50), (0.5, 5), "phones, watches, toys", "MEMS", 0.03),
    ("industrial", (0.8, 5), (100, 2000), "drones, robots, cars", "MEMS", 0.005),
    ("tactical", (0.05, 1), (5e3, 4e4), "UAVs, survey, guidance", "MEMS · FOG", 0.001),
    ("navigation", (0.002, 0.01), (5e4, 2e5), "aircraft, ships", "RLG · FOG", 3e-4),
    ("strategic", (5e-5, 5e-4), (5e5, 3e6), "submarines, spacecraft", "RLG · FOG · HRG", 1e-5),
]
GRADE_COL = [P.black_60, P.teal, P.lavender, P.blue, P.black]


def grades() -> Svg:
    """Gyro bias against price: five grades, six orders of magnitude each way."""
    svg = Svg(P.white)
    x0, x1, y0, y1 = M + 74, W - M - 118, ART_TOP + 50, 975
    gx = logm(0.1, 1e7, x0, x1)
    gy = logm(1e-5, 100, y0, y1)
    for b in (100, 10, 1, 0.1, 0.01, 1e-3, 1e-4, 1e-5):
        svg.line(x0, gy(b), x1, gy(b), P.black_20, 1)
        axis_label(svg, x0 - 12, gy(b) + 5, f"{b:.5f}".rstrip("0").rstrip(".") if b < 1 else f"{b:g}", anchor="end", size=13)
    for p, lab in ((0.1, "10¢"), (1, "$1"), (10, "$10"), (100, "$100"), (1e3, "$1k"), (1e4, "$10k"), (1e5, "$100k"),
                   (1e6, "$1M"), (1e7, "$10M")):
        svg.line(gx(p), y0, gx(p), y1, P.black_20, 1)
        axis_label(svg, gx(p), y1 + 24, lab, anchor="middle", size=13)
    axis_label(svg, x0 - 12, y0 - 18, "gyro bias instability, °/h · better ↑")
    axis_label(svg, x1, y1 + 48, "price of the IMU, order of magnitude", anchor="end")
    # the Earth's rate
    e = EARTH / DEG_H
    svg.line(x0, gy(e), x1, gy(e), P.blue, 1.5, stroke_dasharray="6 6")
    svg.text(x1 - 6, gy(e) - 10, f"the Earth turns {e:.2f} °/h", "code", 14, P.blue, "end")
    # right axis: heading from gyrocompassing at 52.5° N
    cl = math.cos(math.radians(LAT))
    svg.line(x1 + 10, y0, x1 + 10, y1, P.black_20, 1)
    for b in (1, 0.1, 0.01, 1e-3, 1e-4):
        psi = math.degrees(b / (e * cl))
        svg.line(x1 + 10, gy(b), x1 + 18, gy(b), P.black_60, 1)
        axis_label(svg, x1 + 24, gy(b) + 5, f"{psi:.2g}°", size=13)
    axis_label(svg, x1 + 10, y0 - 34, "north, alone", size=13)
    axis_label(svg, x1 + 10, y0 - 18, f"to ±, at {LAT}° N", size=13)
    for (name, (b0, b1), (p0, p1), uses, tech, _), col in zip(GRADES, GRADE_COL):
        rx0, rx1, ry0, ry1 = gx(p0), gx(p1), gy(b0), gy(b1)
        svg.rect(rx0, ry0, rx1 - rx0, ry1 - ry0, col, rx=8, opacity="0.88")
        right = name in ("consumer", "industrial", "tactical")
        tx = rx1 + 14 if right else rx0 - 14
        an = "start" if right else "end"
        ym = (ry0 + ry1) / 2
        svg.text(tx, ym - 8, name, "code", 18, col if col != P.black_60 else P.black, an)
        axis_label(svg, tx, ym + 12, uses, anchor=an, size=13)
        axis_label(svg, tx, ym + 29, tech, anchor=an, size=13)

    svg.frame("grades.", "imu grades · bias instability vs price · consumer to strategic")
    brief(svg, "gyro bias spans six orders of magnitude, and so does the price",
          "buy the grade for how long it must go without a fix (see coast.)")
    code_rule(svg)
    svg.code(M, CODE_Y, """
grades = {"consumer": (15, 2), "industrial": (2, 500), "tactical": (0.2, 15e3),
          "navigation": (0.005, 1e5), "strategic": (2e-4, 1e6)}   # (°/h, $)
north_err = bias / (earth_rate * cos(lat))   # gyrocompass: 0.005 °/h -> 0.03°
# below 15 °/h a gyro can feel the Earth turn; below ~0.01 it finds north alone""", "py", 18)
    return svg


def _coast_err(t, b_a, b_g_dph):
    b_g = b_g_dph * DEG_H
    p_acc = b_a / W_S ** 2 * (1 - math.cos(W_S * t))
    p_gyro = b_g * R_E * (t - math.sin(W_S * t) / W_S)
    return math.hypot(p_acc, p_gyro)


def coast() -> Svg:
    """Unaided position error for each grade: t², then t³, bent by the 84-minute Schuler loop."""
    svg = Svg(P.cream)
    x0, x1, y0, y1 = M + 74, W - M - 130, ART_TOP + 50, 975
    t0, t1 = 1, 36000
    gx = logm(t0, t1, x0, x1)
    gy = logm(1e7, 0.01, y0, y1)
    for v, lab in ((1e7, "10 000 km"), (1e5, "100 km"), (1e3, "1 km"), (10, "10 m"), (0.1, "10 cm")):
        svg.line(x0, gy(v), x1, gy(v), P.black_20, 1)
        axis_label(svg, x0 - 12, gy(v) + 5, lab, anchor="end", size=13)
    for t, lab in ((1, "1 s"), (10, "10 s"), (60, "1 min"), (600, "10 min"), (3600, "1 h"), (36000, "10 h")):
        svg.line(gx(t), y0, gx(t), y1, P.black_20, 1)
        axis_label(svg, gx(t), y1 + 24, lab, anchor="middle", size=13)
    schuler = 2 * math.pi / W_S
    svg.line(gx(schuler), y0, gx(schuler), y1, P.black_60, 1, stroke_dasharray="4 6")
    axis_label(svg, gx(schuler) + 8, y1 - 12, f"Schuler: {schuler / 60:.1f} min", size=12)
    svg.line(x0, gy(10), x1, gy(10), P.blue, 1.5, stroke_dasharray="6 6")
    axis_label(svg, x0 - 12, y0 - 18, "horizontal position error, no fix · bias only")
    axis_label(svg, x0 + 20, y0 + 40 + 5 * 26 + 4, "dots: where each crosses 10 m", size=13)
    ts = [t0 * (t1 / t0) ** (i / 400) for i in range(401)]
    svg.clip_begin(x0, y0, x1 - x0, y1 - y0)
    ends, crosses = [], []
    for (name, (b0, b1), _, _, _, b_a), col in zip(GRADES, GRADE_COL):
        b_g = math.sqrt(b0 * b1)
        es = [max(_coast_err(t, b_a, b_g), 1e-3) for t in ts]
        trace(svg, ts, es, gx, gy, col, 3.5)
        tc = next((t for t, e_ in zip(ts, es) if e_ >= 10), None)
        crosses.append((name, tc, col))
        ends.append((name, es[-1], col))
    svg.clip_end()
    for name, tc, col in crosses:
        if tc:
            svg.circle(gx(tc), gy(10), 7, col, stroke=P.cream, stroke_width=2)
    # labels at the right end, nudged apart
    ys = []
    for name, e_, col in sorted(ends, key=lambda r: -r[1]):
        y = gy(min(e_, 1e7))
        if ys and y < ys[-1] + 44:
            y = ys[-1] + 44
        ys.append(y)
        svg.text(x1 + 12, y - 2, name, "code", 15, col if col != P.black_60 else P.black)
        lab = "> 10 000 km" if e_ > 1e7 else f"{e_ / 1e3:,.0f} km".replace(",", " ") if e_ >= 1e3 else f"{e_:.0f} m"
        axis_label(svg, x1 + 12, y + 15, f"{lab} at 10 h", size=12)
    # crossing times as a list
    for j, (name, tc, col) in enumerate(crosses):
        lab = f"{tc:.0f} s" if tc < 120 else f"{tc / 60:.0f} min" if tc < 7200 else f"{tc / 3600:.1f} h"
        svg.text(x0 + 20, y0 + 40 + j * 26, f"{name:<11} 10 m in {lab}", "code", 16,
                 col if col != P.black_60 else P.black)

    def fmt_t(tc):
        return f"{tc:.0f} s" if tc < 120 else f"{tc / 60:.0f} min"

    svg.frame("coast.", "inertial navigation · unaided drift · schuler loop")
    brief(svg, "with no fix the error grows as t², then t³; only a reset stops it",
          f"the grade buys time: 10 m in {fmt_t(crosses[0][1])} for a phone, {fmt_t(crosses[3][1])} for an airliner")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
ws = sqrt(g / R)                         # Schuler: the INS is an {schuler / 60:.0f}-min pendulum
p_acc  = b_a / ws**2 * (1 - cos(ws*t))   # ≈ ½·b_a·t² at first, then it swings
p_gyro = b_g * R * (t - sin(ws*t) / ws)  # ≈ g·b_g·t³/6 at first, then R·b_g·t
err = hypot(p_acc, p_gyro)               # bias only: the best case""", "py", 19)
    return svg


def allan() -> Svg:
    """Allan deviation of 2 h of simulated gyro at rest: white noise, bias instability, rate random walk."""
    svg = Svg(P.black)
    rng = random.Random(11)
    fs, T = 50, 2 * 3600
    n = fs * T
    dt = 1 / fs
    N_arw = 0.25  # °/√h
    sig_w = 60 * N_arw * math.sqrt(fs)  # °/h per sample
    gm = [(tau, 1.1) for tau in (15, 150, 1500)]  # Gauss-Markov bank ≈ flicker
    K_rrw = 0.045  # (°/h)/√s
    states = [0.0] * len(gm)
    coef = [(math.exp(-dt / tau), s * math.sqrt(1 - math.exp(-2 * dt / tau))) for tau, s in gm]
    rrw = 0.0
    w = [0.0] * n
    for i in range(n):
        for j, (a, b) in enumerate(coef):
            states[j] = a * states[j] + b * rng.gauss(0, 1)
        rrw += K_rrw * math.sqrt(dt) * rng.gauss(0, 1)
        w[i] = 3.0 + sig_w * rng.gauss(0, 1) + sum(states) + rrw
    theta = [0.0] * (n + 1)
    for i in range(n):
        theta[i + 1] = theta[i] + w[i] * dt
    ms = sorted({max(1, round(10 ** (e / 8))) for e in range(0, int(8 * math.log10(n / 6)) + 1)})
    taus, adev = [], []
    for m in ms:
        step = max(1, m // 8)
        s, cnt = 0.0, 0
        for k in range(0, n + 1 - 2 * m, step):
            d = theta[k + 2 * m] - 2 * theta[k + m] + theta[k]
            s += d * d
            cnt += 1
        tau = m * dt
        taus.append(tau)
        adev.append(math.sqrt(s / cnt / (2 * tau * tau)))
    i1 = min(range(len(taus)), key=lambda i: abs(math.log(taus[i])))
    N_est = adev[i1] * math.sqrt(taus[i1]) / 60
    imin = min(range(len(adev)), key=lambda i: adev[i])
    B_est = adev[imin] / 0.664

    # raw strip: 2 h at rest
    sx0, sx1, sy0, sy1 = M + 74, W - M, 380, 470
    per = fs * 10
    avg = [sum(w[i:i + per]) / per for i in range(0, n, per)]
    gxs = lin(0, T, sx0, sx1)
    lo_, hi_ = min(avg), max(avg)
    gys = lin(lo_ - 0.3, hi_ + 0.3, sy1, sy0)
    trace(svg, [i * 10 for i in range(len(avg))], avg, gxs, gys, P.teal_60, 1.5)
    axis_label(svg, sx0 - 12, sy0 + 6, "rate", True, "end", 12)
    axis_label(svg, sx0 - 12, sy0 + 22, "10 s avg", True, "end", 12)
    axis_label(svg, sx1, sy1 + 22, f"2 h on the bench, not moving · raw samples ±{sig_w:.0f} °/h at {fs} Hz", True, "end",
               12)

    x0, x1, y0, y1 = M + 74, W - M, 540, 975
    gx = logm(0.02, 1000, x0, x1)
    gy = logm(300, 0.3, y0, y1)
    for v in (100, 10, 1):
        svg.line(x0, gy(v), x1, gy(v), P.black_80, 1)
        axis_label(svg, x0 - 12, gy(v) + 5, f"{v:g}", True, "end", 13)
    for t, lab in ((0.1, "0.1 s"), (1, "1 s"), (10, "10 s"), (100, "100 s"), (1000, "1000 s")):
        svg.line(gx(t), y0, gx(t), y1, P.black_80, 1)
        axis_label(svg, gx(t), y1 + 24, lab, True, "middle", 13)
    axis_label(svg, x0 - 12, y0 - 16, "Allan deviation, °/h", True)
    axis_label(svg, x1, y1 + 48, "averaging time τ", True, "end")
    svg.clip_begin(x0, y0, x1 - x0, y1 - y0)
    # reference slopes
    svg.polyline([(gx(t), gy(60 * N_est / math.sqrt(t))) for t in (0.02, 400)], P.teal_60, 1.5, stroke_dasharray="6 6")
    svg.line(x0, gy(adev[imin]), x1, gy(adev[imin]), P.white, 1.2, stroke_dasharray="6 6")
    k_end = adev[-1] / math.sqrt(taus[-1] / 3)
    svg.polyline([(gx(t), gy(k_end * math.sqrt(t / 3))) for t in (150, 1000)], P.blue_60, 1.5, stroke_dasharray="6 6")
    svg.clip_end()
    trace(svg, taus, adev, gx, gy, P.lavender, 3.5)
    for t, a in zip(taus, adev):
        svg.circle(gx(t), gy(a), 3.5, P.lavender)
    svg.circle(gx(taus[i1]), gy(adev[i1]), 8, "none", stroke=P.teal_60, stroke_width=2.5)
    svg.circle(gx(taus[imin]), gy(adev[imin]), 8, "none", stroke=P.white, stroke_width=2.5)
    svg.text(gx(0.04), gy(11), "slope −½: white noise", "code", 15, P.teal_60)
    axis_label(svg, gx(0.04), gy(11) + 19, "angle random walk", True, size=13)
    svg.text(gx(taus[imin]), gy(adev[imin]) + 46, "flat: bias instability", "code", 15, P.white, "middle")
    svg.text(x1 - 4, gy(adev[-1]) - 34, "+½: rate random walk", "code", 15, P.blue_60, "end")
    tx = gx(2)
    svg.text(tx + 20, y0 + 40, f"ARW = σ(1 s) / 60 = {N_est:.2f} °/√h", "code", 16, P.teal_60)
    svg.text(tx + 20, y0 + 66, f"bias instability = floor / 0.664 = {B_est:.1f} °/h", "code", 16, P.white)
    axis_label(svg, tx + 20, y0 + 88, f"floor at τ ≈ {taus[imin]:.0f} s: averaging longer stops helping", True, size=13)

    svg.frame("allan.", "gyro noise · allan deviation · ARW, bias instability, RRW", dark=True, title_fill=P.white)
    brief(svg, "one 'noise' number can't describe a gyro: hiss, wander and walk all mix",
          "average over longer and longer windows: each kind of noise has its own slope", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
theta = cumsum(gyro) * dt                  # 2 h at rest, 50 Hz
for m in taus:                             # clusters of m samples: tau = m*dt
    d = theta[2*m:] - 2*theta[m:-m] + theta[:-2*m]
    adev[m] = sqrt(mean(d**2) / (2 * (m*dt)**2))
N, B = adev_at(1.0) / 60, min(adev) / 0.664   # °/√h and °/h: the datasheet""", "py", 18, dark=True)
    return svg


# ============================================================================
# drift: why it walks away
# ============================================================================
def integrate() -> Svg:
    """A phone lying still: acceleration with a 2 mg bias, integrated once and twice."""
    svg = Svg(P.white)
    rng = random.Random(3)
    fs, T, b = 100, 60.0, 0.02
    nd = 300e-6 * G  # noise density, m/s²/√Hz
    sig = nd * math.sqrt(fs / 2)
    n = int(T * fs)
    dt = 1 / fs
    ts = [i * dt for i in range(n + 1)]
    noise = [rng.gauss(0, sig) for _ in range(n + 1)]
    a_b = [b + e for e in noise]
    a_n = noise
    v_b, v_n, p_b, p_n = [0.0], [0.0], [0.0], [0.0]
    sig_p = nd * math.sqrt(T ** 3 / 6)  # 1σ position from white noise alone
    for i in range(n):
        v_b.append(v_b[-1] + a_b[i] * dt)
        v_n.append(v_n[-1] + a_n[i] * dt)
        p_b.append(p_b[-1] + v_b[-1] * dt)
        p_n.append(p_n[-1] + v_n[-1] * dt)
    x0, x1 = M + 90, W - M - 110
    gx = lin(0, T, x0, x1)
    panels = [
        (380, 520, -0.08, 0.1, "acceleration", "m/s²", a_b, a_n, (-0.05, 0, 0.05), lambda v: f"{v:g}"),
        (585, 760, -0.4, 1.4, "velocity", "m/s", v_b, v_n, (0, 0.5, 1.0), lambda v: f"{v:g}"),
        (825, 990, -4, 40, "position", "m", p_b, p_n, (0, 10, 20, 30), lambda v: f"{v:g}"),
    ]
    for k, (y0, y1, lo, hi, name, unit, yb, yn, ticks, fmt) in enumerate(panels):
        gy = lin(lo, hi, y1, y0)
        hlines(svg, x0, x1, ticks, gy, fmt, zero=0)
        svg.text(x0, y0 - 10, name, "code", 16, P.black)
        axis_label(svg, x0 + 10 * len(name) + 12, y0 - 10, unit, size=13)
        if k == 0:
            trace(svg, ts, yb, gx, gy, P.blue_40, 1, step=2)
            svg.line(x0, gy(b), x1, gy(b), P.blue, 2.5, stroke_dasharray="8 6")
            svg.text(x1 + 12, gy(b) + 5, "2 mg bias", "code", 14, P.blue)
            svg.text(x1 + 12, gy(-0.05) + 5, "noise", "code", 14, P.blue_40)
        else:
            trace(svg, ts, yn, gx, gy, P.teal, 2.5, step=5)
            trace(svg, ts, yb, gx, gy, P.blue, 3.5, step=5)
            svg.text(x1 + 12, gy(yb[-1]) + 5, f"{yb[-1]:.1f} {unit}" if k == 2 else f"{yb[-1]:.2f}", "code", 15, P.blue)
            svg.text(x1 + 12, gy(yn[-1]) + (5 if k == 1 else 14), f"±{sig_p:.1f} m" if k == 2 else f"{yn[-1]:+.2f}", "code",
                     15, P.teal)
        svg.line(x0, gy(0), x1, gy(0), P.black, 1.5)
    xticks(svg, (0, 10, 20, 30, 40, 50, 60), gx, 1012, lambda v: f"{v} s")
    gyp = lin(-4, 40, 990, 825)
    axis_label(svg, x1, 362, "truth: 0 in every panel. the phone never moved", anchor="end", size=13)
    svg.text(gx(36), gyp(p_b[3600]) - 18, "with the bias", "code", 15, P.blue, "end")
    svg.text(gx(59), gyp(0) - 12, f"bias removed: noise alone, ±{sig_p:.1f} m (1σ)", "code", 15, P.teal, "end")

    svg.frame("integrate.", "dead reckoning · double integration · a phone on a table")
    brief(svg, f"a phone on a table with 2 mg of bias, integrated twice: {p_b[-1]:.0f} m in a minute",
          f"measure the bias while it's still, subtract it: noise alone gives ±{sig_p:.1f} m")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
v += a * dt                        # bias b: v = b·t
p += v * dt                        # p = ½·b·t² = {0.5 * b * T * T:.0f} m after {T:.0f} s
b_hat = mean(a[still])             # learn it at rest (and again whenever it's still)
# what's left is noise: p ~ n·t^1.5, smaller, but it still needs a reset""", "py", 19)
    return svg


def leak() -> Svg:
    """A small tilt error leaves part of gravity behind as a fake horizontal acceleration."""
    svg = Svg(P.cream)
    # vector triangle, tilt drawn large
    d_draw = math.radians(12)
    ox, oy, Lv = 270, 740, 320
    # IMU block, tilted
    svg.add(f'<g transform="translate({ox} {oy}) rotate({math.degrees(d_draw):.2f})">')
    svg.rect(-44, -28, 88, 56, P.black, rx=8)
    svg.text(0, 6, "IMU", "code", 16, P.cream, "middle")
    svg.add("</g>")
    top = (ox, oy - Lv)
    arrow(svg, (ox, oy - 36), top, P.black, 4, 20)
    svg.text(ox - 14, oy - Lv * 0.6, "measured", "code", 16, P.black, "end")
    axis_label(svg, ox - 14, oy - Lv * 0.6 + 20, "+9.81 up", anchor="end", size=13)
    end = (ox + Lv * math.sin(d_draw), oy - Lv + Lv * math.cos(d_draw))
    arrow(svg, top, end, P.blue, 4, 20)
    svg.text(end[0] + 12, oy - Lv * 0.5, "gravity it subtracts", "code", 16, P.blue)
    axis_label(svg, end[0] + 12, oy - Lv * 0.5 + 20, "along its idea of down", size=13)
    arrow(svg, (ox, oy - 4), (end[0] + 2, end[1] + 2), P.lavender, 5, 18)
    svg.text(ox + 4, oy + 60, "left over: g·sin δθ", "code", 16, P.lavender, "middle")
    svg.arc(*top, 64, math.pi / 2, math.pi / 2 - d_draw, P.black_60, 1.5)
    svg.text(top[0] + 18, top[1] + 90, "δθ", "code", 16, P.black_60)
    axis_label(svg, M, ART_TOP + 46, "tilt drawn ×12", size=13)

    # error growth
    x0, x1, y0, y1 = 590, W - M - 70, 400, 780
    T = 60
    gx = lin(0, T, x0, x1)
    gy = lin(0, 330, y1, y0)
    hlines(svg, x0, x1, (0, 100, 200, 300), gy, lambda v: f"{v} m")
    xticks(svg, (0, 20, 40, 60), gx, y1 + 22, lambda v: f"{v} s")
    rows = [(1.0, P.blue), (0.3, P.teal), (0.1, P.lavender), (math.degrees(math.asin(0.001)), P.black_60)]
    ts = [T * i / 120 for i in range(121)]
    for dd, col in rows:
        a = G * math.sin(math.radians(dd))
        trace(svg, ts, [0.5 * a * t * t for t in ts], gx, gy, col, 3)
        lab_y = gy(0.5 * a * T * T) + 5
        if dd < 0.06:
            lab_y += 10
        elif dd < 0.2:
            lab_y -= 6
        svg.text(x1 + 10, lab_y, "1 mg" if dd < 0.06 else f"{dd:g}°", "code", 15, col)
    axis_label(svg, x0 - 12, y0 - 18, "position error from tilt alone")
    a1 = G * math.sin(math.radians(1))

    # the table
    ty = 850
    cols_x = (M, M + 220, M + 440, M + 680)
    for x, h in zip(cols_x, ("tilt error", "leftover", "after 10 s", "after 60 s")):
        axis_label(svg, x, ty, h, size=13)
    for j, (dd, col) in enumerate(rows):
        a = G * math.sin(math.radians(dd))
        y = ty + 32 + j * 30
        vals = (f"{dd:.2g}°", f"{a / G * 1e3:.1f} mg", f"{0.5 * a * 100:.1f} m", f"{0.5 * a * 3600:.0f} m")
        for x, v in zip(cols_x, vals):
            svg.text(x, y, v, "code", 17, col)
    axis_label(svg, W - M, ty + 32 + 3 * 30 + 26, "0.057° of tilt = 1 mg: the bias of a good MEMS accelerometer",
               anchor="end", size=13)

    svg.frame("leak.", "attitude error · gravity leakage · specific force")
    brief(svg, f"to find motion it subtracts gravity; a 1° tilt error leaves {a1:.2f} m/s² behind",
          "get attitude right first: 0.057° of tilt costs as much as 1 mg of bias")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
f = imu.accel                           # specific force: +9.81 up, at rest
a = R_hat @ f - [0, 0, 9.81]            # R_hat tilted by d_theta...
# ...leaves g*sin(d_theta) sideways: 1° -> {a1:.3f} m/s²
p_err = 0.5 * g * sin(d_theta) * t**2   # {0.5 * a1 * 3600:.0f} m after a minute""", "py", 19)
    return svg


def warm() -> Svg:
    """Gyro bias against temperature: the warm-up drift, a chamber sweep, a cubic fit and the hysteresis left over."""
    svg = Svg(P.white)
    rng = random.Random(8)

    def b_of(T):
        x = T - 25
        return 0.1 + 0.02 * x + 0.0004 * x * x - 6e-6 * x ** 3

    # warm-up after power-on
    x0, x1 = M + 90, W - M - 90
    tw = [i / 6 for i in range(0, 121)]  # minutes, every 10 s
    temp = [25 + 13 * (1 - math.exp(-t / 4)) for t in tw]
    bw = [b_of(T) + rng.gauss(0, 0.008) for T in temp]
    y0, y1 = 380, 580
    gx = lin(0, 20, x0, x1)
    gyb = lin(0, 0.5, y1, y0)
    gyt = lin(20, 40, y1, y0)
    hlines(svg, x0, x1, (0, 0.2, 0.4), gyb, lambda v: f"{v:g}")
    for T in (25, 30, 35, 40):
        axis_label(svg, x1 + 12, gyt(T) + 5, f"{T} °C", size=12)
    trace(svg, tw, temp, gx, gyt, P.teal, 2.5)
    trace(svg, tw, bw, gx, gyb, P.blue, 2.5)
    xticks(svg, (0, 5, 10, 15, 20), gx, y1 + 22, lambda v: f"{v} min")
    svg.text(x0, y0 - 14, "power on, sitting still", "code", 16, P.black)
    axis_label(svg, x0 + 252, y0 - 14, "gyro bias °/s (blue) · board temperature (teal)", size=12)
    drift = (bw[-1] - bw[0])
    svg.text(gx(20) - 6, gyb(bw[-1]) + 30, f"+{drift:.2f} °/s = {drift * 60:.0f}° a minute of heading", "code", 15, P.blue,
             "end")

    # chamber sweep: -20 -> 70 -> -20 °C at 1 °C/min, a sample every 6 s
    Ts, bs, dirs = [], [], []
    hyst = 0.0
    for i in range(1800):
        tmin = i / 10
        T = -20 + 90 * (tmin / 90) if tmin <= 90 else 70 - 90 * ((tmin - 90) / 90)
        dirn = 1 if tmin <= 90 else -1
        hyst += (0.03 * dirn - hyst) * 0.02
        Ts.append(T)
        bs.append(b_of(T) + hyst + rng.gauss(0, 0.01))
        dirs.append(dirn)
    X = [[1, (T - 25) / 45, ((T - 25) / 45) ** 2, ((T - 25) / 45) ** 3] for T in Ts]
    th = lstsq(X, [[b] for b in bs])
    fit = lambda T: sum(th[k][0] * ((T - 25) / 45) ** k for k in range(4))  # noqa: E731
    res = [b - fit(T) for T, b in zip(Ts, bs)]
    span = max(bs) - min(bs)
    r95 = sorted(abs(r) for r in res)[int(0.95 * len(res))]
    y0, y1 = 660, 870
    gx2 = lin(-20, 70, x0, x1)
    lo, hi = min(bs) - 0.05, max(bs) + 0.05
    gy2 = lin(lo, hi, y1, y0)
    hlines(svg, x0, x1, [v / 10 for v in range(math.ceil(lo * 10 / 3) * 3, int(hi * 10) + 1, 3)], gy2, lambda v: f"{v:g}")
    for T, b, dr in zip(Ts[::3], bs[::3], dirs[::3]):
        svg.circle(gx2(T), gy2(b), 1.8, P.lavender if dr > 0 else P.blue_60)
    tf = [-20 + 90 * i / 100 for i in range(101)]
    trace(svg, tf, [fit(T) for T in tf], gx2, gy2, P.black, 2.5)
    svg.text(x0, y0 - 14, "chamber sweep, −20 → 70 → −20 °C", "code", 16, P.black)
    svg.text(gx2(64), gy2(fit(64)) - 24, "cubic fit", "code", 15, P.black, "end")
    svg.circle(gx2(48), y1 - 44, 4, P.lavender)
    svg.text(gx2(48) + 12, y1 - 39, "heating", "code", 14, P.lavender)
    svg.circle(gx2(48), y1 - 20, 4, P.blue_60)
    svg.text(gx2(48) + 12, y1 - 15, "cooling", "code", 14, P.blue_60)
    # residual strip
    y3, y4 = 910, 990
    gy3 = lin(-0.1, 0.1, y4, y3)
    svg.line(x0, gy3(0), x1, gy3(0), P.black_60, 1)
    for T, r, dr in zip(Ts[::3], res[::3], dirs[::3]):
        svg.circle(gx2(T), gy3(r), 1.6, P.lavender if dr > 0 else P.blue_60)
    axis_label(svg, x0 - 12, gy3(0) + 5, "after", anchor="end", size=12)
    xticks(svg, (-20, 0, 25, 50, 70), gx2, y4 + 22, lambda v: f"{v} °C")
    svg.text(x1 + 12, gy3(0) - 4, f"±{r95:.2f}", "code", 15, P.blue)
    axis_label(svg, x1 + 12, gy3(0) + 14, "°/s, 95 %", size=12)
    axis_label(svg, x1 - 4, y3 - 8, "what's left is the loop: it depends on which way the temperature went", anchor="end",
               size=12)

    svg.frame("warm.", "temperature · gyro bias drift · thermal calibration")
    brief(svg, f"the bias moves with temperature: {span:.1f} °/s over the range, {drift:.1f} just warming up",
          "sweep it in a chamber, fit bias(T), subtract it live: the hysteresis is what's left")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
x = (T - 25) / 45                              # chip temperature, normalised
coef = lstsq([1, x, x**2, x**3], bias)         # fit once, store in flash
gyro -= poly(coef, x)                          # {span:.1f} °/s -> ±{r95:.2f} °/s
# then let the filter track what's left (see bias.)""", "py", 19)
    return svg


# ============================================================================
# fuse: other sensors keep it honest
# ============================================================================
def bias() -> Svg:
    """A two-state Kalman filter (angle, gyro bias): the accelerometer, noisy but unbiased, teaches it the bias."""
    svg = Svg(P.black)
    rng = random.Random(21)
    dt, T, b_true, sg, sa = 0.01, 40.0, 0.6, 0.3, 4.0
    n = int(T / dt)
    ts = [i * dt for i in range(n + 1)]
    th_t = [20 * math.sin(0.4 * t) + 8 * math.sin(1.3 * t) for t in ts]
    w_t = [20 * 0.4 * math.cos(0.4 * t) + 8 * 1.3 * math.cos(1.3 * t) for t in ts]
    th_hat, b_hat = 0.0, 0.0
    P00, P01, P10, P11 = 25.0, 0.0, 0.0, 1.0
    q_th, q_b, R = (sg * dt) ** 2, 1e-7, sa * sa
    th_g, acc, est, bh, bsd = 0.0, [], [], [], []
    gyro_only = []
    for i in range(n + 1):
        w_m = w_t[i] + b_true + rng.gauss(0, sg)
        z = th_t[i] + rng.gauss(0, sa)
        if i:
            th_g += w_m * dt
            th_hat += (w_m - b_hat) * dt
            p00 = P00 - dt * (P10 + P01) + dt * dt * P11 + q_th
            p01, p10, p11 = P01 - dt * P11, P10 - dt * P11, P11 + q_b
            S = p00 + R
            K0, K1 = p00 / S, p10 / S
            e = z - th_hat
            th_hat += K0 * e
            b_hat += K1 * e
            P00, P01, P10, P11 = (1 - K0) * p00, (1 - K0) * p01, p10 - K1 * p00, p11 - K1 * p01
        acc.append(z)
        est.append(th_hat)
        gyro_only.append(th_g)
        bh.append(b_hat)
        bsd.append(math.sqrt(max(P11, 0)))
    conv = next(ts[i] for i in range(n + 1) if all(abs(b - b_true) < 0.05 for b in bh[i:]))

    def rms(xs, ys, t0=20):
        k = int(t0 / dt)
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(xs[k:], ys[k:])) / len(xs[k:]))

    x0, x1 = M + 70, W - M - 120
    gx = lin(0, T, x0, x1)
    y0, y1 = 390, 720
    gy = lin(-40, 60, y1, y0)
    hlines(svg, x0, x1, (-30, 0, 30), gy, lambda v: f"{v}°", True)
    for i in range(0, n + 1, 6):
        svg.circle(gx(ts[i]), gy(acc[i]), 1.5, P.blue_60, opacity="0.7")
    trace(svg, ts, th_t, gx, gy, P.white, 1.5, step=4)
    trace(svg, ts, gyro_only, gx, gy, P.lavender, 3, step=4)
    trace(svg, ts, est, gx, gy, P.teal_60, 3, step=4)
    svg.text(x1 + 12, gy(gyro_only[-1]) + 5, "gyro only", "code", 15, P.lavender)
    axis_label(svg, x1 + 12, gy(gyro_only[-1]) + 23, f"{rms(gyro_only, th_t):.0f}° rms", True, size=12)
    svg.text(x1 + 12, gy(est[-1]) - 6, "filter", "code", 15, P.teal_60)
    axis_label(svg, x1 + 12, gy(est[-1]) + 12, f"{rms(est, th_t):.1f}° rms", True, size=12)
    svg.text(x1 + 12, gy(-34), "accel tilt", "code", 15, P.blue_60)
    axis_label(svg, x1 + 12, gy(-34) + 18, f"{rms(acc, th_t):.0f}° rms", True, size=12)
    axis_label(svg, x0, y0 - 14, "tilt angle · white: the truth", True)

    y2, y3 = 790, 975
    gyb = lin(-0.2, 1.0, y3, y2)
    hlines(svg, x0, x1, (0, 0.5, 1.0), gyb, lambda v: f"{v:g}", True)
    band = [(gx(t), gyb(min(b + 2 * s_, 1.0))) for t, b, s_ in zip(ts[::10], bh[::10], bsd[::10])]
    band += [(gx(t), gyb(max(b - 2 * s_, -0.2))) for t, b, s_ in reversed(list(zip(ts[::10], bh[::10], bsd[::10])))]
    svg.clip_begin(x0, y2, x1 - x0, y3 - y2)
    svg.poly(band, P.teal, opacity="0.35")
    svg.line(x0, gyb(b_true), x1, gyb(b_true), P.white, 1.5, stroke_dasharray="6 6")
    trace(svg, ts, bh, gx, gyb, P.teal_60, 3, step=4)
    svg.clip_end()
    svg.line(gx(conv), y2, gx(conv), y3, P.white, 1, stroke_dasharray="3 5")
    svg.text(gx(conv) + 10, y2 + 16, f"within 0.05 °/s after {conv:.0f} s", "code", 15, P.white)
    svg.text(x1 + 12, gyb(b_true) + 5, f"{b_true} °/s", "code", 15, P.white)
    axis_label(svg, x1 + 12, gyb(b_true) + 23, "true bias", True, size=12)
    axis_label(svg, x0, y2 - 14, "bias estimate, °/s, ±2σ", True)
    xticks(svg, (0, 10, 20, 30, 40), gx, y3 + 22, lambda v: f"{v} s", True)

    svg.frame("bias.", "sensor fusion · kalman filter · gyro bias as a state", dark=True, title_fill=P.white)
    brief(svg, "a gyro's bias integrates into an angle that walks away, and it's new every power-on",
          "put the bias in the state: the noisy but unbiased accelerometer teaches it", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
x = [theta, b];  F = [[1, -dt], [0, 1]]      # the bias is part of the state
x = F @ x + [gyro*dt, 0];  P = F@P@F.T + Q   # predict with the gyro
K = P @ H.T / (H@P@H.T + R);  H = [1, 0]     # correct with the accel tilt
x += K * (atan2(ay, az) - x[0])              # b is learned through theta""", "py", 18, dark=True)
    return svg


def yaw() -> Svg:
    """Gravity pins roll and pitch, not heading: the accelerometer reads the same at every yaw."""
    svg = Svg(P.white)
    rng = random.Random(5)
    H_, Z_ = 18.5, 46.0  # µT: horizontal and down components, central Europe
    for j, psi in enumerate((0, 120, 240)):
        cx, cy = 230 + j * 310, 500
        svg.add(f'<g transform="translate({cx} {cy}) rotate({psi})">')
        svg.rect(-46, -70, 92, 140, P.black, rx=14)
        svg.circle(0, -48, 6, P.teal)
        svg.add("</g>")
        a = math.radians(psi - 90)
        arrow(svg, (cx, cy), (cx + 105 * math.cos(a), cy + 105 * math.sin(a)), P.blue, 3, 16)
        svg.circle(cx, cy, 11, P.white, stroke=P.black_60, stroke_width=2)
        svg.circle(cx, cy, 3, P.black_60)
        svg.text(cx, cy - 128, f"heading {psi}°", "code", 17, P.black, "middle")
        mx, my = H_ * math.cos(math.radians(psi)), -H_ * math.sin(math.radians(psi))
        svg.text(cx, cy + 116, "accel 0.0  0.0  9.8", "code", 15, P.black_60, "middle")
        svg.text(cx, cy + 140, f"mag {mx:+5.1f} {my:+5.1f} {Z_:.0f}", "code", 15, P.teal, "middle")
    axis_label(svg, M, 690, "seen from above: gravity is the dot, straight through the page", size=13)
    axis_label(svg, W - M, 690, "accel m/s², mag µT, body frame", anchor="end", size=13)

    # 10 minutes of walking: gyro-only drifts, mag sees a steel shelf, fused rides through
    dt, T = 0.1, 600.0
    n = int(T / dt)
    ts = [i * dt for i in range(n + 1)]
    turns = [(110, 90), (280, 180), (460, 90)]

    def truth(t):
        h = 0.0
        prev = 0.0
        for t0, to in turns:
            h += (to - prev) * smooth(t, t0, t0 + 6)
            prev = to
        return h

    tr = [truth(t) for t in ts]
    gb = 0.05  # °/s residual bias
    gyro_h, fused, mag = [0.0], [0.0], []
    for i, t in enumerate(ts):
        steel = 32 * smooth(t, 200, 210) * (1 - smooth(t, 250, 262))
        mag.append(tr[i] + steel + rng.gauss(0, 2.5))
        if i:
            w = (tr[i] - tr[i - 1]) / dt + gb + rng.gauss(0, 0.2)
            gyro_h.append(gyro_h[-1] + w * dt)
            f = fused[-1] + w * dt
            e = mag[i] - f
            if abs(e) < 10:
                f += dt / 15 * e
            fused.append(f)
    x0, x1, y0, y1 = M + 70, W - M - 120, 760, 985
    gx = lin(0, T, x0, x1)
    gy = lin(-20, 225, y1, y0)
    hlines(svg, x0, x1, (0, 90, 180), gy, lambda v: f"{v}°")
    for i in range(0, n + 1, 20):
        svg.circle(gx(ts[i]), gy(mag[i]), 1.6, P.teal_60)
    trace(svg, ts, gyro_h, gx, gy, P.lavender, 3, step=10)
    trace(svg, ts, fused, gx, gy, P.blue, 3, step=10)
    trace(svg, ts, tr, gx, gy, P.black, 1.2, step=10)
    svg.text(x1 + 12, gy(gyro_h[-1]) - 2, "gyro only", "code", 15, P.lavender)
    axis_label(svg, x1 + 12, gy(gyro_h[-1]) + 16, f"+{gyro_h[-1] - tr[-1]:.0f}° in 10 min", size=12)
    svg.text(x1 + 12, gy(fused[-1]) + 8, "fused", "code", 15, P.blue)
    axis_label(svg, x1 + 12, gy(fused[-1]) + 26, f"{fused[-1] - tr[-1]:+.0f}°", size=12)
    svg.text(gx(192), gy(128), "steel shelf: mag off 32°", "code", 14, P.teal, "end")
    axis_label(svg, gx(192), gy(128) + 18, "gated out", anchor="end", size=12)
    xticks(svg, (0, 120, 240, 360, 480, 600), gx, y1 + 22, lambda v: f"{v // 60} min")
    axis_label(svg, x0, y0 - 14, "heading on a 10-minute walk · black: the truth · dots: magnetometer")

    svg.frame("yaw.", "attitude · heading observability · magnetometer aiding")
    brief(svg, "gravity says which way is down, not north: spin about it and nothing changes",
          "add a sensor that sees heading: a magnetometer (gate out steel) or GPS course")
    code_rule(svg)
    svg.code(M, CODE_Y, """
roll, pitch = atan2(ay, az), atan2(-ax, hypot(ay, az))   # gravity: these two
yaw += gz * dt                                # the gyro alone: 0.05 °/s -> 30°
mag_yaw = atan2(-my_level, mx_level)          # tilt-compensate, then compare
if abs(e := wrap(mag_yaw - yaw)) < 10: yaw += e * dt / 15     # gate, then nudge""", "py", 18)
    return svg


def _walk(dt, rng):
    """A foot walking a 24 x 12 m rectangle: (t, world accel, world vel, pos, heading, yaw rate, still) per sample."""
    legs = [(24.0, 0.0), (12.0, 90.0), (24.0, 180.0), (12.0, 270.0)]
    L, Tsw, Tst, Ttn = 1.5, 0.6, 0.5, 0.3
    out = []
    x = y = 0.0
    psi = 0.0
    t = 0.0

    def stance(T, dpsi):
        nonlocal t, psi
        for k in range(int(round(T / dt))):
            tau = k * dt
            w = math.radians(dpsi) * dsmooth(tau, 0, Ttn)
            out.append((t, 0.0, 0.0, 0.0, 0.0, x, y, psi, w, True))
            psi += w * dt
            t += dt

    def swing(h):
        nonlocal t, x, y
        for k in range(int(round(Tsw / dt))):
            tau = k * dt
            v = L / Tsw * (1 - math.cos(2 * math.pi * tau / Tsw))
            a = L / Tsw * 2 * math.pi / Tsw * math.sin(2 * math.pi * tau / Tsw)
            c, s = math.cos(math.radians(h)), math.sin(math.radians(h))
            out.append((t, a * c, a * s, v * c, v * s, x, y, psi, 0.0, False))
            x += v * c * dt
            y += v * s * dt
            t += dt

    stance(1.0, 0)
    for li, (length, h) in enumerate(legs):
        steps = int(round(length / L))
        for k in range(steps):
            swing(h)
            turn = 90 if (k == steps - 1 and li < len(legs) - 1) else 0
            stance(Tst, turn)
    stance(0.5, 0)
    return out


def stance() -> Svg:
    """Foot-mounted IMU: double integration flies off; zero-velocity updates at every footfall pin it down."""
    svg = Svg(P.cream)
    rng = random.Random(14)
    dt = 0.005
    walk = _walk(dt, rng)
    ba = (0.05, -0.035)
    bg = math.radians(0.02)
    raw_p, raw_v = [0.0, 0.0], [0.0, 0.0]
    z_p, z_v = [0.0, 0.0], [0.0, 0.0]
    psi_h = 0.0
    still_n = 0
    raw_path, z_path, steps, speeds = [], [], [], []
    for (t, ax, ay, vx, vy, x, y, psi, w, still) in walk:
        c, s = math.cos(psi), math.sin(psi)
        fb = (c * ax + s * ay + ba[0] + rng.gauss(0, 0.04), -s * ax + c * ay + ba[1] + rng.gauss(0, 0.04))
        gz = w + bg + rng.gauss(0, 0.004)
        ch, sh = math.cos(psi_h), math.sin(psi_h)
        aw = (ch * fb[0] - sh * fb[1], sh * fb[0] + ch * fb[1])
        for p_, v_ in ((raw_p, raw_v), (z_p, z_v)):
            v_[0] += aw[0] * dt
            v_[1] += aw[1] * dt
            p_[0] += v_[0] * dt
            p_[1] += v_[1] * dt
        psi_h += gz * dt
        still_n = still_n + 1 if (math.hypot(*fb) < 0.3 and abs(gz) < 0.3) else 0
        if still_n >= 8:
            if still_n == 8:
                steps.append(tuple(z_p))
            z_v[0] = z_v[1] = 0.0
        raw_path.append(tuple(raw_p))
        z_path.append(tuple(z_p))
        speeds.append((t, math.hypot(vx, vy), math.hypot(*z_v), math.hypot(*raw_v)))
    true_end = (walk[-1][5], walk[-1][6])
    dist = 72.0
    e_z = math.hypot(z_p[0] - true_end[0], z_p[1] - true_end[1])
    e_r = math.hypot(raw_p[0] - true_end[0], raw_p[1] - true_end[1])
    T_end = walk[-1][0]

    sc = 30
    ox, oy = W / 2 - 12 * sc, 800
    g = lambda p: (ox + p[0] * sc, oy - p[1] * sc)  # noqa: E731
    svg.poly([g((0, 0)), g((24, 0)), g((24, 12)), g((0, 12))], "none", stroke=P.black, stroke_width=1.5,
             stroke_dasharray="6 6")
    svg.clip_begin(M - 40, ART_TOP + 20, W - 2 * M + 80, 840 - ART_TOP - 20)
    svg.polyline([g(p) for p in raw_path[::10]], P.lavender, 3)
    svg.clip_end()
    svg.polyline([g(p) for p in z_path[::4]], P.blue, 3)
    for p in steps:
        svg.circle(*g(p), 4, P.blue)
    svg.circle(*g((0, 0)), 9, P.black)
    axis_label(svg, g((0, 0))[0] - 14, g((0, 0))[1] + 26, "start / end", size=13)
    svg.text(g((12, 6))[0], g((12, 6))[1] - 6, "the walk: 72 m", "code", 16, P.black, "middle")
    axis_label(svg, g((12, 6))[0], g((12, 6))[1] + 16, f"{T_end:.0f} s, {len(steps)} footfalls", anchor="middle", size=13)
    clip_y = 840
    exit_ = next((g(p) for p in raw_path if g(p)[1] > clip_y), g(raw_path[-1]))
    svg.text(exit_[0] + 12, clip_y + 16, f"integrated alone: {e_r:.0f} m off by the end", "code", 16, P.lavender)
    svg.text(W - M, ART_TOP + 46, f"zero-velocity updates: {e_z:.2f} m off", "code", 16, P.blue, "end")
    axis_label(svg, W - M, ART_TOP + 66, f"{e_z / dist * 100:.1f} % of the distance walked", anchor="end", size=13)

    x0, x1, y0, y1 = M + 70, W - M, 900, 990
    t_show = 8.0
    gx = lin(0, t_show, x0, x1)
    gy = lin(0, 5.5, y1, y0)
    sp = [r for r in speeds if r[0] <= t_show]
    svg.line(x0, y1, x1, y1, P.black_60, 1)
    trace(svg, [r[0] for r in sp], [r[1] for r in sp], gx, gy, P.black, 1.2, step=2)
    trace(svg, [r[0] for r in sp], [r[2] for r in sp], gx, gy, P.blue, 2.5, step=2)
    trace(svg, [r[0] for r in sp], [r[3] for r in sp], gx, gy, P.lavender, 2.5, step=2)
    axis_label(svg, x0 - 12, y0 + 6, "foot", anchor="end", size=12)
    axis_label(svg, x0 - 12, y0 + 22, "speed", anchor="end", size=12)
    xticks(svg, (0, 2, 4, 6, 8), gx, y1 + 20, lambda v: f"{v} s")
    axis_label(svg, x1, y0 - 10, "the first 8 s: the foot stops every step; the error is pinned there", anchor="end",
               size=12)

    svg.frame("stance.", "pedestrian dead reckoning · foot-mounted IMU · ZUPT")
    brief(svg, f"a shoe IMU on a 72 m walk, integrated twice: {e_r:.0f} m off in under a minute",
          "the foot stands still every step: tell the filter v = 0 there, the error resets")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
v += (R @ f_body) * dt;  p += v * dt     # dead reckoning: error ~ t²
still = norm(f_dyn) < 0.3 and norm(gyro) < 0.3  # for 40 ms: foot on the ground
if still: v[:] = 0                       # zero-velocity update (ZUPT)
# error grows per step, not per t²: {e_z:.2f} m after 72 m, vs {e_r:.0f} m""", "py", 19)
    return svg


# ============================================================================
# use: getting it right on the robot
# ============================================================================
def _cube(svg, cx, cy, s, up, col):
    """An isometric cube with an arrow out of the top face, labelled with the axis pointing up."""
    k = 0.866
    top = [(cx, cy - s), (cx + s * k, cy - s / 2), (cx, cy), (cx - s * k, cy - s / 2)]
    left = [(cx - s * k, cy - s / 2), (cx, cy), (cx, cy + s), (cx - s * k, cy + s / 2)]
    right = [(cx, cy), (cx + s * k, cy - s / 2), (cx + s * k, cy + s / 2), (cx, cy + s)]
    svg.poly(left, P.blue_20, stroke=P.black, stroke_width=1.5, stroke_linejoin="round")
    svg.poly(right, P.white, stroke=P.black, stroke_width=1.5, stroke_linejoin="round")
    svg.poly(top, P.lavender_20, stroke=P.black, stroke_width=1.5, stroke_linejoin="round")
    arrow(svg, (cx, cy - s / 2), (cx, cy - s / 2 - s * 1.1), col, 3, 14)
    svg.text(cx, cy - s / 2 - s * 1.1 - 12, up, "code", 15, col, "middle")


def tumble() -> Svg:
    """Six-position calibration: gravity on each face fixes bias, scale and axis misalignment."""
    svg = Svg(P.white)
    rng = random.Random(9)
    S = [1.012, 0.987, 1.020]
    al, be, ga = (math.radians(v) for v in (0.6, -0.4, 0.3))
    Mis = [[1, 0, 0], [al, 1, 0], [be, ga, 1]]
    K_true = [[S[i] * Mis[i][j] for j in range(3)] for i in range(3)]
    b_true = [0.35, -0.22, 0.48]

    def read(a):
        return [v + b + rng.gauss(0, 0.004) for v, b in zip(matvec(K_true, a), b_true)]

    faces = [("+x up", [G, 0, 0]), ("+y up", [0, G, 0]), ("+z up", [0, 0, G]),
             ("−x up", [-G, 0, 0]), ("−y up", [0, -G, 0]), ("−z up", [0, 0, -G])]
    raws = [read(a) for _, a in faces]
    th = lstsq([a + [1.0] for _, a in faces], raws)  # rows: K^T (3) then b
    K_hat = [[th[j][i] for j in range(3)] for i in range(3)]
    b_hat = th[3]
    K_inv = inv(K_hat)
    for j, ((name, a), r) in enumerate(zip(faces, raws)):
        col_i = j % 3
        cx, cy = M + 64 + (j % 3) * 304, 470 + (j // 3) * 190
        _cube(svg, cx, cy, 40, name, P.blue)
        for i, lab in enumerate("xyz"):
            hi = i == col_i
            svg.text(cx + 76, cy - 34 + i * 26, f"{lab} {r[i]:+7.2f}", "code" if hi else "codel", 16,
                     P.blue if hi else P.black_60)
    axis_label(svg, W - M, ART_TOP + 26, "raw accelerometer, m/s², on each face", anchor="end", size=13)

    sc = [math.sqrt(sum(K_hat[i][j] ** 2 for j in range(3))) for i in range(3)]
    rows = [("bias", "  ".join(f"{v:+.2f}" for v in b_hat) + " m/s²"),
            ("scale", "  ".join(f"{(v - 1) * 100:+.1f}" for v in sc) + " %"),
            ("axes", "  ".join(f"{math.degrees(v):+.1f}" for v in (K_hat[1][0] / sc[1], K_hat[2][0] / sc[2],
                                                                    K_hat[2][1] / sc[2])) + " ° off square")]
    for j, (a, b) in enumerate(rows):
        svg.text(M, 735 + j * 26, a, "code", 16, P.black)
        svg.text(M + 90, 735 + j * 26, b, "codel", 16, P.black)
    axis_label(svg, W - M, 787, "solved from the six faces", anchor="end", size=13)

    # 400 random still orientations: |a| before and after
    x0, x1, y0, y1 = M + 74, W - M - 130, 850, 995
    gy = lin(9.1, 10.6, y1, y0)
    gx = lin(0, 400, x0, x1)
    hlines(svg, x0, x1, (9.3, G, 10.3), gy, lambda v: f"{v:.2f}")
    raw_n, cal_n = [], []
    for i in range(400):
        u = [rng.gauss(0, 1) for _ in range(3)]
        nu = math.sqrt(sum(v * v for v in u))
        a = [G * v / nu for v in u]
        r = read(a)
        c = matvec(K_inv, [ri - bi for ri, bi in zip(r, b_hat)])
        raw_n.append(math.sqrt(sum(v * v for v in r)))
        cal_n.append(math.sqrt(sum(v * v for v in c)))
        svg.circle(gx(i), gy(raw_n[-1]), 2.2, P.lavender)
        svg.circle(gx(i), gy(cal_n[-1]), 2.2, P.blue)
    sd = math.sqrt(sum((v - G) ** 2 for v in cal_n) / len(cal_n))
    svg.text(x1 + 14, gy(10.4), "raw", "code", 15, P.lavender)
    axis_label(svg, x1 + 14, gy(10.4) + 18, f"{min(raw_n):.2f}–{max(raw_n):.2f}", size=12)
    svg.text(x1 + 14, gy(G) - 6, "calibrated", "code", 15, P.blue)
    axis_label(svg, x1 + 14, gy(G) + 12, f"9.81 ± {sd:.3f}", size=12)
    axis_label(svg, x0 - 12, y0 - 18, "|a| in 400 random still poses: should be 9.81 every time")

    svg.frame("tumble.", "calibration · six-position test · bias, scale, misalignment")
    brief(svg, "out of the box: biased, scaled a percent or two off, axes not quite square",
          "rest it on each of six faces: gravity is a known 9.81, solve for the rest")
    code_rule(svg)
    svg.code(M, CODE_Y, """
X = [[*a_up, 1] for a_up in six_faces]     # gravity known: ±9.81 on each axis
K, b = lstsq(X, raw)                       # raw = K @ a + b: 12 unknowns, 18 numbers
a = inv(K) @ (raw - b)                     # |a| = 9.81 in every pose
# gyros: bias at rest; scale on a rate table (a good one can use the Earth)""", "py", 19)
    return svg


def mount() -> Svg:
    """Lever arm: off-centre, an accelerometer on a spinning robot reads centripetal and tangential acceleration."""
    svg = Svg(P.cream)
    rng = random.Random(2)
    r = 0.15
    w_max = 3.0
    # robot, top view
    cx, cy, R = 280, 610, 150
    pxm = R / 0.25
    svg.circle(cx, cy, R, P.white, stroke=P.black, stroke_width=3)
    for sy in (-1, 1):
        svg.rect(cx - 40, cy + sy * (R - 6) - 14, 80, 28, P.black, rx=6)
    svg.line(cx - 10, cy, cx + 10, cy, P.black_60, 2)
    svg.line(cx, cy - 10, cx, cy + 10, P.black_60, 2)
    ix = cx + r * pxm
    svg.rect(ix - 14, cy - 14, 28, 28, P.blue, rx=4)
    svg.line(cx, cy, ix - 14, cy, P.black_60, 1.2, stroke_dasharray="4 4")
    svg.text((cx + ix) / 2, cy + 30, f"r = {r * 100:.0f} cm", "code", 14, P.black_60, "middle")
    cen = w_max ** 2 * r
    arrow(svg, (ix - 2, cy - 40), (ix - 2 - cen * 62, cy - 40), P.blue, 3.5, 16)
    svg.text(ix + 8, cy - 56, f"ω²r = {cen:.2f} m/s²", "code", 15, P.blue, "end")
    arrow(svg, (ix + 26, cy), (ix + 26, cy - 75), P.teal, 3.5, 16)
    svg.text(ix + 26, cy - 88, "αr", "code", 15, P.teal, "middle")
    svg.arc(cx, cy, R + 34, math.radians(320), math.radians(200), P.black, 2.5)
    a = math.radians(200)
    svg.triangle(cx + (R + 34) * math.cos(a), cy + (R + 34) * math.sin(a), 16, P.black, a - math.pi / 2)
    svg.text(cx, cy - R - 52, f"spinning in place, up to {w_max:.0f} rad/s", "code", 15, P.black, "middle")
    axis_label(svg, cx, cy + R + 44, "the centre doesn't move", anchor="middle", size=13)
    axis_label(svg, cx, cy + R + 62, "the gyro reads the same anywhere", anchor="middle", size=13)

    # time traces
    dt, T = 0.005, 4.5
    ts = [i * dt for i in range(int(T / dt) + 1)]
    om = [w_max * (smooth(t, 0.2, 1.2) - smooth(t, 2.8, 3.8)) for t in ts]
    gyro = [w + rng.gauss(0, 0.002) for w in om]
    al = [w_max * (dsmooth(t, 0.2, 1.2) - dsmooth(t, 2.8, 3.8)) for t in ts]
    a_r = [-w * w * r for w in om]
    a_t = [x * r for x in al]
    meas = [math.hypot(ar + rng.gauss(0, 0.03), at + rng.gauss(0, 0.03)) for ar, at in zip(a_r, a_t)]
    # compensation with the gyro: smooth it, differentiate it
    gs, k = [], 0.0
    for gv in gyro:
        k += (gv - k) * 0.1
        gs.append(k)
    al_h = [0.0] + [(gs[i] - gs[i - 1]) / dt for i in range(1, len(gs))]
    comp = []
    for i in range(len(ts)):
        mr = a_r[i] + rng.gauss(0, 0.03)
        mt = a_t[i] + rng.gauss(0, 0.03)
        comp.append(math.hypot(mr + gs[i] ** 2 * r, mt - al_h[i] * r))
    x0, x1 = 560, W - M
    gx = lin(0, T, x0, x1)
    y0, y1 = 410, 560
    gy = lin(0, 3.3, y1, y0)
    hlines(svg, x0, x1, (0, 3), gy, lambda v: f"{v:g}")
    trace(svg, ts, om, gx, gy, P.black, 3, step=4)
    axis_label(svg, x0, y0 - 14, "gyro ω, rad/s")
    y2, y3 = 650, 980
    gy2 = lin(-0.1, 1.6, y3, y2)
    hlines(svg, x0, x1, (0, 0.5, 1.0, 1.5), gy2, lambda v: f"{v:g}", zero=0)
    trace(svg, ts, meas, gx, gy2, P.lavender, 2, step=2)
    trace(svg, ts, comp, gx, gy2, P.blue, 2, step=2)
    trace(svg, ts, [abs(x) for x in a_t], gx, gy2, P.teal, 2, step=4, stroke_dasharray="5 5")
    axis_label(svg, x0, y2 - 14, "|horizontal acceleration|, m/s²")
    svg.text(gx(2.0), gy2(cen) - 14, "IMU off-centre reads", "code", 15, P.lavender, "middle")
    svg.text(gx(2.0), gy2(0.32), "compensated: the centre's 0", "code", 15, P.blue, "middle")
    svg.text(gx(1.6), gy2(0.62), "αr: spinning up", "code", 14, P.teal)
    svg.text(gx(1.6), gy2(0.62) + 18, "and down", "code", 14, P.teal)
    xticks(svg, (0, 1, 2, 3, 4), gx, y3 + 22, lambda v: f"{v} s")

    svg.frame("mount.", "installation · lever arm · rigid-body acceleration")
    brief(svg, f"a robot spins in place; the IMU {r * 100:.0f} cm off-centre reads {cen:.2f} m/s² it never had",
          "mount it at the centre, or take the turning out with the gyro's own rates")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
r = [{r}, 0, 0]                                  # IMU from the centre, m
alpha = d_dt(lowpass(gyro))                      # angular acceleration
a_ctr = a_imu - cross(alpha, r) - cross(w, cross(w, r))
# at {w_max:.0f} rad/s: w²r = {cen:.2f} m/s² that the centre never felt""", "py", 19)
    return svg


def alias() -> Svg:
    """Motor vibration above Nyquist folds down into the band the controller cares about."""
    svg = Svg(P.black)
    f_vib, odr = 11400 / 60, 200.0
    f_al = abs(f_vib - round(f_vib / odr) * odr)
    odr_hi, fc, order = 1000.0, 80.0, 4
    att = 1 / math.sqrt(1 + (f_vib / fc) ** (2 * order))
    att_db = 20 * math.log10(att)

    x0, x1, y0, y1 = M + 70, W - M, 395, 545
    T = 0.2
    gx = lin(0, T, x0, x1)
    gy = lin(-1.25, 1.25, y1, y0)
    ts = [T * i / 3000 for i in range(3001)]
    trace(svg, ts, [math.sin(2 * math.pi * f_vib * t) for t in ts], gx, gy, P.black_60, 1)
    tsamp = [k / odr for k in range(int(T * odr) + 1)]
    vs = [math.sin(2 * math.pi * f_vib * t) for t in tsamp]
    trace(svg, tsamp, vs, gx, gy, P.lavender, 3)
    for t, v in zip(tsamp, vs):
        svg.circle(gx(t), gy(v), 4.5, P.lavender)
    svg.line(x0, gy(0), x1, gy(0), P.black_80, 1)
    xticks(svg, (0, 0.05, 0.1, 0.15, 0.2), gx, y1 + 24, lambda v: f"{v * 1000:.0f} ms", True)
    svg.text(x0, y0 - 14, f"{f_vib:.0f} Hz motor buzz", "code", 16, P.blue_40)
    svg.text(x0 + 260, y0 - 14, f"sampled at {odr:.0f} Hz: a {f_al:.0f} Hz wave that isn't there", "code", 16, P.lavender)

    # spectra
    x0, x1 = M + 210, W - M
    gf = lin(0, 500, x0, x1)
    rows = [(760, f"{odr:.0f} Hz, no filter", odr, 1.0, P.lavender),
            (950, f"{odr_hi:.0f} Hz + {order}th-order {fc:.0f} Hz → {odr:.0f}", odr, att, P.teal_60)]
    for yb, name, fs_out, amp, col in rows:
        h = 120
        svg.line(x0, yb, x1, yb, P.black_80, 1.5)
        svg.line(gf(fs_out / 2), yb - h - 10, gf(fs_out / 2), yb, P.white, 1, stroke_dasharray="4 5")
        axis_label(svg, gf(fs_out / 2) + 6, yb - h - 2, "Nyquist", True, size=12)
        svg.line(gf(f_vib), yb, gf(f_vib), yb - h, P.black_60, 6)
        svg.text(x0 - 16, yb - 60, name.split(",")[0] if "," in name else name.split(" + ")[0], "code", 15, col, "end")
        axis_label(svg, x0 - 16, yb - 40, "no filter" if amp == 1.0 else f"+ {order}th-order", True, "end", 12)
        if amp != 1.0:
            axis_label(svg, x0 - 16, yb - 24, f"{fc:.0f} Hz low-pass", True, "end", 12)
            axis_label(svg, x0 - 16, yb - 8, f"→ {odr:.0f} Hz", True, "end", 12)
            fr = [500 * i / 300 for i in range(301)]
            trace(svg, fr, [1 / math.sqrt(1 + (f / fc) ** (2 * order)) for f in fr], gf, lambda v: yb - h * v, P.teal, 2,
                  stroke_dasharray="6 5")
            svg.line(gf(f_vib), yb, gf(f_vib), yb - h * amp, col, 6)
        svg.line(gf(f_al), yb, gf(f_al), yb - max(h * amp, 4), col, 6)
        mid = (gf(f_al) + gf(f_vib)) / 2
        svg.add(f'<path d="M{gf(f_vib) - 4:.1f} {yb - h * max(amp, 0.04) - 8:.1f} Q{mid:.1f} {yb - h - 34} {gf(f_al) + 4:.1f} {yb - h * max(amp, 0.04) - 8:.1f}" '
                f'fill="none" stroke="{col}" stroke-width="1.5" stroke-dasharray="4 4"/>')
        lab = f"{f_al:.0f} Hz phantom, full size" if amp == 1.0 else f"{f_al:.0f} Hz: {att_db:.0f} dB"
        svg.text(gf(f_al) + 14, yb - h / 2 if amp == 1.0 else yb + 22, lab, "code", 15, col)
    xticks(svg, (0, 100, 200, 300, 400, 500), gf, 1000, lambda v: f"{v} Hz", True)
    svg.text(gf(f_vib) + 10, 760 - 100, f"{f_vib:.0f} Hz in", "code", 15, P.blue_40)

    svg.frame("alias.", "sampling · vibration aliasing · anti-alias filter", dark=True, title_fill=P.white)
    brief(svg, f"motors buzz at {f_vib:.0f} Hz; sampled at {odr:.0f} Hz it shows up as a {f_al:.0f} Hz wobble",
          f"sample fast, low-pass inside the chip, then decimate: the phantom drops {-att_db:.0f} dB", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, f"""
f_vib = 11_400 / 60                          # motor at hover: {f_vib:.0f} Hz
f_alias = abs(f_vib - round(f_vib/fs) * fs)  # at fs = {odr:.0f} Hz: {f_al:.0f} Hz, in the loop's band
imu.odr, imu.lpf = 1000, 80                  # sample fast, filter inside the chip
y = decimate(butter(4, 80, fs=1000)(x), 5)   # then {odr:.0f} Hz: {f_vib:.0f} Hz is {att_db:.0f} dB down""", "py", 18,
             dark=True)
    return svg


# ============================================================================
# build
# ============================================================================
FAMILIES = {
    "sense": ["proof", "coriolis", "sagnac"],
    "grade": ["grades", "coast", "allan"],
    "drift": ["integrate", "leak", "warm"],
    "fuse": ["bias", "yaw", "stance"],
    "use": ["tumble", "mount", "alias"],
}
OUT = Path(__file__).resolve().parents[1] / "out/imu"


def main(names: set[str]) -> None:
    for family, fns in FAMILIES.items():
        for name in fns:
            fn = globals().get(name)
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
