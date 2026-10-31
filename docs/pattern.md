# The pattern

Three shirts, each a front/back pair. The front makes a simple, earnest call;
the back answers it with a shrugging, self-aware *"I'm not saying it fixes
everything, but…"* — a gentle understatement that turns the slogan into a joke
and takes the pressure off.

## Text pattern

| | Template | Example |
|---|---|---|
| **Front** | `We should` / `<verb> more` | We should / hug more |
| **Back**  | `I’m not saying` / `that <the verb as -ing or noun>` / `solves anything,` / `but <it wouldn’t hurt / it wouldn’t make things worse / an inverse argument>` | I’m not saying / that hugging / solves anything, / but it wouldn’t hurt either |

- Front is always exactly 2 lines; the verb is the only variable.
- Back is always the same three-line setup, then a 2–3 line pay-off.
  The pay-off varies in structure:
  - *hug* – understatement: "it wouldn't hurt either"
  - *smile* – understatement: "it probably wouldn't make things worse"
  - *love* – contrast with the opposite: "hate gets us nowhere"
- Lines are broken by hand, short (≈ 2–3 words), so the block stays narrow and tall.
- Plain sentence case, no exclamation marks, only a comma after "anything".

## Visual pattern

- **One colour only**: warm, very light off-white **`#FFF8E7`** ("Cosmic Latte") on a königsblau shirt.
  (Photos look yellowish only because of warm indoor light. Chosen in a blind A/B test
  against `#F5F1E8`: 5:1, see `tools/abtest.py`.)
- **Font**: casual, slightly slanted handwriting (the originals look like
  *Ink Free*). Re-creation uses **Caveat** (SIL Open Font License, free for
  commercial use) at weight 560, which is visually very close.
- **Centered lines**, generous line spacing (baseline distance ≈ 2.1–2.3× cap height).
- **Front**: large (cap height ≈ 3.6 cm, line pitch ≈ 7.6 cm), chest height.
- **Back**: smaller (cap height ≈ 2.4 cm, line pitch ≈ 5.4 cm), upper back,
  starting just below the collar.
- No graphics, no frame, no outline – just text.

All of this is encoded in the `style:` section of [`designs.yaml`](../designs.yaml).
