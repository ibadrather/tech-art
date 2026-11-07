"""Robot posters: three per kind of robot, each on one thing that makes it hard.

Aerial: hover. tilt. endure.   Underwater: drift. tether. whisper.
Manipulator: singular. grasp. either.   Legged: balance. stride. gait.

Run:  uv run --no-project --with fonttools --with brotli python src/robots.py
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from posters import ART, CODE_Y, M, W, code_rule, fit  # noqa: E402
from sensors import arrow  # noqa: E402

G = 9.81


def mix(c1: str, c2: str, t: float) -> str:
    """Blend two hex colours, t = 0 → c1, t = 1 → c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def bisect(f, lo, hi, n=80):
    """Root of a monotonic f on [lo, hi]."""
    flo = f(lo)
    for _ in range(n):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo, flo = mid, f(mid)
        else:
            hi = mid
    return (lo + hi) / 2


# ============================================================================
# aerial
# ============================================================================
def hover() -> Svg:
    """Quadrotor mixer: four motors, four knobs (thrust, roll, pitch, yaw), and what one command does to each."""
    svg = Svg(P.white)
    cmd = {"thrust": 0.55, "roll": 0.0, "pitch": 0.12, "yaw": 0.15}  # pitch nose-down, yaw clockwise (from above)
    #          name  (dx, dy) page   roll pitch yaw  spin
    motors = [("FR", (1, -1), -1, -1, +1, "ccw"), ("BL", (-1, 1), +1, +1, +1, "ccw"),
              ("FL", (-1, -1), +1, -1, -1, "cw"), ("BR", (1, 1), -1, +1, -1, "cw")]
    cx, cy, arm = W / 2, 625, 180
    for _, (dx, dy), *_ in motors:
        svg.line(cx, cy, cx + dx * arm, cy + dy * arm, P.black, 16, stroke_linecap="round")
    svg.rect(cx - 62, cy - 62, 124, 124, P.blue, rx=18)
    svg.triangle(cx, cy - 8, 44, P.white, -math.pi / 2)  # nose: forward is up

    for name, (dx, dy), r, p, y, spin in motors:
        u = cmd["thrust"] + r * cmd["roll"] + p * cmd["pitch"] + y * cmd["yaw"]
        mx, my = cx + dx * arm, cy + dy * arm
        col = P.blue if spin == "ccw" else P.teal
        svg.circle(mx, my, 118, "none", stroke=P.black_20, stroke_width=2, stroke_dasharray="2 7")
        svg.circle(mx, my, 88, "none", stroke=P.lavender_20, stroke_width=14)
        sgn = 1 if spin == "cw" else -1  # page angles grow clockwise
        a0, a1 = -math.pi / 2, -math.pi / 2 + sgn * 2 * math.pi * u
        svg.arc(mx, my, 88, a0, a1, col, 14, n=96, stroke_linecap="butt")
        tip = (mx + 88 * math.cos(a1), my + 88 * math.sin(a1))
        svg.triangle(*tip, 34, col, a1 + sgn * math.pi / 2)
        svg.circle(mx, my, 20, P.black)
        lx, ly = mx + dx * 170, my + dy * 150
        svg.text(lx, ly + (8 if dy < 0 else 18), f"{u:.2f}", "code", 26, P.black, "middle")
        svg.text(lx, ly + (36 if dy < 0 else -14), f"{name} · {spin}", "codel", 15, P.black_60, "middle")

    svg.frame("hover.", "quadrotor · X mixer · pitch forward + yaw right")
    code_rule(svg)
    svg.code(M, CODE_Y, """
#        thrust roll pitch yaw
MIX = [[1, -1, -1, +1],    # front-right  ccw
       [1, +1, +1, +1],    # back-left    ccw
       [1, +1, -1, -1],    # front-left   cw
       [1, -1, +1, -1]]    # back-right   cw
u = MIX @ [thrust, roll, pitch, yaw]   # yaw: speed one pair, slow the other""", "py", 19)
    return svg


