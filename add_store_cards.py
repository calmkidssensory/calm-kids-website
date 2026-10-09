#!/usr/bin/env python3
"""
add_store_cards.py — add the Etsy card, price labels and Amazon prices to every
website/books/<slug>.html offer grid, driven by store-data.json.

store-data.json (keyed by book page slug):
    {"dragons": {"etsy": {"id": "4590601380", "price": "6.99", "pages": 49},
                 "amazon": {"paperback": {"price": "8.99", "asin": "B0..."}, "hardcover": {...}}}, ...}
  - "etsy" present  -> a "{pages}-Page Full Digital Book" card is inserted before the Amazon card.
  - "amazon" present -> the Amazon card shows Paperback (and Hardcover when it exists) prices.
  - Books without a per-book Amazon listing keep their existing card untouched.

Safe to re-run: every step is skipped if its marker is already on the page.
Usage:  python add_store_cards.py            # dry run
        python add_store_cards.py --apply
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
DATA = json.loads((HERE / "store-data.json").read_text(encoding="utf-8"))
APPLY = "--apply" in sys.argv

ETSY_CARD = """        <div class="offer-card">
          <p class="offer-kicker">Full book on Etsy</p>
          <h3>{pages}-Page Full Digital Book</h3>
          <p>The complete coloring book as a printable PDF download, ready to print at home.</p>
          <ul class="feature-list">
            <li class="feature-item">{pages} coloring illustrations</li>
            <li class="feature-item">US Letter size, reprint anytime</li>
            <li class="feature-item">Instant download after checkout</li>
          </ul>
          <p class="offer-price">${price}</p>
          <a class="offer-btn etsy" href="https://www.etsy.com/listing/{id}" target="_blank" rel="noopener noreferrer">Buy on Etsy</a>
        </div>
"""

FORMAT_BLOCK = """          <p class="offer-price">{label} ${price}</p>
          <a class="offer-btn amazon{cls}" href="https://www.amazon.com/dp/{asin}" target="_blank" rel="noopener noreferrer">Buy {label}</a>
"""

AMAZON_CARD = """        <div class="offer-card">
          <p class="offer-kicker">Keep it on the shelf</p>
          <h3>{title}</h3>
          <p>{blurb}</p>
          <ul class="feature-list">
            <li class="feature-item">{first}</li>
            <li class="feature-item">Single-sided pages, so color won't bleed through</li>
            <li class="feature-item">Ships via Amazon</li>
          </ul>
{blocks}        </div>
"""

AMAZON_ANCHOR = '        <div class="offer-card">\n          <p class="offer-kicker">Keep it on the shelf</p>'


def nl_fix(s, crlf):
    return s.replace("\n", "\r\n") if crlf else s


def patch(slug, html):
    d = DATA.get(slug)
    if not d:
        return html, []
    crlf = "\r\n" in html
    h = html.replace("\r\n", "\n")
    done = []

    # 1. Free price on the sampler card (live form only, not the "coming soon" placeholder)
    if 'class="sampler-form"' in h and "offer-price free" not in h:
        h = h.replace('          <form class="sampler-form">',
                      '          <p class="offer-price free">Free</p>\n          <form class="sampler-form">', 1)
        done.append("free")

    # 2. Amazon card: one button per format, each linked straight to that format's own
    #    listing (the generic /dp/ link opens whichever format Amazon shows first, which is
    #    usually the pricier hardcover). Rebuilt in full from store-data.json each run.
    am = d.get("amazon")
    m = re.search(r'(        <div class="offer-card">\n          <p class="offer-kicker">Keep it on the shelf</p>\n.*?        </div>\n)', h, re.S)
    if am and m and "/dp/" in m.group(1):
        pb, hc = am.get("paperback"), am.get("hardcover")
        if pb and hc:
            title, blurb = "Paperback &amp; Hardcover", "The complete, bound coloring book — paperback or hardcover, delivered to your door."
            first = "Choose softcover or hardcover"
        elif hc:
            title, blurb = "Hardcover on Amazon", "The complete, bound coloring book, printed and delivered to your door."
            first = "Durable hardcover binding"
        else:
            title, blurb = "Paperback on Amazon", "The complete, bound coloring book, printed and delivered to your door."
            first = "Durable softcover binding"
        blocks = []
        if pb:
            blocks.append(FORMAT_BLOCK.format(label="Paperback", price=pb["price"], asin=pb["asin"], cls=""))
        if hc:
            blocks.append(FORMAT_BLOCK.format(label="Hardcover", price=hc["price"], asin=hc["asin"], cls=" hardcover"))
        new = AMAZON_CARD.format(title=title, blurb=blurb, first=first, blocks="".join(blocks))
        if new != m.group(1):
            h = h.replace(m.group(1), new, 1)
            done.append("amazon-formats")

    # 3. Etsy card before the Amazon card
    et = d.get("etsy")
    am_card = re.search(r'        <div class="offer-card[^"]*">\n          <p class="offer-kicker">Keep it on the shelf</p>', h)
    if et and 'offer-btn etsy' not in h and am_card:
        h = h[:am_card.start()] + ETSY_CARD.format(**et) + h[am_card.start():]
        h = h.replace('<div class="offer-grid">', '<div class="offer-grid offer-grid-4">', 1)
        done.append("etsy")

    # 4. Note under the grid
    if done and "Prices shown" not in h:
        h = h.replace('<p class="offer-note">Digital downloads are for personal, print-at-home use.</p>',
                      '<p class="offer-note">Digital downloads are for personal, print-at-home use. Prices shown are as listed on each store and may change.</p>', 1)
    return nl_fix(h, crlf), done


changed = 0
for slug in sorted(DATA):
    p = HERE / "books" / f"{slug}.html"
    if not p.exists():
        print("MISSING PAGE", slug); continue
    html = open(p, encoding="utf-8", newline="").read()
    new, done = patch(slug, html)
    if done:
        changed += 1
        print(f"{slug}: {', '.join(done)}")
        if APPLY:
            open(p, "w", encoding="utf-8", newline="").write(new)
print(f"{changed} pages {'updated' if APPLY else 'would change'}")
