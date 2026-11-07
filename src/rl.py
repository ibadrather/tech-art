"""RL posters: reinforcement learning, one idea each, with a lunar lander as the running example.

Minimal like still.py and vision.py: one word, one drawing, one or two lines of code. The pictures are
computed: the value funnel is value iteration, the cliff paths are SARSA and Q-learning actually run,
the overestimation is sampled, the PPO clip is the objective plotted. The learning curve is simulated.

Setup:   agent. state. action. reward. episode. discount.
Maths:   markov. bellman. value. advantage. bootstrap.
Value:   qlearn. cliff. epsilon. dqn. replay. target. double. dueling.
Policy:  reinforce. critic. gae. clip. entropy. gauss. twin.
Map:     zoo. solved.

Run:  uv run --no-project --with fonttools --with brotli python src/rl.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg, _fmt  # noqa: E402
from drone import missing_glyphs  # noqa: E402
from posters import CODE_Y, M, W, code_rule  # noqa: E402
from sensors import arrow  # noqa: E402
from still import mix  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "rl"
CX, CY = W / 2, 640  # centre of the drawing
ACTIONS = ["nothing", "left", "main", "right"]  # LunarLander-v3's Discrete(4)
FIRE = [(), ("left",), ("main",), ("right",)]


# ============================================================================
# shared furniture
# ============================================================================
def label(svg: Svg, x, y, s, fill=P.black_60, anchor="middle", size=20, font="codel"):
    svg.text(x, y, s, font, size, fill, anchor)


def lander(svg: Svg, x, y, s, ang=0.0, fire=(), body=P.blue, ink=P.black, flame=P.lavender, window=P.white):
    """Our lander, centred on its cabin at (x, y), s px per unit, tilted by ang (radians, clockwise)."""
    c, si = math.cos(ang), math.sin(ang)

    def T(px, py):
        return (x + s * (px * c - py * si), y + s * (px * si + py * c))

    if "main" in fire:
        svg.poly([T(-0.14, 0.5), T(0.14, 0.5), T(0, 1.08)], flame)
    if "left" in fire:
        svg.poly([T(-0.5, -0.34), T(-0.5, -0.1), T(-0.98, -0.22)], flame)
    if "right" in fire:
        svg.poly([T(0.5, -0.34), T(0.5, -0.1), T(0.98, -0.22)], flame)
    lw = max(2.0, s * 0.055)
    for sx in (-1, 1):
        svg.line(*T(sx * 0.42, 0.28), *T(sx * 0.78, 0.8), ink, lw, stroke_linecap="round")
        svg.line(*T(sx * 0.92, 0.8), *T(sx * 0.64, 0.8), ink, lw, stroke_linecap="round")
    svg.poly([T(-0.6, 0.08), T(0.6, 0.08), T(0.48, 0.36), T(-0.48, 0.36)], ink)
    svg.poly([T(-0.12, 0.36), T(0.12, 0.36), T(0.19, 0.5), T(-0.19, 0.5)], ink)
    svg.poly([T(-0.32, -0.56), T(0.32, -0.56), T(0.5, -0.33), T(0.5, 0.08), T(-0.5, 0.08), T(-0.5, -0.33)], body)
    svg.circle(*T(0, -0.23), 0.14 * s, window)


def ground(svg: Svg, y, pad, ink=P.black, flag=P.teal, x0=M, x1=W - M, hills=14, width=3):
    """The moon's surface: gentle hills, a flat pad between two flags (like the gym's)."""
    a, b = pad
    pts = []
    for k in range(121):
        x = x0 + (x1 - x0) * k / 120
        if a - 30 <= x <= b + 30:
            h = 0
        else:
            d = min(abs(x - a), abs(x - b)) / 120
            h = hills * min(1, d) * (math.sin(x / 37) + 0.6 * math.sin(x / 13 + 1) + 0.9)
        pts.append((x, y - h))
    svg.polyline(pts, ink, width)
    for fx in (a, b):
        svg.line(fx, y, fx, y - 46, ink, 2)
        svg.poly([(fx, y - 46), (fx + 22, y - 39), (fx, y - 32)], flag)


def curve(svg: Svg, a, b, bend, color, width=3, head=16, dash=None):
    """A quadratic curve a → b bowed sideways by `bend` px, with an arrowhead at b."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    cx, cy = mx - dy / n * bend, my + dx / n * bend
    ang = math.atan2(b[1] - cy, b[0] - cx)
    tip = (b[0] - head * 0.45 * math.cos(ang), b[1] - head * 0.45 * math.sin(ang))
    d = f' stroke-dasharray="{dash}"' if dash else ""
    svg.add(f'<path d="M{_fmt(a[0])},{_fmt(a[1])} Q{_fmt(cx)},{_fmt(cy)} {_fmt(tip[0])},{_fmt(tip[1])}" fill="none" '
            f'stroke="{color}" stroke-width="{_fmt(width)}" stroke-linecap="round"{d}/>')
    if head:
        svg.triangle(*tip, head, color, ang)
    return (0.25 * a[0] + 0.5 * cx + 0.25 * b[0], 0.25 * a[1] + 0.5 * cy + 0.25 * b[1])  # midpoint of the curve


def toward(a, b, d):
    """The point d px from a toward b."""
    n = math.hypot(b[0] - a[0], b[1] - a[1])
    return (a[0] + (b[0] - a[0]) * d / n, a[1] + (b[1] - a[1]) * d / n)


def softmax(z):
    m = max(z)
    e = [math.exp(v - m) for v in z]
    return [v / sum(e) for v in e]


# ============================================================================
# models the posters are drawn from
# ============================================================================
GRID_C, GRID_R, PAD = 31, 12, (14, 16)  # the grid lander: 31 columns, falls one row per step
WIND, GAMMA_G = 0.2, 0.97


def grid_lander():
    """Value iteration on a tiny lander: each step it falls a row and may shift a column (−1 per shift).

    Wind pushes it one more column either way with probability WIND. Reaching the ground on the pad
    pays +100, anywhere else −100. Returns V[r][c] and Q[r][c][a] for a in (←, ·, →).
    """
    V = [[0.0] * GRID_C for _ in range(GRID_R)]
    Q = [[[0.0] * 3 for _ in range(GRID_C)] for _ in range(GRID_R)]
    for _ in range(GRID_R + 2):
        for r in range(GRID_R - 1, -1, -1):
            for c in range(GRID_C):
                for a, dc in enumerate((-1, 0, 1)):
                    q = -abs(dc)
                    for w, p in ((-1, WIND / 2), (0, 1 - WIND), (1, WIND / 2)):
                        c2 = min(GRID_C - 1, max(0, c + dc + w))
                        if r + 1 == GRID_R:
                            q += p * (100 if PAD[0] <= c2 <= PAD[1] else -100)
                        else:
                            q += p * GAMMA_G * V[r + 1][c2]
                    Q[r][c][a] = q
                V[r][c] = max(Q[r][c])
    return V, Q


