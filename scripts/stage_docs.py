#!/usr/bin/env python3
"""
stage_docs.py — populate _docs_build/ for an MkDocs build.

MkDocs requires the docs_dir to be a sibling (not parent) of mkdocs.yml.
Since Wearly's documentation lives alongside the code it documents
(book/, docs/, skills/, graph/, and a few repo-root Markdown files),
we copy the canonical Markdown into _docs_build/ at build time. The
originals never move — this script is the one-way pipe from "code
repo layout" to "MkDocs-compatible docs tree."

Run from the repo root:
    python scripts/stage_docs.py
    mkdocs build

Or for live preview:
    python scripts/stage_docs.py && mkdocs serve

Idempotent — safe to re-run. Wipes _docs_build/ at the start so stale
files from a prior build can't leak through.
"""

import os
import shutil
import sys


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STAGE = os.path.join(_ROOT, "_docs_build")


# Directories copied wholesale (source → destination, both repo-relative).
# Destination paths are preserved so relative links inside the Markdown
# (e.g. "../docs/evidence-and-references.md" from book/12) still resolve.
_DIRS_TO_COPY = [
    ("book",   "book"),
    ("docs",   "docs"),
    ("skills", "skills"),
    ("graph",  "graph"),
]

# Single files copied into the stage root.
_FILES_TO_COPY = [
    "workflow_diagram.md",
    "Wearly_Product_Brief.md",
    "Wearly_References_and_Course_Context.md",
]

# Markdown subpaths within _DIRS_TO_COPY that we DO NOT publish in the
# Intelligent Book at their original location. (Some are internal
# housekeeping; some are re-targeted to a different path in the stage.)
_PATHS_TO_EXCLUDE = {
    os.path.normpath("docs/assets/README.md"),
    # docs/home.md is special: it's the canonical source for the SITE
    # ROOT landing page. The staging step writes it to _docs_build/index.md
    # explicitly (see below), so don't also leave a docs/home.md copy.
    os.path.normpath("docs/home.md"),
}

# Files copied to a DIFFERENT name/location in the stage tree. Used to
# produce a site-root index.html from a source file we keep alongside
# the rest of the docs.
_REMAPPED_FILES = {
    "docs/home.md": "index.md",
}


def _wipe_stage() -> None:
    if os.path.isdir(_STAGE):
        shutil.rmtree(_STAGE)
    os.makedirs(_STAGE, exist_ok=True)


def _copy_md_only(src: str, dst: str, src_root_label: str) -> int:
    """
    Copy only .md files from src -> dst, honoring _PATHS_TO_EXCLUDE.
    Returns count copied. `src_root_label` is the repo-relative directory
    name (e.g. "docs") used to build the exclusion-check path.
    """
    count = 0
    for dirpath, _dirs, files in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        for f in files:
            if not f.lower().endswith(".md"):
                continue
            rel_path = os.path.normpath(os.path.join(
                src_root_label, "" if rel == "." else rel, f,
            ))
            if rel_path in _PATHS_TO_EXCLUDE:
                continue
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(os.path.join(dirpath, f), os.path.join(target_dir, f))
            count += 1
    return count


def main() -> int:
    # ASCII-only output so this script runs cleanly on Windows consoles
    # using legacy codepages (cp1256, cp1252) without UnicodeEncodeError.
    print(f"Staging docs into {_STAGE}")
    _wipe_stage()

    total = 0
    for src_rel, dst_rel in _DIRS_TO_COPY:
        src = os.path.join(_ROOT, src_rel)
        dst = os.path.join(_STAGE, dst_rel)
        if not os.path.isdir(src):
            print(f"  - skip {src_rel}/ (not present)")
            continue
        n = _copy_md_only(src, dst, src_root_label=src_rel)
        total += n
        plural = "" if n == 1 else "s"
        print(f"  - {src_rel}/ -> {dst_rel}/  ({n} markdown file{plural})")

    for fname in _FILES_TO_COPY:
        src = os.path.join(_ROOT, fname)
        if not os.path.isfile(src):
            print(f"  - skip {fname} (not present)")
            continue
        shutil.copy2(src, os.path.join(_STAGE, fname))
        total += 1
        print(f"  - {fname}")

    # Files mapped to a different stage location (e.g. site-root index).
    for src_rel, dst_rel in _REMAPPED_FILES.items():
        src = os.path.join(_ROOT, src_rel)
        if not os.path.isfile(src):
            print(f"  - skip {src_rel} (not present; no site-root index will be generated)")
            continue
        dst = os.path.join(_STAGE, dst_rel)
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(src, dst)
        total += 1
        print(f"  - {src_rel} -> {dst_rel}  (remapped)")

    print(f"Done. {total} files staged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
