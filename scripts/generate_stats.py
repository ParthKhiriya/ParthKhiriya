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

def graphql(query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator"
        }
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read())
    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")
    return result["data"]

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

stats_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="248" viewBox="0 0 780 248">
  <rect width="780" height="248" rx="16" fill="#0d1117"/>
  {''.join(cards)}
  <text x="756" y="238" text-anchor="end" fill="#6e7681" font-family="Arial,sans-serif" font-size="9">Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
</svg>
"""

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""
data = graphql(query, {"login": USERNAME})
calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
palette = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353",
}
cell = 10
gap = 3
left = 48
top = 48
heatmap = []
month_labels = []
last_month = None

for week_index, week in enumerate(weeks):
    for day in week["contributionDays"]:
        date = datetime.strptime(day["date"], "%Y-%m-%d")
        x = left + week_index * (cell + gap)
        y = top + date.weekday() * (cell + gap)
        level = day["contributionLevel"]
        count = day["contributionCount"]
        heatmap.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{palette.get(level, palette["NONE"])}">'
            f'<title>{escape(day["date"])}: {count} contributions</title></rect>'
        )
        if date.month != last_month and date.weekday() < 7:
            month_labels.append(
                f'<text x="{x}" y="34" fill="#8b949e" font-size="10" '
                f'font-family="Arial,sans-serif">{date.strftime("%b")}</text>'
            )
            last_month = date.month

width = max(780, left + len(weeks) * (cell + gap) + 20)
total = calendar["totalContributions"]
activity_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="178" viewBox="0 0 {width} 178">
  <rect width="100%" height="178" rx="12" fill="#0d1117"/>
  <text x="24" y="22" fill="#c9d1d9" font-size="13" font-weight="600" font-family="Arial,sans-serif">{total:,} contributions in the last year</text>
  {''.join(month_labels)}
  {''.join(heatmap)}
  <g font-family="Arial,sans-serif" font-size="9" fill="#8b949e">
    <text x="24" y="160">Less</text>
    <rect x="54" y="150" width="10" height="10" rx="2" fill="#161b22"/>
    <rect x="68" y="150" width="10" height="10" rx="2" fill="#0e4429"/>
    <rect x="82" y="150" width="10" height="10" rx="2" fill="#006d32"/>
    <rect x="96" y="150" width="10" height="10" rx="2" fill="#26a641"/>
    <rect x="110" y="150" width="10" height="10" rx="2" fill="#39d353"/>
    <text x="128" y="160">More</text>
    <text x="{width-16}" y="172" text-anchor="end">Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d')}</text>
  </g>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
    file.write(stats_svg)
with open("assets/contribution-activity.svg", "w", encoding="utf-8") as file:
    file.write(activity_svg)
