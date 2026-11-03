import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape

USERNAME = "ParthKhiriya"
TOKEN = os.environ["GITHUB_TOKEN"]

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

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""
user = graphql(query, {"login": USERNAME})["user"]
collection = user["contributionsCollection"]
calendar = collection["contributionCalendar"]

days = [
    (date.fromisoformat(day["date"]), day["contributionCount"])
    for week in calendar["weeks"]
    for day in week["contributionDays"]
]
active_dates = {day for day, count in days if count > 0}

# GitHub's calendar is UTC-based. Treat yesterday as the latest possible
# streak endpoint when today's contributions have not yet appeared.
today = datetime.now(timezone.utc).date()
streak_end = today if today in active_dates else today - timedelta(days=1)
current_streak = 0
cursor = streak_end
while cursor in active_dates:
    current_streak += 1
    cursor -= timedelta(days=1)

longest_streak = 0
running_streak = 0
previous_day = None
for day, count in days:
    if count > 0:
        if previous_day is not None and day == previous_day + timedelta(days=1):
            running_streak += 1
        else:
            running_streak = 1
        longest_streak = max(longest_streak, running_streak)
        previous_day = day
    else:
        running_streak = 0
        previous_day = None

stats = [
    ("CONTRIBUTIONS · LAST YEAR", calendar["totalContributions"]),
    ("CURRENT STREAK · DAYS", current_streak),
    ("LONGEST STREAK · DAYS", longest_streak),
    ("COMMITS · THIS YEAR", collection["totalCommitContributions"]),
    ("PULL REQUESTS · THIS YEAR", collection["totalPullRequestContributions"]),
    ("ISSUES · THIS YEAR", collection["totalIssueContributions"]),
]

cards = []
for index, (label, value) in enumerate(stats):
    x = 24 + (index % 3) * 252
    y = 24 + (index // 3) * 112
    cards.append(f"""
      <rect x="{x}" y="{y}" width="232" height="88" rx="12" fill="#161b22" stroke="#30363d"/>
      <text x="{x+16}" y="{y+31}" fill="#8b949e" font-family="Arial,sans-serif" font-size="10" font-weight="600" letter-spacing=".5">{escape(label)}</text>
      <text x="{x+16}" y="{y+66}" fill="#58a6ff" font-family="Arial,sans-serif" font-size="27" font-weight="700">{int(value):,}</text>
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
