#!/usr/bin/env python3
"""Write build/index.html: a static gallery of everything in build/ (open via file://)."""
from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"

cfg = yaml.safe_load((ROOT / "designs.yaml").read_text(encoding="utf-8"))
style = cfg["style"]
shirt, color = style["shirt_color"], style["color"]


def size(p: Path) -> str:
    return f"{p.stat().st_size / 1024:.0f} KB"


cards = []
for d in cfg["designs"]:
    did = d["id"]
    if not (BUILD / f"{did}-front.svg").exists():
        continue
    sides = []
    for side in ("front", "back"):
        svg, png = BUILD / f"{did}-{side}.svg", BUILD / f"{did}-{side}.png"
        text = "<br>".join(escape(l) for l in d[side])
        sides.append(f"""
      <figure>
        <a href="{svg.name}" target="_blank"><img class="art" src="{svg.name}" alt="{did} {side}"></a>
        <figcaption><b>{side}</b><br><span class="txt">{text}</span><br>
          <a href="{svg.name}" download>SVG</a> {size(svg)} ·
          <a href="{png.name}" download>PNG</a> {size(png)}</figcaption>
      </figure>""")
    extra = ""
    for name, label in ((f"{did}-preview.jpg", "Mock-up"), (f"{did}-compare.jpg", "Foto vs. Nachbau")):
        if (BUILD / name).exists():
            extra += f'<a href="{name}" target="_blank">{label}</a> '
    cards.append(f"""
  <section id="{did}">
    <h2>{escape(did)}</h2>
    <div class="sides">{''.join(sides)}</div>
    <p class="links">{extra}</p>
  </section>""")

misc = "".join(f'<a href="{p.name}" target="_blank">{p.name}</a> '
               for p in sorted(BUILD.glob("*.png")) if p.stem == "color-candidates")

html = f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>Spreadshirt designs</title>
<style>
 body{{font-family:-apple-system,Helvetica,sans-serif;background:#e9e6df;margin:0;padding:24px 32px;color:#222}}
 nav a{{margin-right:12px}} h1{{font-weight:500}}
 section{{background:#fff;border-radius:10px;padding:16px 24px;margin:20px 0;box-shadow:0 1px 3px #0002}}
 .sides{{display:flex;gap:24px;flex-wrap:wrap}}
 figure{{margin:0;flex:1;min-width:320px}}
 .art{{width:100%;background:{shirt};padding:24px;box-sizing:border-box;border-radius:6px}}
 figcaption{{font-size:14px;margin-top:8px;line-height:1.5}} .txt{{color:#555}}
 .links a{{margin-right:16px}}
</style>
<h1>Spreadshirt designs</h1>
<p>Textfarbe <code>{color}</code> auf Hemdfarbe <code>{shirt}</code> (nur Vorschau).
Bilder anklicken = SVG in Originalgröße. {misc}</p>
<nav>{''.join(f'<a href="#{d["id"]}">{escape(d["id"])}</a>' for d in cfg["designs"])}</nav>
{''.join(cards)}
</html>
"""
(BUILD / "index.html").write_text(html, encoding="utf-8")
print("build/index.html")
