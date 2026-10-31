#!/usr/bin/env python3
"""Render text-only T-shirt designs from designs.yaml.

For every design and side (front/back) this writes to the build directory:
  <id>-<side>.svg          vector, text converted to outlined paths, one fill colour
  <id>-<side>.png          transparent bitmap at the configured dpi
  <id>-preview.jpg         front + back mock-up on the shirt colour (for approval)

Usage:
  python tools/render.py                 # all designs
  python tools/render.py hug smile       # selected ids
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import skia
import uharfbuzz as hb
import yaml
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import OverlapMode, instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
MM_PER_INCH = 25.4


@dataclass
class Side:
    cap_height_mm: float   # height of a capital letter -> defines the font size
    line_pitch_mm: float   # baseline-to-baseline distance
    width_mm: float        # fixed canvas width (identical for every design of this side)
    max_text_width_mm: float


class Typesetter:
    def __init__(self, font_path: Path, weight: float):
        tt = TTFont(font_path)
        if "fvar" in tt:
            # merge overlapping contours: needed for clean plot (flex/flock) cutting
            tt = instantiateVariableFont(tt, {"wght": weight}, overlap=OverlapMode.REMOVE)
        self.tt = tt
        self.glyphs = tt.getGlyphSet()
        self.upem = tt["head"].unitsPerEm
        self.cap = tt["OS/2"].sCapHeight
        blob = hb.Blob.from_file_path(str(font_path))
        self.hb_font = hb.Font(hb.Face(blob))
        self.hb_font.set_variations({"wght": weight})

    def shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": True, "calt": True})
        order = self.tt.getGlyphOrder()
        x, out = 0, []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((order[info.codepoint], x + pos.x_offset, pos.y_offset))
            x += pos.x_advance
        return out, x  # glyph placements in font units, total advance

    def line_outline(self, text: str, scale: float, x0: float, baseline: float) -> RecordingPen:
        """Outline of one line in mm (y pointing down), recorded for SVG and raster output."""
        glyphs, _ = self.shape(text)
        rec = RecordingPen()
        for name, gx, gy in glyphs:
            t = (scale, 0, 0, -scale, x0 + gx * scale, baseline - gy * scale)
            self.glyphs[name].draw(TransformPen(rec, t))
        return rec


class SkiaPen(BasePen):
    def __init__(self):
        super().__init__(None)
        self.path = skia.Path()

    def _moveTo(self, p):
        self.path.moveTo(*p)

    def _lineTo(self, p):
        self.path.lineTo(*p)

    def _curveToOne(self, p1, p2, p3):
        self.path.cubicTo(*p1, *p2, *p3)

    def _qCurveToOne(self, p1, p2):
        self.path.quadTo(*p1, *p2)

    def _closePath(self):
        self.path.close()


def svg_d(rec: RecordingPen) -> str:
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.3f}".rstrip("0").rstrip("."))
    rec.replay(pen)
    return pen.getCommands()


def layout(ts: Typesetter, lines: list[str], side: Side):
    """Return (paths, width_mm, height_mm)."""
    scale = side.cap_height_mm / ts.cap  # mm per font unit
    widest = max(ts.shape(l)[1] for l in lines) * scale
    shrink = min(1.0, side.max_text_width_mm / widest)  # only when a line is too long
    if shrink < 1:
        print(f"  note: shrinking text to {shrink:.0%} to fit {side.max_text_width_mm} mm", file=sys.stderr)
    scale *= shrink
    cap = ts.cap * scale
    pitch = side.line_pitch_mm * shrink
    desc = 0.32 * ts.upem * scale  # room for g/y descenders below the last line
    top = 0.35 * cap               # room for ascenders (l, d, h) above cap height
    height = top + cap + pitch * (len(lines) - 1) + desc
    paths = []
    for i, line in enumerate(lines):
        adv = ts.shape(line)[1] * scale
        baseline = top + cap + i * pitch
        paths.append(ts.line_outline(line, scale, (side.width_mm - adv) / 2, baseline))
    return paths, side.width_mm, height


def write_svg(path: Path, paths: list[RecordingPen], w: float, h: float, color: str):
    d = " ".join(svg_d(p) for p in paths)
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" '
        f'viewBox="0 0 {w:.3f} {h:.3f}">\n'
        f'  <path fill="{color}" fill-rule="nonzero" d="{d}"/>\n'
        f"</svg>\n"
    )


def rasterize(paths: list[RecordingPen], w: float, h: float, color: str, dpi: int,
              background: str | None = None) -> skia.Image:
    px = dpi / MM_PER_INCH
    surface = skia.Surface(round(w * px), round(h * px))
    canvas = surface.getCanvas()
    canvas.clear(skia.Color4f.FromColor(hex_color(background)) if background else skia.ColorTRANSPARENT)
    canvas.scale(px, px)
    paint = skia.Paint(AntiAlias=True, Color=hex_color(color))
    for rec in paths:
        pen = SkiaPen()
        rec.replay(pen)
        canvas.drawPath(pen.path, paint)
    return surface.makeImageSnapshot()


def hex_color(c: str) -> int:
    c = c.lstrip("#")
    return skia.ColorSetARGB(255, int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def write_png(img: skia.Image, path: Path, dpi: int):
    # skia does not write a pHYs chunk; re-save via Pillow to embed the dpi.
    from PIL import Image
    pil = Image.frombytes("RGBA", (img.width(), img.height()),
                          img.toarray(colorType=skia.kRGBA_8888_ColorType,
                                      alphaType=skia.kUnpremul_AlphaType).tobytes())
    pil.save(path, dpi=(dpi, dpi), optimize=True)


def preview(front, back, style, out: Path):
    """Simple mock-up: front and back side by side on shirt-coloured panels."""
    from PIL import Image, ImageDraw
    dpi = 40
    panel_w, panel_h = round(520 / 25.4 * dpi), round(700 / 25.4 * dpi)  # ~ size L torso
    sheet = Image.new("RGB", (panel_w * 2 + 60, panel_h + 40), "#e9e6df")
    for i, (paths, w, h, top_mm) in enumerate([(*front, style["front_offset_mm"]),
                                                (*back, style["back_offset_mm"])]):
        panel = Image.new("RGB", (panel_w, panel_h), style["shirt_color"])
        ImageDraw.Draw(panel).ellipse((panel_w * 0.33, -panel_w * 0.12, panel_w * 0.67,
                                       panel_w * (0.10 if i == 0 else 0.04)), fill="#e9e6df")
        art = rasterize(paths, w, h, style["color"], dpi * 2)
        a = Image.frombytes("RGBA", (art.width(), art.height()),
                            art.toarray(colorType=skia.kRGBA_8888_ColorType,
                                        alphaType=skia.kUnpremul_AlphaType).tobytes())
        a = a.resize((a.width // 2, a.height // 2), Image.LANCZOS)
        panel.paste(a, ((panel_w - a.width) // 2, round(top_mm / 25.4 * dpi)), a)
        sheet.paste(panel, (20 + i * (panel_w + 20), 20))
    sheet.save(out, quality=90)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="design ids to render (default: all)")
    ap.add_argument("--config", default=ROOT / "designs.yaml", type=Path)
    ap.add_argument("--out", default=ROOT / "build", type=Path)
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    style = cfg["style"]
    ts = Typesetter(ROOT / style["font"], style["weight"])
    sides = {k: Side(**style[k]) for k in ("front", "back")}
    designs = [d for d in cfg["designs"] if not args.ids or d["id"] in args.ids]
    if args.ids and len(designs) != len(set(args.ids)):
        sys.exit(f"unknown id(s): {set(args.ids) - {d['id'] for d in designs}}")

    args.out.mkdir(parents=True, exist_ok=True)
    for d in designs:
        results = {}
        for side in ("front", "back"):
            paths, w, h = layout(ts, d[side], sides[side])
            base = args.out / f"{d['id']}-{side}"
            write_svg(base.with_suffix(".svg"), paths, w, h, style["color"])
            write_png(rasterize(paths, w, h, style["color"], style["dpi"]), base.with_suffix(".png"), style["dpi"])
            results[side] = (paths, w, h)
            print(f"{base.name}: {w:.0f} x {h:.0f} mm")
        preview(results["front"], results["back"], style, args.out / f"{d['id']}-preview.jpg")


if __name__ == "__main__":
    main()