def tilt() -> Svg:
    """Underactuation: thrust only points along body-z, so the drone must lean to accelerate sideways."""
    svg = Svg(P.black)
    D, T = 10.0, 3.0  # metres, seconds: a minimum-jerk dash

    def s(t):
        return 10 * t**3 - 15 * t**4 + 6 * t**5

    def acc(t):
        return D / T**2 * (60 * t - 180 * t**2 + 120 * t**3)

    x0, x1, yp = M + 70, W - M - 70, 560

    def px(x):
        return x0 + (x1 - x0) * x / D

    # θ along the path, plotted under the drones
    yz, ks = 870, 3.1
    ts = [i / 400 for i in range(401)]
    curve = [(px(D * s(t)), yz - ks * math.degrees(math.atan2(acc(t), G))) for t in ts]
    svg.line(x0, yz, x1, yz, P.blue_40, 1.5, stroke_dasharray="2 8")
    svg.poly([(x0, yz)] + curve + [(x1, yz)], P.blue, opacity="0.45")
    svg.polyline(curve, P.lavender, 3)
    svg.text(x0 - 14, yz + 6, "θ", "code", 20, P.blue_40, "end")
    th_max = max(math.degrees(math.atan2(acc(t), G)) for t in ts)
    i_hi = max(range(len(ts)), key=lambda i: -curve[i][1])
    i_lo = max(range(len(ts)), key=lambda i: curve[i][1])
    svg.text(curve[i_hi][0], curve[i_hi][1] - 16, f"+{th_max:.0f}°", "code", 17, P.white, "middle")
    svg.text(curve[i_lo][0], curve[i_lo][1] + 32, f"−{th_max:.0f}°", "code", 17, P.white, "middle")
    svg.text(x0 + 40, yz - 22, "speed up", "codel", 15, P.white)
    svg.text(x1 - 40, yz + 36, "slow down", "codel", 15, P.white, "end")

    n = 8
    t_of = [bisect(lambda t, k=k: s(t) - k / (n - 1), 0, 1) for k in range(n)]
    svg.line(px(0) - 30, yp + 120, px(D) + 30, yp + 120, P.blue_40, 1.5)
    for k, t in enumerate(t_of):
        x = px(D * s(t))
        a = acc(t)
        th = math.atan2(a, G)
        up, rt = (math.sin(th), -math.cos(th)), (math.cos(th), math.sin(th))

        def b(bx, by, x=x, up=up, rt=rt):
            return (x + bx * rt[0] + by * up[0], yp + bx * rt[1] + by * up[1])

        svg.line(x, yp + 26, x, yp + 120, P.blue_40, 1, stroke_dasharray="2 6")
        thrust = 150 * math.hypot(a, G) / G
        hi = k == 2
        if hi:  # split one thrust vector into what holds it up and what pushes it along
            tipx, tipy = b(0, thrust)
            svg.line(x, yp, x, tipy, P.lavender, 2, stroke_dasharray="5 6")
            svg.line(x, tipy, tipx, tipy, P.lavender, 2, stroke_dasharray="5 6")
            svg.text(x - 12, (yp + tipy) / 2, "mg", "code", 17, P.lavender, "end")
            svg.text((x + tipx) / 2, tipy - 14, "ma", "code", 17, P.lavender, "middle")
        arrow(svg, b(0, 14), b(0, thrust), P.teal_60, 4 if hi else 3, 20)
        svg.line(*b(-50, 0), *b(50, 0), P.white, 6, stroke_linecap="round")
        for sx in (-1, 1):
            svg.line(*b(sx * 50, 0), *b(sx * 50, 10), P.white, 4)
            svg.line(*b(sx * 50 - 24, 12), *b(sx * 50 + 24, 12), P.lavender, 4, stroke_linecap="round")
        svg.poly([b(-18, -12), b(18, -12), b(18, 6), b(-18, 6)], P.blue)
    svg.text(px(0), yp + 146, "0 m", "codel", 15, P.blue_40, "middle")
    svg.text(px(D), yp + 146, f"{D:.0f} m in {T:.0f} s", "codel", 15, P.blue_40, "middle")

    svg.frame("tilt.", "quadrotor · underactuated · lean first, then move", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
# rotors push only along the body's z-axis,
# so sideways acceleration has to be leaned into
theta  = atan2(a_x, g)          # tilt for the acceleration you want
thrust = m * hypot(a_x, g)      # and a little more, to stay up""", "py", 21, dark=True)
    return svg


def endure() -> Svg:
    """Flight time against battery mass: more battery, more weight to lift; the best is twice everything else."""
    svg = Svg(P.cream)
    rho, r_prop, eta, e = 1.225, 0.127, 0.5, 120 * 3600  # 10" props ×4, 120 Wh/kg usable
    A = 4 * math.pi * r_prop**2

    def minutes(m0, mb):
        P_h = (G * (m0 + mb)) ** 1.5 / math.sqrt(2 * rho * A) / eta
        return e * mb / P_h / 60

    x0, x1, y0, y1 = M + 60, W - M - 10, 960, 330
    mb_max, t_max = 6.0, 50.0

    def pp(mb, t):
        return x0 + (x1 - x0) * mb / mb_max, y0 + (y1 - y0) * t / t_max

    for t in range(10, 51, 10):
        yy = pp(0, t)[1]
        svg.line(x0, yy, x1, yy, P.black_20, 1)
        svg.text(x0 - 14, yy + 5, str(t), "codel", 14, P.black_60, "end")
    svg.text(x0 - 14, y1 - 26, "min", "codel", 14, P.black_60, "end")
    svg.line(x0, y0, x1, y0, P.black, 2)
    for k in range(7):
        xx = pp(k, 0)[0]
        svg.line(xx, y0, xx, y0 + 8, P.black, 2)
        svg.text(xx, y0 + 32, f"{k} kg" if k == 6 else str(k), "codel", 14, P.black_60, "middle" if k < 6 else "end")
    svg.text(x0, y0 + 32, "", "codel", 14, P.black_60)

    for m0, col in [(0.5, P.blue), (1.0, P.teal), (2.0, P.lavender)]:
        line = [pp(mb, minutes(m0, mb)) for mb in [mb_max * i / 300 for i in range(1, 301)]]
        line = [pp(0, 0)] + line
        svg.polyline(line, col, 5)
        pk = pp(2 * m0, minutes(m0, 2 * m0))
        svg.line(pk[0], pk[1] + 12, pk[0], y0, col, 1.5, stroke_dasharray="3 6")
        svg.circle(*pk, 9, P.cream, stroke=col, stroke_width=4)
        svg.text(pk[0] + 4, pk[1] - 22, f"frame {m0:g} kg · {minutes(m0, 2 * m0):.0f} min", "code", 16, P.black, "middle")
    svg.text(x1, pp(0, 4)[1], "every peak sits at battery = 2 × frame", "codel", 16, P.black_80, "end")

    svg.frame("endure.", "multirotor · hover power · the battery paradox")
    code_rule(svg)
    svg.code(M, CODE_Y, """
P = (m*g)**1.5 / sqrt(2*rho*A) / eta     # hover power, momentum theory
t = e * m_b / P                           # flight time, m = m_0 + m_b
# t ∝ m_b / (m_0 + m_b)**1.5  →  best at m_b = 2·m_0, then it falls""", "py", 20)
    return svg


# ============================================================================
# underwater
# ============================================================================
def drift() -> Svg:
    """AUV dead reckoning: no GPS below the surface, so error grows with distance until it comes up for a fix."""
    svg = Svg(P.black)
    rng = random.Random(3)
    legs = [((0, 0), (400, 0)), ((400, 0), (400, -80)), ((400, -80), (0, -80)),
            ((0, -80), (0, -160)), ((0, -160), (400, -160)), ((400, -160), (400, -240)), ((400, -240), (0, -240))]
    surface_after = {2, 6}  # come up at the end of these legs
    k_err, bias = 0.03, math.radians(2.5)

    truth, est, sig, dist = [(0.0, 0.0)], [(0.0, 0.0)], [0.0], [0.0]
    fixes = []
    ex, ey, s, d, walk = 0.0, 0.0, 0.0, 0.0, 0.0
    for i, (a, b) in enumerate(legs):
        n = int(math.dist(a, b))
        hd = math.atan2(b[1] - a[1], b[0] - a[0])
        for j in range(1, n + 1):
            walk += rng.gauss(0, 0.004)
            h = hd + bias + walk
            ex, ey = ex + math.cos(h), ey + math.sin(h)
            d += 1
            s += k_err
            tx, ty = a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n
            truth.append((tx, ty))
            est.append((ex, ey))
            sig.append(s)
            dist.append(d)
        if i in surface_after:
            fixes.append(((ex, ey), (tx, ty), d))
            ex, ey, s = tx, ty, 0.0
            est.append((ex, ey))
            truth.append((tx, ty))
            sig.append(0.0)
            dist.append(d)

    fm = fit([(-20, 30), (420, -270)], (M, 290, W - M, 770), pad=10)
    svg.polyline([fm(p) for p in truth], P.black_60, 2, stroke_dasharray="2 8")
    for p, sg in list(zip(est, sig))[20::40]:
        if sg > 0:
            q = fm(p)
            svg.circle(*q, sg * (fm((1, 0))[0] - fm((0, 0))[0]), "none", stroke=P.teal_60, stroke_width=1.5, opacity="0.55")
    # draw the estimate leg by leg, breaking it where a fix snaps it back
    seg = [fm(est[0])]
    for p0, p1 in zip(est, est[1:]):
        if math.dist(p0, p1) > 1.5:
            svg.polyline(seg, P.lavender, 3)
            seg = []
        seg.append(fm(p1))
    svg.polyline(seg, P.lavender, 3)
    for e_, t_, _ in fixes:
        a, b = fm(e_), fm(t_)
        svg.line(*a, *b, P.white, 2.5)
        svg.circle(*b, 10, "none", stroke=P.white, stroke_width=2.5)
        svg.circle(*a, 5, P.lavender)
        svg.text(b[0] - 18, b[1] + 6, "gps", "code", 16, P.white, "end")
    st = fm((0, 0))
    svg.triangle(st[0] - 26, st[1], 26, P.white, 0)
    svg.text(st[0] - 18, st[1] - 24, "dive", "codel", 15, P.blue_40)
    svg.text(fm((400, 0))[0], fm((400, 0))[1] - 24, "truth", "codel", 15, P.black_60, "end")
    svg.text(fm((200, -80))[0], fm((200, -80))[1] - 36, "estimate", "codel", 15, P.lavender, "middle")

    # σ against distance: a sawtooth, reset at each surfacing
    x0, x1, yb, yt = M + 60, W - M, 975, 845
    smax, dmax = max(sig), max(dist)
    saw = [(x0 + (x1 - x0) * dd / dmax, yb + (yt - yb) * sg / smax) for dd, sg in zip(dist, sig)]
    svg.poly([(x0, yb)] + saw + [(x1, yb)], P.teal, opacity="0.4")
    svg.polyline(saw, P.teal_60, 3)
    svg.line(x0, yb, x1, yb, P.blue_40, 1.5)
    svg.text(x0 - 14, (yb + yt) / 2 + 6, "σ", "code", 20, P.blue_40, "end")
    for _, _, dd in fixes:
        xx = x0 + (x1 - x0) * dd / dmax
        svg.text(xx, yb + 30, "fix", "codel", 14, P.white, "end" if dd == dmax else "middle")
    svg.text(x0 + (x1 - x0) * fixes[0][2] / dmax - 10, yt - 4, f"{smax:.0f} m", "code", 16, P.white, "end")

    svg.frame("drift.", "AUV · dead reckoning · surface to reset", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
# under water there is no GPS: integrate velocity in the compass frame
p     += R(yaw) @ v_dvl * dt        # dead reckoning
sigma += k * norm(v_dvl) * dt       # error grows with distance travelled
if surfaced: p, sigma = gps(), 0    # so come up for air""", "py", 20, dark=True)
    return svg


def tether() -> Svg:
    """ROV in a current: the tether bows downstream, and half its drag lands on a robot too small to fight it."""
    svg = Svg(P.cream)
    D, L, d, Cd, v, rho, F_thr = 150.0, 190.0, 0.02, 1.2, 0.75, 1025.0, 250.0
    a = bisect(lambda a: 2 * a * math.sinh(D / (2 * a)) - L, 5, 5000)  # rotated catenary through both ends
    w = 0.5 * rho * Cd * d * v**2
    F_rov = w * L / 2

    def x_of(y):
        return a * math.cosh(D / (2 * a)) - a * math.cosh((y - D / 2) / a)

    sx, sy, k = 430, 390, 3.7  # ship x, surface y, px per metre

    def pg(x, y):
        return sx + k * x, sy + k * y

    # sea surface and ship
    svg.line(M, sy, W - M - 90, sy, P.blue, 2.5)
    svg.poly([(sx - 90, sy - 34), (sx + 90, sy - 34), (sx + 66, sy + 6), (sx - 70, sy + 6)], P.black)
    svg.rect(sx - 40, sy - 70, 54, 36, P.black)
    svg.line(sx + 46, sy - 34, sx + 46, sy - 78, P.black, 4)
    svg.line(sx + 46, sy - 78, sx + 70, sy - 64, P.black, 4)
    # current: arrows down the water column, all the same speed
    for yy in range(12, int(D) + 1, 22):
        yp = pg(0, yy)[1]
        arrow(svg, (M + 8, yp), (M + 110, yp), P.lavender, 2.5, 14)
    svg.text(M + 8, sy + 34 - 70, f"current {v} m/s", "codel", 15, P.black_80)

    cable = [pg(x_of(D * i / 200), D * i / 200) for i in range(201)]
    svg.line(*pg(0, 0), *pg(0, D), P.black_60, 1.5, stroke_dasharray="3 7")
    svg.polyline(cable, P.black, 4)
    mid = pg(x_of(D / 2), D / 2)
    svg.text(mid[0] + 22, mid[1] - 8, f"{L:.0f} m of tether", "code", 17, P.black)
    svg.text(mid[0] + 22, mid[1] + 20, f"bows {x_of(D / 2):.0f} m downstream", "codel", 15, P.black_80)

    # the ROV, holding station below the ship
    rx, ry = pg(0, D)
    svg.rect(rx - 46, ry, 92, 50, P.blue, rx=6)
    svg.rect(rx - 30, ry + 50, 60, 10, P.blue_60)
    svg.circle(rx - 24, ry + 22, 9, P.cream)
    ks = 0.32  # px per newton
    arrow(svg, (rx + 52, ry + 25), (rx + 52 + F_rov * ks, ry + 25), P.teal, 6, 22)
    arrow(svg, (rx - 52, ry + 25), (rx - 52 - F_thr * ks, ry + 25), P.blue, 6, 22)
    svg.text(rx + 52 + F_rov * ks, ry + 70, f"tether {F_rov:.0f} N", "code", 17, P.teal, "end")
    svg.text(rx - 52 - F_thr * ks, ry + 70, f"thrust {F_thr:.0f} N", "code", 17, P.blue)
    for dd in (0, 50, 100, 150):
        yy = pg(0, dd)[1]
        svg.line(W - M - 8, yy, W - M, yy, P.black_60, 2)
        svg.text(W - M - 16, yy + 5, f"{dd} m", "codel", 14, P.black_60, "end")

    svg.frame("tether.", f"ROV · tether drag · {D:.0f} m down")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
w     = 0.5 * rho * Cd * d * v**2   # drag per metre of tether: {w:.1f} N/m
F     = w * L                       # all {L:.0f} m of it: {w * L / 1000:.1f} kN
F_rov = F / 2                       # half lands on the robot: {F_rov:.0f} N
# more than its thrusters: the cable, not the robot, sets the limit""", "py", 20)
    return svg


def whisper() -> Svg:
    """Underwater comms: for the same 80 dB loss budget, radio dies in centimetres and sound carries for kilometres."""
    svg = Svg(P.white)
    budget, mu0, sigma = 80.0, 4e-7 * math.pi, 4.0

    def radio(f):
        skin = 1 / math.sqrt(math.pi * f * mu0 * sigma)
        return lambda dist: 8.686 * dist / skin

    def light(c):
        return lambda dist: 4.343 * c * dist

    def sound(fk):
        thorp = 0.11 * fk**2 / (1 + fk**2) + 44 * fk**2 / (4100 + fk**2) + 2.75e-4 * fk**2 + 0.003
        return lambda dist: 15 * math.log10(max(dist, 1.0)) + thorp * dist / 1000

    rows = [("radio · 2.4 GHz", radio(2.4e9), P.lavender, "Mbit/s, in air"),
            ("radio · 10 kHz", radio(1e4), P.lavender, "~100 bit/s"),
            ("blue light · 470 nm", light(0.2), P.blue, "~10 Mbit/s"),
            ("sound · 100 kHz", sound(100), P.teal, "~10 kbit/s"),
            ("sound · 12 kHz", sound(12), P.teal, "~1 kbit/s")]
    lo, hi = -2, 5  # 1 cm .. 100 km
    x0, x1 = M, W - M

    def lx(dist):
        return x0 + (x1 - x0) * (math.log10(dist) - lo) / (hi - lo)

    ytop, gap, h0 = 330, 124, 44
    for k in range(lo, hi + 1):
        xx = lx(10.0**k)
        svg.line(xx, ytop - 20, xx, ytop + gap * len(rows) - 30, P.black_20, 1)
    for i, (name, loss, col, rate) in enumerate(rows):
        yc = ytop + i * gap + 40
        rng = bisect(lambda dd: loss(10**dd) - budget, lo, hi)
        ds = [10 ** (lo + (rng - lo) * j / 240) for j in range(241)]
        top = [(lx(dd), yc - h0 / 2 * max(0.0, 1 - loss(dd) / budget)) for dd in ds]
        bot = [(lx(dd), yc + h0 / 2 * max(0.0, 1 - loss(dd) / budget)) for dd in ds]
        svg.poly(top + bot[::-1], col)
        rm = 10**rng
        label = f"{rm * 100:.1f} cm" if rm < 1 else f"{rm:.0f} m" if rm < 1000 else f"{rm / 1000:.0f} km"
        tx = lx(rm)
        anchor = "start" if tx < x1 - 130 else "end"
        svg.text(tx + 14 if anchor == "start" else tx, yc + (6 if anchor == "start" else -24), label, "code", 18, P.black, anchor)
        svg.text(x0, yc - 34, name, "diag", 20, P.black)
        svg.text(x1, yc - 34, rate, "codel", 15, P.black_60, "end")
    yax = ytop + gap * len(rows) - 14
    svg.line(x0, yax, x1, yax, P.black, 2)
    for k, lab in zip(range(lo, hi + 1), ["1 cm", "10 cm", "1 m", "10 m", "100 m", "1 km", "10 km", "100 km"]):
        xx = lx(10.0**k)
        svg.line(xx, yax, xx, yax + 8, P.black, 2)
        svg.text(xx, yax + 32, lab, "codel", 14, P.black_60, "start" if k == lo else "end" if k == hi else "middle")

    svg.frame("whisper.", f"underwater comms · same {budget:.0f} dB budget · how far")
    code_rule(svg)
    svg.code(M, CODE_Y, """
skin  = 1 / sqrt(pi * f * mu0 * sigma)        # radio: 8.7 dB per skin depth
thorp = (0.11*f**2/(1 + f**2) + 44*f**2/(4100 + f**2)
         + 2.75e-4*f**2 + 0.003)              # sound, dB/km (f in kHz)
loss  = 15*log10(d) + thorp * d/1000          # spreading + absorption""", "py", 19)
    return svg


# ============================================================================
# manipulators
# ============================================================================
L1, L2 = 1.0, 0.8


def ik2(x, y, elbow=1):
    c2 = (x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    q2 = elbow * math.acos(max(-1.0, min(1.0, c2)))
    q1 = math.atan2(y, x) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    return q1, q2


def fk2(q1, q2):
    e = (L1 * math.cos(q1), L1 * math.sin(q1))
    return (0.0, 0.0), e, (e[0] + L2 * math.cos(q1 + q2), e[1] + L2 * math.sin(q1 + q2))


def singular() -> Svg:
    """Manipulability: at each reachable point, the ellipse of hand velocities a unit of joint speed can make."""
    svg = Svg(P.white)
    rmin, rmax = L1 - L2, L1 + L2
    fm = fit([(-rmax, -0.12), (rmax, rmax)], ART, pad=30)
    s = fm((1, 0))[0] - fm((0, 0))[0]

    def ellipse(x, y):
        q1, q2 = ik2(x, y)
        s1, c1, s12, c12 = math.sin(q1), math.cos(q1), math.sin(q1 + q2), math.cos(q1 + q2)
        J = [[-L1 * s1 - L2 * s12, -L2 * s12], [L1 * c1 + L2 * c12, L2 * c12]]
        a = J[0][0] ** 2 + J[0][1] ** 2
        b = J[0][0] * J[1][0] + J[0][1] * J[1][1]
        c = J[1][0] ** 2 + J[1][1] ** 2
        mid, rad = (a + c) / 2, math.hypot((a - c) / 2, b)
        return math.sqrt(mid + rad), math.sqrt(max(mid - rad, 0.0)), 0.5 * math.atan2(2 * b, a - c), L1 * L2 * abs(math.sin(q2))

    step = 0.13
    pts_ = []
    n = int(rmax / step) + 1
    for i in range(-n, n + 1):
        for j in range(0, n + 1):
            x, y = i * step, j * step + step / 2
            if rmin + 0.04 < math.hypot(x, y) < rmax - 0.02:
                pts_.append((x, y))
    els = [(p, *ellipse(*p)) for p in pts_]
    big = max(e[1] for e in els)
    wmax = L1 * L2
    k = 0.072 / big
    for (x, y), a, b, ang, w in els:
        poly = [(x + k * (a * math.cos(t) * math.cos(ang) - b * math.sin(t) * math.sin(ang)),
                 y + k * (a * math.cos(t) * math.sin(ang) + b * math.sin(t) * math.cos(ang)))
                for t in [2 * math.pi * m / 40 for m in range(40)]]
        if b * k * s < 1.2:  # flat: draw it as the line it has become
            svg.line(*fm(poly[0]), *fm(poly[20]), P.lavender, 2.4, stroke_linecap="round")
        else:
            svg.poly([fm(p) for p in poly], mix(P.lavender, P.blue, w / wmax))

    o = fm((0, 0))
    svg.arc(*o, rmax * s, math.pi, 2 * math.pi, P.black_20, 2, n=120, stroke_dasharray="4 8")
    svg.arc(*o, rmin * s, math.pi, 2 * math.pi, P.black_20, 2, stroke_dasharray="4 8")
    q = ik2(1.42, 0.95)
    chain = [fm(p) for p in fk2(*q)]
    svg.line(*chain[0], *chain[1], P.black, 14, stroke_linecap="round", opacity="0.85")
    svg.line(*chain[1], *chain[2], P.black, 10, stroke_linecap="round", opacity="0.85")
    for p, r in zip(chain[:2], (14, 11)):
        svg.circle(*p, r, P.white, stroke=P.black, stroke_width=4)
    svg.triangle(o[0], o[1] + 22, 70, P.black, -math.pi / 2)
    edge = fm((-rmax, 0))
    svg.text(edge[0], edge[1] + 46, "stretched out: w = 0", "codel", 15, P.black_60)
    svg.text(o[0], o[1] + 78, "folded: w = 0", "codel", 15, P.black_60, "middle")

    svg.frame("singular.", "2-link arm · manipulability ellipses · det J")
    code_rule(svg)
    svg.code(M, CODE_Y, """
J = [[-l1*s1 - l2*s12, -l2*s12],
     [ l1*c1 + l2*c12,  l2*c12]]
w = sqrt(det(J @ J.T))        # = l1 * l2 * |sin(q2)|
# w → 0 at the edges: some directions need infinite joint speed""", "py", 20)
    return svg


def grasp() -> Svg:
    """Two-finger grasps and friction cones: it holds when the line between the fingers sits inside both cones."""
    svg = Svg(P.cream)
    mu = 0.4
    half = math.atan(mu)
    shape = [(-0.8, -0.6), (0.7, -0.7), (0.9, 0.2), (0.1, 0.85), (-0.75, 0.5)]  # counter-clockwise

    def on_edge(i, t):
        a, b = shape[i], shape[(i + 1) % len(shape)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        n = math.hypot(ex, ey)
        return (a[0] + ex * t, a[1] + ey * t), (-ey / n, ex / n)  # point, inward normal

    def angle(u, v):
        return math.acos(max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v)))))

    cases = [(-1.32, [on_edge(4, 0.5), on_edge(1, 0.72)]), (1.32, [on_edge(0, 0.3), on_edge(2, 0.5)])]
    fm = fit([(-2.65, -1.25), (2.65, 1.35)], ART, pad=10)
    s = fm((1, 0))[0] - fm((0, 0))[0]
    for ox, contacts in cases:
        (c1, n1), (c2, n2) = [((c[0] + ox, c[1]), n) for c, n in contacts]
        dvec = (c2[0] - c1[0], c2[1] - c1[1])
        a1, a2 = angle(dvec, n1), angle((-dvec[0], -dvec[1]), n2)
        holds = a1 <= half and a2 <= half
        col = P.teal if holds else P.lavender
        svg.poly([fm((x + ox, y)) for x, y in shape], P.white, stroke=P.black, stroke_width=3, stroke_linejoin="round")
        for c, n in ((c1, n1), (c2, n2)):
            base = math.atan2(n[1], n[0])
            Lc = 0.62
            wedge = [c] + [(c[0] + Lc * math.cos(base + t), c[1] + Lc * math.sin(base + t))
                           for t in [-half + 2 * half * m / 20 for m in range(21)]]
            svg.poly([fm(p) for p in wedge], col, opacity="0.35", stroke=col, stroke_width=2)
            rf = 0.07
            tip = (c[0] - n[0] * rf, c[1] - n[1] * rf)
            back = (c[0] - n[0] * 0.55, c[1] - n[1] * 0.55)
            svg.line(*fm(tip), *fm(back), P.black, 2 * rf * s, stroke_linecap="round")
            svg.circle(*fm(tip), rf * s, P.blue)
        svg.line(*fm(c1), *fm(c2), P.black, 2.5, stroke_dasharray="2 7")
        lab = fm((ox, -1.22))
        worst = math.degrees(max(a1, a2))
        svg.text(lab[0], lab[1], "holds" if holds else "slips", "head", 34, col if not holds else P.teal, "middle")
        svg.text(lab[0], lab[1] + 34, f"{worst:.0f}° {'≤' if holds else '>'} {math.degrees(half):.0f}°", "code", 18, P.black_80, "middle")

    svg.frame("grasp.", f"two fingers · friction cones · μ = {mu}")
    code_rule(svg)
    svg.code(M, CODE_Y, """
# a fingertip can push anywhere inside its friction cone
half  = atan(mu)                               # cone half-angle
d     = unit(c2 - c1)                          # finger to finger
holds = angle(d, n1) <= half and angle(-d, n2) <= half""", "py", 20)
    return svg


