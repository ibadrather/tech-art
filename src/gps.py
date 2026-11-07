"""GPS / GNSS posters: how a receiver gets from radio noise to a position, and how that position gets good.

Every poster names one problem (issue) and how it's beaten (fix). The sky on them is computed:
GPS's 24-slot baseline (+7 spares), GLONASS, Galileo and BeiDou as circular Kepler orbits,
turning under a receiver at 52.5° N, 13.4° E.

Sky:      constellations. skyplot. relativity. wait.
Signal:   bands. code. doppler. iono.
Fix:      intersect. four. geoid. dop.
Error:    errors. multipath. canyon. cep.
Augment:  dgps. sbas. snap. ladder.

Run:  uv run --no-project --with fonttools --with brotli python src/gps.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from drone import ART_TOP, axis_label, brief, missing_glyphs  # noqa: E402
from localization import path, tag  # noqa: E402
from posters import CODE_Y, M, W, code_rule  # noqa: E402
from sensors import arrow  # noqa: E402

MU, WE, C = 3.986004418e14, 7.2921151467e-5, 299792458.0  # m³/s², rad/s, m/s
A_WGS, F_WGS = 6378137.0, 1 / 298.257223563
RE = 6371e3
RX = (52.5, 13.4, 60.0)  # the receiver on every poster: lat, lon (deg), ellipsoidal height (m)
F0 = 10.23e6  # every GPS frequency is a multiple of this
F_L1, F_L2, F_L5 = 154 * F0, 120 * F0, 115 * F0
CHIP = C / 1.023e6  # one C/A chip of range: 293 m


# ============================================================================
# the sky: circular Kepler orbits under a turning Earth
# ============================================================================
@dataclass(frozen=True)
class Sat:
    sys: str
    name: str
    a: float  # semi-major axis, m
    inc: float  # rad
    raan: float  # rad, at t = 0
    u0: float  # argument of latitude at t = 0, rad

    def inertial(self, t: float):
        n = math.sqrt(MU / self.a ** 3)
        return _orbit(self.a, self.inc, self.raan, self.u0 + n * t)

    def ecef(self, t: float):
        n = math.sqrt(MU / self.a ** 3)
        return _orbit(self.a, self.inc, self.raan - WE * t, self.u0 + n * t)


def _orbit(a, inc, raan, u):
    cu, su, cO, sO, ci, si = math.cos(u), math.sin(u), math.cos(raan), math.sin(raan), math.cos(inc), math.sin(inc)
    return (a * (cu * cO - su * ci * sO), a * (cu * sO + su * ci * cO), a * su * si)


# GPS 24-slot baseline (SPS Performance Standard): plane -> (RAAN, arguments of latitude), degrees
GPS_SLOTS = {
    "A": (272.847, [268.126, 161.786, 11.676, 41.806]),
    "B": (332.847, [80.956, 173.336, 309.976, 204.376]),
    "C": (32.847, [111.876, 11.796, 339.666, 241.556]),
    "D": (92.847, [135.226, 265.446, 35.156, 167.356]),
    "E": (152.847, [197.046, 302.596, 66.066, 333.686]),
    "F": (212.847, [238.886, 345.226, 105.206, 135.346]),
}
A_GPS, A_GLO, A_GAL, A_BDS, A_GEO = 26559.7e3, 25508.2e3, 29599.8e3, 27906.1e3, 42164.2e3


def gps(spares=True) -> list[Sat]:
    """The 24 baseline slots, plus 7 spares dropped into the widest gaps (31 flying, like today)."""
    slots = {p: sorted(us) for p, (_, us) in GPS_SLOTS.items()}
    if spares:
        for _ in range(7):
            gaps = []
            for p, us in slots.items():
                for k, u in enumerate(us):
                    nxt = us[(k + 1) % len(us)] + (360 if k == len(us) - 1 else 0)
                    gaps.append((nxt - u, p, (u + (nxt - u) / 2) % 360))
            _, p, u = max(gaps)
            slots[p] = sorted(slots[p] + [u])
    out = []
    for p, us in slots.items():
        for k, u in enumerate(us):
            out.append(Sat("GPS", f"{p}{k + 1}", A_GPS, math.radians(55), math.radians(GPS_SLOTS[p][0]), math.radians(u)))
    return out


def walker(sys_, n, planes, f, inc, a, raan0=0.0, u0=0.0) -> list[Sat]:
    """Walker delta n/planes/f: planes evenly round the equator, satellites evenly round each plane."""
    s = n // planes
    return [Sat(sys_, f"{sys_[0]}{p * s + k + 1}", a, math.radians(inc), math.radians(raan0 + 360 * p / planes),
                math.radians(u0 + 360 * k / s + 360 * f * p / n)) for p in range(planes) for k in range(s)]


def glonass():
    return walker("GLONASS", 24, 3, 1, 64.8, A_GLO, 15, 10)


def galileo():
    return walker("Galileo", 24, 3, 1, 56.0, A_GAL, 40, 25)


def beidou(high=True):
    meo = walker("BeiDou", 24, 3, 1, 55.0, A_BDS, 70, 50)
    if not high:
        return meo
    geo = [Sat("BeiDou", f"G{k}", A_GEO, 0.0, 0.0, math.radians(lon)) for k, lon in enumerate([80, 110.5, 140], 1)]
    igso = [Sat("BeiDou", f"I{k}", A_GEO, math.radians(55), math.radians(118 - 0), math.radians(u))
            for k, u in enumerate([0, 120, 240], 1)]
    return meo + geo + igso


def everyone():
    return gps() + glonass() + galileo() + beidou()


def geodetic_to_ecef(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    e2 = F_WGS * (2 - F_WGS)
    n = A_WGS / math.sqrt(1 - e2 * math.sin(la) ** 2)
    return ((n + h) * math.cos(la) * math.cos(lo), (n + h) * math.cos(la) * math.sin(lo), (n * (1 - e2) + h) * math.sin(la))


def enu(p, origin=RX):
    """ECEF point -> east, north, up (m) from the receiver."""
    lat, lon = math.radians(origin[0]), math.radians(origin[1])
    o = geodetic_to_ecef(*origin)
    dx, dy, dz = p[0] - o[0], p[1] - o[1], p[2] - o[2]
    sl, cl, sp, cp = math.sin(lon), math.cos(lon), math.sin(lat), math.cos(lat)
    return (-sl * dx + cl * dy, -sp * cl * dx - sp * sl * dy + cp * dz, cp * cl * dx + cp * sl * dy + sp * dz)


def look(sat: Sat, t: float, origin=RX):
    """Azimuth, elevation (deg) and the unit vector (e, n, u) to a satellite."""
    e, n, u = enu(sat.ecef(t), origin)
    r = math.sqrt(e * e + n * n + u * u)
    return math.degrees(math.atan2(e, n)) % 360, math.degrees(math.asin(u / r)), (e / r, n / r, u / r)


def inv(m):
    """Gauss-Jordan inverse of a small square matrix."""
    n = len(m)
    a = [list(row) + [float(i == j) for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]
        piv = a[c][c]
        a[c] = [v / piv for v in a[c]]
        for r in range(n):
            if r != c and a[r][c]:
                f = a[r][c]
                a[r] = [vr - f * vc for vr, vc in zip(a[r], a[c])]
    return [row[n:] for row in a]


def dops(units):
    """HDOP, VDOP, PDOP, TDOP, GDOP from unit vectors (e, n, u) to the satellites."""
    H = [(-e, -n, -u, 1.0) for e, n, u in units]
    HtH = [[sum(h[i] * h[j] for h in H) for j in range(4)] for i in range(4)]
    Q = inv(HtH)
    q = [Q[i][i] for i in range(4)]
    return dict(H=math.sqrt(q[0] + q[1]), V=math.sqrt(q[2]), P=math.sqrt(q[0] + q[1] + q[2]), T=math.sqrt(q[3]),
                G=math.sqrt(sum(q)))


def visible(sats, t, mask=10.0, origin=RX):
    out = []
    for s in sats:
        az, el, u = look(s, t, origin)
        if el > mask:
            out.append((s, az, el, u))
    return out


# ============================================================================
# shared furniture
# ============================================================================
def sys_col(name, dark=False):
    if dark:
        return {"GPS": P.lavender, "GLONASS": P.teal_60, "Galileo": P.white, "BeiDou": P.blue_60}[name]
    return {"GPS": P.blue, "GLONASS": P.teal, "Galileo": P.lavender, "BeiDou": P.black_60}[name]


def skyplot(svg: Svg, cx, cy, R, dark=False, labels=True, rings=(0, 30, 60)):
    """Polar sky: zenith in the middle, horizon on the rim, north up. Returns (az, el) -> page."""
    line = P.black_80 if dark else P.black_20
    for el in rings:
        svg.circle(cx, cy, R * (90 - el) / 90, "none", stroke=line, stroke_width=1.5 if el == 0 else 1)
    for a in range(0, 360, 30):
        r0 = R * 0.0
        svg.line(cx + r0 * math.sin(math.radians(a)), cy - r0 * math.cos(math.radians(a)),
                 cx + R * math.sin(math.radians(a)), cy - R * math.cos(math.radians(a)), line, 1)
    if labels:
        for a, s in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
            x, y = cx + (R + 20) * math.sin(math.radians(a)), cy - (R + 20) * math.cos(math.radians(a))
            svg.text(x, y + 6, s, "code", 16, P.white if dark else P.black, "middle")
        for el in rings[1:]:
            axis_label(svg, cx + 4, cy - R * (90 - el) / 90 - 5, f"{el}°", dark, size=12)

    def g(az, el):
        r = R * (90 - el) / 90
        return cx + r * math.sin(math.radians(az)), cy - r * math.cos(math.radians(az))
    return g


def chart_axes(svg, x0, y0, x1, y1, dark=False):
    ink = P.black_80 if dark else P.black
    svg.line(x0, y1, x1, y1, ink, 1.5)
    svg.line(x0, y0, x0, y1, ink, 1.5)


def hm(sec):
    h, m = divmod(round(sec / 60), 60)
    return f"{h} h {m:02d} m"


def period(a):
    return 2 * math.pi * math.sqrt(a ** 3 / MU)


def clock_face(svg, cx, cy, r, hand_deg, ink, face, tick=None):
    svg.circle(cx, cy, r, face, stroke=ink, stroke_width=3)
    for k in range(12):
        a = math.radians(k * 30)
        svg.line(cx + 0.78 * r * math.sin(a), cy - 0.78 * r * math.cos(a), cx + 0.92 * r * math.sin(a),
                 cy - 0.92 * r * math.cos(a), tick or ink, 2)
    a = math.radians(hand_deg)
    svg.line(cx, cy, cx + 0.72 * r * math.sin(a), cy - 0.72 * r * math.cos(a), ink, 3, stroke_linecap="round")
    svg.line(cx, cy, cx, cy - 0.5 * r, ink, 4, stroke_linecap="round")
    svg.circle(cx, cy, 4, ink)


# ============================================================================
# sky
# ============================================================================
def constellations() -> Svg:
    """Four constellations to scale, each drawn from its own orbit parameters."""
    svg = Svg(P.black)
    rows = [
        ("GPS", gps(), "USA", A_GPS, "6 planes · 55°"),
        ("GLONASS", glonass(), "Russia", A_GLO, "3 planes · 64.8°"),
        ("Galileo", galileo(), "EU", A_GAL, "3 planes · 56°"),
        ("BeiDou", beidou(), "China", A_BDS, "3 planes · 55° +6"),
    ]
    scale = 128 / A_GEO
    el_v, az_v = math.radians(22), math.radians(-35)

    def proj(p):
        x = p[0] * math.cos(az_v) - p[1] * math.sin(az_v)
        y = p[0] * math.sin(az_v) + p[1] * math.cos(az_v)
        up = y * math.sin(el_v) + p[2] * math.cos(el_v)
        depth = -y * math.cos(el_v) + p[2] * math.sin(el_v)
        return x * scale, -up * scale, depth

    for k, (name, sats, who, a, planes) in enumerate(rows):
        px, py = M + (k % 2) * 470, ART_TOP + 40 + (k // 2) * 310
        cx, cy = px + 140, py + 140
        col = sys_col(name, True)
        re_px = RE * scale
        orbits = {}
        for s in sats:
            orbits.setdefault((round(s.a), round(s.inc, 3), round(s.raan, 3) if s.inc else 0), s)
        back, front = [], []
        for s in orbits.values():
            n = 160
            ring = []
            for j in range(n + 1):
                u = 2 * math.pi * j / n
                ring.append(proj(_orbit(s.a, s.inc, s.raan, u)))
            seg, side = [], None
            for x, y, d in ring:
                cur = "b" if (d < 0) else "f"
                if side is not None and cur != side:
                    (back if side == "b" else front).append(seg)
                    seg = seg[-1:]
                seg.append((cx + x, cy + y))
                side = cur
            (back if side == "b" else front).append(seg)
        path(svg, back, col, 1.2, opacity="0.35")
        dots = [(proj(s.inertial(0)), s) for s in sats]
        for (x, y, d), s in dots:
            if d < 0:
                svg.circle(cx + x, cy + y, 3.2, col, opacity="0.45")
        svg.circle(cx, cy, re_px, P.blue)
        svg.add(f'<ellipse cx="{_fmt(cx)}" cy="{_fmt(cy)}" rx="{_fmt(re_px)}" ry="{_fmt(re_px * math.sin(el_v))}" '
                f'fill="none" stroke="{P.blue_60}" stroke-width="1"/>')
        path(svg, front, col, 1.6, opacity="0.9")
        for (x, y, d), s in dots:
            if d >= 0:
                svg.circle(cx + x, cy + y, 4.2, col)
        tx = px + 300
        svg.text(tx, py + 52, name, "head", 30, col)
        svg.text(tx, py + 80, who, "codel", 14, P.blue_40)
        lines = [f"{len(sats)} satellites", planes, f"{(a - RE) / 1e3:,.0f} km up".replace(",", " "),
                 f"round in {hm(period(a))}"]
        for j, s_ in enumerate(lines):
            svg.text(tx, py + 120 + j * 25, s_, "code", 15, P.white if j == 0 else P.blue_40)

    alls = everyone()
    vis = visible(alls, 0, 10)
    by = {n: len([v for v in vis if v[0].sys == n]) for n in ("GPS", "GLONASS", "Galileo", "BeiDou")}
    y = 1000
    svg.text(M, y, f"{len(alls)} satellites in all · above 10° from 52.5° N right now: {len(vis)}", "code", 17, P.white)
    svg.text(M, y + 26, "   ".join(f"{k} {v}" for k, v in by.items()) + "   (one constellation alone: 8–12)", "codel", 14,
             P.blue_40)
    axis_label(svg, W - M, ART_TOP + 18, "all four drawn to the same scale", True, "end")

    svg.frame("constellations.", "gnss · four systems in medium earth orbit · kepler", dark=True, title_fill=P.white)
    brief(svg, "one system's ~30 satellites leave a thin sky: in a street, 4 in view isn't a given",
          "fly four: ~110 satellites, and a modern receiver listens to all of them", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, f"""
