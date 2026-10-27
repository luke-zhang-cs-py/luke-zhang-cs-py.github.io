"""Checks the portfolio in a real browser.

    python tests/check_site.py [--shots DIR] [--coverage coverage.html] [--offline]

Structure, the demo GIFs, the nav, the command palette and the contact form, dark mode, layout
at four widths, reduced motion, print, blocked storage and missing browser features, edited
content, the link preview, valid dates, a privacy guard, that the page's figures add up and match
each project's own README, that the README states the right number of checks, that every
outbound link answers, and that the W3C validator finds no errors. --offline skips the four
checks that need the network.

Every scenario runs under V8 block coverage, and one check fails unless every line, branch and
function of the page's own JavaScript ran in at least one of them. --coverage also writes an
HTML report of which lines and branches ran and which CSS rules were used (Chrome's rule usage).
"""
import base64, html as htmllib, json, os, pathlib, re, sys
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
    """Per page: V8 block coverage of the page's own scripts and Chrome's CSS rule usage, merged by source.

    Lines: a line ran if its first character did. Branches: every block V8 counts on its own (each
    arm of an if/else and of ?:, the right side of && and ||, a catch, a loop body, and the code
    after an early return), hit if it ran in any scenario. V8 reports a block only when its count
    differs from the code around it, so an if with no else adds one branch, not two, and a block
    that always ran exactly as often as its surroundings is never listed, because it cannot have
    been missed. Functions: every function's own range."""
    def __init__(self):
        self.js = {}         # script source -> covered flag per character
        self.blocks = {}     # script source -> {(start, end)} block ranges V8 reported
        self.funcs = {}      # script source -> {(start, end): name}
        self.at = {}         # script source -> the index.html line it starts on, less one
        self.css = {}        # stylesheet text -> {(start, end): used}
        self.sessions = {}   # page -> (cdp session, {scriptId: (url, first line)})

    def attach(self, pg):
        s = pg.context.new_cdp_session(pg)
        scripts = {}
        s.on("Debugger.scriptParsed", lambda e: scripts.__setitem__(e["scriptId"], (e["url"], e["startLine"])))
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
        for script in s.send("Profiler.takePreciseCoverage")["result"]:
            url, at = scripts.get(script["scriptId"], (None, 0))
            if url != PAGE: continue
            src = s.send("Debugger.getScriptSource", {"scriptId": script["scriptId"]})["scriptSource"]
            self.at[src] = at
            spans = []   # (start, end, ran)
            for f in script["functions"]:
                rs = [(r["startOffset"], min(r["endOffset"], len(src)), r["count"] > 0) for r in f["ranges"]]
                spans += rs
                self.funcs.setdefault(src, {})[rs[0][:2]] = f["functionName"]
                if f["isBlockCoverage"]:
                    self.blocks.setdefault(src, set()).update(r[:2] for r in rs[1:])
            flags = [False] * len(src)
            # outer ranges first, so a nested range always overrides the one around it
            for a, b, ran in sorted(spans, key=lambda r: (r[0], -r[1])):
                flags[a:b] = [ran] * (b - a)
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

    def spans(self, table):
        """(ran, where, text) per block or function: it ran if any of its characters did in any scenario."""
        out = []
        for src, spans in table.items():
            flags = self.js[src]
            names = spans if isinstance(spans, dict) else {}
            for a, b in sorted(spans):
                text = src[a:b].split("\n")[0].strip()[:80]
                name = names.get((a, b)) or ""
                out.append((any(flags[a:b]), "index.html line %d" % (self.at[src] + src.count("\n", 0, a) + 1), (name + ": " if name else "") + text))
        return out

    def summary(self):
        code = [r for r in self.lines() if r[0] is not None]
        branches, funcs = self.spans(self.blocks), self.spans(self.funcs)
        return {"lines": (sum(r[0] for r in code), len(code)),
                "branches": (sum(r[0] for r in branches), len(branches)),
                "functions": (sum(r[0] for r in funcs), len(funcs)),
                "missed": [(kind, where, text) for kind, rows in (("branch", branches), ("function", funcs))
                           for ran, where, text in rows if not ran]}

    def complete(self):
        """Whether every line, branch and function ran, and the figures."""
        s = self.summary()
        return bool(self.js) and all(s[k][0] == s[k][1] for k in ("lines", "branches", "functions")), s

    def report(self, out):
        rows, s = self.lines(), self.summary()
        rules = [(text[a:b].split("{")[0].strip(), used) for text, rs in self.css.items() for (a, b), used in sorted(rs.items())]
        used = sum(u for _, u in rules)
        pct = lambda hit, n: 100 * hit / max(n, 1)
        figures = " · ".join("<b>JavaScript %s: %d of %d (%.1f%%)</b>" % (k, s[k][0], s[k][1], pct(*s[k])) for k in ("lines", "branches", "functions"))
        listing = "".join('<div class="%s"><span>%s</span>%s</div>' % ("gap" if r is None else ("hit" if r else "miss"),
                          "" if r is None else ("✓" if r else "✗"), htmllib.escape(l) or "&nbsp;") for r, l in rows)
        missed = "".join("<li>%s, %s: <code>%s</code></li>" % (k, w, htmllib.escape(t)) for k, w, t in s["missed"]) or "<li>none</li>"
        unused = "".join("<li><code>%s</code></li>" % htmllib.escape(sel) for sel, u in rules if not u) or "<li>none</li>"
        pathlib.Path(out).write_text(f"""<!DOCTYPE html><html lang="en"><meta charset="utf-8"><title>Portfolio coverage</title>
<style>body{{font:14px system-ui;margin:24px;max-width:1100px}}h1{{font-size:20px}}.sum b{{font-size:17px}}
pre{{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto}}pre div{{white-space:pre}}
pre span{{display:inline-block;width:1.6em;color:#888}}.hit{{background:#e6ffec}}.miss{{background:#ffebe9}}.gap{{height:10px}}</style>
<h1>Portfolio coverage: tests/check_site.py</h1>
<p class="sum">{figures} · <b>CSS: {used} of {len(rules)} rules used ({pct(used, len(rules)):.1f}%)</b></p>
<p>Merged across every scenario the check drives: desktop, the palette and the form by keyboard and mouse, the system
theme changing, the toggle, a reload, a dark system, 820, 390 and 360 px, print, reduced motion with Play, blocked
storage with no IntersectionObserver and a clipboard that refuses, and edited content. Branches are the blocks V8 counts
on their own: each arm of an if/else and of ?:, the right side of &amp;&amp; and ||, a catch, and the code after an early return.</p>
<h2>Branches and functions never run</h2><ul>{missed}</ul>
<h2>JavaScript</h2><pre>{listing}</pre><h2>CSS rules never used</h2><ul>{unused}</ul></html>""", encoding="utf-8")
        print("\nCoverage: JavaScript %s; CSS %d/%d rules (%.1f%%) -> %s" % (", ".join(
            "%s %d/%d (%.1f%%)" % (k, s[k][0], s[k][1], pct(*s[k])) for k in ("lines", "branches", "functions")),
            used, len(rules), pct(used, len(rules)), out))
        for sel, u in rules:
            if not u: print("  CSS never used: " + sel)
        for ran, line in rows:
            if ran is False: print("  JS never ran:  " + line.strip())
        for kind, where, text in s["missed"]:
            print("  JS %s never ran (%s): %s" % (kind, where, text))


