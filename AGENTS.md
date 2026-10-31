# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, …) working in this repository.

## Project

Text-only T-shirt designs for spreadshirt.de, generated from `designs.yaml`.
See `README.md` for layout and workflow and `docs/pattern.md` for the text and
visual pattern.

## Rules

- Approved designs (`designs/<id>/`) are frozen. Never re-render or overwrite
  them unless the owner explicitly asks; then use `FORCE=1`.
- Only approve designs (`make approve IDS=…`) after the owner approved them.
- Texts: manual line breaks, typographic apostrophe `’`, no final full stop.
  Back pay-offs stay light, shrugging and understated – no moralizing tone.
- Generated output goes to `build/` (not committed). After approving designs,
  run `make site` so the GitHub Pages site in `docs/` stays in sync.
- The site uses no JavaScript, no third-party code, no external requests and
  stores nothing in the visitor's browser (the theme switch is CSS-only).

## Attribution

End every commit message and pull request description with
`Assisted-by:` trailers as the final trailer paragraph, using the model's
name without an email address:

```
Assisted-by: <model> (code generation)
Assisted-by: <model> (code review)
```

- Roles: `(code generation)` for the model that wrote the change,
  `(code review)` for a model that reviewed it.
- At most one line per vendor and per role. Models from different vendors
  each get their own line.
- Several models from the same vendor in the same role: name only one.
  1. The latest model wins: Claude Sonnet 5, then Claude Opus 5.5 →
     `Claude Opus 5.5`.
  2. Same release: the most expensive one wins: Claude Sonnet 5.5 and
     Claude Opus 5.5 → `Claude Opus 5.5`.
- Do not add `Co-Authored-By: … <noreply@…>` trailers or
  "Generated with …" footers.

Example (Claude wrote the change, Codex reviewed it):

```
Protect approved designs from re-rendering

Assisted-by: Claude Opus 5.5 (code generation)
Assisted-by: GPT-6.1 Terra (code review)
```
