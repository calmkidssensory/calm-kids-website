#!/usr/bin/env python3
"""
add_related_reading.py -- give every website/books/<slug>.html a full "Related reading"
block (reading guide + 3 related books + catalog link), add canonical tags, richer meta
descriptions and Product schema (offers, audience, isRelatedTo), publish 3 new reading
guides under blog/, and refresh blog/index.html + sitemap.xml.

Idempotent: the related block lives between <!-- RELATED-READING:START/END --> markers
(an old unmarked <div class="wrap related-reading"> is replaced). Dry run by default.
Usage:  python add_related_reading.py            # dry run, prints a summary
        python add_related_reading.py --apply
"""
import re, sys, json, glob, os, html
from pathlib import Path

HERE = Path(__file__).parent
APPLY = "--apply" in sys.argv
SITE = "https://calmkidssensory.com"
TODAY = "2026-10-09"

# ---- groups (ordered; peers are linked cyclically so every book gets inbound links) ----
G = {
 "toddler": ["toddler-coloring-book","coloring-young-girls","coloring-young-boys","cute-cats-toddlers","fun-mazes-toddlers"],
 "mazes":   ["fun-mazes-toddlers","fun-mazes-relaxation","fun-mazes-adventurers","relaxing-maze","round-maze","sudoku","ultimate-time-killer"],
 "quotes":  ["inspirational-quotes","animal-inspirational-quotes","flowers-butterflies-quotes","mosaic-medieval-designs","positive-journal"],
 "mosaic":  ["mosaic-flowers","mosaic-butterflies","mosaic-churches","mosaic-medieval-designs","psychedelic"],
 "flowers": ["flowers-butterflies","wild-flowers","orchids","flowers-butterflies-quotes","mosaic-flowers","mosaic-butterflies"],
 "birds":   ["birds","roosters","wild-parakeets"],
 "pets":    ["dogs","realistic-cats","cute-cats-toddlers","relaxing-animals"],
 "wild":    ["zoo-animals","jungle-mammals","reptiles-amphibians","relaxing-animals","magical-snakes"],
 "water":   ["koi-fish","underwater-world","magical-mermaids"],
 "fantasy": ["dragons","unicorn","magical-fairies","magical-mermaids","magical-creatures","magical-snakes","dinosaur"],
 "season":  ["magical-christmas","halloween-scenes","scary-zombies"],
 "places":  ["beautiful-houses","historic-architecture","mosaic-churches","relaxing-landscapes","medieval-ships"],
 "vehicles":["heavy-duty-vehicles","super-cars","fighter-jets","medieval-ships"],
 "older":   ["anime-art","samurai","science-fiction","scifi-robots","fun-cowboys","scary-zombies","brides"],
 "young":   ["dinosaur","unicorn","cute-cats-toddlers","birds"],
}
PHRASE = {
 "toddler":"another first book for small hands","mazes":"more quiet maze and puzzle focus",
 "quotes":"gentle words to color and reflect on","mosaic":"patterned mosaic pages with a steady rhythm",
 "flowers":"soft floral pages in a similar mood","birds":"more calm bird portraits",
 "pets":"gentle pet portraits to color","wild":"calm wildlife portraits",
 "water":"flowing water-themed scenes","fantasy":"cozy imaginative scenes, gentle rather than fierce",
 "season":"cozy seasonal scenes","places":"buildings and places in quiet detail",
 "vehicles":"clean vehicle illustrations","older":"detailed pages for older kids who like a slower challenge",
 "young":"simple, friendly pages for younger colorists",
}
# primary group order per book (first group decides the phrase + first peers)
PRIMARY = {}
def prim(slugs, order):
    for s in slugs: PRIMARY[s] = order
