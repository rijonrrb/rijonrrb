#!/usr/bin/env python3
"""Build self-hosted profile SVG cards from the GitHub public REST API.

Runs in GitHub Actions using its ephemeral GITHUB_TOKEN.
No external image/rendering service or third-party Python libraries required.
"""
import collections
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request
from xml.sax.saxutils import escape

OWNER = "rijonrrb"
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "profile"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
YELLOW = "#F5C518"
ORANGE = "#FF9F1C"
AMBER = "#B87800"
DARK_TEXT = "#303030"
GREY = "#686868"


def api_get(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "rijonrrb-profile-svg-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request(API + path, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def public_repos():
    result = []
    for page in range(1, 11):
        batch = api_get(f"/users/{OWNER}/repos?per_page=100&page={page}&type=owner")
        if not isinstance(batch, list):
            raise RuntimeError("Expected public repositories list")
        result.extend(r for r in batch if not r.get("private"))
        if len(batch) < 100:
            break
    return result


def svg_document(title, content, width, height, updated):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
            f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>'
            f'<rect x="1" y="1" width="{width-2}" height="{height-2}" fill="none" stroke="#E6E6E6"/>'
            f'<rect x="22" y="18" width="54" height="4" fill="{YELLOW}"/>'
            f'<text x="22" y="51" font-size="21" font-family="Arial,sans-serif" '
            f'font-weight="700" fill="{AMBER}">{escape(title)}</text>'
            f'{content}'
            f'<text x="22" y="{height-13}" font-size="10" font-family="Arial,sans-serif" '
            f'fill="#858585">Public GitHub data · Updated {escape(updated)} UTC</text>'
            '</svg>\n')


def metric(x, y, number, title):
    return (f'<rect x="{x}" y="{y}" width="177" height="56" fill="#FFFCF4" stroke="#F1E7CC"/>'
            f'<text x="{x+12}" y="{y+29}" font-size="23" font-family="Arial,sans-serif" '
            f'font-weight="700" fill="{DARK_TEXT}">{number:,}</text>'
            f'<text x="{x+12}" y="{y+45}" font-size="11" font-family="Arial,sans-serif" '
            f'fill="{GREY}">{escape(title)}</text>')


def create_cards():
    repos = public_repos()
    own = [r for r in repos if not r.get("fork") and not r.get("archived")]
    language_bytes = collections.Counter()
    for repo in own:
        # A repository's language byte counts exclude forks and archived projects.
        data = api_get(f"/repos/{OWNER}/{repo['name']}/languages")
        language_bytes.update({name: int(size) for name, size in data.items()})

    languages = [(name, size) for name, size in language_bytes.most_common() if size > 0]
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in own)
    forks = sum(int(repo.get("forks_count", 0)) for repo in own)
    stats = "".join([
        f'<text x="22" y="73" font-size="12" font-family="Arial,sans-serif" fill="{GREY}">@{OWNER} · Original public projects</text>',
        metric(22, 86, len(own), "Repositories"),
        metric(218, 86, stars, "Stars received"),
        metric(22, 149, forks, "Forks received"),
        metric(218, 149, len(languages), "Languages detected"),
    ])
    stats_svg = svg_document("GitHub Stats", stats, 420, 230, today)

    body = (f'<text x="22" y="72" font-size="11" font-family="Arial,sans-serif" '
            f'fill="{GREY}">Source-code proportions in original public repositories</text>')
    total = sum(language_bytes.values())
    colors = [YELLOW, ORANGE, "#DCA548", "#CCB98D", "#B7AF9F", "#E6CE9B"]
    for i, (name, size) in enumerate(languages[:5]):
        y = 99 + i * 35
        portion = size / total if total else 0
        bar_width = max(2, round(207 * portion))
        body += (f'<text x="22" y="{y}" font-size="12" font-family="Arial,sans-serif" fill="{DARK_TEXT}">'
                 f'{escape(name[:18])}</text>'
                 f'<rect x="147" y="{y-11}" width="207" height="11" fill="#F0F0F0"/>'
                 f'<rect x="147" y="{y-11}" width="{bar_width}" height="11" fill="{colors[i]}"/>'
                 f'<text x="365" y="{y}" font-size="12" font-family="Arial,sans-serif" '
                 f'fill="{GREY}">{portion*100:.1f}%</text>')
    if not languages:
        body += (f'<text x="22" y="115" font-size="13" font-family="Arial,sans-serif" '
                 f'fill="{GREY}">No public source-language data available</text>')
    langs_svg = svg_document("Most Used Languages", body, 420, 300, today)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "stats.svg").write_text(stats_svg, encoding="utf-8")
    (DEST / "top-langs.svg").write_text(langs_svg, encoding="utf-8")
    print(f"Rendered {len(own)} original public repos and {len(languages)} languages")


if __name__ == "__main__":
    create_cards()
