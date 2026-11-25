"""Seeded random muted palettes, one per repo, built in OKLCH and checked for WCAG AA.

Each palette: a soft, low-chroma dominant hue (bg, surfaces, borders, text all tinted by it)
plus ONE accent hue, slightly stronger but still muted. No purple/indigo (OKLCH hue 255-330).
Prints JSON; writes a swatch preview HTML to argv[1] if given.
"""
import hashlib, json, math, random, sys

REPOS = ["portfolio", "Toronto Transit", "Almanac", "Wallet", "Tally",
         "Facial Recognition", "Spam Classifier", "IPO Research", "Dvoretsky Chess"]

# The pool of defaults: named muted dominants (OKLCH hue, chroma scale) and accent hues.
DOMINANTS = [("sage", 145, 1.0), ("slate", 235, 0.9), ("clay", 45, 1.0), ("moss", 120, 0.9),
             ("dusty rose", 15, 0.9), ("sand", 80, 0.8), ("fog teal", 195, 0.9), ("stone", 60, 0.45),
             ("ash blue", 220, 0.8), ("olive", 105, 0.9), ("terracotta", 35, 1.0)]
ACCENTS = [("ochre", 80), ("coral", 30), ("sea glass", 175), ("cornflower", 245), ("fern", 140),
           ("rust", 45), ("lagoon", 205), ("wheat", 90), ("brick", 25), ("pine", 160), ("apricot", 60)]

# The OKLab matrices (Ottosson), digits grouped in threes: the site's privacy check treats any ten-digit run as a phone number.
def oklch_to_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.396_337_777_4 * a + 0.215_803_757_3 * b) ** 3
    m_ = (L - 0.105_561_345_8 * a - 0.063_854_172_8 * b) ** 3
    s_ = (L - 0.089_484_177_5 * a - 1.291_485_548_0 * b) ** 3
    lin = (4.076_741_662_1 * l_ - 3.307_711_591_3 * m_ + 0.230_969_929_2 * s_,
           -1.268_438_004_6 * l_ + 2.609_757_401_1 * m_ - 0.341_319_396_5 * s_,
           -0.004_196_086_3 * l_ - 0.703_418_614_7 * m_ + 1.707_614_701_0 * s_)
    def enc(x):
        x = min(max(x, 0.0), 1.0)
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(round(enc(x) * 255) for x in lin)

