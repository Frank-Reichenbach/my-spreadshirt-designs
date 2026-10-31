#!/usr/bin/env python3
"""Build the GitHub Pages site in docs/ from the approved designs.

Only approved designs (designs/<id>/ with approved.yaml) are published.
The script owns these paths in docs/ and rewrites them on every run:
  index.html (English), de/index.html (German), style.css, sitemap.xml,
  favicon.svg, og-image.png, .nojekyll, fonts/, designs/
Everything else in docs/ (e.g. pattern.md) is left untouched.

No JavaScript, no third-party code, no external requests and nothing stored
in the visitor's browser: fonts, images and styles are all served from the site
itself. The light/dark switch works with CSS alone (per page view); by default
the site follows the system setting.
"""
from __future__ import annotations

import html
import io
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402
import render  # noqa: E402

ROOT = project.ROOT
DOCS = ROOT / "docs"
SITE = yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8"))
URL = SITE["url"].rstrip("/") + "/"
LASTMOD = ""  # set in main()
SITE_STYLE: dict = {}  # set in main()
REPO = SITE["repo"]

esc = html.escape


# --------------------------------------------------------------------------- data
def published_designs() -> list[dict]:
    cfg = project.load_config()
    order = [d["id"] for d in cfg["designs"]]
    approved = project.approved_ids()
    ids = [i for i in order if i in approved] + sorted(approved - set(order))
    out = []
    for did in ids:
        m = project.read_manifest(did)
        if not m:
            print(f"warning: {did}: no approved.yaml, not published", file=sys.stderr)
            continue
        out.append({"id": did, "front": m["front"], "back": m["back"], "style": m["style"],
                    "approved": str(m.get("approved") or date.today().isoformat())})
    return out


def one_line(lines: list[str]) -> str:
    return " ".join(str(l).strip() for l in lines)


# ------------------------------------------------------------------------- assets
def shirt_tile(png: Path, shirt: str, width: int = 720) -> Image.Image:
    """Design on a shirt-coloured panel (4:5), like a print area on the chest/back."""
    art = Image.open(png).convert("RGBA")
    w, h = width, round(width * 1.25)
    tile = Image.new("RGB", (w, h), shirt)
    scale = (w * 0.86) / art.width
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    if art.height > h * 0.88:  # very tall backs
        s2 = h * 0.88 / art.height
        art = art.resize((round(art.width * s2), round(art.height * s2)), Image.LANCZOS)
    tile.paste(art, ((w - art.width) // 2, round(h * 0.08)), art)
    return tile


def build_design_assets(d: dict) -> dict:
    src = project.APPROVED / d["id"]
    dst = DOCS / "designs" / d["id"]
    dst.mkdir(parents=True, exist_ok=True)
    files = {}
    for side in project.SIDES:
        for ext in ("svg", "png"):
            name = f"{d['id']}-{side}.{ext}"
            shutil.copy2(src / name, dst / name)
            files[f"{side}_{ext}"] = f"designs/{d['id']}/{name}"
        tile = shirt_tile(src / f"{d['id']}-{side}.png", d["style"]["shirt_color"])
        tile.save(dst / f"{d['id']}-{side}.webp", "WEBP", quality=82, method=6)
        tile.save(dst / f"{d['id']}-{side}.jpg", "JPEG", quality=84, optimize=True, progressive=True)
        files[f"{side}_webp"] = f"designs/{d['id']}/{d['id']}-{side}.webp"
        files[f"{side}_jpg"] = f"designs/{d['id']}/{d['id']}-{side}.jpg"
        files["tile_size"] = tile.size
    return files


def static_font(weight: float) -> TTFont:
    tt = TTFont(ROOT / "fonts" / "Caveat[wght].ttf")
    return instantiateVariableFont(tt, {"wght": weight})


def build_font(texts: list[str], weight: float) -> str:
    """Caveat subset (static instance) as WOFF2, only the glyphs the page needs."""
    chars = set("".join(texts)) | set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,’'…-–!?")
    tt = static_font(weight)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)))
    sub.subset(tt)
    (DOCS / "fonts").mkdir(exist_ok=True)
    out = DOCS / "fonts" / "caveat-subset.woff2"
    tt.flavor = "woff2"
    tt.save(out)
    shutil.copy2(ROOT / "fonts" / "Caveat-OFL.txt", DOCS / "fonts" / "Caveat-OFL.txt")
    return "fonts/caveat-subset.woff2"


