"""Minimal posters: one word, one drawing, one line of code. Lots of empty paper.

The quiet siblings of the core set: every poster keeps to two or three brand colours and a single
idea from the first week of building a robot. hello. opens the set and bye. closes it.

hello. boot. blink. zero. loop. step. grip. stop.
charge. go. rotate. think. debug. commit. rest. bye.

Run:  uv run --no-project --with fonttools --with brotli python src/minimal.py [name ...]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from posters import CODE_Y, M, W, H, code_rule  # noqa: E402
from sensors import arrow  # noqa: E402

CX, CY = W / 2, 640  # centre of the drawing


def bezier(p0, p1, p2, p3, n=80):
    return [
        (
            (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t**3 * p3[0],
            (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t**3 * p3[1],
        )
        for t in (k / n for k in range(n + 1))
    ]


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


def boot() -> Svg:
    """Power on: one command, three checks, a cursor."""
    svg = Svg(P.black)
    svg.code(M, 560, "$ robot --boot", "py", 44, dark=True)
    for i, part in enumerate(["motors", "sensors", "brain"]):
        y = 664 + i * 50
        svg.text(M, y, "[ ok ]", "code", 22, P.teal_60)
        svg.text(M + 104, y, part, "codel", 22, P.black_20)
    svg.rect(M, 664 + 3 * 50 - 21, 13, 27, P.teal)
    svg.frame("boot.", "power on · one line at a time", dark=True, title_fill=P.white)
    return svg


def blink() -> Svg:
    """The hello world of hardware: one LED and the square wave that drives it."""
    svg = Svg(P.cream)
    svg.circle(CX, 540, 150, P.lavender_20)
    svg.circle(CX, 540, 62, P.blue)

    x0, x1, hi, lo = M + 40, W - M - 40, 790, 870
    n = 4
    p = (x1 - x0) / n
    wave = [(x0, lo)]
    for k in range(n):
        a = x0 + k * p
        wave += [(a + p / 4, lo), (a + p / 4, hi), (a + 3 * p / 4, hi), (a + 3 * p / 4, lo), (a + p, lo)]
    svg.polyline(wave, P.black, 3, stroke_linejoin="miter")
    a, b = x0 + p / 4, x0 + 3 * p / 4
    svg.text((a + b) / 2, hi - 22, "500 ms", "codel", 16, P.black_60, "middle")

    svg.frame("blink.", "the hello world of hardware")
    code_rule(svg)
    svg.code(M, CODE_Y, """
digitalWrite(LED, !digitalRead(LED));
delay(500);""", "cpp", 22)
    return svg


def zero() -> Svg:
    """Every robot starts at the origin: two axes and a dot."""
    svg = Svg(P.white)
    o = (CX - 190, CY + 190)
    arrow(svg, o, (o[0] + 380, o[1]), P.teal, 6, 32)
    arrow(svg, o, (o[0], o[1] - 380), P.blue, 6, 32)
    svg.circle(*o, 13, P.black)
    svg.text(o[0] + 404, o[1] + 11, "x", "diag", 34, P.teal)
    svg.text(o[0], o[1] - 410, "y", "diag", 34, P.blue, "middle")

    svg.frame("zero.", "every robot starts at the origin")
    code_rule(svg)
    svg.code(M, CODE_Y, "pose = Pose(x=0.0, y=0.0, θ=0.0)", "py", 22)
    return svg


def loop() -> Svg:
    """Sense, think, act: three dots on one circle."""
    svg = Svg(P.black)
    r = 220
    svg.circle(CX, CY, r, "none", stroke=P.black_80, stroke_width=3)
    for a in (-30, 90, 210):  # direction of travel, clockwise
        t = math.radians(a)
        svg.triangle(CX + r * math.cos(t), CY + r * math.sin(t), 22, P.blue_60, t + math.pi / 2)
    for a, name, col in ((-90, "sense", P.lavender), (30, "think", P.white), (150, "act", P.teal_60)):
        t = math.radians(a)
        svg.circle(CX + r * math.cos(t), CY + r * math.sin(t), 20, col)
        lx, ly = CX + (r + 58) * math.cos(t), CY + (r + 58) * math.sin(t) + 11
        anchor = "middle" if a == -90 else ("start" if a == 30 else "end")
        svg.text(lx, ly - (14 if a == -90 else 0), name, "diag", 30, P.white, anchor)

    svg.frame("loop.", "sense · think · act · repeat", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, """
