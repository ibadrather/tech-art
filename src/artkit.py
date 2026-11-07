"""A tiny SVG toolkit for Edreate tech-art posters.

Brand values come from the Edreate Brand Book (github.com/edreate/Brand-Identity-Media):
colours on pages 10-11, Poppins for headings, Fira Code for code, Urbanist for diagrams.
Every poster is a self-contained SVG: the fonts are subset to the glyphs used and embedded.
"""

from __future__ import annotations

import base64
import html
import io
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "brand"


@dataclass(frozen=True)
class Palette:
    """Brand colours and their tints on white (the brand book allows 80/60/40/20%)."""

    blue: str = "#4531CC"  # Cornflower Blue, primary
    teal: str = "#448882"  # Teal Blue
    lavender: str = "#8C8AFE"  # Lavender Blue
    black: str = "#0C0C0C"  # Rich Black
    cream: str = "#FCF3D1"
    white: str = "#FFFFFF"
    blue_80: str = "#6A5AD6"
    blue_60: str = "#8F83E0"
    blue_40: str = "#B5ADEB"
    blue_20: str = "#DAD6F5"
    teal_60: str = "#8FB8B4"
    teal_20: str = "#DAE7E6"
    lavender_60: str = "#BAB9FE"
    lavender_20: str = "#E8E8FF"
    black_80: str = "#3D3D3D"
    black_60: str = "#6D6D6D"
    black_20: str = "#CECECE"


P = Palette()


@dataclass(frozen=True)
class Fonts:
    """Font key -> (CSS family name, file in brand/fonts)."""

    files: dict = field(
        default_factory=lambda: {
            "head": ("EdrPoppins", "Poppins-SemiBold.ttf"),
            "light": ("EdrPoppinsLight", "Poppins-Light.ttf"),
            "code": ("EdrFira", "FiraCode-Medium.ttf"),
            "codel": ("EdrFiraLight", "FiraCode-Regular.ttf"),
            "diag": ("EdrUrbanist", "Urbanist-SemiBold.ttf"),
        }
    )


FONTS = Fonts()


@dataclass(frozen=True)
class Canvas:
    width: int = 1080
    height: int = 1350
    margin: int = 84


CANVAS = Canvas()


def _fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pts(points) -> str:
    return " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in points)


class Svg:
    """Collects SVG elements and the characters drawn in each font."""

    def __init__(self, bg: str, w: int = CANVAS.width, h: int = CANVAS.height):
        self.w, self.h, self.bg = w, h, bg
        self.parts: list[str] = []
        self.chars: dict[str, set[str]] = {k: set() for k in FONTS.files}

    def add(self, s: str) -> None:
        self.parts.append(s)

    # --- shapes -------------------------------------------------------------
    def rect(self, x, y, w, h, fill, **kw) -> None:
        self.add(f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(w)}" height="{_fmt(h)}" fill="{fill}"{_attrs(kw)}/>')

    def circle(self, cx, cy, r, fill="none", **kw) -> None:
        self.add(f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(r)}" fill="{fill}"{_attrs(kw)}/>')

    def line(self, x1, y1, x2, y2, stroke, width=2, **kw) -> None:
        self.add(
            f'<line x1="{_fmt(x1)}" y1="{_fmt(y1)}" x2="{_fmt(x2)}" y2="{_fmt(y2)}" '
            f'stroke="{stroke}" stroke-width="{_fmt(width)}"{_attrs(kw)}/>'
        )

    def poly(self, points, fill, **kw) -> None:
        self.add(f'<polygon points="{pts(points)}" fill="{fill}"{_attrs(kw)}/>')

    def polyline(self, points, stroke, width=2, **kw) -> None:
        kw.setdefault("stroke_linejoin", "round")
        kw.setdefault("stroke_linecap", "round")
        self.add(
            f'<polyline points="{pts(points)}" fill="none" stroke="{stroke}" stroke-width="{_fmt(width)}"{_attrs(kw)}/>'
        )

    def triangle(self, cx, cy, size, fill, angle=0.0, **kw) -> None:
        """Equilateral triangle centred on (cx, cy), pointing along `angle` (radians, 0 = right)."""
        r = size / math.sqrt(3)
        p = [(cx + r * math.cos(angle + k * 2 * math.pi / 3), cy + r * math.sin(angle + k * 2 * math.pi / 3)) for k in range(3)]
        self.poly(p, fill, **kw)

    def arc(self, cx, cy, r, a0, a1, stroke, width=2, n=48, **kw) -> None:
        """Circular arc from angle a0 to a1 (radians, page coords: y down)."""
        p = [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
        self.polyline(p, stroke, width, **kw)

    def clip_begin(self, x, y, w, h) -> None:
        """Start a group clipped to a rectangle; close it with clip_end()."""
        self._clips = getattr(self, "_clips", 0) + 1
        cid = f"clip{self._clips}"
        self.add(
            f'<clipPath id="{cid}"><rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(w)}" height="{_fmt(h)}"/></clipPath>'
            f'<g clip-path="url(#{cid})">'
        )

    def clip_end(self) -> None:
        self.add("</g>")

    # --- text ---------------------------------------------------------------
    def text(self, x, y, s, font="head", size=24, fill=P.black, anchor="start", **kw) -> None:
        self.chars[font].update(s)
        family = FONTS.files[font][0]
        self.add(
            f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-family="{family}" font-size="{_fmt(size)}" fill="{fill}" '
            f'text-anchor="{anchor}" style="white-space:pre"{_attrs(kw)}>{html.escape(s)}</text>'
        )

    def code(self, x, y, src: str, lang="py", size=22, leading=1.55, dark=False, font="code") -> float:
        """Syntax-tinted code block in Fira Code; returns the y below the last line."""
        theme = CODE_THEME_DARK if dark else CODE_THEME_LIGHT
        for i, line in enumerate(src.strip("\n").split("\n")):
            spans = []
            for kind, tok in tokenize(line, lang):
                self.chars[font].update(tok)
                spans.append(f'<tspan fill="{theme[kind]}">{html.escape(tok)}</tspan>')
            self.add(
                f'<text x="{_fmt(x)}" y="{_fmt(y + i * size * leading)}" font-family="{FONTS.files[font][0]}" '
                f'font-size="{size}" style="white-space:pre;font-variant-ligatures:contextual">{"".join(spans)}</text>'
            )
        return y + (len(src.strip(chr(10)).split(chr(10)))) * size * leading

    # --- brand furniture ----------------------------------------------------
    def logo_mark(self, x, y, h, fill=P.blue, opacity=1.0) -> None:
        """The 'edr.' mark, top-left corner at (x, y), height h."""
        src = (BRAND / "logo/logo-mark.svg").read_text()
        vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', src).group(1).split()]
        body = re.sub(r"<defs>.*?</defs>|<title>.*?</title>", "", src, flags=re.S)
        body = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", body, flags=re.S)
        body = body.replace('class="cls-1"', f'fill="{fill}"')
        s = h / vb[3]
        self.add(f'<g transform="translate({_fmt(x)} {_fmt(y)}) scale({s:.5f}) translate({-vb[0]} {-vb[1]})" opacity="{opacity}">{body}</g>')

    def icon(self, x, y, size, name: str) -> None:
        """A brand icon from brand/icons, as an isolated data-URI image."""
        data = base64.b64encode((BRAND / "icons" / f"{name}.svg").read_bytes()).decode()
        self.add(f'<image x="{_fmt(x)}" y="{_fmt(y)}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>')

    def frame(self, title: str, kicker: str, dark=False, title_fill=None) -> None:
        """Title top-left; the brand-book corner triangle bottom-right, carrying a small white logo mark."""
        m = CANVAS.margin
        ink = P.white if dark else P.black
        self.text(m, m + 70, title, "head", 92, title_fill or (P.white if dark else P.blue), letter_spacing="-2")
        self.text(m + 4, m + 118, kicker, "codel", 20, P.black_60 if not dark else P.blue_40)
        t = 150  # brand-book page marker: a triangle in the corner
        self.poly([(self.w, self.h - t * 0.95), (self.w, self.h), (self.w - t * 1.1, self.h)], P.blue)
        self.logo_mark(self.w - 62, self.h - 44, 30, P.white, 0.95)  # the mark sits inside the corner triangle
        _ = ink

    # --- output -------------------------------------------------------------
    def render(self) -> str:
        css = "".join(_font_face(k, chars) for k, chars in self.chars.items() if chars)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}">'
            f"<style>{css}</style>"
            f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>' + "\n".join(self.parts) + "</svg>\n"
        )

    def save(self, name: str, series: str) -> Path:
        out = ROOT / "out" / series / f"{name}.svg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render())
        return out