prim(G["toddler"], ["toddler","young","mazes"])
PRIMARY["fun-mazes-toddlers"] = ["mazes","toddler"]
for s in G["mazes"]: PRIMARY.setdefault(s, ["mazes"])
PRIMARY["fun-mazes-toddlers"] = ["mazes","toddler"]
for s in G["quotes"]: PRIMARY[s] = ["quotes","flowers" if "flowers" in s else "mosaic"]
PRIMARY["mosaic-medieval-designs"] = ["mosaic","quotes"]
PRIMARY["flowers-butterflies-quotes"] = ["quotes","flowers"]
PRIMARY["positive-journal"] = ["quotes"]
for s in ["mosaic-flowers","mosaic-butterflies","mosaic-churches","psychedelic"]: PRIMARY[s]=["mosaic","flowers","places"] if s!="psychedelic" else ["mosaic","older"]
for s in ["flowers-butterflies","wild-flowers","orchids"]: PRIMARY[s]=["flowers","mosaic"]
for s in G["birds"]: PRIMARY[s]=["birds","wild","pets"]
PRIMARY["dogs"]=["pets","wild","birds"]; PRIMARY["realistic-cats"]=["pets","wild","birds"]
PRIMARY["cute-cats-toddlers"]=["toddler","pets","young"]
PRIMARY["relaxing-animals"]=["wild","pets","birds"]
for s in ["zoo-animals","jungle-mammals","reptiles-amphibians"]: PRIMARY[s]=["wild","pets","birds"]
PRIMARY["koi-fish"]=["water","birds","flowers"]; PRIMARY["underwater-world"]=["water","wild","fantasy"]
for s in ["dragons","unicorn","magical-fairies","magical-mermaids","magical-creatures"]: PRIMARY[s]=["fantasy","season","young"]
PRIMARY["magical-snakes"]=["fantasy","wild"]; PRIMARY["dinosaur"]=["young","fantasy","wild"]
PRIMARY["magical-christmas"]=["season","fantasy"]; PRIMARY["halloween-scenes"]=["season","fantasy","older"]
PRIMARY["scary-zombies"]=["older","season"]
for s in ["beautiful-houses","historic-architecture","relaxing-landscapes"]: PRIMARY[s]=["places","flowers","mosaic"]
PRIMARY["medieval-ships"]=["vehicles","places","older"]
for s in ["heavy-duty-vehicles","super-cars","fighter-jets"]: PRIMARY[s]=["vehicles","older"]
for s in ["anime-art","samurai","science-fiction","scifi-robots","fun-cowboys","brides"]: PRIMARY[s]=["older","vehicles"]
PRIMARY["brides"]=["older","places","flowers"]

# ---- reading guides ----
B = "blog/"
GUIDE_TITLES = {
 "coloring-for-focus-and-reflection":"Coloring for Focus and Reflection",
 "first-coloring-books-for-toddlers":"First Coloring Books for Toddlers",
 "mazes-and-puzzles-for-quiet-focus":"Mazes and Puzzles for Quiet Focus",
 "realistic-coloring-books-for-kids-and-adults":"Realistic Coloring Books for Kids and Adults",
 "gentle-fantasy-and-seasonal-coloring-books":"Gentle Fantasy and Seasonal Coloring Books",
 "mosaic-and-pattern-coloring-books":"Mosaic and Pattern Coloring Books for Steady Focus",
 "detailed-coloring-books-for-older-kids-and-teens":"Detailed Coloring Books for Older Kids and Teens",
}
GUIDE_BOOKS = {
 "first-coloring-books-for-toddlers":["toddler-coloring-book","coloring-young-boys","coloring-young-girls","cute-cats-toddlers","fun-mazes-toddlers"],
 "coloring-for-focus-and-reflection":["animal-inspirational-quotes","flowers-butterflies-quotes","inspirational-quotes","mosaic-medieval-designs","positive-journal"],
 "mazes-and-puzzles-for-quiet-focus":["fun-mazes-adventurers","fun-mazes-relaxation","fun-mazes-toddlers","relaxing-maze","round-maze","sudoku","ultimate-time-killer"],
 "realistic-coloring-books-for-kids-and-adults":["beautiful-houses","birds","dogs","heavy-duty-vehicles","historic-architecture","jungle-mammals","koi-fish","orchids","realistic-cats","relaxing-animals","relaxing-landscapes","reptiles-amphibians","roosters","underwater-world","wild-flowers","wild-parakeets","zoo-animals"],
 "gentle-fantasy-and-seasonal-coloring-books":["dragons","unicorn","magical-fairies","magical-mermaids","magical-creatures","magical-snakes","dinosaur","magical-christmas","halloween-scenes"],
 "mosaic-and-pattern-coloring-books":["mosaic-flowers","mosaic-butterflies","mosaic-churches","mosaic-medieval-designs","psychedelic","flowers-butterflies"],
 "detailed-coloring-books-for-older-kids-and-teens":["anime-art","samurai","fighter-jets","medieval-ships","science-fiction","scifi-robots","super-cars","fun-cowboys","scary-zombies","brides"],
}
GUIDE_OF = {}
for g, bs in GUIDE_BOOKS.items():
    for b in bs: GUIDE_OF.setdefault(b, []).append(g)
