"""Small writer for Excalidraw files: sans font, no hand-drawn wobble (roughness 0)."""
import json
import random

INK, GREY, LINE = "#1e1e1e", "#495057", "#adb5bd"
FACT, FACT_LIGHT, DIM, BRIDGE = "#a5d8ff", "#e7f5ff", "#ffec99", "#fff3bf"
PILL = {
    "main": "#b2f2bb", "pr": "#d0bfff", "new": "#ffd8a8", "gap": "#ffc9c9", "ok": "#b2f2bb",
    "partial": "#ffd8a8", "blocked": "#ffc9c9", "none": "#f1f3f5",
}
CHAR_W = 0.55


class Drawing:
    def __init__(self, source):
        self.source = source
        self.elements = []
        self._rng = random.Random(145)
        self._n = 0

    def _base(self, kind, x, y, w, h, stroke=INK, bg="transparent", stroke_width=1, stroke_style="solid"):
        self._n += 1
        return {
            "id": f"e{self._n}", "type": kind, "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid", "strokeWidth": stroke_width,
            "strokeStyle": stroke_style, "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": None, "seed": self._rng.randint(1, 2**31 - 1), "version": 1,
            "versionNonce": self._rng.randint(1, 2**31 - 1), "isDeleted": False, "boundElements": None,
            "updated": 1793000000000, "link": None, "locked": False,
        }

    def text(self, x, y, s, size=16, color=INK, align="left", bold=False):
        lines = s.split("\n")
        w = max(len(l) for l in lines) * size * CHAR_W
        h = len(lines) * size * 1.25
        if align == "center":
            x = x - w / 2
        e = self._base("text", x, y, w, h, stroke=color)
        e.update({"text": s, "fontSize": size, "fontFamily": 2, "textAlign": align, "verticalAlign": "top",
                  "containerId": None, "originalText": s, "autoResize": True, "lineHeight": 1.25})
        self.elements.append(e)
        return e

    def rect(self, x, y, w, h, bg="transparent", stroke=INK, stroke_width=2, dashed=False):
        e = self._base("rectangle", x, y, w, h, stroke=stroke, bg=bg, stroke_width=stroke_width,
                       stroke_style="dashed" if dashed else "solid")
        self.elements.append(e)
        return e

    def line(self, x1, y1, x2, y2, color=LINE, width=1, arrow=False, dashed=False):
        e = self._base("arrow" if arrow else "line", x1, y1, x2 - x1, y2 - y1, stroke=color,
                       stroke_width=width, stroke_style="dashed" if dashed else "solid")
        e.update({"points": [[0, 0], [x2 - x1, y2 - y1]], "lastCommittedPoint": None, "startBinding": None,
                  "endBinding": None, "startArrowhead": None, "endArrowhead": "arrow" if arrow else None})
        self.elements.append(e)
        return e

    def pill(self, x, y, label, kind, size=13):
        w = len(label) * size * CHAR_W + 16
        self.rect(x, y, w, size * 1.7, bg=PILL[kind], stroke_width=1)
        self.text(x + 8, y + size * 0.22, label, size=size)
        return w

    def save(self, path):
        doc = {"type": "excalidraw", "version": 2, "source": self.source, "elements": self.elements,
               "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20}, "files": {}}
        with open(path, "w") as f:
            json.dump(doc, f, indent=1)
