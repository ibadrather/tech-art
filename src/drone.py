"""Drone posters: one small folding quad (sub-250 g, 4K camera on a 3-axis gimbal), taken apart.

Every poster names one problem the design has to beat (issue) and how it's beaten (fix),
and the drawing is computed from the maths in the code block.

Airframe:   anatomy. weigh. fold. wind.
Camera:     readout. stops. shutter. bin.
Gimbal:     level. damp. lock. portrait.
Link:       budget. fresnel. hop. lag.
Navigate:   bowl. home. reserve. avoid.
Missions:   orbit. map. follow. pano.

Run:  uv run --no-project --with fonttools --with brotli python src/drone.py [name ...]
"""

from __future__ import annotations

import cmath
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import BRAND, FONTS, P, Svg, _fmt  # noqa: E402
from localization import ellipse, path, tag  # noqa: E402
from posters import CODE_Y, M, W, code_rule, fit  # noqa: E402
from robots import mix  # noqa: E402
from sensors import arrow  # noqa: E402

G, RHO = 9.81, 1.225

# One drone, used on every poster: a folding sub-250 g quad. Typical numbers for the class.
MASS = 0.249  # kg
PROP_D = 0.1524  # 6-inch props
OPEN_MM = (298, 373)  # width × length, arms open, props included
FOLDED_MM = (94, 148)
BATTERY_WH = 7.32 * 2.59  # 2S Li-ion, 2590 mAh
HOVER_W = 30.0  # electrical, all in
SENSOR_MM = (9.6, 7.2)  # 1/1.3-inch, 4:3
PIXEL_UM = 1.2  # 48 MP; 2.4 µm binned to 12 MP
FOCAL_MM = 6.7  # 24 mm equivalent
V_MAX = 16.0  # m/s, fastest mode
ART_TOP = 340  # drawings start below the issue / fix chips


# ============================================================================
# shared furniture
# ============================================================================
def brief(svg: Svg, issue: str, fix: str, dark=False) -> None:
    """The issue / fix pair under the kicker: an outlined chip for the problem, a filled one for the answer."""
    ink = P.white if dark else P.black
    dim = P.blue_40 if dark else P.black_60
    y = 262
    svg.rect(M, y - 19, 64, 27, "none", rx=13.5, stroke=dim, stroke_width=1.5)
    svg.text(M + 32, y, "issue", "code", 14, dim, "middle")
    svg.text(M + 80, y, issue, "diag", 20, ink)
    y += 38
    svg.rect(M, y - 19, 64, 27, P.lavender if dark else P.blue, rx=13.5)
    svg.text(M + 32, y, "fix", "code", 14, P.black if dark else P.white, "middle")
    svg.text(M + 80, y, fix, "diag", 20, ink)


def group(svg: Svg, x, y, rot_deg=0.0, s=1.0, opacity=1.0) -> None:
    svg.add(f'<g transform="translate({_fmt(x)} {_fmt(y)}) rotate({_fmt(rot_deg)}) scale({s:.4f})" opacity="{opacity}">')


def end(svg: Svg) -> None:
    svg.add("</g>")


def side_drone(svg: Svg, x, y, s=1.0, pitch_deg=0.0, col=P.black, prop=P.blue_60, lens=P.teal, opacity=1.0,
               gimbal_deg=None, flip=False) -> None:
    """The drone from the side, nose to the right (left if flip). pitch_deg > 0 is nose down.
    gimbal_deg: camera pitch in the world (None = fixed to the body)."""
    if flip:
        svg.add(f'<g transform="translate({_fmt(x)} {_fmt(y)}) scale(-1 1)">')
        side_drone(svg, 0, 0, s, pitch_deg, col, prop, lens, opacity, gimbal_deg)
        svg.add("</g>")
        return
    group(svg, x, y, pitch_deg, s, opacity)
    svg.rect(-38, -8, 76, 18, col, rx=8)
    for sx in (-1, 1):
        svg.line(sx * 30, -3, sx * 58, -14, col, 6, stroke_linecap="round")
        svg.rect(sx * 58 - 5, -25, 10, 13, col, rx=2)
        svg.line(sx * 58 - 27, -27, sx * 58 + 27, -27, prop, 3.5, stroke_linecap="round")
    svg.rect(24, 8, 10, 8, col)
    cam = 0.0 if gimbal_deg is None else gimbal_deg - pitch_deg
    group(svg, 33, 20, cam)
    svg.rect(-9, -8, 20, 16, col, rx=5)
    svg.circle(11, 0, 5, lens)
    end(svg)
    end(svg)


def top_drone(svg: Svg, x, y, s=1.0, heading=0.0, col=P.black, disc=P.lavender_20, ring=P.lavender,
              lens=P.teal, opacity=1.0) -> None:
    """The drone from above, nose along `heading` (radians, 0 = right, page coords)."""
    group(svg, x, y, math.degrees(heading), s, opacity)
    for mx, my in [(26, 30), (26, -30), (-30, 30), (-30, -30)]:
        svg.circle(mx, my, 21, disc, stroke=ring, stroke_width=1.5)
    for mx, my in [(26, 30), (26, -30), (-30, 30), (-30, -30)]:
        svg.line(0, 0, mx, my, col, 6, stroke_linecap="round")
        svg.circle(mx, my, 5, col)
    svg.rect(-28, -12, 56, 24, col, rx=11)
    svg.circle(30, 0, 6, lens)
    end(svg)


def callout(svg: Svg, p, tx, ty, title, sub, anchor="start", col=P.black, dim=P.black_60, line=P.black_60):
    """A dot on the drawing, a leader to the text, a title and a quiet second line."""
    svg.circle(*p, 4.5, col)
    ex = tx - 10 if anchor == "start" else tx + 10
    svg.polyline([p, (ex, ty - 6)], line, 1.2)
    svg.text(tx, ty, title, "code", 17, col, anchor)
    svg.text(tx, ty + 21, sub, "codel", 14, dim, anchor)


def axis_label(svg, x, y, s, dark=False, anchor="start", size=14):
    svg.text(x, y, s, "codel", size, P.blue_40 if dark else P.black_60, anchor)


def blade(svg: Svg, c, ang, r, fill, w=9.0) -> None:
    """One propeller blade from the hub outwards: a thin leaf."""
    out, back = [], []
    for k in range(13):
        t = k / 12
        rr = r * (0.12 + 0.88 * t)
        ww = w * math.sin(math.pi * min(t * 1.25, 1.0)) * (1.1 - 0.5 * t)
        px, py = c[0] + rr * math.cos(ang), c[1] + rr * math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        out.append((px + nx * ww * 0.35, py + ny * ww * 0.35))
        back.append((px - nx * ww, py - ny * ww))
    svg.poly(out + back[::-1], fill)


# ============================================================================
# airframe
# ============================================================================
def anatomy() -> Svg:
    """Top view of the folding quad with each part placed where its noise isn't."""
    svg = Svg(P.white)
    k, cx, cy = 1.5, 540, 690

    def g(x, y):  # drone frame: x right, y forward (mm) → page
        return cx + k * x, cy - k * y

    motors = [(-73, 110), (73, 110), (-73, -110), (73, -110)]
    pivots = [(-36, 44), (36, 44), (-36, -50), (36, -50)]
    rp = PROP_D * 1000 / 2
    for (mx, my), spin in zip(motors, [1, -1, -1, 1]):
        c = g(mx, my)
        svg.circle(*c, rp * k, P.lavender_20, stroke=P.lavender_60, stroke_width=1.5, stroke_dasharray="3 6")
        a0 = 0.6 if spin > 0 else 2.2
        for a in (a0, a0 + math.pi):
            blade(svg, c, a, rp * k * 0.97, P.blue_40, 13)
    for (px, py), (mx, my) in zip(pivots, motors):
        svg.line(*g(px, py), *g(mx, my), P.black, 15, stroke_linecap="round")
    for i in (2, 3):  # antennas run down the rear arms
        a, b = g(*pivots[i]), g(*motors[i])
        svg.line(a[0] + (b[0] - a[0]) * 0.2, a[1] + (b[1] - a[1]) * 0.2, a[0] + (b[0] - a[0]) * 0.8,
                 a[1] + (b[1] - a[1]) * 0.8, P.lavender, 4, stroke_linecap="round")
    for mx, my in motors:
        svg.circle(*g(mx, my), 17, P.black)
        svg.circle(*g(mx, my), 6, P.blue_40)
    # body, nose to the top of the page
    x0, y0 = g(-38, 62)
    svg.rect(x0, y0, 76 * k, 136 * k, P.black, rx=30)
    svg.rect(*g(-17, 86), 34 * k, 26 * k, P.blue, rx=10)  # gimbal + camera
    svg.circle(*g(0, 76), 8, P.teal_60)
    svg.circle(*g(0, 76), 3.5, P.black)
    for sx in (-1, 1):  # forward stereo pair
        svg.circle(*g(sx * 24, 55), 5, P.white)
    svg.rect(*g(-12, 12), 24 * k, 24 * k, P.teal_60, rx=4)  # gnss, under the lid
    svg.rect(*g(-26, -38), 52 * k, 34 * k, "none", rx=8, stroke=P.blue_60, stroke_width=2.5)  # battery
    svg.line(*g(-14, -55), *g(14, -55), P.blue_60, 2.5)
    for sx in (-1, 1):  # rear stereo pair
        svg.circle(*g(sx * 24, -68), 5, P.white)
    fl_arm = g(-36 + (-73 + 36) * 0.55, 44 + (110 - 44) * 0.55)
    svg.circle(*fl_arm, 6, P.teal)

    L, R = 294, 786
    callout(svg, g(-73 - rp * 0.6, 110 + rp * 0.55), L, 392, '6" props', "big discs, gentle air", "end")
    callout(svg, fl_arm, L, 545, "compass", "out on an arm", "end")
    callout(svg, g(-26, -21), L, 700, "battery · 19 Wh", "2S Li-ion · ≈ 34 min", "end")
    callout(svg, g(-60, -90), L, 862, "antennas", "in the rear arms", "end")
    callout(svg, g(17, 80), R, 392, "3-axis gimbal", "1/1.3 in · 48 MP · 4K", "start")
    callout(svg, g(24, 55), R, 545, "vision", "stereo pairs, all round", "start")
    callout(svg, g(12, 0), R, 700, "GNSS", "GPS · Galileo · BeiDou", "start")
    callout(svg, g(58, -112), R, 862, "folding arms", f"{OPEN_MM[1]} → {FOLDED_MM[1]} mm", "start")
    # scale bar
    sb = g(-50, -205)
    svg.line(sb[0], sb[1], sb[0] + 100 * k, sb[1], P.black, 2.5)
    for xx in (sb[0], sb[0] + 100 * k):
        svg.line(xx, sb[1] - 6, xx, sb[1] + 6, P.black, 2.5)
    svg.text(sb[0] + 50 * k, sb[1] + 26, "100 mm", "codel", 14, P.black_60, "middle")

    svg.frame("anatomy.", "mini drone · 249 g · folding quad · 4K camera on a 3-axis gimbal")
    brief(svg, "a big drone's sensors, radios and camera, in a palm-sized 249 g",
          "fold the arms, and put each sensor where the noise isn't")
    code_rule(svg)
    svg.code(M, CODE_Y, """
mass_g     = 249                 # just under the 250 g line
battery_Wh = 7.32 * 2.59         # 2S Li-ion: 19 Wh ≈ 34 min of air
camera     = dict(sensor="1/1.3in", mp=48, video="4K60 HDR")
compass    = "in an arm"         # far from the battery's 15 A""", "py", 20)
    return svg


BUDGET = [  # grams, typical split for a 249 g folding quad
    ("battery", 78, P.blue), ("frame + shell", 42, P.black), ("gimbal + camera", 36, P.teal),
    ("4 motors", 34, P.blue_60), ("flight ctrl + ESCs", 22, P.lavender), ("vision sensors", 14, P.teal_60),
    ("radio + antennas", 10, P.lavender_60), ("4 props", 5, P.black_60), ("GNSS + compass", 4, P.blue_40),
    ("wiring + screws", 4, P.black_20),
]


