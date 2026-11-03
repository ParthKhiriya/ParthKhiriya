import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape

USERNAME = "ParthKhiriya"
TOKEN = os.environ["GITHUB_TOKEN"]

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar { totalContributions }
    }
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""
payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
)
with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read())

if "errors" in result or not result.get("data", {}).get("user"):
    raise RuntimeError(f"GitHub GraphQL request failed: {result.get('errors', result)}")

user = result["data"]["user"]
contrib = user["contributionsCollection"]
repos = user["repositories"]["nodes"]
stats = [
    ("CONTRIBUTIONS", contrib["contributionCalendar"]["totalContributions"]),
    ("COMMITS", contrib["totalCommitContributions"]),
    ("PULL REQUESTS", contrib["totalPullRequestContributions"]),
    ("ISSUES", contrib["totalIssueContributions"]),
    ("PUBLIC REPOSITORIES", user["repositories"]["totalCount"]),
    ("STARS EARNED", sum(repo["stargazerCount"] for repo in repos)),
]

cards = []
for index, (label, value) in enumerate(stats):
    x = 24 + (index % 3) * 252
    y = 24 + (index // 3) * 112
    cards.append(f"""
      <rect x="{x}" y="{y}" width="232" height="88" rx="12" fill="#161b22" stroke="#30363d"/>
      <text x="{x+18}" y="{y+32}" fill="#8b949e" font-size="11" font-weight="600" letter-spacing="1">{escape(label)}</text>
      <text x="{x+18}" y="{y+66}" fill="#58a6ff" font-size="27" font-weight="700">{int(value):,}</text>
    """)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="248" viewBox="0 0 780 248">
  <rect width="780" height="248" rx="16" fill="#0d1117"/>
  <text x="24" y="16" fill="#c9d1d9" font-size="1"> </text>
  {''.join(cards)}
  <text x="756" y="238" text-anchor="end" fill="#6e7681" font-size="9">Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
</svg>
"""
os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
    file.write(svg)