# Always on: the check that every line, branch and function of the page's script ran needs it.
# --coverage adds the HTML report.
COV = Coverage()


def open_page(browser, init=None, offsite=None, **kw):
    """A fresh context on the page; init is a script run before the page's own (to change its world),
    and offsite, if given, handles every request that isn't for a local file."""
    context = browser.new_context(**kw)
    if offsite: context.route(lambda url: not url.startswith("file:"), offsite)
    pg = context.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    if init: pg.add_init_script(init)
    COV.attach(pg)
    pg.goto(PAGE)
    return pg


def reload_page(pg):
    COV.snapshot(pg)
    pg.reload()


def close_page(pg):
    """Closes the page and returns its console errors."""
    COV.collect(pg)
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
    check("%d projects, each with a live demo, a write-up or guide, and its source" % DEMOS,
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
    pg.fill("#cfName", "Ada"); pg.fill("#cfEmail", "ada@example"); pg.fill("#cfMessage", "Hello & welcome")
    pg.click("#contactForm button[type=submit]")
    partial = (pg.text_content("#formStatus"), pg.evaluate("document.activeElement.id"), pg.get_attribute("#cfName", "aria-invalid"))
    pg.fill("#cfEmail", "ada@example.com")
    pg.click("#contactForm button[type=submit]"); pg.wait_for_timeout(300)
    mailto = pg.evaluate("document.getElementById('contactForm').dataset.mailto || ''")
    check("the contact form refuses to send empty, and marks what's missing", empty[0] == "true" and "fill in" in empty[1], empty)
    check("an email address with no domain is named as the problem, and focused",
          partial == ("That email address looks incomplete.", "cfEmail", "false"), partial)
    check("a filled-in form becomes an email to Luke with the message in it",
          mailto.startswith("mailto:zhang.l17@northeastern.edu?subject=Portfolio%3A%20message%20from%20Ada") and "Hello%20%26%20welcome" in mailto, mailto[:90])


def check_palette(pg):
    """The palette by mouse, its edge cases, and the commands that change the theme or leave the page."""
    is_open = lambda: pg.evaluate("document.getElementById('palette').open")
    selected = lambda: pg.evaluate("document.querySelector('#paletteList [aria-selected=\"true\"]').id")
    command = lambda query: (pg.keyboard.press("Control+k"), pg.keyboard.type(query), pg.keyboard.press("Enter"))

    pg.keyboard.press("Control+k"); pg.keyboard.press("Control+k")
    toggled = not is_open()
    pg.click("#paletteBtn"); pg.keyboard.type("pro")
    by_button = is_open()
    pg.evaluate("document.getElementById('paletteBtn').click()")   # asked to open while open: nothing restarts
    kept = pg.input_value("#paletteInput")
    check("Ctrl+K again closes the palette, the header button opens it, and opening it twice keeps what was typed",
          toggled and by_button and kept == "pro", (toggled, by_button, kept))

    pg.fill("#paletteInput", "")
    last = "cmd-%d" % (pg.locator("#paletteList li").count() - 1)
    pg.keyboard.press("ArrowUp")
    check("ArrowUp from the first command wraps round to the last", selected() == last, (selected(), last))

    pg.fill("#paletteInput", "zzzz")
    nothing = pg.evaluate("""[!document.getElementById('paletteEmpty').hidden, document.getElementById('paletteInput').hasAttribute('aria-activedescendant'),
                              document.querySelectorAll('#paletteList li').length]""")
    pg.keyboard.press("Enter")
    check("a search that matches nothing says so, and Enter then does nothing", nothing == [True, False, 0] and is_open(), nothing)

    pg.fill("#paletteInput", "")
    pg.click("#paletteInput"); pg.click("#paletteList", position={"x": 2, "y": 2})   # the list's padding, between items
    inside = is_open()
    pg.mouse.click(4, 4)   # the backdrop
    check("clicks inside the palette leave it open, and a click on the backdrop closes it", inside and not is_open(), inside)

    pg.click('.chip[data-filter="Computer vision"]')
    pg.keyboard.press("Control+k"); pg.keyboard.type("tally")
    pg.locator("#paletteList li").first.click(); pg.wait_for_timeout(1500)
    tally = pg.evaluate("""[document.querySelectorAll('.project:not([hidden])').length,
                            (r => r.top < innerHeight && r.bottom > 0)(document.getElementById('tally').getBoundingClientRect())]""")
    check("clicking a project in the palette clears the filter and goes to its card", tally == [DEMOS, True] and not is_open(), tally)

    theme = lambda: pg.evaluate("document.documentElement.dataset.theme")
    start, flips = theme(), []
    for _ in range(2):
        command("switch theme"); flips.append(theme())
    check("the palette's Switch theme command switches the theme, and back", flips == [{"dark": "light", "light": "dark"}[start], start], (start, flips))


def check_leaving(browser):
    """The palette commands that leave the page, each in a context of its own that is closed after.

    Nothing reaches the network. The navigation a command starts is recorded and cancelled
    (net::ERR_ABORTED, which Chromium treats as a navigation that never happened on every
    platform), so the page stays put with its coverage readable, and nothing is left pending:
    the nav link is clicked afterwards with a short timeout to prove it. The demo GIFs the page
    asks for get a blank 1x1 GIF, so no failed load reaches the console."""
    errors, asked = [], []
    for query, target in (("open the tally demo", "PROJECTS.find(p => p.id === 'tally').demo"),
                          ("open github", "PROFILE.links.find(l => l.label === 'GitHub').url"),
                          ("open linkedin", "PROFILE.links.find(l => l.label === 'LinkedIn').url")):
        went = []
        def offsite(route):
            if route.request.is_navigation_request():
                went.append(route.request.url); route.abort("aborted")
            else:
                route.fulfill(status=200, content_type="image/gif", body=BLANK_GIF)
        pg = open_page(browser, offsite=offsite, viewport={"width": 1280, "height": 900})
        wanted = pg.evaluate(target)
        pg.keyboard.press("Control+k"); pg.keyboard.type(query); pg.keyboard.press("Enter")
        for _ in range(50):
            if went: break
            pg.wait_for_timeout(100)
        stayed = pg.url == PAGE and pg.evaluate("typeof PROJECTS") == "object"
        try:
            pg.click('.bar nav a[href="#about"]', timeout=5000); free = True
        except Exception as e:   # a navigation still pending would hold this click
            free = str(e).split("\n")[0][:80]
        asked.append((wanted, went, stayed, free))
        errors += close_page(pg)
    check("the palette's demo, GitHub and LinkedIn commands go to those pages, and the page is free after",
          all(went == [wanted] and stayed and free is True for wanted, went, stayed, free in asked), asked)
    return errors


BLANK_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")   # the page's own STILL


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
    # Polled from here, not with wait_for_function: its string predicate is eval'd in the page, which the CSP refuses.
    for _ in range(240):
        if pg.evaluate("[...document.querySelectorAll('.shot img')].every(i => i.complete && i.naturalWidth)"):
            break
        pg.wait_for_timeout(250)
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
    # Two scroll events inside one frame: the nav is worked out once, on the next frame, not twice.
    frames = pg.evaluate("""() => { const raf = window.requestAnimationFrame; let n = 0;
        window.requestAnimationFrame = f => { n++; return raf.call(window, f); };
        try { dispatchEvent(new Event('scroll')); dispatchEvent(new Event('scroll')); } finally { window.requestAnimationFrame = raf; }
        return n; }""")
    check("scroll events within one frame update the nav once", frames == 1, "%s frames asked for" % frames)


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
    pg.click("#themeBtn"); pg.wait_for_timeout(400)
    check("the button switches back to dark, and remembers that too",
          theme() == "dark" and pg.evaluate("localStorage.getItem('theme')") == "dark" and toolbar() == "#0B1220", toolbar())
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
    grid = p.evaluate("""() => {
      const g = document.querySelector('#projectList .grid'), cards = [...g.children];
      const cols = getComputedStyle(g).gridTemplateColumns.split(' ').length;
      const cells = cards.reduce((n, c) => n + (c.classList.contains('featured') ? 2 : 1), 0);
      const rows = new Set(cards.map(c => Math.round(c.getBoundingClientRect().top))).size;
      const f = document.querySelector('.project.featured').getBoundingClientRect(), o = cards[1].getBoundingClientRect();
      return {cols, cells, rows, wide: Math.round(f.width / o.width * 10) / 10, first: cards[0].id, tall: Math.round(f.height / o.height * 100) / 100};
    }""")
    check("at 1280 px the projects fill whole rows of three, the transit card taking two cells",
          grid["cols"] == 3 and grid["cells"] % 3 == 0 and grid["rows"] == grid["cells"] // 3 and grid["wide"] >= 2 and grid["first"] == "transit", grid)
    check("the transit card is no taller than the card beside it", grid["tall"] <= 1.02, grid)
    if SHOTS:
        p.locator("#projectList").screenshot(path=SHOTS + "/pf-grid.png")
    p.emulate_media(media="print"); p.wait_for_timeout(200)
    check("print leaves out the header, demos and buttons",
          p.evaluate("['.bar', '.shot', '.links'].every(s => getComputedStyle(document.querySelector(s)).display === 'none')"))
    return errors + close_page(p)


def check_motion(browser):
    rm = open_page(browser, viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    rm.wait_for_timeout(300)
    loaded = rm.evaluate("[...document.querySelectorAll('.shot img')].filter(i => i.currentSrc.endsWith('.gif')).length")
    buttons = rm.locator(".play:visible").count()
    # Buttons all named "Play demo" are indistinguishable in a screen reader's list of buttons.
    names = set(rm.evaluate("[...document.querySelectorAll('.play')].map(b => b.getAttribute('aria-label') || '')"))
    check("reduced motion: no GIF plays by itself, each has a Play button", loaded == 0 and buttons == DEMOS and len(names) == DEMOS and "" not in names,
          "%d loaded, %d buttons, %d distinct names" % (loaded, buttons, len(names)))
    # A hidden still takes no room: the featured card's demo at two columns is not a tall empty box.
    rm.set_viewport_size({"width": 760, "height": 900}); rm.wait_for_timeout(300)
    ghost = rm.evaluate("[...document.querySelectorAll('.shot img[hidden]')].filter(i => i.getBoundingClientRect().height > 0).length")
    check("reduced motion: a hidden demo takes no room at any width", ghost == 0, "%d hidden images still laid out" % ghost)
    rm.set_viewport_size({"width": 1280, "height": 900}); rm.wait_for_timeout(300)
    rm.locator(".play").first.click(); rm.wait_for_timeout(800)
    check("reduced motion: Play shows that demo",
          rm.evaluate("document.querySelector('.shot img').currentSrc.endsWith('.gif') && !document.querySelector('.shot img').hidden"))
    rm.keyboard.press("Control+k"); rm.keyboard.type("skills"); rm.keyboard.press("Enter"); rm.wait_for_timeout(100)
    check("reduced motion: the palette jumps to a section at once, with no smooth scroll",
          rm.evaluate("Math.abs(document.getElementById('skills').getBoundingClientRect().top) < 120"))
    return close_page(rm)


# Storage that throws (a private window, blocked site data), a browser with no IntersectionObserver,
# and a clipboard that refuses the write.
BLOCKED = """
for (const m of ['getItem', 'setItem']) Storage.prototype[m] = function () { throw new DOMException('blocked', 'SecurityError'); };
delete window.IntersectionObserver;
Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('refused')) } });
"""


def check_fallbacks(browser):
    f = open_page(browser, init=BLOCKED, viewport={"width": 1280, "height": 900})
    theme = lambda: f.evaluate("document.documentElement.dataset.theme")
    check("without IntersectionObserver every section is simply shown, with no scrolling",
          f.evaluate("[...document.querySelectorAll('.reveal')].every(e => e.classList.contains('in'))"))
    opened = theme()
    f.click("#themeBtn"); switched = theme()
    reload_page(f)
    check("with storage blocked the page opens dark, the button still switches, and a reload is dark again",
          (opened, switched, theme()) == ("dark", "light", "dark"), (opened, switched, theme()))
    f.keyboard.press("Control+k"); f.keyboard.type("copy my email"); f.keyboard.press("Enter"); f.wait_for_timeout(200)
    status = f.text_content("#formStatus")
    check("Copy my email address still answers when the clipboard refuses", "Copied zhang.l17@northeastern.edu" in status, status)
    return close_page(f)


# The content arrays edited before the page renders: no photo, no status, the LinkedIn link
# removed, and one project with no test count, no commit count and no live demo.
EDITED = """
const trap = (name, edit) => { let v; Object.defineProperty(window, name, { configurable: true, get: () => v, set: x => { v = edit(x); } }); };
trap('PROFILE', p => Object.assign(p, { photo: '', status: '', links: p.links.filter(l => l.label !== 'LinkedIn') }));
trap('PROJECTS', ps => ps.map(p => p.id !== 'tally' ? p : Object.assign(p, {
  demo: '', commits: undefined, impact: p.impact.map(i => ({ html: i.html.replace(' data-tests', '') })) })));
"""


def check_edited_content(browser):
    e = open_page(browser, init=EDITED, viewport={"width": 1280, "height": 900})
    v = e.evaluate("""({avatar: document.getElementById('avatar').textContent, photo: !!document.querySelector('#avatar img'),
        status: !!document.querySelector('#who .open'), linkedin: !!document.querySelector('a[href*="linkedin.com"]'),
        first: document.querySelector('#stats span').textContent,
        total: +document.querySelector('[data-tests-total]').textContent.replace(/,/g, ''),
        parts: [...document.querySelectorAll('[data-tests]')].map(b => +b.textContent.replace(/,/g, '')),
        commits: document.querySelector('[data-commits]').textContent,
        floor: Math.floor(PROJECTS.reduce((n, p) => n + (p.commits || 0), 0) / 10) * 10})""")
    e.keyboard.press("Control+k"); e.keyboard.type("open ")
    links = e.evaluate("[...document.querySelectorAll('#paletteList li')].map(li => li.firstChild.textContent).filter(t => /^Open (GitHub|LinkedIn)$/.test(t))")
    check("edited content: no photo shows the initials, no status shows none, and a removed link takes its command with it",
          (v["avatar"], v["photo"], v["status"], v["linkedin"], links) == ("LZ", False, False, False, ["Open GitHub"]), (v, links))
    check("edited content: a project with no test or commit count adds nothing to the totals, and one with no demo drops the live-demos claim",
          len(v["parts"]) == DEMOS - 1 and v["total"] == sum(v["parts"]) and v["commits"] == "{:,}+".format(v["floor"])
          and v["first"] == "open-source projects", v)
    return close_page(e)


def fetch(api, url):
    try:
        r = api.get(url, timeout=20000)
        return r.status, (r.text() if r.status == 200 else "")
    except Exception as e:
        return str(e)[:80], ""


class CommitCountUnavailable(Exception):
    """GitHub didn't give a count, so the figure couldn't be checked (as opposed to failing the check)."""


def commit_count(api, repo):
    """Commits on the default branch: ask for one per page and read the last page number."""
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):   # CI passes one: unauthenticated calls share 60 an hour per IP
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    r = api.get("https://api.github.com/repos/luke-zhang-cs-py/%s/commits?per_page=1" % repo, headers=headers, timeout=20000)
    if r.status != 200:
        # Say why: a refusal (403 with no requests left is the hourly limit for unauthenticated calls) is not a wrong figure.
        limited = r.status == 403 and r.headers.get("x-ratelimit-remaining") == "0"
        raise CommitCountUnavailable("GitHub's hourly API limit is used up; set GITHUB_TOKEN" if limited else "GitHub answered HTTP %s" % r.status)
    last = re.search(r'[?&]page=(\d+)>; rel="last"', r.headers.get("link", ""))
    return int(last.group(1)) if last else len(r.json())


def check_commits(api, commits):
    """The commits figure: every project's count is a floor GitHub meets, and the headline is their sum, rounded down."""
    per_repo, shown = commits
    try:
        actual = {repo: commit_count(api, repo) for repo, _ in per_repo}
    except CommitCountUnavailable as e:
        check("the commits figure (%s) could be checked against GitHub" % shown, False, str(e))
        return
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
    check_palette(pg)
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
    errors += check_leaving(browser)
    errors += check_fallbacks(browser)
    errors += check_edited_content(browser)
    check("no errors in the console, in any scenario", not errors, errors[:3])
    full, cov = COV.complete()
    check("every line, branch and function of the page's own JavaScript ran (%s)" % ", ".join(
          "%d/%d %s" % (cov[k][0], cov[k][1], k) for k in ("lines", "branches", "functions")), full, cov["missed"][:4])
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

if COVERAGE_OUT: COV.report(COVERAGE_OUT)
failed = sum(not ok for _, ok in results)
print("%d passed, %d failed" % (len(results) - failed, failed))
sys.exit(1 if failed else 0)
