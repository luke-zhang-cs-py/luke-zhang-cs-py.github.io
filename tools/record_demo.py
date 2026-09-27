"""Records docs/demo.gif from the live site.

    python tools/record_demo.py [url]      (default: the published site)

One browser, real waits: the page loads, scrolls from the introduction through the
projects (pausing on each so its own demo GIF plays), switches to dark mode, and
carries on to skills, education and contact. Frames are captured at 1280x800 and
saved at 880x550.
"""
import io, pathlib, sys
from PIL import Image
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://luke-zhang-cs-py.github.io/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "demo.gif"
SIZE = (880, 550)
frames = []   # (image, ms)

def grab(pg, ms):
    img = Image.open(io.BytesIO(pg.screenshot())).convert("RGB").resize(SIZE, Image.LANCZOS)
    frames.append((img, ms))

def glide(pg, to_y, steps=4, ms=110):
    start = pg.evaluate("window.scrollY")
    for i in range(1, steps + 1):
        pg.evaluate(f"window.scrollTo(0, {start + (to_y - start) * i / steps})")
        pg.wait_for_timeout(60)
        grab(pg, ms)

def top_of(pg, sel, offset=70):
    return pg.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top + window.scrollY - {offset}")

def dwell(pg, count, ms, gap=250):
    for _ in range(count):
        pg.wait_for_timeout(gap)
        grab(pg, ms)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 800}, color_scheme="light")
    pg.goto(URL, wait_until="networkidle")
    # let every demo GIF arrive before recording, so none appears half-loaded
    for y in range(0, pg.evaluate("document.body.scrollHeight"), 700):
        pg.evaluate(f"window.scrollTo(0, {y})"); pg.wait_for_timeout(150)
    pg.wait_for_function("[...document.querySelectorAll('.shot img')].every(i => i.complete && i.naturalWidth)", timeout=90000)
    pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(600)

    grab(pg, 1600)                                  # the introduction
    glide(pg, top_of(pg, "#about")); dwell(pg, 1, 1300)
    for pid in ("#transit", "#almanac", "#chess"):  # three projects, their GIFs playing
        glide(pg, top_of(pg, pid, 90)); dwell(pg, 4, 300)
    pg.click("#themeBtn"); pg.wait_for_timeout(300)  # dark mode
    grab(pg, 1200)
    for pid in ("#faces", "#spam", "#tally"):
        glide(pg, top_of(pg, pid, 90)); dwell(pg, 4, 300)
    glide(pg, top_of(pg, "#skills")); dwell(pg, 1, 1300)
    glide(pg, pg.evaluate("document.body.scrollHeight - innerHeight")); dwell(pg, 1, 2000)
    b.close()

OUT.parent.mkdir(exist_ok=True)
# each frame its own palette: light mode, dark mode and six different demo GIFs share none
pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f, _ in frames]
pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=[ms for _, ms in frames], loop=0, optimize=True)
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(frames)} frames, {sum(ms for _, ms in frames) / 1000:.1f} s)")
