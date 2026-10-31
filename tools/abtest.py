#!/usr/bin/env python3
"""Blind A/B test of two text colours in the browser.

Renders every design side in both colours on the shirt colour, serves a small
page on http://localhost:8765 and records each click in build/abtest/results.json.

Approved designs are left out unless --include-approved is given.

Usage: python tools/abtest.py "#F5F1E8" "#FFF8E7" [--shirt "#1F4E9C"] [--include-approved]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402

ROOT = render.ROOT
OUT = ROOT / "build" / "abtest"


def to_pil(img):
    import skia
    return Image.frombytes("RGBA", (img.width(), img.height()),
                           img.toarray(colorType=skia.kRGBA_8888_ColorType,
                                       alphaType=skia.kUnpremul_AlphaType).tobytes())


def build_images(colors, shirt, include_approved=False):
    cfg = yaml.safe_load((ROOT / "designs.yaml").read_text(encoding="utf-8"))
    approved = set() if include_approved else render.project.approved_ids()
    style = cfg["style"]
    ts = render.Typesetter(ROOT / style["font"], style["weight"])
    sides = {k: render.Side(**style[k]) for k in ("front", "back")}
    trials = []
    OUT.mkdir(parents=True, exist_ok=True)
    for d in cfg["designs"]:
        if d["id"] in approved:
            continue
        for side in ("front", "back"):
            paths, w, h, _ = render.layout(ts, d[side], sides[side])
            entry = {"id": f"{d['id']}-{side}", "images": {}}
            for key, col in zip("AB", colors):
                art = to_pil(render.rasterize(paths, w, h, col, 60))
                pad = 60
                tile = Image.new("RGB", (art.width + 2 * pad, art.height + 2 * pad), shirt)
                tile.paste(art, (pad, pad), art)
                name = f"{entry['id']}-{key}.png"
                tile.save(OUT / name)
                entry["images"][key] = name
            trials.append(entry)
    return trials


PAGE = """<!doctype html><html lang="de"><meta charset="utf-8">
<title>Farbtest</title>
<style>
 body{font-family:-apple-system,Helvetica,sans-serif;background:#e9e6df;margin:0;padding:24px;text-align:center}
 h1{font-weight:500;font-size:20px} #prog{color:#666}
 .pair{display:flex;gap:24px;justify-content:center;align-items:center;margin-top:16px}
 .pair img{max-width:46vw;max-height:72vh;cursor:pointer;border:4px solid transparent;border-radius:6px}
 .pair img:hover{border-color:#333}
 table{margin:24px auto;border-collapse:collapse} td,th{padding:6px 14px;border-bottom:1px solid #ccc}
 .sw{display:inline-block;width:14px;height:14px;border:1px solid #999;vertical-align:middle}
</style>
<h1>Welche Schrift gefällt dir besser? Einfach klicken.</h1>
<div id="prog"></div><div class="pair" id="pair"></div><div id="res"></div>
<script>
const T=__TRIALS__, C=__COLORS__;
// shuffle order of trials and left/right position (blind test)
T.sort(()=>Math.random()-.5);
let i=0, picks=[];
function show(){
  if(i>=T.length) return done();
  const t=T[i], keys=Math.random()<.5?['A','B']:['B','A'];
  document.getElementById('prog').textContent=`${i+1} / ${T.length}`;
  const p=document.getElementById('pair'); p.innerHTML='';
  keys.forEach(k=>{const im=new Image(); im.src=t.images[k];
    im.onclick=()=>{picks.push({trial:t.id,choice:k,position:keys.indexOf(k)?'right':'left'});
      fetch('/result',{method:'POST',body:JSON.stringify(picks.at(-1))}); i++; show();};
    p.appendChild(im);});
}
function done(){
  document.getElementById('pair').innerHTML=''; document.getElementById('prog').textContent='Fertig – danke!';
  const n={A:0,B:0}; picks.forEach(p=>n[p.choice]++);
  document.getElementById('res').innerHTML=`<table><tr><th></th><th>Farbe</th><th>Stimmen</th></tr>`+
   ['A','B'].map(k=>`<tr><td>${k}</td><td><span class=sw style="background:${C[k]}"></span> ${C[k]}</td><td>${n[k]}</td></tr>`).join('')+
   `</table><table>`+picks.map(p=>`<tr><td>${p.trial}</td><td>${p.choice} (${C[p.choice]})</td></tr>`).join('')+`</table>`;
}
show();
</script></html>"""


class Handler(SimpleHTTPRequestHandler):
    page = b""
    results = OUT / "results.json"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(OUT), **kw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.page)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != "/result":
            return self.send_error(404)
        pick = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        pick["time"] = datetime.now().isoformat(timespec="seconds")
        data = json.loads(self.results.read_text()) if self.results.exists() else {"picks": []}
        data["picks"].append(pick)
        self.results.write_text(json.dumps(data, indent=2))
        print("pick:", pick, flush=True)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("color_a")
    ap.add_argument("color_b")
    ap.add_argument("--shirt", default="#1F4E9C", help="shirt colour (Königsblau guess)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--include-approved", action="store_true",
                    help="also show approved designs (images go to build/abtest/ only)")
    args = ap.parse_args()

    trials = build_images([args.color_a, args.color_b], args.shirt, args.include_approved)
    Handler.page = (PAGE.replace("__TRIALS__", json.dumps(trials))
                    .replace("__COLORS__", json.dumps({"A": args.color_a, "B": args.color_b}))).encode()
    res = OUT / "results.json"
    res.write_text(json.dumps({"colors": {"A": args.color_a, "B": args.color_b},
                               "shirt": args.shirt, "picks": []}, indent=2))
    print(f"open http://localhost:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
