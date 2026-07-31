#!/usr/bin/env python3
"""Wrap src/page.html into a standalone index.html for GitHub Pages.

src/page.html is an HTML *fragment* — it carries <title>, <style>, the body
markup and <script>, but no document shell, because that is what the Claude
artifact host supplies. GitHub Pages does not, so this adds:

  - the doctype / <html lang> / <head> / <body> scaffold
  - <meta charset>            (the page is pure ASCII, but be explicit)
  - <meta name="viewport">    (WITHOUT THIS every mobile breakpoint is dead:
                               phone browsers assume a ~980px viewport and the
                               max-width:700px rules never fire)
  - a description meta and an emoji favicon as an inline SVG data URI

Run after any edit to src/page.html:  python3 build.py
"""

import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src" / "page.html"
OUT = ROOT / "index.html"

DESCRIPTION = (
    "What every Famicom Disk System error code means, in plain language: "
    "what triggers it, what the screen shows, and where the fault actually lives."
)
FAVICON_EMOJI = "&#128269;"  # magnifying glass


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1

    fragment = SRC.read_text(encoding="utf-8")

    # split head-ish content (title + style) from the rest
    m = re.search(r"</style>", fragment)
    if not m:
        print("expected a </style> in the fragment", file=sys.stderr)
        return 1
    head_part = fragment[: m.end()].strip()
    body_part = fragment[m.end():].strip()

    title_m = re.search(r"<title>(.*?)</title>", head_part, re.S)
    title = title_m.group(1).strip() if title_m else "FDS Error Code Explorer"

    favicon = (
        "data:image/svg+xml,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
        "%3Ctext y='.9em' font-size='90'%3E%F0%9F%94%8D%3C/text%3E%3C/svg%3E"
    )

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{html.escape(DESCRIPTION, quote=True)}">
<meta name="color-scheme" content="light">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(DESCRIPTION, quote=True)}">
<meta property="og:type" content="website">
<link rel="icon" href="{favicon}">
{head_part}
</head>
<body>
{body_part}
</body>
</html>
"""

    OUT.write_text(doc, encoding="utf-8")
    non_ascii = sorted({c for c in doc if ord(c) > 127})
    print(f"wrote {OUT.name} ({len(doc):,} bytes)")
    if non_ascii:
        print(f"note: non-ASCII characters present: {non_ascii}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