T = 2*pi*sqrt(a**3 / mu)                       # higher orbit, slower lap
gps     = walker(31, planes=6, inc=55,   a=26_560e3)   # T = {hm(period(A_GPS))}
glonass = walker(24, planes=3, inc=64.8, a=25_508e3)   # T = {hm(period(A_GLO))}
galileo = walker(24, planes=3, inc=56,   a=29_600e3)   # T = {hm(period(A_GAL))}
beidou  = walker(24, planes=3, inc=55,   a=27_906e3)   # + 3 GEO, 3 IGSO""", "py", 18, dark=True)
    return svg


def skyplot_poster() -> Svg:
    """A day of GPS tracks over 52.5° N: the north hole the 55° tilt leaves."""
    svg = Svg(P.white)
    cx, cy, R = 540, 622, 262
    g = skyplot(svg, cx, cy, R)
    sats = gps()
    day = 86164
    segs = []
    for s in sats:
        cur = []
        for t in range(0, day + 1, 90):
            az, el, _ = look(s, t)
            if el > 0:
                cur.append(g(az, el))
            elif cur:
                segs.append(cur)
                cur = []
        if cur:
            segs.append(cur)
    path(svg, segs, P.blue_40, 1.4, opacity="0.75")
    for s, az, el, _ in visible(sats, 0, 0):
        p = g(az, el)
        svg.circle(*p, 9, P.blue)
        tag(svg, p[0] + 13, p[1] + 5, s.name, "code", 13, P.blue, bg=P.white, pad=3)
    # where nothing goes
    hp = g(0, 47)
    tag(svg, hp[0], hp[1] - 8, "nothing passes here", "code", 15, P.black, "middle", pad=4)
    tag(svg, hp[0], hp[1] + 14, "orbits tilt 55°; you sit at 52.5°", "codel", 13, P.black_60, "middle", pad=4)

    # how many are up, over the day
    x0, x1, y0, y1 = M + 90, W - M, 948, 1000
    counts = [len(visible(sats, t, 10)) for t in range(0, day, 300)]
    lo, hi = min(counts), max(counts)
    pts_ = []
    for k, n in enumerate(counts):
        x = x0 + (x1 - x0) * k / len(counts)
        xn = x0 + (x1 - x0) * (k + 1) / len(counts)
        y = y1 - (y1 - y0) * (n - 4) / (hi - 4)
        pts_ += [(x, y), (xn, y)]
    svg.poly([(x0, y1)] + pts_ + [(x1, y1)], P.blue_20)
    svg.polyline(pts_, P.blue, 2)
    svg.line(x0, y1, x1, y1, P.black, 1.5)
    for h in range(0, 25, 6):
        axis_label(svg, x0 + (x1 - x0) * h / 24, y1 + 22, f"{h} h", anchor="middle")
    axis_label(svg, x0 - 12, y0 + 14, f"{hi}", anchor="end")
    axis_label(svg, x0 - 12, y1 - 2, "4", anchor="end")
    svg.text(M, y0 - 16, f"in view above 10°, over one day: {lo} to {hi}", "code", 15, P.black)
    axis_label(svg, W - M, ART_TOP + 22, f"{len(sats)} GPS satellites · one sidereal day", anchor="end")
    axis_label(svg, W - M, ART_TOP + 42, "dots: where they are at t = 0", anchor="end")

    svg.frame("skyplot.", "gps · 24 h of tracks from 52.5° N · azimuth × elevation")
    brief(svg, "from 52.5° N, no GPS satellite ever crosses a slice of the northern sky",
          "the orbits tilt 55°: aim base stations where the south is clear")
    code_rule(svg)
    svg.code(M, CODE_Y, """
for t in range(0, 86_164, 90):                  # one sidereal day, then it repeats
    e, n, u = enu(sat.ecef(t) - rx_ecef)        # the satellite, seen from 52.5° N
    el, az = asin(u / norm), atan2(e, n)
    if el > 0: track.append(polar(az, r=90 - el))   # zenith in the middle""", "py", 19)
    return svg


def relativity() -> Svg:
    """Satellite clocks gain 38.6 µs a day: gravity speeds them, motion slows them; so they're tuned slow."""
    svg = Svg(P.cream)
    a = 26561.75e3
    W0 = 6.969290134e-10  # potential of the geoid / c² (the rate of a clock on the ground)
    gr = W0 - MU / (a * C * C)
    sr = -MU / (2 * a * C * C)
    net = gr + sr
    day = 86400
    us = lambda x: x * day * 1e6  # noqa: E731
    f_sat = F0 * (1 - net)

    # left: the ground clock and the orbit clock
    ex, er = 330, 900  # a big Earth, mostly off the bottom of the drawing
    ey = 700 + er
    svg.clip_begin(0, ART_TOP + 20, W, 765 - ART_TOP - 20)
    svg.circle(ex, ey, er, P.teal_20, stroke=P.teal, stroke_width=2)
    orb = er + 230
    svg.arc(ex, ey, orb, math.radians(-128), math.radians(-80), P.blue_40, 2, stroke_dasharray="6 8")
    svg.clip_end()
    gx, gy = ex, ey - er
    clock_face(svg, gx, gy - 50, 40, 20, P.black, P.white)
    svg.text(gx, gy - 108, "ground", "code", 16, P.black, "middle")
    sa = math.radians(-96)
    sx, sy = ex + orb * math.cos(sa), ey + orb * math.sin(sa)
    clock_face(svg, sx, sy, 40, 25, P.blue, P.white)
    svg.rect(sx - 92, sy - 9, 44, 18, P.blue_60, rx=2)
    svg.rect(sx + 48, sy - 9, 44, 18, P.blue_60, rx=2)
    svg.text(sx, sy - 58, "orbit · 20 200 km up", "code", 16, P.blue, "middle")
    tang = sa + math.pi / 2
    arrow(svg, (sx - 40 * math.cos(tang), sy - 40 * math.sin(tang) + 66),
          (sx + 60 * math.cos(tang), sy + 60 * math.sin(tang) + 66), P.blue, 3)
    v = math.sqrt(MU / a)
    svg.text(sx, sy + 110, f"{v / 1000:.2f} km/s", "code", 15, P.blue, "middle")

    # right: the two effects and their sum
    bx0, bx1, zy, k = 590, W - M, 640, 4.6  # px per µs/day
    svg.line(bx0, zy, bx1, zy, P.black, 1.5)
    bars = [("gravity", us(gr), "weaker up there:", "runs fast", P.blue),
            ("speed", us(sr), "moving clocks", "run slow", P.lavender),
            ("net", us(net), "every day,", "it gains", P.black)]
    bw = 70
    for j, (name, val, l1, l2, col) in enumerate(bars):
        x = bx0 + 30 + j * 130
        top = zy - val * k
        svg.rect(x, min(top, zy), bw, abs(val * k), col, rx=3)
        yl = top - 14 if val > 0 else top + 28
        svg.text(x + bw / 2, yl, f"{val:+.1f}", "code", 20, col, "middle")
        svg.text(x + bw / 2, zy + (26 if val > 0 else -val * k + 50), name, "code", 15, P.black, "middle")
        _ = (l1, l2)
    axis_label(svg, bx1, ART_TOP + 28, "µs per day, against a clock on the ground", anchor="end")
    svg.text(bx0 + 30 + 130 + bw / 2, zy - 120, "+", "head", 40, P.black_60, "middle")

    # bottom: what that does to the position
    x0, x1, y0, y1 = M + 60, W - M, 830, 995
    chart_axes(svg, x0, y0, x1, y1)
    km = net * day * C / 1000
    svg.polyline([(x0, y1), (x1, y1 - (y1 - y0) * 0.92)], P.black, 4)
    svg.line(x0, y1 - 4, x1, y1 - 4, P.blue, 4)
    for h in range(0, 25, 6):
        axis_label(svg, x0 + (x1 - x0) * h / 24, y1 + 24, f"{h} h", anchor="middle")
    yk = lambda v: y1 - (y1 - y0) * 0.92 * v / km  # noqa: E731
    for v in (0, 4, 8):
        axis_label(svg, x0 - 12, yk(v) + 5, f"{v}", anchor="end")
    axis_label(svg, x0 - 12, y0 - 14, "range error, km")
    svg.text(x1 - 10, y1 - (y1 - y0) * 0.92 - 18, f"left alone: {km:.1f} km a day", "code", 17, P.black, "end")
    hr = net * 3600 * C
    p1 = (x0 + (x1 - x0) / 24, y1 - (y1 - y0) * 0.92 / 24)
    svg.circle(*p1, 5, P.black)
    svg.line(p1[0], p1[1] - 8, p1[0] + 30, p1[1] - 56, P.black_60, 1.2)
    svg.text(p1[0] + 36, p1[1] - 60, f"{hr:.0f} m after an hour", "codel", 14, P.black_60)
    svg.text(x1 - 10, y1 - 18, f"tuned slow before launch: {f_sat / 1e6:.11f} MHz", "code", 16, P.blue, "end")

    svg.frame("relativity.", "gps · satellite clocks · general + special relativity")
    brief(svg, f"clocks in orbit gain {us(net):.1f} µs a day: light runs {km:.1f} km in that time",
          "set them slow on the ground: 10.22999999543 MHz, not 10.23")
    code_rule(svg)
    svg.code(M, CODE_Y, """
gr = (W0 - GM/a) / c**2          # weaker gravity up there: +45.7 µs/day
sr = -GM / (2*a * c**2)          # 3.87 km/s, time dilation: -7.2 µs/day
f_sat = 10.23e6 * (1 - (gr + sr))       # = 10.22999999543 MHz
# both effects, measured every day: GPS is a working test of Einstein""", "py", 19)
    return svg


