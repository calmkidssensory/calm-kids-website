#!/usr/bin/env python3
"""
generate_catalog_pages.py — Calm Kids Sensory book-page compiler.

Rebuilds each live book's page in website/books/<slug>.html on the
"dragons.html" blueprint (shared header/footer/site.css, live SEO schema,
the working Google Apps Script sampler form, and the 3-card sage-green
offer grid with feature-list bullets + the "Easiest to Print" badge).

DESIGN NOTES — read before running with --apply / --overwrite
================================================================
1. gumroad-links.json and cover-mapping.json do NOT carry a book's title,
   age range, description, or real cover path — only a checkout URL (the
   former) and a mapping to raw Gumroad-upload screenshot staging files
   (the latter, e.g. "Screenshot 2026-08-25 121927.png" — NOT a website
   image path). Using cover-mapping.json for <img src> would have produced
   a broken image on every page, so it is NOT used for that. Its only real
   purpose here is a sanity cross-check log line.

2. Every book targeted by this script (every gumroad-links.json entry with
   "published": true) ALREADY has a hand-curated page in website/books/ —
   confirmed 57/57 existing pages, 40 currently published on Gumroad. So
   the highest-quality source for title / age / description / cover path /
   Amazon link is each book's OWN EXISTING PAGE, not a re-derivation from
   the slug. This script parses that existing page and re-skins it into
   the new template, rather than fabricating copy from scratch. Only the
   Gumroad checkout URL is taken fresh from gumroad-links.json (the
   authoritative source for that one field, in case it ever drifts).

3. website-book-slug-map.json maps a gumroad product key to the EXISTING
   website filename (e.g. "beautiful_dragons_coloring_book" -> "dragons.html").
   Output always targets that same existing filename — never a new name
   derived from the gumroad key — so a run can never create a duplicate
   page alongside the real one. Unmapped books are reported and skipped,
   never guessed.

4. Amazon card: if the parsed Amazon href is the generic author-page URL
   (no specific /dp/<ASIN>), that book has no confirmed per-book paperback
   listing yet. Rather than publish that misleading generic link on every
   such page, this renders a neutral "Paperback — coming soon on Amazon"
   block instead. Verified this pattern is already how several existing
   pages behave (e.g. beautiful-houses.html).

5. Safety / idempotency:
   - dragons.html is hard-excluded as a write target (it's the blueprint).
   - Dry-run by default. Nothing is written to disk unless --apply is passed.
   - Even with --apply, an existing target file is left untouched unless
     --overwrite is also passed (every target already exists today, so a
     plain --apply run with no --overwrite writes zero files — safe no-op).
   - Every file that IS overwritten gets a timestamped .bak sibling first.
   - Unparsable / unmatched books are reported, never silently skipped.

Usage:
    python generate_catalog_pages.py                    # dry run, summary only
    python generate_catalog_pages.py --apply             # writes NEW pages only (none today — all 57 exist)
    python generate_catalog_pages.py --apply --overwrite # regenerate existing pages into the new template (backs up first)
    python generate_catalog_pages.py --apply --overwrite --only dragons,birds  # scope to specific slugs
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent          # website/
BOOKS_DIR = SCRIPT_DIR / "books"
IMAGES_DIR = SCRIPT_DIR / "images" / "covers"
DEFAULT_DATA_DIR = SCRIPT_DIR.parent                   # video-editor/ (sibling repo root)

BLUEPRINT_SLUG = "dragons"  # never a write target — it's the hand-tuned source template

GENERIC_AMAZON_HREFS = {
    "https://www.amazon.com/author/calmkidssensory",
    "https://www.amazon.com/author/calmkidssensor",  # the typo'd variant seen in one bad template
}


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

@dataclass
class BookRecord:
    gumroad_key: str
    gumroad_url: str
    filename: str
    slug: str
    title: str = ""
    title_tag_text: str = ""  # raw <title> text before " &mdash;" — may carry a "(5-up)"-style suffix the clean H1 doesn't have
    age: str = ""
    meta_description: str = ""
    desc_paragraphs: list[str] = field(default_factory=list)
    phase3_body: str | None = None
    cover_src: str = ""
    amazon_href: str | None = None
    has_real_amazon: bool = False
    cover_file_exists: bool = False
    parse_ok: bool = False
    parse_error: str = ""


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"required data file missing: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_published_books(data_dir: Path) -> dict[str, str]:
    """gumroad product key -> checkout URL, published:true only."""
    data = load_json(data_dir / "gumroad-links.json")
    return {k: v["url"] for k, v in data.items() if v.get("published")}


def load_slug_map(data_dir: Path) -> dict[str, str]:
    """website filename -> gumroad product key (as stored); we invert it."""
    raw = load_json(data_dir / "website-book-slug-map.json")
    inverted: dict[str, str] = {}
    for filename, gumroad_key in raw.items():
        inverted[gumroad_key] = filename
    return inverted


def load_cover_mapping(data_dir: Path) -> dict[str, str]:
    """gumroad key -> raw Gumroad-upload screenshot staging filename.

    NOT used for <img> src (see module docstring, point 1) — kept only for
    a sanity cross-check line in the summary.
    """
    try:
        return load_json(data_dir / "cover-mapping.json")
    except FileNotFoundError:
        return {}


# --------------------------------------------------------------------------
# Parsing an existing page for its curated content
# --------------------------------------------------------------------------

TITLE_RE = re.compile(r"<title>(.*?)&mdash;.*?</title>", re.S)
META_DESC_RE = re.compile(r'<meta name="description" content="(.*?)"\s*/?>', re.S)
AGE_RE = re.compile(r'<span class="age-badge">(.*?)</span>')
H1_RE = re.compile(r"<h1>(.*?)</h1>", re.S)
COVER_RE = re.compile(r'<div class="book-hero-cover">\s*<img src="([^"]+)"', re.S)
DESC_RE = re.compile(r'<p class="book-desc">(.*?)</p>', re.S)
PHASE3_RE = re.compile(
    r"<!-- SEO-PHASE3-BODY:START -->\s*<p class=\"book-desc\">(.*?)</p>\s*<!-- SEO-PHASE3-BODY:END -->",
    re.S,
)
AMAZON_RE = re.compile(r'<a class="offer-btn amazon" href="([^"]+)"')


def parse_existing_page(html: str, record: BookRecord) -> None:
    try:
        # <h1> is the canonical clean book name (e.g. "Beautiful Birds Coloring
        # Book"); <title> often carries an extra "(5-up)"-style annotation
        # meant only for the browser tab / SEO title, not the on-page H1 or
        # the JSON-LD product name — so <h1> wins, <title> is a fallback only.
        m = H1_RE.search(html)
        record.title = m.group(1).strip() if m else ""

        m = TITLE_RE.search(html)
        record.title_tag_text = m.group(1).strip() if m else record.title

        m = META_DESC_RE.search(html)
        record.meta_description = m.group(1).strip() if m else ""

        m = AGE_RE.search(html)
        record.age = m.group(1).strip() if m else ""

        if not record.title:
            record.title = record.title_tag_text

        m = COVER_RE.search(html)
        record.cover_src = m.group(1).strip() if m else ""

        phase3 = PHASE3_RE.search(html)
        record.phase3_body = phase3.group(1).strip() if phase3 else None

        all_desc = [d.strip() for d in DESC_RE.findall(html)]
        # first .book-desc paragraph is the intro line; phase3 (if present)
        # is captured separately above and also matched here, so de-dupe it
        if record.phase3_body and record.phase3_body in all_desc:
            all_desc.remove(record.phase3_body)
        record.desc_paragraphs = all_desc

        m = AMAZON_RE.search(html)
        record.amazon_href = m.group(1).strip() if m else None
        record.has_real_amazon = bool(
            record.amazon_href and record.amazon_href not in GENERIC_AMAZON_HREFS
        )

        record.parse_ok = bool(record.title and record.cover_src and record.desc_paragraphs)
        if not record.parse_ok:
            record.parse_error = "missing title, cover, or description after parsing"
    except Exception as exc:  # keep going — report, don't crash the whole run
        record.parse_error = f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# Rendering (dragons.html structure, minus its page-specific hero-kicker
# copy which was written by hand for that one launch and isn't generic)
# --------------------------------------------------------------------------

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title_tag_text} &mdash; Calm Kids Sensory</title>
<meta name="description" content="{meta_description}" />
<link rel="icon" type="image/png" href="../images/logo.png" />
<link rel="stylesheet" href="../css/site.css" />
<!-- SEO-SCHEMA:START -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "{title_json}",
  "description": "{meta_description_json}",
  "image": "https://calmkidssensory.com/images/covers/{cover_filename}",
  "url": "https://calmkidssensory.com/books/{slug}.html",
  "brand": {{
    "@type": "Brand",
    "name": "Calm Kids Sensory"
  }}
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{
      "@type": "ListItem",
      "position": 1,
      "name": "Calm Kids Sensory",
      "item": "https://calmkidssensory.com/"
    }},
    {{
      "@type": "ListItem",
      "position": 2,
      "name": "{title_json}",
      "item": "https://calmkidssensory.com/books/{slug}.html"
    }}
  ]
}}
</script>
<!-- SEO-SCHEMA:END -->
<style>
  .offer-card.is-featured {{
    position: relative;
    background: var(--white);
    border: 2px solid var(--sage);
    box-shadow: 0 8px 24px rgba(143, 158, 139, 0.16);
    padding-top: 40px;
  }}

  .offer-badge {{
    position: absolute;
    top: -14px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--sage);
    color: var(--white);
    padding: 5px 16px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    white-space: nowrap;
    width: max-content;
    text-shadow: var(--text-legibility-shadow-strong);
    box-shadow: 0 3px 8px rgba(143, 158, 139, 0.25);
  }}

  .feature-list {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 0 0 22px;
    padding: 0;
    text-align: left;
  }}

  .feature-item {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 0.85rem;
    color: var(--ink-soft);
  }}

  .feature-item::before {{
    content: "\\2713";
    color: var(--sage-ink);
    font-weight: 700;
    flex-shrink: 0;
  }}

  .offer-card .offer-btn {{
    margin-top: auto;
  }}

  .offer-card.coming-soon {{
    align-items: center;
    text-align: center;
    justify-content: center;
    color: var(--ink-faint);
  }}

  .offer-card.coming-soon .offer-kicker {{
    color: var(--ink-faint);
  }}
</style>
</head>
<body>

<header class="site-header compact">
  <div class="header-inner wrap" style="text-align:left; max-width: 1080px;">
    <a class="back-link" href="../index.html">&larr; All coloring books</a>
    <p class="brand-mark"><a href="../index.html">Calm Kids Sensory</a></p>
    <p class="brand-sub">PikMe Publishing</p>
  </div>
</header>

<section class="book-hero">
  <div class="wrap book-hero-inner">
    <div class="book-hero-cover">
      <img src="{cover_src}" alt="{title} cover" />
    </div>
    <div class="book-hero-info">
      <span class="age-badge">{age}</span>
      <h1>{title}</h1>
{description_block}
      <div class="offer-grid">
        <div class="offer-card">
          <p class="offer-kicker">Try it first</p>
          <h3>3-Page Free Sampler</h3>
          <p>A few pages to try before you decide. Tell us where to send them.</p>
          <ul class="feature-list">
            <li class="feature-item">3 high-resolution PDF pages</li>
            <li class="feature-item">Delivered straight to your inbox</li>
            <li class="feature-item">Try the paper and coloring layout first</li>
          </ul>
          <form class="sampler-form">
            <input type="hidden" name="book" value="{title_attr}" />
            <input type="hidden" name="slug" value="{slug}" />
            <input type="email" name="email" class="sampler-input" placeholder="Your cozy email address..." required />
            <button type="submit" class="offer-btn sampler">Send Me My Free Pages</button>
            <p class="sampler-success" hidden>A gentle email with your coloring pages is on its way to your inbox.</p>
            <p class="sampler-error" hidden></p>
          </form>
        </div>
        <div class="offer-card is-featured">
          <span class="offer-badge">Easiest to Print</span>
          <p class="offer-kicker">Print at home</p>
          <h3>10-Page Digital Pack</h3>
          <p>The full page set as a printable download, ready whenever you want a quiet coloring session.</p>
          <ul class="feature-list">
            <li class="feature-item">10 pages themed to this book</li>
            <li class="feature-item">Reprint anytime, no limits</li>
            <li class="feature-item">Delivered instantly after checkout</li>
          </ul>
          <p class="offer-price">$2.99</p>
          <a class="offer-btn pack" href="{gumroad_url}" target="_blank" rel="noopener noreferrer">Get the Digital Pack</a>
        </div>
{amazon_card}
      </div>
      <p class="offer-note">Digital downloads are for personal, print-at-home use.</p>
    </div>
  </div>
</section>

<footer class="site-footer" id="footer">
  <div class="wrap">
    <img src="../images/logo.png" alt="Calm Kids Sensory logo" class="footer-logo" />
    <p class="footer-brand">Calm Kids Sensory &middot; PikMe Publishing</p>
    <p>Serene, low-stimulation coloring books for kids and the grown-ups who care for them.</p>

    <div class="footer-connect">
      <p class="connect-title">Connect With Us</p>
      <p>YouTube: Calm Kids Sensory</p>
      <p>Amazon Author Page, PikMe Publishing: <a href="https://www.amazon.com/author/calmkidssensory" target="_blank" rel="noopener noreferrer">amazon.com/author/calmkidssensory</a></p>
      <p>Instagram: @calmkidssensory</p>
      <p><a class="btn-tiktok" href="https://www.tiktok.com/@calmkidssensory" target="_blank" rel="noopener noreferrer">Follow on TikTok</a></p>
      <p>Pinterest: CalmKidsSensory</p>
    </div>

    <div class="footer-links">
      <a href="../index.html#footer" style="color:var(--sage-text); font-weight:600; font-size:0.9rem; text-decoration:underline;">Back to Calm Kids Sensory</a>
    </div>

    <p class="footer-copy">&copy; 2026 Calm Kids Sensory / PikMe Publishing. All rights reserved.</p>
  </div>
</footer>

<script src="../js/sampler-form.js" defer></script>
</body>
</html>
"""

