#!/usr/bin/env python3
"""Build the published site from src/page.html.

src/page.html is an HTML *fragment* — <title>, <style>, markup and <script>,
but no document shell, because that is what the Claude artifact host supplies.
It is also the single source of truth for the error data, which lives in the
ORIGINS and CODES literals inside its <script>.

This produces:

  index.html   the standalone page, with every entry PRE-RENDERED as real
               markup. Without that, a crawler which does not execute
               JavaScript sees ~2.3k characters of scaffolding and none of the
               ~16.5k of content, because the entries are injected by script at
               runtime. Googlebot renders JS; GPTBot, ClaudeBot, PerplexityBot
               and CCBot do not. The runtime hides the static copy once it
               boots, so the interactive page is unchanged and the page still
               works with JavaScript disabled.

  llms.txt     the whole reference as plain markdown, for language models and
               anything else that would rather read text than parse a page.

  sitemap.xml  trivial, but it is the documented way to nominate a canonical URL.

Requires node on PATH (used to evaluate the data literals rather than
hand-rolling a JavaScript parser).

Run after any edit to src/page.html:  python3 build.py
"""

import html
import json
import pathlib
import re
import subprocess
import sys
import datetime

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src" / "page.html"
OUT = ROOT / "index.html"
LLMS = ROOT / "llms.txt"
SITEMAP = ROOT / "sitemap.xml"

SITE = "https://stephen-arsenault.github.io/fds-error-explorer/"
TITLE_FALLBACK = "FDS Error Code Explorer"
DESCRIPTION = (
    "What every Famicom Disk System error code means, in plain language: "
    "what triggers it, what the screen shows, and where the fault actually lives."
)

WHEN_LABEL = {
    "boot": "start-up only",
    "both": "at start-up and during play",
    "game": "only from a running game",
}


def extract_data(fragment: str) -> tuple[dict, list]:
    """Evaluate the ORIGINS and CODES literals with node and return them."""
    o = re.search(r"const ORIGINS = (\{.*?\n\};)", fragment, re.S)
    c = re.search(r"const CODES = (\[.*?\n\];)", fragment, re.S)
    if not (o and c):
        raise SystemExit("could not locate ORIGINS / CODES in the fragment")
    script = (
        "const ORIGINS = " + o.group(1) + "\n"
        "const CODES = " + c.group(1) + "\n"
        "process.stdout.write(JSON.stringify({ORIGINS, CODES}));"
    )
    res = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=False
    )
    if res.returncode != 0:
        raise SystemExit("node failed to evaluate the data:\n" + res.stderr)
    data = json.loads(res.stdout)
    return data["ORIGINS"], data["CODES"]


def anchor(code: str) -> str:
    return "err-" + code.lstrip("$").lower()


def label(code: str) -> str:
    return code.replace("$", "ERR.")


def e(t: str) -> str:
    return html.escape(t, quote=False)


def screen_line(entry: dict) -> str:
    s = entry.get("screen") or {}
    num = entry["code"].lstrip("$")
    if s.get("msg"):
        return f"{s['msg']} / ERR.{num}"
    return f"ERR.{num} with no message line"


