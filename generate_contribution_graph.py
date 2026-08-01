#!/usr/bin/env python3
"""Render my GitHub contribution calendar as an animated SVG.

Pulls the last year of contribution data from the GraphQL API and draws the
familiar 53x7 grid with a staggered left-to-right reveal. Colors match
GitHub's own light/dark palettes.
"""

import argparse
import json
import os
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionLevel } }
      }
    }
  }
}
"""

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

THEMES = {
    "dark": {
        "cells": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "text": "#7d8590",
        "title": "#e6edf3",
    },
    "light": {
        "cells": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "text": "#57606a",
        "title": "#1f2328",
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CELL = 11
PITCH = 14
LEFT = 34
TOP = 46
STAGGER_MS = 35


def fetch_calendar(user: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render(cal: dict, theme_name: str) -> str:
    theme = THEMES[theme_name]
    weeks = cal["weeks"]
    width = LEFT + len(weeks) * PITCH + 10
    height = TOP + 7 * PITCH + 30

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="-apple-system, \'Segoe UI\', Helvetica, Arial, sans-serif">',
        "<style>"
        ".w{animation:sweep .5s ease-out backwards}"
        "@keyframes sweep{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}"
        "@media (prefers-reduced-motion: reduce){.w{animation:none}}"
        "</style>",
        f'<text x="{LEFT}" y="18" font-size="13" font-weight="600" fill="{theme["title"]}">'
        f'{cal["totalContributions"]:,} contributions in the last year</text>',
    ]

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = TOP + row * PITCH + CELL - 2
        parts.append(f'<text x="{LEFT - 6}" y="{y}" font-size="9" text-anchor="end" fill="{theme["text"]}">{label}</text>')

    label_weeks = []
    prev_month = None
    for i, week in enumerate(weeks):
        month = int(week["contributionDays"][0]["date"][5:7])
        if month != prev_month and i < len(weeks) - 2:
            label_weeks.append((i, month))
        prev_month = month
    if len(label_weeks) >= 2 and label_weeks[1][0] - label_weeks[0][0] < 3:
        label_weeks.pop(0)
    label_map = dict(label_weeks)

    for i, week in enumerate(weeks):
        delay = i * STAGGER_MS
        x = LEFT + i * PITCH
        if i in label_map:
            parts.append(
                f'<text class="w" style="animation-delay:{delay}ms" x="{x}" y="{TOP - 8}" '
                f'font-size="10" fill="{theme["text"]}">{MONTHS[label_map[i] - 1]}</text>'
            )

        cells = []
        for j, day in enumerate(week["contributionDays"]):
            color = theme["cells"][LEVELS.index(day["contributionLevel"])]
            cells.append(
                f'<rect x="{x}" y="{TOP + j * PITCH}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">'
                f'<title>{day["date"]}</title></rect>'
            )
        parts.append(f'<g class="w" style="animation-delay:{delay}ms">{"".join(cells)}</g>')

    legend_x = width - 10 - 5 * PITCH - 100
    legend_y = TOP + 7 * PITCH + 14
    legend_delay = len(weeks) * STAGGER_MS
    legend = [f'<text x="{legend_x}" y="{legend_y + CELL - 2}" font-size="10" fill="{theme["text"]}">Less</text>']
    for k, color in enumerate(theme["cells"]):
        legend.append(f'<rect x="{legend_x + 30 + k * PITCH}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"/>')
    legend.append(
        f'<text x="{legend_x + 30 + 5 * PITCH + 6}" y="{legend_y + CELL - 2}" font-size="10" fill="{theme["text"]}">More</text>'
    )
    parts.append(f'<g class="w" style="animation-delay:{legend_delay}ms">{"".join(legend)}</g>')

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--theme", choices=list(THEMES), required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cal = fetch_calendar(args.user, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(render(cal, args.theme))


if __name__ == "__main__":
    main()
