#!/usr/bin/env python3
"""Put reference photos next to the mock-up: build/<id>-compare.jpg

Approved designs use their approved preview, drafts the one in build/.
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402

PHOTOS = project.ROOT / "reference" / "photos"
H = 700
ids = sys.argv[1:] or sorted({p.stem.rsplit("-", 1)[0] for p in PHOTOS.glob("*.jpg")})
for did in ids:
    photos = [PHOTOS / f"{did}-{s}.jpg" for s in project.SIDES]
    photos = [p for p in photos if p.exists()]
    if did in project.approved_ids():  # never show a forced re-render as the approved version
        preview = project.APPROVED / did / f"{did}-preview.jpg"
    else:
        preview = project.BUILD / f"{did}-preview.jpg"
    if not preview.exists():
        preview = None
    if not photos or preview is None:
        continue  # no reference photos or nothing rendered
    tiles = []
    for p in photos:
        im = Image.open(p); im.thumbnail((H, H)); tiles.append(im)
    prev = Image.open(preview); prev.thumbnail((H * 3, H)); tiles.append(prev)
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 20 * (len(tiles) + 1), H + 40), "white")
    x = 20
    for t in tiles:
        sheet.paste(t, (x, 20)); x += t.width + 20
    project.BUILD.mkdir(exist_ok=True)
    sheet.save(project.BUILD / f"{did}-compare.jpg", quality=88)
    print(f"build/{did}-compare.jpg")