def render_static(origins: dict, codes: list) -> str:
    """Every entry as plain semantic markup, for crawlers and no-JS readers."""
    parts = [
        '<section id="static-entries" class="static-entries">',
        "  <h2>Every error code in full</h2>",
        "  <p>The complete reference, laid out in order. The interactive version "
        "above shows one code at a time.</p>",
    ]
    for c in codes:
        o = origins[c["origin"]]
        parts.append("  <article>")
        parts.append(
            f'    <h3 id="{anchor(c["code"])}">{e(label(c["code"]))} '
            f'&mdash; {e(c["title"])}</h3>'
        )
        parts.append(
            '    <p class="se-meta">'
            f'<strong>Where the problem lives:</strong> {e(o["name"])} &middot; '
            f'<strong>When:</strong> {e(WHEN_LABEL.get(c.get("when", "game"), ""))} &middot; '
            f'<strong>On screen:</strong> {e(screen_line(c))}</p>'
        )
        for heading, key in (("What it means", "meaning"), ("What triggers it", "trigger")):
            if c.get(key):
                parts.append(f"    <h4>{heading}</h4>")
                for p in c[key]:
                    parts.append(f"    <p>{e(p)}</p>")
        if c.get("notes"):
            parts.append("    <h4>Worth knowing</h4>")
            parts.append("    <ul>")
            for n in c["notes"]:
                parts.append(f"      <li>{e(n)}</li>")
            parts.append("    </ul>")
        t = c.get("tech") or {}
        if t:
            parts.append("    <h4>In the ROM</h4>")
            parts.append("    <dl>")
            for dt, key in (("Raise site", "site"), ("Condition", "test"), ("Detail", "extra")):
                if t.get(key):
                    parts.append(f"      <dt>{dt}</dt><dd>{e(t[key])}</dd>")
            parts.append("    </dl>")
        parts.append("  </article>")
    parts.append("</section>")
    return "\n".join(parts)


STATIC_CSS = """
  /* Pre-rendered copy of every entry. Present so that crawlers and readers
     without JavaScript get the whole reference; the script hides it on boot. */
  .static-entries {
    margin-top: 56px;
    padding-top: 28px;
    border-top: 1px solid var(--rule);
  }
  .static-entries > h2 {
    font-size: 19px; font-weight: 600; margin: 0 0 6px; letter-spacing: -0.011em;
  }
  .static-entries > p { margin: 0 0 26px; color: var(--ink-3); font-size: 14px; }
  .static-entries article {
    padding: 20px 0;
    border-top: 1px solid var(--rule);
    max-width: 78ch;
  }
  .static-entries h3 {
    font-size: 17px; font-weight: 620; margin: 0 0 8px; letter-spacing: -0.008em;
  }
  .static-entries .se-meta {
    font-size: 12.5px; color: var(--ink-3); margin: 0 0 14px;
  }
  .static-entries .se-meta strong { color: var(--ink-2); font-weight: 600; }
  .static-entries h4 {
    font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.13em;
    text-transform: uppercase; color: var(--ink-3); font-weight: 500;
    margin: 16px 0 6px;
  }
  .static-entries p, .static-entries li { font-size: 14.5px; color: var(--ink-2); }
  .static-entries article p { margin: 0 0 8px; }
  .static-entries ul { margin: 0; padding-left: 18px; display: grid; gap: 5px; }
  .static-entries dl {
    margin: 0; display: grid; grid-template-columns: 110px minmax(0, 1fr);
    gap: 4px 16px; font-family: var(--mono); font-size: 12.5px;
  }
  .static-entries dt { color: var(--ink-3); text-transform: uppercase; font-size: 10px; letter-spacing: 0.1em; }
  .static-entries dd { margin: 0; color: var(--ink-2); }
"""