def fly(seed=3):
    """A point-mass lander flown by a hand-written controller, scored with LunarLander's reward shape."""
    g, thrust, side, dt = -1.62, 3.4, 0.9, 0.05
    x, y, vx, vy = -6.5, 11.5, 1.6, 0.0
    rng = random.Random(seed)

    def shaping(x, y, vx, vy):
        return -100 * math.hypot(x, y) / 10 - 100 * math.hypot(vx, vy) / 5

    prev, steps, G = shaping(x, y, vx, vy), [], 0.0
    while y > 0:
        tvx = max(-1.5, min(1.5, -0.45 * x))
        a = 0
        if vy < -(0.18 * y + 0.35):
            a = 2
        elif tvx - vx > 0.15:
            a = 3
        elif tvx - vx < -0.15:
            a = 1
        ax = side if a == 3 else -side if a == 1 else 0.0
        ay = g + (thrust if a == 2 else 0.0)
        vx += (ax + rng.gauss(0, 0.15)) * dt
        vy += ay * dt
        x, y = x + vx * dt, max(0.0, y + vy * dt)
        sh = shaping(x, y, vx, vy)
        r = sh - prev - (0.3 if a == 2 else 0.03 if a else 0)
        prev = sh
        if y <= 0:
            r += 100 if abs(x) < 1 and math.hypot(vx, vy) < 1.2 else -100
        G += r
        steps.append((x, y, a, r))
    return steps, G


# ============================================================================
# setup
# ============================================================================
def agent() -> Svg:
    """The loop: the agent acts, the world answers with a new state and a reward."""
    svg = Svg(P.white)
    lander(svg, CX, 440, 120)
    label(svg, CX, 330, "agent", P.black, size=26, font="diag")
    ground(svg, 880, (CX - 110, CX + 110))
    label(svg, CX, 940, "environment", P.black, size=26, font="diag")
    xr, xl, top, bot = CX + 260, CX - 260, 440, 820
    svg.polyline([(CX + 150, top), (xr, top), (xr, bot - 10)], P.blue, 4)
    svg.triangle(xr, bot, 22, P.blue, math.pi / 2)
    label(svg, xr + 22, 640, "action a", P.blue, "start", 22)
    svg.polyline([(CX - 150, bot + 20), (xl, bot + 20), (xl, top + 10)], P.teal, 4)
    svg.triangle(xl, top, 22, P.teal, -math.pi / 2)
    label(svg, xl - 22, 620, "state s", P.teal, "end", 22)
    label(svg, xl - 22, 656, "reward r", P.teal, "end", 22)

    svg.frame("agent.", "act · observe · repeat")
    code_rule(svg)
    svg.code(M, CODE_Y, "s, r, terminated, truncated, info = env.step(a)", "py", 22)
    return svg


def state() -> Svg:
    """What the lander is told each step: eight numbers."""
    svg = Svg(P.cream)
    vals = [("x", 0.21), ("y", 0.86), ("vx", -0.18), ("vy", -0.42), ("angle", 0.21), ("spin", 0.05), ("leg_l", 0.0), ("leg_r", 0.0)]
    for i, (k, v) in enumerate(vals):
        yy = 360 + i * 66
        label(svg, M, yy, k, P.black_60, "start", 22)
        svg.text(M + 220, yy, f"{v:+.2f}" if k[:3] != "leg" else f"{v:.0f}", "code", 24, P.blue, "end")
    gy, pc = 900, 640
    ground(svg, gy, (pc - 80, pc + 80), x0=440)
    lx, ly, th = 840, 520, 0.21
    svg.line(pc, gy + 34, lx, gy + 34, P.black_60, 2)
    for xx in (pc, lx):
        svg.line(xx, gy + 26, xx, gy + 42, P.black_60, 2)
    label(svg, (pc + lx) / 2, gy + 66, "x", P.black_60, size=22)
    svg.line(lx + 120, ly, lx + 120, gy, P.black_60, 2, stroke_dasharray="4 8")
    label(svg, lx + 138, (ly + gy) / 2, "y", P.black_60, "start", 22)
    svg.line(lx, ly, lx, ly - 170, P.black_20, 2, stroke_dasharray="4 8")
    svg.line(lx, ly, lx + 170 * math.sin(th), ly - 170 * math.cos(th), P.black_60, 2)
    svg.arc(lx, ly, 140, -math.pi / 2, -math.pi / 2 + th, P.black, 3)
    label(svg, lx + 62, ly - 150, "angle", P.black, "start", 18)
    v = (-0.18, 0.42)
    n = math.hypot(*v)
    arrow(svg, (lx - 40, ly + 40), (lx - 40 + 150 * v[0] / n, ly + 40 + 150 * v[1] / n), P.teal, 4, 20)
    label(svg, lx - 120, ly + 150, "v", P.teal, size=22)
    lander(svg, lx, ly, 110, th)
    label(svg, M, 920, "legs down: 0 0", P.black_60, "start", 18)

    svg.frame("state.", "eight numbers · all it gets to see")
    code_rule(svg)
    svg.code(M, CODE_Y, "x, y, vx, vy, angle, spin, leg_l, leg_r = obs", "py", 22)
    return svg


