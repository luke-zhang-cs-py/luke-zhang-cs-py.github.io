"""Checks the portfolio in a real browser.

    python tests/check_site.py [--shots DIR] [--coverage coverage.html] [--offline]

Structure, the demo GIFs, the nav, dark mode, layout at three widths, reduced motion, print,
the link preview, valid dates, a privacy guard, that the page's figures add up and match each
project's own README, that the README states the right number of checks, and that every
outbound link answers, and the W3C validator finds no errors. --offline skips the three checks
that need the network.

--coverage writes an HTML report of which lines of the page's JavaScript and which CSS rules
ran, merged over every scenario above (V8 block coverage and Chrome's CSS rule usage).
"""
import hashlib, html as htmllib, json, pathlib, re, sys
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "index.html").as_uri()
SECTIONS = ["about", "projects", "skills", "education", "contact"]
WIDTHS = (1280, 820, 390)
DEMOS = 6
NETWORK_CHECKS = 3          # the W3C validator, figures against the READMEs, and outbound links
OFFLINE = "--offline" in sys.argv
SHOTS = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
COVERAGE_OUT = sys.argv[sys.argv.index("--coverage") + 1] if "--coverage" in sys.argv else None

# The resume's phone number, kept here only as a hash so this public repo can't leak it either:
# every phone-shaped string in the site is normalised to ten digits, hashed and compared.
PHONE_SHA256 = "acf09c88d166a1bee808a66010d3e9662137f95c1a42f36bad835d2d66c7f426"
PHONE_SHAPE = re.compile(r"(?:\+?1[\s.\-]*)?\(?\d{3}\)?[\s.\-]*\d{3}[\s.\-]*\d{4}")

results = []   # (name, ok)


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or detail == "" else "  [%s]" % (detail,)))


def leaks_phone(text):
    return any(hashlib.sha256(re.sub(r"\D", "", m.group())[-10:].encode()).hexdigest() == PHONE_SHA256
               for m in PHONE_SHAPE.finditer(text))


def site_text():
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*")
                     if p.is_file() and p.suffix in (".html", ".md", ".svg", ".py", ".json", ".txt", ".yml")
                     and ".git" not in p.parts)


def scroll_to(pg, target):
    """Jump without smooth scrolling (target is a number or a JS expression), then let the nav update."""
    pg.evaluate("window.scrollTo({top: %s, behavior: 'instant'})" % target)
    pg.wait_for_timeout(250)