def render_llms(origins: dict, codes: list) -> str:
    out = [
        "# FDS Error Code Explorer",
        "",
        f"> {DESCRIPTION}",
        "",
        f"Source: {SITE}",
        "",
        "Behaviour is traced from static analysis of one 8 KB Famicom Disk System",
        "BIOS image (`disksys.rom`), mapped at $E000; nothing was executed or",
        "emulated. Physical details of the media and drive come from the NESdev",
        "Wiki and community hardware documentation.",
        "",
        "Codes $0A-$0F, $35 and $40 appear in circulating tables but have no raise",
        "site in this ROM and cannot occur. $35 is not an error: it is the",
        "warm-boot signature written to $0102.",
        "",
        "## Categories",
        "",
    ]
    for key, o in origins.items():
        n = sum(1 for c in codes if c["origin"] == key)
        out.append(f"- **{o['name']}** ({n} codes) — {o['blurb']}")
    out += ["", "## Codes", ""]
    for c in codes:
        o = origins[c["origin"]]
        out.append(f"### {label(c['code'])} — {c['title']}")
        out.append("")
        out.append(f"- Category: {o['name']}")
        out.append(f"- When: {WHEN_LABEL.get(c.get('when', 'game'), '')}")
        out.append(f"- On screen: {screen_line(c)}")
        out.append("")
        for p in c.get("meaning", []):
            out.append(p); out.append("")
        if c.get("trigger"):
            out.append("**What triggers it.** " + " ".join(c["trigger"]))
            out.append("")
        if c.get("notes"):
            out.append("**Worth knowing.**")
            out.append("")
            for n in c["notes"]:
                out.append(f"- {n}")
            out.append("")
        t = c.get("tech") or {}
        if t:
            bits = [f"raise site {t['site']}" if t.get("site") else "",
                    f"condition: {t['test']}" if t.get("test") else "",
                    t.get("extra", "")]
            out.append("**In the ROM.** " + " ".join(b for b in bits if b))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1

    fragment = SRC.read_text(encoding="utf-8")
    origins, codes = extract_data(fragment)

    m = re.search(r"</style>", fragment)
    if not m:
        print("expected a </style> in the fragment", file=sys.stderr)
        return 1
    head_part = fragment[: m.start()].rstrip()          # up to, not including, </style>
    body_part = fragment[m.end():].strip()

    title_m = re.search(r"<title>(.*?)</title>", head_part, re.S)
    title = title_m.group(1).strip() if title_m else TITLE_FALLBACK

    # The static copy goes inside .wrap, just before its closing </div>.
    # Search only the markup ahead of the <script>: the script's template
    # literals contain </div> too, and matching one of those would splice the
    # section into the middle of the JavaScript.
    static = render_static(origins, codes)
    script_at = body_part.find("<script")
    if script_at == -1:
        print("expected a <script> in the fragment", file=sys.stderr)
        return 1
    idx = body_part.rfind("</div>", 0, script_at)
    if idx == -1:
        print("could not find the wrap's closing </div>", file=sys.stderr)
        return 1
    body_part = body_part[:idx] + static + "\n\n" + body_part[idx:]

    # hide the static copy once the interactive version is live
    body_part = body_part.replace(
        "select(CODES[0].code, false);",
        "select(CODES[0].code, false);\n"
        "\n"
        "/* the pre-rendered copy exists for crawlers and no-JS readers */\n"
        "document.getElementById('static-entries')?.setAttribute('hidden', '');",
        1,
    )

    favicon = (
        "data:image/svg+xml,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
        "%3Ctext y='.9em' font-size='90'%3E%F0%9F%94%8D%3C/text%3E%3C/svg%3E"
    )

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "description": DESCRIPTION,
        "url": SITE,
        "inLanguage": "en",
        "about": {"@type": "Thing", "name": "Famicom Disk System"},
        "license": "https://opensource.org/licenses/MIT",
    }, separators=(",", ":"))

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{html.escape(DESCRIPTION, quote=True)}">
<meta name="color-scheme" content="light">
<link rel="canonical" href="{SITE}">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(DESCRIPTION, quote=True)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="{favicon}">
<script type="application/ld+json">{jsonld}</script>
<noscript><style>
  /* without JavaScript the grid and panel never populate; show only the
     pre-rendered reference rather than two empty cards above it */
  .work, .legendrow {{ display: none; }}
  .static-entries {{ margin-top: 0; border-top: 0; padding-top: 0; }}
</style></noscript>
{head_part}
{STATIC_CSS.rstrip()}
</style>
</head>
<body>
{body_part}
</body>
</html>
"""
    OUT.write_text(doc, encoding="utf-8")
    LLMS.write_text(render_llms(origins, codes), encoding="utf-8")
    today = datetime.date.today().isoformat()
    SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE}</loc><lastmod>{today}</lastmod></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )

    # how much of the page a non-JS crawler can now actually read
    stripped = re.sub(r"<script.*?</script>", "", doc, flags=re.S)
    stripped = re.sub(r"<style.*?</style>", "", stripped, flags=re.S)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", stripped)).strip()

    print(f"wrote {OUT.name} ({len(doc):,} bytes), {LLMS.name}, {SITEMAP.name}")
    print(f"entries pre-rendered: {len(codes)}")
    print(f"text visible without JavaScript: {len(text):,} characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