# a book listed in two guides: keep the most specific one first
GUIDE_OF["mosaic-medieval-designs"] = ["coloring-for-focus-and-reflection","mosaic-and-pattern-coloring-books"]
GUIDE_OF["flowers-butterflies-quotes"] = ["coloring-for-focus-and-reflection"]
GUIDE_OF["fun-mazes-toddlers"] = ["mazes-and-puzzles-for-quiet-focus","first-coloring-books-for-toddlers"]

NEW_GUIDES = {
 "gentle-fantasy-and-seasonal-coloring-books": dict(
  dek="Dragons, fairies, mermaids, and cozy holiday scenes drawn softly enough for calm, imaginative coloring.",
  img="dragons",
  sections=[
   ("The problem","Fantasy subjects often arrive with sharp teeth, crowded battle scenes, and dense detail. For a sensory-sensitive child, an exciting idea can turn into an overwhelming page before the first color goes down."),
   ("Why this helps","Soft outlines and one clear subject per page let a child enjoy the story of a dragon, a fairy, or a mermaid without the visual noise. Cozy seasonal scenes add a familiar, predictable theme, which can make a holiday afternoon feel slower instead of busier."),
   ("What to look for","Look for rounded linework, open space to color, and a single focal subject. Check the age range on each book page, and request the free 3-page sampler first to see whether the level of detail suits your child.")]),
 "mosaic-and-pattern-coloring-books": dict(
  dek="Patterned mosaic and flowing designs that give focused hands a calm, repeatable rhythm.",
  img="mosaic-flowers",
  sections=[
   ("The problem","A wide-open page can feel like too many decisions at once. Some children and adults settle more easily when the page already has structure to follow."),
   ("Why this helps","Mosaic pages break a picture into small, clearly outlined sections. Coloring one section, then the next, gives the session a clear rhythm, an easy place to pause, and a simple way to see progress."),
   ("What to look for","Look for clean cell boundaries, sections of a similar size, and a page count that suits how long your sessions usually last. The free 3-page sampler on each book page is a low-pressure way to test the pattern size.")]),
 "detailed-coloring-books-for-older-kids-and-teens": dict(
  dek="Anime, samurai, aircraft, ships, and sci-fi scenes with enough detail to hold an older child's attention, drawn calmly.",
  img="anime-art",
  sections=[
   ("The problem","Older kids and teens often find simple pages too easy, while very busy, high-contrast pages can be tiring to look at. The middle ground is detail that stays organized."),
   ("Why this helps","Uncluttered, finely drawn scenes give an older child a longer, absorbing session without an overstimulating page. A subject they already enjoy, such as aircraft, ships, or characters, makes it easier to sit down and stay with it."),
   ("What to look for","Check the age label on each book page, then match it to the subject your child likes. Some titles, such as the zombie and cowboy books, are playful rather than frightening. The free 3-page sampler shows the line weight and detail level before you buy.")]),
}