while ok():
    act(think(sense()))""", "py", 22, dark=True)
    return svg


def step() -> Svg:
    """A stepper motor: 200 ticks a turn, 37 of them taken."""
    svg = Svg(P.white)
    R, k = 250, 37
    for i in range(200):
        a = -math.pi / 2 + 2 * math.pi * i / 200
        l = 28 if i % 10 == 0 else 13
        col = P.blue if i <= k else P.black_20
        svg.line(CX + (R - l) * math.cos(a), CY + (R - l) * math.sin(a), CX + R * math.cos(a), CY + R * math.sin(a),
                 col, 3 if i % 10 == 0 else 2)
    a = -math.pi / 2 + 2 * math.pi * k / 200
    svg.line(CX, CY, CX + (R - 50) * math.cos(a), CY + (R - 50) * math.sin(a), P.teal, 5, stroke_linecap="round")
    svg.circle(CX, CY, 11, P.black)
    svg.text(CX, CY + 66, f"{k} × 1.8° = {k * 1.8:.1f}°", "codel", 20, P.black_60, "middle")

    svg.frame("step.", "stepper motor · 200 steps a turn")
    code_rule(svg)
    svg.code(M, CODE_Y, "angle = steps * 1.8   # degrees", "py", 22)
    return svg


def grip() -> Svg:
    """A parallel gripper closing on a ball."""
    svg = Svg(P.cream)
    r, fw, top = 108, 38, 430
    svg.rect(CX - 17, top - 110, 34, 110, P.black)
    svg.rect(CX - 230, top, 460, 34, P.black)
    svg.rect(CX - r - fw, top + 34, fw, 300, P.black)
    svg.rect(CX + r, top + 34, fw, 300, P.black)
    svg.circle(CX, top + 34 + 300 - r - 6, r, P.teal)
    for s in (-1, 1):
        svg.triangle(CX + s * (r + fw + 52), top + 34 + 300 - r - 6, 34, P.blue, 0 if s < 0 else math.pi)

    svg.frame("grip.", "parallel gripper · close until contact")
    code_rule(svg)
    svg.code(M, CODE_Y, "gripper.close(force=5.0)   # newtons", "py", 22)
    return svg


def stop() -> Svg:
    """Emergency stop: the one button every robot needs."""
    svg = Svg(P.black)
    svg.circle(CX, CY, 250, P.cream)
    svg.circle(CX, CY, 172, P.blue)
    svg.circle(CX, CY, 120, "none", stroke=P.blue_80, stroke_width=4)

    svg.frame("stop.", "emergency stop · always in reach", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "if (estop) motors.disable();", "cpp", 22, dark=True)
    return svg


def charge() -> Svg:
    """A battery, four cells of five."""
    svg = Svg(P.white)
    bw, bh = 460, 220
    x0, y0 = CX - bw / 2 - 14, CY - bh / 2
    svg.rect(x0, y0, bw, bh, "none", stroke=P.black, stroke_width=8, rx=28)
    svg.rect(x0 + bw + 4, CY - 38, 24, 76, P.black, rx=6)
    pad, gap, n = 24, 14, 5
    cw = (bw - 2 * pad - (n - 1) * gap) / n
    for i in range(n):
        svg.rect(x0 + pad + i * (cw + gap), y0 + pad, cw, bh - 2 * pad, P.teal if i < 4 else P.teal_20, rx=6)

    svg.frame("charge.", "battery · four cells of five")
    code_rule(svg)
    svg.code(M, CODE_Y, """
if battery.level < 0.2:
    robot.go(dock)""", "py", 22)
    return svg


def go() -> Svg:
    """Start, goal, and one dotted line between."""
    svg = Svg(P.cream)
    s, g = (250, 880), (830, 420)
    c1, c2 = (250, 620), (830, 700)
    curve = bezier(s, c1, c2, g)
    svg.polyline(curve[6:-6], P.teal, 9, stroke_dasharray="0 22")
    svg.triangle(*s, 62, P.blue, -math.pi / 2)
    svg.circle(*g, 14, P.blue)
    svg.circle(*g, 32, "none", stroke=P.blue, stroke_width=4)

    svg.frame("go.", "start · goal · one line between")
    code_rule(svg)
    svg.code(M, CODE_Y, "robot.go(goal)", "py", 22)
    return svg


def rotate() -> Svg:
    """A square turned by a rotation matrix, where it started dashed behind it."""
    svg = Svg(P.white)
    half = 150

    def square(th):
        return [(CX + half * (sx * math.cos(th) - sy * math.sin(th)), CY + half * (sx * math.sin(th) + sy * math.cos(th)))
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    svg.poly(square(0), "none", stroke=P.lavender_60, stroke_width=3, stroke_dasharray="10 10")
    svg.poly(square(math.radians(36)), P.blue)
    svg.arc(CX, CY, 262, -math.pi / 4, -math.pi / 4 + math.radians(36), P.teal, 4)
    t = -math.pi / 4 + math.radians(18)
    svg.text(CX + 300 * math.cos(t), CY + 300 * math.sin(t) + 10, "θ", "codel", 30, P.teal, "middle")

    svg.frame("rotate.", "one square, one matrix")
    code_rule(svg)
    svg.code(M, CODE_Y, """