# ---------------------------------------------------------------- coverage
class Coverage:
    """Per page: V8 block coverage of the page's own scripts and Chrome's CSS rule usage, merged by source."""
    def __init__(self):
        self.js = {}         # script source -> covered flag per character
        self.css = {}        # stylesheet text -> {(start, end): used}
        self.sessions = {}   # page -> (cdp session, {scriptId: url})

    def attach(self, pg):
        s = pg.context.new_cdp_session(pg)
        scripts = {}
        s.on("Debugger.scriptParsed", lambda e: scripts.__setitem__(e["scriptId"], e["url"]))
        for cmd in ("Debugger.enable", "Profiler.enable", "DOM.enable", "CSS.enable"):
            s.send(cmd)
        s.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": True})
        s.send("CSS.startRuleUsageTracking")
        self.sessions[pg] = (s, scripts)

    def snapshot(self, pg):
        """Coverage so far; Chrome drops a page's coverage when it reloads, so call this first."""
        self.collect(pg, keep=True)

    def collect(self, pg, keep=False):
        s, scripts = self.sessions[pg] if keep else self.sessions.pop(pg)
        for fn in s.send("Profiler.takePreciseCoverage")["result"]:
            if scripts.get(fn["scriptId"]) != PAGE: continue
            src = s.send("Debugger.getScriptSource", {"scriptId": fn["scriptId"]})["scriptSource"]
            flags = [False] * len(src)
            for f in fn["functions"]:              # ranges run outer to inner, so inner ones win
                for r in f["ranges"]:
                    end = min(r["endOffset"], len(src))
                    flags[r["startOffset"]:end] = [r["count"] > 0] * (end - r["startOffset"])
            seen = self.js.get(src, [False] * len(src))
            self.js[src] = [a or b for a, b in zip(seen, flags)]
        for u in s.send("CSS.stopRuleUsageTracking")["ruleUsage"]:
            text = s.send("CSS.getStyleSheetText", {"styleSheetId": u["styleSheetId"]})["text"]
            rules = self.css.setdefault(text, {})
            key = (u["startOffset"], u["endOffset"])
            rules[key] = rules.get(key, False) or u["used"]
        if keep: s.send("CSS.startRuleUsageTracking")

    def lines(self):
        """(ran, text) per line of code; None marks the gap between scripts."""
        rows = []
        for src, flags in self.js.items():
            offset = 0
            for line in src.split("\n"):
                code = line.strip()
                first = offset + len(line) - len(line.lstrip())
                offset += len(line) + 1
                if not code or code.startswith("//") or re.fullmatch(r"[}\])]+[;,)]*", code): continue
                rows.append((first < len(flags) and flags[first], line))
            rows.append((None, ""))
        return rows

    def report(self, out):
        rows = self.lines()
        code = [r for r in rows if r[0] is not None]
        hit = sum(r[0] for r in code)
        rules = [(text[a:b].split("{")[0].strip(), used) for text, rs in self.css.items() for (a, b), used in sorted(rs.items())]
        used = sum(u for _, u in rules)
        js_pct, css_pct = 100 * hit / max(len(code), 1), 100 * used / max(len(rules), 1)
        listing = "".join('<div class="%s"><span>%s</span>%s</div>' % ("gap" if r is None else ("hit" if r else "miss"),
                          "" if r is None else ("✓" if r else "✗"), htmllib.escape(l) or "&nbsp;") for r, l in rows)
        unused = "".join("<li><code>%s</code></li>" % htmllib.escape(sel) for sel, u in rules if not u) or "<li>none</li>"
        pathlib.Path(out).write_text(f"""<!DOCTYPE html><html lang="en"><meta charset="utf-8"><title>Portfolio coverage</title>
<style>body{{font:14px system-ui;margin:24px;max-width:1100px}}h1{{font-size:20px}}.sum b{{font-size:17px}}
pre{{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto}}pre div{{white-space:pre}}
pre span{{display:inline-block;width:1.6em;color:#888}}.hit{{background:#e6ffec}}.miss{{background:#ffebe9}}.gap{{height:10px}}</style>
<h1>Portfolio coverage: tests/check_site.py</h1>
<p class="sum"><b>JavaScript: {hit} of {len(code)} lines ran ({js_pct:.1f}%)</b> · <b>CSS: {used} of {len(rules)} rules used ({css_pct:.1f}%)</b></p>
<p>Merged across every scenario the check drives: desktop, the system theme changing, the toggle, a reload, a dark system,
820 and 390 px, print, and reduced motion with Play.</p>
<h2>JavaScript</h2><pre>{listing}</pre><h2>CSS rules never used</h2><ul>{unused}</ul></html>""", encoding="utf-8")
        print("\nCoverage: JavaScript %d/%d lines (%.1f%%), CSS %d/%d rules (%.1f%%) -> %s" % (hit, len(code), js_pct, used, len(rules), css_pct, out))
        for sel, u in rules:
            if not u: print("  CSS never used: " + sel)
        for ran, line in rows:
            if ran is False: print("  JS never ran:  " + line.strip())


COV = Coverage() if COVERAGE_OUT else None


def open_page(browser, **kw):
    pg = browser.new_context(**kw).new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    if COV: COV.attach(pg)
    pg.goto(PAGE)
    return pg


def reload_page(pg):
    if COV: COV.snapshot(pg)
    pg.reload()


def close_page(pg):
    """Closes the page and returns its console errors."""
    if COV: COV.collect(pg)
    pg.context.close()
    return pg.errors


