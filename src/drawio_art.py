"""Two posters drawn in draw.io: a robot node graph and a rover spec sheet.

Each poster is written as an editable .drawio file, exported to SVG with the draw.io CLI, and then
the brand fonts (Poppins, Fira Code, Urbanist) are embedded into that SVG, because the CLI only uses
fonts installed on the machine.

Run:  uv run --no-project --with fonttools --with brotli python src/drawio_art.py
"""

from __future__ import annotations

import base64
import html
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from artkit import BRAND, CANVAS, CODE_THEME_LIGHT, P, ROOT, _font_face, tokenize  # noqa: E402

W, H, M = CANVAS.width, CANVAS.height, CANVAS.margin
FAMILIES = {"head": "Poppins", "code": "Fira Code", "diag": "Urbanist"}


def data_uri(path: Path, fill: str | None = None) -> str:
    raw = path.read_text()
    if fill:
        raw = re.sub(r"fill:#[0-9a-fA-F]{6}", f"fill:{fill}", raw)
    return "data:image/svg+xml," + base64.b64encode(raw.encode()).decode()


class Drawio:
    def __init__(self, name: str, bg: str):
        self.name, self.bg = name, bg
        self.cells: list[str] = []
        self.n = 0
        self.vertex(0, 0, W, H, "", f"rounded=0;strokeColor=none;fillColor={bg};")

    def _id(self) -> str:
        self.n += 1
        return f"c{self.n}"

    def vertex(self, x, y, w, h, value, style) -> str:
        i = self._id()
        self.cells.append(
            f'<mxCell id="{i}" value="{html.escape(value, quote=True)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return i

    def edge(self, src, tgt, style, value="", points=()) -> str:
        i = self._id()
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        arr = f'<Array as="points">{pts}</Array>' if pts else ""
        self.cells.append(
            f'<mxCell id="{i}" value="{html.escape(value, quote=True)}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">'
            f'<mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>'
        )
        return i

    def line(self, x1, y1, x2, y2, style) -> str:
        i = self._id()
        self.cells.append(
            f'<mxCell id="{i}" value="" style="{style}" edge="1" parent="1"><mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1}" y="{y1}" as="sourcePoint"/><mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry></mxCell>'
        )
        return i

    def image(self, x, y, w, h, uri, opacity=100) -> str:
        return self.vertex(x, y, w, h, "", f"shape=image;aspect=fixed;imageAspect=1;opacity={opacity};image={uri};")

    def text(self, x, y, w, h, value, font="diag", size=20, color=P.black, align="left", valign="top") -> str:
        return self.vertex(
            x, y, w, h, value,
            f"text;html=1;whiteSpace=wrap;strokeColor=none;fillColor=none;align={align};verticalAlign={valign};"
            f"fontFamily={FAMILIES[font]};fontSize={size};fontColor={color};spacing=0;",
        )

    def frame(self, title: str, kicker: str):
        self.text(M - 2, M - 8, 700, 120, title, "head", 92, P.blue)
        self.text(M + 4, M + 101, 800, 30, kicker, "code", 20, P.black_60)
        tri = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 165 143">'
               f'<polygon points="165,0 165,143 0,143" fill="{P.blue}"/></svg>')
        self.vertex(W - 165, H - 143, 165, 143, "",
                    "shape=image;imageAspect=0;image=data:image/svg+xml," + base64.b64encode(tri.encode()).decode() + ";")
        self.image(W - 62, H - 44, 48, 30, data_uri(BRAND / "logo/logo-mark.svg", P.white), 95)

    def save(self) -> Path:
        xml = (
            f'<mxfile><diagram name="{self.name}"><mxGraphModel dx="0" dy="0" grid="0" page="1" pageWidth="{W}" pageHeight="{H}" '
            f'background="{self.bg}"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(self.cells)}</root>'
            "</mxGraphModel></diagram></mxfile>\n"
        )
        out = ROOT / "out/core" / f"{self.name}.drawio"
        out.write_text(xml)
        return out