def either() -> Svg:
    """Inverse kinematics has two answers: the elbow sits where two circles cross. The table picks one."""
    svg = Svg(P.black)
    target = (1.1, 0.75)
    ground = -0.28
    box = (0.7, ground, 1.25, 0.08)  # x0, y0, x1, y1
    fm = fit([(-1.05, -0.32), (1.95, 1.62)], ART, pad=10)
    s = fm((1, 0))[0] - fm((0, 0))[0]
    svg.clip_begin(*ART[:2], ART[2] - ART[0], ART[3] - ART[1])
    o, t = fm((0, 0)), fm(target)
    svg.circle(*o, L1 * s, "none", stroke=P.blue_40, stroke_width=1.5, stroke_dasharray="3 8")
    svg.circle(*t, L2 * s, "none", stroke=P.blue_40, stroke_width=1.5, stroke_dasharray="3 8")
    svg.clip_end()
    g0, g1 = fm((-1.0, ground)), fm((1.9, ground))
    svg.line(*g0, *g1, P.blue_40, 2)
    b0, b1 = fm((box[0], box[3])), fm((box[2], box[1]))
    svg.rect(b0[0], b0[1], b1[0] - b0[0], b1[1] - b0[1], P.blue)
    svg.line(o[0], o[1], o[0], g0[1], P.white, 12)

    def hits(p, q):
        return any(box[0] <= p[0] + (q[0] - p[0]) * u <= box[2] and box[1] <= p[1] + (q[1] - p[1]) * u <= box[3]
                   for u in [m / 60 for m in range(61)])

    for elbow in (+1, -1):
        base, el, ee = fk2(*ik2(*target, elbow))
        bad = hits(base, el) or hits(el, ee)
        col = P.lavender if bad else P.white
        op = "0.75" if bad else "1"
        dash = {"stroke_dasharray": "1 14"} if bad else {}
        svg.line(*fm(base), *fm(el), col, 14 if not bad else 10, stroke_linecap="round", opacity=op, **dash)
        svg.line(*fm(el), *fm(ee), col, 10 if not bad else 8, stroke_linecap="round", opacity=op, **dash)
        e = fm(el)
        svg.circle(*e, 13, P.black, stroke=col, stroke_width=4)
        if bad:
            for sgn in (-1, 1):
                svg.line(e[0] - 30, e[1] - 30 * sgn, e[0] + 30, e[1] + 30 * sgn, P.lavender, 4, stroke_linecap="round")
        if bad:
            svg.text((b0[0] + b1[0]) / 2, g0[1] + 40, "elbow down: hits the table", "code", 17, col, "middle")
        else:
            svg.text(e[0] + 40, e[1] - 18, "elbow up", "code", 17, col)
    svg.circle(*o, 14, P.black, stroke=P.white, stroke_width=4)
    svg.circle(*t, 24, "none", stroke=P.teal_60, stroke_width=4)
    svg.circle(*t, 8, P.teal_60)
    svg.text(t[0] + 36, t[1] + 6, "target", "codel", 16, P.teal_60)
    svg.text(o[0] - 26, o[1] - L1 * s - 16, "|elbow| = l1", "codel", 15, P.blue_40, "end")
    svg.text(t[0], t[1] - L2 * s - 16, "|hand − elbow| = l2", "codel", 15, P.blue_40, "middle")

    svg.frame("either.", "2-link arm · inverse kinematics · two answers", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
c2 = (x*x + y*y - l1*l1 - l2*l2) / (2*l1*l2)    # law of cosines
for s in (+1, -1):                              # elbow down, elbow up
    q2 = s * acos(c2)
    q1 = atan2(y, x) - atan2(l2*sin(q2), l1 + l2*cos(q2))""", "py", 20, dark=True)
    return svg


# ============================================================================
# legged
# ============================================================================
def balance() -> Svg:
    """Statically stable crawl: one foot up at a time, and the body shifted into the triangle of the other three."""
    svg = Svg(P.cream)
    st = 0.26  # stride, m
    hips = {"LF": (0.3, 0.17), "RF": (0.3, -0.17), "LH": (-0.3, 0.17), "RH": (-0.3, -0.17)}
    order = ["RH", "RF", "LH", "LF"]
    offs = {"RH": -3 * st / 8, "RF": -st / 8, "LH": st / 8, "LF": 3 * st / 8}  # foot ahead of its hip at phase start

    def incircle(tri):
        A, B, C = tri
        a, b, c = math.dist(B, C), math.dist(A, C), math.dist(A, B)
        per = a + b + c
        ctr = ((a * A[0] + b * B[0] + c * C[0]) / per, (a * A[1] + b * B[1] + c * C[1]) / per)
        area = abs((B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])) / 2
        return ctr, 2 * area / per

    phases = []
    for k, swing in enumerate(order):
        # hip frame, mid-phase: the body has moved s/4 per phase, each foot that already swung is s further on
        feet = {f: (hips[f][0] + offs[f] - st / 4 * k - st / 8 + (st if order.index(f) < k else 0), hips[f][1]) for f in hips}
        tri = [feet[f] for f in order if f != swing]
        phases.append((swing, feet, tri, *incircle(tri)))

    # one panel per phase: the body slides over the incentre of the three feet that stay down
    cw, ch = (ART[2] - ART[0]) / 2, (ART[3] - ART[1]) / 2
    for k, (swing, feet, tri, ctr, r) in enumerate(phases):
        bx, by = ART[0] + (k % 2) * cw, ART[1] + (k // 2) * ch
        fm = fit([(-0.5, -0.27), (0.5, 0.27)], (bx + 10, by + 40, bx + cw - 10, by + ch - 20), pad=6)
        s = fm((1, 0))[0] - fm((0, 0))[0]
        svg.text(bx + 10, by + 22, f"{k + 1} · {swing} up", "code", 18, P.black)
        svg.text(bx + 128, by + 22, f"margin {r * 100:.0f} cm", "codel", 15, P.black_60)
        a0, a1 = fm((ctr[0] - 0.36, ctr[1] + 0.2)), fm((ctr[0] + 0.36, ctr[1] - 0.2))
        svg.rect(a0[0], a0[1], a1[0] - a0[0], a1[1] - a0[1], "none", rx=26, stroke=P.black_20, stroke_width=2)
        svg.poly([fm(q) for q in tri], P.teal, opacity="0.18", stroke=P.teal, stroke_width=2.5, stroke_linejoin="round")
        svg.circle(*fm(ctr), r * s, "none", stroke=P.teal, stroke_width=1.5, stroke_dasharray="3 6")
        o, c = fm((0, 0)), fm(ctr)
        svg.line(o[0] - 7, o[1] - 7, o[0] + 7, o[1] + 7, P.black_60, 2)
        svg.line(o[0] - 7, o[1] + 7, o[0] + 7, o[1] - 7, P.black_60, 2)
        if math.dist(o, c) > 24:
            arrow(svg, o, c, P.black_60, 2, 12)
        svg.circle(*c, 9, P.blue)
        for f, q in feet.items():
            if f == swing:
                svg.circle(*fm(q), 11, P.cream, stroke=P.lavender, stroke_width=3.5)
            else:
                svg.circle(*fm(q), 8, P.black)
    svg.text(W - M, ART[3] + 10, "×  hips' centre   ●  CoM shifted to the incentre", "codel", 15, P.black_60, "end")

    svg.frame("balance.", "quadruped crawl · support triangles · margin")
    code_rule(svg)
    svg.code(M, CODE_Y, """
# lift one foot at a time; keep the body over the other three
for swing in ("RH", "RF", "LH", "LF"):
    tri = [feet[f] for f in feet if f != swing]   # support triangle
    shift_body_to(incentre(tri))    # margin = the incircle's radius
    step(swing)""", "py", 20)
    return svg


def stride() -> Svg:
    """Biped LIPM: the ZMP hops foot to foot, and the CoM that produces it sways smoothly between them."""
    svg = Svg(P.black)
    zc, dt = 0.8, 0.005
    w2 = G / zc
    step, half_w, t_ss, t_ds = 0.3, 0.1, 0.5, 0.15
    supports = [(step * i, half_w * (-1 if i % 2 == 0 else 1)) for i in range(6)]
    feet = [(0.0, half_w), (0.0, -half_w)] + supports[1:] + [(supports[-1][0], -supports[-1][1])]
    # ZMP reference: rest between the feet, then ramp to each support foot and hold
    key = [(0.0, (0.0, 0.0)), (0.7, (0.0, 0.0))]
    t = 0.7
    for f in supports:
        t += t_ds
        key.append((t, f))
        t += t_ss
        key.append((t, f))
    end = (supports[-1][0], 0.0)
    key += [(t + t_ds, end), (t + t_ds + 0.8, end)]
    n = int(key[-1][0] / dt) + 1
    ts = [i * dt for i in range(n)]

    def zmp_at(tt):
        for (ta, pa), (tb, pb) in zip(key, key[1:]):
            if ta <= tt <= tb:
                u = (tt - ta) / (tb - ta) if tb > ta else 0
                return (pa[0] + (pb[0] - pa[0]) * u, pa[1] + (pb[1] - pa[1]) * u)
        return key[-1][1]

    zmp = [zmp_at(tt) for tt in ts]

    def solve(rhs):  # (I - D2 / (w2 dt^2)) c = p, ends pinned: the Thomas algorithm
        kk = 1 / (w2 * dt * dt)
        a = [0.0] + [-kk] * (n - 2) + [0.0]
        b = [1.0] + [1 + 2 * kk] * (n - 2) + [1.0]
        c = [0.0] + [-kk] * (n - 2) + [0.0]
        d = list(rhs)
        for i in range(1, n):
            m = a[i] / b[i - 1]
            b[i] -= m * c[i - 1]
            d[i] -= m * d[i - 1]
        x = [0.0] * n
        x[-1] = d[-1] / b[-1]
        for i in range(n - 2, -1, -1):
            x[i] = (d[i] - c[i] * x[i + 1]) / b[i]
        return x

    com = list(zip(solve([p[0] for p in zmp]), solve([p[1] for p in zmp])))

    x0m, x1m = -0.25, supports[-1][0] + 0.25
    xs = (W - 2 * M) / (x1m - x0m)

    def tx(x):
        return M + (x - x0m) * xs

    # top view (lateral ×2)
    yc, ys = 445, 1.6 * xs
    for fx, fy in feet:
        svg.rect(tx(fx) - 0.11 * xs, yc - fy * ys - 0.045 * ys, 0.22 * xs, 0.09 * ys, "none", rx=10,
                 stroke=P.blue_40, stroke_width=2)
    svg.polyline([(tx(x), yc - y * ys) for x, y in zmp], P.lavender, 2.5, stroke_dasharray="1 0")
    svg.polyline([(tx(x), yc - y * ys) for x, y in com], P.teal_60, 5)
    svg.text(M, 300, "top · sideways ×1.6", "codel", 15, P.blue_40)
    svg.text(W - M, 300, "zmp", "code", 17, P.lavender, "end")
    svg.text(W - M - 70, 300, "com", "code", 17, P.teal_60, "end")

    # side view: a pendulum from the stance foot to the CoM, at constant height
    yg, zs = 960, xs
    yz = yg - zc * zs
    svg.line(M, yg, W - M, yg, P.blue_40, 2)
    for fx, _ in feet:
        svg.rect(tx(fx) - 0.11 * xs, yg - 7, 0.22 * xs, 7, P.blue_40)
    for i in range(0, n, 14):
        p = zmp[i]
        if any(math.dist(p, f) < 1e-9 for f in supports):  # single support: the ZMP is the foot
            svg.line(tx(p[0]), yg - 7, tx(com[i][0]), yz, P.lavender, 1.5, opacity="0.55")
    svg.line(tx(com[0][0]), yz, tx(com[-1][0]), yz, P.teal_60, 5, stroke_linecap="round")
    svg.text(tx(com[0][0]) - 12, yz + 6, f"z_c = {zc} m", "codel", 15, P.teal_60, "end")
    svg.text(W - M, yz - 14, "side", "codel", 15, P.blue_40, "end")

    svg.frame("stride.", "biped · linear inverted pendulum · ZMP → CoM", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
# the CoM falls away from the ZMP:  c'' = (g / z_c) * (c - p)
w2  = g / z_c
A   = eye(n) - D2 / (w2 * dt**2)      # D2: second difference
com = solve(A, zmp)                   # the sway that keeps p on the feet""", "py", 20, dark=True)
    return svg


