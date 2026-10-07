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
import html as htmllib, json, os, pathlib, re, sys
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "index.html").as_uri()
SECTIONS = ["about", "projects", "skills", "contact"]
SKILL_BLOCKS = 8
WIDTHS = (1280, 820, 390, 360)
DEMOS = 8
NETWORK_CHECKS = 4          # the W3C validator, figures against the READMEs, commits against GitHub, and outbound links
OFFLINE = "--offline" in sys.argv
SHOTS = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
COVERAGE_OUT = sys.argv[sys.argv.index("--coverage") + 1] if "--coverage" in sys.argv else None

# The site publishes no phone number, so any phone-shaped string is a leak. This used to compare
# against an unsalted SHA-256 of the resume's number, but a ten-digit number has only 10^10
# candidates, so that hash could be brute-forced back to the number in seconds.
PHONE_SHAPE = re.compile(r"(?:\+?1[\s.\-]*)?\(?\d{3}\)?[\s.\-]*\d{3}[\s.\-]*\d{4}")

results = []   # (name, ok)


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or detail == "" else "  [%s]" % (detail,)))


def leaks_phone(text):
    return [m.group() for m in PHONE_SHAPE.finditer(text)]


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
    # 555-0100..0199 is reserved for fiction: the control proves the pattern can match at all,
    # and is split so this file does not match itself. Only a count is printed, because CI logs
    # on a public repo are public too.
    found = leaks_phone(site_text())
    check("privacy: the resume's phone number is nowhere in the site",
          not found and leaks_phone("call (555) 555-" + "0123"), "%d phone-shaped strings" % len(found))
    check("the favicon, link-preview image and 404 page exist", all((ROOT / f).is_file() for f in ("favicon.svg", "og.png", "404.html")))
    size = Image.open(ROOT / "og.png").size
    check("the link-preview image is 1200 x 630, as its tags say", size == (1200, 630), size)


