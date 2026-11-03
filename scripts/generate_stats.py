import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape

USERNAME = "ParthKhiriya"
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com"

def request_json(url, payload=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-stats-generator",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())

def graphql(query, variables):
    result = request_json("https://api.github.com/graphql", {
        "query": query,
        "variables": variables,
    })
    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")
    return result["data"]

# Public profile metrics.
profile = request_json(f"{API}/users/{USERNAME}")
repositories = []
page = 1
while True:
    batch = request_json(
        f"{API}/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
    )
    if not batch:
        break
    repositories.extend(batch)
    if len(batch) < 100:
        break
    page += 1

public_repo_count = profile.get("public_repos", 0)
followers = profile.get("followers", 0)
forks_earned = sum(repo.get("forks_count", 0) for repo in repositories)

# Fetch contribution calendars year-by-year from account creation to today.
query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
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
created = date.fromisoformat(profile["created_at"][:10])
today = datetime.now(timezone.utc).date()
all_days = {}
total_contributions = 0
year_start = created

while year_start <= today:
    year_end = min(date(year_start.year, 12, 31), today)
    data = graphql(query, {
        "login": USERNAME,
        "from": datetime.combine(year_start, datetime.min.time(), timezone.utc).isoformat(),
        "to": datetime.combine(year_end, datetime.max.time(), timezone.utc).isoformat(),
    })
    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    total_contributions += calendar["totalContributions"]
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            all_days[date.fromisoformat(day["date"])] = day["contributionCount"]
    year_start = year_end + timedelta(days=1)

active_dates = {day for day, count in all_days.items() if count > 0}

# Current streak: today if active, otherwise yesterday if active.
streak_end = today if today in active_dates else today - timedelta(days=1)
current_streak = 0
cursor = streak_end
while cursor in active_dates:
    current_streak += 1
    cursor -= timedelta(days=1)

# Longest consecutive run across the complete account history.
longest_streak = 0
running_streak = 0
previous_day = None
for day in sorted(all_days):
    if all_days[day] > 0:
        running_streak = running_streak + 1 if previous_day == day - timedelta(days=1) else 1
        longest_streak = max(longest_streak, running_streak)
        previous_day = day
    else:
        running_streak = 0
        previous_day = None

groups = [
    ("PROFILE STATS", [
        ("PUBLIC REPOSITORIES", public_repo_count),
        ("FORKS EARNED", forks_earned),
        ("FOLLOWERS", followers),
    ]),
    ("CONTRIBUTION STATS", [
        ("TOTAL CONTRIBUTIONS · ALL TIME", total_contributions),
        ("CURRENT STREAK · DAYS", current_streak),
        ("LONGEST STREAK · ALL TIME · DAYS", longest_streak),
    ]),
]

def render_group(title, items, y):
    cards = []
    for index, (label, value) in enumerate(items):
        x = 24 + index * 252
        cards.append(f"""
          <rect x="{x}" y="{y}" width="232" height="88" rx="12" fill="#161b22" stroke="#30363d"/>
          <text x="{x+15}" y="{y+31}" fill="#8b949e" font-family="Arial,sans-serif" font-size="9.5" font-weight="600" letter-spacing=".35">{escape(label)}</text>
          <text x="{x+15}" y="{y+66}" fill="#58a6ff" font-family="Arial,sans-serif" font-size="27" font-weight="700">{int(value):,}</text>
        """)
    return f'<text x="24" y="{y-12}" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="12" font-weight="700">{escape(title)}</text>' + "".join(cards)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="290" viewBox="0 0 780 290">
  <rect width="780" height="290" rx="16" fill="#0d1117"/>
  {render_group(groups[0][0], groups[0][1], 40)}
  {render_group(groups[1][0], groups[1][1], 174)}
  <text x="756" y="278" text-anchor="end" fill="#6e7681" font-family="Arial,sans-serif" font-size="9">Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
</svg>
"""
os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
    file.write(svg)
