# Code audit

## 2026-10-05

Baseline `python tests/check_site.py`: **49 passed, 0 failed**, plus a
`SyntaxWarning` from the suite itself. After: **49 passed, 0 failed**, no
warnings. The count of checks is unchanged, so the README's "49 checks"
still holds.

### Bugs fixed

| Bug | Kind | Check that covers it |
|---|---|---|
| **The privacy guard published what it guarded.** `check_site.py` held an unsalted SHA-256 of the resume's ten-digit phone number. A ten-digit number has only 10^10 candidates, so the hash reverses to the number in seconds on a laptop. Since the site publishes no phone number at all, the guard now fails on *any* phone-shaped string, checks itself against a fictional 555-01xx number, and prints only a count, because CI logs on a public repo are public too. | security (PII in a public repo) | "privacy: the resume's phone number is nowhere in the site" |
| **Seven identical "▶ Play demo" buttons.** In reduced-motion mode every card's button had the same accessible name, so a screen reader's list of buttons could not tell them apart. Each one is now named "Play demo: <project>", which keeps the visible text in the name (WCAG 2.5.3). | accessibility | "reduced motion: no GIF plays by itself, each has a Play button" now also requires 7 distinct names. It failed (1 distinct name) before the fix. |
| **`"\d"` in a non-raw Python string** (the contrast checker's JS). Python 3.12 warns about it and a later version will make it a syntax error, which would break CI on a runner upgrade. The string is now raw, and the JS it produces is the same. | adaptive | the whole suite (it would fail to import) |

**Still exposed: the hash is in git history** (added in 22fa4bd,
2026-09-27). History was not rewritten. Treat that number as public and
decide whether that matters to you.

### Resume / phone number

There is no separate resume page or PDF in this repo. The only contact
details published are the GitHub and LinkedIn profiles and the university
email, all of which are deliberate. No phone-shaped string appears anywhere
in the site's text files.

### Links

All 25 links on the page answer (the suite's own check), and so do the 19
distinct URLs in README.md (checked by hand with curl, all 200). The skip
link and the `#top`, `#main` and section anchors all resolve.

### Accessibility basics

Already covered by the suite and passing: `lang`, one h1 with headings in
order, skip link first in tab order, `aria-pressed` filters, a labelled
combobox/listbox palette, labelled form fields, alt text on every image,
WCAG AA contrast in both themes, no sideways scroll at 360-1280 px, and
reduced motion. The one gap found was the Play button names above.

### Checklist

* **Dispensables**: the `hashlib` import went with the hash. Nothing else
  is dead.
* **Bloaters**: `check_site.py` (460 lines) is one script of check
  functions, which is in proportion to what it checks.
* **Abusers / couplers / change preventers**: none. Content lives in four
  arrays (`PROFILE`, `PROJECTS`, `SKILLS`, commands) that the markup is
  rendered from, which is the right shape.
* **Security (XSS)**: `innerHTML` is used only with the page's own constant
  arrays. `PROFILE.role`, `bio` and `impact` are deliberately raw HTML
  written by the author, and everything else goes through `esc()`. The
  palette's search text is never echoed into markup.
* **Magic numbers / naming**: nothing worth changing.

### Coverage (`python tests/check_site.py --coverage`)

| File | JS lines | CSS rules |
|---|---|---|
| index.html | 362 / 362 (100%) | 157 / 157 (100%) |

404.html has no script and is checked only for existing. `tools/` (OG image
and demo recorder) is not exercised by the suite.

### Maintenance types

* **Corrective**: the brute-forceable phone hash, and the Play button names.
* **Adaptive**: the invalid escape that a future Python will reject.
* **Perfective**: the Play buttons are distinguishable for screen-reader
  users.
* **Preventive**: the privacy check is stricter (any phone shape) and has a
  negative control, and the Play check now pins distinct names.

### Left for later

* The phone hash in history, above. Only the author can decide whether a
  history rewrite is worth it.
* `tools/record_demo.py` and `tools/make_og.py` have no checks of their
  own. Their outputs (the GIF and og.png) are checked for size and existing.
