#!/usr/bin/env python3
"""Consistency checks for the hostcd-dist site (docs/).

Dependency-free (stdlib only). Catches the classes of drift a real review found:
stale JSON-LD, pricing that disagrees with itself, a demo duration quoted two
different ways, dangling in-page anchors, and relative links to files that do not
exist. Run from the repo root: `python3 scripts/check-site.py`.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
errors = []


def err(msg):
    errors.append(msg)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


INDEX = os.path.join(DOCS, "index.html")
html = read(INDEX)

# 1. Every JSON-LD block must be valid JSON.
for i, block in enumerate(re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)):
    try:
        json.loads(block)
    except Exception as e:  # noqa: BLE001
        err(f"index.html: JSON-LD block {i} does not parse: {e}")

# 2. Pricing must not regress to annual billing (the product is billed monthly).
if re.search(r"billed annually", html, re.I):
    err('index.html: found "billed annually" — pricing is billed monthly')

# 3. The demo duration must be quoted as ONE value everywhere (NN-sec / NN-second
#    prose and the ISO-8601 VideoObject duration must agree).
secs = set()
for m in re.finditer(r"(\d+)-sec(?:ond)?\b", html):
    secs.add(int(m.group(1)))
for m in re.finditer(r'"duration"\s*:\s*"PT(?:(\d+)M)?(?:(\d+)S)?"', html):
    secs.add(int(m.group(1) or 0) * 60 + int(m.group(2) or 0))
if len(secs) > 1:
    err(f"index.html: demo duration is quoted inconsistently: {sorted(secs)} seconds")

# 4. Every in-page anchor href="#id" must point at an existing id.
ids = set(re.findall(r'\bid="([^"]+)"', html))
for href in re.findall(r'href="#([^"]+)"', html):
    if href and href not in ids:
        err(f"index.html: dangling anchor #{href} (no matching id)")

# 5. Root-relative links/srcs ("/foo" or "/foo/") must resolve to a file in docs/.
EXT_OK = re.compile(r"\.(xml|txt|json|js|css|png|jpg|jpeg|svg|webp|ico|woff2?)$", re.I)
for attr in re.findall(r'(?:href|src)="(/[^"#?]*)"', html):
    if attr == "/":
        continue
    rel = attr.lstrip("/")
    target = os.path.join(DOCS, rel)
    if attr.endswith("/"):
        target = os.path.join(target, "index.html")
    elif not os.path.splitext(rel)[1]:
        # extensionless, no trailing slash: treat as a directory index
        target = os.path.join(target, "index.html")
    if not os.path.exists(target):
        err(f"index.html: relative link {attr} -> missing {os.path.relpath(target, ROOT)}")

if errors:
    print("site consistency check FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("site consistency check OK")