AMAZON_CARD_REAL = """        <div class="offer-card">
          <p class="offer-kicker">Keep it on the shelf</p>
          <h3>Paperback on Amazon</h3>
          <p>The complete, bound coloring book, printed and delivered to your door.</p>
          <ul class="feature-list">
            <li class="feature-item">Durable softcover binding</li>
            <li class="feature-item">Single-sided pages, so color won't bleed through</li>
            <li class="feature-item">Ships via Amazon</li>
          </ul>
          <a class="offer-btn amazon" href="{amazon_href}" target="_blank" rel="noopener noreferrer">Buy on Amazon</a>
        </div>"""

AMAZON_CARD_COMING_SOON = """        <div class="offer-card coming-soon">
          <p class="offer-kicker">Keep it on the shelf</p>
          <h3>Paperback &mdash; Coming Soon</h3>
          <p>A bound paperback edition is on its way to Amazon. The digital pack works today if you'd like to print at home in the meantime.</p>
        </div>"""


def json_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def html_escape_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;")


def render_page(rec: BookRecord) -> str:
    desc_blocks = []
    for p in rec.desc_paragraphs:
        desc_blocks.append(f'      <p class="book-desc">{p}</p>')
    if rec.phase3_body:
        desc_blocks.append(
            "      <!-- SEO-PHASE3-BODY:START -->\n"
            f'      <p class="book-desc">{rec.phase3_body}</p>\n'
            "      <!-- SEO-PHASE3-BODY:END -->"
        )
    description_block = "\n".join(desc_blocks) if desc_blocks else '      <p class="book-desc"></p>'

    amazon_card = (
        AMAZON_CARD_REAL.format(amazon_href=rec.amazon_href)
        if rec.has_real_amazon
        else AMAZON_CARD_COMING_SOON
    )

    cover_filename = rec.cover_src.rsplit("/", 1)[-1]

    return PAGE_TEMPLATE.format(
        title=rec.title,
        title_tag_text=rec.title_tag_text,
        title_json=json_escape(rec.title),
        title_attr=html_escape_attr(rec.title),
        meta_description=html_escape_attr(rec.meta_description),
        meta_description_json=json_escape(rec.meta_description),
        cover_filename=cover_filename,
        cover_src=rec.cover_src,
        age=rec.age,
        slug=rec.slug,
        gumroad_url=rec.gumroad_url,
        description_block=description_block,
        amazon_card=amazon_card,
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def build_records(data_dir: Path) -> tuple[list[BookRecord], list[str]]:
    unmatched: list[str] = []
    published = load_published_books(data_dir)
    slug_map = load_slug_map(data_dir)
    cover_mapping = load_cover_mapping(data_dir)  # cross-check only, see docstring

    records: list[BookRecord] = []
    for gumroad_key, url in sorted(published.items()):
        filename = slug_map.get(gumroad_key)
        if not filename:
            unmatched.append(gumroad_key)
            continue
        slug = filename[:-5] if filename.endswith(".html") else filename
        rec = BookRecord(gumroad_key=gumroad_key, gumroad_url=url, filename=filename, slug=slug)

        page_path = BOOKS_DIR / filename
        if not page_path.exists():
            rec.parse_error = f"mapped filename {filename} does not exist in website/books/"
            records.append(rec)
            continue

        html = page_path.read_text(encoding="utf-8")
        parse_existing_page(html, rec)

        if gumroad_key in cover_mapping:
            # sanity cross-check only — not used to build the <img> path
            pass

        cover_check_path = IMAGES_DIR / (rec.cover_src.rsplit("/", 1)[-1] if rec.cover_src else "")
        rec.cover_file_exists = cover_check_path.exists()

        records.append(rec)

    return records, unmatched


def main() -> int:
    # Windows consoles default to a legacy codepage that mangles the em-dashes
    # used in the summary output below; force UTF-8 so it prints cleanly.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                         help="folder containing gumroad-links.json / website-book-slug-map.json / cover-mapping.json (default: parent of website/)")
    parser.add_argument("--apply", action="store_true", help="actually write files (default: dry run / summary only)")
    parser.add_argument("--overwrite", action="store_true", help="allow overwriting a page that already exists (default: only create missing pages)")
    parser.add_argument("--only", type=str, default=None, help="comma-separated slugs to restrict this run to (matches the output filename, e.g. 'dragons,birds')")
    args = parser.parse_args()

    only: set[str] | None = None
    if args.only:
        only = {s.strip() for s in args.only.split(",") if s.strip()}

    records, unmatched = build_records(args.data_dir)

    if only:
        records = [r for r in records if r.slug in only]

    written, backed_up, skipped_existing, skipped_blueprint, skipped_bad_parse = [], [], [], [], []

    for rec in records:
        if rec.slug == BLUEPRINT_SLUG:
            skipped_blueprint.append(rec.slug)
            continue
        if not rec.parse_ok:
            skipped_bad_parse.append((rec.slug, rec.parse_error))
            continue

        target = BOOKS_DIR / rec.filename
        exists = target.exists()

        if exists and not args.overwrite:
            skipped_existing.append(rec.slug)
            continue

        if not args.apply:
            written.append(rec.slug)  # would-write, for dry-run reporting
            continue

        if exists:
            backup = target.with_suffix(f".html.bak-{datetime.now():%Y%m%d%H%M%S}")
            shutil.copy2(target, backup)
            backed_up.append(str(backup.relative_to(SCRIPT_DIR)))

        target.write_text(render_page(rec), encoding="utf-8")
        written.append(rec.slug)

    # ---------------- summary ----------------
    real_amazon = sum(1 for r in records if r.has_real_amazon)
    coming_soon = sum(1 for r in records if r.parse_ok and not r.has_real_amazon)
    covers_ok = sum(1 for r in records if r.cover_file_exists)
    covers_missing = [r.slug for r in records if r.parse_ok and not r.cover_file_exists]

    print("=" * 72)
    print("generate_catalog_pages.py — summary" + ("" if args.apply else "  [DRY RUN — nothing written]"))
    print("=" * 72)
    print(f"Published on Gumroad (source: gumroad-links.json): {len(load_published_books(args.data_dir))}")
    print(f"Matched to an existing website/books/ page:         {len(records)}")
    if unmatched:
        print(f"Unmatched (no entry in website-book-slug-map.json): {len(unmatched)}")
        for key in unmatched:
            print(f"    - {key}")
    if skipped_bad_parse:
        print(f"Skipped — could not parse existing page cleanly:    {len(skipped_bad_parse)}")
        for slug, err in skipped_bad_parse:
            print(f"    - {slug}: {err}")
    print(f"Skipped — blueprint file (never a write target):    {len(skipped_blueprint)}")
    print(f"Skipped — already exists (pass --overwrite):        {len(skipped_existing)}")
    print(f"Amazon card — real per-book listing:                {real_amazon}")
    print(f"Amazon card — 'Coming Soon' fallback:                {coming_soon}")
    print(f"Cover image resolved on disk:                       {covers_ok}/{len(records)}")
    if covers_missing:
        print(f"    missing covers for: {', '.join(covers_missing)}")
    verb = "Written" if args.apply else "Would write"
    print(f"{verb}: {len(written)}")
    for slug in written:
        print(f"    - website/books/{slug}.html")
    if backed_up:
        print(f"Backups created: {len(backed_up)}")
        for b in backed_up:
            print(f"    - {b}")
    print("=" * 72)
    if not args.apply:
        print("This was a dry run — no files were changed. Re-run with --apply to write,")
        print("and add --overwrite to regenerate pages that already exist.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