# ---------------------------------------------------------------- the checks
def check_files():
    check("privacy: the resume's phone number is nowhere in the site", not leaks_phone(site_text()))
    check("the favicon, link-preview image and 404 page exist", all((ROOT / f).is_file() for f in ("favicon.svg", "og.png", "404.html")))
    size = Image.open(ROOT / "og.png").size
    check("the link-preview image is 1200 x 630, as its tags say", size == (1200, 630), size)


def check_structure(pg):
    ids = pg.evaluate("[...document.querySelectorAll('.bar nav a')].map(a => a.getAttribute('href').slice(1))")
    check("every section in the nav exists (%s)" % ", ".join(ids), ids == SECTIONS and all(pg.locator("#" + i).count() == 1 for i in ids))
    check("two schools in Education, and no Experience section", pg.locator(".school").count() == 2 and pg.locator("#experience, .job").count() == 0)
    check("six projects, each with a live demo, a write-up or guide, and its source",
          pg.locator(".project").count() == DEMOS and pg.evaluate("""[...document.querySelectorAll('.project')].every(p => {
              const hrefs = [...p.querySelectorAll('.links a')].map(a => a.href);
              return p.querySelector('.links .btn.primary') && hrefs.some(h => /github\\.com\\/luke-zhang-cs-py\\/[^/]+$/.test(h)) && hrefs.length >= 3; })"""))
    check("the first thing Tab reaches is Skip to content", pg.evaluate("document.querySelector('a[href], button').className") == "skip")
    check("the page has one h1 and headings in order", pg.locator("h1").count() == 1 and
          pg.evaluate("[...document.querySelectorAll('h1,h2,h3')].every((h, i, a) => !i || +h.tagName[1] <= +a[i-1].tagName[1] + 1)"))
    check("every date is machine-readable (<time datetime>)",
          pg.evaluate("[...document.querySelectorAll('time')].every(t => /^\\d{4}-\\d{2}$/.test(t.getAttribute('datetime') || ''))"))
    parts = pg.evaluate("[...document.querySelectorAll('[data-tests]')].map(b => +b.textContent.replace(/,/g, ''))")
    total = pg.evaluate("+document.querySelector('[data-tests-total]').textContent.replace(/,/g, '')")
    check("the test total (%d) is the sum of the projects' own counts" % total, len(parts) == DEMOS and sum(parts) == total, "%s = %d" % (parts, sum(parts)))


def check_demos(pg):
    for y in range(0, pg.evaluate("document.body.scrollHeight"), 500):
        scroll_to(pg, y)
    pg.wait_for_function("[...document.querySelectorAll('.shot img')].every(i => i.complete && i.naturalWidth)", timeout=60000)
    imgs = pg.evaluate("[...document.querySelectorAll('.shot img')].map(i => ({src: i.src, w: i.naturalWidth, attr: +i.getAttribute('width')}))")
    check("every demo GIF loads (%d)" % len(imgs), len(imgs) == DEMOS and all(i["w"] for i in imgs))
    check("each GIF's width attribute matches the file, so nothing jumps as it loads", all(i["w"] == i["attr"] for i in imgs),
          [(i["src"].split("/")[-2], i["w"], i["attr"]) for i in imgs if i["w"] != i["attr"]])


def check_nav(pg):
    def current():
        return pg.evaluate("[...document.querySelectorAll('.bar nav a[aria-current]')].map(a => a.getAttribute('href').slice(1)).join()")
    def settle():   # smooth scrolling: wait until the page has held still for three looks in a row
        still, last = 0, None
        for _ in range(60):
            pg.wait_for_timeout(120)
            y = pg.evaluate("scrollY")
            still = still + 1 if y == last else 0
            last = y
            if still >= 3: return
    marks = {}
    for sid in SECTIONS:
        pg.click('.bar nav a[href="#%s"]' % sid); settle()
        marks[sid] = current()
    check("clicking each section in the nav marks that section", all(marks[s] == s for s in SECTIONS), marks)
    scroll_to(pg, 0); top = current()
    pg.mouse.wheel(0, 20000); settle(); bottom = current()
    check("scrolling marks Contact at the foot of the page, and nothing at the top", bottom == "contact" and top == "", (top, bottom))


