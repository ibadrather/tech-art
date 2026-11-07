"""Still: minimal computer-vision and photogrammetry posters. One word, one drawing, one line of code.

The quiet siblings of hello. build. plan. assemble., kept as bare as the minimal set: two or
three colours, one idea, a lot of empty paper. From the light coming in to the mesh coming out.

iris. frame. gray. hist. binary. smooth. sharp. harris. pyramid. match.
checker. box. segment. around. down. stitch. cross. cloud. mesh.

Run:  uv run --no-project --with fonttools --with brotli python src/still.py [name ...]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import P, Svg  # noqa: E402
from posters import CODE_Y, M, W, code_rule  # noqa: E402

CX, CY = W / 2, 640  # centre of the drawing
SERIES = "still"


def mix(a: str, b: str, t: float) -> str:
    """Blend two #rrggbb colours: t = 0 gives a, t = 1 gives b."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def solve(A, b):
    """Gaussian elimination with partial pivoting (no numpy needed for an 8 × 8)."""
    n = len(b)
    A = [row[:] + [v] for row, v in zip(A, b)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]
        for r in range(n):
            if r != c:
                f = A[r][c] / A[c][c]
                A[r] = [x - f * y for x, y in zip(A[r], A[c])]
    return [A[i][n] / A[i][i] for i in range(n)]