def build_favicon(style: dict):
    ts = render.Typesetter(ROOT / style["font"], style["weight"])
    side = render.Side(cap_height_mm=20, line_pitch_mm=30, width_mm=32, max_text_width_mm=30)
    paths, w, h, _ = render.layout(ts, ["W"], side)
    d = " ".join(render.svg_d(p) for p in paths)
    oy = (32 - h) / 2 + 1.5
    (DOCS / "favicon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        f'<rect width="32" height="32" rx="7" fill="{style["shirt_color"]}"/>'
        f'<path transform="translate(0 {oy:.2f})" fill="{style["color"]}" d="{d}"/></svg>\n')


def build_og_image(designs: list[dict], style: dict):
    """1200x630 social preview: title + one front/back pair."""
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), style["shirt_color"])
    font_bytes = io.BytesIO()
    static_font(style["weight"]).save(font_bytes)
    font_bytes.seek(0)
    big = ImageFont.truetype(io.BytesIO(font_bytes.getvalue()), 96)
    small = ImageFont.truetype(io.BytesIO(font_bytes.getvalue()), 44)
    dr = ImageDraw.Draw(img)
    dr.text((70, 150), "We should", font=big, fill=style["color"])
    dr.text((70, 260), "… more", font=big, fill=style["color"])
    dr.text((72, 420), f"{len(designs)} free T-shirt designs · CC0", font=small, fill=style["color"])
    hug = next((d for d in designs if d["id"] == "hug"), designs[0])
    art = Image.open(project.APPROVED / hug["id"] / f"{hug['id']}-back.png").convert("RGBA")
    art.thumbnail((470, 520), Image.LANCZOS)
    img.paste(art, (W - art.width - 70, (H - art.height) // 2), art)
    img.save(DOCS / "og-image.png", optimize=True)


# --------------------------------------------------------------------------- i18n
LANGS = {
    "en": {"dir": "", "prefix": "", "locale": "en_US", "name": "English", "short": "EN"},
    "de": {"dir": "de/", "prefix": "../", "locale": "de_DE", "name": "Deutsch", "short": "DE"},
}

T = {
    "en": {
        "title": "We should … more – free T-shirt designs (CC0)",
        "description": "{n} friendly, text-only T-shirt designs: a gentle call on the front, a shrug on the back. Free SVG and PNG downloads, public domain (CC0).",
        "lead": "{n} friendly, text-only T-shirt designs. A gentle call on the front, a shrug on the back – light, a little ironic, never preachy.",
        "free": 'Free for everyone: no rights reserved (<a href="{lic}">CC0</a>). Print them, change them, sell them.',
        "badges": ["{n} front &amp; back pairs", "Vector SVG + 300 dpi PNG", "CC0 – public domain"],
        "designs_h": "The designs",
        "pattern": "Every shirt follows the same pattern: <strong>“We should &lt;something&gt; more”</strong> on the front, <strong>“I’m not saying that it solves anything, but …”</strong> on the back. Topics: {verbs}.",
        "front": "Front", "back": "Back", "download": "Download:",
        "alt_front": "T-shirt front: {t}", "alt_back": "T-shirt back: {t}",
        "use_h": "How to use them",
        "steps": [
            "Download the <strong>SVG</strong> files (vector, one colour, real size in millimetres). They suit flex or flock printing, which is durable on sports shirts. Use the <strong>PNG</strong> files (transparent, 300 dpi) for digital printing.",
            "Upload front and back to the print-on-demand shop of your choice, for example Spreadshirt, and check its current upload requirements.",
            "Recommended look: text colour <code>{color}</code> (warm off-white) on a royal-blue shirt. All fronts share one canvas width ({width} cm), all backs too – scale every design of one side to the same width and the series stays consistent.",
            'Want your own verb? The <a href="{repo}">generator in the repository</a> renders new texts in the same style.',
        ],
        "note": "<strong>Please note:</strong> CC0 covers the copyright in these designs only. It does not grant any trademark rights. Some short phrases may be registered as trademarks for clothing by third parties in some countries – check before selling merchandise.",
        "theme": "Theme", "system": "System", "light": "Light", "dark": "Dark",
        "lang_nav": "Language",
        "f_designs": "Designs", "f_source": "Source on GitHub", "f_license": "License",
        "f_text": "Designs and texts: CC0 1.0 (public domain). Font: Caveat, SIL Open Font License 1.1. No cookies, no tracking, no external resources, nothing is stored in your browser.",
        "og_alt": "We should … more – {n} free T-shirt designs",
    },
    "de": {
        "title": "We should … more – kostenlose T-Shirt-Designs (CC0)",
        "description": "{n} freundliche T-Shirt-Designs nur aus Text: vorne ein sanfter Aufruf, hinten ein Schulterzucken. Kostenlose SVG- und PNG-Downloads, gemeinfrei (CC0).",
        "lead": "{n} freundliche T-Shirt-Designs nur aus Text. Vorne ein sanfter Aufruf, hinten ein Schulterzucken – leicht, ein bisschen ironisch, nie belehrend.",
        "free": 'Frei für alle: keine Rechte vorbehalten (<a href="{lic}">CC0</a>). Drucken, verändern, verkaufen – alles erlaubt.',
        "badges": ["{n} Paare Vorder- &amp; Rückseite", "Vektor-SVG + PNG mit 300 dpi", "CC0 – gemeinfrei"],
        "designs_h": "Die Designs",
        "pattern": 'Jedes Shirt folgt demselben Muster: vorne <strong lang="en">„We should &lt;something&gt; more“</strong>, hinten <strong lang="en">„I’m not saying that it solves anything, but …“</strong>. Themen: <span lang="en">{verbs}</span>.',
        "front": "Vorne", "back": "Hinten", "download": "Download:",
        "alt_front": "T-Shirt-Vorderseite: {t}", "alt_back": "T-Shirt-Rückseite: {t}",
        "use_h": "So nutzt du sie",
        "steps": [
            "Lade die <strong>SVG</strong>-Dateien herunter (Vektor, einfarbig, echte Größe in Millimetern). Sie eignen sich für Flex- oder Flockdruck, der auf Sportshirts besonders haltbar ist. Für Digitaldruck nimmst du die <strong>PNG</strong>-Dateien (transparent, 300 dpi).",
            "Lade Vorder- und Rückseite beim Print-on-Demand-Anbieter deiner Wahl hoch, zum Beispiel bei Spreadshirt, und prüfe dessen aktuelle Upload-Anforderungen.",
            "Empfohlener Look: Textfarbe <code>{color}</code> (warmes Off-White) auf einem königsblauen Shirt. Alle Vorderseiten haben dieselbe Breite ({width} cm), alle Rückseiten ebenso – skaliere alle Designs einer Seite auf dieselbe Breite, dann bleibt die Serie einheitlich.",
            'Lust auf ein eigenes Verb? Der <a href="{repo}">Generator im Repository</a> setzt neue Texte im selben Stil.',
        ],
        "note": "<strong>Bitte beachten:</strong> CC0 betrifft nur das Urheberrecht an diesen Designs. Markenrechte werden damit nicht eingeräumt. Manche kurzen Sprüche können in einigen Ländern von Dritten als Marke für Kleidung eingetragen sein – prüfe das, bevor du Merchandise verkaufst.",
        "theme": "Darstellung", "system": "System", "light": "Hell", "dark": "Dunkel",
        "lang_nav": "Sprache",
        "f_designs": "Designs", "f_source": "Quellcode auf GitHub", "f_license": "Lizenz",
        "f_text": "Designs und Texte: CC0 1.0 (gemeinfrei). Schrift: Caveat, SIL Open Font License 1.1. Keine Cookies, kein Tracking, keine externen Inhalte, nichts wird in deinem Browser gespeichert.",
        "og_alt": "We should … more – {n} kostenlose T-Shirt-Designs",
    },
}

# --------------------------------------------------------------------------- html
LIGHT = "--paper:#f6f3ec;--card:#fff;--ink:#1d2433;--muted:#5a6272;--line:#e2ddd2;--link:%(blue)s;--quote:#f6f3ec;--code:#ece7dc;--hero:%(blue)s;color-scheme:light"
DARK = "--paper:#11151d;--card:#1a202c;--ink:#e9e6df;--muted:#a4abb8;--line:#2d3546;--link:#9dbbff;--quote:#232a38;--code:#2a3242;--hero:#173e7c;color-scheme:dark"

CSS = """@font-face{font-family:"Caveat";src:url("fonts/caveat-subset.woff2") format("woff2");font-weight:400 700;font-display:swap}
:root{--blue:%(blue)s;--cream:%(cream)s;""" + LIGHT + """}
@media (prefers-color-scheme:dark){:root{""" + DARK + """}}
:root:has(#theme-light:checked){""" + LIGHT + """}
:root:has(#theme-dark:checked){""" + DARK + """}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%%}
body{margin:0;font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--paper)}
a{color:var(--link)} a:focus-visible,input:focus-visible+label{outline:3px solid var(--link);outline-offset:2px}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
header.hero{background:var(--hero);color:var(--cream);padding:20px 0 48px}
.topbar{display:flex;flex-wrap:wrap;justify-content:flex-end;align-items:center;gap:10px 22px;margin-bottom:28px;font-size:.92rem}
.topbar a{color:var(--cream)} .hero a:focus-visible,.hero input:focus-visible+label{outline-color:var(--cream)}
.langs{display:flex;gap:10px;margin:0;padding:0;list-style:none}
.langs [aria-current]{font-weight:700;text-decoration:none}
.theme{border:0;margin:0;padding:0;display:flex;align-items:center;gap:4px}
.theme legend{float:left;margin-right:8px}
.theme input{position:absolute;opacity:0;width:1px;height:1px}
.theme label{border:1px solid color-mix(in srgb,var(--cream) 55%%,transparent);border-radius:999px;padding:2px 11px;cursor:pointer}
.theme input:checked+label{background:var(--cream);color:var(--hero)}
@supports not selector(:has(*)){.theme{display:none}}
.hand{font-family:"Caveat","Segoe Print","Bradley Hand",cursive;font-weight:560}
.hero h1{font-size:clamp(3rem,9vw,5.5rem);line-height:1;margin:0 0 .3em}
.hero p{max-width:40em;font-size:1.15rem;margin:.4em 0}
.hero p a{color:var(--cream)}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px;padding:0;list-style:none}
.badges li{border:1px solid color-mix(in srgb,var(--cream) 55%%,transparent);border-radius:999px;padding:3px 12px;font-size:.9rem}
main section{padding:40px 0 8px}
h2{font-size:1.6rem;margin:0 0 .6em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(330px,100%%),1fr));gap:24px;padding:0;list-style:none}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card h3{font-size:2.1rem;line-height:1.1;margin:0;padding:18px 20px 4px;color:var(--link)}
.sides{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px 16px}
.sides figure{margin:0}
.sides img{width:100%%;height:auto;display:block;border-radius:8px}
.sides figcaption{font-size:.8rem;color:var(--muted);text-align:center;margin-top:4px}
.back{margin:0 20px;padding:10px 14px;border-left:3px solid var(--link);background:var(--quote);border-radius:0 8px 8px 0}
.dl{display:flex;flex-wrap:wrap;gap:6px 14px;padding:14px 20px 18px;margin-top:auto;font-size:.92rem}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.steps{padding-left:1.2em} .steps li{margin:.35em 0}
.note{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px}
code{background:var(--code);border-radius:4px;padding:1px 5px;font-size:.92em}
footer{margin-top:48px;border-top:1px solid var(--line);padding:24px 0 40px;color:var(--muted);font-size:.92rem}
footer nav{display:flex;flex-wrap:wrap;gap:6px 18px;margin-bottom:8px}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""


def page_url(lang: str) -> str:
    return URL + LANGS[lang]["dir"]


def head(lang: str, n: int, extra: str) -> str:
    t, p = T[lang], LANGS[lang]["prefix"]
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{page_url(l)}">\n' for l in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{page_url("en")}">\n'
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(t['title'])}</title>
<meta name="description" content="{esc(t['description'].format(n=n))}">
<link rel="canonical" href="{page_url(lang)}">
{alts}<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="{SITE_STYLE['shirt_color']}">
<link rel="icon" href="{p}favicon.svg" type="image/svg+xml">
<link rel="preload" href="{p}fonts/caveat-subset.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{p}style.css">
{extra}</head>
"""


def topbar(lang: str) -> str:
    t = T[lang]
    langs = "".join(
        # explicit index.html: works on GitHub Pages and when opened as local files
        f'<li><a href="{LANGS[lang]["prefix"]}{LANGS[l]["dir"]}index.html" hreflang="{l}" lang="{l}"'
        + (' aria-current="page"' if l == lang else "") + f'>{LANGS[l]["name"]}</a></li>'
        for l in LANGS)
    radios = "".join(
        f'<input type="radio" name="theme" id="theme-{v}" value="{v}"{" checked" if v == "system" else ""}>'
        f'<label for="theme-{v}">{t[v]}</label>' for v in ("system", "light", "dark"))
    return (f'<div class="topbar"><nav aria-label="{t["lang_nav"]}"><ul class="langs">{langs}</ul></nav>'
            f'<fieldset class="theme"><legend>{t["theme"]}</legend>{radios}</fieldset></div>')


def footer(lang: str) -> str:
    t = T[lang]
    return f"""<footer><div class="wrap">
<nav aria-label="Footer">
<a href="#top">{t['f_designs']}</a>
<a href="{REPO}">{t['f_source']}</a>
<a href="{REPO}/blob/main/LICENSE.md">{t['f_license']}</a>
</nav>
<p>{t['f_text']}</p>
</div></footer>
"""


def card(d: dict, f: dict, eager: bool, lang: str) -> str:
    t, p = T[lang], LANGS[lang]["prefix"]
    front, back = one_line(d["front"]), one_line(d["back"])
    tw, th = f["tile_size"]
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'

    def pic(side: str, alt: str) -> str:
        return (f'<picture><source srcset="{p}{f[side + "_webp"]}" type="image/webp">'
                f'<img src="{p}{f[side + "_jpg"]}" width="{tw}" height="{th}" {loading} decoding="async" alt="{esc(alt)}">'
                f'</picture>')

    def dl(key: str, label: str) -> str:
        return f'<a href="{p}{f[key]}" download>{label}<span class="vh"> – {esc(front)}</span></a>'

    fr, bk = t["front"], t["back"]
    return f"""<li class="card" id="{d['id']}">
<h3 class="hand" lang="en">{esc(front)}</h3>
<div class="sides">
<figure>{pic("front", t["alt_front"].format(t=front))}<figcaption>{fr}</figcaption></figure>
<figure>{pic("back", t["alt_back"].format(t=back))}<figcaption>{bk}</figcaption></figure>
</div>
<p class="back" lang="en">{esc(back)}</p>
<p class="dl">{t['download']}
{dl("front_svg", f"{fr} SVG")}
{dl("back_svg", f"{bk} SVG")}
{dl("front_png", f"{fr} PNG")}
{dl("back_png", f"{bk} PNG")}</p>
</li>"""


def jsonld(designs: list[dict], files: dict, lang: str) -> str:
    imgs = []
    for d in designs:
        for side in project.SIDES:
            imgs.append({
                "@type": "ImageObject",
                "name": f"{one_line(d['front'])} – {side}",
                "description": one_line(d[side]),
                "contentUrl": URL + files[d["id"]][f"{side}_png"],
                "license": "https://creativecommons.org/publicdomain/zero/1.0/",
                "acquireLicensePage": f"{REPO}/blob/main/LICENSE.md",
                "creditText": SITE["author"],
                "creator": {"@type": "Person", "name": SITE["author"]},
                "copyrightNotice": "CC0 1.0 – no rights reserved",
            })
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": T[lang]["title"],
        "description": T[lang]["description"].format(n=len(designs)),
        "url": page_url(lang),
        "inLanguage": lang,
        "dateModified": LASTMOD,
        "author": {"@type": "Person", "name": SITE["author"]},
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "hasPart": imgs,
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>\n"


def build_index(designs: list[dict], files: dict, style: dict, lang: str):
    t, n = T[lang], len(designs)
    lic = f"{REPO}/blob/main/LICENSE.md"
    others = "".join(f'<meta property="og:locale:alternate" content="{LANGS[l]["locale"]}">\n' for l in LANGS if l != lang)
    og = f"""<meta property="og:type" content="website">
<meta property="og:title" content="{esc(t['title'])}">
<meta property="og:description" content="{esc(t['description'].format(n=n))}">
<meta property="og:url" content="{page_url(lang)}">
<meta property="og:locale" content="{LANGS[lang]['locale']}">
{others}<meta property="og:image" content="{URL}og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(t['og_alt'].format(n=n))}">
<meta name="twitter:card" content="summary_large_image">
{jsonld(designs, files, lang)}"""
    cards = "\n".join(card(d, files[d["id"]], i < 2, lang) for i, d in enumerate(designs))
    verbs = ", ".join(d["id"] for d in designs)
    badges = "".join(f"<li>{b.format(n=n)}</li>" for b in t["badges"])
    width = f"{style['front']['width_mm'] / 10:g}"
    steps = "".join(f"<li>{s.format(color=esc(style['color']), width=width, repo=REPO)}</li>" for s in t["steps"])
    page = head(lang, n, og) + f"""<body id="top">
<header class="hero"><div class="wrap">
{topbar(lang)}
<h1 class="hand" lang="en">We should … more</h1>
<p>{t['lead'].format(n=n)}</p>
<p>{t['free'].format(lic=lic)}</p>
<ul class="badges">{badges}</ul>
</div></header>
<main class="wrap">
<section aria-labelledby="designs-h">
<h2 id="designs-h">{t['designs_h']}</h2>
<p>{t['pattern'].format(verbs=esc(verbs))}</p>
<ul class="grid">
{cards}
</ul>
</section>
<section aria-labelledby="use-h">
<h2 id="use-h">{t['use_h']}</h2>
<ol class="steps">{steps}</ol>
<div class="note"><p>{t['note']}</p></div>
</section>
</main>
""" + footer(lang) + "</body>\n</html>\n"
    out = DOCS / LANGS[lang]["dir"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def build_meta():
    (DOCS / ".nojekyll").write_text("")
    # robots.txt is only read at the host root (not under /<repo>/), so none is written;
    # submit sitemap.xml in Google Search Console / Bing Webmaster Tools instead.
    alts = "".join(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{page_url(l)}"/>\n' for l in LANGS)
    alts += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{page_url("en")}"/>\n'
    urls = "".join(f"  <url>\n    <loc>{page_url(l)}</loc>\n    <lastmod>{LASTMOD}</lastmod>\n{alts}  </url>\n" for l in LANGS)
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        f"{urls}</urlset>\n")


def main():
    global LASTMOD, SITE_STYLE
    designs = published_designs()
    if not designs:
        sys.exit("error: no approved designs to publish")
    LASTMOD = max(d["approved"] for d in designs)  # stable: changes only when designs change
    style = SITE_STYLE = designs[0]["style"]
    DOCS.mkdir(exist_ok=True)
    shutil.rmtree(DOCS / "designs", ignore_errors=True)  # owned by this script
    files = {d["id"]: build_design_assets(d) for d in designs}
    texts = ["We should … more"] + [one_line(d["front"]) for d in designs]
    build_font(texts, style["weight"])
    (DOCS / "style.css").write_text(CSS % {"blue": style["shirt_color"], "cream": style["color"]})
    build_favicon(style)
    build_og_image(designs, style)
    for lang in LANGS:
        build_index(designs, files, style, lang)
    build_meta()
    size = sum(p.stat().st_size for p in DOCS.rglob("*") if p.is_file())
    print(f"docs/: {len(designs)} designs, {len(LANGS)} languages, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
