# Luke Zhang — software engineering portfolio

A single-page portfolio: about, six projects (each with its demo, what it does, measured results and links to
the live demo, write-up and source), skills, education and contact. Plain HTML and CSS with a little JavaScript, no build
step. Open `index.html`, or visit the published site.

- **Demos** are loaded from each project's own GitHub Pages site, so they stay current when a project re-records its demo.
  Visitors who ask their system for reduced motion get a Play button instead of autoplaying GIFs.
- **Dark mode** follows the system setting and remembers a choice made with the toggle.
- **Link previews and search**: Open Graph and Twitter tags, a 1200×630 `og.png` (rebuilt with `python tools/make_og.py`),
  schema.org `Person` data, a favicon and a `404.html`.

```bash
pip install playwright && python -m playwright install chromium
python tests/check_site.py
```

The check covers:
- structure: every section in the nav, and every project's links;
- all six GIFs load at their declared sizes;
- layout at 1280, 820 and 390 px;
- dark mode and its memory, and reduced motion;
- the preview tags;
- every outbound link;
- a privacy guard: the phone number on the resume is stored only as a hash, and the check fails if it appears anywhere in the site.