def homography(src, dst):
    """The 3×3 H (h33 = 1) taking four src points onto four dst points."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = solve(A, b) + [1.0]

    def apply(p):
        x, y = p
        w = h[6] * x + h[7] * y + h[8]
        return ((h[0] * x + h[1] * y + h[2]) / w, (h[3] * x + h[4] * y + h[5]) / w)

    return apply


def rect_pts(cx, cy, w, h, th):
    c, s = math.cos(th), math.sin(th)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


# ----------------------------------------------------------------------------
def iris() -> Svg:
    """A six-blade aperture: the hole is the background showing through."""
    svg = Svg(P.black)
    R, r, rot = 250, 104, math.radians(15)
    v = [(CX + r * math.cos(rot + k * math.pi / 3), CY + r * math.sin(rot + k * math.pi / 3)) for k in range(6)]
    svg.circle(CX, CY, R, P.blue)
    for k in range(6):
        a, b = v[k - 1], v[k]
        d = (b[0] - a[0], b[1] - a[1])
        n = math.hypot(*d)
        d = (d[0] / n, d[1] / n)
        w = (b[0] - CX, b[1] - CY)
        wd = w[0] * d[0] + w[1] * d[1]
        t = -wd + math.sqrt(wd * wd - (w[0] ** 2 + w[1] ** 2) + R * R)  # blade edge runs on to the rim
        svg.line(*a, b[0] + t * d[0], b[1] + t * d[1], P.black, 5)
    svg.poly(v, P.black)

    svg.frame("iris.", "aperture · how much light gets in", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "N = f / D   # the f-number", "py", 22, dark=True)
    return svg


def frame() -> Svg:
    """A viewfinder: four corners, a centre, one dot on a third."""
    svg = Svg(P.white)
    fw, fh, L = 600, 400, 52
    x0, y0, x1, y1 = CX - fw / 2, CY - fh / 2, CX + fw / 2, CY + fh / 2
    for x, y, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
        svg.polyline([(x + sx * L, y), (x, y), (x, y + sy * L)], P.black, 5, stroke_linecap="square", stroke_linejoin="miter")
    svg.line(CX - 14, CY, CX + 14, CY, P.black_20, 2)
    svg.line(CX, CY - 14, CX, CY + 14, P.black_20, 2)
    svg.circle(x0 + 2 * fw / 3, y0 + fh / 3, 13, P.blue)

    svg.frame("frame.", "one picture · h × w × 3 numbers")
    code_rule(svg)
    svg.code(M, CODE_Y, "ok, frame = cap.read()", "py", 22)
    return svg


def gray() -> Svg:
    """Three channels in, one out: the luma weights as widths."""
    svg = Svg(P.cream)
    x, y, bw, bh = M, CY - 110, W - 2 * M, 84
    for name, wt, col in (("R", 0.299, P.lavender), ("G", 0.587, P.teal), ("B", 0.114, P.blue)):
        svg.rect(x, y, wt * bw, bh, col)
        svg.text(x, y - 22, name, "diag", 30, col)
        svg.text(x, y + bh + 36, f"{wt:.3f}", "codel", 18, P.black_60)
        x += wt * bw
    svg.rect(M, CY + 120, bw, bh, P.black_60)
    svg.text(M, CY + 98, "Y", "diag", 30, P.black_60)

    svg.frame("gray.", "three channels · one brightness")
    code_rule(svg)
    svg.code(M, CODE_Y, "gray = 0.299*r + 0.587*g + 0.114*b", "py", 22)
    return svg


def hist() -> Svg:
    """A bimodal histogram and the Otsu threshold that splits it."""
    svg = Svg(P.white)
    n = 32

    def g(x, mu, s):
        return math.exp(-0.5 * ((x - mu) / s) ** 2)

    h = [0.6 * g(i, 8, 3.2) + 1.0 * g(i, 22, 2.6) + 0.04 for i in range(n)]
    tot = sum(h)
    best, t_best = -1, 0
    for t in range(1, n):  # Otsu: maximise between-class variance
        w0 = sum(h[:t]) / tot
        w1 = 1 - w0
        if w0 == 0 or w1 == 0:
            continue
        m0 = sum(i * h[i] for i in range(t)) / sum(h[:t])
        m1 = sum(i * h[i] for i in range(t, n)) / sum(h[t:])
        if (v := w0 * w1 * (m0 - m1) ** 2) > best:
            best, t_best = v, t
    base, top, cw = 880, 380, (W - 2 * M) / n
    for i, v in enumerate(h):
        bh = (base - top) * v / max(h)
        svg.rect(M + i * cw + 3, base - bh, cw - 6, bh, P.black if i < t_best else P.black_20)
    tx = M + t_best * cw
    svg.line(tx, top - 30, tx, base + 30, P.blue, 4)
    svg.text(tx + 14, top - 10, "otsu", "codel", 18, P.blue)

    svg.frame("hist.", "brightness counted · two humps, one valley")
    code_rule(svg)
    svg.code(M, CODE_Y, "t, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)", "py", 21)
    return svg


def binary() -> Svg:
    """A ramp of grays, and the same ramp after one threshold."""
    svg = Svg(P.cream)
    n, s, gap = 12, 64, 12
    x0 = CX - (n * (s + gap) - gap) / 2
    for i in range(n):
        x = x0 + i * (s + gap)
        t = i / (n - 1)
        svg.rect(x, CY - 150, s, s, mix(P.white, P.black, t))
        if t >= 0.5:
            svg.rect(x, CY + 86, s, s, P.black)
        else:
            svg.rect(x + 1.5, CY + 87.5, s - 3, s - 3, P.white, stroke=P.black_20, stroke_width=3)
    cut = x0 + n / 2 * (s + gap) - gap / 2
    svg.triangle(cut, CY - 10, 30, P.blue, math.pi / 2)

    svg.frame("binary.", "one threshold · two colours")
    code_rule(svg)
    svg.code(M, CODE_Y, "bw = gray > 128", "py", 22)
    return svg


def smooth() -> Svg:
    """A 5 × 5 Gaussian kernel: each dot's area is its weight."""
    svg = Svg(P.white)
    k, step = [1, 4, 6, 4, 1], 118
    for i, a in enumerate(k):
        for j, b in enumerate(k):
            svg.circle(CX + (j - 2) * step, CY + (i - 2) * step, 46 * math.sqrt(a * b / 36), P.blue)

    svg.frame("smooth.", "gaussian kernel · 5 × 5 · sums to 1")
    code_rule(svg)
    svg.code(M, CODE_Y, "blur = cv2.GaussianBlur(img, (5, 5), 0)", "py", 22)
    return svg


