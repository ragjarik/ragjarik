#!/usr/bin/env python3
"""Render the profile SVGs: header, lifecycle (V-model) and WakaTime flight log.

Standard library only. The flight log reads the *public* WakaTime stats
endpoint, so no API key is needed as long as coding time, languages and
editors stay public on the WakaTime profile.

    python3 scripts/render_cards.py                      # fetch and render
    python3 scripts/render_cards.py --stats stats.json   # render from a saved response
"""

import argparse
import html
import json
import pathlib
import re
import sys
import time
import urllib.request

WAKATIME_USER = "IaroslavDev"
NAME = "Iaroslav Zaikin"
ROLE = "Senior Embedded Software Engineer"
TAGLINE = "AVIONICS · SAFETY-CRITICAL · BARE-METAL"

STACK = [
    ("LANGUAGES", ["C99 / C11", "C++23"]),
    ("TARGETS", ["Cortex-M · Cortex-A", "Bare-metal", "FreeRTOS"]),
    ("BUSES", ["CAN · Ethernet", "ARINC 429 · 825", "UART · SPI · I²C"]),
    ("TOOLING", ["Python", "GCC · OpenOCD", "JTAG / SWD"]),
    ("PROCESS", ["DO-178C", "MISRA C", "HIL · Traceability"]),
]

# V-model, one row per level: (left arm, right arm). Code sits at the bottom.
LIFECYCLE = [
    (("Requirements", "HLR · system"), ("Qualification", "DO-178C")),
    (("Architecture", "partitioning · interfaces"), ("Integration", "HW/SW · HIL")),
    (("Design", "LLR"), ("Unit tests", "MC/DC coverage")),
]
CODE = ("Code", "C · C++23 · MISRA C")

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets"
W, PAD = 840, 36

# Glass-cockpit palette: a dark display in both GitHub themes, colours used
# the way avionics displays use them (cyan = selected, green = active,
# magenta = managed, amber = own aircraft).
C = {
    "panel": "#0b1117",
    "edge": "#1e2a36",
    "fg": "#e6edf3",
    "muted": "#8a97a6",
    "cyan": "#22d3ee",
    "green": "#4ade80",
    "magenta": "#e879f9",
    "amber": "#fbbf24",
    "sky": "#1f5fa8",
    "ground": "#6b4423",
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# WakaTime entries that aren't really languages / editors.
NOT_CODE = {
    "Markdown", "Text", "Other", "JSON", "JSONC", "YAML", "TOML", "INI", "XML", "CSV",
    "Log", "textmate", "Git Config", "Git", "Diff", "Properties", "reStructuredText",
    "Image (svg)", "Image (png)", "Unknown",
}
NOT_EDITOR = {"Unknown Editor", "Other"}
TOP = 4


# -------------------------------------------------------------------- helpers

def text(x, y, s, size, fill, cls="sans", anchor="start", weight=400, spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x:g}" y="{y:g}" class="{cls}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{ls}>{html.escape(str(s))}</text>'
    )


def rule(y):
    return f'<rect x="{PAD}" y="{y}" width="{W - 2 * PAD}" height="1" fill="{C["edge"]}" />'


def eyebrow(left, right=None, y=42, color=None):
    out = [text(PAD, y, left, 12, color or C["muted"], "mono", spacing=1.8)]
    if right:
        out.append(text(W - PAD, y, right, 12, C["muted"], "mono", anchor="end"))
    return out


