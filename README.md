# spreadshirt

Text-only T-shirt designs for [spreadshirt.de](https://www.spreadshirt.de),
generated from a single YAML file so every shirt in the series looks the same.

## Layout

```
designs.yaml          texts (front/back pairs) + shared style
docs/pattern.md       description of the text and visual pattern
tools/render.py       YAML -> SVG + PNG + preview mock-up
tools/compare.py      reference photo vs. recreation sheet
fonts/                Caveat (SIL OFL 1.1) + licence
reference/photos/     photos of the printed shirts (EXIF/GPS stripped)
build/                generated output, not committed
designs/<id>/         approved, upload-ready files (committed)
```

## Usage

```sh
make setup                       # once: .venv + dependencies
make render                      # all designs -> build/
make render IDS="hug"            # only some
make compare                     # build/<id>-compare.jpg for designs with photos
make approve IDS="hug smile"     # copy build files -> designs/<id>/
```

New design: add an entry to `designs.yaml` (manual line breaks, typographic
apostrophe `’`), run `make render`, look at `build/<id>-preview.jpg`.

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
- The print colour `#F6E8A6` is a target; flex/flock use the closest foil
  colour Spreadshirt offers (e.g. a pastel/light yellow).