def _attrs(kw: dict) -> str:
    return "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())


def _font_face(key: str, chars: set[str], family: str | None = None) -> str:
    family, file = family or FONTS.files[key][0], FONTS.files[key][1]
    font = TTFont(BRAND / "fonts" / file)
    opts = subset.Options()
    opts.layout_features = ["*"]  # keep Fira Code ligatures and contextual alternates
    opts.flavor = "woff2" if _has_brotli() else None
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(chars) + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = opts.flavor
    font.save(buf)
    fmt, mime = ("woff2", "font/woff2") if opts.flavor else ("truetype", "font/ttf")
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:{mime};base64,{data}) format('{fmt}');}}"


def _has_brotli() -> bool:
    try:
        import brotli  # noqa: F401

        return True
    except ImportError:
        return False


# --- a very small syntax highlighter ------------------------------------------
KEYWORDS = {
    "py": "def return for in if else while import from as class self lambda and or not None True False yield with".split(),
    "cpp": "auto const return for if else while void double float int bool struct class include namespace using std "
    "template typename true false nullptr static_cast".split(),
}
TOKEN_RE = re.compile(
    r"(?P<comment>#(?!include).*|//.*)|(?P<string>\"[^\"]*\"|'[^']*')|(?P<pre>#include)|(?P<number>\b\d+\.?\d*(?:e-?\d+)?[fFuUlL]?\b)"
    r"|(?P<word>[A-Za-z_]\w*)|(?P<op>[^\sA-Za-z_\d\"']+)|(?P<space>\s+)|(?P<other>\S)"
)
CODE_THEME_LIGHT = {"comment": P.black_60, "string": P.teal, "number": P.lavender, "keyword": P.blue, "pre": P.blue,
                    "call": P.teal, "word": P.black, "op": P.black_60, "space": P.black}
CODE_THEME_DARK = {"comment": P.black_60, "string": P.teal_60, "number": P.lavender, "keyword": P.lavender, "pre": P.lavender,
                   "call": P.teal_60, "word": P.white, "op": P.blue_40, "space": P.white}


def tokenize(line: str, lang: str):
    toks = [(m.lastgroup, m.group()) for m in TOKEN_RE.finditer(line)]
    out = []
    for i, (kind, tok) in enumerate(toks):
        if kind == "other":  # e.g. the "3" of "3in": draw it, don't drop it
            kind = "word"
        if kind == "word":
            if tok in KEYWORDS[lang]:
                kind = "keyword"
            elif i + 1 < len(toks) and toks[i + 1][1].startswith("("):
                kind = "call"
        out.append((kind, tok))
    return out