def check_meta(pg):
    meta = pg.evaluate("""Object.fromEntries([...document.querySelectorAll('meta[property], meta[name]')].map(m => [m.getAttribute('property') || m.getAttribute('name'), m.content]))""")
    check("link preview: title, description, image and card are set",
          all(meta.get(k) for k in ("og:title", "og:description", "og:image", "og:url", "description", "twitter:card")))
    ld = json.loads(pg.evaluate("document.querySelector('script[type=\"application/ld+json\"]').textContent"))
    check("structured data names the person and their profiles", ld.get("@type") == "Person" and len(ld.get("sameAs", [])) == 2)
    csp = pg.evaluate("document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]')?.content || ''")
    scripts = re.search(r"script-src([^;]*)", csp)
    check("a Content-Security-Policy allows no scripts from anywhere else", "default-src 'none'" in csp and scripts and "http" not in scripts.group(1), csp)


def check_theme(browser):
    pg = open_page(browser, viewport={"width": 1280, "height": 900}, color_scheme="light")
    theme = lambda: pg.evaluate("document.documentElement.dataset.theme")
    toolbar = lambda: pg.evaluate("[...document.querySelectorAll('meta[name=\"theme-color\"]')].map(m => m.content).join()")
    before = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    pg.emulate_media(color_scheme="dark"); pg.wait_for_timeout(100)
    check("with no choice made, the page follows the system switching to dark", theme() == "dark")
    pg.emulate_media(color_scheme="light"); pg.wait_for_timeout(100)
    pg.click("#themeBtn")
    after = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    check("the theme button switches to dark", theme() == "dark" and before != after, (before, after))
    check("the browser toolbar colour follows the chosen theme", toolbar() == "#0B1220,#0B1220", toolbar())
    pg.emulate_media(color_scheme="light"); pg.wait_for_timeout(100)
    check("once chosen, the theme no longer follows the system", theme() == "dark")
    reload_page(pg)
    check("dark mode is remembered after a reload", theme() == "dark")
    if SHOTS:
        scroll_to(pg, "document.getElementById('projects').getBoundingClientRect().top + scrollY"); pg.wait_for_timeout(1200)
        pg.screenshot(path=SHOTS + "/pf-dark.png")
    errors = close_page(pg)
    d = open_page(browser, viewport={"width": 1280, "height": 900}, color_scheme="dark")
    check("a visitor whose system is dark gets dark mode first", d.evaluate("document.documentElement.dataset.theme") == "dark")
    return errors + close_page(d)


def check_layout(browser):
    errors = []
    for w in WIDTHS[1:]:
        m = open_page(browser, viewport={"width": w, "height": 860})
        m.wait_for_timeout(300)
        over = m.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("no sideways scroll at %d px" % w, over <= 0, "%d px too wide" % over)
        visible = m.locator(".bar nav a:visible").count()
        check("at %d px the section links are still in the header" % w, visible == len(SECTIONS), "%d visible" % visible)
        if SHOTS and w == 390:
            m.screenshot(path=SHOTS + "/pf-390.png")
        errors += close_page(m)
    p = open_page(browser, viewport={"width": 1280, "height": 900})
    p.emulate_media(media="print"); p.wait_for_timeout(200)
    check("print leaves out the header, demos and buttons",
          p.evaluate("['.bar', '.shot', '.links'].every(s => getComputedStyle(document.querySelector(s)).display === 'none')"))
    return errors + close_page(p)


