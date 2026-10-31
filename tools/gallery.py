#!/usr/bin/env python3
"""Write build/index.html: drafts (build/) and approved designs (designs/), open via file://."""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402

BUILD = project.BUILD
cfg = project.load_config()
style = cfg["style"]
by_id = {d["id"]: d for d in cfg["designs"]}
approved = project.approved_ids()


def kb(p: Path) -> str:
    return f"{p.stat().st_size / 1024:.0f} KB"


def card(did: str, texts: dict, folder: Path, href: str, note: str = "") -> str:
    """folder: where the files are; href: same folder relative to build/index.html."""
    sides = []
    for side in project.SIDES:
        svg, png = f"{did}-{side}.svg", f"{did}-{side}.png"
        text = "<br>".join(escape(str(l)) for l in texts.get(side, []))
        if (folder / svg).exists():
            img = f'<a href="{href}{svg}" target="_blank"><img class="art" src="{href}{svg}" alt="{did} {side}"></a>'
            dl = (f'<a href="{href}{svg}" download>SVG</a> {kb(folder / svg)} · '
                  f'<a href="{href}{png}" download>PNG</a> {kb(folder / png)}' if (folder / png).exists() else "")
        else:
            img, dl = '<div class="art missing">not rendered</div>', ""
        sides.append(f'<figure>{img}<figcaption><b>{side}</b><br><span class="txt">{text}</span><br>{dl}</figcaption></figure>')
    links = []
    for name, label in ((f"{did}-preview.jpg", "Mock-up"), (f"{did}-compare.jpg", "Foto vs. Nachbau")):
        for f, h in ((folder / name, href), (BUILD / name, "")):
            if f.exists():
                links.append(f'<a href="{h}{name}" target="_blank">{label}</a>')
                break
    note = f'<p class="note">{escape(note)}</p>' if note else ""
    return (f'<section id="{did}"><h3>{escape(did)}</h3>{note}<div class="sides">{"".join(sides)}</div>'
            f'<p class="links">{" ".join(links)}</p></section>')


drafts = [card(did, d, BUILD, "") for did, d in by_id.items() if did not in approved]
done = []
for did in sorted(approved, key=lambda i: (list(by_id).index(i) if i in by_id else 999, i)):
    m = project.read_manifest(did) or by_id.get(did, {})
    note = project.drift(did, by_id.get(did), style) or ""
    if m.get("approved"):
        note = f"approved {m['approved']}" + (f" – {note}" if note else "")
    done.append(card(did, m, project.APPROVED / did, f"../designs/{did}/", note))

misc = "".join(f'<a href="{p.name}" target="_blank">{p.name}</a> ' for p in sorted(BUILD.glob("color-candidates.png")))
nav = lambda ids: " ".join(f'<a href="#{i}">{escape(i)}</a>' for i in ids)  # noqa: E731

html = f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>Spreadshirt designs</title>
<style>
 body{{font-family:-apple-system,Helvetica,sans-serif;background:#e9e6df;margin:0;padding:24px 32px;color:#222}}
 h1{{font-weight:500}} h2{{font-weight:500;margin-top:36px}} nav a{{margin-right:10px}}
 section{{background:#fff;border-radius:10px;padding:16px 24px;margin:20px 0;box-shadow:0 1px 3px #0002}}
 .sides{{display:flex;gap:24px;flex-wrap:wrap}}
 figure{{margin:0;flex:1;min-width:320px}}
 .art{{width:100%;background:{style["shirt_color"]};padding:24px;box-sizing:border-box;border-radius:6px}}
 .missing{{color:#fff;text-align:center;padding:60px}}
 figcaption{{font-size:14px;margin-top:8px;line-height:1.5}} .txt{{color:#555}}
 .links a{{margin-right:16px}} .note{{color:#8a5a00;font-size:14px;margin:0 0 8px}}
</style>
<h1>Spreadshirt designs</h1>
<p>Textfarbe <code>{style["color"]}</code> auf Hemdfarbe <code>{style["shirt_color"]}</code> (nur Vorschau).
Bilder anklicken = SVG in Originalgröße. {misc}</p>
<h2>Entwürfe ({len(drafts)})</h2><nav>{nav(i for i in by_id if i not in approved)}</nav>
{"".join(drafts) or "<p>Keine offenen Entwürfe.</p>"}
<h2>Freigegeben ({len(done)})</h2><nav>{nav(sorted(approved))}</nav>
{"".join(done)}
</html>
"""
BUILD.mkdir(exist_ok=True)
(BUILD / "index.html").write_text(html, encoding="utf-8")
print("build/index.html")
