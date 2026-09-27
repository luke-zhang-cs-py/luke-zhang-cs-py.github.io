"""Checks the portfolio in a real browser.

    python tests/check_site.py [--shots DIR]

Structure (every section the nav names, six projects each with a demo, write-up and source),
the demo GIFs (all load, sized so nothing jumps), layout at 1280/820/390 px, dark mode and its
memory across a reload, reduced motion, the link-preview tags and image, a privacy guard (the
phone number on the resume never reaches the page), and every outbound link answering 200.
"""
import hashlib, json, pathlib, re, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "index.html").as_uri()
SHOTS = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
# The resume's phone number, kept here only as a hash so this public repo can't leak it either:
# every phone-shaped string in the site is normalised to ten digits, hashed and compared.
PHONE_SHA256 = "acf09c88d166a1bee808a66010d3e9662137f95c1a42f36bad835d2d66c7f426"
PHONE_SHAPE = re.compile(r"(?:\+?1[\s.\-]*)?\(?\d{3}\)?[\s.\-]*\d{3}[\s.\-]*\d{4}")
def leaks_phone(text):
    return any(hashlib.sha256(re.sub(r"\D", "", m.group())[-10:].encode()).hexdigest() == PHONE_SHA256 for m in PHONE_SHAPE.finditer(text))
fails = 0

def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or detail == "" else "  [%s]" % detail))

html = (ROOT / "index.html").read_text(encoding="utf-8")
everything = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*")
                       if p.is_file() and p.suffix in (".html", ".md", ".svg", ".py", ".json", ".txt") and ".git" not in p.parts)
