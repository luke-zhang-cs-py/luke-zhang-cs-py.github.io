# Luke Zhang — Software Engineering Portfolio

[![checks](https://github.com/luke-zhang-cs-py/luke-zhang-cs-py.github.io/actions/workflows/checks.yml/badge.svg)](https://github.com/luke-zhang-cs-py/luke-zhang-cs-py.github.io/actions/workflows/checks.yml)
[![Live site](https://img.shields.io/badge/live-luke--zhang--cs--py.github.io-0F766E.svg)](https://luke-zhang-cs-py.github.io/)
[![No build step](https://img.shields.io/badge/HTML%20%2B%20CSS-no%20build%20step-blue.svg)](index.html)

Six projects in one place, each with a live demo that runs in your browser, what it does, what was measured,
and links to its write-up and source.

### ▶ [Open the portfolio →](https://luke-zhang-cs-py.github.io/)

![Scrolling the portfolio: the introduction, then Toronto Transit, Almanac and the chess coach with their demos playing, a switch to dark mode, then face recognition, the spam classifier, Tally, and the skills, education and contact sections](docs/demo.gif)

*Above: the live site, top to bottom. Each project's own demo plays inside its card, and the theme
switches to dark halfway. Recorded from the published page by
[`tools/record_demo.py`](tools/record_demo.py).*

If `github.io` is blocked on your network (some university wifi is), open [`index.html`](index.html) locally instead.

## The projects

| Project | What it is | Demo | Source |
|---|---|---|---|
| **Toronto Transit Reach** | Isochrone map and trip planner over the TTC's timetable and live feed | [live](https://luke-zhang-cs-py.github.io/Toronto-Transit-Distance-Matrix/app/) | [repo](https://github.com/luke-zhang-cs-py/Toronto-Transit-Distance-Matrix) |
| **Almanac** | Calendar and multi-role booking platform, Flask + JWT | [live](https://luke-zhang-cs-py.github.io/Almanac-Main-Full-Stack-Calendar/app/) | [repo](https://github.com/luke-zhang-cs-py/Almanac-Main-Full-Stack-Calendar) |
| **Dvoretsky Lab** | Chess coach with its own engine, built from a player's games | [live](https://luke-zhang-cs-py.github.io/Dvoerstky-AI-Chess-Coach/) | [repo](https://github.com/luke-zhang-cs-py/Dvoerstky-AI-Chess-Coach) |
| **Face Recognition Attendance** | Local OpenCV attendance, benchmarked for fairness on 97,698 faces | [live](https://luke-zhang-cs-py.github.io/Facial-Recognition-Software/camera/) | [repo](https://github.com/luke-zhang-cs-py/Facial-Recognition-Software) |
| **AI Spam Classifier** | TF-IDF classifier that shows which words drove each verdict | [live](https://luke-zhang-cs-py.github.io/AI-Spam-Message-Classifier/app/) | [repo](https://github.com/luke-zhang-cs-py/AI-Spam-Message-Classifier) |
| **Tally** | Phone-first expense capture in two taps | [live](https://luke-zhang-cs-py.github.io/tally/app/) | [repo](https://github.com/luke-zhang-cs-py/tally) |

## Run it

Double-click `index.html`. It's plain HTML and CSS with a little JavaScript: no build, no framework, nothing to install.

## Checks

```bash
pip install playwright && python -m playwright install chromium
python tests/check_site.py        # 21 checks in a real browser
python tools/record_demo.py       # re-record docs/demo.gif from the live site
python tools/make_og.py           # re-render og.png, the link-preview image
```

`check_site.py` covers:
- every section and project link;
- that all six demo GIFs load at their declared sizes;
- layout at 1280, 820 and 390 px;
- dark mode and that it's remembered;
- reduced motion;
- the link-preview tags;
- that every outbound link answers.

It also guards privacy: it fails if the phone number from the resume appears anywhere in the site. The number itself is stored only as a hash.

## Layout

```
index.html      the whole site
404.html        GitHub Pages' not-found page
og.png          1200×630 link preview (from tools/og.html)
favicon.svg
docs/demo.gif   the recording above
tests/          the browser check
tools/          the demo recorder and the preview renderer
```