def check_structure(pg):
    ids = pg.evaluate("[...document.querySelectorAll('.bar nav a')].map(a => a.getAttribute('href').slice(1))")
    check("every section in the nav exists (%s)" % ", ".join(ids), ids == SECTIONS and all(pg.locator("#" + i).count() == 1 for i in ids))
    check("no Experience or Education section", pg.locator("#experience, .job, #education, .school").count() == 0)
    check("eight skill blocks, each with a heading and at least four skills",
          pg.locator(".skill").count() == SKILL_BLOCKS and pg.evaluate("[...document.querySelectorAll('.skill')].every(s => s.querySelector('h3') && s.querySelectorAll('li').length >= 4)"))
    check("eight projects, each with a live demo, a write-up or guide, and its source",
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


def check_components(pg):
    """The featured case study, the category filter, the command palette and the contact form."""
    featured = pg.evaluate("[...document.querySelectorAll('.project.featured .case dt')].map(d => d.textContent)")
    check("one featured project, told as problem, approach and result", pg.locator(".project.featured").count() == 1 and featured == ["Problem", "Approach", "Result"], featured)

    visible = lambda: pg.evaluate("[...document.querySelectorAll('.project')].filter(a => !a.hidden).map(a => a.id)")
    pg.click('.chip[data-filter="Computer vision"]')
    cv, count = visible(), pg.text_content("#projectCount")
    pg.click('.chip[data-filter="All"]')
    check("the filter shows only a category's projects, and says how many", cv == ["faces"] and "1 of %d" % DEMOS in count and len(visible()) == DEMOS, (cv, count))
    check("the pressed filter is announced as pressed", pg.get_attribute('.chip[data-filter="All"]', "aria-pressed") == "true")

    pg.keyboard.press("Control+k")
    opened = pg.evaluate("document.getElementById('palette').open && document.activeElement.id === 'paletteInput'")
    pg.keyboard.type("skills"); pg.keyboard.press("Enter"); pg.wait_for_timeout(1500)
    landed = pg.evaluate("Math.abs(document.getElementById('skills').getBoundingClientRect().top) < 120")
    check("Ctrl+K opens the command palette, and typing a section then Enter goes there", opened and landed and not pg.evaluate("document.getElementById('palette').open"), (opened, landed))
    pg.keyboard.press("/"); pg.keyboard.type("tally"); pg.keyboard.press("ArrowDown")
    second = pg.evaluate("document.querySelector('#paletteList [aria-selected=\"true\"]').textContent")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Control+k"); pg.keyboard.type("copy my email"); pg.keyboard.press("Enter")
    copied = pg.text_content("#formStatus")
    check("the palette's Copy my email address command says it copied it", "Copied zhang.l17@northeastern.edu" in copied, copied)
    check("/ opens it too, arrows move through the matches, and Esc closes it",
          "demo" in second and not pg.evaluate("document.getElementById('palette').open"), second)

    pg.click("#contactForm button[type=submit]")
    empty = (pg.get_attribute("#cfName", "aria-invalid"), pg.text_content("#formStatus"))
    pg.fill("#cfName", "Ada"); pg.fill("#cfEmail", "ada@example.com"); pg.fill("#cfMessage", "Hello & welcome")
    pg.click("#contactForm button[type=submit]"); pg.wait_for_timeout(300)
    mailto = pg.evaluate("document.getElementById('contactForm').dataset.mailto || ''")
    check("the contact form refuses to send empty, and marks what's missing", empty[0] == "true" and "fill in" in empty[1], empty)
    check("a filled-in form becomes an email to Luke with the message in it",
          mailto.startswith("mailto:zhang.l17@northeastern.edu?subject=Portfolio%3A%20message%20from%20Ada") and "Hello%20%26%20welcome" in mailto, mailto[:90])


def contrast_failures(pg):
    """WCAG AA: every piece of visible text against the colour actually behind it."""
    return pg.evaluate(r"""() => {
      // rgb()/rgba() give 0-255 channels; color(srgb ...), which Chrome uses for color-mix(), gives 0-1
      const parse = c => { const n = c.match(/[\d.]+/g).map(Number); const unit = c.startsWith('color(') ? 1 : 255;
                           return { rgb: n.slice(0, 3).map(v => v / unit), a: n.length > 3 ? n[3] : 1 }; };
      const lum = c => { const [r, g, b] = parse(c).rgb.map(v => v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
                         return .2126 * r + .7152 * g + .0722 * b; };
      const behind = el => { for (let e = el; e; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor;
                         if (/\d/.test(bg) && parse(bg).a > .5) return bg; } return getComputedStyle(document.body).backgroundColor; };
      const out = [];
      for (const el of document.querySelectorAll('body *')) {
        if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
        const s = getComputedStyle(el); if (s.visibility === 'hidden' || s.display === 'none' || !el.getClientRects().length) continue;
        if (el.closest('dialog:not([open]), [hidden], .skip, noscript')) continue;
        const big = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && +s.fontWeight >= 700);
        const [L1, L2] = [lum(s.color), lum(behind(el))].sort((a, b) => b - a);
        const ratio = (L1 + .05) / (L2 + .05);
        if (ratio < (big ? 3 : 4.5)) out.push(el.tagName + '.' + el.className + ' ' + ratio.toFixed(2) + ' "' + el.textContent.trim().slice(0, 24) + '"');
      }
      return [...new Set(out)];
    }""")


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
    check("the page opens in dark mode, even on a system set to light", theme() == "dark")
    pg.evaluate("document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'))"); pg.wait_for_timeout(700)
    dark_fail = contrast_failures(pg)
    check("dark mode: all text meets WCAG AA contrast", not dark_fail, dark_fail[:4])
    pg.emulate_media(color_scheme="dark"); pg.emulate_media(color_scheme="light"); pg.wait_for_timeout(100)
    check("a system theme change doesn't override it", theme() == "dark")
    before = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    pg.click("#themeBtn"); pg.wait_for_timeout(400)
    after = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    check("the theme button switches to light", theme() == "light" and before != after, (before, after))
    check("the browser toolbar colour follows the chosen theme", toolbar() == "#F8FAFC", toolbar())
    light_fail = contrast_failures(pg)
    check("light mode: all text meets WCAG AA contrast", not light_fail, light_fail[:4])
    reload_page(pg)
    check("a choice of light is remembered after a reload", theme() == "light")
    if SHOTS:
        scroll_to(pg, "document.getElementById('projects').getBoundingClientRect().top + scrollY"); pg.wait_for_timeout(1200)
        pg.screenshot(path=SHOTS + "/pf-dark.png")
    errors = close_page(pg)
    d = open_page(browser, viewport={"width": 1280, "height": 900}, color_scheme="dark")
    check("a visitor whose system is dark gets dark mode too", d.evaluate("document.documentElement.dataset.theme") == "dark")
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
    # Eight buttons all named "Play demo" are indistinguishable in a screen reader's list of buttons.
    names = set(rm.evaluate("[...document.querySelectorAll('.play')].map(b => b.getAttribute('aria-label') || '')"))
    check("reduced motion: no GIF plays by itself, each has a Play button", loaded == 0 and buttons == DEMOS and len(names) == DEMOS and "" not in names,
          "%d loaded, %d buttons, %d distinct names" % (loaded, buttons, len(names)))
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


def commit_count(api, repo):
    """Commits on the default branch: ask for one per page and read the last page number."""
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):   # CI passes one: unauthenticated calls share 60 an hour per IP
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    r = api.get("https://api.github.com/repos/luke-zhang-cs-py/%s/commits?per_page=1" % repo, headers=headers, timeout=20000)
    if r.status != 200:
        return None
    last = re.search(r'[?&]page=(\d+)>; rel="last"', r.headers.get("link", ""))
    return int(last.group(1)) if last else len(r.json())