def check_motion(browser):
    rm = open_page(browser, viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    rm.wait_for_timeout(300)
    loaded = rm.evaluate("[...document.querySelectorAll('.shot img')].filter(i => i.currentSrc.endsWith('.gif')).length")
    buttons = rm.locator(".play:visible").count()
    check("reduced motion: no GIF plays by itself, each has a Play button", loaded == 0 and buttons == DEMOS, "%d loaded, %d buttons" % (loaded, buttons))
    rm.locator(".play").first.click(); rm.wait_for_timeout(800)
    check("reduced motion: Play shows that demo",
          rm.evaluate("document.querySelector('.shot img').currentSrc.endsWith('.gif') && !document.querySelector('.shot img').hidden"))
    return close_page(rm)


def fetch(api, url):
    try:
        r = api.get(url, timeout=20000)
        return r.status, (r.text() if r.status == 200 else "")
    except Exception as e:
        return str(e)[:80], ""


def check_figures(api, cards):
    """Every figure in a card's results row must appear in that project's own README."""
    missing = []
    for repo, figures in cards:
        _, readme = fetch(api, "https://raw.githubusercontent.com/luke-zhang-cs-py/%s/main/README.md" % repo)
        missing += [(repo, fig) for fig in figures if fig not in readme]
    check("every figure on the page appears in its project's README (%d figures)" % sum(len(f) for _, f in cards), not missing, missing)


def check_valid_html(api):
    """The W3C Nu validator, on the page and the 404 page (both are public, so nothing is disclosed)."""
    errors = []
    for name in ("index.html", "404.html"):
        r = api.post("https://validator.w3.org/nu/?out=json", data=(ROOT / name).read_bytes(),
                     headers={"Content-Type": "text/html; charset=utf-8"}, timeout=30000)
        if r.status != 200: errors.append((name, "validator answered %s" % r.status)); continue
        errors += [(name, m.get("lastLine"), m["message"][:90]) for m in r.json()["messages"] if m["type"] == "error"]
    check("the W3C validator finds no errors in either page", not errors, errors[:4])


def check_links(api, links):
    bad = []
    for u in links:
        code, _ = fetch(api, u)
        # LinkedIn answers bots with 999 rather than the profile; that's LinkedIn, not a dead link
        if code != 200 and not ("linkedin.com" in u and code in (999, 429)): bad.append((u, code))
    check("every link answers (%d links)" % len(links), not bad, bad)


# ---------------------------------------------------------------- run
check_files()
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    pg = open_page(browser, viewport={"width": WIDTHS[0], "height": 900}, color_scheme="light")
    check_structure(pg)
    check_demos(pg)
    check_nav(pg)
    check_meta(pg)
    if SHOTS:
        scroll_to(pg, 0); pg.screenshot(path=SHOTS + "/pf-light.png")
    links = sorted(set(pg.evaluate("[...document.querySelectorAll('a[href^=\"http\"]')].map(a => a.href)")))
    # a figure the page derives (a sum of several README numbers) carries data-derived and is skipped
    cards = pg.evaluate("""[...document.querySelectorAll('.project')].map(p => [
        [...p.querySelectorAll('.links a')].pop().href.split('/')[4],
        [...p.querySelectorAll('.impact b:not([data-derived])')].map(b => b.textContent)])""")
    errors = close_page(pg)
    errors += check_theme(browser)
    errors += check_layout(browser)
    errors += check_motion(browser)
    check("no errors in the console, in any scenario", not errors, errors[:3])
    if not OFFLINE:
        api = pw.request.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0) portfolio-link-check")
        check_valid_html(api)
        check_figures(api, cards)
        check_links(api, links)
        api.dispose()
    browser.close()

# the README says how many checks there are; hold it to that (this one included)
stated = re.search(r"# (\d+) checks in a real browser", (ROOT / "README.md").read_text(encoding="utf-8"))
actual = len(results) + 1 + (NETWORK_CHECKS if OFFLINE else 0)
check("the README's count of checks is right (%d)" % actual, stated and int(stated.group(1)) == actual, stated and stated.group(1))

if COV: COV.report(COVERAGE_OUT)
failed = sum(not ok for _, ok in results)
print("%d passed, %d failed" % (len(results) - failed, failed))
sys.exit(1 if failed else 0)