check("privacy: the resume's phone number is nowhere in the site", not leaks_phone(everything))
check("the favicon, link-preview image and 404 page exist", all((ROOT / f).is_file() for f in ("favicon.svg", "og.png", "404.html")))

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, color_scheme="light")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(PAGE)

    ids = pg.evaluate("[...document.querySelectorAll('.bar nav a')].map(a => a.getAttribute('href').slice(1))")
    check("every section in the nav exists (%s)" % ", ".join(ids),
          ids == ["about", "projects", "skills", "education", "contact"] and all(pg.locator("#" + i).count() == 1 for i in ids))
    check("two schools in Education, and no Experience section", pg.locator(".school").count() == 2 and pg.locator("#experience, .job").count() == 0)
    check("six projects, each with a live demo, a write-up or guide, and its source",
          pg.locator(".project").count() == 6 and pg.evaluate("""[...document.querySelectorAll('.project')].every(p => {
              const hrefs = [...p.querySelectorAll('.links a')].map(a => a.href);
              return p.querySelector('.links .btn.primary') && hrefs.some(h => /github\\.com\\/luke-zhang-cs-py\\/[^/]+$/.test(h)) && hrefs.length >= 3; })"""))
    check("the first thing Tab reaches is Skip to content", pg.evaluate("document.querySelector('a[href], button').className") == "skip")

    for y in range(0, pg.evaluate("document.body.scrollHeight"), 500):
        pg.evaluate(f"window.scrollTo(0, {y})"); pg.wait_for_timeout(120)
    pg.wait_for_function("[...document.querySelectorAll('.shot img')].every(i => i.complete && i.naturalWidth)", timeout=60000)
    imgs = pg.evaluate("[...document.querySelectorAll('.shot img')].map(i => ({src: i.src, w: i.naturalWidth, attr: +i.getAttribute('width')}))")
    check("every demo GIF loads (%d)" % len(imgs), len(imgs) == 6 and all(i["w"] for i in imgs))
    check("each GIF's width attribute matches the file, so nothing jumps as it loads", all(i["w"] == i["attr"] for i in imgs),
          [(i["src"].split("/")[-2], i["w"], i["attr"]) for i in imgs if i["w"] != i["attr"]])
    pg.evaluate("document.getElementById('skills').scrollIntoView()"); pg.wait_for_timeout(500)
    check("the nav marks the section in view", pg.get_attribute('.bar nav a[href="#skills"]', "aria-current") == "true")

    meta = pg.evaluate("""Object.fromEntries([...document.querySelectorAll('meta[property], meta[name]')].map(m => [m.getAttribute('property') || m.getAttribute('name'), m.content]))""")
    check("link preview: title, description, image and card are set",
          all(meta.get(k) for k in ("og:title", "og:description", "og:image", "og:url", "description", "twitter:card")))
    ld = json.loads(pg.evaluate("document.querySelector('script[type=\"application/ld+json\"]').textContent"))
    check("structured data names the person and their profiles", ld.get("@type") == "Person" and len(ld.get("sameAs", [])) == 2)
    check("the page has one h1 and headings in order", pg.locator("h1").count() == 1 and
          pg.evaluate("[...document.querySelectorAll('h1,h2,h3')].every((h, i, a) => !i || +h.tagName[1] <= +a[i-1].tagName[1] + 1)"))

    if SHOTS:
        pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(300); pg.screenshot(path=SHOTS + "/pf-light-top.png")
        pg.evaluate("document.getElementById('about').scrollIntoView()"); pg.wait_for_timeout(400); pg.screenshot(path=SHOTS + "/pf-light-about.png")

    # dark mode: the toggle flips it, and a reload remembers
    before = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    pg.click("#themeBtn")
    after = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    check("the theme button switches to dark", pg.evaluate("document.documentElement.dataset.theme") == "dark" and before != after, (before, after))
    pg.reload()
    check("dark mode is remembered after a reload", pg.evaluate("document.documentElement.dataset.theme") == "dark")
    if SHOTS:
        pg.evaluate("document.getElementById('chess').scrollIntoView()"); pg.wait_for_timeout(1500); pg.screenshot(path=SHOTS + "/pf-dark-chess.png")
    check("no errors in the console", not errors, errors[:3])
    links = sorted(set(pg.evaluate("[...document.querySelectorAll('a[href^=\"http\"]')].map(a => a.href)")))
    ctx.close()

    dctx = b.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    d = dctx.new_page(); d.goto(PAGE)
    check("a visitor whose system is dark gets dark mode first", d.evaluate("document.documentElement.dataset.theme") == "dark")
    dctx.close()

    for w in (820, 390):
        m = b.new_page(viewport={"width": w, "height": 860})
        m.goto(PAGE); m.wait_for_timeout(400)
        over = m.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("no sideways scroll at %d px" % w, over <= 0, "%d px too wide" % over)
        if SHOTS and w == 390:
            m.screenshot(path=SHOTS + "/pf-390-top.png")
            m.evaluate("document.getElementById('projects').scrollIntoView()"); m.wait_for_timeout(1500); m.screenshot(path=SHOTS + "/pf-390-proj.png")
        m.close()

    rm = b.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    rm.goto(PAGE); rm.wait_for_timeout(300)
    loaded = rm.evaluate("[...document.querySelectorAll('.shot img')].filter(i => i.getAttribute('src')).length")
    check("reduced motion: no GIF plays by itself, each has a Play button", loaded == 0 and rm.locator(".play:visible").count() == 6,
          "%d loaded, %d buttons" % (loaded, rm.locator(".play:visible").count()))
    rm.locator(".play").first.click(); rm.wait_for_timeout(800)
    check("reduced motion: Play shows that demo", rm.evaluate("!!document.querySelector('.shot img').getAttribute('src') && !document.querySelector('.shot img').hidden"))

    # the browser's own HTTP client: Python 3.14's stricter TLS rejects some local CA setups
    bad = []
    api = pw.request.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0) portfolio-link-check")
    for u in links:
        try: code = api.get(u, timeout=20000).status
        except Exception as e: code = str(e)[:80]
        # LinkedIn answers bots with 999 rather than the profile; that's LinkedIn, not a dead link
        if code != 200 and not ("linkedin.com" in u and code in (999, 429)): bad.append((u, code))
    api.dispose()
    b.close()

check("every link answers (%d links)" % len(links), not bad, bad)
print("%d failed" % fails)
sys.exit(1 if fails else 0)