def sharp() -> Svg:
    """The same disc out of focus and in focus."""
    svg = Svg(P.cream)
    svg.add('<defs><filter id="soft" x="-60%" y="-60%" width="220%" height="220%">'
            '<feGaussianBlur stdDeviation="24"/></filter></defs>')
    svg.circle(CX - 210, CY, 130, P.black, filter="url(#soft)")
    svg.circle(CX + 210, CY, 130, P.black)
    svg.circle(CX + 210, CY, 152, "none", stroke=P.blue, stroke_width=4)

    svg.frame("sharp.", "focus · the sharp one has edges")
    code_rule(svg)
    svg.code(M, CODE_Y, "focus = cv2.Laplacian(gray, cv2.CV_64F).var()", "py", 22)
    return svg


def harris() -> Svg:
    """Slide a window: flat changes nothing, an edge one way, a corner every way."""
    svg = Svg(P.white)
    c = (CX - 70, CY - 50)
    svg.rect(c[0], c[1], 360, 360, P.teal)
    r = 64
    for (x, y), name, dy in (((CX - 270, CY - 230), "flat", -r - 20), ((CX + 150, c[1]), "edge", -r - 20)):
        svg.circle(x, y, r, "none", stroke=P.black_60, stroke_width=3)
        svg.text(x, y + dy, name, "codel", 18, P.black_60, "middle")
    svg.circle(*c, r, "none", stroke=P.blue, stroke_width=5)
    svg.circle(*c, 11, P.blue)
    svg.text(c[0] - r - 18, c[1] + 6, "corner", "codel", 18, P.blue, "end")

    svg.frame("harris.", "a corner changes every way you move")
    code_rule(svg)
    svg.code(M, CODE_Y, "R = det(M) - k * trace(M)**2", "py", 22)
    return svg


def pyramid() -> Svg:
    """An image pyramid: each level half the size of the last."""
    svg = Svg(P.cream)
    sizes, gap = [384, 192, 96, 48, 24], 36
    cols = [P.blue_20, P.blue_40, P.blue_60, P.blue_80, P.blue]
    x = CX - (sum(sizes) + gap * (len(sizes) - 1)) / 2
    for s, col in zip(sizes, cols):
        svg.rect(x, CY + 192 - s, s, s, col)
        x += s + gap

    svg.frame("pyramid.", "every scale · half each time")
    code_rule(svg)
    svg.code(M, CODE_Y, "small = cv2.pyrDown(img)", "py", 22)
    return svg


def match() -> Svg:
    """Two pictures of one scene, the same points joined across."""
    svg = Svg(P.black)
    rw, rh = 340, 450
    L = (M + 20, CY - rh / 2)
    R = (W - M - 20 - rw, CY - rh / 2)
    for x, y in (L, R):
        svg.rect(x, y, rw, rh, "none", stroke=P.black_80, stroke_width=3)
    rng = random.Random(7)
    pts = [(rng.uniform(0.15, 0.85), rng.uniform(0.1, 0.9)) for _ in range(8)]
    th, sc = math.radians(9), 0.88

    def right(u, v):
        x, y = (u - 0.5) * rw, (v - 0.5) * rh
        return (R[0] + rw / 2 + sc * (x * math.cos(th) - y * math.sin(th)),
                R[1] + rh / 2 + sc * (x * math.sin(th) + y * math.cos(th)))

    pairs = [((L[0] + u * rw, L[1] + v * rh), right(u, v)) for u, v in pts]
    for i, (a, b) in enumerate(pairs):
        if i == 3:  # one bad match
            b = pairs[6][1]
        svg.line(*a, *b, P.lavender if i == 3 else P.teal_60, 2)
    for a, b in pairs:
        svg.circle(*a, 6, P.white)
        svg.circle(*b, 6, P.white)

    svg.frame("match.", "same point · two pictures", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "matches = bf.knnMatch(d1, d2, k=2)", "py", 22, dark=True)
    return svg


def checker() -> Svg:
    """A calibration board seen at an angle, its inner corners found."""
    svg = Svg(P.white)
    cols, rows = 8, 6
    H = homography([(0, 0), (cols, 0), (cols, rows), (0, rows)],
                   [(250, 420), (860, 372), (880, 860), (196, 812)])
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2 == 0:
                svg.poly([H(p) for p in ((c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1))], P.black)
    svg.poly([H(p) for p in ((0, 0), (cols, 0), (cols, rows), (0, rows))], "none", stroke=P.black, stroke_width=2)
    corners = [H((c, r)) for r in range(1, rows) for c in range(1, cols)]
    for p in corners:
        svg.circle(*p, 9, P.blue)

    svg.frame("checker.", "calibration · 7 × 5 inner corners")
    code_rule(svg)
    svg.code(M, CODE_Y, "ok, pts = cv2.findChessboardCorners(gray, (7, 5))", "py", 22)
    return svg


