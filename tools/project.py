"""Shared project helpers: config loading, approval state, input fingerprints.

Approval model
--------------
A design is *approved* when the directory designs/<id>/ exists. It holds the
upload files plus approved.yaml, a snapshot of the texts and style it was
rendered with. Approved designs are never re-rendered unless explicitly forced,
and never overwritten by approval unless explicitly forced.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "designs.yaml"
BUILD = ROOT / "build"
APPROVED = ROOT / "designs"
MANIFEST = "approved.yaml"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SIDES = ("front", "back")


def artifacts(did: str) -> list[str]:
    """Files that make up one design (in build/ and designs/<id>/)."""
    return [f"{did}-{s}.{ext}" for s in SIDES for ext in ("svg", "png")] + [f"{did}-preview.jpg"]


def load_config(path: Path = CONFIG) -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    seen = set()
    for d in cfg["designs"]:
        did = d.get("id", "")
        if not ID_RE.match(did):
            sys.exit(f"error: invalid id {did!r} (use lowercase letters, digits, '-')")
        if did in seen:
            sys.exit(f"error: duplicate id {did!r}")
        seen.add(did)
        for s in SIDES:
            if not d.get(s) or not any(str(l).strip() for l in d[s]):
                sys.exit(f"error: {did}: {s} has no text")
    return cfg


def approved_ids() -> set[str]:
    if not APPROVED.is_dir():
        return set()
    return {p.name for p in APPROVED.iterdir() if p.is_dir() and not p.name.startswith(".")}


def read_manifest(did: str) -> dict | None:
    p = APPROVED / did / MANIFEST
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None


def snapshot(design: dict, style: dict) -> dict:
    """The inputs that define how a design looks (texts + effective style)."""
    return {"front": list(design["front"]), "back": list(design["back"]), "style": style}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(design: dict, style: dict) -> str:
    """Hash of everything that influences the rendered files: texts, style,
    font file and renderer code. Written next to build output at render time and
    checked at approval, so stale build files cannot be approved by accident."""
    h = hashlib.sha256()
    h.update(json.dumps(snapshot(design, style), sort_keys=True, ensure_ascii=False).encode())
    h.update(_sha(ROOT / style["font"]).encode())
    h.update(_sha(ROOT / "tools" / "render.py").encode())
    return h.hexdigest()


def drift(did: str, design: dict | None, style: dict) -> str | None:
    """Describe how designs.yaml differs from the approved snapshot (None = no drift)."""
    m = read_manifest(did)
    if m is None:
        return "no approved.yaml - cannot check for changes"
    if design is None:
        return "approved, but no longer in designs.yaml"
    diffs = [s for s in SIDES if list(design[s]) != m.get(s)]
    if style != m.get("style"):
        diffs.append("style")
    return f"designs.yaml differs from approved version ({', '.join(diffs)})" if diffs else None


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