R = [[cos(θ), -sin(θ)],
     [sin(θ),  cos(θ)]]""", "py", 22)
    return svg


def think() -> Svg:
    """A tiny network: 3 in, 4 hidden, 2 out."""
    svg = Svg(P.black)
    xs, sizes, gap = (290, CX, 790), (3, 4, 2), 130
    nodes = [[(x, CY + (i - (k - 1) / 2) * gap) for i in range(k)] for x, k in zip(xs, sizes)]
    for a, b in zip(nodes, nodes[1:]):
        for p in a:
            for q in b:
                svg.line(*p, *q, P.black_80, 2)
    for layer, col in zip(nodes, (P.lavender, P.white, P.teal_60)):
        for p in layer:
            svg.circle(*p, 22, col)

    svg.frame("think.", "a tiny network · 3 → 4 → 2", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "y = relu(W @ x + b)", "py", 22, dark=True)
    return svg


def debug() -> Svg:
    """Code as grey bars and one breakpoint."""
    svg = Svg(P.cream)
    lines = [(0, 9), (1, 14), (1, 11), (2, 16), (2, 8), (1, 13), (2, 10), (1, 6), (0, 4)]
    bp, lh, y0, unit = 4, 56, 400, 24
    gx, bx = M + 74, M + 130
    for i, (ind, w) in enumerate(lines):
        y = y0 + i * lh
        if i == bp:
            svg.rect(M, y - lh / 2, W - 2 * M, lh, P.lavender_20)
            svg.circle(M + 22, y, 11, P.teal)
        svg.text(gx, y + 7, str(i + 1), "codel", 18, P.black_60, "end")
        svg.rect(bx + ind * 2 * unit, y - 8, w * unit, 16, P.blue if i == bp else P.black_20, rx=8)

    svg.frame("debug.", "one breakpoint at a time")
    code_rule(svg)
    svg.code(M, CODE_Y, "breakpoint()   # pause, look, continue", "py", 22)
    return svg


def commit() -> Svg:
    """A branch leaves main, picks up three commits, and comes home."""
    svg = Svg(P.white)
    y, yb = CY + 60, CY - 90
    xs = [190 + i * 116 for i in range(7)]
    up = bezier((xs[1], y), (xs[1] + 60, y), (xs[2] - 60, yb), (xs[2], yb))
    down = bezier((xs[4], yb), (xs[4] + 60, yb), (xs[5] - 60, y), (xs[5], y))
    svg.polyline(up + [(xs[3], yb)] + down, P.teal, 4)
    svg.line(xs[0], y, xs[-1], y, P.black, 4)
    for x in xs[2:5]:
        svg.circle(x, yb, 15, P.white, stroke=P.teal, stroke_width=4)
    for x in xs[:-1]:
        svg.circle(x, y, 15, P.white, stroke=P.black, stroke_width=4)
    svg.circle(xs[-1], y, 20, P.blue)
    svg.text(xs[-1], y + 62, "HEAD", "codel", 16, P.blue, "middle")
    svg.text(xs[0] - 36, y + 7, "main", "codel", 18, P.black_60, "end")
    svg.text(xs[3], yb - 40, "wave", "codel", 18, P.teal, "middle")

    svg.frame("commit.", "small steps, saved")
    code_rule(svg)
    svg.code(M, CODE_Y, 'git commit -m "teach robot to wave"', "py", 22)
    return svg


def rest() -> Svg:
    """A robot asleep: closed eyes and three z's."""
    svg = Svg(P.cream)
    hw, hh = 190, 140
    svg.line(CX, CY - hh, CX, CY - hh - 72, P.black, 6)
    svg.circle(CX, CY - hh - 86, 15, P.lavender)
    svg.rect(CX - hw, CY - hh, 2 * hw, 2 * hh, "none", stroke=P.black, stroke_width=8, rx=56)
    for s in (-1, 1):
        svg.arc(CX + s * 72, CY - 6, 34, 0, math.pi, P.black, 8, stroke_linecap="round")
    for i, (size, col) in enumerate(((40, P.lavender), (56, P.blue_60), (74, P.blue))):
        svg.text(CX + hw + 30 + i * 62, CY - hh - 10 - i * 74, "z", "diag", size, col)

    svg.frame("rest.", "sleep mode · wake on motion")
    code_rule(svg)
    svg.code(M, CODE_Y, "robot.sleep(until=motion)", "py", 22)
    return svg


def bye() -> Svg:
    """hello.'s other half: the diagonal flipped, every program ending."""
    svg = Svg(P.black)
    svg.poly([(W, 0), (W, H), (0, H)], P.blue)
    svg.text(M, 380, "// c++", "codel", 20, P.black_60)
    svg.code(M, 440, """
    return 0;
}""", "cpp", 34, dark=True)

    x = 520
    svg.text(x, 846, ">>>", "code", 24, P.lavender_60)
    svg.text(x, 916, "exit(0)", "code", 44, P.white)
    svg.text(x, 982, "# python", "codel", 20, P.blue_40)
    svg.rect(x + 7 * 26.4 + 14, 916 - 32, 15, 38, P.teal)
    svg.frame("bye.", "every program ends somewhere", dark=True, title_fill=P.white)
    return svg


POSTERS = [hello, boot, blink, zero, loop, step, grip, stop, charge, go, rotate, think, debug, commit, rest, bye]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, "minimal")
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
