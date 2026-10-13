#!/usr/bin/env python3
"""
add_etsy_videos.py -- put the Etsy "page being colored" videos on the website.

For every book listed in etsy-videos.json:
  * two videos go on the right of that book's "Related reading" section
    (text left, videos side by side; phones stack videos first, then text)
  * the third video (the "sample") goes on coloring-samples.html ("Page coloring samples")

Usage
  python add_etsy_videos.py --ingest SLUG --title "Book Title" NAME=a.mp4 NAME=b.mp4 NAME=c.mp4 [--apply]
      First two files -> related reading, third -> samples page. Makes small web (with the video's music)
      versions + posters in videos/etsy/ and records the book in etsy-videos.json.
      NAME is the short subject label (kittens, owls, sled ...). A bare path uses the file stem.
  python add_etsy_videos.py [--apply]
      Rebuilds every book page + coloring-samples.html + nav/sitemap links from etsy-videos.json.

Dry run unless --apply. Idempotent. Run it AFTER add_related_reading.py if you ever re-run
that script (that script also preserves the videos now, but this is the safe order).
Needs ffmpeg for --ingest.
"""
import re, sys, json, subprocess, html
from pathlib import Path

HERE = Path(__file__).parent
APPLY = "--apply" in sys.argv
MANIFEST = HERE / "etsy-videos.json"
OUT = HERE / "videos" / "etsy"
SITE = "https://calmkidssensory.com"

def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

def save(m):
    if APPLY:
        MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- ingest
def ingest(argv):
    args = [a for a in argv if a != "--apply"]
    slug = args[args.index("--ingest") + 1]
    title = args[args.index("--title") + 1]
    files = [a for a in args if a.lower().endswith(".mp4")]
    if len(files) != 3:
        sys.exit("need exactly 3 .mp4 files: two for related reading, one for the samples page")
    names = []
    for f in files:
        name, _, path = f.partition("=") if "=" in f else (None, None, f)
        names.append((name or re.sub(r"^(post_|tiktok_)", "", Path(path).stem), path))
    m = load()
    m[slug] = {"title": title, "related": [n for n, _ in names[:2]], "sample": names[2][0]}
    print(f"{slug}: related={m[slug]['related']} sample={m[slug]['sample']}")
    if APPLY:
        OUT.mkdir(parents=True, exist_ok=True)
        for n, path in names:
            base = OUT / f"{slug}-{n}"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf", "scale=540:960",
                            "-c:v", "libx264", "-crf", "27", "-preset", "slow", "-c:a", "aac", "-b:a", "64k", "-ac", "1", "-movflags", "+faststart",
                            str(base) + ".mp4"], check=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "24", "-i", path, "-frames:v", "1",
                            "-vf", "scale=540:960", "-q:v", "4", str(base) + ".jpg"], check=True)
    save(m)

# ---------------------------------------------------------------- book pages
def vid_fig(slug, name, title, rel):
    alt = html.escape(f"{title}: {name} page being colored with soft pencils")
    return (f'        <figure class="related-video">\n'
            f'          <video controls preload="none" playsinline poster="{rel}videos/etsy/{slug}-{name}.jpg" aria-label="{alt}">\n'
            f'            <source src="{rel}videos/etsy/{slug}-{name}.mp4" type="video/mp4" />\n'
            f'          </video>\n'
            f'        </figure>')

def update_book(slug, b):
    p = HERE / "books" / f"{slug}.html"
    if not p.exists():
        print(f"  ! books/{slug}.html missing"); return False
    s = p.read_text(encoding="utf-8")
    m = re.search(r"  <!-- RELATED-READING:START -->\n(.*?)  <!-- RELATED-READING:END -->\n", s, re.S)
    if not m:
        print(f"  ! {slug}: no RELATED-READING markers"); return False
    body = m.group(1)
    t = re.search(r'<div class="related-text">\n(.*?)\n\s*</div>\n\s*<div class="related-videos">', body, re.S)
    if t:
        text = t.group(1)
    else:
        t = re.search(r'<div class="wrap related-reading">\n(.*)\n  </div>\n?$', body, re.S)
        text = t.group(1)
    def _ind(l):
        l = l.strip()
        if not l: return ""
        return ("          " if l.startswith("<li") else "        ") + l
    text = "\n".join(_ind(l) for l in text.split("\n"))
    figs = "\n".join(vid_fig(slug, n, b["title"], "../") for n in b["related"])
    cap = f'Two {html.escape(b["title"])} pages, colored with soft pencils.'
    new = ('  <!-- RELATED-READING:START -->\n  <div class="wrap related-reading">\n    <div class="related-split">\n'
           '      <div class="related-text">\n' + text + '\n      </div>\n      <div class="related-videos">\n' + figs +
           f'\n        <p class="related-videos-caption">{cap}</p>\n      </div>\n    </div>\n  </div>\n'
           '  <!-- RELATED-READING:END -->\n')
    s2 = s[:m.start()] + new + s[m.end():]
    if s2 != s:
        print(f"  books/{slug}.html: related reading videos updated")
        if APPLY: p.write_text(s2, encoding="utf-8")
    else:
        print(f"  books/{slug}.html: up to date")
    return True

