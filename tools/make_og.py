"""Renders og.png (the 1200x630 link-preview image) from tools/og.html."""
import pathlib
from playwright.sync_api import sync_playwright
here = pathlib.Path(__file__).resolve().parent
OG_SIZE = {"width": 1200, "height": 630}   # the size index.html's og:image tags declare


def main(out=here.parent / "og.png"):
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport=OG_SIZE)
        pg.goto((here / "og.html").as_uri()); pg.screenshot(path=str(out)); b.close()
    print("wrote og.png")


if __name__ == "__main__":
    main()