def action() -> Svg:
    """Discrete(4): four buttons."""
    svg = Svg(P.white)
    for i, name in enumerate(ACTIONS):
        x = CX + (-1 if i % 2 == 0 else 1) * 220
        y = 470 + (i // 2) * 330
        lander(svg, x, y, 96, 0, FIRE[i])
        label(svg, x, y + 150, f"{i} · {name}", P.black if i else P.black_60, size=22)

    svg.frame("action.", "discrete(4) · four buttons, pick one")
    code_rule(svg)
    svg.code(M, CODE_Y, "a = env.action_space.sample()   # 0, 1, 2 or 3", "py", 22)
    return svg


def reward() -> Svg:
    """LunarLander's reward, term by term, to scale: fuel is cheap per frame, it adds up."""
    svg = Svg(P.cream)
    terms = [("come to rest", 100), ("each leg down", 10), ("closer, slower, level", 6),
             ("main engine / frame", -0.3), ("side engine / frame", -0.03), ("crash", -100)]
    zx, k, y0, dy, bh = CX + 60, 3.6, 390, 96, 40
    svg.line(zx, y0 - 50, zx, y0 + dy * (len(terms) - 1) + bh + 20, P.black, 2)
    for i, (name, v) in enumerate(terms):
        y = y0 + i * dy
        wbar = max(3, abs(v) * k)
        col = P.teal if v > 0 else P.lavender if v > -1 else P.blue
        svg.rect(zx if v > 0 else zx - wbar, y, wbar, bh, col)
        label(svg, zx - 14 if v > 0 else zx + 14, y + 27, name, P.black_60, "end" if v > 0 else "start", 18)
        txt = f"{v:+g}"
        label(svg, zx + wbar + 14 if v > 0 else zx - wbar - 14, y + 28, txt, col, "start" if v > 0 else "end", 20)
    label(svg, zx, y0 + dy * len(terms) + 40, "+200 over an episode = solved", P.black, size=20)

    svg.frame("reward.", "the only signal it gets · to scale")
    code_rule(svg)
    svg.code(M, CODE_Y, "r = shaping - prev_shaping - 0.3*main - 0.03*side", "py", 22)
    return svg


def episode() -> Svg:
    """One flight, start to touchdown, every step coloured by the sign of its reward."""
    svg = Svg(P.black)
    steps, G = fly()
    gy = 900

    def px(x, y):
        return (CX + x * 52, gy - 52 - y * 46)

    ground(svg, gy, (CX - 52, CX + 52), P.black_80, P.teal_60, hills=10)
    for i, (x, y, a, r) in enumerate(steps):
        svg.circle(*px(x, y), 3.4, P.teal_60 if r > 0 else P.lavender)
    n = len(steps)
    for j in (0, n // 4, n // 2, 3 * n // 4):
        x, y, a, _ = steps[j]
        lander(svg, *px(x, y), 44, 0, FIRE[a], P.black_80, P.black_60, P.blue_80, P.black)
    x, y, a, _ = steps[-1]
    lander(svg, *px(x, y), 44, 0, (), P.white, P.blue_40, window=P.black)
    label(svg, W - M, 380, f"G = {G:.0f}", P.white, "end", 34, "code")
    label(svg, W - M, 420, f"{n} steps", P.black_60, "end", 18)
    svg.circle(W - M - 230, 470, 6, P.teal_60)
    label(svg, W - M - 214, 476, "r > 0", P.teal_60, "start", 18)
    svg.circle(W - M - 110, 470, 6, P.lavender)
    label(svg, W - M - 94, 476, "r < 0", P.lavender, "start", 18)

    svg.frame("episode.", "reset to touchdown · rewards add up", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "G = sum(rewards)   # the return of one episode", "py", 22, dark=True)
    return svg


def discount() -> Svg:
    """γ^k for γ = 0.9 and 0.99: how much a reward k steps away counts now."""
    svg = Svg(P.white)
    n, x0, bw = 100, M, (W - 2 * M) / 100
    for row, (gam, col) in enumerate(((0.9, P.lavender), (0.99, P.blue))):
        base, hmax = 600 + row * 330, 230
        for k in range(n):
            h = hmax * gam ** k
            svg.rect(x0 + k * bw + 1, base - h, bw - 2, h, col)
        hz = 1 / (1 - gam)
        hx = x0 + min(hz, n - 0.5) * bw
        svg.line(hx, base + 12, hx, base - hmax - 20, P.black, 2, stroke_dasharray="3 6")
        label(svg, hx + (-10 if row else 12), base - hmax - 30, f"1/(1-γ) = {hz:.0f}", P.black, "end" if row else "start", 18)
        label(svg, x0, base - hmax - 30, f"γ = {gam}", col, "start", 22)
        svg.line(x0, base, W - M, base, P.black_20, 2)
    label(svg, W - M, 970, "k steps ahead →", P.black_60, "end", 18)

    svg.frame("discount.", "later is worth less · γ^k")
    code_rule(svg)
    svg.code(M, CODE_Y, "G = sum(gamma**k * r for k, r in enumerate(rewards))", "py", 22)
    return svg


# ============================================================================
# maths
# ============================================================================
def markov() -> Svg:
    """A Markov decision process: states, actions, and where each action might lead."""
    svg = Svg(P.cream)
    air, pad, crash = (CX, 420), (CX - 270, 840), (CX + 270, 840)
    fire, coast = (CX - 150, 620), (CX + 150, 620)
    R = 64
    edges = [(air, fire, 0, P.black, ""), (air, coast, 0, P.black, "")]
    for a, b, bend, col, _ in edges:
        svg.line(*toward(a, b, R), *b, col, 3)
    trans = [(fire, air, 0.7, -80), (fire, pad, 0.3, 0), (coast, pad, 0.2, 0), (coast, crash, 0.6, 0), (coast, air, 0.2, 80)]
    for a, b, p, bend in trans:
        end = toward(b, a, R + 6)
        st = toward(a, b, 10)
        mid = curve(svg, st, end, bend, P.black_60, 2.5, 16)
        dx, dy = end[0] - st[0], end[1] - st[1]
        n = math.hypot(dx, dy)
        side = math.copysign(1, bend) if bend else (1 if (mid[0] - CX) * (-dy) + (mid[1] - CY) * dx > 0 else -1)
        label(svg, mid[0] - dy / n * side * 26, mid[1] + dx / n * side * 26 + 7, f"{p}", P.blue, size=20, font="code")
    for (x, y), name in ((air, "air"), (pad, "pad"), (crash, "crash")):
        svg.circle(x, y, R, P.white, stroke=P.black, stroke_width=3)
        if name != "air":
            svg.circle(x, y, R - 9, "none", stroke=P.black, stroke_width=2)
        label(svg, x, y + 8, name, P.black, size=24, font="diag")
    for (x, y), name in ((fire, "fire"), (coast, "coast")):
        svg.circle(x, y, 10, P.black)
        label(svg, x + (-24 if x < CX else 24), y + 6, name, P.black, "end" if x < CX else "start", 20)
    label(svg, pad[0], pad[1] + 110, "+100", P.teal, size=24, font="code")
    label(svg, crash[0], crash[1] + 110, "−100", P.lavender, size=24, font="code")

    svg.frame("markov.", "states · actions · odds of what comes next")
    code_rule(svg)
    svg.code(M, CODE_Y, 'P["air"]["coast"] = [(0.2, "pad", 100), (0.6, "crash", -100), ...]', "py", 19)
    return svg


def bellman() -> Svg:
    """The backup diagram: a state's value from its actions, an action's from where it leads."""
    svg = Svg(P.white)
    root, ya, ys = (CX, 380), 580, 800
    xs = [CX - 345, CX - 115, CX + 115, CX + 345]
    best = 2
    svg.arc(CX, root[1], 90, math.radians(52), math.radians(128), P.black, 2)
    for i, x in enumerate(xs):
        col = P.blue if i == best else P.black
        svg.line(*toward(root, (x, ya), 22), x, ya, col, 4 if i == best else 2)
        for dx, p in ((-62, 0.8), (62, 0.2)):
            svg.line(x, ya, x + dx, ys - 22, col if i == best else P.black_20, 2)
            svg.circle(x + dx, ys, 20, P.white, stroke=col if i == best else P.black_60, stroke_width=3)
            label(svg, x + dx * 0.55 + (-14 if dx < 0 else 14), (ya + ys) / 2 + 6, f"{p}", P.black_60, "end" if dx < 0 else "start", 16)
        svg.circle(x, ya, 11, col)
        label(svg, x + 22, ya + 6, ACTIONS[i], col, "start", 17)
    svg.circle(*root, 22, P.white, stroke=P.blue, stroke_width=4)
    label(svg, root[0] + 40, root[1] - 30, "max over a", P.black, "start", 18)
    label(svg, M, root[1] + 7, "s", P.black, "start", 24)
    label(svg, M, ya + 7, "a", P.black, "start", 24)
    label(svg, M, ys + 7, "s'", P.black, "start", 24)
    label(svg, CX, ys + 90, "V(s) = max  Σ p · (r + γ · V(s'))", P.black, size=26)
    label(svg, CX - 70, ys + 112, "a", P.black_60, size=16)

    svg.frame("bellman.", "value now = best of reward + value next")
    code_rule(svg)
    svg.code(M, CODE_Y, """
V[s] = max(sum(p * (r + gamma * V[s2]) for p, s2, r in P[s][a])
           for a in actions)""", "py", 21)
    return svg


def value() -> Svg:
    """Value iteration on a grid lander: the funnel of places it can still land from."""
    svg = Svg(P.black)
    V, _ = grid_lander()
    cs = (W - 2 * M) / GRID_C
    oy = 400
    for r in range(GRID_R):
        for c in range(GRID_C):
            t = (V[r][c] + 100) / 200
            x, y = M + (c + 0.5) * cs, oy + (r + 0.5) * cs
            svg.circle(x, y, 1.6 + 11 * t, mix(P.black_80, P.lavender, t) if t < 0.9 else mix(P.lavender, P.white, (t - 0.9) * 10))
    gy = oy + GRID_R * cs + 8
    svg.line(M, gy, W - M, gy, P.black_80, 3)
    svg.line(M + PAD[0] * cs + 3, gy, M + (PAD[1] + 1) * cs - 3, gy, P.teal_60, 8)
    label(svg, CX, gy + 46, "pad +100 · ground −100 · each sideways step −1 · wind 20 %", P.black_60, size=17)

    svg.frame("value.", "how good is it to be here · value iteration", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
for _ in range(100):
    V = np.max(R + gamma * P @ V, axis=1)""", "py", 22, dark=True)
    return svg


def advantage() -> Svg:
    """A = Q − V: how much better each action is than the policy's average."""
    svg = Svg(P.cream)
    Q, pi = [12.0, 9.5, 18.0, 15.5], [0.1, 0.2, 0.4, 0.3]
    V = sum(p * q for p, q in zip(pi, Q))
    base, k, bw = 860, 22, 120
    xs = [CX - 330 + i * 200 for i in range(4)]
    vy = base - V * k
    for i, x in enumerate(xs):
        top = base - Q[i] * k
        svg.rect(x - bw / 2, top, bw, Q[i] * k, P.black_20)
        A = Q[i] - V
        col = P.teal if A > 0 else P.lavender
        svg.rect(x - bw / 2, min(top, vy), bw, abs(A) * k, col)
        label(svg, x, min(top, vy) - 16, f"{A:+.1f}", col, size=22, font="code")
        lander(svg, x, base + 64, 38, 0, FIRE[i])
    svg.line(M, vy, W - M, vy, P.black, 3, stroke_dasharray="10 8")
    label(svg, W - M, vy - 44, "V(s)", P.black, "end", 20)
    label(svg, W - M, vy - 16, f"{V:.1f}", P.black, "end", 20)
    svg.line(M, base, W - M, base, P.black, 2)

    svg.frame("advantage.", "better or worse than usual · A = Q − V")
    code_rule(svg)
    svg.code(M, CODE_Y, "A = Q[s, a] - V[s]", "py", 22)
    return svg


def bootstrap() -> Svg:
    """TD(0), n-step and Monte Carlo: how far you look before you trust an estimate."""
    svg = Svg(P.white)
    n, x0, dx = 9, M + 70, 92
    rows = [("TD(0)", 1, P.blue), ("3-step", 3, P.teal), ("Monte Carlo", n, P.lavender)]
    for j, (name, k, col) in enumerate(rows):
        y = 470 + j * 190
        label(svg, M, y - 50, name, col, "start", 22)
        for i in range(n + 1):
            x = x0 + i * dx
            if i == n:
                svg.rect(x - 13, y - 13, 26, 26, P.black)
            else:
                svg.circle(x, y, 12, P.black if i == 0 else P.black_20)
        for i in range(k):
            svg.circle(x0 + i * dx + dx / 2, y - 26, 5, col)
        end = x0 + k * dx
        curve(svg, (x0, y - 18), (end - (0 if k < n else 0), y - 20), -46 - 12 * k ** 0.6, col, 3, 16)
        if k < n:
            svg.circle(end, y, 15, "none", stroke=col, stroke_width=4)
            label(svg, end, y + 46, "V(s')", col, size=18)
        else:
            label(svg, end, y + 46, "end", col, size=18)
    label(svg, x0, 470 + 2 * 190 + 46, "s", P.black, size=20)
    label(svg, W - M, 980, "dots: rewards actually seen", P.black_60, "end", 17)

    svg.frame("bootstrap.", "how far to look before you guess")
    code_rule(svg)
    svg.code(M, CODE_Y, """
target = r + gamma * V[s_next]    # TD(0): guess from the next guess
target = G                        # Monte Carlo: wait for the end""", "py", 21)
    return svg


# ============================================================================
# value-based
# ============================================================================
def qlearn() -> Svg:
    """A slice of the grid lander's Q-table: one column per state, one row per action."""
    svg = Svg(P.black)
    _, Q = grid_lander()
    r, cols = 8, list(range(5, 26))
    cs = (W - 2 * M - 60) / len(cols)
    ox, oy = M + 60, 540
    qs = [Q[r][c][a] for c in cols for a in range(3)]
    lo, hi = min(qs), max(qs)
    for a, name in enumerate("← · →".split()):
        label(svg, M + 10, oy + a * cs + cs / 2 + 8, name, P.black_60, size=24)
    for j, c in enumerate(cols):
        best = max(range(3), key=lambda a: Q[r][c][a])
        for a in range(3):
            t = (Q[r][c][a] - lo) / (hi - lo)
            x, y = ox + j * cs, oy + a * cs
            svg.rect(x + 3, y + 3, cs - 6, cs - 6, mix(P.black_80, P.lavender, t), rx=4)
            if a == best:
                svg.circle(x + cs / 2, y + cs / 2, 5, P.white)
    j = cols.index(10)
    svg.rect(ox + j * cs, oy + 2 * cs, cs, cs, "none", stroke=P.white, stroke_width=3, rx=6)
    label(svg, ox + j * cs + cs / 2, oy + 3 * cs + 46, "updating Q(s, →)", P.white, size=18)
    label(svg, ox, oy - 30, "far left", P.black_60, "start", 17)
    label(svg, W - M, oy - 30, "far right", P.black_60, "end", 17)
    pc = [cols.index(c) for c in range(PAD[0], PAD[1] + 1)]
    svg.line(ox + pc[0] * cs + 4, oy + 3 * cs + 12, ox + (pc[-1] + 1) * cs - 4, oy + 3 * cs + 12, P.teal_60, 5)
    label(svg, CX, 870, "white dot: greedy action · near the pad, steer in · too far, save the fuel", P.black_60, size=17)

    svg.frame("qlearn.", "q-learning · a table of how good each move is", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "Q[s, a] += alpha * (r + gamma * Q[s2].max() - Q[s, a])", "py", 21, dark=True)
    return svg


def cliff_run(sarsa: bool, seed=1, episodes=600, eps=0.1, alpha=0.5):
    """Cliff walking (4 × 12, Sutton & Barto 6.6) learned by SARSA or Q-learning; returns the greedy path."""
    rows, cols = 4, 12
    start, goal = (3, 0), (3, 11)
    moves = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    Q = {(r, c): [0.0] * 4 for r in range(rows) for c in range(cols)}
    rng = random.Random(seed)

    def step(s, a):
        r, c = s[0] + moves[a][0], s[1] + moves[a][1]
        r, c = min(rows - 1, max(0, r)), min(cols - 1, max(0, c))
        if r == 3 and 0 < c < 11:
            return start, -100
        return (r, c), -1

    def pick(s):
        if rng.random() < eps:
            return rng.randrange(4)
        m = max(Q[s])
        return rng.choice([a for a in range(4) if Q[s][a] == m])

    for _ in range(episodes):
        s, a = start, pick(start)
        while s != goal:
            s2, r = step(s, a)
            a2 = pick(s2)
            nxt = Q[s2][a2] if sarsa else max(Q[s2])
            Q[s][a] += alpha * (r + (0 if s2 == goal else nxt) - Q[s][a])
            s, a = s2, a2
    path, s = [start], start
    while s != goal and len(path) < 60:
        s, _ = step(s, max(range(4), key=lambda a: Q[s][a]))
        path.append(s)
    return path


def cliff() -> Svg:
    """SARSA and Q-learning on the cliff: the same task, two different routes."""
    svg = Svg(P.cream)
    cs = (W - 2 * M) / 12
    oy = 470

    def c2p(rc, off=0.0):
        return (M + (rc[1] + 0.5) * cs, oy + (rc[0] + 0.5) * cs + off)

    for r in range(4):
        for c in range(12):
            if r == 3 and 0 < c < 11:
                svg.rect(M + c * cs + 2, oy + r * cs + 2, cs - 4, cs - 4, P.black)
            else:
                svg.circle(*c2p((r, c)), 3, P.black_20)
    for path, col, name in ((cliff_run(False), P.blue, "q-learning: along the edge"), (cliff_run(True), P.teal, "sarsa: the safe way round")):
        svg.polyline([c2p(p) for p in path], col, 6)
        ly = c2p(path[len(path) // 2])[1]
        label(svg, CX, ly - 18, name, col, size=20)
    for rc, t in (((3, 0), "S"), ((3, 11), "G")):
        svg.circle(*c2p(rc), 24, P.white, stroke=P.black, stroke_width=3)
        label(svg, *c2p(rc, 8), t, P.black, size=22, font="diag")
    label(svg, CX, oy + 4 * cs + 34, "the cliff · −100", P.black, size=18)
    label(svg, CX, oy + 4 * cs + 110, "ε = 0.1 while learning · q-learning learns the best path, sarsa the one it survives", P.black_60, size=16)

    svg.frame("cliff.", "on-policy vs off-policy")
    code_rule(svg)
    svg.code(M, CODE_Y, """
Q[s, a] += alpha * (r + gamma * Q[s2, a2]    - Q[s, a])   # sarsa
Q[s, a] += alpha * (r + gamma * Q[s2].max()  - Q[s, a])   # q-learning""", "py", 19)
    return svg


def epsilon() -> Svg:
    """ε-greedy: explore at random early, exploit later; every tick is one real draw."""
    svg = Svg(P.white)
    T, x0, x1, top, base = 160, M, W - M, 400, 740
    rng = random.Random(4)

    def eps(t):
        return max(0.05, 1 - 0.95 * t / (0.6 * T))

    pts = [(x0 + (x1 - x0) * t / T, base - (base - top) * eps(t)) for t in range(T + 1)]
    svg.line(x0, base, x1, base, P.black_20, 2)
    svg.polyline(pts, P.black, 4)
    label(svg, x0, top - 20, "ε = 1.0", P.black, "start", 20)
    label(svg, x1, base - (base - top) * 0.05 - 20, "ε = 0.05", P.black, "end", 20)
    tw = (x1 - x0) / T
    for t in range(T):
        rand = rng.random() < eps(t)
        svg.rect(x0 + t * tw + 1, 800, tw - 2, 120, P.lavender if rand else P.blue)
    label(svg, x0, 960, "random", P.lavender, "start", 18)
    label(svg, x1, 960, "greedy", P.blue, "end", 18)

    svg.frame("epsilon.", "ε-greedy · explore early, exploit late")
    code_rule(svg)
    svg.code(M, CODE_Y, "a = env.action_space.sample() if random() < eps else Q[s].argmax()", "py", 19)
    return svg


def dqn() -> Svg:
    """A deep Q-network: the lander's eight numbers in, one Q-value per button out."""
    svg = Svg(P.black)
    rng = random.Random(11)
    sizes, shown = [8, 64, 64, 4], [8, 9, 9, 4]
    xs = [M + 150, CX - 110, CX + 110, W - M - 210]
    s = [0.21, 0.86, -0.18, -0.42, 0.21, 0.05, 0.0, 0.0]
    acts = [s]
    for li in range(3):  # a real forward pass through random weights
        Wm = [[rng.gauss(0, 1 / math.sqrt(sizes[li])) for _ in range(sizes[li])] for _ in range(sizes[li + 1])]
        z = [sum(w * a for w, a in zip(row, acts[-1])) + 0.1 for row in Wm]
        acts.append([max(0.0, v) for v in z] if li < 2 else [10 * v + 12 for v in z])
    q = acts[-1]
    best = max(range(4), key=lambda i: q[i])

    def ys(k):
        gap = 62 if k > 4 else 96
        return [CY - gap * (k - 1) / 2 + gap * i for i in range(k)]

    for li in range(3):
        for ya in ys(shown[li]):
            for yb in ys(shown[li + 1]):
                svg.line(xs[li], ya, xs[li + 1], yb, P.black_80, 1, opacity=f"{rng.uniform(0.25, 1):.2f}")
    for li, k in enumerate(shown):
        for i, y in enumerate(ys(k)):
            hot = li == 3 and i == best
            svg.circle(xs[li], y, 11 if li in (0, 3) else 8, P.blue if hot else P.white if li in (0, 3) else P.black_60)
        if li in (1, 2):
            label(svg, xs[li], ys(k)[0] - 36, str(sizes[li]), P.black_60, size=18)
    for i, y in enumerate(ys(8)):
        label(svg, xs[0] - 28, y + 7, ["x", "y", "vx", "vy", "angle", "spin", "leg_l", "leg_r"][i], P.blue_40, "end", 18)
    for i, y in enumerate(ys(4)):
        col = P.lavender if i == best else P.black_60
        label(svg, xs[3] + 28, y + 7, f"{q[i]:5.1f}", col, "start", 20, "code")
        label(svg, xs[3] + 110, y + 7, ACTIONS[i], col, "start", 18)
    label(svg, xs[3] + 28, ys(4)[0] - 50, "Q(s, a)", P.white, "start", 20)

    svg.frame("dqn.", "deep q-network · 8 in, 4 out, take the biggest", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
q = net(s)          # one number per action
a = q.argmax()""", "py", 22, dark=True)
    return svg


def replay() -> Svg:
    """The replay buffer: a ring of past transitions, sampled at random so they don't come in order."""
    svg = Svg(P.cream)
    N, head, R = 48, 31, 250
    cx, cy = CX - 110, CY
    rng = random.Random(8)
    batch = set(rng.sample([i for i in range(N) if i != head], 8))
    for i in range(N):
        a = -math.pi / 2 + 2 * math.pi * i / N
        age = (head - i) % N / N
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        col = P.teal if i in batch else mix(P.black, P.black_20, age)
        svg.add(f'<g transform="translate({_fmt(x)} {_fmt(y)}) rotate({_fmt(math.degrees(a))})">'
                f'<rect x="-15" y="-11" width="30" height="22" rx="4" fill="{col}"/></g>')
    ah = -math.pi / 2 + 2 * math.pi * head / N
    svg.triangle(cx + (R - 46) * math.cos(ah), cy + (R - 46) * math.sin(ah), 26, P.blue, ah)
    label(svg, cx + (R - 90) * math.cos(ah), cy + (R - 90) * math.sin(ah) + 6, "write", P.blue, size=18)
    bx = W - M - 60
    for j, i in enumerate(sorted(batch)):
        a = -math.pi / 2 + 2 * math.pi * i / N
        y = CY - 7 * 34 / 2 + j * 34
        svg.line(cx + (R + 18) * math.cos(a), cy + (R + 18) * math.sin(a), bx - 22, y, P.teal_60, 1.5)
        svg.rect(bx - 15, y - 11, 30, 22, P.teal, rx=4)
    label(svg, bx, CY - 160, "batch", P.teal, size=20)
    label(svg, cx, cy - 8, "(s, a, r, s', done)", P.black_60, size=17)
    label(svg, cx, cy + 22, "dark = recent", P.black_60, size=15)

    svg.frame("replay.", "replay buffer · learn from the past, shuffled")
    code_rule(svg)
    svg.code(M, CODE_Y, """
buffer.append((s, a, r, s2, done))
batch = random.sample(buffer, 64)""", "py", 22)
    return svg


def target() -> Svg:
    """The target network: a frozen copy the online net chases, refreshed every C steps."""
    svg = Svg(P.white)
    T, C, x0, x1 = 400, 80, M, W - M
    rng = random.Random(2)
    w, ws = 0.0, []
    for t in range(T):
        w += 0.012 + rng.gauss(0, 0.05)
        ws.append(w + 0.35 * math.sin(t / 9))
    lo, hi = min(ws), max(ws)

    def P_(t, v):
        return (x0 + (x1 - x0) * t / (T - 1), 900 - (v - lo) / (hi - lo) * 480)

    svg.polyline([P_(t, v) for t, v in enumerate(ws)], P.blue, 3)
    tgt = []
    for t in range(T):
        tv = ws[(t // C) * C]
        tgt.append(P_(t, tv))
    for k in range(0, T, C):
        seg = tgt[k:k + C]
        svg.polyline(seg, P.teal, 6)
        if k:
            svg.line(*tgt[k - 1], *tgt[k], P.teal, 2, stroke_dasharray="3 6")
            svg.circle(*tgt[k], 7, P.teal)
    top = min(P_(t, v)[1] for t, v in enumerate(ws) if P_(t, v)[0] > x1 - 120)  # clear the peak under the label
    label(svg, x1, top - 16, "online θ", P.blue, "end", 20)
    label(svg, tgt[2 * C][0] + 14, tgt[2 * C][1] + 34, "target θ⁻", P.teal, "start", 20)  # under a step, clear of θ
    label(svg, (P_(C, 0)[0] + P_(2 * C, 0)[0]) / 2, 960, f"C = {C} steps", P.black_60, size=18)

    svg.frame("target.", "target network · something still to aim at")
    code_rule(svg)
    svg.code(M, CODE_Y, """
if step % C == 0:
    target.load_state_dict(online.state_dict())""", "py", 22)
    return svg


def double() -> Svg:
    """The max of noisy estimates is biased up; double Q-learning picks with one and rates with the other."""
    svg = Svg(P.black)
    rng = random.Random(5)
    ns, trials = list(range(1, 17)), 3000
    single, dbl = [], []
    for n in ns:
        s = d = 0.0
        for _ in range(trials):
            A = [rng.gauss(0, 1) for _ in range(n)]
            B = [rng.gauss(0, 1) for _ in range(n)]
            i = max(range(n), key=lambda k: A[k])
            s += A[i]
            d += B[i]
        single.append(s / trials)
        dbl.append(d / trials)
    x0, x1, y0, ky = M + 40, W - M, 820, 240

    def px(n, v):
        return (x0 + (x1 - x0) * (n - 1) / 15, y0 - v * ky)

    svg.line(x0, y0, x1, y0, P.black_80, 2, stroke_dasharray="6 8")
    label(svg, x1, y0 + 34, "true value: 0", P.black_60, "end", 18)
    for vals, col in ((single, P.lavender), (dbl, P.teal_60)):
        svg.polyline([px(n, v) for n, v in zip(ns, vals)], col, 4)
        for n, v in zip(ns, vals):
            svg.circle(*px(n, v), 5, col)
    label(svg, px(16, single[-1])[0], px(16, single[-1])[1] - 24, f"max Q   +{single[-1]:.2f}", P.lavender, "end", 20)
    label(svg, px(16, dbl[-1])[0], px(16, dbl[-1])[1] - 24, f"double   {dbl[-1]:+.2f}", P.teal_60, "end", 20)
    label(svg, x0, y0 + 76, "1 action", P.black_60, "start", 17)
    label(svg, x1, y0 + 76, "16 actions · each estimate = truth + N(0, 1)", P.black_60, "end", 17)

    svg.frame("double.", "double dqn · the max of noisy guesses is too high", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "y = r + gamma * Q_target(s2)[Q_online(s2).argmax()]", "py", 22, dark=True)
    return svg


def dueling() -> Svg:
    """Dueling heads: one number for the state, four for the actions, put back together."""
    svg = Svg(P.cream)
    v, adv = 14.9, [-2.9, -5.4, 3.1, 0.6]
    m = sum(adv) / 4
    q = [v + a - m for a in adv]
    xin, xh, xs, xq = M + 60, M + 250, CX + 80, W - M - 190
    yin = [CY - 150 + 50 * i for i in range(7)]
    yh = [CY - 100 + 50 * i for i in range(5)]
    yv, ya = [CY - 210], [CY + 70 + 60 * i for i in range(4)]
    yq = [CY - 90 + 60 * i for i in range(4)]
    for a in yin:
        for b in yh:
            svg.line(xin, a, xh, b, P.black_20, 1)
    for a in yh:
        for b in yv + ya:
            svg.line(xh, a, xs, b, P.black_20, 1)
    for b in ya:
        for c in yq:
            svg.line(xs, b, xq, c, P.lavender, 1.5, opacity="0.5")
    for c in yq:
        svg.line(xs, yv[0], xq, c, P.teal, 1.5, opacity="0.6")
    for y in yin:
        svg.circle(xin, y, 8, P.black)
    for y in yh:
        svg.circle(xh, y, 8, P.black_60)
    svg.circle(xs, yv[0], 13, P.teal)
    label(svg, xs, yv[0] - 30, f"V = {v}", P.teal, size=20, font="code")
    for i, y in enumerate(ya):
        svg.circle(xs, y, 11, P.lavender)
        label(svg, xs - 24, y + 6, f"{adv[i]:+.1f}", P.lavender, "end", 18, "code")
    label(svg, xs, ya[-1] + 50, "A(s, a)", P.lavender, size=18)
    for i, y in enumerate(yq):
        svg.circle(xq, y, 13, P.blue)
        label(svg, xq + 28, y + 7, f"{q[i]:.1f}", P.blue, "start", 20, "code")
        label(svg, xq + 100, y + 7, ACTIONS[i], P.black_60, "start", 17)
    label(svg, xq, yq[0] - 36, "Q", P.blue, size=22)

    svg.frame("dueling.", "dueling dqn · how good is here, and each move on top")
    code_rule(svg)
    svg.code(M, CODE_Y, "q = v + a - a.mean()", "py", 22)
    return svg


# ============================================================================
# policy-based
# ============================================================================
def reinforce() -> Svg:
    """REINFORCE: after a good episode, the actions it took get more likely."""
    svg = Svg(P.white)
    z = [0.2, 0.0, 0.5, 0.1]
    before = softmax(z)
    taken, G, lr = [2, 2, 3, 2, 0, 2, 3, 2], 1.0, 0.25  # the actions of an episode that paid off
    for a in taken:  # ∇ log softmax = onehot − π
        pi = softmax(z)
        z = [zi + lr * G * ((1 if i == a else 0) - pi[i]) for i, zi in enumerate(z)]
    after = softmax(z)
    base, k, bw = 820, 900, 110
    xs = [CX - 330 + i * 220 for i in range(4)]
    for i, x in enumerate(xs):
        svg.rect(x - bw / 2, base - after[i] * k, bw, after[i] * k, P.blue if after[i] > before[i] else P.blue_40)
        svg.rect(x - bw / 2 + 1.5, base - before[i] * k, bw - 3, before[i] * k, "none", stroke=P.black, stroke_width=3, stroke_dasharray="8 6")
        label(svg, x, base - max(before[i], after[i]) * k - 18, f"{before[i]:.2f} → {after[i]:.2f}", P.black, size=18)
        lander(svg, x, base + 60, 36, 0, FIRE[i])
    svg.line(M, base, W - M, base, P.black, 2)
    label(svg, M, 380, "dashed: π before · filled: after one good episode", P.black_60, "start", 17)

    svg.frame("reinforce.", "policy gradient · do more of what paid off")
    code_rule(svg)
    svg.code(M, CODE_Y, """
loss = -(log_probs * returns).sum()
loss.backward(); opt.step()""", "py", 22)
    return svg


def critic() -> Svg:
    """Actor–critic: the actor picks, the critic judges, one TD error teaches both."""
    svg = Svg(P.black)
    actor, crit, env = (CX - 230, 450), (CX + 230, 450), (CX, 790)
    R = 92
    for (x, y), name, sub, col in ((actor, "actor", "π(a|s)", P.lavender), (crit, "critic", "V(s)", P.teal_60)):
        svg.circle(x, y, R, "none", stroke=col, stroke_width=4)
        label(svg, x, y - 4, name, col, size=26, font="diag")
        label(svg, x, y + 28, sub, P.black_60, size=18)
    lander(svg, env[0], env[1] - 30, 70, 0, ("main",), P.white, P.blue_40, P.lavender, P.black)
    svg.line(env[0] - 120, env[1] + 50, env[0] + 120, env[1] + 50, P.black_80, 3)
    m1 = curve(svg, toward(actor, env, R + 6), (env[0] - 90, env[1] - 30), -40, P.lavender, 3, 18)
    label(svg, m1[0] - 26, m1[1] + 4, "a", P.lavender, "end", 22)
    m2 = curve(svg, (env[0] + 90, env[1] - 30), toward(crit, env, R + 6), -40, P.teal_60, 3, 18)
    label(svg, m2[0] + 26, m2[1] + 4, "s, r", P.teal_60, "start", 22)
    curve(svg, (crit[0] - R - 6, crit[1]), (actor[0] + R + 6, actor[1]), 0, P.white, 4, 20)
    label(svg, CX, actor[1] - 22, "δ", P.white, size=30, font="code")

    svg.frame("critic.", "actor-critic · one acts, one judges", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
delta = r + gamma * V(s2) - V(s)
actor_loss = -log_prob * delta;  critic_loss = delta ** 2""", "py", 21, dark=True)
    return svg


def gae() -> Svg:
    """GAE: the weight on the TD error k steps ahead is (γλ)^k."""
    svg = Svg(P.cream)
    n, gam = 60, 0.99
    bw = (W - 2 * M) / n
    rows = [(0.0, P.blue, "λ = 0 · one-step TD, low variance, biased"), (0.95, P.teal, "λ = 0.95 · the usual"), (1.0, P.lavender, "λ = 1 · Monte Carlo, unbiased, noisy")]
    for j, (lam, col, name) in enumerate(rows):
        base, hm = 520 + j * 200, 120
        label(svg, M, base - hm - 22, name, col, "start", 19)
        for k in range(n):
            h = hm * (gam * lam) ** k
            if h > 0.4:
                svg.rect(M + k * bw + 1, base - h, bw - 2, h, col)
        svg.line(M, base, W - M, base, P.black_20, 2)
    label(svg, W - M, 980, "weight on δ k steps ahead →", P.black_60, "end", 17)

    svg.frame("gae.", "generalised advantage estimation · (γλ)^k")
    code_rule(svg)
    svg.code(M, CODE_Y, "adv = delta + gamma * lam * (1 - done) * adv    # backwards in time", "py", 20)
    return svg


def clip() -> Svg:
    """PPO's clipped objective: no reward for pushing the ratio past 1 ± ε."""
    svg = Svg(P.white)
    eps = 0.2
    pw, ph, gap = 400, 380, 112
    for j, A in enumerate((1.0, -1.0)):
        ox, oy = M + j * (pw + gap), 470

        def px(r, L):
            yv = (L + 0.1) / 1.4 if A > 0 else (L + 2.1) / 2.2
            return (ox + r / 2 * pw, oy + ph - yv * ph)

        rs = [2 * i / 200 for i in range(201)]
        svg.line(*px(0, 0), *px(2, 0), P.black_20, 2)
        svg.polyline([px(r, r * A) for r in rs], P.black_20, 3, stroke_dasharray="8 8")
        Ls = [min(r * A, max(1 - eps, min(1 + eps, r)) * A) for r in rs]
        svg.polyline([px(r, L) for r, L in zip(rs, Ls)], P.blue, 6)
        for rv in (1 - eps, 1 + eps):
            svg.line(px(rv, 0)[0], oy - 10, px(rv, 0)[0], oy + ph + 10, P.black_20, 2, stroke_dasharray="3 6")
            label(svg, px(rv, 0)[0], oy + ph + 42, f"{rv:g}", P.black_60, size=17)
        svg.circle(*px(1, A), 9, P.teal)
        label(svg, ox, oy - 30, "A > 0 · good action" if A > 0 else "A < 0 · bad action", P.black, "start", 21)
        label(svg, ox + pw, oy + ph + 76, "ratio π_new / π_old", P.black_60, "end", 16)

    svg.frame("clip.", "ppo · small steps, no cliff dives")
    code_rule(svg)
    svg.code(M, CODE_Y, "L = min(ratio * A, clip(ratio, 1 - eps, 1 + eps) * A)", "py", 22)
    return svg


def entropy() -> Svg:
    """Entropy of the policy: from 'anything goes' to 'always main engine'."""
    svg = Svg(P.black)
    dists = [[0.25] * 4, [0.4, 0.3, 0.2, 0.1], [0.07, 0.08, 0.75, 0.1], [0.01, 0.01, 0.97, 0.01]]
    gw, bw, base, k = 912 / 4, 34, 800, 380
    for j, d in enumerate(dists):
        cx = M + gw * (j + 0.5)
        H = -sum(p * math.log(p) for p in d)
        for i, p in enumerate(d):
            x = cx + (i - 1.5) * (bw + 10)
            svg.rect(x - bw / 2, base - p * k, bw, p * k, P.lavender if p == max(d) and j else P.blue_40)
        label(svg, cx, base + 50, f"H = {H:.2f}", P.white, size=22, font="code")
    svg.line(M, base, W - M, base, P.black_80, 2)
    label(svg, M, base + 110, "← explores", P.black_60, "start", 18)
    label(svg, W - M, base + 110, "commits →", P.black_60, "end", 18)
    label(svg, M, 380, "four actions · max H = log 4 = 1.39", P.black_60, "start", 18)

    svg.frame("entropy.", "a bonus for keeping options open", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "loss = policy_loss - 0.01 * entropy", "py", 22, dark=True)
    return svg


def gauss() -> Svg:
    """Continuous lander: a Gaussian over two throttles, squashed into the box by tanh."""
    svg = Svg(P.cream)
    S, ox, oy = 560, CX - 280, 400
    rng = random.Random(9)
    mu, sd = (-0.25, 0.75), (0.55, 0.45)

    def px(lat, main):
        return (ox + (lat + 1) / 2 * S, oy + (1 - main) / 2 * S)

    svg.rect(*px(-1, 1), S, S / 2, P.teal_20)
    svg.rect(*px(-1, 1), S * 0.25, S, P.lavender_20, opacity="0.8")
    svg.rect(*px(0.5, 1), S * 0.25, S, P.lavender_20, opacity="0.8")
    svg.rect(ox, oy, S, S, "none", stroke=P.black, stroke_width=3)
    svg.line(*px(-1, 0), *px(1, 0), P.black_20, 2)
    svg.line(*px(0, -1), *px(0, 1), P.black_20, 2)
    for _ in range(500):
        a = (math.tanh(mu[0] + sd[0] * rng.gauss(0, 1)), math.tanh(mu[1] + sd[1] * rng.gauss(0, 1)))
        svg.circle(*px(*a), 3.2, P.blue, opacity="0.55")
    svg.triangle(*px(math.tanh(mu[0]), math.tanh(mu[1])), 26, P.black, -math.pi / 2)
    label(svg, ox + S / 2, oy - 18, "main > 0: main engine on", P.teal, size=17)
    label(svg, ox + S / 2, oy + S + 40, "lateral →", P.black_60, size=18)
    label(svg, ox - 18, oy + S / 2, "main ↑", P.black_60, "end", 18)
    label(svg, ox + S + 18, oy + 30, "|lateral| > 0.5:", P.lavender, "start", 16)
    label(svg, ox + S + 18, oy + 54, "side engine on", P.lavender, "start", 16)

    svg.frame("gauss.", "continuous actions · two throttles, one bell curve")
    code_rule(svg)
    svg.code(M, CODE_Y, "a = torch.tanh(mu + std * torch.randn(2))   # main, lateral", "py", 21)
    return svg


def twin() -> Svg:
    """TD3 / SAC: two critics, trust the lower one, so errors don't get chased upward."""
    svg = Svg(P.white)
    rng = random.Random(6)
    x0, x1, base, ky = M, W - M, 760, 210

    def bumps():
        ph = [(rng.uniform(2, 7), rng.uniform(0, 6), rng.uniform(0.15, 0.35)) for _ in range(3)]
        return lambda a: sum(amp * math.sin(f * a + p) for f, p, amp in ph)

    true = lambda a: 1.0 - 1.2 * (a - 0.1) ** 2  # noqa: E731
    e1, e2 = bumps(), bumps()
    As = [-1 + 2 * i / 200 for i in range(201)]

    def px(a, q):
        return (x0 + (a + 1) / 2 * (x1 - x0), base - q * ky)

    svg.polyline([px(a, true(a)) for a in As], P.black_20, 3, stroke_dasharray="8 8")
    q1 = [true(a) + e1(a) for a in As]
    q2 = [true(a) + e2(a) for a in As]
    qm = [min(u, v) for u, v in zip(q1, q2)]
    svg.polyline([px(a, q) for a, q in zip(As, q1)], P.lavender, 2.5)
    svg.polyline([px(a, q) for a, q in zip(As, q2)], P.teal, 2.5)
    svg.polyline([px(a, q) for a, q in zip(As, qm)], P.blue, 6)
    for qs, col in ((q1, P.lavender), (q2, P.teal), (qm, P.blue)):
        i = max(range(len(As)), key=lambda k: qs[k])
        svg.circle(*px(As[i], qs[i]), 9, col)
    hi1 = q1[-1] > q2[-1]  # the upper end gets its label above, the lower one below: the min line runs between
    label(svg, x1, px(1, q1[-1])[1] + (-16 if hi1 else 30), "Q1", P.lavender, "end", 20)
    label(svg, x1, px(1, q2[-1])[1] + (30 if hi1 else -16), "Q2", P.teal, "end", 20)
    label(svg, x0, 400, "dashed: the true Q · bold: min(Q1, Q2)", P.black_60, "start", 17)
    label(svg, CX, base + 190, "action →", P.black_60, size=18)

    svg.frame("twin.", "td3 · sac · two critics, believe the lower")
    code_rule(svg)
    svg.code(M, CODE_Y, "y = r + gamma * torch.min(Q1(s2, a2), Q2(s2, a2))", "py", 22)
    return svg


# ============================================================================
# map
# ============================================================================
def zoo() -> Svg:
    """The family tree, after Spinning Up's taxonomy; the ones used on the lander in blue."""
    svg = Svg(P.white)
    cols = [("q-learning", ["Q-learning", "SARSA", "DQN", "Double DQN", "Dueling", "Rainbow"]),
            ("policy", ["REINFORCE", "A2C · A3C", "TRPO", "PPO"]),
            ("both", ["DDPG", "TD3", "SAC"]),
            ("model-based", ["Dyna-Q", "AlphaZero", "MuZero", "Dreamer"])]
    used = {"DQN", "PPO", "SAC"}
    cw = (W - 2 * M) / 4
    root, mf = (CX, 340), (M + 1.5 * cw, 430)
    svg.circle(*root, 10, P.black)
    label(svg, root[0] + 20, root[1] + 6, "RL", P.black, "start", 22, "diag")
    svg.line(*root, *mf, P.black_20, 2)
    svg.circle(*mf, 7, P.black)
    label(svg, mf[0] - 16, mf[1] - 8, "model-free", P.black_60, "end", 17)
    for j, (head, items) in enumerate(cols):
        hx = M + (j + 0.5) * cw
        hy = 530
        svg.line(*(mf if j < 3 else root), hx, hy - 14, P.black_20, 2)
        svg.circle(hx, hy, 7, P.black)
        label(svg, hx, hy + 40, head, P.black, size=20)
        for i, it in enumerate(items):
            y = hy + 100 + i * 54
            label(svg, hx, y, it, P.blue if it in used else P.black, size=23, font="diag")

    svg.frame("zoo.", "the family tree · blue ones fly the lander")
    code_rule(svg)
    svg.code(M, CODE_Y, "from stable_baselines3 import A2C, DDPG, DQN, PPO, SAC, TD3", "py", 21)
    return svg


def solved() -> Svg:
    """A learning curve (simulated): returns per episode, a rolling mean, the line at 200."""
    svg = Svg(P.black)
    rng = random.Random(12)
    N, x0, x1, top, base = 900, M + 50, W - M, 380, 920
    rets = []
    for e in range(N):
        mean = -190 + 450 / (1 + math.exp(-(e - 330) / 85))
        sd = 70 * (1 - 0.55 * e / N)
        r = rng.gauss(mean, sd)
        if rng.random() < 0.06 * (1 - e / N) + 0.02:
            r = rng.uniform(-260, -80)  # a crash
        rets.append(max(-300, min(320, r)))
    roll = [sum(rets[max(0, e - 49):e + 1]) / len(rets[max(0, e - 49):e + 1]) for e in range(N)]
    hit = next(e for e in range(N) if roll[e] >= 200 and e > 50)

    def px(e, v):
        return (x0 + (x1 - x0) * e / (N - 1), base - (v + 300) / 620 * (base - top))

    for e, r in enumerate(rets):
        svg.circle(*px(e, r), 2.2, P.black_80)
    svg.line(*px(0, 200), *px(N - 1, 200), P.teal_60, 2, stroke_dasharray="8 8")
    svg.line(*px(0, 0), *px(N - 1, 0), P.black_80, 1.5)
    svg.polyline([px(e, v) for e, v in enumerate(roll)], P.lavender, 4)
    svg.circle(*px(hit, roll[hit]), 9, P.white)
    label(svg, px(hit, 0)[0] - 16, px(0, 200)[1] - 18, f"solved at episode {hit}", P.white, "end", 19)
    label(svg, x0 - 12, px(0, 200)[1] + 6, "200", P.teal_60, "end", 17)
    label(svg, x0 - 12, px(0, 0)[1] + 6, "0", P.black_60, "end", 17)
    label(svg, x0 - 12, px(0, -200)[1] + 6, "−200", P.black_60, "end", 17)
    label(svg, x1, base + 40, "episodes →  (simulated)", P.black_60, "end", 17)

    svg.frame("solved.", "lunar lander · mean return over 200", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, 'model = PPO("MlpPolicy", "LunarLander-v3").learn(1_000_000)', "py", 21, dark=True)
    return svg


FAMILIES = {
    "setup": ["agent", "state", "action", "reward", "episode", "discount"],
    "maths": ["markov", "bellman", "value", "advantage", "bootstrap"],
    "value": ["qlearn", "cliff", "epsilon", "dqn", "replay", "target", "double", "dueling"],
    "policy": ["reinforce", "critic", "gae", "clip", "entropy", "gauss", "twin"],
    "map": ["zoo", "solved"],
}


def main(names: set[str]) -> None:
    for family, fns in FAMILIES.items():
        for name in fns:
            if names and name not in names:
                continue
            svg = globals()[name]()
            out = OUT / family / f"{name}.svg"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(svg.render())
            bad = missing_glyphs(svg)
            print(out.relative_to(OUT.parents[1]), f"{out.stat().st_size // 1024} KB", "MISSING " + " ".join(bad) if bad else "")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
