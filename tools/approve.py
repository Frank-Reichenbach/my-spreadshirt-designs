#!/usr/bin/env python3
"""Approve rendered designs: copy build/<id>-* to designs/<id>/ with a snapshot.

Refuses when
  - designs/<id>/ already exists (use --force to replace an approved design),
  - build files are missing, or
  - build files are stale (texts, style, font or renderer changed since rendering).

Usage: python tools/approve.py laugh dance [--force]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--force", action="store_true", help="replace an already approved design")
    args = ap.parse_args(argv)

    cfg = project.load_config()
    style = cfg["style"]
    by_id = {d["id"]: d for d in cfg["designs"]}
    approved = project.approved_ids()

    # validate everything first, then write: no partial approvals
    errors = []
    for did in args.ids:
        if did not in by_id:
            errors.append(f"{did}: not in designs.yaml")
            continue
        if did in approved and not args.force:
            errors.append(f"{did}: already approved (designs/{did}/) - use --force / FORCE=1 to replace")
            continue
        missing = [f for f in project.artifacts(did) if not (project.BUILD / f).exists()]
        if missing:
            hint = f"make render IDS={did}" + (" FORCE=1" if did in approved else "")
            errors.append(f"{did}: not rendered, missing {', '.join(missing)} - run: {hint}")
            continue
        stamp = project.BUILD / f"{did}.inputs"
        current = project.fingerprint(by_id[did], style)
        if not stamp.exists() or stamp.read_text().strip() != current:
            hint = f"make render IDS={did}" + (" FORCE=1" if did in approved else "")
            errors.append(f"{did}: build files are stale (texts/style/font/renderer changed since rendering) - run: {hint}")
    if errors:
        sys.exit("error:\n  " + "\n  ".join(errors))

    project.APPROVED.mkdir(exist_ok=True)
    for did in args.ids:
        target = project.APPROVED / did
        # stage in a temp dir next to the target, then swap in
        stage = Path(tempfile.mkdtemp(prefix=f".{did}-", dir=project.APPROVED))
        try:
            for f in project.artifacts(did):
                shutil.copy2(project.BUILD / f, stage / f)
            manifest = {"id": did, "approved": date.today().isoformat(),
                        **project.snapshot(by_id[did], style)}
            (stage / project.MANIFEST).write_text(
                yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
            backup = None
            if target.exists():  # forced: keep the old version until the new one is in place
                backup = target.with_name(f".{did}-replaced")
                shutil.rmtree(backup, ignore_errors=True)
                target.rename(backup)
            try:
                stage.rename(target)
            except OSError:
                if backup:
                    backup.rename(target)
                raise
            if backup:
                shutil.rmtree(backup)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        for f in project.artifacts(did) + [f"{did}.inputs"]:
            (project.BUILD / f).unlink(missing_ok=True)  # build/ keeps drafts only
        print(f"approved: designs/{did}/")


if __name__ == "__main__":
    main()
