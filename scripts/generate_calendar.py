#!/usr/bin/env python3
"""Generate a native-style GitHub contribution calendar SVG in electric blue.

Replicates GitHub's own contribution calendar (dark theme) 1:1 — header,
month labels, Mon/Wed/Fri day labels, Less→More legend — with the only
difference being the blue intensity ramp instead of GitHub's green.

Data source: https://github-contributions-api.jogruber.de/v4/<user>?y=last
(tokenless, read-only; mirrors GitHub's native per-day counts and 0-4 levels).

Usage: python3 generate_calendar.py [--user siva169] [--out metrics/contributions-calendar.svg]
"""

import argparse
import datetime as dt
import json
import sys
import urllib.request

API = "https://github-contributions-api.jogruber.de/v4/{user}?y=last"

# Electric-blue ramp (level 0 = empty cell), matching the profile's
# typing-SVG header color family (#58A6FF). 0 -> 4 = fewer -> more.
COLORS = ["#161b22", "#0c3a6b", "#1158c7", "#1f6feb", "#58a6ff"]
BG = "#0d1117"
FG_MUTED = "#656d76"
FG_SUBTLE = "#7d8590"
BORDER = "#30363d"

# Native calendar geometry (px, matches GitHub dark theme)
CELL = 11
GAP = 3
STEP = CELL + GAP
ROW_LABEL_W = 26
LEFT_PAD = 10
TOP_PAD = 30
CELL_TOP_PAD = 2
LEGEND_H = 20
BOTTOM_PAD = 12

WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch(user: str) -> dict:
    url = API.format(user=user)
    req = urllib.request.Request(url, headers={"User-Agent": "calendar-svg/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(days: list[dict]) -> str:
    days = sorted(days, key=lambda d: d["date"])
    first_day = dt.date.fromisoformat(days[0]["date"])
    total = sum(d["count"] for d in days)

    # Column = week, row = weekday (Sun=0 top ... Sat=6 bottom, like GitHub)
    weeks: dict[dt.date, list[dict | None]] = {}
    for d in days:
        day = dt.date.fromisoformat(d["date"])
        week_start = day - dt.timedelta(days=(day.weekday() + 1) % 7)
        weeks.setdefault(week_start, [None] * 7)[(day.weekday() + 1) % 7] = d

    starts = sorted(weeks)
    grid_w = len(starts) * STEP - GAP
    grid_h = 7 * STEP - GAP
    width = LEFT_PAD + ROW_LABEL_W + grid_w + LEFT_PAD
    height = TOP_PAD + CELL_TOP_PAD + grid_h + LEGEND_H + BOTTOM_PAD

    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
             f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{total} contributions in the last year">')
    s.append(f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
             f'fill="{BG}" stroke="{BORDER}" rx="6" ry="6"/>')

    # Header — native wording
    s.append(f'<text x="{LEFT_PAD}" y="20" fill="#e6edf3" '
             f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans,Helvetica,Arial,sans-serif" '
             f'font-size="16" font-weight="600">{total} contributions in the last year</text>')

    gx = LEFT_PAD + ROW_LABEL_W
    gy = TOP_PAD + CELL_TOP_PAD

    # Month labels above the grid: label the column where a month's 1st
    # falls (like GitHub), plus the leading partial month of the window.
    labeled = set()
    for i, ws in enumerate(starts):
        x = gx + i * STEP
        for offset in range(7):
            day = ws + dt.timedelta(days=offset)
            if day.day == 1:
                labeled.add((i, day.month))
                break
    first_month = first_day.month
    if not any(i == 0 and m == first_month for i, m in labeled):
        labeled.add((0, first_month))
    for i, month in sorted(labeled):
        x = gx + i * STEP
        s.append(f'<text x="{x}" y="{gy - 8}" fill="{FG_SUBTLE}" '
                 f'font-family="ui-monospace,SFMono-Regular,Helvetica,Arial,sans-serif" '
                 f'font-size="10">{esc(MONTH_NAMES[month - 1])}</text>')

    # Weekday labels on the left
    for row, label in WEEKDAY_LABELS.items():
        y = gy + row * STEP + CELL - 2
        s.append(f'<text x="{LEFT_PAD}" y="{y}" fill="{FG_SUBTLE}" '
                 f'font-family="ui-monospace,SFMono-Regular,Helvetica,Arial,sans-serif" '
                 f'font-size="10" text-anchor="end">{label}</text>')

    # Cells — future days in the current week render as empty boxes (native)
    for i, ws in enumerate(starts):
        for row, day_data in enumerate(weeks[ws]):
            x = gx + i * STEP
            y = gy + row * STEP
            if day_data is None:
                s.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'fill="{COLORS[0]}" rx="2" ry="2"/>')
                continue
            level = day_data["level"]
            count = day_data["count"]
            date = day_data["date"]
            fill = COLORS[min(level, 4)]
            s.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'fill="{fill}" rx="2" ry="2" data-date="{date}" '
                f'data-count="{count}">'
                f'<title>{count} contribution{"s" if count != 1 else ""} '
                f'on {date}</title>'
                f'</rect>')

    # Legend (Less → More), right-aligned — 5 squares like native
    legend_w = 5 * CELL + 4 * GAP
    lx = width - LEFT_PAD - legend_w - 34
    ly = gy + grid_h + 14
    s.append(f'<text x="{lx - 6}" y="{ly + CELL - 2}" fill="{FG_SUBTLE}" '
             f'font-family="ui-monospace,SFMono-Regular,Helvetica,Arial,sans-serif" '
             f'font-size="10" text-anchor="end">Less</text>')
    for i, c in enumerate(COLORS):
        s.append(f'<rect x="{lx + i * STEP}" y="{ly}" width="{CELL}" '
                 f'height="{CELL}" fill="{c}" rx="2" ry="2"/>')
    s.append(f'<text x="{lx + legend_w + 6}" y="{ly + CELL - 2}" '
             f'fill="{FG_SUBTLE}" '
             f'font-family="ui-monospace,SFMono-Regular,Helvetica,Arial,sans-serif" '
             f'font-size="10">More</text>')

    s.append('</svg>')
    return "\n".join(s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="siva169")
    ap.add_argument("--out", default="metrics/contributions-calendar.svg")
    args = ap.parse_args()

    data = fetch(args.user)
    days = data.get("contributions", [])
    if not days:
        print("No contribution data returned", file=sys.stderr)
        return 1

    svg = build_svg(days)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    total = sum(d["count"] for d in days)
    print(f"Wrote {args.out} ({total} contributions, {len(days)} days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
