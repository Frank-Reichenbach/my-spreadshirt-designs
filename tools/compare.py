#!/usr/bin/env python3
"""Put reference photos next to rendered previews: build/<id>-compare.jpg"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
H = 700
ids = sys.argv[1:] or sorted({p.stem.rsplit("-", 1)[0] for p in (ROOT / "reference" / "photos").glob("*.jpg")})
for did in ids:
    tiles = []
    for side in ("front", "back"):
        p = ROOT / "reference" / "photos" / f"{did}-{side}.jpg"
        if p.exists():
            im = Image.open(p); im.thumbnail((H, H)); tiles.append(im)
    prev = Image.open(ROOT / "build" / f"{did}-preview.jpg"); prev.thumbnail((H * 3, H))
    tiles.append(prev)
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 20 * (len(tiles) + 1), H + 40), "white")
    x = 20
    for t in tiles:
        sheet.paste(t, (x, 20)); x += t.width + 20
    sheet.save(ROOT / "build" / f"{did}-compare.jpg", quality=88)
    print("build/" + f"{did}-compare.jpg")
