# spreadshirt

Text-only T-shirt designs for [spreadshirt.de](https://www.spreadshirt.de),
generated from a single YAML file so every shirt in the series looks the same.

## Layout

```
designs.yaml          texts (front/back pairs) + shared style
docs/pattern.md       description of the text and visual pattern
tools/render.py       YAML -> SVG + PNG + preview mock-up (drafts only)
tools/approve.py      build/ -> designs/<id>/ with snapshot (approved.yaml)
tools/gallery.py      build/index.html: drafts + approved designs
tools/compare.py      reference photo vs. recreation sheet
tools/abtest.py       blind A/B colour test in the browser
tools/project.py      shared helpers (config, approval state, fingerprints)
fonts/                Caveat (SIL OFL 1.1) + licence
reference/photos/     photos of the printed shirts (EXIF/GPS stripped)
build/                generated drafts, not committed
designs/<id>/         approved, upload-ready files + approved.yaml (committed)
```

## Workflow

```sh
make setup                       # once: .venv + dependencies
make render                      # render all drafts -> build/
make render IDS="dance laugh"    # only some
open build/index.html            # browse drafts and approved designs
make approve IDS="dance laugh"   # build/ -> designs/<id>/
make compare                     # photo vs. recreation (designs with reference photos)
make clean                       # remove build/ (never touches designs/)
```

New design: add an entry to `designs.yaml` (manual line breaks, typographic
apostrophe `’`), `make render`, check it in the gallery, `make approve`.

### Approved designs are frozen

A design is approved as soon as `designs/<id>/` exists.

- `make render` **skips** approved designs (and removes their old files from
  `build/`). `FORCE=1` re-renders them into `build/` for comparison only —
  `designs/` is never written by rendering.
- `make approve` **refuses** to overwrite an approved design; `FORCE=1`
  replaces it (`make render IDS=hug FORCE=1 && make approve IDS=hug FORCE=1`).
- `make approve` also refuses stale build files: each render stores a
  fingerprint of texts, style, font and renderer (`build/<id>.inputs`).
- `designs/<id>/approved.yaml` snapshots the texts and style at approval.
  If `designs.yaml` changes later (texts or the global style), `make render`
  warns, but the approved files stay as they are. Designs removed from
  `designs.yaml` keep their approved folder and are still shown in the gallery.

## Output per design

| File | Use |
|---|---|
| `<id>-front.svg`, `<id>-back.svg` | **Primary upload.** Text converted to merged outlines, one colour, real size in mm. Suitable for flex/flock (plot) printing. |
| `<id>-front.png`, `<id>-back.png` | Fallback for digital printing: transparent, 300 dpi, < 4000 px. |
| `<id>-preview.jpg` | Mock-up for approval only, don't upload. |

All fronts share one canvas width (28 cm) and font size, all backs too. In the
Spreadshirt designer, scale every design of a side to the **same width** to
keep the series consistent.

### Spreadshirt constraints (checked)

- Vector/plot: lines ≥ 1.5 mm, gaps ≥ 1 mm, ≤ 3 colours, max 38 × 38 cm.
  Smallest strokes here: ≈ 2.5 mm (back text).
- Pixel: ≥ 200 dpi at print size, max 4000 × 4000 px and 10 MB.
- The print colour `#FFF8E7` is a target; flex/flock use the closest foil
  colour Spreadshirt offers (white foil, or cream if available).