def weigh() -> Svg:
    """250 grams as 250 squares: what each gram is spent on, and the one left over."""
    svg = Svg(P.cream)
    cols, rows = 25, 10
    pitch = (W - 2 * M + 4.5) / cols
    cell = pitch - 4.5
    y0 = ART_TOP + 30
    cells = [col for _, g_, col in BUDGET for _ in range(g_)]
    assert len(cells) == 249
    for i in range(cols * rows):
        c, r = divmod(i, rows)
        x, y = M + c * pitch, y0 + r * pitch
        if i < len(cells):
            svg.rect(x, y, cell, cell, cells[i], rx=4)
        else:
            svg.rect(x + 1, y + 1, cell - 2, cell - 2, "none", rx=4, stroke=P.blue, stroke_width=2,
                     stroke_dasharray="4 4")
    last = (M + (cols - 1) * pitch + cell / 2, y0 + (rows - 1) * pitch + cell / 2)
    svg.text(last[0] + cell / 2, last[1] + cell / 2 + 34, "1 g to spare", "code", 17, P.blue, "end")
    svg.text(M, y0 - 14, "1 square = 1 gram", "codel", 14, P.black_60)
    svg.text(W - M, y0 - 14, "250 g", "code", 15, P.black, "end")

    ly, lh = y0 + rows * pitch + 90, 38
    for i, (name, g_, col) in enumerate(BUDGET):
        cx_ = M + (i // 5) * 470
        y = ly + (i % 5) * lh
        svg.rect(cx_, y - 15, 18, 18, col, rx=3)
        svg.text(cx_ + 32, y, name, "diag", 19, P.black)
        svg.text(cx_ + 400, y, f"{g_} g", "code", 17, P.black, "end")
    svg.text(W - M, ly + 5 * lh + 8, "typical split for the class · approximate", "codel", 13, P.black_60, "end")

    svg.frame("weigh.", "mini drone · mass budget · 249 of 250 grams")
    brief(svg, "at 250 g and over, the rules in most countries get stricter",
          "budget every gram: this one lands on 249")
    code_rule(svg)
    svg.code(M, CODE_Y, """
budget = dict(battery=78, frame=42, gimbal_cam=36, motors=34, fc_esc=22,
              vision=14, radio=10, props=5, gnss_compass=4, wiring=4)
assert sum(budget.values()) < 250       # 249: one gram of margin
# a bigger battery flies longer, and lands on the wrong side of the line""", "py", 19)
    return svg


def _plan(svg: Svg, g, folded=False) -> None:
    """The quad from above in a mapping g(x_mm, y_mm) → page; arms open or tucked along the body."""
    motors = [(-73, 110), (73, 110), (-73, -110), (73, -110)]
    pivots = [(-36, 44), (36, 44), (-36, -50), (36, -50)]
    rp = PROP_D * 1000 / 2
    k = g(1, 0)[0] - g(0, 0)[0]
    if not folded:
        for mx, my in motors:
            svg.circle(*g(mx, my), rp * k, P.lavender_20, stroke=P.lavender_60, stroke_width=1.5)
        for (px, py), (mx, my) in zip(pivots, motors):
            svg.line(*g(px, py), *g(mx, my), P.black, 13, stroke_linecap="round")
            svg.circle(*g(mx, my), 14, P.black)
        svg.rect(*g(-38, 62), 76 * k, 136 * k, P.black, rx=24 * k / 1.3)
    else:
        svg.rect(*g(-36, 62), 72 * k, 136 * k, P.black, rx=24 * k / 1.3)
        for (px, py), (mx, my), front in zip(pivots, motors, [1, 1, 0, 0]):
            arm = math.dist((px, py), (mx, my))
            sx = 1 if px > 0 else -1
            base, tip = (sx * 40, py), (sx * 40, py - arm if front else py + arm)
            svg.line(*g(*base), *g(*tip), P.black_80, 11, stroke_linecap="round")
            svg.circle(*g(*tip), 9, P.black_80)
            back = arm * 0.85 if front else -arm * 0.85
            svg.line(*g(sx * 40, tip[1]), *g(sx * 40, tip[1] + back), P.lavender, 3, stroke_linecap="round")
    svg.rect(*g(-15, 84), 30 * k, 22 * k, P.blue, rx=8)
    svg.circle(*g(0, 73), 5 * k, P.teal_60)


def fold() -> Svg:
    """Big props need a big frame; the arms swing in so the frame doesn't stay big."""
    svg = Svg(P.white)
    k = 1.0
    ow, ol = OPEN_MM
    fw, fl = FOLDED_MM
    oc, fc = (M + ow * k / 2 + 10, 562), (640, 562)

    def go(x, y):
        return oc[0] + k * x, oc[1] - k * y

    def gf(x, y):
        return fc[0] + k * x, fc[1] - k * y

    svg.rect(*go(-ow / 2, ol / 2), ow * k, ol * k, "none", stroke=P.black_20, stroke_width=1.5, stroke_dasharray="2 6")
    _plan(svg, go)
    # sweep arcs on the left arms: where they go when folded
    for (px, py), (mx, my), front in [((-36, 44), (-73, 110), 1), ((-36, -50), (-73, -110), 0)]:
        arm = math.dist((px, py), (mx, my))
        a1 = math.atan2(-(my - py), mx - px)
        a0 = math.atan2(arm if front else -arm, -5)
        c = go(px, py)
        r = arm * k * 0.75
        d = (a0 - a1 + math.pi) % (2 * math.pi) - math.pi
        svg.arc(*c, r, a1, a1 + d, P.blue, 2.5, stroke_dasharray="4 6")
        tip = (c[0] + r * math.cos(a1 + d), c[1] + r * math.sin(a1 + d))
        svg.triangle(*tip, 14, P.blue, a1 + d + math.copysign(math.pi / 2, d))
    lo = go(0, -ol / 2)
    svg.text(lo[0], lo[1] + 32, f"open · {ow} × {ol} mm", "codel", 15, P.black_60, "middle")

    svg.rect(*gf(-fw / 2, fl / 2), fw * k, fl * k, "none", stroke=P.blue, stroke_width=2, stroke_dasharray="6 6")
    _plan(svg, gf, folded=True)
    lf = gf(0, -fl / 2)
    svg.text(lf[0], lf[1] + 32, f"folded · {fw} × {fl} mm", "code", 15, P.blue, "middle")
    arrow(svg, (go(ow / 2, 0)[0] + 18, fc[1]), (gf(-fw / 2, 0)[0] - 26, fc[1]), P.blue, 3, 16)

    tx = 790
    svg.text(tx, 470, f"{ow * ol / (fw * fl):.0f}×", "head", 64, P.blue)
    svg.text(tx, 504, "smaller footprint", "codel", 15, P.black_60)
    svg.text(tx, 590, "same 6\" props", "code", 18, P.black)
    svg.text(tx, 615, "blades fold back", "codel", 15, P.black_60)
    svg.text(tx, 640, "along each arm", "codel", 15, P.black_60)

    # hover power against prop size, from momentum theory
    x0, x1, yt, yb = M + 50, W - M, 868, 992
    T = MASS * G

    def p_ideal(d_in):
        A = 4 * math.pi * (d_in * 0.0254 / 2) ** 2
        return T**1.5 / math.sqrt(2 * RHO * A)

    def gp(d, p):
        return x0 + (x1 - x0) * (d - 2) / 6, yb - (yb - yt) * p / 30

    for p in (10, 20, 30):
        svg.line(x0, gp(2, p)[1], x1, gp(2, p)[1], P.black_20, 1)
        axis_label(svg, x0 - 10, gp(2, p)[1] + 5, f"{p} W", anchor="end")
    svg.line(x0, yb, x1, yb, P.black, 2)
    for d in range(2, 9):
        axis_label(svg, gp(d, 0)[0], yb + 24, f'{d}"', anchor="middle")
    svg.polyline([gp(2 + 0.05 * i, p_ideal(2 + 0.05 * i)) for i in range(121)], P.blue, 4)
    for d, col in [(3, P.lavender), (6, P.blue)]:
        q = gp(d, p_ideal(d))
        svg.line(q[0], q[1], q[0], yb, col, 1.5, stroke_dasharray="3 5")
        svg.circle(*q, 7, col)
        svg.text(q[0] + 14, q[1] - 10, f"{p_ideal(d):.0f} W", "code", 18, col)
    axis_label(svg, x0, yt - 26, "ideal rotor power to hover 249 g, by prop diameter")
    svg.text(x1, yt - 26, "half the prop, ×2 the power", "code", 16, P.black, "end")

    svg.frame("fold.", "mini drone · prop size vs frame size · momentum theory")
    brief(svg, "small props need far more power to hover; big props, a big frame",
          "6\" props on arms that swing in: big discs, small bag")
    code_rule(svg)
    svg.code(M, CODE_Y, """
A = 4 * pi * (D / 2)**2                      # four rotor discs
P = (m * g)**1.5 / sqrt(2 * rho * A)         # momentum theory: P ~ 1 / D
# 3in props: 18 W.  6in props: 9 W.  so the props stay big
arms.pivot(front="swing forward", rear="swing back")   # and the frame folds""", "py", 19)
    return svg


def wind() -> Svg:
    """Wind: lean into it to hold still; it blows you out fast and makes you crawl home."""
    svg = Svg(P.black)
    CdA = 0.0226
    winds = [0.0, 5.0, 10.7]

    def tilt(v):
        return math.atan(0.5 * RHO * CdA * v * v / (MASS * G))

    for v, cx in zip(winds, [230, 540, 850]):
        cy = 470
        th = tilt(v)
        rng = random.Random(int(v * 10) + 3)
        for j in range(5):  # wind streaks from the left, stopping short of the drone
            yy = cy - 70 + 35 * j
            if v:
                xe = cx - 100 - rng.uniform(0, 12)
                svg.line(xe - 8 * v, yy, xe, yy, P.blue_60, 2, stroke_linecap="round", opacity="0.8")
        side_drone(svg, cx, cy, 1.15, math.degrees(th), P.white, P.lavender, P.teal_60, flip=True)
        n = (-math.sin(th), -math.cos(th))  # body-up, leaning into the wind
        L = 92 / math.cos(th)
        arrow(svg, (cx + n[0] * 30, cy + n[1] * 30), (cx + n[0] * (30 + L), cy + n[1] * (30 + L)), P.lavender, 3.5, 16)
        arrow(svg, (cx, cy + 30), (cx, cy + 122), P.blue_40, 3, 14)
        if v:
            D = 92 * math.tan(th)
            arrow(svg, (cx + 62, cy + 8), (cx + 62 + D, cy + 8), P.teal_60, 3.5, 14)
        svg.text(cx, cy + 172, f"{v:g} m/s", "code", 20, P.white, "middle")
        svg.text(cx, cy + 198, f"lean {math.degrees(th):.0f}°", "codel", 15, P.blue_40, "middle")
    lx = W - M - 330
    for word, col in [("thrust", P.lavender), ("weight", P.blue_40), ("drag", P.teal_60)]:
        svg.rect(lx, 694, 18, 4, col)
        svg.text(lx + 26, 701, word, "codel", 14, col)
        lx += 26 + 9 * len(word) + 34

    # out with the wind, home against it
    v_air, v_w, d = 12.0, 8.0, 1500.0
    v_out, v_home = v_air + v_w, v_air - v_w
    t_out, t_home = d / v_out, d / v_home
    x0, x1, yt, yb = M + 60, W - M, 790, 990
    T = t_out + t_home + 20

    def gq(t, dd):
        return x0 + (x1 - x0) * t / T, yb - (yb - yt) * dd / 1600

    for dd in (500, 1000, 1500):
        svg.line(x0, gq(0, dd)[1], x1, gq(0, dd)[1], P.black_80, 1)
        axis_label(svg, x0 - 12, gq(0, dd)[1] + 5, f"{dd / 1000:g} km", True, "end")
    for t in range(0, int(T) + 1, 60):
        axis_label(svg, gq(t, 0)[0], yb + 26, f"{t // 60} min", True, "middle")
    svg.line(x0, yb, x1, yb, P.blue_40, 1.5)
    out = [gq(0, 0), gq(t_out, d)]
    home = [gq(t_out, d), gq(t_out + t_home, 0)]
    svg.poly(out + [gq(t_out, 0)], P.teal, opacity="0.25")
    svg.poly(home + [gq(t_out, 0)], P.lavender, opacity="0.2")
    svg.polyline(out, P.teal_60, 4)
    svg.polyline(home, P.lavender, 4)
    pct = 100 * HOVER_W / 3600 / (BATTERY_WH * 0.9)
    a = gq(t_out, d)
    a = gq(t_out, d * 0.28)
    svg.text(a[0] + 18, a[1], f"out {v_out:.0f} m/s · {t_out:.0f} s · {pct * t_out:.0f} %", "code", 16, P.teal_60)
    b = gq(t_out + t_home * 0.5, d * 0.5)
    svg.text(b[0] + 20, b[1] - 6, f"home {v_home:.0f} m/s · {t_home / 60:.1f} min · {pct * t_home:.0f} %",
             "code", 16, P.lavender)
    axis_label(svg, x0 - 12, yt - 22, f"distance from home · airspeed {v_air:.0f} m/s · wind {v_w:.0f} m/s", True)

    svg.frame("wind.", "mini drone · 249 g in a 10.7 m/s wind · lean and ground speed", dark=True, title_fill=P.white)
    brief(svg, "wind blows a 249 g drone out fast, then makes it crawl home",
          "lean into it, and budget the trip home against the wind", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
tilt   = atan(0.5 * rho * CdA * v_wind**2 / (m * g))   # 10.7 m/s → 33°
v_out  = v_air + v_wind      # 12 + 8 = 20 m/s with the wind
v_home = v_air - v_wind      # 12 - 8 =  4 m/s against it: 5× slower
E_home = P_hover * d / v_home     # so it reserves the battery for that""", "py", 19, dark=True)
    return svg


# ============================================================================
# camera
# ============================================================================
def readout() -> Svg:
    """Rolling shutter: rows are read one after another, so anything moving leans or wobbles."""
    svg = Svg(P.white)
    towers = [(0.08, 0.07, 0.30), (0.22, 0.04, 0.12), (0.34, 0.09, 0.42), (0.52, 0.05, 0.22), (0.64, 0.08, 0.36),
              (0.80, 0.03, 0.18), (0.88, 0.07, 0.48)]
    horizon = 0.8
    T_slow, T_fast = 15e-3, 6e-3
    cases = [("global shutter", lambda v: 0.0), ("rolling · yaw 60°/s", lambda v: 0.16 * v),
             ("rolling · motor buzz", lambda v: 0.035 * math.sin(2 * math.pi * 3.2 * v))]
    pw, ph, gap = 288, 216, 24
    y0 = ART_TOP + 40
    for i, (name, dx) in enumerate(cases):
        x0 = M + i * (pw + gap)
        svg.rect(x0, y0, pw, ph, P.lavender_20)
        svg.clip_begin(x0, y0, pw, ph)
        svg.rect(x0, y0 + horizon * ph, pw, ph * (1 - horizon), P.teal_20)
        for tx, tw, top in towers:
            vs = [top + (horizon - top) * j / 40 for j in range(41)]
            left = [(x0 + pw * (tx + dx(v)), y0 + ph * v) for v in vs]
            right = [(x0 + pw * (tx + tw + dx(v)), y0 + ph * v) for v in vs]
            svg.poly(left + right[::-1], P.black if i != 1 or tx > 0.3 else P.black)
        svg.line(x0, y0 + horizon * ph, x0 + pw, y0 + horizon * ph, P.teal, 2)
        svg.clip_end()
        svg.rect(x0, y0, pw, ph, "none", stroke=P.black, stroke_width=2)
        svg.text(x0, y0 - 14, name, "code", 16, P.blue if i else P.black)

    # timing: each row starts its exposure a little after the one above
    x0, x1, yt, yb = M + 70, W - M, 700, 960
    Tmax = 18e-3
    exp_t = 2e-3

    def gt(t, r):
        return x0 + (x1 - x0) * t / Tmax, yt + (yb - yt) * r

    for t in range(0, 19, 3):
        svg.line(gt(t * 1e-3, 0)[0], yt, gt(t * 1e-3, 0)[0], yb, P.black_20, 1)
        axis_label(svg, gt(t * 1e-3, 0)[0], yb + 26, f"{t} ms", anchor="middle")
    for T, col, lab in [(T_slow, P.lavender, "older sensor · 15 ms"), (T_fast, P.blue, "fast · 6 ms")]:
        svg.poly([gt(0, 0), gt(exp_t, 0), gt(T + exp_t, 1), gt(T, 1)], col, opacity="0.85")
        e = gt(T * 0.62 + exp_t, 0.62)
        svg.text(e[0] + 14, e[1] + 5, lab, "code", 16, col)
    for r, lab in [(0, "row 1"), (1, "row 2160")]:
        axis_label(svg, x0 - 12, gt(0, r)[1] + 5, lab, anchor="end")
    lean_slow = 60 / 71 * 3840 * T_slow
    lean_fast = 60 / 71 * 3840 * T_fast
    svg.text(x1, yt - 40, f"yaw 60°/s → {lean_slow:.0f} px lean vs {lean_fast:.0f} px", "code", 16, P.black, "end")
    svg.text(x1, yt - 16, "each bar: one row's 2 ms exposure, top row to bottom", "codel", 14, P.black_60, "end")

    svg.frame("readout.", "drone camera · rolling shutter · rows read top to bottom")
    brief(svg, "rows are read one at a time: things that move lean and wobble",
          "read the rows faster, and let the gimbal cancel the motion")
    code_rule(svg)
    svg.code(M, CODE_Y, """
t_row  = row / n_rows * t_readout          # each row sees a later instant
x_seen = x + v_px * t_row                  # so a pan shears verticals
lean   = v_px * t_readout                  # 60°/s pan: 49 px at 15 ms, 19 at 6
# vibration at f Hz: a sine down the frame, f * t_readout waves of jello""", "py", 19)
    return svg


def stops() -> Svg:
    """Dynamic range: the scene spans more stops than one read of a small sensor; two gains merged cover it."""
    svg = Svg(P.black)
    comps = [(4.0, 0.9, 0.55), (8.5, 1.4, 1.0), (13.4, 0.8, 0.8), (15.8, 0.5, 0.35)]  # shadows, ground, sky, clouds

    def hist(s):
        return sum(a * math.exp(-0.5 * ((s - m) / sd) ** 2) for m, sd, a in comps)

    x0, x1 = M + 40, W - M
    smin, smax = 0, 18

    def gs(s):
        return x0 + (x1 - x0) * (s - smin) / (smax - smin)

    yb, hh = 600, 200
    one = (3.0, 14.5)
    hdr = (2.0, 17.0)
    ss = [smin + (smax - smin) * i / 360 for i in range(361)]
    for lo, hi, col in [(smin, one[0], P.teal_60), (one[0], one[1], P.lavender), (one[1], smax, P.teal_60)]:
        seg = [s for s in ss if lo <= s <= hi]
        svg.poly([(gs(seg[0]), yb)] + [(gs(s), yb - hh * hist(s)) for s in seg] + [(gs(seg[-1]), yb)], col,
                 opacity="0.9" if col == P.lavender else "0.55")
    svg.line(x0, yb, x1, yb, P.blue_40, 1.5)
    for st in range(0, 19, 2):
        axis_label(svg, gs(st), yb + 24, f"{st}", True, "middle")
    axis_label(svg, (x0 + x1) / 2, yb + 50, "scene brightness, stops (each one ×2 the light)", True, "middle")
    for name, s_ in [("shadows", 4.0), ("ground", 8.5), ("sky", 13.4), ("sunlit cloud", 15.8)]:
        svg.text(gs(s_), yb - hh * hist(s_) - 14, name, "codel", 14, P.white, "middle")
    svg.text(gs(1.5), yb + 50, "crushed", "code", 15, P.teal_60, "middle")
    svg.text(gs(16.5), yb + 50, "clipped", "code", 15, P.teal_60, "middle")

    for row, (lo, hi, col, lab) in enumerate([(*one, P.lavender, "one read"), (*hdr, P.blue_60, "two gains, merged")]):
        y = 708 + row * 70
        svg.rect(gs(lo), y - 14, gs(hi) - gs(lo), 20, col, rx=10)
        svg.text(gs(lo), y - 26, f"{lab} · {hi - lo:.1f} stops", "code", 16, P.white)
    hi_g = (hdr[0], hdr[0] + 11.5)
    lo_g = (hdr[1] - 11.5, hdr[1])
    for lo, hi, yy in [(hi_g[0], hi_g[1], 778 + 20), (lo_g[0], lo_g[1], 778 + 30)]:
        svg.line(gs(lo), yy, gs(hi), yy, P.blue_40, 2.5, stroke_linecap="round")
    svg.text(gs(hdr[0]), 778 + 54, "high gain: clean shadows", "codel", 14, P.blue_40)
    svg.text(gs(hdr[1]), 778 + 54, "low gain: keeps the sky", "codel", 14, P.blue_40, "end")

    # how the stops are stored: 10-bit code values
    yt2, yb2 = 880, 985

    def gv(st, v):
        return gs(st), yb2 - (yb2 - yt2) * v / 1023

    lin = [gv(s, min(1023, 1023 * (2 ** (s - hdr[1])) ** (1 / 2.4))) for s in ss if s >= hdr[0]]
    log = [gv(s, 1023 * min(max((s - hdr[0]) / (hdr[1] - hdr[0]), 0), 1)) for s in ss if s >= hdr[0]]
    svg.polyline(lin, P.teal_60, 3)
    svg.polyline(log, P.white, 3)
    svg.line(gs(hdr[0]), yb2, gs(hdr[1]), yb2, P.blue_40, 1.5)
    svg.text(gs(hdr[0]) - 14, yt2 + 6, "1023", "codel", 13, P.blue_40, "end")
    svg.text(gs(hdr[0]) - 14, yb2, "0", "codel", 13, P.blue_40, "end")
    svg.text(gs(11.2), gv(11.2, 1023 * (11.2 - 2) / 15)[1] - 12, "log: same codes per stop", "code", 15, P.white, "end")
    svg.text(gs(hdr[0]), yb2 + 24, "gamma: the dark stops get almost no codes", "code", 15, P.teal_60)

    svg.frame("stops.", "drone camera · dynamic range · dual-gain HDR + log", dark=True, title_fill=P.white)
    brief(svg, "a sunny scene spans ~15 stops; one read of a small sensor holds ~11",
          "read every pixel at two gains and merge; store it log", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
hi = read(gain=8)        # shadows clean, sky clipped
lo = read(gain=1)        # sky kept, shadows noisy
hdr = where(hi < clip, hi / 8, lo)            # per pixel: best of both
code = 1023 * (log2(hdr) - s0) / (s1 - s0)    # log: every stop gets codes""", "py", 19, dark=True)
    return svg


def shutter() -> Svg:
    """180° rule: bright light forces a tiny shutter and stuttering motion; ND filters buy the blur back."""
    svg = Svg(P.cream)
    fps, N, EV = 60, 1.7, 14
    t0 = N * N / 2**EV
    rows = [("no filter", 1), ("ND8", 8), ("ND32", 32), ("ND64", 64)]
    tf = 1 / fps
    x0, step, nfr = M + 230, 106, 6
    y = ART_TOP + 60
    for name, nd in rows:
        t = t0 * nd
        ang = 360 * t / tf
        good = 110 <= ang <= 260
        col = P.blue if good else P.black
        svg.text(M, y + 4, name, "code", 20, col)
        svg.text(M, y + 30, f"1/{1 / t:.0f} s · {ang:.0f}°", "codel", 15, P.black_60)
        # what the frames record: the ball moves `step` px per frame, smeared over the exposure
        for k in range(nfr):
            xs = x0 + k * step
            L = step * t / tf
            op = 0.35 + 0.65 * k / (nfr - 1)
            svg.rect(xs - 12, y - 18, L + 24, 24, col, rx=12, opacity=f"{op:.2f}")
        # the shutter timeline under it
        for k in range(nfr):
            xs = x0 + k * step
            svg.rect(xs, y + 26, step - 6, 8, P.black_20, rx=2)
            svg.rect(xs, y + 26, max(2, (step - 6) * t / tf), 8, col, rx=2)
        if good:
            svg.text(W - M, y + 2, "smooth", "code", 15, P.blue, "end")
        y += 150
    svg.text(x0, ART_TOP + 8, f"one moving ball, {nfr} frames at {fps} fps", "codel", 14, P.black_60)
    svg.text(W - M, ART_TOP + 8, "bar: shutter open, per frame", "codel", 14, P.black_60, "end")
    svg.text(x0, y - 70, "the 180° rule: shutter open half of each frame, 1/120 s at 60 fps", "codel", 15, P.blue)

    svg.frame("shutter.", f"drone camera · f/{N} fixed · sunny EV {EV} · 4K{fps}")
    brief(svg, "fixed f/1.7 in sunshine: 1/5700 s, frames so sharp that motion stutters",
          "an ND filter cuts the light, so the shutter can stay open ~half the frame")
    code_rule(svg)
    svg.code(M, CODE_Y, """
t     = N**2 / 2**EV          # f/1.7 at EV 14, ISO 100: 1/5700 s
angle = 360 * t * fps         # 4°: every frame frozen, the gaps jump
t_nd  = t * nd                # ND32 → 1/178 s, ND64 → 1/89 s
# aim for 180° (1/120 at 60 fps): each frame smears into the next""", "py", 19)
    return svg


def _poisson(rng, lam):
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def bin() -> Svg:
    """Quad-Bayer binning: four small same-colour pixels summed into one, for 4× the light and 2× the SNR."""
    svg = Svg(P.white)
    rng = random.Random(6)
    cols = {"R": P.lavender_60, "G": P.teal_60, "B": P.blue_60}
    quad = [["R", "G"], ["G", "B"]]
    y0, c = ART_TOP + 40, 25
    mx = M
    for j in range(8):
        for i in range(8):
            ch = quad[(j // 2) % 2][(i // 2) % 2]
            svg.rect(mx + i * c, y0 + j * c, c - 2, c - 2, cols[ch], rx=2)
            svg.text(mx + i * c + (c - 2) / 2, y0 + j * c + 17, ch, "code", 11, P.white, "middle")
    svg.text(mx, y0 - 14, "48 MP · 1.2 µm pixels", "code", 16, P.black)
    arrow(svg, (mx + 8 * c + 30, y0 + 4 * c), (mx + 8 * c + 130, y0 + 4 * c), P.blue, 3.5, 18)
    svg.text(mx + 8 * c + 80, y0 + 4 * c - 18, "sum 2×2", "codel", 14, P.blue, "middle")
    bx = mx + 8 * c + 160
    for j in range(4):
        for i in range(4):
            ch = quad[j % 2][i % 2]
            svg.rect(bx + i * 2 * c, y0 + j * 2 * c, 2 * c - 3, 2 * c - 3, cols[ch], rx=4)
            svg.text(bx + i * 2 * c + c - 1.5, y0 + j * 2 * c + c + 6, ch, "code", 16, P.white, "middle")
    svg.text(bx, y0 - 14, "12 MP · 2.4 µm", "code", 16, P.blue)
    tx = bx + 8 * c + 34
    svg.text(tx, y0 + 30, "same colour", "codel", 15, P.black_60)
    svg.text(tx, y0 + 54, "in each 2×2", "codel", 15, P.black_60)
    svg.text(tx, y0 + 78, "block: so the", "codel", 15, P.black_60)
    svg.text(tx, y0 + 102, "sum stays a", "codel", 15, P.black_60)
    svg.text(tx, y0 + 126, "colour sample", "codel", 15, P.black_60)

    # the same dim scene, as photons
    def scene(u, v):
        tri = v > 0.22 and abs(u - 0.5) < (v - 0.22) * 0.62 and v < 0.82
        return 0.25 + 0.15 * u + (0.6 if tri else 0.0)

    n_small, ph = 48, 330
    lam = 9.0
    py_ = 662
    for k, (nn, binned) in enumerate([(n_small, False), (n_small // 2, True)]):
        px0 = M if k == 0 else W - M - ph
        cs = ph / nn
        vmax = lam * (4 if binned else 1) * 1.2
        for j in range(nn):
            for i in range(nn):
                u, v = (i + 0.5) / nn, (j + 0.5) / nn
                if binned:
                    n = sum(_poisson(rng, lam * scene(u + du / n_small, v + dv / n_small)) for du in (-0.5, 0.5)
                            for dv in (-0.5, 0.5))
                else:
                    n = _poisson(rng, lam * scene(u, v))
                svg.rect(px0 + i * cs, py_ + j * cs, cs + 0.3, cs + 0.3, mix(P.black, P.lavender_20, min(n / vmax, 1)))
        snr = math.sqrt(lam * (4 if binned else 1))
        lab = f"binned · ~{lam * 4:.0f} photons · SNR {snr:.0f}" if binned else \
            f"full res · ~{lam:.0f} photons · SNR {snr:.0f}"
        svg.text(px0, py_ - 14, lab, "code", 15, P.blue if binned else P.black)
    svg.text(W / 2, py_ + ph / 2 - 10, "dusk,", "codel", 15, P.black_60, "middle")
    svg.text(W / 2, py_ + ph / 2 + 14, "same light", "codel", 15, P.black_60, "middle")

    svg.frame("bin.", "drone camera · 1/1.3 in quad-Bayer sensor · 48 MP → 12 MP")
    brief(svg, "48 MP on a small sensor: 1.2 µm pixels catch few photons, so noise wins",
          "add up each 2×2 of same-colour pixels: ¼ the pixels, 2× the SNR")
    code_rule(svg)
    svg.code(M, CODE_Y, """
n   = photons(pixel_area)                  # ~9 per 1.2 µm pixel at dusk
snr = n / sqrt(n)                          # shot noise: SNR = √n = 3
img = raw.reshape(h//2, 2, w//2, 2).sum(axis=(1, 3))   # 4 pixels → 1
# 4× the photons → √4 = 2× the SNR. bright day: keep all 48 MP""", "py", 19)
    return svg


# ============================================================================
# gimbal
# ============================================================================
def _smooth(t, a, b):
    """0 before a, 1 after b, smoothstep between."""
    x = min(max((t - a) / (b - a), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def level() -> Svg:
    """The drone tips to fly; the gimbal measures the tip and turns the camera back, a thousand times a second."""
    svg = Svg(P.white)

    def body(t):  # pitch, degrees, nose down +: hover, accelerate, cruise, brake, hover
        th = 24 * _smooth(t, 0.6, 1.0) - 14 * _smooth(t, 2.6, 3.0) - 38 * _smooth(t, 5.0, 5.4) + 28 * _smooth(t, 6.4, 7.0)
        return th + 1.6 * math.sin(7.3 * t) + 0.9 * math.sin(17.1 * t + 1)

    dt, T = 0.0005, 8.0
    J, b, wn, z = 1.0, 6.0, 60.0, 0.7
    Kp, Kd = J * wn * wn, 2 * z * wn * J
    phi = dphi = 0.0
    ts, tb, tc = [], [], []
    prev = body(0)
    for i in range(int(T / dt)):
        t = i * dt
        tht = body(t)
        dth = (tht - prev) / dt if i else 0.0
        prev = tht
        tau = Kp * (0 - phi) - Kd * dphi
        ddphi = (tau + b * (dth - dphi)) / J
        dphi += ddphi * dt
        phi += dphi * dt
        if i % 8 == 0:
            ts.append(t)
            tb.append(tht)
            tc.append(phi)

    # three moments, drawn
    for t, label, cx in [(0.3, "hover", 250), (1.8, "accelerate", 540), (5.8, "brake", 830)]:
        th = body(t)
        cy = 405
        side_drone(svg, cx, cy, 1.05, th, P.black, P.blue_60, P.teal, gimbal_deg=0)
        a = math.radians(th)
        lx, ly = 44 * 1.05, 20 * 1.05
        px, py = cx + lx * math.cos(a) - ly * math.sin(a), cy + lx * math.sin(a) + ly * math.cos(a)
        svg.line(px + 8, py, px + 120, py, P.teal, 2, stroke_dasharray="3 5")
        svg.text(cx, cy + 82, label, "code", 17, P.black, "middle")
        svg.text(cx, cy + 106, f"body {th:+.0f}° · camera 0°", "codel", 14, P.black_60, "middle")

    x0, x1 = M + 70, W - M

    def gx(t):
        return x0 + (x1 - x0) * t / T

    yc, ys = 722, 3.9
    for d in (-30, -15, 0, 15, 30):
        svg.line(x0, yc - ys * d, x1, yc - ys * d, P.black_20, 1)
        axis_label(svg, x0 - 12, yc - ys * d + 5, f"{d:+d}°" if d else "0°", anchor="end")
    svg.polyline([(gx(t), yc - ys * v) for t, v in zip(ts, tb)], P.lavender, 3.5)
    svg.polyline([(gx(t), yc - ys * v) for t, v in zip(ts, tc)], P.blue, 3.5)
    svg.text(gx(3.6), yc - ys * 19, "drone body", "code", 16, P.lavender)
    svg.text(gx(3.4), yc + 26, "camera", "code", 16, P.blue)
    axis_label(svg, x0 - 12, yc - ys * 30 - 24, "pitch")

    yc2, ys2 = 935, 130
    svg.line(x0, yc2, x1, yc2, P.black_20, 1)
    for d in (-0.2, 0.2):
        svg.line(x0, yc2 - ys2 * d, x1, yc2 - ys2 * d, P.black_20, 1, stroke_dasharray="2 6")
        axis_label(svg, x0 - 12, yc2 - ys2 * d + 5, f"{d:+.1f}°", anchor="end")
    svg.polyline([(gx(t), yc2 - ys2 * v) for t, v in zip(ts, tc)], P.blue, 2.5)
    err = max(abs(v) for v in tc)
    axis_label(svg, x0 - 12, yc2 - ys2 * 0.2 - 24, f"camera error, zoomed in · worst {err:.2f}°")
    for t in range(0, 9, 2):
        axis_label(svg, gx(t), yc2 + 62, f"{t} s", anchor="middle")

    svg.frame("level.", "3-axis gimbal · pitch loop · 1 kHz · brushless motors")
    brief(svg, "to fly, the whole drone tips 20–30°; the picture would tip with it",
          "an IMU on the camera, a motor per axis, a loop that turns it back")
    code_rule(svg)
    svg.code(M, CODE_Y, """
while True:                                   # every 1 ms
    err = target - imu_cam.pitch              # where the camera points, in the world
    tau = Kp * err - Kd * imu_cam.rate        # motor torque, wn = 60 rad/s
    motor_pitch.torque(tau)                   # the body tips 30°, the camera 0.2°""", "py", 19)
    return svg


def damp() -> Svg:
    """Vibration isolation: soft rubber below a resonance passes slow motion and blocks the motor buzz."""
    svg = Svg(P.black)

    def trans(f, fn, z):
        r = f / fn
        return math.sqrt((1 + (2 * z * r) ** 2) / ((1 - r * r) ** 2 + (2 * z * r) ** 2))

    x0, x1, yt, yb = M + 70, W - M, 380, 780
    fl, fh, tl, th = 1, 1000, 0.01, 10

    def g(f, t):
        return (x0 + (x1 - x0) * math.log10(f / fl) / math.log10(fh / fl),
                yb - (yb - yt) * math.log10(t / tl) / math.log10(th / tl))

    for lo, hi, col, lab in [(120, 200, P.teal, "motors"), (240, 400, P.lavender, "blade pass")]:
        svg.rect(g(lo, th)[0], yt, g(hi, th)[0] - g(lo, th)[0], yb - yt, col, opacity="0.22")
        svg.text((g(lo, th)[0] + g(hi, th)[0]) / 2, yb + 50, lab, "codel", 13, col if col != P.teal else P.teal_60,
                 "middle")
    for f in (1, 10, 100, 1000):
        svg.line(g(f, tl)[0], yt, g(f, tl)[0], yb, P.black_80, 1)
        axis_label(svg, g(f, tl)[0], yb + 26, f"{f} Hz", True, "middle")
    for t, lab in [(0.01, "1 %"), (0.1, "10 %"), (1, "100 %"), (10, "×10")]:
        svg.line(x0, g(1, t)[1], x1, g(1, t)[1], P.black_80 if t != 1 else P.blue_80, 1 if t != 1 else 1.5)
        axis_label(svg, x0 - 12, g(1, t)[1] + 5, lab, True, "end")
    fs = [10 ** (3 * i / 400) for i in range(401)]
    fn_soft, fn_hard, z = 25.0, 160.0, 0.1
    svg.clip_begin(x0, yt, x1 - x0, yb - yt)
    svg.polyline([g(f, trans(f, fn_hard, z)) for f in fs], P.teal_60, 2.5, stroke_dasharray="6 6")
    svg.polyline([g(f, trans(f, fn_soft, z)) for f in fs], P.white, 4)
    svg.clip_end()
    pk = g(fn_soft, trans(fn_soft, fn_soft, z))
    svg.text(pk[0] - 10, pk[1] - 14, f"resonance {fn_soft:.0f} Hz", "code", 15, P.white, "end")
    pk2 = g(fn_hard, min(trans(fn_hard, fn_hard, z), 9))
    svg.text(pk2[0] - 16, pk2[1] + 6, "stiff mount", "code", 15, P.teal_60, "end")
    svg.text(pk2[0] - 16, pk2[1] + 28, "rings right on the motors", "codel", 13, P.teal_60, "end")
    q = g(150, trans(150, fn_soft, z))
    svg.circle(*q, 7, P.lavender)
    svg.text(q[0] - 16, q[1] + 6, f"150 Hz → {trans(150, fn_soft, z) * 100:.1f} %", "code", 16, P.lavender, "end")
    axis_label(svg, x0 - 12, yt - 20, "how much shake reaches the camera", True)

    # schematic: body, rubber, gimbal
    sx, sy = M + 130, 650
    svg.rect(sx - 60, sy - 34, 120, 14, P.blue_40, rx=4)
    for dx in (-36, 36):
        svg.circle(sx + dx, sy, 13, "none", stroke=P.lavender, stroke_width=3)
    svg.rect(sx - 46, sy + 18, 92, 34, P.white, rx=8)
    svg.circle(sx + 46, sy + 35, 8, P.teal_60)
    svg.text(sx + 74, sy - 22, "body", "codel", 13, P.blue_40)
    svg.text(sx + 74, sy + 4, "rubber", "codel", 13, P.lavender)
    svg.text(sx + 74, sy + 40, "gimbal", "codel", 13, P.white)

    # the buzz, in time
    yc = 920
    Ab = 44
    T1, T2 = trans(150, fn_soft, z), trans(300, fn_soft, z)
    ts = [i / 4000 * 0.04 for i in range(4001)]
    inp = [(x0 + (x1 - x0) * t / 0.04, yc - Ab * (0.7 * math.sin(2 * math.pi * 150 * t) + 0.3 * math.sin(2 * math.pi * 300 * t + 1)))
           for t in ts]
    out = [(x0 + (x1 - x0) * t / 0.04, yc - Ab * (0.7 * T1 * math.sin(2 * math.pi * 150 * t - math.pi) + 0.3 * T2 * math.sin(2 * math.pi * 300 * t + 1 - math.pi)))
           for t in ts]
    svg.polyline(inp, P.lavender, 1.6, opacity="0.7")
    svg.polyline(out, P.white, 3)
    axis_label(svg, x0 - 12, yc - 30, "body", True, "end")
    svg.text(x0 - 12, yc + 5, "camera", "codel", 14, P.white, "end")
    axis_label(svg, x1, yc + 66, "40 ms of hover", True, "end")

    svg.frame("damp.", "3-axis gimbal · rubber isolators · transmissibility", dark=True, title_fill=P.white)
    brief(svg, "four motors at ~150 rev/s shake the frame; the sensor sees jello",
          "hang the gimbal on soft rubber: tuned to 25 Hz, it passes ~4 %", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
r = f / fn                                   # fn = 25 Hz: rubber + gimbal mass
T = sqrt((1 + (2*z*r)**2) / ((1 - r**2)**2 + (2*z*r)**2))
# below √2·fn it amplifies, above it isolates: keep fn far under the motors
# at 150 Hz: T ≈ 0.045, so the buzz arrives 22× smaller""", "py", 19, dark=True)
    return svg


def _rot(axis, a):
    c, s_ = math.cos(a), math.sin(a)
    if axis == "x":
        return [[1, 0, 0], [0, c, -s_], [0, s_, c]]
    if axis == "y":
        return [[c, 0, s_], [0, 1, 0], [-s_, 0, c]]
    return [[c, -s_, 0], [s_, c, 0], [0, 0, 1]]


def _mv(m, v):
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def lock() -> Svg:
    """Gimbal lock: turn the middle axis 90° and the outer and inner axes line up."""
    svg = Svg(P.cream)

    def iso(c, s_):
        return lambda p: (c[0] + s_ * (p[0] - p[1]) * 0.866, c[1] + s_ * ((p[0] + p[1]) * 0.5 - p[2]))

    cols = {"yaw": P.teal, "roll": P.lavender, "pitch": P.blue}
    for k, (roll, cx, title) in enumerate([(0.0, 300, "roll 0°: three free axes"), (90.0, 780, "roll 90°: two")]):
        pr = iso((cx, 590), 92)
        Rz, Rx = _rot("z", 0.0), _rot("x", math.radians(roll))
        axes = {"yaw": [0, 0, 1], "roll": _mv(Rz, [1, 0, 0]), "pitch": _mv(_mm(Rz, Rx), [0, 1, 0])}
        radii = {"yaw": 1.25, "roll": 1.0, "pitch": 0.75}
        for name in ("yaw", "roll", "pitch"):
            a = axes[name]
            e1 = [0, 0, 1] if abs(a[2]) < 0.9 else [1, 0, 0]
            e1 = [e1[i] - a[i] * sum(e1[j] * a[j] for j in range(3)) for i in range(3)]
            n1 = math.sqrt(sum(v * v for v in e1))
            e1 = [v / n1 for v in e1]
            e2 = [a[1] * e1[2] - a[2] * e1[1], a[2] * e1[0] - a[0] * e1[2], a[0] * e1[1] - a[1] * e1[0]]
            r = radii[name]
            ring = [pr([r * (math.cos(t) * e1[i] + math.sin(t) * e2[i]) for i in range(3)])
                    for t in [2 * math.pi * j / 96 for j in range(97)]]
            svg.polyline(ring, cols[name], 5 if name == "pitch" else 4, opacity="0.9")
        for name in ("yaw", "roll", "pitch"):
            a = axes[name]
            ln = 1.6 if name != "pitch" else 1.45
            arrow(svg, pr([-a[i] * ln for i in range(3)]), pr([a[i] * ln for i in range(3)]), cols[name], 2.5, 14)
        # camera at the centre, lens along its forward axis
        fwd = _mv(_mm(Rz, Rx), [1, 0, 0])
        svg.circle(*pr([0, 0, 0]), 16, P.black)
        svg.circle(*pr([fwd[i] * 0.35 for i in range(3)]), 7, P.teal_60)
        svg.text(cx, 388, title, "code", 18, P.black if k == 0 else P.blue, "middle")
        if k == 1:
            t = pr([0, 0, 1.6])
            svg.text(t[0] + 18, t[1] + 22, "yaw = pitch axis", "code", 15, P.blue)
    lx = M
    for name in ("yaw", "roll", "pitch"):
        svg.rect(lx, 772, 22, 5, cols[name])
        svg.text(lx + 30, 780, f"{name}", "codel", 15, P.black_80)
        lx += 120
    svg.text(W - M, 780, "outer → middle → inner", "codel", 15, P.black_60, "end")

    # how fast the motors must spin to keep up, by roll angle
    x0, x1, yt, yb = M + 70, W - M, 850, 990

    def g(r, v):
        return x0 + (x1 - x0) * r / 90, yb - (yb - yt) * min(v, 10) / 10

    for v in (1, 5, 10):
        svg.line(x0, g(0, v)[1], x1, g(0, v)[1], P.black_20, 1)
        axis_label(svg, x0 - 12, g(0, v)[1] + 5, f"×{v}", anchor="end")
    rs = [i * 0.1 for i in range(900)]
    svg.polyline([g(r, 1 / math.cos(math.radians(r))) for r in rs if 1 / math.cos(math.radians(r)) < 10.5], P.blue, 4)
    svg.line(g(90, 0)[0], yt, g(90, 0)[0], yb, P.blue, 2, stroke_dasharray="4 6")
    for r in (0, 30, 60, 90):
        axis_label(svg, g(r, 0)[0], yb + 24, f"{r}°", anchor="middle")
    axis_label(svg, x0, yt - 16, "motor speed for the same camera turn, by roll angle")
    q = g(80, 1 / math.cos(math.radians(80)))
    svg.text(q[0] - 14, q[1] + 6, "×5.8 at 80°", "code", 16, P.blue, "end")

    svg.frame("lock.", "3-axis gimbal · yaw → roll → pitch · gimbal lock")
    brief(svg, "turn the middle axis to 90° and the outer and inner axes line up",
          "keep roll small, and let the drone's own yaw take the big turns")
    code_rule(svg)
    svg.code(M, CODE_Y, """
R = Rz(yaw) @ Rx(roll) @ Ry(pitch)                # outer → inner
J = [z, Rz(yaw) @ x, Rz(yaw) @ Rx(roll) @ y]      # each motor's axis, in the world
det(J) == cos(roll)            # 90°: the pitch axis is the yaw axis, one turn lost
w_motor = w_cam / cos(roll)    # near the lock, the motors can't keep up""", "py", 19)
    return svg


def portrait() -> Svg:
    """Vertical video: crop a 16:9 frame and keep 32 % of it, or roll the camera 90° and keep it all."""
    svg = Svg(P.white)
    k = 466 / 3840
    W4, H4 = 3840, 2160
    cw = H4 * 9 / 16
    py0 = 524  # phone screen top
    ax, ay = M, py0 + W4 * k / 2 - H4 * k / 2
    svg.rect(ax, ay, W4 * k, H4 * k, P.lavender_20, stroke=P.black_20, stroke_width=1.5)
    svg.rect(ax + (W4 - cw) / 2 * k, ay, cw * k, H4 * k, P.lavender, stroke=P.black, stroke_width=2)
    svg.text(ax, ay - 16, "crop the landscape frame", "code", 17, P.black)
    svg.text(ax, ay + H4 * k + 34, f"{cw:.0f} × {H4} px · {cw * H4 / 1e6:.1f} MP", "code", 17, P.black)
    svg.text(ax, ay + H4 * k + 60, f"{cw * H4 / (W4 * H4) * 100:.0f} % of the frame,", "codel", 15, P.black_60)
    svg.text(ax, ay + H4 * k + 84, f"upscaled ×{H4 / cw:.2f} to fill 2160 wide", "codel", 15, P.black_60)
    bx = W - M - H4 * k - 14
    svg.rect(bx - 14, py0 - 14, H4 * k + 28, W4 * k + 28, "none", rx=26, stroke=P.black, stroke_width=3)
    svg.rect(bx, py0, H4 * k, W4 * k, P.blue, rx=4)
    svg.text(bx + H4 * k / 2, py0 + W4 * k / 2 - 6, f"{H4} × {W4}", "code", 20, P.white, "middle")
    svg.text(bx + H4 * k / 2, py0 + W4 * k / 2 + 22, f"{H4 * W4 / 1e6:.1f} MP · all of it", "codel", 15, P.lavender_20, "middle")

    # the camera head, from the front, before and after the roll
    heads = [(ax + W4 * k / 2, 0, P.black), (bx + H4 * k / 2, 90, P.blue)]
    for cx, rot, col in heads:
        cy = 415
        group(svg, cx, cy, rot)
        svg.rect(-46, -30, 92, 60, col, rx=12)
        svg.circle(0, 0, 18, P.white)
        svg.circle(0, 0, 9, P.teal)
        svg.rect(-30, -24, 14, 6, P.white, rx=2)
        end(svg)
    rx_, ry_ = heads[1][0], 415
    svg.arc(rx_, ry_, 66, math.radians(-160), math.radians(-70), P.blue, 3)
    svg.triangle(rx_ + 66 * math.cos(math.radians(-70)), ry_ + 66 * math.sin(math.radians(-70)), 14, P.blue,
                 math.radians(20))
    svg.text(rx_ - 74, ry_ - 48, "roll 90°", "code", 16, P.blue, "end")
    arrow(svg, (heads[0][0] + 80, 415), (rx_ - 90, 415), P.black_20, 2.5, 14)

    svg.frame("portrait.", "3-axis gimbal · true vertical · 9:16 without the crop")
    brief(svg, "phones want 9:16; cut from a 16:9 frame, only 32 % of the pixels are left",
          "the gimbal rolls the whole camera 90°, so the sensor shoots tall")
    code_rule(svg)
    svg.code(M, CODE_Y, """
crop = frame[:, (3840 - 1215)//2 :][:, :1215]    # 1215 × 2160: 2.6 MP
keep = 1215 * 2160 / (3840 * 2160)               # 0.32: and it's upscaled
gimbal.roll(90)                                  # the sensor itself turns
tall = frame                                     # 2160 × 3840: 8.3 MP, all of it""", "py", 19)
    return svg


# ============================================================================
# link
# ============================================================================
LINK = dict(p_tx=30.0, g_tx=3.0, g_rx=6.0, margin=6.0)  # dBm, dBi, dBi, dB
MODES = [("1080p60", 20, -85.0, P.blue), ("1080p30", 10, -90.0, P.blue_60), ("720p30", 4, -95.0, P.lavender),
         ("control only", 0.1, -108.0, P.teal)]  # name, Mbps, receiver sensitivity dBm


def _fspl(d_m, f_hz):
    return 20 * math.log10(d_m) + 20 * math.log10(f_hz) - 147.55


def _p_rx(d_m, f_hz):
    return LINK["p_tx"] + LINK["g_tx"] + LINK["g_rx"] - _fspl(d_m, f_hz)


def _range(sens, f_hz):
    need = sens + LINK["margin"]
    return 10 ** ((LINK["p_tx"] + LINK["g_tx"] + LINK["g_rx"] - need - 20 * math.log10(f_hz) + 147.55) / 20)


def budget() -> Svg:
    """Link budget: received power falls 6 dB per doubling; each video mode has a floor; the bitrate steps down."""
    svg = Svg(P.white)
    x0, x1, yt, yb = M + 70, W - M, ART_TOP + 40, 840
    dmin, dmax, pmax, pmin = 100, 30000, -40, -112

    def g(d, p):
        return (x0 + (x1 - x0) * math.log10(d / dmin) / math.log10(dmax / dmin),
                yt + (yb - yt) * (pmax - p) / (pmax - pmin))

    for d, lab in [(100, "100 m"), (300, ""), (1000, "1 km"), (3000, "3 km"), (10000, "10 km"), (30000, "30 km")]:
        svg.line(g(d, 0)[0], yt, g(d, 0)[0], yb, P.black_20, 1)
        if lab:
            axis_label(svg, g(d, 0)[0], yb + 26, lab, anchor="middle")
    for p in range(-40, -111, -10):
        axis_label(svg, x0 - 12, g(dmin, p)[1] + 5, f"{p}", anchor="end")
    axis_label(svg, x0 - 12, yt - 22, "received power, dBm")
    ds = [dmin * (dmax / dmin) ** (i / 300) for i in range(301)]
    for name, mbps, sens, col in MODES:
        y = g(dmin, sens + LINK["margin"])[1]
        svg.line(x0, y, x1, y, col, 1.5, stroke_dasharray="5 6")
        r = _range(sens, 2.44e9)
        if r < dmax:
            q = g(r, sens + LINK["margin"])
            svg.circle(*q, 7, col)
            svg.text(q[0] + 12, q[1] - 12, f"{r / 1000:.0f} km", "code", 16, col)
        svg.text(x0 + 8, y - 8, f"{name} · {mbps:g} Mbps", "codel", 14, col)
    svg.polyline([g(d, _p_rx(d, 5.8e9)) for d in ds], P.teal_60, 3)
    svg.polyline([g(d, _p_rx(d, 2.44e9)) for d in ds], P.black, 4)
    lab = g(250, _p_rx(250, 2.44e9))
    svg.text(lab[0] + 26, lab[1] - 26, "2.4 GHz", "code", 17, P.black)
    lab = g(160, _p_rx(160, 5.8e9))
    svg.text(lab[0] + 30, lab[1] + 40, "5.8 GHz", "code", 17, P.teal)
    svg.text(g(600, 0)[0], g(dmin, -52)[1], "−6 dB every time the distance doubles", "codel", 15, P.black_60)

    # what the screen shows, by distance
    y = 900
    prev = dmin
    for name, mbps, sens, col in MODES:
        r = min(_range(sens, 2.44e9), dmax)
        svg.rect(g(prev, 0)[0], y, g(r, 0)[0] - g(prev, 0)[0] - 3, 26, col, rx=4)
        if g(r, 0)[0] - g(prev, 0)[0] > 90:
            svg.text((g(prev, 0)[0] + g(r, 0)[0]) / 2, y + 18, name, "code", 14, P.white, "middle")
        prev = r
    axis_label(svg, x0 - 12, y + 18, "video", anchor="end")
    svg.text(x1, y + 60, f"{LINK['p_tx']:.0f} dBm out · {LINK['g_tx']:.0f} + {LINK['g_rx']:.0f} dBi antennas · "
             f"{LINK['margin']:.0f} dB margin · open sky", "codel", 14, P.black_60, "end")

    svg.frame("budget.", "video link · free-space path loss · 2.4 / 5.8 GHz")
    brief(svg, "the signal falls with distance squared: 10 km out, a trillionth is left",
          "trade bitrate for range: the video steps down instead of cutting out")
    code_rule(svg)
    svg.code(M, CODE_Y, """
fspl = 20*log10(d) + 20*log10(f) - 147.55       # free space, dB
p_rx = p_tx + g_tx + g_rx - fspl                 # what reaches the controller
mode = max(m for m in modes if p_rx - margin > m.sensitivity)   # by bitrate
# fewer bits per second need less signal: 1080p60 → 720p30 → control only""", "py", 19)
    return svg


def fresnel() -> Svg:
    """Line of sight is not enough: the radio needs a fat ellipse of clear air between the two antennas."""
    svg = Svg(P.cream)
    rng = random.Random(12)
    lam, D, h_tx = 3e8 / 2.44e9, 2000.0, 1.5
    trees = []
    x = 820.0
    while x < 1560:
        los30 = h_tx + (30 - h_tx) * x / D  # the low flight's line of sight: trees stay just under it
        trees.append((x, min(10 + 5 * rng.random(), los30 - 0.4), 0))
        x += 14 + 12 * rng.random()

    def ground(x):
        return 1.5 * math.sin(x / 260) + 1.0 * math.sin(x / 90 + 1)

    def worst(h_rx):
        best = None
        for tx, th, _ in trees:
            los = h_tx + (h_rx - h_tx) * tx / D
            h = th - los
            v = h * math.sqrt(2 * D / (lam * tx * (D - tx)))
            if best is None or v > best[0]:
                best = (v, tx, h)
        return best

    def j(v):
        return 0.0 if v <= -0.78 else 6.9 + 20 * math.log10(math.sqrt((v - 0.1) ** 2 + 1) + v - 0.1)

    vs = 3.0  # px per metre of height
    for k, (h_rx, y0, base) in enumerate([(30.0, ART_TOP + 40, 600), (90.0, 640, 968)]):
        x0, x1 = M, W - M

        def g(x, h, base=base):
            return x0 + (x1 - x0) * x / D, base - vs * h

        gl = [g(xx, ground(xx)) for xx in range(0, int(D) + 1, 10)]
        svg.poly(gl + [g(D, -8), g(0, -8)], P.teal_20)
        svg.polyline(gl, P.black, 2)
        # first Fresnel zone around the straight line
        up, dn, up60 = [], [], []
        for i in range(201):
            xx = D * i / 200
            los = h_tx + (h_rx - h_tx) * xx / D
            r = math.sqrt(lam * xx * (D - xx) / D)
            up.append(g(xx, los + r))
            dn.append(g(xx, los - r))
            up60.append(g(xx, los - 0.6 * r))
        svg.poly(up + dn[::-1], P.lavender, opacity="0.35")
        svg.polyline(up, P.lavender, 1.5)
        svg.polyline(dn, P.lavender, 1.5)
        svg.polyline(up60, P.blue_60, 1.2, stroke_dasharray="3 5")
        svg.polyline([g(0, h_tx), g(D, h_rx)], P.blue, 2.5)
        for tx, th, _ in trees:
            top = g(tx, th)
            svg.line(*g(tx, ground(tx)), top[0], top[1] + 8, P.black_60, 2)
            svg.circle(top[0], top[1] + 8, 8, P.teal_60, opacity="0.95")
        v, tx, h = worst(h_rx)
        loss = j(v)
        pilot = g(0, h_tx)
        svg.rect(pilot[0] - 4, pilot[1] - 4, 10, 18, P.black, rx=2)
        side_drone(svg, *g(D, h_rx), 0.42, 0, P.black, P.blue_60, P.teal)
        col = P.black if loss > 1 else P.blue
        svg.text(x0, y0 + 4, f"drone at {h_rx:.0f} m, 2 km out", "code", 18, col)
        if loss > 1:
            rr = 10 ** (-loss / 20)
            svg.text(x0, y0 + 28, f"line of sight clear, zone clipped: −{loss:.1f} dB, {(1 - rr) * 100:.0f} % less range",
                     "codel", 15, P.black_60)
        else:
            svg.text(x0, y0 + 28, "zone clear: no loss", "codel", 15, P.black_60)
    svg.text(W - M, 640, f"first Fresnel zone · r = {math.sqrt(lam * D / 4):.1f} m mid-way · heights ×{vs * D / (W - 2 * M):.1f}",
             "codel", 14, P.black_60, "end")
    svg.text(W - M, 664, "- - 60 % of it: the part to keep clear", "codel", 14, P.blue_60, "end")

    svg.frame("fresnel.", "video link · 2.4 GHz · first Fresnel zone · knife-edge loss")
    brief(svg, "radio fills an ellipse, not a line: trees under the line still cost signal",
          "fly higher, or raise the controller: keep 60 % of the zone clear")
    code_rule(svg)
    svg.code(M, CODE_Y, """
r  = sqrt(lam * d1 * d2 / (d1 + d2))            # zone radius: 7.8 m mid-way at 2 km
v  = h_obstacle * sqrt(2 * (d1 + d2) / (lam * d1 * d2))   # how deep it cuts in
J  = 6.9 + 20*log10(sqrt((v - .1)**2 + 1) + v - .1)       # knife-edge loss, dB
ok = clearance > 0.6 * r                         # the rule of thumb""", "py", 19)
    return svg


def hop() -> Svg:
    """Frequency hopping: listen between packets, then send on whichever channel is quiet."""
    svg = Svg(P.black)
    rng = random.Random(21)
    ch24 = [2405 + 10 * i for i in range(8)]
    ch58 = [5730 + 10 * i for i in range(12)]
    chans = [("2.4", f) for f in ch24] + [("5.8", f) for f in ch58]
    n_t = 36
    wifi24 = [2412, 2437, 2462]
    on = {c: [False] * n_t for c in wifi24}
    for c in wifi24:
        state = rng.random() < 0.5
        for t in range(n_t):
            if rng.random() < 0.18:
                state = not state
            on[c][t] = state
    stream = (14, 30)  # someone starts an 80 MHz stream on 5.8

    def noise(band, f, t):
        burst = 0.85 if rng.random() < (0.12 if band == "2.4" else 0.03) else 0.0  # phones, bluetooth, video senders
        if band == "2.4":
            return min(1.0, sum(0.95 for c in wifi24 if on[c][t] and abs(f - c) < 14) + burst + 0.08 * rng.random())
        busy = stream[0] <= t < stream[1] and 5735 <= f <= 5815
        return min(1.0, (0.9 if busy else 0.0) + burst + 0.06 * rng.random())

    grid = [[noise(b, f, t) for b, f in chans] for t in range(n_t)]
    cur, hops, fixed_hits, hop_hits = 3, [], 0, 0
    avg = [0.0] * len(chans)  # how busy each channel has been lately
    for t in range(n_t):
        if t:
            sensed = grid[t - 1]
            avg = [0.6 * a + 0.4 * v for a, v in zip(avg, sensed)]
            best = min(range(len(chans)), key=lambda i: avg[i] + (0.05 if chans[i][0] != chans[cur][0] else 0))
            if sensed[cur] > 0.3:
                cur = best
        hops.append(cur)
        _ = chans[cur]
        hop_hits += grid[t][cur] > 0.5
        fixed_hits += grid[t][3] > 0.5

    x0, gap = M + 50, 60
    cw = (W - M - x0 - gap) / len(chans)
    yt, ch = ART_TOP + 50, 13.0

    def cx(i):
        return x0 + i * cw + (gap if i >= len(ch24) else 0)

    for t in range(n_t):
        for i in range(len(chans)):
            v = grid[t][i]
            svg.rect(cx(i) + 1, yt + t * ch + 1, cw - 2, ch - 2, mix("#1A1A1A", P.blue_80, v))
    for t, i in enumerate(hops):
        hit = grid[t][i] > 0.5
        svg.rect(cx(i) + 3, yt + t * ch + 2, cw - 6, ch - 4, P.white if not hit else P.teal_60, rx=2)
    for t in range(1, n_t):
        a, b = hops[t - 1], hops[t]
        if a != b:
            svg.line(cx(a) + cw / 2, yt + t * ch, cx(b) + cw / 2, yt + t * ch, P.white, 1, opacity="0.5")
    yb = yt + n_t * ch
    svg.text(cx(0), yt - 14, "2.4 GHz · 8 channels", "code", 15, P.white)
    svg.text(cx(len(ch24)), yt - 14, "5.8 GHz · 12 channels", "code", 15, P.white)
    for i, f in [(0, 2405), (7, 2475), (8, 5730), (19, 5840)]:
        axis_label(svg, cx(i) + cw / 2, yb + 22, f"{f}", True, "middle")
    axis_label(svg, W - M, yb + 46, "MHz", True, "end")
    axis_label(svg, x0 - 12, yt + 10, "time", True, "end")
    arrow(svg, (x0 - 30, yt + 24), (x0 - 30, yt + 110), P.blue_40, 2, 12)
    tag(svg, cx(len(ch24)) + 1.2 * cw, yt + (stream[0] + 3) * ch + 4, "a neighbour starts", "codel", 13, P.white, bg=P.black)
    tag(svg, cx(len(ch24)) + 1.2 * cw, yt + (stream[0] + 4.6) * ch + 4, "an 80 MHz stream", "codel", 13, P.white, bg=P.black)

    ly = yb + 84
    svg.rect(M, ly - 13, 18, 14, P.white, rx=2)
    svg.text(M + 28, ly, "the link, hopping", "codel", 15, P.white)
    svg.rect(M + 230, ly - 13, 18, 14, P.blue_80, rx=2)
    svg.text(M + 258, ly, "someone else's traffic", "codel", 15, P.blue_40)
    svg.rect(M + 500, ly - 13, 18, 14, P.teal_60, rx=2)
    svg.text(M + 528, ly, "a slot lost", "codel", 15, P.teal_60)
    svg.text(M, ly + 36, f"slots lost: {hop_hits} of {n_t} hopping · {fixed_hits} of {n_t} on one fixed channel", "code", 16,
             P.lavender)

    svg.frame("hop.", "video link · dual band · frequency hopping", dark=True, title_fill=P.white)
    brief(svg, "2.4 GHz is shared with every router and phone in the park",
          "listen between packets, then hop to a quiet channel, across both bands", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
noise = scan(channels)                           # listen in the gaps
if noise[ch] > busy:                             # our channel got loud
    ch = argmin(recent_noise + band_switch_cost) # move: 2.4 ↔ 5.8 if need be
send(frame_slice, ch); tell_controller(ch)       # both ends hop together""", "py", 19, dark=True)
    return svg


def lag() -> Svg:
    """Glass-to-glass latency: whole frames wait at every stage; slices flow through."""
    svg = Svg(P.white)
    stages = [("capture", 16.7), ("isp", 12.0), ("encode", 16.7), ("radio", 18.0), ("decode", 12.0), ("display", 16.7)]
    jitter = 18.0
    cols = [P.black_60, P.teal_60, P.blue, P.lavender, P.teal, P.black]
    n_sl = 8
    x0, x1 = M + 120, W - M
    tmax = 130.0

    def gx(t):
        return x0 + (x1 - x0) * t / tmax

    def gantt(y0, slices, label):
        rh = 24
        fin = [[0.0] * slices for _ in stages]
        for si, (name, d) in enumerate(stages):
            dd = d / slices
            for k in range(slices):
                start = max(fin[si - 1][k] + (jitter if name == "decode" else 0.0) if si else k * dd,
                            fin[si][k - 1] if k else 0.0)
                fin[si][k] = start + dd
                svg.rect(gx(start), y0 + si * rh, max(gx(start + dd) - gx(start) - (1.5 if slices > 1 else 0), 2), rh - 6,
                         cols[si], rx=2)
            if slices == 1 or si == 0:
                pass
            svg.text(x0 - 14, y0 + si * rh + 14, name, "codel", 14, P.black_60, "end")
        total = fin[-1][-1]
        svg.line(gx(total), y0 - 8, gx(total), y0 + len(stages) * rh, P.black, 2)
        svg.text(gx(total) + 10, y0 + 6, f"{total:.0f} ms", "code", 20, P.black)
        svg.text(x0, y0 - 18, label, "code", 17, P.black)
        return total

    t_whole = gantt(ART_TOP + 60, 1, "whole frames: each stage waits for the last")
    t_slice = gantt(ART_TOP + 280, n_sl, f"{n_sl} slices: each stage starts on the first slice")
    for t in range(0, 131, 20):
        axis_label(svg, gx(t), ART_TOP + 470, f"{t} ms", anchor="middle")
    svg.text(gx(stages[0][1] + stages[1][1] + stages[2][1] + stages[3][1]) + 6, ART_TOP + 60 + 4 * 24 - 2, "jitter buffer",
             "codel", 12, P.black_60)

    # where the drone is vs where you see it
    yr = 915
    v = V_MAX
    x_now = W - M - 60
    scale = 190  # px per metre
    for m10 in range(0, 26):
        xx = x_now - m10 * 0.1 * scale
        if xx < M + 260:
            break
        svg.line(xx, yr + 48, xx, yr + (60 if m10 % 5 == 0 else 54), P.black_60, 1.2)
        if m10 % 5 == 0:
            axis_label(svg, xx, yr + 80, f"{m10 / 10:g} m", anchor="middle")
    svg.line(M + 260, yr + 48, x_now, yr + 48, P.black_60, 1.2)
    for t_lat, col, name in [(t_whole, P.lavender, "whole frames"), (t_slice, P.blue, "sliced")]:
        xs = x_now - v * t_lat / 1000 * scale
        top_drone(svg, xs, yr, 0.6, 0, P.black_20, P.white, col, P.black_20)
        svg.text(xs, yr - 46, f"{v * t_lat / 1000:.1f} m", "code", 16, col, "middle")
        svg.text(xs, yr - 26, name, "codel", 13, col, "middle")
    top_drone(svg, x_now, yr, 0.6, 0, P.black, P.lavender_20, P.lavender, P.teal)
    svg.text(x_now, yr - 46, "now", "code", 16, P.black, "middle")
    svg.text(M, yr - 10, f"at {v:.0f} m/s, the screen", "codel", 15, P.black_60)
    svg.text(M, yr + 14, "shows where it was", "codel", 15, P.black_60)

    svg.frame("lag.", "video link · glass-to-glass latency · 4K camera to 1080p screen")
    brief(svg, "every stage takes time; what you see is where the drone was",
          "encode and send in slices, so the stages overlap instead of queueing")
    code_rule(svg)
    svg.code(M, CODE_Y, f"""
for s in slices(frame, {n_sl}):          # don't wait for the whole frame
    radio.send(encode(isp(s)))        # each slice leaves while the next is read
latency = sum(stage) / {n_sl} + max(stage) * (1 - 1/{n_sl}) + jitter   # ≈ {t_slice:.0f} ms
# whole frames: {t_whole:.0f} ms. at 16 m/s that's {v * t_whole / 1000:.1f} m behind the truth""", "py", 19)
    return svg


# ============================================================================
# navigate
# ============================================================================
def bowl() -> Svg:
    """Toilet-bowling: position hold with a compass that's off. Every push lands rotated; past ~70° it spirals out."""
    svg = Svg(P.black)
    kp, kd, dt, T = 1.0, 1.6, 0.01, 24.0
    cases = [(0, "compass right"), (45, "off by 45°"), (80, "off by 80°")]
    runs = []
    for deg, _ in cases:
        e = cmath.exp(1j * math.radians(deg))
        z, v = complex(4, 0), 0j
        tr = []
        for i in range(int(T / dt)):
            a = -e * (kp * z + kd * v)  # the push, rotated by the heading error
            v += a * dt
            z += v * dt
            tr.append((i * dt, z))
        runs.append(tr)

    pw, gap, y0 = 288, 24, ART_TOP + 60
    lim = 9.0
    cols = [P.teal_60, P.lavender, P.white]
    for k, ((deg, name), tr, col) in enumerate(zip(cases, runs, cols)):
        x0 = M + k * (pw + gap)
        c = (x0 + pw / 2, y0 + pw / 2)
        sc = pw / 2 / lim
        svg.rect(x0, y0, pw, pw, "#151515", rx=8)
        for r in (2, 4, 6, 8):
            svg.circle(*c, r * sc, "none", stroke=P.black_80, stroke_width=1)
        svg.clip_begin(x0, y0, pw, pw)
        pts_ = [(c[0] + z.real * sc, c[1] - z.imag * sc) for _, z in tr[::3]]
        svg.polyline(pts_, col, 2.5)
        svg.clip_end()
        svg.circle(*c, 5, P.blue_40)
        svg.circle(c[0] + 4 * sc, c[1], 6, P.black, stroke=col, stroke_width=2.5)
        svg.text(x0, y0 - 16, name, "code", 17, col)
        # the compass needle: true north vs what it reads
        nx, ny = x0 + pw - 30, y0 + 30
        svg.line(nx, ny + 18, nx, ny - 18, P.black_60, 2)
        a = math.radians(deg)
        svg.line(nx, ny, nx + 20 * math.sin(a), ny - 20 * math.cos(a), col, 3, stroke_linecap="round")
    svg.text(M, y0 + pw + 30, "hold point ·  start 4 m off (a gust) ·  rings every 2 m", "codel", 14, P.blue_40)

    # distance from the hold point over time
    x0, x1, yt, yb = M + 70, W - M, 770, 985

    def g(t, d):
        return x0 + (x1 - x0) * t / T, yb - (yb - yt) * d / 10

    for d in (0, 5, 10):
        svg.line(x0, g(0, d)[1], x1, g(0, d)[1], P.black_80, 1)
        axis_label(svg, x0 - 12, g(0, d)[1] + 5, f"{d} m", True, "end")
    for t in range(0, 25, 6):
        axis_label(svg, g(t, 0)[0], yb + 24, f"{t} s", True, "middle")
    for tr, col in zip(runs, cols):
        svg.clip_begin(x0, yt - 4, x1 - x0, yb - yt + 8)
        svg.polyline([g(t, abs(z)) for t, z in tr[::5]], col, 3)
        svg.clip_end()
    axis_label(svg, x0 - 12, yt - 22, "distance from the hold point", True)
    svg.text(g(9.6, 8.6)[0], g(9.6, 8.6)[1], "off by 80°: spirals out", "code", 16, P.white)
    svg.text(g(6.5, 1.6)[0], g(6.5, 1.6)[1], "0° and 45°: settle", "code", 16, P.lavender)

    svg.frame("bowl.", "position hold · compass heading error · toilet-bowling", dark=True, title_fill=P.white)
    brief(svg, "near steel or power lines, a wrong compass turns 'hold still' into a spiral",
          "calibrate away from metal; cross-check heading against GPS velocity", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
a = R(heading_error) @ (-kp * e - kd * v)     # each push lands rotated
# small error: it curls in. past ~70°: s² + kd·e^{iδ}s + kp·e^{iδ} goes unstable
if angle(v_gps, v_expected) > limit:          # moving where it didn't push?
    distrust_compass(); hold_by_gps_velocity()     # the "compass error" warning""", "py", 19, dark=True)
    return svg


def home() -> Svg:
    """Return to home: climb, fly back, descend; then match the photo it took at takeoff to land on the spot."""
    svg = Svg(P.white)
    rng = random.Random(14)
    x0, x1, yb = M + 30, W - M, 640
    X, Hm = 600.0, 78.0
    sx, sy = (x1 - x0) / X, (yb - (ART_TOP + 30)) / Hm

    def g(x, h):
        return x0 + x * sx, yb - h * sy

    svg.line(x0 - 30, yb, x1, yb, P.black, 2.5)
    for tx in range(250, 360, 14):  # a tree line between the drone and home
        th = 30 + 12 * rng.random()
        svg.line(*g(tx, 0), *g(tx, th - 6), P.black_60, 2)
        svg.circle(*g(tx, th - 6), 10, P.teal_60)
    rth_h = 60.0
    drone = (520.0, 22.0)
    path_ = [g(*drone), g(drone[0], rth_h), g(0, rth_h), g(0, 0)]
    svg.polyline([g(*drone), g(0, 0)], P.black_20, 2, stroke_dasharray="4 7")
    svg.polyline(path_, P.blue, 4)
    for a, b in zip(path_, path_[1:]):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        svg.triangle(*mid, 16, P.blue, ang)
    side_drone(svg, *g(*drone), 0.55, 0)
    svg.rect(g(0, 0)[0] - 16, yb - 6, 32, 6, P.black)
    svg.text(g(0, 0)[0], yb + 28, "home", "code", 16, P.black, "middle")
    svg.text(g(drone[0], rth_h)[0] + 14, g(drone[0], rth_h)[1] + 30, "1 · climb", "code", 15, P.blue)
    svg.text(g(300, rth_h)[0], g(300, rth_h)[1] - 14, "2 · straight back, above the trees", "code", 15, P.blue, "middle")
    svg.text(g(0, rth_h)[0] + 14, g(0, rth_h * 0.45)[1], "3 · descend", "code", 15, P.blue)
    svg.text(g(300, 2)[0], yb + 28, "a straight line home goes through them", "codel", 14, P.black_60, "middle")
    svg.text(x1, g(0, rth_h)[1] + 5, f"{rth_h:.0f} m", "codel", 14, P.black_60, "end")

    # the landing, from above
    y0, ph = 735, 230
    sc = 34  # px per metre
    for k, (name, sig, col) in enumerate([("GPS only · σ 1.5 m", 1.5, P.lavender), ("+ vision match · σ 0.1 m", 0.1, P.blue)]):
        px0 = M + k * (ph + 160)
        c = (px0 + ph / 2, y0 + ph / 2)
        svg.rect(px0, y0, ph, ph, P.teal_20, rx=6)
        svg.clip_begin(px0, y0, ph, ph)
        lake = [(px0 + ph * 0.72 + 14 * math.sin(j / 3), y0 + ph * j / 20) for j in range(21)]
        svg.poly(lake + [(px0 + ph + 10, y0 + ph), (px0 + ph + 10, y0)], P.lavender_20)
        svg.polyline(lake, P.blue_40, 1.5)
        svg.circle(*c, 0.45 * sc, P.white, stroke=P.black, stroke_width=2)
        svg.text(c[0], c[1] + 5, "H", "code", 14, P.black, "middle")
        wet = 0
        for _ in range(60):
            p = (c[0] + rng.gauss(0, sig) * sc, c[1] + rng.gauss(0, sig) * sc)
            svg.circle(*p, 3.2, col, opacity="0.85")
            wet += p[0] > px0 + ph * 0.72
        svg.clip_end()
        svg.text(px0, y0 - 14, name, "code", 15, col if k else P.black)
        svg.text(px0, y0 + ph + 26, f"{wet} of 60 landings in the water" if wet else "0 of 60 in the water",
                 "codel", 14, P.black_60)
    tx = M + 2 * (ph + 160) - 120
    svg.text(tx, y0 + 30, "at takeoff it photographs", "codel", 15, P.black_60)
    svg.text(tx, y0 + 54, "the ground below; coming", "codel", 15, P.black_60)
    svg.text(tx, y0 + 78, "down, it matches that", "codel", 15, P.black_60)
    svg.text(tx, y0 + 102, "picture and steers onto it", "codel", 15, P.black_60)

    svg.frame("home.", "return to home · climb, cruise, descend · precision landing")
    brief(svg, "GPS lands it a metre or two from takeoff; sometimes that's in the lake",
          "climb over the trees, fly back, then land on the photo it took leaving")
    code_rule(svg)
    svg.code(M, CODE_Y, """
climb_to(max(rth_alt, obstacles_ahead + margin))   # 1: up and over
fly_to(home.gps)                                    # 2: straight back, GPS ±1.5 m
while alt > 0.5:                                    # 3: down, steering on the picture
    dx, dy = match(down_cam(), takeoff_photo);  move(-dx, -dy)""", "py", 19)
    return svg


def reserve() -> Svg:
    """Smart return: the battery it needs to get home grows with distance; it turns back where the two lines meet."""
    svg = Svg(P.cream)
    rate = 100 / 34.0  # % per minute
    v_out, v_home, alt, land_at = 8.0, 6.0, 60.0, 10.0  # m/s; v_home: 10 m/s into a 4 m/s wind
    dt = 1 / 60
    t, d, bat = 0.0, 0.0, 100.0
    ts, ds, bats, needs = [], [], [], []
    trig = None
    plan = [(5, v_out), (4, 0.0), (99, v_out)]  # minutes, speed: out, film for 4 min, further out

    def speed_at(t):
        acc = 0.0
        for dur, v in plan:
            if t < acc + dur:
                return v
            acc += dur
        return 0.0

    while True:
        need = land_at + rate * (d / v_home + alt / 3.0) / 60
        ts.append(t)
        ds.append(d)
        bats.append(bat)
        needs.append(need)
        if trig is None and bat <= need + 0.05:
            trig = (t, d, bat)
        v = -v_home if trig else speed_at(t)
        d = max(0.0, d + v * dt * 60)
        bat -= rate * dt
        t += dt
        if trig and d <= 0:
            t_land = t + alt / 3.0 / 60
            bat_land = bat - rate * alt / 3.0 / 60
            break

    x0, x1 = M + 70, W - M
    T = 32.0

    def gx(t):
        return x0 + (x1 - x0) * t / T

    # distance
    yt, yb, dmax = ART_TOP + 40, 560, 6000
    for dd in (0, 3000, 6000):
        y = yb - (yb - yt) * dd / dmax
        svg.line(x0, y, x1, y, P.black_20, 1)
        axis_label(svg, x0 - 12, y + 5, f"{dd / 1000:g} km", anchor="end")
    svg.polyline([(gx(t), yb - (yb - yt) * d / dmax) for t, d in zip(ts, ds)], P.black, 3.5)
    axis_label(svg, x0 - 12, yt - 20, "distance from home")
    svg.text(gx(5.5), yb - (yb - yt) * (5 * 60 * v_out) / dmax - 14, "filming", "codel", 14, P.black_60)

    # battery
    yt2, yb2 = 620, 985

    def gy(pct):
        return yb2 - (yb2 - yt2) * pct / 100

    for pc in (0, 25, 50, 75, 100):
        svg.line(x0, gy(pc), x1, gy(pc), P.black_20, 1)
        axis_label(svg, x0 - 12, gy(pc) + 5, f"{pc} %", anchor="end")
    i_tr = next(i for i, t in enumerate(ts) if t >= trig[0])
    svg.poly([(gx(t), gy(b)) for t, b in zip(ts[:i_tr], bats[:i_tr])] +
             [(gx(t), gy(n)) for t, n in zip(ts[:i_tr], needs[:i_tr])][::-1], P.lavender, opacity="0.25")
    svg.polyline([(gx(t), gy(n)) for t, n in zip(ts[:i_tr + 1], needs[:i_tr + 1])], P.blue, 3.5)
    svg.polyline([(gx(t), gy(n)) for t, n in zip(ts[i_tr:], needs[i_tr:])], P.blue, 2, stroke_dasharray="4 6")
    svg.polyline([(gx(t), gy(b)) for t, b in zip(ts, bats)] + [(gx(t_land), gy(bat_land))], P.black, 3.5)
    svg.line(gx(0), gy(land_at), x1, gy(land_at), P.teal, 1.5, stroke_dasharray="3 6")
    svg.text(gx(19), gy(land_at) - 8, f"land with {land_at:.0f} %", "codel", 14, P.teal)
    q = (gx(trig[0]), gy(trig[2]))
    svg.line(q[0], yt, q[0], yb2, P.blue, 1.5, stroke_dasharray="3 6")
    svg.circle(*q, 9, P.blue)
    svg.text(q[0] + 16, q[1] - 14, f"turn back · {trig[0]:.1f} min · {trig[1] / 1000:.1f} km out", "code", 16, P.blue)
    svg.text(gx(4.5), gy(97), "battery left", "code", 16, P.black)
    svg.text(gx(2.6), gy(37), "battery needed to get home", "code", 16, P.blue)
    svg.text(gx(t_land) - 6, gy(bat_land) + 24, f"lands with {bat_land:.0f} %", "codel", 14, P.black_60, "end")
    for t in range(0, 31, 5):
        axis_label(svg, gx(t), yb2 + 24, f"{t} min", anchor="middle")
    svg.text(q[0] + 16, yb - 14, f"{trig[1] / 1000:.1f} km", "code", 15, P.blue)

    svg.frame("reserve.", "smart return to home · battery vs distance · into a 4 m/s wind")
    brief(svg, "the trip home costs more battery the further out you fly",
          "work out that cost every second; turn back where the lines meet")
    code_rule(svg)
    svg.code(M, CODE_Y, """
t_home = d / v_home + alt / v_descend          # v_home: airspeed - headwind
need   = land_reserve + drain_rate * t_home    # % to get back with 10 % left
if battery <= need:                            # the lines meet
    return_to_home()                           # not a fixed 30 %: it depends""", "py", 19)
    return svg


def avoid() -> Svg:
    """Obstacle sensing: stopping distance grows as v²; the cameras see ~18 m; so avoidance caps the speed."""
    svg = Svg(P.white)
    a, t_r, R, margin = G * math.tan(math.radians(35)), 0.3, 18.0, 2.0

    def d_stop(v):
        return v * t_r + v * v / (2 * a)

    v_safe = a * (-t_r + math.sqrt(t_r * t_r + 2 * (R - margin) / a))
    x0, x1 = M + 140, W - M - 20
    Dm = 26.0

    def gx(d):
        return x0 + (x1 - x0) * d / Dm

    y0 = ART_TOP + 70
    svg.rect(gx(R), y0 - 40, 10, 3 * 92 + 10, P.black, rx=3)
    svg.text(gx(R) + 18, y0 - 26, f"obstacle, first seen at {R:.0f} m", "codel", 14, P.black_60)
    for k, v in enumerate([8.0, v_safe, V_MAX]):
        y = y0 + k * 92
        top_drone(svg, gx(0) - 28, y + 10, 0.5, 0, P.black, P.lavender_20, P.lavender, P.teal)
        r, b = v * t_r, v * v / (2 * a)
        hit = r + b > R
        svg.rect(gx(0), y, gx(r) - gx(0), 20, P.lavender, rx=3)
        svg.rect(gx(r), y, gx(r + b) - gx(r), 20, P.teal_60 if hit else P.blue, rx=3)
        svg.text(M, y + 16, f"{v:.1f} m/s" if v == v_safe else f"{v:.0f} m/s", "code", 17,
                 P.blue if v == v_safe else P.black)
        lab = f"needs {r + b:.1f} m" + (" · hits it" if hit else " · stops in time")
        svg.text(gx(0), y + 44, lab, "codel", 15, P.teal if hit else P.blue)
    svg.rect(M, y0 + 3 * 92 - 4, 16, 12, P.lavender, rx=2)
    svg.text(M + 24, y0 + 3 * 92 + 7, f"seeing + deciding · {t_r} s", "codel", 14, P.black_60)
    svg.rect(M + 300, y0 + 3 * 92 - 4, 16, 12, P.blue, rx=2)
    svg.text(M + 324, y0 + 3 * 92 + 7, f"braking at 35° tilt · {a:.1f} m/s²", "codel", 14, P.black_60)

    # stopping distance against speed
    px0, px1, yt, yb = M + 70, W - M, 760, 985

    def g(v, d):
        return px0 + (px1 - px0) * v / V_MAX, yb - (yb - yt) * d / 26

    for d in (0, 10, 20):
        svg.line(px0, g(0, d)[1], px1, g(0, d)[1], P.black_20, 1)
        axis_label(svg, px0 - 12, g(0, d)[1] + 5, f"{d} m", anchor="end")
    for v in range(0, 17, 4):
        axis_label(svg, g(v, 0)[0], yb + 24, f"{v} m/s", anchor="middle")
    svg.rect(px0, g(0, R)[1], px1 - px0, g(0, R - margin)[1] - g(0, R)[1], P.teal_20)
    svg.line(px0, g(0, R)[1], px1, g(0, R)[1], P.teal, 2, stroke_dasharray="5 6")
    svg.polyline([g(v / 10, d_stop(v / 10)) for v in range(0, 161)], P.black, 3.5)
    q = g(v_safe, R - margin)
    svg.circle(*q, 8, P.blue)
    svg.line(q[0], q[1], q[0], yb, P.blue, 1.5, stroke_dasharray="3 5")
    svg.text(px0 + 8, g(0, R - margin)[1] + 34, f"avoidance on: max {v_safe:.1f} m/s", "code", 16, P.blue)
    axis_label(svg, px0 - 12, yt - 20, "distance to stop")
    svg.text(px0 + 8, g(0, R)[1] - 10, "what the cameras can see: 18 m", "codel", 14, P.teal)

    svg.frame("avoid.", "obstacle sensing · stereo vision range · stopping distance")
    brief(svg, "small stereo cameras see ~18 m; at 16 m/s it needs 23 m to stop",
          "with avoidance on, cap the speed at what it can stop inside what it sees")
    code_rule(svg)
    svg.code(M, CODE_Y, """
d_stop = v * t_react + v**2 / (2 * g * tan(tilt_max))   # see, decide, brake
v_max  = solve(d_stop(v) == range - margin)             # 18 m → 12.9 m/s
# why 18 m: depth error grows as z² / (f · baseline), and the baseline is 5 cm
# the fastest mode switches avoidance off: there it can't stop in time""", "py", 19)
    return svg


# ============================================================================
# missions
# ============================================================================
def orbit() -> Svg:
    """Point of interest: circle a subject with the camera on it; the wind makes every part of the circle different."""
    svg = Svg(P.black)
    r, h, v, w = 40.0, 30.0, 6.0, 5.0  # radius, height, ground speed, wind from the left (m/s)
    CdA = 0.0226
    c, R = (W / 2, 600), 205
    svg.circle(*c, R, "none", stroke=P.blue_80, stroke_width=2, stroke_dasharray="3 7")
    for k in range(5):  # the wind, from the left
        yy = c[1] - 200 + 100 * k
        arrow(svg, (M, yy), (M + 64, yy), P.blue_60, 2, 11)
    svg.text(M, c[1] + 280, f"wind {w:.0f} m/s", "codel", 14, P.blue_40)

    def state(th):  # th: angle around the circle (page coords), drone flies counter-clockwise on screen
        pos = (math.cos(th), math.sin(th))
        vg = (v * math.sin(th), -v * math.cos(th))  # tangent
        va = (vg[0] - w, vg[1])  # air-relative velocity
        sa = math.hypot(*va)
        drag = 0.5 * RHO * CdA * sa * sa
        ac = v * v / r
        fx = MASS * ac * -pos[0] + drag * va[0] / sa
        fy = MASS * ac * -pos[1] + drag * va[1] / sa
        lean = math.degrees(math.atan(math.hypot(fx, fy) / (MASS * G)))
        return pos, vg, sa, lean

    half = math.radians(71.2 / 2)
    for k in range(12):
        th = 2 * math.pi * k / 12
        pos, vg, sa, lean = state(th)
        p = (c[0] + R * pos[0], c[1] + R * pos[1])
        to_c = math.atan2(c[1] - p[1], c[0] - p[0])
        L = R * 0.92
        svg.poly([p, (p[0] + L * math.cos(to_c - half), p[1] + L * math.sin(to_c - half)),
                  (p[0] + L * math.cos(to_c + half), p[1] + L * math.sin(to_c + half))], P.lavender, opacity="0.05")
        top_drone(svg, *p, 0.42, to_c, P.white, P.black, P.lavender, P.teal_60)
        sc = 7
        arrow(svg, (p[0] + vg[0] / v * 26, p[1] + vg[1] / v * 26),
              (p[0] + vg[0] / v * (26 + sa * sc * 0.0) + vg[0] * sc, p[1] + vg[1] * sc + vg[1] / v * 26), P.blue_40, 2, 10)
        lab = (c[0] + (R + 58) * pos[0], c[1] + (R + 58) * pos[1] + 5)
        svg.text(*lab, f"{lean:.0f}°", "code", 15, P.white if lean > 15 else P.blue_40, "middle")
    svg.triangle(c[0], c[1] + 6, 40, P.teal_60, -math.pi / 2)
    svg.text(c[0], c[1] + 46, "subject", "codel", 14, P.teal_60, "middle")
    leans = [state(2 * math.pi * k / 360)[3] for k in range(360)]
    svg.text(W - M, c[1] + 280, f"numbers: lean needed · {min(leans):.0f}° to {max(leans):.0f}°", "codel", 14, P.blue_40,
             "end")
    svg.text(W - M, c[1] + 304, f"r {r:.0f} m · {h:.0f} m up · {v:.0f} m/s · gimbal {-math.degrees(math.atan(h / r)):.0f}°",
             "codel", 14, P.blue_40, "end")

    svg.frame("orbit.", "point of interest · yaw on the subject · constant ground speed", dark=True,
              title_fill=P.white)
    brief(svg, "a circle in wind: the same ground speed needs a different lean all the way round",
          "fix the subject's point; steer yaw, gimbal and speed from that, every tick", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
theta += v / r * dt                          # constant speed over the ground
yaw    = bearing(drone, subject)             # nose, and camera, on the subject
pitch  = -atan(h / r)                        # gimbal: 30 m up, 40 m out → -37°
lean   = atan(|m * v**2/r + drag(v - wind)| / (m * g))   # upwind side works harder""", "py", 19, dark=True)
    return svg


def map() -> Svg:
    """Photogrammetry: a lawnmower grid with 80 % / 70 % overlap, so every point is in many photos."""
    svg = Svg(P.white)
    alt = 60.0
    fw, fh = alt * SENSOR_MM[0] / FOCAL_MM, alt * SENSOR_MM[1] / FOCAL_MM  # across, along track
    front, side = 0.8, 0.7
    ds, dl = fh * (1 - front), fw * (1 - side)
    FX, FY = 280.0, 100.0
    sc = (W - 2 * M) / (FX + fh)
    x0, y0 = M + fh / 2 * sc, ART_TOP + 40 + fw / 2 * sc

    def g(x, y):
        return x0 + x * sc, y0 + y * sc

    lines = math.ceil(FY / dl) + 1
    ys = [FY / 2 - dl * (lines - 1) / 2 + i * dl for i in range(lines)]
    shots = []
    for i, yy in enumerate(ys):
        xs = [-fh / 2 + k * ds for k in range(int((FX + fh) / ds) + 1)]
        if i % 2:
            xs = xs[::-1]
        shots += [(xx, yy) for xx in xs]
    # coverage: how many photos see each 3 m cell
    cell = 3.0
    svg.clip_begin(*g(0, 0), FX * sc, FY * sc)
    for gy_ in range(int(FY / cell)):
        for gx_ in range(int(FX / cell)):
            px, py = (gx_ + 0.5) * cell, (gy_ + 0.5) * cell
            n = sum(1 for sx, sy in shots if abs(px - sx) <= fh / 2 and abs(py - sy) <= fw / 2)
            svg.rect(*g(gx_ * cell, gy_ * cell), cell * sc + 0.4, cell * sc + 0.4, mix(P.lavender_20, P.blue, min(n / 20, 1)))
    svg.clip_end()
    svg.rect(*g(0, 0), FX * sc, FY * sc, "none", stroke=P.black, stroke_width=2)
    path_ = [g(*p) for p in shots]
    svg.polyline(path_, P.black, 1.5, opacity="0.7")
    for p in path_:
        svg.circle(*p, 2.2, P.black)
    mid = len(shots) // 2 - 6
    for k in (mid, mid + 1):  # two consecutive footprints, drawn
        sx, sy = shots[k]
        svg.rect(*g(sx - fh / 2, sy - fw / 2), fh * sc, fw * sc, "none", stroke=P.white, stroke_width=5)
        svg.rect(*g(sx - fh / 2, sy - fw / 2), fh * sc, fw * sc, "none", stroke=P.teal, stroke_width=2.5,
                 stroke_dasharray="6 5" if k > mid else "1 0")
    sx, sy = shots[mid]
    tag(svg, g(sx - fh / 2, 0)[0] + 4, g(0, sy - fw / 2)[1] - 10, f"one photo: {fw:.0f} × {fh:.0f} m", "code", 14,
        P.teal)
    svg.rect(*g(0, 0), FX * sc, FY * sc, "none", stroke=P.black, stroke_width=2)
    fy_bot = g(0, ys[-1] + fw / 2)[1]
    svg.text(W - M, fy_bot + 6, f"{FX:.0f} × {FY:.0f} m field · {len(shots)} photos · {lines} passes",
             "code", 16, P.black, "end")
    # legend ramp
    ly = fy_bot + 36
    for i in range(23):
        svg.rect(M + i * 14, ly, 14, 12, mix(P.lavender_20, P.blue, min(i / 20, 1)))
    svg.rect(M, ly, 23 * 14, 12, "none", stroke=P.black_20, stroke_width=1)
    svg.text(M, ly + 34, "photos seeing each spot: 0 → 20", "codel", 14, P.black_60)
    gsd = alt * PIXEL_UM * 1e-6 / (FOCAL_MM * 1e-3) * 100
    svg.text(W - M, ly + 10, f"{alt:.0f} m up · 1 px = {gsd:.1f} cm on the ground", "code", 16, P.blue, "end")
    svg.text(W - M, ly + 34, f"{front * 100:.0f} % front · {side * 100:.0f} % side overlap · "
             f"a photo every {ds:.0f} m · lines {dl:.0f} m apart", "codel", 14, P.black_60, "end")

    svg.frame("map.", "photogrammetry · lawnmower survey · ground sample distance")
    brief(svg, "one photo can't measure depth; every spot needs to be seen from several places",
          "fly a grid where each photo overlaps the next by 80 % and the next line by 70 %")
    code_rule(svg)
    svg.code(M, CODE_Y, """
foot  = alt * sensor_mm / focal_mm          # 60 m up: 86 × 64 m per photo
step  = foot.along * (1 - 0.8)              # shoot every 13 m
lane  = foot.across * (1 - 0.7)             # next pass 26 m over
gsd   = alt * pixel_um / focal_mm           # 1.1 cm per pixel → a 3D model""", "py", 19)
    return svg


def follow() -> Svg:
    """Follow-me: the subject goes behind trees; a motion model keeps guessing until it's seen again."""
    svg = Svg(P.cream)
    rng = random.Random(17)
    dt, n = 0.25, 64
    occl = (24, 38)
    truth = []
    for i in range(n):
        t = i * dt
        truth.append((4.6 * t, 14 * math.sin(t / 2.6) + 2.0 * math.sin(t * 0.9)))
    x = [truth[0][0], truth[0][1], 4.6, 5.0]
    Pm = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    q, rm = 1.6, 0.5
    ests, covs, seen = [], [], []
    for i in range(n):
        F = [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]]
        x = [x[0] + dt * x[2], x[1] + dt * x[3], x[2], x[3]]
        FP = [[sum(F[a][k] * Pm[k][b] for k in range(4)) for b in range(4)] for a in range(4)]
        Pm = [[sum(FP[a][k] * F[b][k] for k in range(4)) for b in range(4)] for a in range(4)]
        for a, qa in [(0, dt**3 / 3), (1, dt**3 / 3), (2, dt), (3, dt)]:
            Pm[a][a] += q * q * qa
        for a, b in [(0, 2), (1, 3)]:
            Pm[a][b] += q * q * dt * dt / 2
            Pm[b][a] += q * q * dt * dt / 2
        vis = not (occl[0] <= i < occl[1])
        if vis:
            z = (truth[i][0] + rng.gauss(0, rm), truth[i][1] + rng.gauss(0, rm))
            for k in (0, 1):  # position measurements, one axis at a time
                S = Pm[k][k] + rm * rm
                K = [Pm[a][k] / S for a in range(4)]
                res = z[k] - x[k]
                x = [x[a] + K[a] * res for a in range(4)]
                Pm = [[Pm[a][b] - K[a] * Pm[k][b] for b in range(4)] for a in range(4)]
            seen.append(z)
        ests.append((x[0], x[1]))
        covs.append([[Pm[0][0], Pm[0][1]], [Pm[1][0], Pm[1][1]]])

    fm = fit(truth + [(-8, -26), (80, 22)], (M, ART_TOP + 30, W - M, 900), pad=10)
    # trees between the drone's side and the path
    i_mid = (occl[0] + occl[1]) // 2
    tc = truth[i_mid]
    for _ in range(14):
        p = fm((tc[0] + rng.uniform(-9, 9), tc[1] - 6 + rng.uniform(-4, 2)))
        svg.circle(*p, rng.uniform(18, 30), P.teal_60, opacity="0.9")
    svg.polyline([fm(p) for p in truth], P.black_60, 2, stroke_dasharray="2 7")
    for k in range(occl[0], occl[1], 2):
        svg.polyline([fm(p) for p in ellipse(ests[k], covs[k], 2)], P.lavender, 1.8)
    svg.polyline([fm(p) for p in ests[occl[0] - 1:occl[1] + 1]], P.lavender, 3)
    for z in seen:
        svg.circle(*fm(z), 4, P.blue)
    svg.polyline([fm(p) for p in ests[:occl[0]]], P.blue, 2.5)
    svg.polyline([fm(p) for p in ests[occl[1]:]], P.blue, 2.5)
    # the drone, trailing and looking at the estimate
    for i in (6, i_mid, n - 6):
        e = ests[i]
        vx, vy = ests[i][0] - ests[i - 2][0], ests[i][1] - ests[i - 2][1]
        L = math.hypot(vx, vy)
        dpos = (e[0] - 14 * vx / L - 6 * vy / L, e[1] - 14 * vy / L + 6 * vx / L - 12)
        a, b = fm(dpos), fm(e)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        svg.line(*a, *b, P.black_20, 1.5, stroke_dasharray="3 5")
        top_drone(svg, *a, 0.45, ang, P.black, P.lavender_20, P.lavender, P.teal)
    lab = fm((tc[0], tc[1] - 17))
    tag(svg, lab[0], lab[1], "hidden: predict, and grow the doubt", "code", 15, P.lavender, "middle", bg=P.cream)
    lab2 = fm(ests[occl[1] + 2])
    tag(svg, lab2[0] + 20, lab2[1] + 40, "seen again: snap back", "code", 15, P.blue, bg=P.cream)
    s0 = fm(truth[0])
    svg.text(s0[0], s0[1] - 18, "cyclist", "code", 15, P.black)
    ly = 950
    svg.circle(M + 6, ly - 5, 4, P.blue)
    svg.text(M + 20, ly, "detections", "codel", 14, P.black_60)
    svg.line(M + 140, ly - 5, M + 170, ly - 5, P.lavender, 3)
    svg.text(M + 180, ly, "prediction · 2σ", "codel", 14, P.black_60)
    svg.line(M + 340, ly - 5, M + 370, ly - 5, P.black_60, 2, stroke_dasharray="2 5")
    svg.text(M + 380, ly, "where they really went", "codel", 14, P.black_60)
    svg.text(W - M, ly, f"hidden {(occl[1] - occl[0]) * dt:.1f} s", "code", 15, P.lavender, "end")

    svg.frame("follow.", "subject tracking · constant-velocity kalman filter · occlusion")
    brief(svg, "the subject goes behind trees and the camera loses them",
          "predict where they'll come out with a motion model; look there")
    code_rule(svg)
    svg.code(M, CODE_Y, """
x, P = F @ x, F @ P @ F.T + Q          # every frame: move the guess on, doubt grows
if box := detect(frame):               # seen: pull the guess onto the detection
    x, P = update(x, P, box.center)
gimbal.aim(x[:2]); drone.trail(x, 14)  # hidden: keep flying toward the guess""", "py", 19)
    return svg


def pano() -> Svg:
    """Spherical panorama: 21 overlapping frames on yaw rings at four tilts, mapped onto latitude × longitude."""
    svg = Svg(P.black)
    hf, vf = math.radians(71.2), math.radians(56.5)
    rows = [(0, 8), (-30, 8), (-60, 4), (-90, 1)]
    x0, x1 = M, W - M
    pw = x1 - x0
    ph = pw / 2
    y0 = ART_TOP + 50

    def g(lon, lat):
        return x0 + pw * (lon + 180) / 360, y0 + ph * (90 - lat) / 180

    svg.rect(x0, y0, pw, ph, "#151515")
    for lat in range(-60, 61, 30):
        svg.line(*g(-180, lat), *g(180, lat), P.black_80, 1)
    for lon in range(-180, 181, 45):
        svg.line(*g(lon, 90), *g(lon, -90), P.black_80, 1)

    def outline(yaw, pitch):
        """The frame's edge, ray by ray, as (lon, lat) with longitude unwrapped."""
        tu, tv = math.tan(hf / 2), math.tan(vf / 2)
        R = _mm(_rot("z", math.radians(yaw)), _rot("y", -math.radians(pitch)))
        edge = []
        for u, v in ([(-1 + 2 * j / 24, 1) for j in range(24)] + [(1, 1 - 2 * j / 24) for j in range(24)] +
                     [(1 - 2 * j / 24, -1) for j in range(24)] + [(-1, -1 + 2 * j / 24) for j in range(24)]):
            w_ = _mv(R, [1.0, u * tu, v * tv])
            nrm = math.sqrt(sum(c * c for c in w_))
            lon, lat = math.degrees(math.atan2(w_[1], w_[0])), math.degrees(math.asin(w_[2] / nrm))
            if edge:
                while lon - edge[-1][0] > 180:
                    lon -= 360
                while lon - edge[-1][0] < -180:
                    lon += 360
            edge.append((lon, lat))
        if abs(edge[-1][0] - edge[0][0]) > 180:  # it went all the way round: it holds the pole
            edge += [(edge[-1][0], -90.0), (edge[0][0], -90.0)]
        return edge

    svg.clip_begin(x0, y0, pw, ph)
    n_shot = 0
    offsets = {0: -157.5, -30: -135.0, -60: -112.5, -90: 0.0}
    for pitch, n in rows:
        for k in range(n):
            yaw = offsets[pitch] + 360 * k / n
            e = outline(yaw, pitch)
            for off in (-360, 0, 360):
                svg.poly([g(lon + off, lat) for lon, lat in e], P.lavender, opacity="0.18", stroke=P.lavender,
                         stroke_width=1.5)
            n_shot += 1
            c = g((yaw + 180) % 360 - 180, max(pitch, -78))
            svg.text(c[0], c[1] + 6, f"{n_shot}", "code", 16, P.white, "middle")
    svg.clip_end()
    top0 = max(lat for _, lat in outline(0, 0))
    svg.line(*g(-180, top0), *g(180, top0), P.teal_60, 1.5, stroke_dasharray="4 6")
    svg.text(g(0, (90 + top0) / 2)[0], g(0, (90 + top0) / 2)[1] + 6, f"sky above +{top0:.0f}°: filled in by software",
             "code", 15, P.teal_60, "middle")
    for lon in (-180, -90, 0, 90, 180):
        axis_label(svg, g(lon, 0)[0], y0 + ph + 24, f"{lon:+d}°" if lon else "0°", True, "middle")
    for lat in (90, 0, -90):
        axis_label(svg, x0 - 10, g(0, lat)[1] + 5, f"{lat:+d}°" if lat else "0°", True, "end")
    axis_label(svg, x1, y0 + ph + 48, "yaw →   ·   one frame: 71° × 56°", True, "end")
    svg.text(x0, y0 + ph + 48, f"{n_shot} frames · rings at 0°, −30°, −60°, and one straight down", "code", 15,
             P.lavender)

    svg.frame("pano.", "spherical panorama · gimbal sweep · equirectangular stitch", dark=True, title_fill=P.white)
    brief(svg, "the lens sees 71° × 56°; a full sphere is 360° × 180°",
          "sweep the gimbal in rings of overlapping frames, then stitch them", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
for pitch, n in [(0, 8), (-30, 8), (-60, 4), (-90, 1)]:
    for yaw in linspace(-180, 180, n, endpoint=False):
        gimbal.point(yaw, pitch); shoot()          # 21 frames, ~25° overlap
sphere = stitch(frames)        # match features in the overlaps, warp, blend""", "py", 19, dark=True)
    return svg


# ============================================================================
# build
# ============================================================================
FAMILIES = {
    "airframe": ["anatomy", "weigh", "fold", "wind"],
    "camera": ["readout", "stops", "shutter", "bin"],
    "gimbal": ["level", "damp", "lock", "portrait"],
    "link": ["budget", "fresnel", "hop", "lag"],
    "navigate": ["bowl", "home", "reserve", "avoid"],
    "missions": ["orbit", "map", "follow", "pano"],
}
OUT = Path(__file__).resolve().parents[1] / "out/drone"


def missing_glyphs(svg: Svg) -> list[str]:
    """Characters drawn in a font that the font can't draw."""
    from fontTools.ttLib import TTFont

    bad = []
    for key, chars in svg.chars.items():
        if not chars:
            continue
        cmap = TTFont(BRAND / "fonts" / FONTS.files[key][1]).getBestCmap()
        bad += [f"{key}:{c!r}" for c in sorted(chars) if ord(c) not in cmap and not c.isspace()]
    return bad


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