def rd(p): return Path(p).read_text(encoding="utf-8")
def wr(p, s):
    if APPLY: Path(p).write_text(s, encoding="utf-8", newline="\n")

# ---- parse book pages ----
books = {}
for f in sorted(glob.glob(str(HERE/"books"/"*.html"))):
    s = rd(f); slug = os.path.basename(f)[:-5]
    title = re.search(r"<h1>(.*?)</h1>", s).group(1)
    age = re.search(r'age-badge">(.*?)<', s).group(1)
    desc = re.findall(r'class="book-desc">(.*?)</p>', s)[0]
    cover = re.search(r'<img src="(\.\./images/covers/[^"]+)"', s).group(1)
    books[slug] = dict(title=title, age=age, desc=desc, cover=cover, file=f)

missing = [s for s in books if s not in PRIMARY or s not in GUIDE_OF]
assert not missing, missing
for s, order in PRIMARY.items(): assert s in books, s
for g in G.values():
    for s in g: assert s in books, s
for g, bs in GUIDE_BOOKS.items():
    for s in bs: assert s in books, (g, s)

def related(slug):
    out, seen = [], {slug}
    for gname in PRIMARY[slug]:
        grp = G[gname]
        if slug in grp:
            i = grp.index(slug); peers = grp[i+1:] + grp[:i]
        else:
            peers = list(grp)
        for p in peers:
            if p not in seen and len(out) < 3:
                seen.add(p); out.append((p, gname))
    assert len(out) == 3, (slug, out)
    return out

def e(t): return t  # titles already contain HTML entities where needed

def rr_block(slug):
    b = books[slug]
    li = []
    for g in GUIDE_OF[slug]:
        li.append(f'      <li><a href="../blog/{g}.html">{GUIDE_TITLES[g]}</a> <span>&mdash; a short reading guide to books like this one</span></li>')
    for p, gname in related(slug):
        pb = books[p]
        li.append(f'      <li><a href="{p}.html">{pb["title"]}</a> <span>&mdash; {pb["age"]}; {PHRASE[gname]}</span></li>')
    li.append('      <li><a href="../index.html#books">All Calm Kids Sensory coloring books</a> <span>&mdash; browse the full catalog</span></li>')
    return ('  <!-- RELATED-READING:START -->\n'
            '  <div class="wrap related-reading">\n'
            '    <p class="related-reading-label">Related reading</p>\n'
            f'    <p class="related-reading-intro">If the {b["title"]} suits your quiet coloring time, these guides and books share the same calm, low-stimulation approach.</p>\n'
            '    <ul class="related-reading-list">\n' + "\n".join(li) + '\n    </ul>\n'
            '  </div>\n'
            '  <!-- RELATED-READING:END -->\n')

def minage(age):
    m = re.search(r"(\d+)", age); return int(m.group(1)) if m else None
def maxage(age):
    m = re.match(r"Ages (\d+)-(\d+)$", age); return int(m.group(2)) if m else None