def check_commits(api, commits):
    """The commits figure: every project's count is a floor GitHub meets, and the headline is their sum, rounded down."""
    per_repo, shown = commits
    actual = {repo: commit_count(api, repo) for repo, _ in per_repo}
    short = [(repo, claimed, actual[repo]) for repo, claimed in per_repo if not claimed or actual[repo] is None or actual[repo] < claimed]
    floor = sum(c for _, c in per_repo) // 10 * 10
    check("the commits figure (%s) is a floor GitHub meets in every repo" % shown,
          not short and shown == "{:,}+".format(floor), short or {r: a for r, a in actual.items()})


def check_figures(api, cards):
    """Every figure in a card's results row must appear in that project's own README."""
    missing = []
    for repo, figures in cards:
        _, readme = fetch(api, "https://raw.githubusercontent.com/luke-zhang-cs-py/%s/main/README.md" % repo)
        missing += [(repo, fig) for fig in figures if fig not in readme]
    check("every figure on the page appears in its project's README (%d figures)" % sum(len(f) for _, f in cards), not missing, missing)


# The Nu validator's CSS checker predates container queries (CSS Containment Level 3, in every
# current browser since 2023) and reports the property and the at-rule as unknown. Only those.
VALIDATOR_LAGS = re.compile(r"^CSS: (“container”: Property “container” doesn't exist|Unrecognized at-rule “@container”)")


def check_valid_html(api):
    """The W3C Nu validator, on the page and the 404 page (both are public, so nothing is disclosed)."""
    errors = []
    for name in ("index.html", "404.html"):
        r = api.post("https://validator.w3.org/nu/?out=json", data=(ROOT / name).read_bytes(),
                     headers={"Content-Type": "text/html; charset=utf-8"}, timeout=30000)
        if r.status != 200: errors.append((name, "validator answered %s" % r.status)); continue
        errors += [(name, m.get("lastLine"), m["message"][:90]) for m in r.json()["messages"]
                   if m["type"] == "error" and not VALIDATOR_LAGS.search(m["message"])]
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
    browser = pw.chromium.launch(channel=os.environ.get("PW_CHANNEL") or None)   # PW_CHANNEL=msedge uses an installed Edge
    pg = open_page(browser, viewport={"width": WIDTHS[0], "height": 900}, color_scheme="light")
    check_structure(pg)
    check_components(pg)
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
    commits = pg.evaluate("[PROJECTS.map(p => [p.source.split('/').pop(), p.commits || 0]), document.querySelector('[data-commits]').textContent]")
    errors = close_page(pg)
    errors += check_theme(browser)
    errors += check_layout(browser)
    errors += check_motion(browser)
    check("no errors in the console, in any scenario", not errors, errors[:3])
    if not OFFLINE:
        api = pw.request.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0) portfolio-link-check")
        check_valid_html(api)
        check_figures(api, cards)
        check_commits(api, commits)
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
