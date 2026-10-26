"""tools/make_og.py and tools/record_demo.py, with Playwright and Pillow stood in for.

No browser starts and no image is decoded: sys.modules gets a fake playwright.sync_api and a
fake PIL before each tool is imported, and the fakes record what the tool asked of them.

    python -m coverage run -m pytest -q tests && python -m coverage report
"""
import contextlib, importlib.util, pathlib, re, sys, types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FakePage:
    """A page 3,000 px tall in an 800 px window, where every section's top is 1,000 px down."""
    HEIGHT, VIEW, SECTION_TOP = 3000, 800, 1000.0

    def __init__(self, log, **kw):
        self.log, self.y = log, 0.0
        log.append(("new_page", kw))

    def goto(self, url, **kw):
        self.log.append(("goto", url, kw))

    def screenshot(self, path=None):
        self.log.append(("screenshot", path))
        if path: pathlib.Path(path).write_bytes(b"\x89PNG")
        return b"\x89PNG"

    def evaluate(self, js):
        self.log.append(("evaluate", js))
        if js == "window.scrollY": return self.y
        if js == "document.body.scrollHeight": return self.HEIGHT
        if js == "document.body.scrollHeight - innerHeight": return self.HEIGHT - self.VIEW
        if js.startswith("document.querySelector("): return self.SECTION_TOP
        assert js.startswith("window.scrollTo(0, "), js
        self.y = float(js[len("window.scrollTo(0, "):-1])

    def wait_for_timeout(self, ms):
        self.log.append(("wait", ms))

    def wait_for_function(self, js, timeout):
        self.log.append(("wait_for_function", js, timeout))


class FakePlaywright:
    def __init__(self, log):
        self.log = log
        self.chromium = types.SimpleNamespace(launch=self.launch)

    def launch(self):
        self.log.append(("launch",))
        return types.SimpleNamespace(new_page=lambda **kw: FakePage(self.log, **kw), close=lambda: self.log.append(("close",)))


class FakeImage:
    """Pillow's Image, as far as the recorder uses it."""
    def __init__(self, log, data):
        self.log, self.data = log, data

    def convert(self, mode):
        self.log.append(("convert", mode)); return self

    def resize(self, size, method):
        self.log.append(("resize", size, method)); return self

    def quantize(self, colors, method, dither):
        self.log.append(("quantize", colors, method, dither)); return self

    def save(self, out, **kw):
        self.log.append(("save", out, kw))
        pathlib.Path(out).write_bytes(b"GIF89a" + bytes(3 * 1024))


@pytest.fixture
def fakes(monkeypatch):
    """Installs the fake playwright and PIL; returns the log they write to."""
    log = []
    sync_api = types.ModuleType("playwright.sync_api")

    @contextlib.contextmanager
    def sync_playwright():
        log.append(("start",))
        yield FakePlaywright(log)
        log.append(("stop",))
    sync_api.sync_playwright = sync_playwright
    playwright = types.ModuleType("playwright"); playwright.sync_api = sync_api

    image = types.ModuleType("PIL.Image")
    image.open = lambda fp: FakeImage(log, fp.read())
    image.LANCZOS = "lanczos"
    image.Quantize = types.SimpleNamespace(MEDIANCUT="mediancut")
    image.Dither = types.SimpleNamespace(NONE="no dither")
    pil = types.ModuleType("PIL"); pil.Image = image

    for name, module in (("playwright", playwright), ("playwright.sync_api", sync_api), ("PIL", pil), ("PIL.Image", image)):
        monkeypatch.setitem(sys.modules, name, module)
    return log