stats = dict(rr_new=0, rr_replaced=0, canon=0, meta=0, schema=0)
for slug, b in books.items():
    f = b["file"]; s = rd(f); orig = s
    # 1. related reading block
    blk = rr_block(slug)
    if "<!-- RELATED-READING:START -->" in s:
        s = re.sub(r"  <!-- RELATED-READING:START -->.*?<!-- RELATED-READING:END -->\n", lambda m: blk, s, flags=re.S)
    elif re.search(r'<div class="wrap related-reading">.*?</div>\n', s, re.S):
        s = re.sub(r'  <div class="wrap related-reading">.*?</div>\n', lambda m: blk, s, count=1, flags=re.S); stats["rr_replaced"] += 1
    else:
        i = s.index('class="wrap offer-row"'); j = s.index("</section>", i)
        s = s[:j] + blk + s[j:]; stats["rr_new"] += 1
    # 2. canonical
    url = f"{SITE}/books/{slug}.html"
    if 'rel="canonical"' not in s:
        s = s.replace('<link rel="icon"', f'<link rel="canonical" href="{url}" />\n<link rel="icon"', 1); stats["canon"] += 1
    # 3. meta description (+og)
    m = re.search(r'<meta name="description" content="(.*?)" />', s)
    old = m.group(1)
    if "Free sampler and printable downloads" not in old:
        new = old.rstrip(". ") + f". {b['age']}. Free sampler and printable downloads."
        s = s.replace(f'content="{old}"', f'content="{new}"')  # meta + og:description
        s = s.replace(f'"description": "{old}"', f'"description": "{new}"'); stats["meta"] += 1
    # 4. Product schema
    pm = re.search(r'<script type="application/ld\+json">\s*(\{[^<]*?"@type": "Product".*?\n\})\s*</script>', s, re.S)
    prod = json.loads(pm.group(1))
    prod["category"] = "Coloring books"
    aud = {"@type": "PeopleAudience", "suggestedMinAge": minage(b["age"])}
    if maxage(b["age"]): aud["suggestedMaxAge"] = maxage(b["age"])
    prod["audience"] = aud
    offers = []
    for price, kind, href in re.findall(r'class="offer-price">\$([\d.]+)</p>\s*<a class="offer-btn (pack|etsy)" href="([^"]+)"', s):
        nm = "10-Page Digital Pack (printable PDF)" if kind == "pack" else None
        if kind == "etsy":
            pg = re.search(r"(\d+)-Page Digital Book", s); nm = f"{pg.group(1)}-Page Digital Book (printable PDF)" if pg else "Digital Book (printable PDF)"
        offers.append({"@type":"Offer","name":nm,"price":price,"priceCurrency":"USD","availability":"https://schema.org/InStock","url":href})
    if offers: prod["offers"] = offers
    prod["isRelatedTo"] = [{"@type":"Product","name":books[p]["title"],"url":f"{SITE}/books/{p}.html"} for p,_ in related(slug)]
    new_json = json.dumps(prod, indent=2, ensure_ascii=False)
    s = s.replace(pm.group(1), new_json, 1); stats["schema"] += 1
    if s != orig: wr(f, s)

# ---- CSS ----
css = rd(HERE/"css"/"site.css")
CSS_MARK = "/* RELATED-READING-LIST:START */"
if CSS_MARK not in css:
    css += f"""
{CSS_MARK}
.related-reading .related-reading-intro {{ margin: 0 0 12px; font-size: 0.9rem; color: var(--ink-soft); }}
.related-reading .related-reading-list {{ list-style: none; margin: 0; padding: 0; }}
.related-reading .related-reading-list li {{ margin: 0 0 8px; font-size: 0.85rem; color: var(--ink-soft); }}
.related-reading .related-reading-list a {{ display: inline; margin: 0; }}
/* RELATED-READING-LIST:END */
"""
    wr(HERE/"css"/"site.css", css)