def box() -> Svg:
    """A detection: one thing, one box, one score."""
    svg = Svg(P.cream)
    r, pad = 118, 30
    svg.circle(CX, CY + 30, r, P.teal)
    x, y, s = CX - r - pad, CY + 30 - r - pad, 2 * (r + pad)
    svg.rect(x, y, s, s, "none", stroke=P.blue, stroke_width=5)
    svg.rect(x - 2.5, y - 46, 168, 46, P.blue)
    svg.text(x + 14, y - 15, "ball 0.97", "code", 20, P.white)

    svg.frame("box.", "detection · where, what, how sure")
    code_rule(svg)
    svg.code(M, CODE_Y, "boxes = model(img)   # x, y, w, h, score", "py", 22)
    return svg


def segment() -> Svg:
    """Segmentation: every pixel answers yes or no."""
    svg = Svg(P.black)
    cols, rows, cs = 13, 10, 60
    ox, oy = CX - cols * cs / 2, CY - rows * cs / 2 + 20

    def inside(c, r):
        return math.hypot(c - 5.2, r - 5.4) < 3.3 or math.hypot(c - 8.6, r - 3.6) < 2.3

    for r in range(rows):
        for c in range(cols):
            x, y = ox + c * cs, oy + r * cs
            if inside(c + 0.5, r + 0.5):
                svg.rect(x + 3, y + 3, cs - 6, cs - 6, P.lavender)
            else:
                svg.circle(x + cs / 2, y + cs / 2, 2.6, P.black_80)

    svg.frame("segment.", "every pixel · yes or no", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "mask = model(img) > 0.5", "py", 22, dark=True)
    return svg


def around() -> Svg:
    """Photogrammetry's first rule: walk round it, a photo every 15°."""
    svg = Svg(P.white)
    R = 300
    svg.circle(CX, CY, R, "none", stroke=P.black_20, stroke_width=2, stroke_dasharray="2 10", stroke_linecap="round")
    svg.circle(CX, CY, 74, P.teal)
    for k in range(24):
        a = -math.pi / 2 + 2 * math.pi * k / 24
        svg.triangle(CX + R * math.cos(a), CY + R * math.sin(a), 34, P.blue if k == 0 else P.blue_40, a + math.pi)

    svg.frame("around.", "photogrammetry · walk round it")
    code_rule(svg)
    svg.code(M, CODE_Y, "for a in range(0, 360, 15): shoot(a)", "py", 22)
    return svg


def down() -> Svg:
    """A nadir photo: one camera straight down, the patch of ground it sees."""
    svg = Svg(P.cream)
    cam, gy, half = (CX, 400), 880, 270
    svg.line(cam[0], cam[1] + 20, CX - half, gy, P.black_20, 2)
    svg.line(cam[0], cam[1] + 20, CX + half, gy, P.black_20, 2)
    svg.line(CX, cam[1] + 40, CX, gy - 16, P.black_20, 2, stroke_dasharray="6 10")
    svg.text(CX + 16, (cam[1] + gy) / 2 + 8, "H", "codel", 22, P.black_60)
    svg.line(M, gy, W - M, gy, P.black, 3)
    svg.line(CX - half, gy, CX + half, gy, P.teal, 12, stroke_linecap="butt")
    svg.triangle(*cam, 64, P.blue, math.pi / 2)

    svg.frame("down.", "nadir · straight down, one footprint")
    code_rule(svg)
    svg.code(M, CODE_Y, "gsd = H * pixel_size / f", "py", 22)
    return svg


def stitch() -> Svg:
    """Two photos that share a strip become one."""
    svg = Svg(P.cream)
    svg.poly(rect_pts(CX - 120, CY - 30, 440, 320, math.radians(-4)), P.lavender, opacity="0.75")
    svg.poly(rect_pts(CX + 120, CY + 36, 440, 320, math.radians(5)), P.teal, opacity="0.6")

    svg.frame("stitch.", "two photos · one shared strip")
    code_rule(svg)
    svg.code(M, CODE_Y, "ok, pano = cv2.Stitcher_create().stitch(imgs)", "py", 22)
    return svg


