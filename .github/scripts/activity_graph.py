"""Draw the last 31 days of contributions as an SVG line chart.

Usage: GITHUB_TOKEN=... python activity_graph.py <username> <output.svg>

Standard library only, so the workflow needs no install step. Colors match
the github_dark_dimmed stats cards and the #00AEFF accent of the README.
"""

import json
import sys
import urllib.request
from datetime import date
from os import environ

DAYS = 31
W, H = 1000, 320
LEFT, RIGHT, TOP, BOTTOM = 60, 30, 60, 50

BG = "#22272e"
BORDER = "#444c56"
TEXT = "#adbac7"
GRID = "#373e47"
ACCENT = "#00AEFF"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    return [(date.fromisoformat(d["date"]), d["contributionCount"]) for d in days[-DAYS:]]


def nice_max(value):
    # Round the top of the y axis up to 1, 2 or 5 times a power of ten.
    if value <= 4:
        return 4
    step = 1
    while True:
        for m in (1, 2, 5):
            if step * m * 4 >= value:
                return step * m * 4
        step *= 10


def render(login, days):
    top = nice_max(max(c for _, c in days))
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM

    def x(i):
        return LEFT + plot_w * i / (len(days) - 1)

    def y(c):
        return TOP + plot_h * (1 - c / top)

    points = [(x(i), y(c)) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    area = f"{LEFT},{TOP + plot_h} {line} {LEFT + plot_w},{TOP + plot_h}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">',
        "<defs><linearGradient id=\"fill\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\">"
        f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0.35"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>'
        "</linearGradient></defs>",
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="4.5" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="{W / 2}" y="36" text-anchor="middle" font-size="18" font-weight="600" '
        f'fill="{ACCENT}">{login}\'s contributions, last {DAYS} days</text>',
    ]

    for k in range(5):
        value = top * k // 4
        gy = y(value)
        parts.append(f'<line x1="{LEFT}" y1="{gy:.1f}" x2="{LEFT + plot_w}" y2="{gy:.1f}" stroke="{GRID}"/>')
        parts.append(
            f'<text x="{LEFT - 10}" y="{gy + 4:.1f}" text-anchor="end" font-size="12" fill="{TEXT}">{value}</text>'
        )

    for i, (d, _) in enumerate(days):
        parts.append(
            f'<text x="{x(i):.1f}" y="{TOP + plot_h + 22}" text-anchor="middle" font-size="12" fill="{TEXT}">{d.day}</text>'
        )

    parts.append(f'<polygon points="{area}" fill="url(#fill)"/>')
    parts.append(f'<polyline points="{line}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round"/>')
    for (px, py), (d, c) in zip(points, days):
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{BG}" stroke="{ACCENT}" stroke-width="2">'
            f"<title>{d.isoformat()}: {c}</title></circle>"
        )

    parts.append(
        f'<text x="{W / 2}" y="{H - 8}" text-anchor="middle" font-size="12" fill="{TEXT}">'
        f"{days[0][0]:%b %d} to {days[-1][0]:%b %d}</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    login, out = sys.argv[1], sys.argv[2]
    svg = render(login, fetch_days(login, environ["GITHUB_TOKEN"]))
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg + "\n")


if __name__ == "__main__":
    main()