def panel(height, title, body, css="", gap=16):
    """Dark display panel; `gap` is transparent space below it so panels stack evenly."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height + gap}" '
        f'viewBox="0 0 {W} {height + gap}" role="img" aria-labelledby="title">\n'
        f'<title id="title">{html.escape(title)}</title>\n'
        f"<style>.sans{{font-family:{SANS}}}.mono{{font-family:{MONO}}}{css}</style>\n"
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="12" '
        f'fill="{C["panel"]}" stroke="{C["edge"]}" />\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )


# --------------------------------------------------------------------- header

def attitude_indicator(cx, cy, r):
    """Flat attitude indicator; the horizon group banks gently via CSS."""
    px = 2.4  # pixels per degree of pitch
    ladder = []
    for deg in (-20, -15, -10, -5, 5, 10, 15, 20):
        y = cy - deg * px
        half = 26 if deg % 10 == 0 else 12
        ladder.append(
            f'<line x1="{cx - half}" y1="{y:g}" x2="{cx + half}" y2="{y:g}" '
            f'stroke="{C["fg"]}" stroke-width="1.5" />'
        )
        if deg % 10 == 0:
            for side in (-1, 1):
                ladder.append(text(cx + side * (half + 12), y + 3.5, abs(deg), 10, C["fg"], "mono", "middle"))

    ticks = []
    for a in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
        major = a % 30 == 0
        ticks.append(
            f'<line x1="{cx}" y1="{cy - r - 4}" x2="{cx}" y2="{cy - r - (13 if major else 9)}" '
            f'stroke="{C["muted"]}" stroke-width="1.5" transform="rotate({a} {cx} {cy})" />'
        )

    wing = f"M{cx - 54} {cy} H{cx - 20} V{cy + 9} M{cx + 54} {cy} H{cx + 20} V{cy + 9}"
    return [
        f'<defs><clipPath id="adi"><circle cx="{cx}" cy="{cy}" r="{r}" /></clipPath></defs>',
        f'<g clip-path="url(#adi)"><g class="att">',
        f'<rect x="{cx - 2 * r}" y="{cy - 2 * r}" width="{4 * r}" height="{2 * r}" fill="{C["sky"]}" />',
        f'<rect x="{cx - 2 * r}" y="{cy}" width="{4 * r}" height="{2 * r}" fill="{C["ground"]}" />',
        f'<line x1="{cx - 2 * r}" y1="{cy}" x2="{cx + 2 * r}" y2="{cy}" stroke="{C["fg"]}" stroke-width="1.5" />',
        *ladder,
        f'<path d="M{cx} {cy - r + 3} l-6 10 h12 Z" fill="{C["fg"]}" />',
        "</g></g>",
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C["edge"]}" stroke-width="2" />',
        *ticks,
        f'<path d="M{cx} {cy - r - 15} l-6 -9 h12 Z" fill="{C["amber"]}" />',
        f'<path d="{wing}" fill="none" stroke="{C["panel"]}" stroke-width="8" />',
        f'<path d="{wing}" fill="none" stroke="{C["amber"]}" stroke-width="4" />',
        f'<rect x="{cx - 4}" y="{cy - 4}" width="8" height="8" fill="{C["amber"]}" '
        f'stroke="{C["panel"]}" stroke-width="2" />',
    ]


def header():
    cx, cy = 704, 116
    body = [
        *eyebrow(TAGLINE, color=C["cyan"], y=52),
        text(PAD, 108, NAME, 44, C["fg"], weight=600, spacing=-0.5),
        text(PAD, 142, ROLE, 18, C["muted"]),
        *attitude_indicator(cx, cy, 68),
        rule(212),
    ]
    col = (W - 2 * PAD) / len(STACK)
    for i, (label, items) in enumerate(STACK):
        x = PAD + i * col
        body.append(text(x, 244, label, 11, C["muted"], "mono", spacing=1.6))
        body += [text(x, 270 + j * 21, item, 14, C["fg"]) for j, item in enumerate(items)]

    css = (
        f".att{{transform-box:view-box;transform-origin:{cx}px {cy}px;"
        "animation:bank 11s ease-in-out infinite}"
        "@keyframes bank{0%,100%{transform:rotate(-7deg) translateY(5px)}"
        "50%{transform:rotate(9deg) translateY(-6px)}}"
        "@media (prefers-reduced-motion:reduce){.att{animation:none;transform:rotate(-5deg)}}"
    )
    return panel(336, f"{NAME} - {ROLE}. Avionics, safety-critical, bare-metal.", body, css)


# ------------------------------------------------------------------ lifecycle

def lifecycle():
    levels = [104, 154, 204]
    bottom, xc, dx = 254, W // 2, 84
    left = [xc - dx * (3 - i) for i in range(3)]
    right = [xc + dx * (3 - i) for i in range(3)]

    def node(x, y, color):
        return f'<circle cx="{x}" cy="{y}" r="6" fill="{C["panel"]}" stroke="{color}" stroke-width="2" />'

    def label(x, y, title, detail, anchor):
        # Sits just below the node: the arm leaves each node upwards, so this side is clear.
        return [text(x, y + 5, title, 14, C["fg"], anchor=anchor),
                text(x, y + 21, detail, 11, C["muted"], "mono", anchor=anchor)]

    route = f"M{left[0]} {levels[0]} L{xc} {bottom} L{right[0]} {levels[0]}"
    body = [
        *eyebrow("LIFECYCLE", "from requirements to certification"),
        rule(58),
        f'<path d="M{left[0]} {levels[0]} L{xc} {bottom}" stroke="{C["cyan"]}" stroke-width="2" fill="none" />',
        f'<path d="M{xc} {bottom} L{right[0]} {levels[0]}" stroke="{C["green"]}" stroke-width="2" fill="none" />',
    ]
    for i, ((lt, ld), (rt, rd)) in enumerate(LIFECYCLE):
        y = levels[i]
        body.append(
            f'<line x1="{left[i] + 12}" y1="{y}" x2="{right[i] - 12}" y2="{y}" stroke="{C["magenta"]}" '
            f'stroke-width="1.5" stroke-dasharray="2 6" stroke-linecap="round" />'
        )
        body += [node(left[i], y, C["cyan"]), node(right[i], y, C["green"])]
        body += label(left[i] - 18, y, lt, ld, "end") + label(right[i] + 18, y, rt, rd, "start")

    body.append(f'<circle cx="{xc}" cy="{bottom}" r="7" fill="{C["fg"]}" stroke="{C["panel"]}" stroke-width="2" />')
    body.append(text(xc, bottom + 30, CODE[0], 14, C["fg"], anchor="middle"))
    body.append(text(xc, bottom + 47, CODE[1], 11, C["muted"], "mono", anchor="middle"))

    # A work item travelling down the V and back up.
    body.append(
        f'<circle r="4.5" fill="{C["amber"]}" stroke="{C["panel"]}" stroke-width="2">'
        f'<animateMotion dur="7s" repeatCount="indefinite" path="{route}" />'
        '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.94;1" '
        'dur="7s" repeatCount="indefinite" /></circle>'
    )

    legend_y, x = 346, PAD
    for name, color, dash in (("development", C["cyan"], ""), ("verification", C["green"], ""),
                              ("traceability", C["magenta"], ' stroke-dasharray="2 5" stroke-linecap="round"')):
        body.append(f'<line x1="{x}" y1="{legend_y - 4}" x2="{x + 20}" y2="{legend_y - 4}" '
                    f'stroke="{color}" stroke-width="2"{dash} />')
        body.append(text(x + 28, legend_y, name, 11, C["muted"], "mono"))
        x += 150
    return panel(372, "Development lifecycle (V-model): requirements, architecture and design down to code, "
                      "then unit tests, integration and DO-178C qualification, traced level to level.", body)


# ----------------------------------------------------------------- flight log

def fetch_stats(user, attempts=3):
    url = f"https://wakatime.com/api/v1/users/{user}/stats"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-cards"})
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # network hiccup, rate limit, etc.
            if i == attempts - 1:
                raise
            print(f"fetch failed ({e}), retrying", file=sys.stderr)
            time.sleep(10 * (i + 1))


def since_label(stats):
    raw = stats.get("human_readable_range") or ""
    m = re.search(r"([A-Z][a-z]{2})\w*\s+\d{1,2},?\s+(\d{4})", raw)
    return f"since {m.group(1)} {m.group(2)}" if m else raw.lower()


def bar(x, y, w, h, fill):
    """Bar square at the baseline, rounded at the data end."""
    r = h / 2
    if w <= r:
        return f'<rect x="{x:g}" y="{y:g}" width="{max(w, 1):.1f}" height="{h}" fill="{fill}" />'
    return (f'<path d="M{x:g} {y:g} H{x + w - r:.1f} A{r:g} {r:g} 0 0 1 {x + w - r:.1f} {y + h:g} '
            f'H{x:g} Z" fill="{fill}" />')


def bar_list(x0, width, heading, rows, color):
    label_w, value_w, top, pitch = 108, 54, 218, 30
    track = width - label_w - value_w
    peak = max((r["percent"] for r in rows), default=1)
    out = [text(x0, 186, heading, 11, C["muted"], "mono", spacing=1.6)]
    for i, row in enumerate(rows):
        cy = top + i * pitch
        w = track * row["percent"] / peak
        out.append(text(x0, cy + 5, row["name"][:15], 14, C["fg"]))
        out.append(bar(x0 + label_w, cy - 4, w, 8, color))
        out.append(text(x0 + label_w + w + 8, cy + 4.5, f"{row['percent']:.1f}%", 12, C["muted"], "mono"))
    return out


def flight_log(stats):
    langs = [l for l in stats["languages"] if l["name"] not in NOT_CODE and l["percent"] > 0][:TOP]
    editors = [e for e in stats["editors"] if e["name"] not in NOT_EDITOR and e["percent"] > 0][:TOP]
    hours = round(stats["total_seconds"] / 3600)
    days = stats["days_minus_holidays"]
    since = since_label(stats)

    body = [*eyebrow("FLIGHT LOG", f"WakaTime · {since}"), rule(58)]
    c_share = sum(l["percent"] for l in stats["languages"] if l["name"] in ("C", "C++"))
    tiles = (("Hours logged", f"{hours:,} h"), ("Days active", f"{days:,}"), ("C / C++ share", f"{c_share:.1f}%"))
    for x, (label, value) in zip((PAD, PAD + 240, PAD + 480), tiles):
        body.append(text(x, 92, label, 13, C["muted"]))
        body.append(text(x, 132, value, 36, C["fg"], weight=600))

    col = (W - 2 * PAD - 32) / 2
    body += bar_list(PAD, col, "LANGUAGES", langs, C["green"])
    body += bar_list(PAD + col + 32, col, "EDITORS", editors, C["cyan"])

    height = 218 + 30 * (TOP - 1) + 34
    title = (f"WakaTime flight log: {hours:,} hours over {days:,} days {since}. Languages: "
             + ", ".join(f"{l['name']} {l['percent']:.1f}%" for l in langs)
             + ". Editors: " + ", ".join(f"{e['name']} {e['percent']:.1f}%" for e in editors) + ".")
    return panel(height, title, body)


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stats", type=pathlib.Path, help="render from a saved stats JSON instead of fetching")
    ap.add_argument("--user", default=WAKATIME_USER)
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    (OUT / "header.svg").write_text(header(), encoding="utf-8")
    (OUT / "lifecycle.svg").write_text(lifecycle(), encoding="utf-8")

    payload = json.loads(args.stats.read_text("utf-8")) if args.stats else fetch_stats(args.user)
    stats = payload.get("data") or {}
    if stats.get("status") != "ok" or stats.get("percent_calculated", 0) < 100 or not stats.get("languages"):
        # WakaTime is still crunching numbers: keep the previous card instead of a partial one.
        print("WakaTime stats not ready; keeping the existing flight log", file=sys.stderr)
        return
    (OUT / "flight-log.svg").write_text(flight_log(stats), encoding="utf-8")
    print(f"rendered cards into {OUT}")


if __name__ == "__main__":
    main()