def gait() -> Svg:
    """Gait diagrams: the same four legs, five timings. Bars are feet on the ground."""
    svg = Svg(P.white)
    legs = ["LF", "RF", "LH", "RH"]
    gaits = [("walk", (0.00, 0.50, 0.75, 0.25), 0.75), ("trot", (0.00, 0.50, 0.50, 0.00), 0.55),
             ("pace", (0.00, 0.50, 0.00, 0.50), 0.55), ("bound", (0.00, 0.00, 0.50, 0.50), 0.40),
             ("gallop", (0.50, 0.60, 0.00, 0.10), 0.35)]
    cycles = 2
    x0, x1 = M + 160, W - M
    y, row, bar, block = 300, 25, 15, 138

    def gx(t):
        return x0 + (x1 - x0) * t / cycles

    for k in range(cycles + 1):
        svg.line(gx(k), y - 18, gx(k), y + block * len(gaits) - 46, P.black_20, 1, stroke_dasharray="2 6")
    for name, phase, duty in gaits:
        # flight: moments with no foot down
        N = 2000
        down = [[((cycles * i / N - ph) % 1) < duty for ph in phase] for i in range(N)]
        i = 0
        while i < N:
            if not any(down[i]):
                j = i
                while j < N and not any(down[j]):
                    j += 1
                svg.rect(gx(cycles * i / N), y - 8, gx(cycles * j / N) - gx(cycles * i / N), 4 * row - 2, P.lavender_20)
                i = j
            i += 1
        svg.text(M, y + 1.5 * row + 6, name, "diag", 26, P.black)
        svg.text(M, y + 2.5 * row + 10, f"β = {duty:.2f}", "codel", 14, P.black_60)
        for li, (leg, ph) in enumerate(zip(legs, phase)):
            yy = y + li * row
            svg.text(x0 - 14, yy + 5 + bar / 2 - 4, leg, "codel", 13, P.black_60, "end")
            col = P.blue if leg.endswith("F") else P.teal
            for c in range(-1, cycles + 1):
                a, b = c + ph, c + ph + duty
                a, b = max(a, 0), min(b, cycles)
                if b > a:
                    svg.rect(gx(a), yy - 2, gx(b) - gx(a), bar, col, rx=3)
        y += block
    svg.text(x1, y - 4, "front legs", "codel", 15, P.blue, "end")
    svg.text(x1 - 140, y - 4, "hind legs", "codel", 15, P.teal, "end")
    svg.rect(x0, y - 16, 26, 14, P.lavender_20)
    svg.text(x0 + 36, y - 4, "all four in the air", "codel", 15, P.black_60)

    svg.frame("gait.", "quadruped · when each foot is down · two cycles")
    code_rule(svg)
    svg.code(M, CODE_Y, """
#          LF    RF    LH    RH    duty
walk  = (0.00, 0.50, 0.75, 0.25, 0.75)    # three feet down, always
trot  = (0.00, 0.50, 0.50, 0.00, 0.55)    # diagonal pairs
bound = (0.00, 0.00, 0.50, 0.50, 0.40)    # front pair, back pair
down  = ((t - phase[leg]) % 1) < duty""", "py", 20)
    return svg


FAMILIES = {"aerial": [hover, tilt, endure], "underwater": [drift, tether, whisper],
            "manipulator": [singular, grasp, either], "legged": [balance, stride, gait]}
OUT = Path(__file__).resolve().parents[1] / "out/robots"

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