def wait() -> Svg:
    """The navigation message at 50 bit/s: orbits every 30 s, the whole almanac every 12.5 minutes."""
    svg = Svg(P.white)
    rng = random.Random(4)
    x0, x1, y0 = M + 112, W - M, ART_TOP + 64
    cw, rh = (x1 - x0) / 25, 32
    rows = [("1 clock", P.blue), ("2 orbit", P.blue_80), ("3 orbit", P.blue_80), ("4 almanac", P.lavender),
            ("5 almanac", P.lavender)]
    for r, (name, col) in enumerate(rows):
        y = y0 + r * (rh + 4)
        svg.text(x0 - 12, y + 21, name, "code", 14, P.black, "end")
        for f in range(25):
            x = x0 + f * cw
            fill = col if r < 3 else (P.lavender if r == 3 else P.lavender_60)
            svg.rect(x + 1, y, cw - 3, rh, fill, rx=3)
            if r >= 3:
                svg.text(x + cw / 2 - 1, y + 21, f"{f + 1}", "code", 11, P.white if r == 3 else P.black, "middle")
    yb = y0 + 5 * (rh + 4) + 6
    for mnt in (0, 2.5, 5, 7.5, 10, 12.5):
        x = x0 + (x1 - x0) * mnt / 12.5
        svg.line(x, yb, x, yb + 6, P.black, 1.5)
        axis_label(svg, x, yb + 26, f"{mnt:g} min", anchor="middle")
    axis_label(svg, x0, y0 - 14, "one column = one frame = 30 s  ·  rows 1–3 repeat, rows 4–5 page through all satellites")

    # one subframe, bit by bit
    y = yb + 84
    svg.text(M, y - 16, "one subframe: 300 bits, 6 s, 20 ms per bit", "code", 15, P.black)
    pre = [1, 0, 0, 0, 1, 0, 1, 1]
    bits = pre + [rng.randint(0, 1) for _ in range(292)]
    bw = (x1 - M) / 300
    for k, b in enumerate(bits):
        word = k // 30
        col = P.blue if k < 8 else (P.teal if word < 2 else P.black_60)
        h = 26 if b else 9
        svg.rect(M + k * bw, y + 26 - h, max(bw - 0.6, 0.8), h, col)
    for wd in range(11):
        svg.line(M + wd * 30 * bw, y + 30, M + wd * 30 * bw, y + 38, P.black_60, 1)
    axis_label(svg, M, y + 58, "preamble 10001011")
    axis_label(svg, M + 30 * bw, y + 76, "TLM + HOW: time of week")
    axis_label(svg, M + 60 * bw + 120, y + 58, "8 more words of 30 bits: 24 data + 6 parity")

    # time to first fix
    ty0 = y + 128
    tx0, tx1 = M + 230, W - M
    lo, hi = 0.5, 1000.0
    gx = lambda s: tx0 + (tx1 - tx0) * math.log(s / lo) / math.log(hi / lo)  # noqa: E731
    # waiting for subframes 1-3 from a random moment: next subframe 1 starts in 0..30 s, then 18 s to read
    waits = sorted(rng.uniform(0, 30) + 18 for _ in range(4000))
    w_med = waits[len(waits) // 2]
    starts = [("hot · ephemeris kept", 0.8, 2.0, P.blue),
              ("assisted · over LTE", 1.0, 5.0, P.teal),
              ("warm · read orbits", 18.0, 48.0, P.blue_80),
              ("cold · search, then read", 30.0, 90.0, P.black_60),
              ("almanac, start to end", 750.0, 750.0 * 1.02, P.lavender)]
    for s in (1, 10, 60, 600):
        svg.line(gx(s), ty0 - 8, gx(s), ty0 + 5 * 34, P.black_20, 1)
        axis_label(svg, gx(s), ty0 + 5 * 34 + 20, {1: "1 s", 10: "10 s", 60: "1 min", 600: "10 min"}[s], anchor="middle")
    for j, (name, a, b, col) in enumerate(starts):
        yy = ty0 + j * 34
        svg.text(tx0 - 14, yy + 18, name, "code", 14, P.black, "end")
        svg.rect(gx(a), yy + 4, max(gx(b) - gx(a), 10), 20, col, rx=10)
    svg.circle(gx(w_med), ty0 + 2 * 34 + 14, 4, P.white)
    svg.text(gx(750) - 26, ty0 + 4 * 34 + 19, "12.5 min", "code", 14, P.lavender, "end")
    axis_label(svg, W - M, ty0 - 14, f"time to first fix · median warm wait {w_med:.0f} s", anchor="end")

    svg.frame("wait.", "gps · navigation message · 50 bit/s · time to first fix")
    brief(svg, "the orbit data trickles down at 50 bit/s: 18–48 s to read, 12.5 min for everything",
          "keep it from last time (hot start), or download it over the phone network")
    code_rule(svg)
    svg.code(M, CODE_Y, """
bit   = 20 * ca_period              # 20 ms: 50 bit/s, under the 1 ms code
frame = 5 * subframe                # 5 x 300 bits x 20 ms = 30 s
ephemeris = frame[0:3]              # this satellite's clock and orbit: every 30 s
almanac   = [frame[3:5] for page in range(25)]   # everyone's, roughly: 12.5 min""", "py", 19)
    return svg


# ============================================================================
# signal
# ============================================================================
def _sinc(x):
    return 1.0 if abs(x) < 1e-12 else math.sin(math.pi * x) / (math.pi * x)


def psd(f_off_mhz, kind, rate):
    """Power spectral density (unnormalised) at an offset from the carrier: BPSK(rate) or sine-BOC(1,1)."""
    f = f_off_mhz
    if kind == "bpsk":
        return _sinc(f / rate) ** 2 / rate
    fs = rate
    x = math.pi * f / (2 * fs)
    if abs(math.cos(x)) < 1e-9:
        return 0.0
    if abs(f) < 1e-9:
        return 0.0
    return rate * (math.sin(x) * math.sin(math.pi * f / rate) / (math.pi * f * math.cos(x))) ** 2


def bands() -> Svg:
    """The L-band, two windows of it: every system's signals, as their spectra."""
    svg = Svg(P.cream)
    lo_a, hi_a, lo_b, hi_b = 1160.0, 1290.0, 1555.0, 1612.0
    x0, gap, x1 = M + 118, 34, W - M
    k = (x1 - x0 - gap) / ((hi_a - lo_a) + (hi_b - lo_b))

    def gx(f):
        return x0 + (f - lo_a) * k if f <= hi_a + 1 else x0 + (hi_a - lo_a) * k + gap + (f - lo_b) * k

    glo1 = [(1602 + 0.5625 * c, "bpsk", 0.511) for c in range(-7, 7)]
    glo2 = [(1246 + 0.4375 * c, "bpsk", 0.511) for c in range(-7, 7)]
    rows = [
        ("GPS", [(1575.42, "bpsk", 1.023), (1575.42, "boc", 1.023), (1227.60, "bpsk", 1.023), (1176.45, "bpsk", 10.23),
                 (1575.42, "bpsk", 10.23, 0.4), (1227.60, "bpsk", 10.23, 0.4)],
         [(1176.45, "L5"), (1227.60, "L2C · P(Y)"), (1575.42, "L1 C/A · L1C")]),
        ("GLONASS", glo1 + glo2 + [(1202.025, "bpsk", 10.23)],
         [(1202.025, "G3"), (1246.0, "G2"), (1602.0, "G1")]),
        ("Galileo", [(1575.42, "boc", 1.023), (1278.75, "bpsk", 5.115), (1176.45, "bpsk", 10.23), (1207.14, "bpsk", 10.23)],
         [(1176.45, "E5a"), (1207.14, "E5b"), (1278.75, "E6"), (1575.42, "E1")]),
        ("BeiDou", [(1561.098, "bpsk", 2.046), (1575.42, "boc", 1.023), (1176.45, "bpsk", 10.23),
                    (1207.14, "bpsk", 10.23), (1268.52, "bpsk", 10.23)],
         [(1176.45, "B2a"), (1207.14, "B2b"), (1268.52, "B3"), (1561.098, "B1I"), (1588.0, "B1C")]),
    ]
    top, rh, floor = ART_TOP + 110, 116, -24.0
    shared = [(115, "L5"), (118, ""), (120, "L2"), (125, "E6"), (154, "L1")]
    for mult, _ in shared:
        f = mult * F0 / 1e6
        svg.line(gx(f), top - 30, gx(f), top + 4 * rh, P.black_20, 1.2, stroke_dasharray="3 5")
        svg.text(gx(f), top - 40, f"{mult}·f0", "code", 13, P.black_60, "middle")
    for i, (name, sigs, labels) in enumerate(rows):
        base = top + (i + 1) * rh - 14
        col = sys_col(name)
        svg.text(M, base - 30, name, "code", 17, col)
        svg.line(x0, base, gx(hi_a), base, P.black_60, 1)
        svg.line(gx(lo_b), base, x1, base, P.black_60, 1)
        for win in ((lo_a, hi_a), (lo_b, hi_b)):
            for faint in (True, False):
                n = int((win[1] - win[0]) * 12)
                pts_ = []
                for j in range(n + 1):
                    f = win[0] + (win[1] - win[0]) * j / n
                    best = floor
                    for sg in sigs:
                        if (len(sg) > 3) != faint:
                            continue
                        fc, kind, rate = sg[:3]
                        if abs(f - fc) > 60:
                            continue
                        v = psd(f - fc, kind, rate)
                        pk = max(psd(d / 200 * rate, kind, rate) for d in range(-300, 301, 10))
                        db = 10 * math.log10(max(v / pk, 1e-9)) if v > 0 else floor
                        best = max(best, db)
                    pts_.append((gx(f), base - (rh - 38) * (best - floor) / -floor))
                if faint:
                    svg.poly([(gx(win[0]), base)] + pts_ + [(gx(win[1]), base)], col, opacity="0.14")
                else:
                    svg.poly([(gx(win[0]), base)] + pts_ + [(gx(win[1]), base)], col, opacity="0.85")
        for fc, lab in labels:
            svg.text(gx(fc), base + 18, lab, "code", 12, col, "middle")
    yb = top + 4 * rh + 14
    for f in (1180, 1200, 1220, 1240, 1260, 1280, 1560, 1580, 1600):
        axis_label(svg, gx(f), yb + 18, f"{f}", anchor="middle", size=13)
    axis_label(svg, x1, yb + 40, "MHz · each signal scaled to its own peak, 24 dB deep", anchor="end")
    svg.text((gx(hi_a) + gx(lo_b)) / 2, top + 2 * rh, "//", "code", 18, P.black_60, "middle")
    svg.text(M, yb + 74, "narrow lobe: 1.023 Mchip/s, civil · wide lobe: 10.23 Mchip/s, sharper ranging",
             "codel", 14, P.black_60)
    svg.text(M, yb + 96, "GLONASS G1/G2: one 0.511 Mchip/s channel per satellite (FDMA); everyone else shares by code",
             "codel", 14, P.black_60)

    svg.frame("bands.", "gnss signals · L-band, 1.1–1.6 GHz · f0 = 10.23 MHz")
    brief(svg, "four systems, one quiet slice of radio that goes through cloud and rain",
          "share it: overlap the carriers, tell the signals apart by their codes")
    code_rule(svg)
    svg.code(M, CODE_Y, """
f0 = 10.23e6                                   # the master clock on board
L1, L2, L5 = 154*f0, 120*f0, 115*f0            # 1575.42, 1227.60, 1176.45 MHz
psd_bpsk = lambda f: Tc * sinc(f * Tc)**2      # chip rate sets the width
psd_boc  = lambda f: psd_bpsk(f) * tan(pi*f*Tc/2)**2   # split: E1, L1C, B1C""", "py", 19)
    return svg


CA_TAPS = {1: (2, 6), 2: (3, 7), 3: (4, 8), 4: (5, 9), 5: (1, 9), 6: (2, 10), 7: (1, 8), 8: (2, 9), 9: (3, 10),
           10: (2, 3), 11: (3, 4), 12: (5, 6), 13: (6, 7), 14: (7, 8), 15: (8, 9), 16: (9, 10)}


def ca_code(prn):
    """The GPS C/A Gold code: two 10-stage shift registers, 1023 chips, as ±1."""
    g1, g2, out = [1] * 10, [1] * 10, []
    s1, s2 = CA_TAPS[prn]
    for _ in range(1023):
        out.append(g1[9] ^ g2[s1 - 1] ^ g2[s2 - 1])
        f1 = g1[2] ^ g1[9]
        f2 = g2[1] ^ g2[2] ^ g2[5] ^ g2[7] ^ g2[8] ^ g2[9]
        g1, g2 = [f1] + g1[:9], [f2] + g2[:9]
    assert prn != 1 or out[:10] == [1, 1, 0, 0, 1, 0, 0, 0, 0, 0]  # ICD: PRN 1 starts 1440 octal
    return [1 - 2 * b for b in out]


def correlate(rx, code):
    n = len(code)
    return [sum(rx[i] * code[(i - k) % n] for i in range(n)) for k in range(n)]


def code_poster() -> Svg:
    """C/A codes: what arrives looks like noise; multiply by the right code and add, and one lag stands out."""
    svg = Svg(P.white)
    rng = random.Random(7)
    prn, other, delay, periods = 7, 12, 412, 10
    sigma = 10 ** (18 / 20)  # each chip arrives 18 dB below the noise
    ca, cb = ca_code(prn), ca_code(other)
    rx = [0.0] * 1023
    raw = []
    for p in range(periods):
        for i in range(1023):
            s = ca[(i - delay) % 1023] + rng.gauss(0, sigma)
            rx[i] += s
            if p == 0 and i < 160:
                raw.append(s)
    n = 1023 * periods
    c7 = [v / n for v in correlate(rx, ca)]
    c12 = [v / n for v in correlate(rx, cb)]
    x0, x1 = M + 150, W - M

    def chips(y, code, col, label, sub):
        svg.text(M, y + 4, label, "code", 15, col)
        axis_label(svg, M, y + 24, sub)
        pts_, cw = [], (x1 - x0) / 64
        for k in range(64):
            lv = y - 14 * code[k]
            pts_ += [(x0 + k * cw, lv), (x0 + (k + 1) * cw, lv)]
        svg.polyline(pts_, col, 2.2, stroke_linejoin="miter")
    chips(ART_TOP + 56, ca, P.blue, f"PRN {prn}", "first 64 chips")
    chips(ART_TOP + 122, cb, P.teal, f"PRN {other}", "another satellite")

    y = ART_TOP + 216
    svg.text(M, y + 4, "what arrives", "code", 15, P.black)
    axis_label(svg, M, y + 24, "PRN 7, −18 dB")
    s = 28 / (3 * sigma)
    svg.polyline([(x0 + (x1 - x0) * k / (len(raw) - 1), y + 4 - v * s) for k, v in enumerate(raw)], P.black_60, 1.3)

    def corr_plot(y0, h, vals, col, label, sub, peak=None):
        svg.text(M, y0 + 20, label, "code", 15, col)
        axis_label(svg, M, y0 + 40, sub)
        base = y0 + h
        svg.line(x0, base, x1, base, P.black_20, 1)
        svg.polyline([(x0 + (x1 - x0) * k / 1022, base - h * max(v, -0.1) / 1.05) for k, v in enumerate(vals)], col, 1.4)
        if peak is not None:
            px = x0 + (x1 - x0) * peak / 1022
            svg.circle(px, base - h * vals[peak] / 1.05, 5, col)
            svg.text(px + 12, base - h * vals[peak] / 1.05 + 6, f"lag {peak} chips · {peak * CHIP / 1000:.1f} km", "code", 15, col)
        return base

    b = corr_plot(ART_TOP + 290, 170, c7, P.blue, "× PRN 7", "summed over 10 ms", delay)
    b2 = corr_plot(b + 30, 90, c12, P.teal, "× PRN 12", "nothing to find")
    for k in (0, 256, 512, 768, 1023):
        axis_label(svg, x0 + (x1 - x0) * k / 1022, b2 + 22, f"{k}", anchor="middle")
    axis_label(svg, x1, b2 + 44, "lag, chips · 1 chip = 977.5 ns = 293 m", anchor="end")
    noise = (sum(v * v for i, v in enumerate(c7) if abs(i - delay) > 2) / 1020) ** 0.5
    axis_label(svg, x1, ART_TOP + 330, f"peak = {c7[delay] / noise:.0f} × the noise", anchor="end")

    svg.frame("code.", "gps L1 C/A · 1023-chip Gold codes · correlation")
    brief(svg, "every GPS satellite sends on 1575.42 MHz, and arrives 20 dB under the noise",
          "each has its own 1023-chip code: multiply by it, add up, and one lag stands out")
    code_rule(svg)
    svg.code(M, CODE_Y, """
g1, g2 = lfsr(taps=[3, 10]), lfsr(taps=[2, 3, 6, 8, 9, 10])
ca = g1 ^ g2.tap(1, 8)                     # PRN 7: 1023 chips, every 1 ms
corr = [sum(rx * roll(ca, k)) for k in range(1023)]    # 10 ms of samples
lag = argmax(corr)                         # the code phase: range, modulo 300 km""", "py", 19)
    return svg


def doppler() -> Svg:
    """Acquisition: guess the Doppler and the code phase together; one cell of the grid lights up."""
    svg = Svg(P.black)
    rng = random.Random(3)
    fd_true, k_true, T = 2350.0, 412.4, 1e-3
    bins = list(range(-5000, 5001, 500))
    x0, x1, ytop, dy, H = M + 120, W - M - 50, ART_TOP + 210, 20, 250
    shear = 2.5
    grid = []
    for fd in bins:
        att = abs(_sinc((fd - fd_true) * T))
        ph = rng.uniform(0, 2 * math.pi)
        row = []
        for k in range(1023):
            d = abs(k - k_true)
            r = max(0.0, 1 - d) * att
            re, im = r * math.cos(ph) + rng.gauss(0, 0.022), r * math.sin(ph) + rng.gauss(0, 0.022)
            row.append(math.hypot(re, im))
        grid.append(row)
    best = max(((v, i, k) for i, row in enumerate(grid) for k, v in enumerate(row)))
    for i, (fd, row) in enumerate(zip(bins, grid)):
        base = ytop + i * dy
        off = (len(bins) - 1 - i) * shear
        pts_ = [(x0 + off + (x1 - x0) * k / 1022, base - H * v) for k, v in enumerate(row)]
        svg.poly([(x0 + off, base)] + pts_ + [(x1 + off, base)], P.black)
        hit = i == best[1]
        svg.polyline(pts_, P.lavender if hit else P.blue_60, 2.2 if hit else 1.1, opacity="1" if hit else "0.75")
        if fd % 2500 == 0 or hit:
            svg.text(x0 + off - 14, base + 4, f"{fd / 1000:+.1f} kHz" if fd else "0", "code", 13,
                     P.lavender if hit else P.blue_40, "end")
    bi, bk = best[1], best[2]
    px = x0 + (len(bins) - 1 - bi) * shear + (x1 - x0) * bk / 1022
    py = ytop + bi * dy - H * best[0]
    svg.circle(px, py, 6, P.white)
    tag(svg, px + 16, py - 4, f"{bins[bi] / 1000:+.1f} kHz · chip {bk}", "code", 17, P.white, bg=P.black)
    tag(svg, px + 16, py + 20, f"(truth: {fd_true / 1000:+.2f} kHz, {k_true})", "codel", 14, P.blue_40, bg=P.black)
    yb = ytop + (len(bins) - 1) * dy + 30
    for k in (0, 256, 512, 768, 1023):
        axis_label(svg, x0 + (x1 - x0) * k / 1022, yb, f"{k}", True, "middle")
    axis_label(svg, x1, yb + 22, "code phase, chips", True, "end")
    axis_label(svg, M, ytop - 40, "Doppler guess", True)
    vmax = math.sqrt(MU / A_GPS) * RE / A_GPS  # fastest range rate: satellite on the horizon
    svg.text(M, yb + 46, f"satellite at {math.sqrt(MU / A_GPS) / 1000:.2f} km/s · up to {vmax:.0f} m/s along the line of"
             f" sight · ±{vmax * F_L1 / C / 1000:.1f} kHz on L1", "codel", 14, P.blue_40)

    svg.frame("doppler.", "acquisition · 21 frequency bins × 1023 code phases · 1 ms", dark=True, title_fill=P.white)
    brief(svg, f"satellites rush toward or away from you: the carrier lands up to ±{vmax * F_L1 / C / 1000:.1f} kHz off",
          "search both at once: wipe each Doppler guess, correlate every code phase", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
for fd in range(-5000, 5001, 500):                # 21 frequency guesses
    base = rx * exp(-2j*pi*(f_if + fd)*t)         # undo this much Doppler
    grid[fd] = abs(ifft(fft(base) * conj(fft(ca))))   # all 1023 lags at once
fd, lag = argmax(grid)          # a coarse fix on both: hand it to the trackers""", "py", 19, dark=True)
    return svg


def iono() -> Svg:
    """The ionosphere delays code by 40.3·TEC/f²: longer slant paths, longer delays, and two bands cancel it."""
    svg = Svg(P.cream)
    h_ion, tec = 350e3, 20e16  # thin-shell height; 20 TECU, a calm midday

    def obliq(el):
        return 1 / math.sqrt(1 - (RE * math.cos(math.radians(el)) / (RE + h_ion)) ** 2)

    def delay(f, el, tecu=tec):
        return 40.3 * tecu / f ** 2 * obliq(el)

    # the scene, to scale: Earth's curve, a 250-450 km layer, three rays
    s = 1600 / RE
    rx = (540, 640)
    o = (rx[0], rx[1] + RE * s)
    y_clip = ART_TOP + 50
    svg.clip_begin(M - 84, y_clip, W, rx[1] - y_clip + 60)
    svg.circle(*o, (RE + 450e3) * s, P.lavender_20, stroke=P.lavender_60, stroke_width=1)
    svg.circle(*o, (RE + 250e3) * s, P.cream, stroke=P.lavender_60, stroke_width=1)
    svg.circle(*o, RE * s, P.teal_20, stroke=P.teal, stroke_width=2)
    for el, side, col in [(90, 1, P.black), (30, -1, P.blue), (10, 1, P.teal)]:
        d = (side * math.cos(math.radians(el)), -math.sin(math.radians(el)))

        def hit(r):  # ray from rx along d meets the circle of radius r about o
            bx, by = rx[0] - o[0], rx[1] - o[1]
            bb = bx * d[0] + by * d[1]
            cc = bx * bx + by * by - r * r
            return -bb + math.sqrt(bb * bb - cc)
        t0, t1 = hit((RE + 250e3) * s), hit((RE + 450e3) * s)
        far = 900
        svg.line(rx[0], rx[1], rx[0] + far * d[0], rx[1] + far * d[1], col, 1.5, stroke_dasharray="5 6")
        svg.line(rx[0] + t0 * d[0], rx[1] + t0 * d[1], rx[0] + t1 * d[0], rx[1] + t1 * d[1], col, 7,
                 stroke_linecap="round")
        lab = f"{el}° · {obliq(el):.1f}× the path"
        if el == 10:
            q = (rx[0] + (t0 + t1) / 2 * d[0], rx[1] + (t0 + t1) / 2 * d[1])
            svg.text(q[0], q[1] + 40, lab, "code", 15, col, "middle")
        else:
            q = (rx[0] + (t1 + 18) * d[0], rx[1] + (t1 + 18) * d[1])
            svg.text(q[0] + (10 if side > 0 else -10), q[1] - 4, lab, "code", 15, col, "start" if side > 0 else "end")
    svg.clip_end()
    svg.rect(rx[0] - 9, rx[1] - 16, 18, 16, P.black, rx=3)
    svg.text(M, (rx[1] + y_clip) / 2 - 40, "ionosphere", "code", 15, P.blue_80)
    axis_label(svg, M, (rx[1] + y_clip) / 2 - 20, "250–450 km, to scale")

    # delay against elevation
    x0, x1, y0, y1 = M + 60, W - M, 740, 995
    dmax = 20.0
    gx = lambda e: x0 + (x1 - x0) * (e - 5) / 85  # noqa: E731
    gy = lambda d: y1 - (y1 - y0) * d / dmax  # noqa: E731
    chart_axes(svg, x0, y0, x1, y1)
    for e in (5, 10, 30, 60, 90):
        axis_label(svg, gx(e), y1 + 22, f"{e}°", anchor="middle")
    for d in (0, 5, 10, 15, 20):
        axis_label(svg, x0 - 12, gy(d) + 5, f"{d}", anchor="end")
    axis_label(svg, x0 - 12, y0 - 16, "delay, m · 20 TECU")
    axis_label(svg, x1, y1 + 44, "elevation", anchor="end")
    els = [5 + 85 * k / 120 for k in range(121)]
    for f, name, col in [(F_L5, "L5 · 1176 MHz", P.teal), (F_L1, "L1 · 1575 MHz", P.blue)]:
        svg.polyline([(gx(e), gy(delay(f, e))) for e in els], col, 3.5)
        svg.text(gx(16), gy(delay(f, 16)) - 12, name, "code", 15, col)
        svg.text(x1, gy(delay(f, 90)) - 12, f"{delay(f, 90):.1f} m", "code", 15, col, "end")
    svg.line(gx(5), gy(0) - 3, x1, gy(0) - 3, P.black, 3.5)
    a1, a5 = F_L1 ** 2 / (F_L1 ** 2 - F_L5 ** 2), -F_L5 ** 2 / (F_L1 ** 2 - F_L5 ** 2)
    svg.text(x1, gy(0) - 14, f"L1 + L5, iono-free: 0 m (noise × {math.hypot(a1, a5):.1f})", "code", 15, P.black, "end")

    svg.frame("iono.", "ionospheric delay · 40.3 · TEC / f² · dual frequency")
    brief(svg, "the ionosphere delays the code by metres; more at low elevation, more at midday",
          "it delays each band by 1/f²: measure on two bands and solve it out")
    code_rule(svg)
    svg.code(M, CODE_Y, """
F = 1 / sqrt(1 - (Re*cos(el) / (Re + 350e3))**2)   # slant path through the layer
delay = 40.3 * TEC / f**2 * F                      # metres: dispersive
p_if = (f1**2*p1 - f5**2*p5) / (f1**2 - f5**2)     # L1 + L5: the 1/f² term cancels""", "py", 19)
    return svg


# ============================================================================
# fix
# ============================================================================
def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _mul(a, k):
    return tuple(x * k for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    return _mul(a, 1 / _norm(a))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def trilaterate(p1, r1, p2, r2, p3, r3):
    """The two points at distances r1, r2, r3 from p1, p2, p3."""
    ex = _unit(_sub(p2, p1))
    i = _dot(ex, _sub(p3, p1))
    ey = _unit(_sub(_sub(p3, p1), _mul(ex, i)))
    ez = _cross(ex, ey)
    d, j = _norm(_sub(p2, p1)), _dot(ey, _sub(p3, p1))
    x = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    y = (r1 * r1 - r3 * r3 + i * i + j * j) / (2 * j) - i / j * x
    z = math.sqrt(max(r1 * r1 - x * x - y * y, 0))
    base = _add(p1, _add(_mul(ex, x), _mul(ey, y)))
    return _add(base, _mul(ez, z)), _sub(base, _mul(ez, z))


def intersect() -> Svg:
    """Trilateration in four steps: a sphere, a circle, two points, one point."""
    svg = Svg(P.white)
    r0 = (0.0, 0.0, RE)

    def sat_at(az, el):
        a, e = math.radians(az), math.radians(el)
        u = (math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e))
        rho = -RE * u[2] + math.sqrt((RE * u[2]) ** 2 - RE * RE + A_GPS ** 2)
        return _add(r0, _mul(u, rho))
    sats = [sat_at(300, 62), sat_at(60, 38), sat_at(165, 30), sat_at(235, 18)]
    rs = [_norm(_sub(s, r0)) for s in sats]
    v = _unit((0.55, -1.0, 0.32))  # towards the viewer
    right = _unit(_cross((0, 0, 1), v))
    up = _cross(v, right)
    sc = 0.0066 / 1e3
    mid = (0.0, 0.0, 10500e3)
    pw, ph = 440, 268
    cols = [P.blue, P.teal, P.lavender, P.black_60]
    titles = [("1 · one satellite", "you are somewhere on a sphere"),
              ("2 · two", "the spheres meet in a circle"),
              ("3 · three", "the circle meets it in two points"),
              ("4 · four", "only one point fits the fourth")]
    a, b = trilaterate(sats[0], rs[0], sats[1], rs[1], sats[2], rs[2])
    mirror = a if _norm(_sub(a, r0)) > 1e3 else b

    def circle12():
        p1, p2 = sats[0], sats[1]
        ex = _unit(_sub(p2, p1))
        d = _norm(_sub(p2, p1))
        x = (rs[0] ** 2 - rs[1] ** 2 + d * d) / (2 * d)
        c = _add(p1, _mul(ex, x))
        h = math.sqrt(rs[0] ** 2 - x * x)
        e1 = _unit(_cross(ex, (0, 0, 1)))
        e2 = _cross(ex, e1)
        return [_add(c, _add(_mul(e1, h * math.cos(t)), _mul(e2, h * math.sin(t))))
                for t in [2 * math.pi * k / 120 for k in range(121)]]

    for k in range(4):
        px, py = M + (k % 2) * (pw + 32), ART_TOP + 74 + (k // 2) * (ph + 56)
        cx, cy = px + pw / 2, py + ph / 2

        def g(p):
            q = _sub(p, mid)
            return cx + _dot(q, right) * sc, cy - _dot(q, up) * sc
        svg.rect(px, py, pw, ph, P.white, rx=8, stroke=P.black_20, stroke_width=1.2)
        svg.clip_begin(px, py, pw, ph)
        for j in range(k + 1):
            c = g(sats[j])
            last = j == k
            svg.circle(*c, rs[j] * sc, cols[j], fill_opacity="0.07" if last else "0", stroke=cols[j],
                       stroke_width=2 if last else 1.2, stroke_opacity="1" if last else "0.45")
        e = g((0, 0, 0))
        svg.circle(*e, RE * sc, P.teal_20, stroke=P.teal, stroke_width=1.5)
        if k >= 1:
            svg.polyline([g(p) for p in circle12()], P.blue if k == 1 else P.blue_40, 3 if k == 1 else 1.5)
        for j in range(k + 1):
            svg.circle(*g(sats[j]), 7, cols[j])
            svg.text(g(sats[j])[0] + 11, g(sats[j])[1] - 8, f"sat {j + 1}", "code", 13, cols[j])
        rp = g(r0)
        if k == 2:
            mp = g(mirror)
            inside = px < mp[0] < px + pw and py < mp[1] < py + ph
            if inside:
                svg.circle(*mp, 7, P.black)
        svg.circle(*rp, 6, P.black)
        if k == 3:
            svg.circle(*rp, 14, "none", stroke=P.blue, stroke_width=3)
        svg.clip_end()
        if k == 2:
            mp = g(mirror)
            if not (px < mp[0] < px + pw and py < mp[1] < py + ph):
                d = (mp[0] - rp[0], mp[1] - rp[1])
                t = min(((px + 14 if d[0] < 0 else px + pw - 14) - rp[0]) / d[0] if d[0] else 9e9,
                        ((py + 14 if d[1] < 0 else py + ph - 14) - rp[1]) / d[1] if d[1] else 9e9)
                tip = (rp[0] + t * d[0], rp[1] + t * d[1])
                svg.line(*rp, *tip, P.black, 1.5, stroke_dasharray="4 5")
                arrow(svg, (tip[0] - 0.15 * t * d[0], tip[1] - 0.15 * t * d[1]), tip, P.black, 2.5, 13)
                alt = (_norm(mirror) - RE) / 1e6
                tag(svg, tip[0] - 14, tip[1] + 22, f"the other point: {alt:,.0f} 000 km up", "codel", 13, P.black,
                    "end", bg=P.white)
        svg.text(px, py - 30, titles[k][0], "code", 16, P.black)
        svg.text(px, py - 10, titles[k][1], "codel", 14, P.black_60)
    axis_label(svg, W - M, ART_TOP + 16, "Earth and orbits to scale · black dot: you", anchor="end")

    svg.frame("intersect.", "gnss positioning · trilateration · ranges, not angles")
    brief(svg, "a range says how far, not which way: one satellite puts you anywhere on a sphere",
          "intersect: two give a circle, three give two points, four leave one")
    code_rule(svg)
    svg.code(M, CODE_Y, """
# |x - sat_i| = r_i for every satellite i     (ranges, not angles)
ring = sphere(sat1, r1) & sphere(sat2, r2)          # a circle
a, b = ring & sphere(sat3, r3)                      # mirror images in the sats' plane
x = min((a, b), key=lambda p: abs(norm(p - sat4) - r4))   # the 4th agrees""", "py", 19)
    return svg


def solve_fix(sats_pos, rho, x0=(0.0, 0.0, 0.0, 0.0)):
    """Gauss-Newton on pseudoranges: (x, y, z, c·b). Yields each iterate."""
    x = list(x0)
    yield tuple(x)
    for _ in range(12):
        J, r = [], []
        for s, p in zip(sats_pos, rho):
            d = _sub(s, x[:3])
            n = _norm(d)
            J.append([-d[0] / n, -d[1] / n, -d[2] / n, 1.0])
            r.append(p - (n + x[3]))
        JtJ = [[sum(row[i] * row[j] for row in J) for j in range(4)] for i in range(4)]
        Jtr = [sum(row[i] * ri for row, ri in zip(J, r)) for i in range(4)]
        Q = inv(JtJ)
        dx = [sum(Q[i][j] * Jtr[j] for j in range(4)) for i in range(4)]
        x = [a + b for a, b in zip(x, dx)]
        yield tuple(x)
        if math.sqrt(sum(d * d for d in dx)) < 1e-4:
            break


def four() -> Svg:
    """The receiver clock is the fourth unknown: every range is long by the same c·b."""
    svg = Svg(P.cream)
    px0, py0, side = M, ART_TOP + 60, 520
    cx, cy = px0 + side / 2, py0 + side / 2
    s = side / 860  # px per metre, ±430 m
    dirs = [80, 205, 330]
    cb = C * 1e-6
    svg.rect(px0, py0, side, side, P.white, rx=8)
    svg.clip_begin(px0, py0, side, side)
    guesses = [(0.0, P.black_60, "b = 0"), (0.5, P.lavender, "b = 0.5 µs"), (1.0, P.blue, "b = 1.0 µs")]
    for b, col, _ in guesses:
        delta = cb - C * b * 1e-6
        lines = []
        for a in dirs:
            u = (math.cos(math.radians(a)), math.sin(math.radians(a)))
            lines.append((u, -delta))
        if delta > 1:
            verts = []
            for i in range(3):
                (u1, d1), (u2, d2) = lines[i], lines[(i + 1) % 3]
                det = u1[0] * u2[1] - u1[1] * u2[0]
                x = (d1 * u2[1] - d2 * u1[1]) / det
                y = (u1[0] * d2 - u2[0] * d1) / det
                verts.append((cx + x * s, cy - y * s))
            svg.poly(verts, col, opacity="0.12")
        for u, d in lines:
            p0 = (u[0] * d, u[1] * d)
            t = (-u[1], u[0])
            a_, b_ = _add(p0, _mul(t, -800)), _add(p0, _mul(t, 800))
            svg.line(cx + a_[0] * s, cy - a_[1] * s, cx + b_[0] * s, cy - b_[1] * s, col, 3 if b == 1.0 else 2)
    svg.clip_end()
    svg.circle(cx, cy, 7, P.black)
    for k, a in enumerate(dirs, 1):
        u = (math.cos(math.radians(a)), -math.sin(math.radians(a)))
        tip = (cx + u[0] * (side / 2 - 22), cy + u[1] * (side / 2 - 22))
        arrow(svg, (tip[0] - 40 * u[0], tip[1] - 40 * u[1]), tip, P.black, 2, 12)
        svg.text(tip[0] - 60 * u[0], tip[1] - 60 * u[1] + 5, f"to sat {k}", "code", 13, P.black, "middle")
    for j, (b, col, lab) in enumerate(guesses):
        y = py0 + side + 32 + j * 24
        svg.rect(px0, y - 12, 26, 5, col)
        svg.text(px0 + 36, y - 4, lab, "code", 15, col)
        r = (cb - C * b * 1e-6)
        axis_label(svg, px0 + 160, y - 4, "all three meet: the fix" if r < 1 else f"every range {r:.0f} m too long")
    svg.line(px0 + side - 100, py0 + side - 20, px0 + side - 100 + 100 * s, py0 + side - 20, P.black, 2.5)
    axis_label(svg, px0 + side - 100, py0 + side - 30, "100 m")

    # the real thing: 4 GPS satellites, Gauss-Newton from the centre of the Earth
    vis = visible(gps(), 0, 10)
    best = None
    import itertools
    for combo in itertools.combinations(vis, 4):
        gd = dops([c[3] for c in combo])["G"]
        if best is None or gd < best[0]:
            best = (gd, combo)
    truth = geodetic_to_ecef(*RX)
    spos = [c[0].ecef(0) for c in best[1]]
    rho = [_norm(_sub(p, truth)) + cb for p in spos]
    its = list(solve_fix(spos, rho))
    tx = px0 + side + 40
    svg.text(tx, py0 + 14, "in 3D: x, y, z and b", "code", 17, P.black)
    axis_label(svg, tx, py0 + 38, f"4 GPS sats ({', '.join(c[0].name for c in best[1])})")
    axis_label(svg, tx, py0 + 58, "start: the centre of the Earth")
    svg.text(tx, py0 + 100, "step   off by      c·b", "code", 14, P.black_60)
    for i, it in enumerate(its):
        err = _norm(_sub(it[:3], truth))
        e = f"{err / 1000:,.0f} km" if err > 2000 else f"{err:,.1f} m" if err > 0.05 else "0.0 m"
        cbs = f"{it[3] / 1000:,.0f} km" if abs(it[3]) > 2000 else f"{it[3]:.1f} m"
        svg.text(tx, py0 + 130 + i * 26, f"{i:>3}   {e:>9}   {cbs:>9}", "code", 15, P.blue if err < 0.05 else P.black)
    yb = py0 + 130 + len(its) * 26 + 20
    svg.text(tx, yb, f"c·b = {cb:.1f} m = 1 µs", "code", 15, P.blue)
    for j, ln in enumerate(["a quartz clock drifts ~0.5 ppm:", "150 m of range a second, so", "b is solved fresh every fix"]):
        axis_label(svg, tx, yb + 40 + j * 20, ln)

    svg.frame("four.", "gnss · pseudoranges · the receiver clock bias")
    brief(svg, "the receiver's clock is cheap quartz: 1 µs off is 300 m on every range",
          "make the clock an unknown too: x, y, z, b, so four satellites")
    code_rule(svg)
    svg.code(M, CODE_Y, """
rho_i = norm(sat_i - x) + c*b             # the same clock error on every range
J = [[*-unit(sat_i - x), 1] for sat_i in sats]     # one row per satellite
dx, dcb = lstsq(J, rho - predicted)       # Gauss-Newton: 4 unknowns, 4 sats
# in the plane: 3 unknowns (x, y, b), 3 lines that meet only when b is right""", "py", 19)
    return svg


def geoid() -> Svg:
    """Where on the ellipsoid, and how high above which surface."""
    svg = Svg(P.white)
    e2 = F_WGS * (2 - F_WGS)
    b_wgs = A_WGS * (1 - F_WGS)
    # top: the ellipsoid, drawn 60x flatter than it is
    ox, oy, ap = M + 10, ART_TOP + 330, 360
    bp = ap * (1 - 60 * F_WGS)
    pts_ = [(ox + ap * math.cos(t), oy - bp * math.sin(t)) for t in [math.pi / 2 * k / 80 for k in range(81)]]
    svg.poly([(ox, oy)] + pts_, P.teal_20)
    svg.polyline(pts_, P.teal, 2.5)
    svg.line(ox, oy, ox + ap + 40, oy, P.black, 1.5)
    svg.line(ox, oy, ox, oy - bp - 40, P.black, 1.5)
    axis_label(svg, ox + ap + 44, oy + 5, "x")
    axis_label(svg, ox + 8, oy - bp - 30, "z")
    phi = math.radians(52.5)
    fe = 60 * F_WGS
    beta = math.atan((1 - fe) * math.tan(phi))
    p = (ox + ap * math.cos(beta), oy - bp * math.sin(beta))
    n = (math.cos(phi), -math.sin(phi))
    foot = p[1] - oy  # normal meets the x axis here
    t_axis = foot / n[1]
    q = (p[0] - t_axis * n[0], oy)
    svg.line(q[0], q[1], p[0] + 70 * n[0], p[1] + 70 * n[1], P.blue, 2.5)
    svg.line(ox, oy, p[0], p[1], P.black_60, 2, stroke_dasharray="5 6")
    svg.circle(*p, 6, P.black)
    up = (p[0] + 70 * n[0], p[1] + 70 * n[1])
    svg.circle(*up, 6, P.blue)
    svg.text(up[0] + 12, up[1] - 6, "you, h above it", "code", 14, P.blue)
    svg.arc(q[0], q[1], 50, -phi, 0, P.blue, 2)
    svg.text(q[0] + 64 * math.cos(phi / 2), q[1] - 64 * math.sin(phi / 2) + 6, "φ", "code", 18, P.blue, "middle")
    psi = math.atan2(oy - p[1], p[0] - ox)
    svg.arc(ox, oy, 90, -psi, 0, P.black_60, 1.5)
    svg.text(ox + 108 * math.cos(psi / 2), oy - 108 * math.sin(psi / 2) + 6, "ψ", "code", 18, P.black_60, "middle")
    tx = M + 520
    phi45 = math.radians(45)
    dmax = math.degrees(phi45 - math.atan((1 - e2) * math.tan(phi45)))
    rows = [("a", f"{A_WGS:,.0f} m".replace(",", " "), P.black), ("b", f"{b_wgs:,.0f} m".replace(",", " "), P.black),
            ("f", "1 / 298.257223563", P.black), ("φ", "geodetic: along the normal (maps)", P.blue),
            ("ψ", "geocentric: from the centre", P.black_60)]
    for j, (k_, v_, col) in enumerate(rows):
        svg.text(tx, ART_TOP + 70 + j * 30, k_, "code", 17, col)
        svg.text(tx + 30, ART_TOP + 70 + j * 30, v_, "code", 15, col)
    axis_label(svg, tx, ART_TOP + 70 + 5 * 30 + 6, f"φ − ψ peaks at 45°: {dmax:.2f}° ≈ {dmax * 111.32:.0f} km on the ground")
    axis_label(svg, tx, ART_TOP + 70 + 5 * 30 + 28, "WGS 84 ellipsoid · drawn 60× flatter")

    # bottom: three heights
    x0, x1, ye = M, W - M, 990
    k = 1.55  # px per metre, vertical
    xs = [x0 + (x1 - x0) * i / 300 for i in range(301)]
    Nf = lambda t: 44 + 11 * math.sin(2 * math.pi * (1.1 * t + 0.1)) + 5 * math.sin(2 * math.pi * 2.7 * t)  # noqa: E731
    Hf = lambda t: max(0.0, 135 * math.exp(-((t - 0.7) / 0.13) ** 2) + 38 * math.exp(-((t - 0.45) / 0.09) ** 2)
                       + 12 * (t > 0.32) * (1 - math.exp(-(t - 0.32) * 30)))  # noqa: E731
    ts = [(x - x0) / (x1 - x0) for x in xs]
    geo = [(x, ye - k * Nf(t)) for x, t in zip(xs, ts)]
    land = [(x, ye - k * (Nf(t) + Hf(t))) for x, t in zip(xs, ts)]
    sea = [(x, y) for (x, y), t in zip(geo, ts) if t <= 0.33]
    svg.poly([(x0, ye)] + sea + [(sea[-1][0], ye)], P.lavender_20)
    svg.poly([(x, y) for (x, y), t in zip(land, ts) if t >= 0.32] + [(x1, ye), (xs[96], ye)], P.teal_20)
    svg.polyline([(x, y) for (x, y), t in zip(land, ts) if t >= 0.32], P.teal, 2.5)
    svg.polyline(geo, P.lavender, 2.5, stroke_dasharray="7 6")
    svg.line(x0, ye, x1, ye, P.black, 2.5)
    tp = 0.7
    xp = x0 + (x1 - x0) * tp
    N_, H_ = Nf(tp), Hf(tp)
    yp, yg = ye - k * (N_ + H_), ye - k * N_
    svg.circle(xp, yp, 7, P.black)
    for xo, ya, yb_, col, lab in [(-58, ye, yp, P.blue, f"h = {N_ + H_:.0f} m · GPS"),
                                  (26, ye, yg, P.lavender, f"N = {N_:.0f} m · geoid model"),
                                  (26, yg, yp, P.black, f"H = {H_:.0f} m · the map")]:
        xx = xp + xo
        svg.line(xx, ya, xx, yb_, col, 2.5)
        for yy in (ya, yb_):
            svg.line(xx - 6, yy, xx + 6, yy, col, 2.5)
        if xo < 0:
            tag(svg, xx - 10, yb_ + 30, lab, "code", 15, col, "end", bg=P.white)
        else:
            tag(svg, xx + 12, (ya + yb_) / 2 + 5, lab, "code", 15, col, bg=P.white)
    svg.text(x0 + 6, ye - 12, "ellipsoid: smooth maths", "code", 14, P.black)
    svg.text(x0 + 6, geo[0][1] - 30, "geoid: where the sea would sit", "code", 14, P.lavender)
    axis_label(svg, x0, ye + 26, "heights to scale, distance not · the geoid runs from −106 m (south of India) to +85 m"
               " (New Guinea)", size=13)

    svg.frame("geoid.", "wgs 84 · ellipsoid, geoid, sea level · h = N + H")
    brief(svg, "GPS measures height above a smooth ellipsoid; sea level wanders ±100 m around it",
          "subtract a geoid model: H = h − N, and the height matches the map")
    code_rule(svg)
    svg.code(M, CODE_Y, """
x, y, z = solve(pseudoranges)                    # GPS works in ECEF metres
lat, lon, h = ecef_to_geodetic(x, y, z)          # a = 6378137, f = 1/298.257
H = h - egm2008.N(lat, lon)                      # above sea level, for maps
# at 52.5° N, N ≈ +40 m: skip it and every altitude reads 40 m high""", "py", 19)
    return svg


def dop() -> Svg:
    """HDOP, VDOP, PDOP over a day: GPS alone against all four constellations."""
    svg = Svg(P.black)
    g_only, alls = gps(), everyone()
    day = 86164
    series = []
    for t in range(0, day, 600):
        a = visible(g_only, t, 10)
        b = visible(alls, t, 10)
        series.append((t, dops([v[3] for v in a]), dops([v[3] for v in b]), len(a), len(b)))
    t_bad = max(series, key=lambda r: r[1]["P"])[0]
    ratio = sorted(r[1]["V"] / r[1]["H"] for r in series)[len(series) // 2]
    R = 135
    for k, (sats, title, col) in enumerate([(g_only, "GPS only", P.lavender), (alls, "all four", P.teal_60)]):
        cx, cy = M + 170 + k * 470, ART_TOP + 210
        g = skyplot(svg, cx, cy, R, dark=True, rings=(0, 30, 60))
        vis = visible(sats, t_bad, 10)
        for s, az, el, _ in vis:
            svg.circle(*g(az, el), 6, sys_col(s.sys, True))
        d = dops([v[3] for v in vis])
        svg.text(cx - R - 20, ART_TOP + 40, f"{title} · {len(vis)} in view", "code", 16, col)
        tx = cx + R + 40
        for j, key in enumerate("HVPTG"):
            svg.text(tx, cy - 70 + j * 30, f"{key}DOP", "code", 14, P.blue_40)
            svg.text(tx + 110, cy - 70 + j * 30, f"{d[key]:.1f}", "code", 18, P.white if key in "HV" else col, "end")
    axis_label(svg, W - M, ART_TOP + 18, f"the worst moment of the day for GPS alone: {t_bad / 3600:.1f} h", True, "end")
    # a day of it
    x0, x1, y0, y1 = M + 50, W - M, 720, 990
    vmax = 5.0
    gx = lambda t: x0 + (x1 - x0) * t / day  # noqa: E731
    gy = lambda v: y1 - (y1 - y0) * min(v, vmax) / vmax  # noqa: E731
    chart_axes(svg, x0, y0, x1, y1, True)
    for v in range(0, 6):
        axis_label(svg, x0 - 12, gy(v) + 5, f"{v}", True, "end")
    for h in range(0, 25, 6):
        axis_label(svg, gx(h * 3600 * day / 86400), y1 + 22, f"{h} h", True, "middle")
    svg.line(gx(t_bad), y0, gx(t_bad), y1, P.black_60, 1.5, stroke_dasharray="4 5")
    for idx, col in [(1, P.lavender), (2, P.teal_60)]:
        for key, dash, w in [("V", None, 3), ("H", "2 6", 3)]:
            pl = [(gx(r[0]), gy(r[idx][key])) for r in series]
            if dash:
                svg.polyline(pl, col, w, stroke_dasharray=dash)
            else:
                svg.polyline(pl, col, w)
    svg.text(x0 + 16, y0 + 6, "solid VDOP · dotted HDOP", "codel", 14, P.blue_40)
    svg.text(x0 + 16, y0 + 32, "GPS only", "code", 15, P.lavender)
    svg.text(x0 + 116, y0 + 32, "all four", "code", 15, P.teal_60)

    svg.frame("dop.", "dilution of precision · H, V, P, T, G · 24 h from 52.5° N", dark=True, title_fill=P.white)
    brief(svg, "all the satellites are above you and none below: height is always the weak axis",
          f"expect VDOP ≈ {ratio:.1f} × HDOP; more constellations pull every DOP down", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
H = [[-e, -n, -u, 1] for e, n, u in units]       # one row per satellite in view
Q = inv(H.T @ H)                                 # range noise -> fix noise
hdop, vdop = sqrt(Q[0,0] + Q[1,1]), sqrt(Q[2,2])
pdop, tdop = sqrt(Q[0,0] + Q[1,1] + Q[2,2]), sqrt(Q[3,3])   # σ_fix = DOP × σ_range""", "py", 18, dark=True)
    return svg


# ============================================================================
# error
# ============================================================================
UERE = [("ionosphere", 4.0, "a single-band model gets half of it"), ("satellite clock", 1.1, "broadcast fit, hours old"),
        ("multipath", 1.0, "reflections near the antenna"), ("orbit", 0.8, "where the satellite thinks it is"),
        ("troposphere", 0.5, "water vapour, modelled"), ("receiver noise", 0.3, "tracking jitter")]


def errors() -> Svg:
    """The range error budget: six sources along the path, and how they add (as squares)."""
    svg = Svg(P.cream)
    total = math.sqrt(sum(v * v for _, v, _ in UERE))
    linear = sum(v for _, v, _ in UERE)
    hdop = 1.2
    # left: where each one happens, top (satellite) to bottom (antenna)
    rx, top, bot = M + 18, ART_TOP + 70, 985
    where = {"satellite clock": top + 20, "orbit": top + 80, "ionosphere": top + 250, "troposphere": top + 400,
             "multipath": bot - 90, "receiver noise": bot - 18}
    svg.rect(M, where["ionosphere"] - 34, 470, 68, P.lavender_20, rx=6)
    svg.rect(M, where["troposphere"] - 26, 470, 52, P.teal_20, rx=6)
    svg.line(rx, top - 20, rx, bot, P.black, 2, stroke_dasharray="5 6")
    svg.rect(rx - 14, top - 40, 28, 18, P.black, rx=3)
    svg.rect(rx - 34, top - 36, 16, 10, P.blue_60)
    svg.rect(rx + 18, top - 36, 16, 10, P.blue_60)
    svg.rect(rx - 10, bot, 20, 10, P.black, rx=2)
    k = 52
    cols = [P.blue, P.black, P.black_60, P.teal, P.lavender, P.black_80]
    for (name, v, sub), col in zip(UERE, cols):
        y = where[name]
        svg.circle(rx, y, 5, col)
        svg.text(rx + 26, y - 6, name, "code", 15, col)
        axis_label(svg, rx + 26, y + 14, sub, size=12)
        bx = rx + 236
        svg.rect(bx, y - 18, v * k, 14, col, rx=3)
        svg.text(bx + v * k + 8, y - 6, f"{v:.1f} m", "code", 14, col)
    axis_label(svg, W - M, ART_TOP + 16, "1σ range error, metres · single-band receiver, open sky", anchor="end")

    # right: the errors are independent, so they add like the sides of right triangles
    ox, oy, kk = 574, 905, 92
    pts_ = [(ox, oy)]
    cur = (0.0, 0.0)
    for j, (name, v, _) in enumerate(UERE):
        if j == 0:
            step = (v, 0.0)
        else:
            h = _unit(cur)
            step = (-h[1] * v, h[0] * v)  # perpendicular to the running total
        nxt = (cur[0] + step[0], cur[1] + step[1])
        a, b = (ox + cur[0] * kk, oy - cur[1] * kk), (ox + nxt[0] * kk, oy - nxt[1] * kk)
        if j:
            svg.line(ox, oy, *a, P.black_20, 1.2)
        svg.line(*a, *b, cols[j], 5, stroke_linecap="round")
        cur = nxt
        pts_.append(b)
    end_ = (ox + cur[0] * kk, oy - cur[1] * kk)
    svg.line(ox, oy, *end_, P.blue, 3.5, stroke_dasharray="9 6")
    svg.circle(ox, oy, 5, P.black)
    mid = ((ox + end_[0]) / 2, (oy + end_[1]) / 2)
    tag(svg, mid[0] - 30, mid[1] - 2, f"{total:.1f} m", "code", 22, P.blue, "middle", bg=P.cream)
    axis_label(svg, ox, oy + 30, "each error at right angles to the running total")
    axis_label(svg, ox, oy + 50, f"added straight: {linear:.1f} m · as squares: {total:.1f} m")
    svg.text(574, ART_TOP + 60, f"σ_range = {total:.1f} m", "code", 20, P.black)
    svg.text(574, ART_TOP + 92, f"× HDOP {hdop} = {total * hdop:.1f} m across", "code", 20, P.blue)

    svg.frame("errors.", "gnss error budget · UERE · root sum of squares")
    brief(svg, "six independent errors land on every range; the sky itself is the biggest",
          f"they add as squares, not straight: {total:.1f} m, not {linear:.1f}; go after the biggest first")
    code_rule(svg)
    svg.code(M, CODE_Y, """
budget = {"iono": 4.0, "clock": 1.1, "multipath": 1.0,
          "orbit": 0.8, "tropo": 0.5, "receiver": 0.3}     # 1σ, metres
uere = sqrt(sum(s**2 for s in budget.values()))     # 4.4 m: squares add
sigma_h = hdop * uere                               # the fix, across: 5.3 m""", "py", 19)
    return svg


def _tri(t):
    return max(0.0, 1 - abs(t))


def track_error(alpha, delay, d):
    """Where an early-late tracker settles (chips) with one reflection of relative amplitude alpha."""
    c = lambda t: _tri(t) + alpha * _tri(t - delay)  # noqa: E731
    prev = None
    for i in range(0, 4401):
        tau = -0.6 + i * 0.0005
        f = c(tau - d / 2) - c(tau + d / 2)
        if prev is not None and prev < 0 <= f:
            return tau
        prev = f
    return 0.0


def multipath() -> Svg:
    """A reflection off a wall: the correlation peak smears; a narrow correlator is fooled less."""
    svg = Svg(P.white)
    el, D, alpha = 25.0, 75.0, 0.5
    gy, ax = 640, 360
    s = 400 / D
    wx = ax + D * s
    d = (math.cos(math.radians(el)), math.sin(math.radians(el)))
    ant = (ax, gy - 22)
    svg.line(M, gy, W - M, gy, P.black, 2.5)
    svg.rect(wx, ART_TOP + 50, 150, gy - ART_TOP - 50, P.lavender_20, stroke=P.lavender, stroke_width=2)
    for yy in range(ART_TOP + 80, gy - 20, 44):
        svg.line(wx + 20, yy, wx + 130, yy, P.lavender_60, 1)
    t = (wx - ax) / math.cos(math.radians(el))
    R = (ant[0] + t * math.cos(math.radians(el)), ant[1] - t * math.sin(math.radians(el)))
    L = 600
    svg.clip_begin(M, ART_TOP + 40, W - 2 * M, gy - ART_TOP - 40)
    svg.line(R[0] - L * d[0], R[1] - L * d[1], *R, P.lavender, 3)
    svg.line(*R, *ant, P.lavender, 3)
    back = _unit((ant[0] - R[0], ant[1] - R[1]))
    mid_ = ((R[0] + ant[0]) / 2, (R[1] + ant[1]) / 2)
    arrow(svg, (mid_[0] - 40 * back[0], mid_[1] - 40 * back[1]), mid_, P.lavender, 3, 14)
    svg.line(ant[0] - L * d[0], ant[1] - L * d[1], *ant, P.blue, 4)
    arrow(svg, (ant[0] - 120 * d[0], ant[1] - 120 * d[1]), (ant[0] - 60 * d[0], ant[1] - 60 * d[1]), P.blue, 4, 16)
    svg.clip_end()
    svg.line(ax, gy, ax, ant[1], P.black, 4)
    svg.rect(ax - 22, ant[1] - 8, 44, 10, P.black, rx=4)
    extra = 2 * D * math.cos(math.radians(el))
    delay = extra / CHIP
    svg.text(M, ART_TOP + 70, "direct", "code", 16, P.blue)
    axis_label(svg, M, ART_TOP + 92, f"satellite at {el:.0f}°")
    svg.text(wx - 14, R[1] - 16, f"+{extra:.0f} m = {delay:.2f} chip", "code", 16, P.lavender, "end")
    axis_label(svg, wx - 14, R[1] + 6, f"reflected, {alpha:.0%} as strong", anchor="end")
    svg.text(wx + 75, gy + 26, f"glass, {D:.0f} m away", "code", 14, P.black, "middle")
    svg.text(ax, gy + 26, "antenna", "code", 14, P.black, "middle")

    # correlation: what the tracker sees
    x0, x1, y0, y1 = M, M + 420, 730, 990
    gx = lambda tt: x0 + (x1 - x0) * (tt + 1.3) / 3.1  # noqa: E731
    gyy = lambda v: y1 - (y1 - y0) * v / 1.6  # noqa: E731
    ts = [-1.3 + 3.1 * i / 310 for i in range(311)]
    svg.line(x0, y1, x1, y1, P.black, 1.5)
    svg.polyline([(gx(tt), gyy(_tri(tt))) for tt in ts], P.blue, 2.5)
    svg.polyline([(gx(tt), gyy(alpha * _tri(tt - delay))) for tt in ts], P.lavender, 2.5)
    csum = lambda tt: _tri(tt) + alpha * _tri(tt - delay)  # noqa: E731
    svg.polyline([(gx(tt), gyy(csum(tt))) for tt in ts], P.black, 4)
    tau = track_error(alpha, delay, 1.0)
    for e in (tau - 0.5, tau + 0.5):
        svg.circle(gx(e), gyy(csum(e)), 6, P.white, stroke=P.black, stroke_width=2.5)
    svg.line(gx(tau), gyy(csum(tau)) - 10, gx(tau), y1, P.black, 1.5, stroke_dasharray="4 4")
    svg.line(gx(0), gyy(1) - 10, gx(0), y1, P.blue, 1.5, stroke_dasharray="4 4")
    svg.text(gx(tau) + 8, y0 + 4, f"tracks here: {tau * CHIP:+.0f} m", "code", 14, P.black)
    axis_label(svg, gx(0) - 8, y0 + 34, "truth", anchor="end")
    axis_label(svg, x0, y1 + 24, "delay, chips →  ·  ○ early and late, 1 chip apart")
    svg.text(x0, y0 - 18, "the peak it tracks", "code", 16, P.black)

    # error envelope: every delay, two correlator spacings
    ex0, ex1 = M + 510, W - M
    emax = 80.0
    gex = lambda dl: ex0 + (ex1 - ex0) * dl / 1.6  # noqa: E731
    gey = lambda m: (y0 + y1) / 2 - (y1 - y0) / 2 * m / emax  # noqa: E731
    svg.line(ex0, gey(0), ex1, gey(0), P.black, 1.5)
    svg.line(ex0, y0, ex0, y1, P.black, 1.5)
    for m in (-60, -30, 30, 60):
        axis_label(svg, ex0 - 8, gey(m) + 5, f"{m:+d}", anchor="end", size=12)
    for dl in (0.5, 1.0, 1.5):
        axis_label(svg, gex(dl), gey(0) + 20, f"{dl}", anchor="middle", size=12)
    dls = [1.6 * i / 160 for i in range(161)]
    for dsp, col, lab in [(1.0, P.black_60, "1 chip spacing"), (0.1, P.blue, "0.1 chip")]:
        for a in (alpha, -alpha):
            svg.polyline([(gex(dl), gey(track_error(a, dl, dsp) * CHIP)) for dl in dls], col, 3 if dsp < 1 else 2.5)
        e1 = track_error(alpha, delay, dsp) * CHIP
        svg.circle(gex(delay), gey(e1), 5.5, col)
        svg.text(ex1, gey(track_error(alpha, 0.5, dsp) * CHIP) - 10 if dsp == 1 else gey(18), lab, "code", 14, col, "end")
    svg.text(ex0, y0 - 18, "error, m, for every reflection delay", "code", 16, P.black)
    axis_label(svg, ex1, y1 + 24, "reflection delay, chips", anchor="end")
    e_wide, e_narrow = track_error(alpha, delay, 1.0) * CHIP, track_error(alpha, delay, 0.1) * CHIP

    svg.frame("multipath.", "code multipath · early-late correlator · error envelope")
    brief(svg, "a wall adds a late, weaker copy; the correlation peak leans toward it",
          f"narrow the early-late spacing: {e_wide:.0f} m becomes {e_narrow:.0f} m; choke rings do the rest")
    code_rule(svg)
    svg.code(M, CODE_Y, """
C = lambda t: R(t) + a * R(t - delay)    # direct + reflection: one smeared peak
early, late = C(tau - d/2), C(tau + d/2)
tau = solve(early == late)               # the tracker sits where they balance
# d = 1 chip: tens of metres off · d = 0.1 chip: a tenth of that""", "py", 19)
    return svg


def canyon() -> Svg:
    """A street between 30 m buildings: the sky becomes a strip, and one constellation isn't enough."""
    svg = Svg(P.black)
    Hb, w, street = 24.0, 30.0, 0.0  # building height, street width (m), street runs north-south

    def mask(az):
        return math.degrees(math.atan(Hb * abs(math.sin(math.radians(az - street))) / (w / 2)))

    # cross-section
    gy, k = 905, 6.0
    cx = M + 170
    xl, xr = cx - w / 2 * k, cx + w / 2 * k
    for x0_, x1_ in [(M, xl), (xr, xr + (xl - M))]:
        svg.rect(x0_, gy - Hb * k, x1_ - x0_, Hb * k, P.black_80)
        for yy in range(int(gy - Hb * k) + 20, gy - 10, 34):
            for xx in range(int(x0_) + 14, int(x1_) - 20, 30):
                svg.rect(xx, yy, 14, 18, P.blue_60, opacity="0.35", rx=2)
    svg.line(M, gy, xr + (xl - M), gy, P.blue_40, 2)
    rxp = (cx, gy - 4)
    for xe in (xl, xr):
        dx, dy = xe - rxp[0], (gy - Hb * k) - rxp[1]
        svg.line(*rxp, rxp[0] + dx * 1.45, rxp[1] + dy * 1.45, P.lavender, 1.8, stroke_dasharray="5 5")
    svg.poly([rxp, (rxp[0] + (xl - cx) * 1.45, rxp[1] + (gy - Hb * k - rxp[1]) * 1.45),
              (rxp[0] + (xr - cx) * 1.45, rxp[1] + (gy - Hb * k - rxp[1]) * 1.45)], P.lavender, opacity="0.15")
    svg.rect(cx - 8, gy - 12, 16, 10, P.white, rx=2)
    svg.text(cx, gy + 26, f"{w:.0f} m street", "code", 14, P.white, "middle")
    svg.text(M + 8, gy - Hb * k - 12, f"{Hb:.0f} m", "code", 14, P.blue_40)
    m90 = mask(90)
    svg.text(cx, gy - Hb * k * 1.55, f"open across: {90 - m90:.0f}° each side", "code", 14, P.lavender, "middle")
    svg.text(cx, gy - Hb * k * 1.55 + 20, "of straight up", "codel", 13, P.blue_40, "middle")

    # skyplot with the buildings' mask
    scx, scy, R = 742, ART_TOP + 290, 228
    rim = [(scx + R * math.sin(math.radians(a)), scy - R * math.cos(math.radians(a))) for a in range(0, 361, 3)]
    svg.poly(rim, P.blue, opacity="0.28")

    def gsky(az, el):
        r = R * (90 - el) / 90
        return scx + r * math.sin(math.radians(az)), scy - r * math.cos(math.radians(az))
    svg.poly([gsky(a, mask(a)) for a in range(0, 361, 2)], P.black)
    skyplot(svg, scx, scy, R, dark=True)
    tag(svg, *gsky(90, 30), "wall", "code", 14, P.blue_40, "middle", bg=P.black)
    tag(svg, *gsky(270, 30), "wall", "code", 14, P.blue_40, "middle", bg=P.black)
    alls = everyone()
    t = 0
    seen = {"open": [], "canyon": []}
    for s_ in alls:
        az, el, u = look(s_, t)
        if el < 10:
            continue
        seen["open"].append((s_, u))
        col = sys_col(s_.sys, True)
        p = gsky(az, el)
        if el > mask(az):
            seen["canyon"].append((s_, u))
            svg.circle(*p, 7, col)
        else:
            svg.circle(*p, 6, "none", stroke=col, stroke_width=1.5, opacity="0.6")
    ys = scy + R + 52
    for j, name in enumerate(("GPS", "GLONASS", "Galileo", "BeiDou")):
        svg.circle(scx - R + 6 + j * 118, ys - 5, 6, sys_col(name, True))
        svg.text(scx - R + 18 + j * 118, ys, name, "code", 13, sys_col(name, True))
    axis_label(svg, scx - R, ys + 24, "filled: in the street's strip of sky · hollow: behind a wall", True, size=13)

    def summary(lst):
        g = [u for s_, u in lst if s_.sys == "GPS"]
        a = [u for _, u in lst]
        hg = dops(g)["H"] if len(g) >= 4 else None
        return len(g), len(a), hg, dops(a)["H"]
    o, c_ = summary(seen["open"]), summary(seen["canyon"])
    ty = 1000
    hg_c = "no fix" if c_[2] is None else f"HDOP {c_[2]:.1f}"
    svg.text(M, ty - 26, f"open sky   GPS {o[0]:>2} · HDOP {o[2]:.1f}    all four {o[1]:>2} · HDOP {o[3]:.1f}", "code", 15,
             P.blue_40)
    svg.text(M, ty, f"canyon     GPS {c_[0]:>2} · {hg_c:<8}    all four {c_[1]:>2} · HDOP {c_[3]:.1f}", "code", 15,
             P.white)

    svg.frame("canyon.", "urban canyon · visibility mask · multi-constellation", dark=True, title_fill=P.white)
    brief(svg, f"between {Hb:.0f} m buildings the sky shrinks to a strip along the street",
          f"listen to every constellation: {c_[0]} GPS left, but {c_[1]} across all four", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
mask = lambda az: atan(H * abs(sin(az - street)) / (w / 2))   # the roofline
seen = [s for s in sky if s.el > max(mask(s.az), 10)]       # what's left
# along the street: fine · across it: HDOP grows, reflections creep in""", "py", 19, dark=True)
    return svg


def cep() -> Svg:
    """2000 fixes and the circles people quote: CEP, DRMS, R95, 2DRMS."""
    svg = Svg(P.cream)
    rng = random.Random(21)
    se, sn, rot = 1.4, 2.3, math.radians(25)
    pts_ = []
    for _ in range(2000):
        a, b = rng.gauss(0, se), rng.gauss(0, sn)
        pts_.append((a * math.cos(rot) - b * math.sin(rot), a * math.sin(rot) + b * math.cos(rot)))
    r = sorted(math.hypot(*p) for p in pts_)
    n = len(r)
    drms = math.sqrt(sum(v * v for v in r) / n)
    circles = [("CEP", r[n // 2], P.blue), ("DRMS", drms, P.teal), ("R95", r[int(0.95 * n)], P.black_60),
               ("2DRMS", 2 * drms, P.black)]
    cx, cy, k = M + 330, ART_TOP + 340, 50
    svg.line(cx - 310, cy, cx + 310, cy, P.black_20, 1)
    svg.line(cx, cy - 310, cx, cy + 310, P.black_20, 1)
    svg.clip_begin(cx - 330, cy - 320, 660, 640)
    for x, y in pts_:
        svg.circle(cx + x * k, cy - y * k, 2.2, P.blue_60, opacity="0.55")
    svg.clip_end()
    for j, (name, rad, col) in enumerate(circles):
        svg.circle(cx, cy, rad * k, "none", stroke=col, stroke_width=3 if name == "CEP" else 2.2)
        a = math.radians(-50 + 18 * j)
        p = (cx + rad * k * math.cos(a), cy + rad * k * math.sin(a))
        tag(svg, p[0] + 6, p[1] + 6, name, "code", 15, col, bg=P.cream)
    svg.circle(cx, cy, 5, P.black)
    svg.line(cx + 200, cy + 330, cx + 200 + k, cy + 330, P.black, 2.5)
    axis_label(svg, cx + 200 + k / 2, cy + 320, "1 m", anchor="middle")
    axis_label(svg, cx - 320, cy + 330, f"{n} fixes, σ {se} × {sn} m, tilted")

    tx = M + 690
    svg.text(tx, ART_TOP + 60, "circle    r      inside", "code", 14, P.black_60)
    for j, (name, rad, col) in enumerate(circles):
        inside = sum(v <= rad for v in r) / n
        y = ART_TOP + 96 + j * 34
        svg.text(tx, y, f"{name:<7} {rad:4.1f} m  {inside:5.0%}", "code", 16, col)
    for j, ln in enumerate(["CEP: half land inside", "DRMS: √(mean r²), ~65 %", "R95: 95 % inside",
                            "2DRMS: 2 × DRMS, ~95–98 %"]):
        axis_label(svg, tx, ART_TOP + 260 + j * 22, ln, size=13)

    # accuracy vs precision, four little targets
    ty0 = ART_TOP + 380
    kinds = [("precise, accurate", 0.25, (0, 0)), ("precise, biased", 0.25, (0.9, 0.6)),
             ("scattered, unbiased", 0.8, (0, 0)), ("neither", 0.8, (0.8, -0.7))]
    for j, (lab, sg, off) in enumerate(kinds):
        bx, by = tx + (j % 2) * 130 + 52, ty0 + (j // 2) * 150 + 56
        for rr in (48, 32, 16):
            svg.circle(bx, by, rr, "none", stroke=P.black_20, stroke_width=1.2)
        svg.circle(bx, by, 3, P.black)
        for _ in range(14):
            svg.circle(bx + (off[0] + rng.gauss(0, sg)) * 26, by - (off[1] + rng.gauss(0, sg)) * 26, 3.2, P.blue)
        axis_label(svg, bx, by + 74, lab, anchor="middle", size=12)

    svg.frame("cep.", "accuracy statistics · CEP, DRMS, R95, 2DRMS")
    brief(svg, "'accurate to 3 m' means little until you say which circle, and how many land in it",
          "quote the circle: CEP holds half, DRMS about 65 %, 2DRMS about 95 %")
    code_rule(svg)
    svg.code(M, CODE_Y, """
r = hypot(e - e_true, n - n_true)        # each fix's distance from the truth
cep  = percentile(r, 50)                 # half inside
drms = sqrt(mean(r**2))                  # 2DRMS = 2 * drms: ~95 % inside
r95  = percentile(r, 95)                 # and bias is a separate question""", "py", 19)
    return svg


# ============================================================================
# augment
# ============================================================================
def antenna(svg, x, y, col=P.black, tripod=False):
    """A survey antenna on a pole (y = ground)."""
    if tripod:
        for dx in (-22, 0, 22):
            svg.line(x, y - 40, x + dx, y, col, 3)
    else:
        svg.line(x, y, x, y - 40, col, 4)
    svg.rect(x - 22, y - 52, 44, 12, col, rx=6)


def dgps() -> Svg:
    """A base on a known point measures each range's error and sends it; it fades with distance."""
    svg = Svg(P.white)
    common = [("satellite clock", 1.1, 1e12), ("orbit", 0.8, 2e4), ("ionosphere", 4.0, 1500), ("troposphere", 0.5, 100)]
    local_rover, local_base = [("multipath", 1.0), ("receiver", 0.3)], [("multipath", 0.3), ("receiver", 0.3)]

    def resid(d):
        v = sum(2 * s * s * (1 - math.exp(-d / L)) for _, s, L in common)
        v += sum(s * s for _, s in local_rover) + sum(s * s for _, s in local_base)
        return math.sqrt(v)
    alone = math.sqrt(sum(s * s for _, s, _ in common) + sum(s * s for _, s in local_rover))

    # scene
    gy = 650
    base, rover = (M + 120, gy), (W - M - 120, gy)
    sats = [(M + 200, ART_TOP + 60), (540, ART_TOP + 40), (W - M - 180, ART_TOP + 70)]
    svg.rect(M, ART_TOP + 130, W - 2 * M, 50, P.lavender_20, rx=6)
    axis_label(svg, W - M - 10, ART_TOP + 160, "ionosphere: nearly the same over both", anchor="end")
    for j, sp in enumerate(sats):
        for tgt in (base, rover):
            svg.line(*sp, tgt[0], tgt[1] - 52, P.blue_40, 1.5)
        svg.rect(sp[0] - 12, sp[1] - 8, 24, 16, P.blue, rx=3)
        svg.rect(sp[0] - 36, sp[1] - 4, 18, 8, P.blue_60)
        svg.rect(sp[0] + 18, sp[1] - 4, 18, 8, P.blue_60)
    svg.line(M, gy, W - M, gy, P.black, 2.5)
    antenna(svg, *base, P.black, tripod=True)
    antenna(svg, *rover, P.teal)
    svg.rect(rover[0] - 40, gy - 22, 80, 22, P.teal, rx=6)
    pts_ = [(base[0] + (rover[0] - base[0]) * t, gy - 95 - 120 * math.sin(math.pi * t)) for t in [k / 40 for k in range(41)]]
    svg.polyline(pts_, P.black, 2, stroke_dasharray="2 7")
    arrow(svg, pts_[-6], pts_[-2], P.black, 2, 14)
    tag(svg, 540, gy - 222, "corrections, every second", "code", 15, P.black, "middle", bg=P.white)
    svg.text(base[0], gy + 28, "base · surveyed point", "code", 15, P.black, "middle")
    svg.text(rover[0], gy + 28, "rover", "code", 15, P.teal, "middle")
    svg.line(base[0], gy + 50, rover[0], gy + 50, P.black_60, 1.5)
    axis_label(svg, 540, gy + 44, "30 km", anchor="middle")

    # residual against baseline
    x0, x1, y0, y1 = M + 60, W - M, 760, 995
    dmax, emax = 300.0, 5.0
    gx = lambda d: x0 + (x1 - x0) * d / dmax  # noqa: E731
    gyy = lambda e: y1 - (y1 - y0) * e / emax  # noqa: E731
    chart_axes(svg, x0, y0, x1, y1)
    for e in range(0, 6):
        axis_label(svg, x0 - 12, gyy(e) + 5, f"{e}", anchor="end")
    for d in (0, 50, 100, 150, 200, 250, 300):
        axis_label(svg, gx(d), y1 + 22, f"{d}", anchor="middle")
    axis_label(svg, x1, y1 + 44, "distance to the base, km", anchor="end")
    axis_label(svg, x0 - 12, y0 - 16, "1σ range error left, m")
    svg.line(x0, gyy(alone), x1, gyy(alone), P.black_60, 2.5, stroke_dasharray="8 6")
    svg.text(x1, gyy(alone) - 12, f"alone: {alone:.1f} m", "code", 15, P.black_60, "end")
    ds = [dmax * k / 150 for k in range(151)]
    svg.polyline([(gx(d), gyy(resid(d))) for d in ds], P.blue, 4)
    for d in (10, 100, 300):
        p = (gx(d), gyy(resid(d)))
        svg.circle(*p, 6, P.blue)
        svg.text(p[0] + (10 if d < 300 else -10), p[1] - 14, f"{resid(d):.1f} m", "code", 15, P.blue,
                 "start" if d < 300 else "end")
    svg.text(gx(4), gyy(0.45), "even at 0 km: multipath is local, it never cancels", "codel", 14, P.black_60)

    svg.frame("dgps.", "differential gnss · reference station · range corrections")
    brief(svg, "most of each range's error is the same for every receiver within tens of km",
          f"a base on a known spot measures it and sends it: {alone:.1f} m → {resid(10):.1f} m nearby")
    code_rule(svg)
    svg.code(M, CODE_Y, """
corr_i = norm(sat_i - base_known) - rho_base_i    # what it should be, minus seen
rho_rover_i += corr_i                             # same sky, same error: gone
# clocks cancel fully; iono and tropo fade with distance; multipath never""", "py", 19)
    return svg


def sbas() -> Svg:
    """A continent of reference stations fits an ionosphere grid; a GEO satellite broadcasts it."""
    svg = Svg(P.black)
    rng = random.Random(9)
    x0, x1, y0, y1 = M + 56, W - M - 24, 570, 930
    lon0, lon1, lat0, lat1 = -10, 40, 35, 70
    gx = lambda lon: x0 + (x1 - x0) * (lon - lon0) / (lon1 - lon0)  # noqa: E731
    gy = lambda lat: y1 - (y1 - y0) * (lat - lat0) / (lat1 - lat0)  # noqa: E731

    def vtec(lat, lon):  # a smooth daytime field: more electrons toward the equator, peaking past local noon
        return 7 + 26 * math.exp(-((lat - 30) / 15) ** 2) * (0.65 + 0.35 * math.cos(math.radians((lon - 22) * 3)))
    geo = (540, ART_TOP + 52)
    svg.poly([geo, (x0, y0), (x1, y0)], P.lavender, opacity="0.07")
    svg.line(*geo, x0, y0, P.lavender, 1, opacity="0.4")
    svg.line(*geo, x1, y0, P.lavender, 1, opacity="0.4")
    svg.rect(geo[0] - 16, geo[1] - 11, 32, 22, P.white, rx=3)
    svg.rect(geo[0] - 56, geo[1] - 6, 34, 12, P.blue_60)
    svg.rect(geo[0] + 22, geo[1] - 6, 34, 12, P.blue_60)
    svg.text(geo[0] + 72, geo[1] + 6, "geostationary · 36 000 km · on L1", "code", 15, P.white)
    # reference stations, and the master that turns them into a grid
    stations = []
    while len(stations) < 34:
        p = (rng.uniform(lon0 + 1, lon1 - 1), rng.uniform(lat0 + 1, lat1 - 1))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 4.5 for q in stations):
            stations.append(p)
    mcc = (2.0, 48.0)
    svg.line(gx(mcc[0]), gy(mcc[1]), *geo, P.teal_60, 2, stroke_dasharray="6 6")
    arrow(svg, (gx(mcc[0]) + (geo[0] - gx(mcc[0])) * 0.55, gy(mcc[1]) + (geo[1] - gy(mcc[1])) * 0.55),
          (gx(mcc[0]) + (geo[0] - gx(mcc[0])) * 0.6, gy(mcc[1]) + (geo[1] - gy(mcc[1])) * 0.6), P.teal_60, 2, 14)
    for lat in range(lat0, lat1 + 1, 5):
        svg.line(x0, gy(lat), x1, gy(lat), P.black_80, 1)
        axis_label(svg, x0 - 26, gy(lat) + 5, f"{lat}°", True, "end", 12)
    for lon in range(lon0, lon1 + 1, 5):
        svg.line(gx(lon), y0, gx(lon), y1, P.black_80, 1)
        axis_label(svg, gx(lon), y1 + 40, f"{lon}°", True, "middle", 12)
    for lat in range(lat0, lat1 + 1, 5):
        for lon in range(lon0, lon1 + 1, 5):
            dl = 40.3 * vtec(lat, lon) * 1e16 / F_L1 ** 2
            r = 6 + 3.0 * dl
            svg.circle(gx(lon), gy(lat), r, P.lavender, opacity=f"{0.25 + 0.15 * dl:.2f}")
            svg.text(gx(lon), gy(lat) + 4, f"{dl:.1f}", "code", 11, P.white, "middle")
    for lon, lat in stations:
        svg.triangle(gx(lon), gy(lat), 13, P.teal_60, -math.pi / 2)
    svg.triangle(gx(mcc[0]), gy(mcc[1]), 22, P.teal_60, -math.pi / 2)
    tag(svg, gx(mcc[0]) + 14, gy(mcc[1]) + 24, "master station", "code", 13, P.teal_60, bg=P.black)
    # one user: interpolate the four grid points around its pierce point
    ipp = (23.2, 46.4)
    c0 = (20, 45)
    svg.rect(gx(c0[0]), gy(c0[1] + 5), gx(c0[0] + 5) - gx(c0[0]), gy(c0[1]) - gy(c0[1] + 5), "none", stroke=P.white,
             stroke_width=2.5)
    svg.circle(gx(ipp[0]), gy(ipp[1]), 6, P.white)
    tx, ty = (ipp[0] - c0[0]) / 5, (ipp[1] - c0[1]) / 5
    dd = [40.3 * vtec(c0[1] + j * 5, c0[0] + i * 5) * 1e16 / F_L1 ** 2 for i, j in [(0, 0), (1, 0), (0, 1), (1, 1)]]
    val = dd[0] * (1 - tx) * (1 - ty) + dd[1] * tx * (1 - ty) + dd[2] * (1 - tx) * ty + dd[3] * tx * ty
    tag(svg, gx(ipp[0]) + 16, gy(ipp[1]) - 30, f"a user's pierce point: {val:.2f} m", "code", 14, P.white, bg=P.black)
    axis_label(svg, M, y0 - 64, "vertical delay on L1, metres · one number every 5° × 5°", True)
    axis_label(svg, M, y0 - 44, "▲ reference station (receiver at a surveyed point)", True)

    svg.frame("sbas.", "satellite-based augmentation · WAAS, EGNOS, MSAS, GAGAN", dark=True, title_fill=P.white)
    brief(svg, "a DGPS base helps only nearby, and someone has to run one everywhere",
          "a continent of stations fits an ionosphere grid; a GEO satellite sends it, free", dark=True)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
grid = fit_vertical_delay(ref_stations, every=5)    # one number per 5° x 5°
ipp  = pierce_point(rx, sat, h=350e3)               # where the ray crosses
iono = obliquity(el) * bilinear(grid, ipp)          # four corners, then slant
# + fast clock and orbit corrections, + integrity: ~1 m, and it says when not""", "py", 19, dark=True)
    return svg


def snap() -> Svg:
    """RTK float to fixed: ambiguity estimates settle, the ratio test passes, the position snaps to centimetres."""
    svg = Svg(P.white)
    rng = random.Random(4)
    lam, n_amb, T = 0.1903, 6, 40
    sig_m = 0.9
    sums = [0.0] * n_amb
    est, fixed_at, ratio_at = [], None, None
    for k in range(1, T + 1):
        for i in range(n_amb):
            sums[i] += rng.gauss(0, sig_m)
        e = [s_ / k for s_ in sums]
        est.append(e)
        if fixed_at is None:
            best = [v - round(v) for v in e]
            second = sorted(range(n_amb), key=lambda i: -abs(best[i]))[0]
            alt = [b - (math.copysign(1, b) if i == second else 0) for i, b in enumerate(best)]
            ratio = sum(a * a for a in alt) / max(sum(b * b for b in best), 1e-9)
            if ratio > 3 and k >= 4:
                fixed_at, ratio_at = k, ratio
    x0, x1 = M + 70, W - M
    gx = lambda k: x0 + (x1 - x0) * k / T  # noqa: E731
    # top: float ambiguity minus the true integer
    y0, y1 = ART_TOP + 60, 650
    ym = (y0 + y1) / 2
    gy = lambda c: ym - (y1 - y0) / 2 * c / 1.6  # noqa: E731
    for c in (-1, 0, 1):
        svg.line(x0, gy(c), x1, gy(c), P.black_20 if c else P.black_60, 1.5, stroke_dasharray="4 6" if c else None)
        axis_label(svg, x0 - 12, gy(c) + 5, f"{c:+d}" if c else "0", anchor="end")
    kend = fixed_at or T
    band = [(gx(k), gy(min(sig_m / math.sqrt(k), 1.6))) for k in range(1, kend + 1)]
    band_lo = [(gx(k), gy(-min(sig_m / math.sqrt(k), 1.6))) for k in range(kend, 0, -1)]
    svg.poly(band + band_lo, P.lavender_20)
    cols = [P.blue, P.teal, P.lavender, P.black_60, P.blue_60, P.teal_60]
    for i in range(n_amb):
        pts_ = []
        for k in range(1, T + 1):
            v = est[k - 1][i] if fixed_at is None or k < fixed_at else 0.0
            if fixed_at is not None and k == fixed_at:
                pts_.append((gx(k), gy(max(min(est[k - 1][i], 1.6), -1.6))))
            pts_.append((gx(k), gy(max(min(v, 1.6), -1.6))))
        svg.polyline(pts_, cols[i], 2.2)
    axis_label(svg, x0 - 12, y0 - 16, "float ambiguity − true integer, cycles")
    # bottom: position error, log scale
    b0, b1 = 745, 990
    lo, hi = 0.005, 2.0
    gl = lambda m: b1 - (b1 - b0) * math.log(m / lo) / math.log(hi / lo)  # noqa: E731
    for m, lab in [(0.01, "1 cm"), (0.1, "10 cm"), (1.0, "1 m")]:
        svg.line(x0, gl(m), x1, gl(m), P.black_20, 1)
        axis_label(svg, x0 - 12, gl(m) + 5, lab, anchor="end")
    pos = []
    for k in range(1, T + 1):
        if fixed_at is None or k < fixed_at:
            rms = math.sqrt(sum(v * v for v in est[k - 1]) / n_amb)
            pos.append((gx(k), gl(min(max(1.6 * lam * rms + 0.02, lo), hi))))
        else:
            pos.append((gx(k), gl(0.012 + rng.gauss(0, 0.002))))
    svg.polyline(pos, P.black, 3)
    for k in range(0, T + 1, 10):
        axis_label(svg, gx(k), b1 + 22, f"{k} s", anchor="middle")
    axis_label(svg, x0 - 12, b0 - 16, "position error")
    if fixed_at:
        xf = gx(fixed_at)
        svg.line(xf, y0 - 8, xf, b1, P.blue, 2, stroke_dasharray="5 5")
        svg.text(xf + 10, y0 + 6, f"{fixed_at} s · ratio {ratio_at:.1f} > 3: fix", "code", 16, P.blue)
        svg.text(gx(T) - 4, gl(0.012) - 14, "fixed: 1.2 cm", "code", 15, P.blue, "end")
        svg.text(gx(1) + 8, gl(0.45), "float: decimetres", "code", 15, P.black)
    axis_label(svg, x1, y1 + 30, f"simulated · {n_amb} double differences · λ = 19 cm · 1 Hz", anchor="end")

    svg.frame("snap.", "rtk · float to fixed · ambiguity resolution · ratio test")
    brief(svg, "with the whole cycles still unknown, the float answer wanders at decimetres",
          "once they sit near integers, round them all (LAMBDA): the fix snaps to cm")
    code_rule(svg)
    svg.code(M, CODE_Y, """
N_float, Q = kalman(phase_dd, code_dd)       # real numbers, σ shrinking
best, second = lambda_search(N_float, Q, k=2)     # nearest integer vectors
if dist(second) / dist(best) > 3:            # ratio test: no close runner-up
    x = x_float - Q_xN @ inv(Q_N) @ (N_float - best)    # snap: cm""", "py", 19)
    return svg


def ladder() -> Svg:
    """Every method on one chart: how close, and how long it takes to get there."""
    svg = Svg(P.cream)
    x0, x1, y0, y1 = M + 70, W - M, ART_TOP + 40, 975
    tlo, thi, alo, ahi = 0.5, 2e5, 0.001, 10.0
    gx = lambda t: x0 + (x1 - x0) * math.log(t / tlo) / math.log(thi / tlo)  # noqa: E731
    gy = lambda a: y0 + (y1 - y0) * math.log(ahi / a) / math.log(ahi / alo)  # noqa: E731
    for a, lab in [(10, "10 m"), (1, "1 m"), (0.1, "10 cm"), (0.01, "1 cm"), (0.001, "1 mm")]:
        svg.line(x0, gy(a), x1, gy(a), P.black_20, 1)
        axis_label(svg, x0 - 12, gy(a) + 5, lab, anchor="end")
    for t, lab in [(1, "1 s"), (10, "10 s"), (60, "1 min"), (600, "10 min"), (3600, "1 h"), (86400, "1 day")]:
        svg.line(gx(t), y0, gx(t), y1, P.black_20, 1)
        axis_label(svg, gx(t), y1 + 22, lab, anchor="middle")
    axis_label(svg, x1, y1 + 44, "time until it's that good", anchor="end")
    axis_label(svg, x0 - 12, y0 - 14, "horizontal, 95 %")
    rungs = [
        ("standalone L1", (1, 30), (2.5, 5), "nothing: any receiver", P.black_60),
        ("+ L5", (1, 30), (1.2, 2.5), "a dual-band chip", P.black),
        ("SBAS", (2, 90), (0.6, 1.2), "free, from a GEO satellite", P.teal),
        ("DGPS", (1, 30), (0.3, 0.6), "a base within ~100 km", P.teal_60),
        ("PPP", (900, 2400), (0.04, 0.1), "global orbit + clock corrections", P.lavender),
        ("PPP-RTK", (30, 300), (0.025, 0.07), "+ a regional atmosphere model", P.blue_60),
        ("RTK", (5, 60), (0.01, 0.025), "a base within ~20 km, carrier phase", P.blue),
        ("static survey", (7200, 86400), (0.002, 0.005), "hours on a tripod, post-processed", P.black),
    ]
    for name, (ta, tb), (aa, ab), need, col in rungs:
        rx0, rx1, ry0, ry1 = gx(ta), gx(tb), gy(ab), gy(aa)
        svg.rect(rx0, ry0, rx1 - rx0, ry1 - ry0, col, rx=8, opacity="0.85")
        right = name not in ("static survey", "PPP-RTK")
        tx = rx1 + 12 if right else rx0 - 12
        anchor = "start" if right else "end"
        svg.text(tx, (ry0 + ry1) / 2 - 2, name, "code", 16, col if col != P.black_60 else P.black, anchor)
        axis_label(svg, tx, (ry0 + ry1) / 2 + 17, need, anchor=anchor, size=12)

    svg.frame("ladder.", "gnss accuracy · standalone to survey · what each step costs")
    brief(svg, "how close do you need to be, and how long can you wait?",
          "every rung down costs something: a band, a base nearby, a subscription, or time")
    code_rule(svg)
    svg.code(M, CODE_Y, """
need = {"phone map": 5.0, "lane": 0.5, "tractor": 0.03, "survey": 0.005}  # m
ok = [m for m in methods if m.acc <= need[job] and m.ttf <= patience]
pick = min(ok, key=lambda m: m.cost)      # bands, bases, subscriptions, time
# code ranges get you metres; carrier phase gets you centimetres""", "py", 19)
    return svg


# ============================================================================
# build
# ============================================================================
FAMILIES = {
    "sky": ["constellations", "skyplot", "relativity", "wait"],
    "signal": ["bands", "code", "doppler", "iono"],
    "fix": ["intersect", "four", "geoid", "dop"],
    "error": ["errors", "multipath", "canyon", "cep"],
    "augment": ["dgps", "sbas", "snap", "ladder"],
}
OUT = Path(__file__).resolve().parents[1] / "out/gps"
RENAMED = {"skyplot": "skyplot_poster", "code": "code_poster"}  # names taken by helpers


def main(names: set[str]) -> None:
    for family, fns in FAMILIES.items():
        for name in fns:
            fn = globals().get(RENAMED.get(name, name))
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