def load(name):
    spec = importlib.util.spec_from_file_location("tool_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- make_og.py
def test_make_og_renders_og_html_at_the_declared_size(fakes, tmp_path, capsys):
    og = load("make_og")
    out = tmp_path / "og.png"
    og.main(out)
    assert fakes[:4] == [("start",), ("launch",), ("new_page", {"viewport": {"width": 1200, "height": 630}}),
                         ("goto", (ROOT / "tools" / "og.html").as_uri(), {})]
    assert fakes[4:] == [("screenshot", str(out)), ("close",), ("stop",)]
    assert out.read_bytes() == b"\x89PNG"
    assert capsys.readouterr().out == "wrote og.png\n"


def test_make_og_writes_the_root_og_png_by_default(fakes):
    # the image index.html's og:image points at, so the default must stay at the repo root
    assert load("make_og").main.__defaults__ == (ROOT / "og.png",)


# ---------------------------------------------------------------- record_demo.py
@pytest.mark.parametrize("argv, url, out", [
    ([], "https://luke-zhang-cs-py.github.io/", ROOT / "docs" / "demo.gif"),
    (["http://localhost:8000/"], "http://localhost:8000/", ROOT / "docs" / "demo.gif"),
    (["--out", "x.gif"], "https://luke-zhang-cs-py.github.io/", pathlib.Path("x.gif")),
    (["--out", "x.gif", "file:///site/index.html"], "file:///site/index.html", pathlib.Path("x.gif")),
    (["file:///site/index.html", "--out", "x.gif"], "file:///site/index.html", pathlib.Path("x.gif")),
])
def test_record_demo_reads_a_url_and_an_out_file_in_either_order(fakes, argv, url, out):
    rec = load("record_demo")
    assert rec.parse_args(argv) == (url, out)


def test_record_demo_leaves_the_callers_argv_alone(fakes):
    argv = ["--out", "x.gif", "u"]
    load("record_demo").parse_args(argv)
    assert argv == ["--out", "x.gif", "u"]


def test_glide_steps_evenly_and_grabs_a_frame_each_step(fakes):
    rec = load("record_demo")
    page, frames = FakePage(fakes), []
    page.y = 100.0
    rec.glide(frames, page, 500, steps=4, ms=110)
    scrolls = [e[1] for e in fakes if e[0] == "evaluate" and e[1].startswith("window.scrollTo")]
    assert scrolls == ["window.scrollTo(0, 200.0)", "window.scrollTo(0, 300.0)", "window.scrollTo(0, 400.0)", "window.scrollTo(0, 500.0)"]
    assert [ms for _, ms in frames] == [110] * 4
    assert ("resize", (880, 550), "lanczos") in fakes and ("convert", "RGB") in fakes


def test_top_of_asks_for_the_section_less_the_header(fakes):
    rec = load("record_demo")
    page = FakePage(fakes)
    assert rec.top_of(page, "#chess", 90) == FakePage.SECTION_TOP
    assert fakes[-1] == ("evaluate", "document.querySelector('#chess').getBoundingClientRect().top + window.scrollY - 90")


def test_dwell_waits_between_frames(fakes):
    rec = load("record_demo")
    page, frames = FakePage(fakes), []
    rec.dwell(frames, page, 3, 300)
    assert [ms for _, ms in frames] == [300] * 3
    assert [e for e in fakes if e[0] == "wait"] == [("wait", 250)] * 3


def test_record_walks_the_page_in_dark_mode_and_waits_for_every_gif(fakes):
    rec = load("record_demo")
    frames = rec.record("https://example.test/")
    assert ("new_page", {"viewport": {"width": 1280, "height": 800}, "color_scheme": "dark"}) in fakes
    assert ("goto", "https://example.test/", {"wait_until": "networkidle"}) in fakes
    # the warm-up scroll visits every 700 px of the 3,000 px page before recording starts
    whole = [e[1] for e in fakes if e[0] == "evaluate" and re.fullmatch(r"window\.scrollTo\(0, \d+\)", e[1])]
    assert whole == ["window.scrollTo(0, %d)" % y for y in (0, 700, 1400, 2100, 2800)] + ["window.scrollTo(0, 0)"]
    assert any(e[0] == "wait_for_function" and e[2] == 90000 for e in fakes)
    # intro, then about, seven projects, skills and the end: four glide frames each, plus the dwells
    stops = 1 + 7 + 1 + 1
    assert len(frames) == 1 + 4 * stops + 1 + 7 * rec.DEMO_FRAMES + 1 + 1
    assert frames[0][1] == rec.HOLD_MS["intro"] and frames[-1][1] == rec.HOLD_MS["end"]
    assert fakes[-2:] == [("close",), ("stop",)]


def test_save_quantizes_each_frame_and_writes_the_gif(fakes, tmp_path, capsys):
    rec = load("record_demo")
    out = tmp_path / "docs" / "demo.gif"
    frames = [(FakeImage(fakes, b""), 1600), (FakeImage(fakes, b""), 300), (FakeImage(fakes, b""), 2000)]
    rec.save(frames, out)
    assert [e for e in fakes if e[0] == "quantize"] == [("quantize", 128, "mediancut", "no dither")] * 3
    (_, path, kw), = [e for e in fakes if e[0] == "save"]
    assert path == out and kw["duration"] == [1600, 300, 2000] and kw["loop"] == 0 and len(kw["append_images"]) == 2
    assert capsys.readouterr().out == "wrote %s (3 KB, 3 frames, 3.9 s)\n" % out


def test_main_records_then_saves(fakes, monkeypatch, tmp_path):
    rec = load("record_demo")
    calls = []
    monkeypatch.setattr(rec, "record", lambda url: calls.append(("record", url)) or ["frames"])
    monkeypatch.setattr(rec, "save", lambda frames, out: calls.append(("save", frames, out)))
    rec.main(["u", "--out", str(tmp_path / "d.gif")])
    monkeypatch.setattr(sys, "argv", ["record_demo.py", "v"])
    rec.main()
    assert calls == [("record", "u"), ("save", ["frames"], tmp_path / "d.gif"),
                     ("record", "v"), ("save", ["frames"], rec.DEFAULT_OUT)]


def test_a_full_run_writes_a_gif(fakes, tmp_path):
    rec = load("record_demo")
    out = tmp_path / "demo.gif"
    rec.main(["https://example.test/", "--out", str(out)])
    assert out.read_bytes().startswith(b"GIF89a")