def cross() -> Svg:
    """Two cameras, two rays, one point in space."""
    svg = Svg(P.black)
    X = (CX + 70, 400)
    for cam, col in (((CX - 260, 900), P.teal_60), ((CX + 260, 900), P.lavender)):
        f = 120
        svg.line(cam[0] - 90, cam[1] - f, cam[0] + 90, cam[1] - f, P.black_80, 3)
        svg.line(*cam, *X, col, 3)
        t = f / (cam[1] - X[1])
        svg.circle(cam[0] + t * (X[0] - cam[0]), cam[1] - f, 7, col)
        svg.triangle(*cam, 44, P.white, -math.pi / 2)
    svg.circle(*X, 14, P.white)

    svg.frame("cross.", "two rays · one point", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, "X = cv2.triangulatePoints(P1, P2, x1, x2)", "py", 22, dark=True)
    return svg


def cloud() -> Svg:
    """A point cloud: a torus of dots, nearer ones bigger and brighter."""
    svg = Svg(P.black)
    Rt, rt, tilt = 230, 90, 1.05
    pts = []
    for i in range(96):
        for j in range(30):
            u, v = 2 * math.pi * (i + 0.5 * (j % 2)) / 96, 2 * math.pi * j / 30
            x = (Rt + rt * math.cos(v)) * math.cos(u)
            y = (Rt + rt * math.cos(v)) * math.sin(u)
            z = rt * math.sin(v)
            y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
            pts.append((x, y, z))
    zmax = Rt + rt
    for x, y, z in sorted(pts, key=lambda p: p[2]):
        t = (z + zmax) / (2 * zmax)
        svg.circle(CX + x, CY + y, 1.4 + 2.6 * t, mix(P.black_80, P.lavender, t))

    svg.frame("cloud.", "points · no surface yet", dark=True, title_fill=P.white)
    code_rule(svg, P.lavender)
    svg.code(M, CODE_Y, 'pcd = o3d.io.read_point_cloud("scan.ply")', "py", 22, dark=True)
    return svg


def mesh() -> Svg:
    """Points joined into triangles: a bump in a sheet."""
    svg = Svg(P.white)
    n, s, yaw, el = 9, 330, math.radians(30), math.radians(32)

    def proj(i, j):
        x, y = -1 + 2 * i / (n - 1), -1 + 2 * j / (n - 1)
        z = 0.62 * math.exp(-((x + 0.1) ** 2 + (y - 0.1) ** 2) / 0.3)
        x, y = x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw)
        return (CX + s * x, CY + 110 - s * (y * math.sin(el) + z * math.cos(el)))

    P2 = [[proj(i, j) for j in range(n)] for i in range(n)]
    i0, j0 = n // 2 - 1, n // 2 - 2  # one face filled, on the slope facing us
    svg.poly([P2[i0][j0], P2[i0 + 1][j0], P2[i0 + 1][j0 + 1]], P.blue)
    for i in range(n):
        for j in range(n):
            if i + 1 < n:
                svg.line(*P2[i][j], *P2[i + 1][j], P.black, 2)
            if j + 1 < n:
                svg.line(*P2[i][j], *P2[i][j + 1], P.black, 2)
            if i + 1 < n and j + 1 < n:
                svg.line(*P2[i][j], *P2[i + 1][j + 1], P.black_20, 1.5)

    svg.frame("mesh.", "points joined · now a surface")
    code_rule(svg)
    svg.code(M, CODE_Y, "mesh = poisson(pcd, depth=9)", "py", 22)
    return svg


POSTERS = [iris, frame, gray, hist, binary, smooth, sharp, harris, pyramid, match,
           checker, box, segment, around, down, stitch, cross, cloud, mesh]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in POSTERS:
        if want and fn.__name__ not in want:
            continue
        out = fn().save(fn.__name__, SERIES)
        print(out.relative_to(Path(__file__).resolve().parents[1]), f"{out.stat().st_size // 1024} KB")