# ---- blog: new guides ----
tpl = rd(HERE/"blog"/"first-coloring-books-for-toddlers.html")
def card(slug):
    b = books[slug]
    return f'''      <a class="book-card" href="../books/{slug}.html">
        <div class="book-cover">
          <img src="{b['cover']}" alt="{b['title']} cover" loading="lazy" />
        </div>
        <div class="book-body">
          <span class="age-badge">{b['age']}</span>
          <h3>{b['title']}</h3>
          <p>{b['desc']}</p>
          <span class="btn-view">View Coloring Book</span>
        </div>
      </a>
'''
for g, d in NEW_GUIDES.items():
    t = GUIDE_TITLES[g]
    p = tpl
    p = p.replace("First Coloring Books for Toddlers", t)
    p = re.sub(r"What makes a coloring book actually work.*?play\.", lambda m: d["dek"], p)
    p = p.replace("toddler-coloring-book.jpg", f"{d['img']}.jpg")
    p = p.replace("first-coloring-books-for-toddlers.html", f"{g}.html")
    p = p.replace('"datePublished": "2026-09-21"', f'"datePublished": "{TODAY}"')
    if 'rel="canonical"' not in p:
        p = p.replace('<link rel="icon"', f'<link rel="canonical" href="{SITE}/blog/{g}.html" />\n<link rel="icon"', 1)
    secs = "\n".join(f'''      <div class="blog-section">
        <h2>{h}</h2>
        <p>{txt}</p>
      </div>
''' for h, txt in d["sections"])
    p = re.sub(r'(<div class="wrap blog-article">\n).*?(  </div>\n</section>\n\n<section id="books">)', lambda m: m.group(1)+secs+m.group(2), p, flags=re.S)
    cards = "\n".join(card(x) for x in GUIDE_BOOKS[g])
    p = re.sub(r'(<div class="book-grid">\n).*?(    </div>\n  </div>\n</section>\n\n<footer)', lambda m: m.group(1)+cards+m.group(2), p, flags=re.S)
    assert d["dek"] in p and t in p
    wr(HERE/"blog"/f"{g}.html", p)

# canonical on existing blog pages + index
for f in glob.glob(str(HERE/"blog"/"*.html")):
    s = rd(f)
    if 'rel="canonical"' not in s:
        name = os.path.basename(f)
        s = s.replace('<link rel="icon"', f'<link rel="canonical" href="{SITE}/blog/{name}" />\n<link rel="icon"', 1); wr(f, s)

# blog index cards
idx = rd(HERE/"blog"/"index.html")
for g, d in NEW_GUIDES.items():
    if f'href="{g}.html"' in idx: continue
    teaser = d["dek"]
    c = f'''      <a class="book-card blog-post-card" href="{g}.html">
        <div class="book-cover">
          <img src="../images/covers/{d['img']}.jpg" alt="{GUIDE_TITLES[g]} cover" loading="lazy" />
        </div>
        <div class="book-body">
          <h3>{GUIDE_TITLES[g]}</h3>
          <p class="blog-post-teaser">{teaser}</p>
          <span class="btn-view">Read the Guide</span>
        </div>
      </a>

'''
    idx = idx.replace("    </div>\n  </div>\n</section>\n\n<footer", c.rstrip("\n").join(["",""]) + "\n" + "    </div>\n  </div>\n</section>\n\n<footer", 1) if False else idx.replace("    </div>\n  </div>\n</section>\n\n<footer", "\n" + c + "    </div>\n  </div>\n</section>\n\n<footer", 1)
wr(HERE/"blog"/"index.html", idx)

# sitemap
sm = rd(HERE/"sitemap.xml")
def touch(url, prio):
    global sm
    pat = re.compile(r"(<url>\s*<loc>"+re.escape(url)+r"</loc>\s*<lastmod>)[^<]*(</lastmod>)")
    if pat.search(sm): sm = pat.sub(lambda m: m.group(1)+TODAY+m.group(2), sm)
    else: sm = sm.replace("</urlset>", f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{TODAY}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>{prio}</priority>\n  </url>\n</urlset>")
for slug in books: touch(f"{SITE}/books/{slug}.html", "0.7")
for g in GUIDE_TITLES: touch(f"{SITE}/blog/{g}.html", "0.6")
touch(f"{SITE}/blog/index.html", "0.8")
wr(HERE/"sitemap.xml", sm)

print("MODE:", "APPLY" if APPLY else "DRY RUN", stats)
for s in ["samurai","orchids","sudoku","dragons"]:
    print(s, "->", [(p, g) for p, g in related(s)], GUIDE_OF[s])
