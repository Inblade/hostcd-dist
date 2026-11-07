#!/usr/bin/env python3
"""Consistency checks for the hostcd-dist site (docs/).

Dependency-free (stdlib only). Catches the classes of drift a real review found,
across EVERY page under docs/ (not just the landing page): invalid JSON-LD,
pricing that regresses to annual billing, a demo duration quoted inconsistently,
dangling in-page anchors, and root-relative links to files that do not exist.

Run from the repo root: `python3 scripts/check-site.py`.

Note: cross-repo consistency between the site and the private core's README /
LICENSING.md is guarded on the core side (scripts/check-docs-consistency.sh),
since those files do not live in this repo.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
INDEX = os.path.join(DOCS, "index.html")
errors = []


def err(msg):
    errors.append(msg)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


PAGES = sorted(glob.glob(os.path.join(DOCS, "**", "*.html"), recursive=True))
if not PAGES:
    print("no HTML pages found under docs/", file=sys.stderr)
    sys.exit(1)

# --- per-page checks (all pages) ---------------------------------------------
for page in PAGES:
    name = os.path.relpath(page, DOCS)
    html = read(page)

    # 1. Every JSON-LD block must be valid JSON.
    for i, block in enumerate(re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S)):
        try:
            json.loads(block)
        except Exception as e:  # noqa: BLE001
            err(f"{name}: JSON-LD block {i} does not parse: {e}")

    # 2. Pricing must not regress to annual billing (the product is billed
    #    monthly). The exact phrase is banned; "no annual commitment" is fine.
    if re.search(r"billed annually", html, re.I):
        err(f'{name}: found "billed annually" — pricing is billed monthly')

    # 3. Don't claim the core source is public yet.
    if re.search(r"the source is available", html, re.I):
        err(f'{name}: "the source is available" — the core source is not public yet')

    # 4. Every in-page anchor href="#id" must point at an id on the same page.
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    for href in re.findall(r'href="#([^"]+)"', html):
        if href and href not in ids:
            err(f"{name}: dangling anchor #{href} (no matching id)")

    # 5. Root-relative links/srcs ("/foo" or "/foo/") must resolve to a file in
    #    docs/ (a directory or extensionless path resolves to its index.html).
    for attr in re.findall(r'(?:href|src)="(/[^"#?]*)"', html):
        if attr == "/":
            continue
        rel = attr.lstrip("/")
        target = os.path.join(DOCS, rel)
        if attr.endswith("/") or not os.path.splitext(rel)[1]:
            target = os.path.join(target, "index.html")
        if not os.path.exists(target):
            err(f"{name}: relative link {attr} -> missing {os.path.relpath(target, ROOT)}")

# --- landing-page-only checks ------------------------------------------------
idx = read(INDEX)
# The demo duration must be quoted as ONE value (NN-sec/NN-second prose and the
# ISO-8601 VideoObject duration must agree). Only the landing page has the demo.
secs = set()
for m in re.finditer(r"(\d+)-sec(?:ond)?\b", idx):
    secs.add(int(m.group(1)))
for m in re.finditer(r'"duration"\s*:\s*"PT(?:(\d+)M)?(?:(\d+)S)?"', idx):
    secs.add(int(m.group(1) or 0) * 60 + int(m.group(2) or 0))
if len(secs) > 1:
    err(f"index.html: demo duration is quoted inconsistently: {sorted(secs)} seconds")

if errors:
    print("site consistency check FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"site consistency check OK ({len(PAGES)} pages)")