def code_html(src: str, lang: str, theme=CODE_THEME_LIGHT) -> str:
    lines = []
    for line in src.strip("\n").split("\n"):
        spans = "".join(
            f'<font color="{theme[k]}">{html.escape(t).replace(" ", "&nbsp;")}</font>' for k, t in tokenize(line, lang)
        )
        lines.append(spans or "&nbsp;")
    return "<br>".join(lines)


# --- styles -------------------------------------------------------------------------------------------------
BOX = "rounded=0;whiteSpace=wrap;html=1;strokeColor=none;fontFamily=Urbanist;fontSize=22;"
PART = BOX + f"fillColor={P.blue_20};fontColor={P.black};"
CORE = "ellipse;" + BOX + f"fillColor={P.teal};fontColor={P.white};"
RESULT = BOX + f"fillColor={P.black};fontColor={P.white};"
EXTERNAL = BOX + f"fillColor={P.cream};fontColor={P.black};"
ARROW = (
    f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor={P.black};strokeWidth=2.5;endArrow=block;endFill=1;"
    f"endSize=8;fontFamily=Fira Code;fontSize=15;fontColor={P.black};labelBackgroundColor={P.white};"
)
THIN = f"endArrow=oval;endFill=1;endSize=7;startArrow=none;html=1;strokeColor={P.black};strokeWidth=1.5;"


