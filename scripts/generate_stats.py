import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape

USERNAME = "ParthKhiriya"
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com"

def github_get(path):
    request = urllib.request.Request(
        API + path,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-stats-generator"
        }
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())

profile = github_get(f"/users/{USERNAME}")
repositories = github_get(f"/users/{USERNAME}/repos?type=owner&per_page=100&sort=updated")
if not isinstance(repositories, list):
    raise RuntimeError("GitHub returned an unexpected repository response")

stats = [
    ("FOLLOWERS", profile.get("followers", 0)),
    ("PUBLIC REPOSITORIES", profile.get("public_repos", 0)),
    ("STARS EARNED", sum(repo.get("stargazers_count", 0) for repo in repositories)),
    ("FORKS EARNED", sum(repo.get("forks_count", 0) for repo in repositories)),
    ("FOLLOWING", profile.get("following", 0)),
    ("PUBLIC GISTS", profile.get("public_gists", 0)),
]

cards = []
for index, (label, value) in enumerate(stats):
    x = 24 + (index % 3) * 252
    y = 24 + (index // 3) * 112
    cards.append(f"""
      <rect x="{x}" y="{y}" width="232" height="88" rx="12" fill="#161b22" stroke="#30363d"/>
      <text x="{x+18}" y="{y+32}" fill="#8b949e" font-family="Arial,sans-serif" font-size="11" font-weight="600" letter-spacing="1">{escape(label)}</text>
      <text x="{x+18}" y="{y+66}" fill="#58a6ff" font-family="Arial,sans-serif" font-size="27" font-weight="700">{int(value):,}</text>
    """)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="248" viewBox="0 0 780 248">
  <rect width="780" height="248" rx="16" fill="#0d1117"/>
  {''.join(cards)}
  <text x="756" y="238" text-anchor="end" fill="#6e7681" font-family="Arial,sans-serif" font-size="9">Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
</svg>
"""
os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
    file.write(svg)