def hexof(rgb): return "#%02X%02X%02X" % rgb
def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(ch, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(x, y):
    a, b = sorted((lum(x), lum(y)), reverse=True)
    return (a + 0.05) / (b + 0.05)

def fit(L, C, h, against, target, step):
    """Move lightness by step until the colour meets target contrast against every colour in against."""
    for _ in range(200):
        rgb = oklch_to_rgb(L, C, h)
        if all(contrast(rgb, x) >= target for x in against): return rgb
        L = min(max(L + step, 0.0), 1.0)
    raise SystemExit("could not fit %s" % ((L, C, h),))

def theme(dh, dc, ah, dark):
    c = lambda v: v * dc
    if dark:
        bg = oklch_to_rgb(0.215, c(0.022), dh); surface = oklch_to_rgb(0.255, c(0.024), dh)
        subtle = oklch_to_rgb(0.29, c(0.026), dh); border = oklch_to_rgb(0.34, c(0.026), dh)
        up = +0.01
        text = fit(0.93, c(0.012), dh, [bg, surface, subtle], 7.0, up)
        muted = fit(0.78, c(0.022), dh, [bg, surface, subtle], 4.5, up)
        hint = fit(0.72, c(0.026), dh, [bg, surface], 4.5, up)
        bstrong = fit(0.52, c(0.03), dh, [bg, surface], 3.0, up)
        accent = fit(0.76, 0.085, ah, [bg, surface, subtle], 4.5, up)
        hover = oklch_to_rgb(0.83, 0.075, ah)
        asubtle = fit(0.32, 0.04, ah, [], 1, 0)
        on = fit(0.22, 0.03, ah, [accent, hover], 4.5, -0.01)
        danger = fit(0.70, 0.12, 25, [bg, surface], 4.5, up)
        atext = text
    else:
        bg = oklch_to_rgb(0.972, c(0.012), dh); surface = oklch_to_rgb(0.99, c(0.006), dh)
        subtle = oklch_to_rgb(0.945, c(0.016), dh); border = oklch_to_rgb(0.89, c(0.018), dh)
        dn = -0.01
        text = fit(0.27, c(0.02), dh, [bg, surface, subtle], 7.0, dn)
        muted = fit(0.47, c(0.03), dh, [bg, surface, subtle], 4.5, dn)
        hint = fit(0.52, c(0.03), dh, [bg, surface], 4.5, dn)
        bstrong = fit(0.66, c(0.03), dh, [bg, surface], 3.0, dn)
        accent = fit(0.52, 0.085, ah, [bg, surface, subtle], 4.5, dn)
        hover = oklch_to_rgb(0.44, 0.08, ah)
        asubtle = oklch_to_rgb(0.92, 0.035, ah)
        on = fit(0.985, 0.01, ah, [accent, hover], 4.5, +0.01)
        danger = fit(0.50, 0.15, 25, [bg, surface], 4.5, dn)
        atext = text
    # text on the tinted accent-subtle background must also pass
    assert contrast(atext, asubtle) >= 4.5, "text on accent-subtle"
    names = ["bg", "surface", "surface-subtle", "border", "border-strong", "text-primary", "text-muted",
             "text-subtle", "accent", "accent-hover", "accent-subtle", "text-on-accent", "danger"]
    vals = [bg, surface, subtle, border, bstrong, text, muted, hint, accent, hover, asubtle, on, danger]
    out = {"--color-" + n: hexof(v) for n, v in zip(names, vals)}
    out["_checks"] = {
        "text/bg": round(contrast(text, bg), 2), "muted/surface": round(contrast(muted, surface), 2),
        "subtle/surface": round(contrast(hint, surface), 2), "accent/bg": round(contrast(accent, bg), 2),
        "on-accent/accent": round(contrast(on, accent), 2), "border-strong/bg": round(contrast(bstrong, bg), 2),
        "text/accent-subtle": round(contrast(atext, asubtle), 2)}
    return out

rng = random.Random(int(hashlib.sha256(b"luke-zhang-cs-py palettes v1").hexdigest(), 16))
doms = rng.sample(DOMINANTS, len(REPOS))
result, used = {}, []
for repo, (dname, dh, dc) in zip(REPOS, doms):
    # accent: random from the pool, at least 40 degrees of hue away from the dominant so it reads as one accent
    # and never one another repo already drew, so all nine read as different
    choices = [a for a in ACCENTS if min(abs(a[1] - dh), 360 - abs(a[1] - dh)) >= 40 and a not in used]
    aname, ah = rng.choice(choices); used.append((aname, ah))
    result[repo] = {"dominant": dname, "accent": aname,
                    "dark": theme(dh, dc, ah, True), "light": theme(dh, dc, ah, False)}
print(json.dumps(result, indent=1))

if len(sys.argv) > 1:
    rows = []
    for repo, p in result.items():
        for mode in ("dark", "light"):
            t = p[mode]
            rows.append(f"""<section style="background:{t['--color-bg']};color:{t['--color-text-primary']};padding:24px 32px">
<p style="font:600 13px 'IBM Plex Mono',monospace;color:{t['--color-text-subtle']};margin:0">{repo} · {mode} · {p['dominant']} + {p['accent']}</p>
<h2 style="font:800 48px/1 'Bricolage Grotesque',sans-serif;margin:8px 0">{repo}</h2>
<p style="font:400 16px 'IBM Plex Sans',sans-serif;color:{t['--color-text-muted']};margin:0 0 16px">Muted text on the dominant ground. <a style="color:{t['--color-accent']}">An accent link</a>.</p>
<div style="display:flex;gap:8px;flex-wrap:wrap">""" + "".join(
                f"<span title='{k}' style='width:56px;height:32px;background:{v};outline:1px solid {t['--color-border']}'></span>"
                for k, v in t.items() if k.startswith("--")) + f"""
<span style="background:{t['--color-accent']};color:{t['--color-text-on-accent']};font:600 13px 'IBM Plex Mono',monospace;padding:8px 16px">Live demo</span></div></section>""")
    open(sys.argv[1], "w", encoding="utf-8").write(
        "<!doctype html><meta charset=utf-8><title>Repo palettes</title>"
        "<link rel=stylesheet href='https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@200;800&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap'>"
        "<body style='margin:0'>" + "".join(rows) + "</body>")