def connect() -> Drawio:
    """A node graph: sensors -> perception -> planner -> motors, topics on the arrows."""
    d = Drawio("connect", P.white)
    icon = lambda n: data_uri(BRAND / "icons" / f"{n}.svg")  # noqa: E731
    cam = d.vertex(196, 300, 220, 84, "/camera", EXTERNAL)
    d.image(110, 306, 72, 72, icon("Camera"))
    lid = d.vertex(664, 300, 220, 84, "/lidar", EXTERNAL)
    d.image(898, 306, 72, 72, icon("Range Finder Sensor"))
    per = d.vertex(420, 480, 240, 124, "/perception", CORE)
    mp = d.vertex(196, 700, 220, 84, "/map", EXTERNAL)
    d.image(110, 706, 72, 72, icon("Map"))
    pln = d.vertex(430, 700, 220, 84, "/planner", PART)
    mot = d.vertex(430, 880, 220, 84, "/motors", RESULT)
    d.image(664, 886, 72, 72, icon("Actuator"))

    d.edge(cam, per, ARROW + "exitX=0.5;exitY=1;entryX=0;entryY=0.5;", "/image_raw", [(306, 542)])
    d.edge(lid, per, ARROW + "exitX=0.5;exitY=1;entryX=1;entryY=0.5;", "/scan", [(774, 542)])
    d.edge(per, pln, ARROW + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;", "/obstacles")
    d.edge(mp, pln, ARROW + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    d.edge(pln, mot, ARROW + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;", "/cmd_vel")

    # terminal, like the brand's Terminal icon
    d.vertex(M, 1040, W - 2 * M - 70, 170, "", f"rounded=0;strokeColor=none;fillColor={P.black};")
    for i, c in enumerate((P.lavender, P.teal, P.blue)):
        d.vertex(M + 26 + i * 26, 1060, 14, 14, "", f"ellipse;strokeColor=none;fillColor={c};")
    term = (
        f'<font color="{P.teal_60}">$</font> <font color="{P.white}">./rover --config rover.yaml</font><br>'
        f'<font color="{P.black_60}">[perception]</font> <font color="{P.lavender}">subscribed /scan /image_raw</font><br>'
        f'<font color="{P.black_60}">[planner]</font> <font color="{P.lavender}">publishing /cmd_vel @ 20 Hz</font>'
    )
    d.text(M + 26, 1094, 820, 110, term, "code", 19, P.white)
    d.frame("connect.", "node graph · topics on the wires")
    return d


def assemble() -> Drawio:
    """A rover drawn from draw.io primitives, annotated like a spec sheet, with its mount struct below."""
    d = Drawio("assemble", P.cream)
    ink = f"strokeColor=none;rounded=0;"
    # body
    d.vertex(640, 400, 14, 200, "", ink + f"fillColor={P.black};")  # mast
    d.vertex(330, 520, 200, 80, "", ink + f"fillColor={P.blue_20};")  # compute
    d.vertex(230, 600, 620, 100, "", ink + f"fillColor={P.blue};")  # chassis
    d.vertex(580, 625, 160, 50, "", ink + f"fillColor={P.lavender};")  # battery
    d.vertex(800, 532, 76, 68, "", ink + f"fillColor={P.black};")  # camera
    d.vertex(823, 551, 30, 30, "", f"ellipse;strokeColor=none;fillColor={P.lavender};")
    d.vertex(595, 345, 104, 56, "", ink + f"fillColor={P.teal};")  # lidar
    d.vertex(617, 327, 60, 18, "", ink + f"fillColor={P.black};")
    for cx in (330, 750):  # wheels
        d.vertex(cx - 78, 667, 156, 156, "", f"ellipse;strokeColor=none;fillColor={P.black};")
        d.vertex(cx - 24, 721, 48, 48, "", f"ellipse;strokeColor=none;fillColor={P.cream};")
    d.line(110, 823, 970, 823, f"endArrow=none;html=1;strokeColor={P.black};strokeWidth=2;")

    # call-outs: a dot on the part, a line, then name + topic
    def callout(px, py, lx, ly, name, sub, align="left"):
        tx = lx if align == "left" else lx - 220
        ex = lx - 8 if align == "left" else lx + 8
        d.line(ex, ly + 16, px, py, THIN)
        label = f'{name}<br><font face="Fira Code" style="font-size:15px" color="{P.black_60}">{sub}</font>'
        d.text(tx, ly, 220, 60, label, "diag", 24, P.black, align)

    callout(699, 372, 790, 300, "lidar", "/scan · 10 Hz")
    callout(430, 540, 330, 420, "compute", "python + c++", "right")
    callout(876, 566, 905, 470, "camera", "/image_raw")
    callout(740, 650, 905, 640, "battery", "24 V · 10 Ah")
    callout(256, 745, 230, 700, "drive", "/cmd_vel", "right")

    # wheelbase dimension
    dim = f"endArrow=none;html=1;strokeColor={P.black};strokeWidth=1.5;"
    d.line(330, 880, 750, 880, dim)
    d.line(330, 866, 330, 894, dim)
    d.line(750, 866, 750, 894, dim)
    d.text(330, 896, 420, 30, "L = 0.42 m", "code", 18, P.black, "center")

    mount = """
struct Mount {
    std::string parent = "base";
    std::string child  = "lidar";
    Vec3 xyz {0.12, 0.0, 0.31};   // metres
};"""
    d.vertex(M, 1010, 56, 5, "", ink + f"fillColor={P.blue};")
    d.text(M, 1040, 800, 210, code_html(mount, "cpp"), "code", 20, P.black)
    d.frame("assemble.", "a rover, one primitive at a time")
    return d


def export(d: Drawio) -> Path:
    src = d.save()
    svg = ROOT / "out/core" / f"{d.name}.svg"
    subprocess.run(["drawio", "-x", "-f", "svg", "-b", "0", "-o", str(svg), str(src)], check=True, capture_output=True)
    s = svg.read_text()
    text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r'(href|content|xlink:href)="[^"]*"', "", s)))
    chars = set(text)
    css = "".join(_font_face(key, chars, family) for key, family in FAMILIES.items())
    s = re.sub(r"<svg ([^>]*?)>", lambda m: _root(m.group(1)), s, count=1)
    s = s.replace("<defs/>", f"<defs><style>{css}</style></defs>", 1) if "<defs/>" in s else s.replace(
        "<defs>", f"<defs><style>{css}</style>", 1)
    svg.write_text(s)
    return svg


def _root(attrs: str) -> str:
    attrs = re.sub(r'\s(width|height|viewBox|style)="[^"]*"', "", " " + attrs)
    return f'<svg{attrs} width="{W}" height="{H}" viewBox="0 0 {W} {H}">'


if __name__ == "__main__":
    for fn in (connect, assemble):
        out = export(fn())
        print(out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")