# ---------------------------------------------------------------- samples page
PAGE_HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Page Coloring Samples &mdash; Calm Kids Sensory</title>
<meta name="description" content="Watch single pages from our coloring books being colored with soft pencils, a quiet look at how a finished page can look." />
<link rel="canonical" href="https://calmkidssensory.com/coloring-samples.html" />
<link rel="icon" type="image/png" href="images/logo.png" />
<link rel="stylesheet" href="css/site.css" />
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "Page Coloring Samples",
  "url": "https://calmkidssensory.com/coloring-samples.html",
  "description": "Single coloring pages being colored with soft pencils.",
  "isPartOf": { "@type": "WebSite", "name": "Calm Kids Sensory", "url": "https://calmkidssensory.com/" }
}
</script>
</head>
<body>

<header class="site-header compact">
  <div class="header-inner wrap" style="text-align:left; max-width: 1080px;">
    <a class="back-link" href="index.html">&larr; Back to Calm Kids Sensory</a>
    <p class="brand-mark"><a href="index.html">Calm Kids Sensory</a></p>
    <p class="brand-sub">PikMe Publishing</p>
  </div>
</header>

<section id="samples">
  <div class="wrap">
    <div class="section-heading" data-reveal>
      <h2>Page Coloring Samples</h2>
      <p>One page at a time, colored slowly with soft pencils. A quiet look at how a finished page can look. For full previews of each book, see <a href="videos.html">Videos &amp; Page Previews</a>.</p>
    </div>
    <div class="video-grid samples-grid">
'''
PAGE_TAIL = '''    </div>
  </div>
</section>

<footer class="site-footer" id="footer">
  <div class="wrap">
    <img src="images/logo.png" alt="Calm Kids Sensory logo" class="footer-logo" />
    <p class="footer-brand">Calm Kids Sensory &middot; PikMe Publishing</p>
    <p>Serene, low-stimulation coloring books for kids and the grown-ups who care for them.</p>

    <div class="footer-connect">
      <p class="connect-title">Connect With Us</p>
      <p>YouTube: Calm Kids Sensory</p>
      <p>Amazon Author Page, PikMe Publishing: <a href="https://www.amazon.com/author/calmkidssensory" target="_blank" rel="noopener noreferrer">amazon.com/author/calmkidssensory</a></p>
      <p>Etsy Shop: <a href="https://calmkidssensory.etsy.com" target="_blank" rel="noopener noreferrer">calmkidssensory.etsy.com</a></p>
      <p>Instagram: @calmkidssensory</p>
      <p><a class="btn-tiktok" href="https://www.tiktok.com/@calmkidssensory" target="_blank" rel="noopener noreferrer">Follow on TikTok</a></p>
      <p>Pinterest: CalmKidsSensory</p>
    </div>

    <div class="footer-links">
      <a href="index.html#footer" style="color:var(--sage-text); font-weight:600; font-size:0.9rem; text-decoration:underline;">Back to Calm Kids Sensory</a>
    </div>

    <p class="footer-copy">&copy; 2026 Calm Kids Sensory / PikMe Publishing. All rights reserved.</p>
  </div>
</footer>

<script src="js/reveal.js" defer></script>
</body>
</html>
'''

def sample_card(slug, b):
    n = b["sample"]; title = html.escape(b["title"])
    return (f'      <div class="video-card sample-card">\n'
            f'        <div class="video-frame">\n'
            f'          <video controls preload="none" playsinline poster="videos/etsy/{slug}-{n}.jpg">\n'
            f'            <source src="videos/etsy/{slug}-{n}.mp4" type="video/mp4" />\n'
            f'          </video>\n'
            f'        </div>\n'
            f'        <div class="video-body">\n'
            f'          <h3>{title}</h3>\n'
            f'          <p>A {html.escape(n)} page from this book, colored with soft pencils.</p>\n'
            f'          <a class="btn-video-cta" href="books/{slug}.html">See the Book</a>\n'
            f'        </div>\n'
            f'      </div>\n')

def write_samples(m):
    page = PAGE_HEAD + "".join(sample_card(s, b) for s, b in m.items()) + PAGE_TAIL
    p = HERE / "coloring-samples.html"
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    print("  coloring-samples.html:", "updated" if old != page else "up to date", f"({len(m)} samples)")
    if APPLY and old != page: p.write_text(page, encoding="utf-8")

def link_site():
    # nav link on the home page, sitemap entry
    idx = HERE / "index.html"; s = idx.read_text(encoding="utf-8")
    if "coloring-samples.html" not in s:
        s = s.replace('<a href="videos.html">Videos</a>', '<a href="videos.html">Videos</a>\n      <a href="coloring-samples.html">Coloring Samples</a>', 1)
        print("  index.html: nav link added")
        if APPLY: idx.write_text(s, encoding="utf-8")
    sm = HERE / "sitemap.xml"; t = sm.read_text(encoding="utf-8")
    if "coloring-samples.html" not in t:
        t = t.replace("</urlset>", f"  <url>\n    <loc>{SITE}/coloring-samples.html</loc>\n  </url>\n</urlset>", 1)
        print("  sitemap.xml: entry added")
        if APPLY: sm.write_text(t, encoding="utf-8")

def main():
    if "--ingest" in sys.argv:
        ingest(sys.argv)
    m = load() if not ("--ingest" in sys.argv and not APPLY) else {**load()}
    if "--ingest" in sys.argv and not APPLY:
        print("(dry run: manifest not written; re-run with --apply)"); return
    for slug, b in m.items():
        update_book(slug, b)
    write_samples(m)
    link_site()
    print("done" if APPLY else "dry run only; add --apply to write")

if __name__ == "__main__":
    main()
