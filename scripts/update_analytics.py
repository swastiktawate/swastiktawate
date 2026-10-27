import urllib.request
import json
import re
import os

token = os.environ.get("GITHUB_TOKEN")
username = "swastiktawate"

headers = {
    "User-Agent": "GitHub-Analytics-Updater",
    "Accept": "application/vnd.github.v3+json"
}
if token:
    headers["Authorization"] = f"Bearer {token}"

# 1. Fetch user public repos
user_req = urllib.request.Request(f"https://api.github.com/users/{username}", headers=headers)
with urllib.request.urlopen(user_req) as resp:
    user_data = json.loads(resp.read().decode())
    public_repos = user_data.get("public_repos", 16)

# 2. Fetch total stars across public repos
repos_req = urllib.request.Request(f"https://api.github.com/users/{username}/repos?per_page=100", headers=headers)
with urllib.request.urlopen(repos_req) as resp:
    repos_data = json.loads(resp.read().decode())
    total_stars = sum(r.get("stargazers_count", 0) for r in repos_data)

# 3. Fetch total merged PRs
search_pr_req = urllib.request.Request(
    f"https://api.github.com/search/issues?q=author:{username}+type:pr+is:merged",
    headers=headers
)
with urllib.request.urlopen(search_pr_req) as resp:
    pr_data = json.loads(resp.read().decode())
    merged_prs = pr_data.get("total_count", 8)

# 4. Fetch contributions & streak via GraphQL
graphql_query = """
query {
  user(login: "%s") {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
""" % username

graphql_req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": graphql_query}).encode("utf-8"),
    headers={**headers, "Content-Type": "application/json"}
)

total_contributions = 63
current_streak = 10

try:
    with urllib.request.urlopen(graphql_req) as resp:
        gql_data = json.loads(resp.read().decode())
        calendar = gql_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        total_contributions = calendar.get("totalContributions", 63)
        
        days = []
        for week in calendar.get("weeks", []):
            for day in week.get("contributionDays", []):
                days.append((day["date"], day["contributionCount"]))
        days.sort(key=lambda x: x[0])
        
        streak = 0
        for i, (date, count) in enumerate(reversed(days)):
            if i == 0 and count == 0:
                continue
            if count > 0:
                streak += 1
            else:
                break
        current_streak = streak
except Exception as e:
    print(f"GraphQL error (fallback used): {e}")

print(f"Metrics fetched: Repos={public_repos}, Contributions={total_contributions}, MergedPRs={merged_prs}, Streak={current_streak}d, Stars={total_stars}")

# 5. Update SVG files
def update_svg(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Update Repos
    content = re.sub(
        r'(<!-- CARD 1: REPOSITORIES -->[\s\S]*?<text x="50" y="38"[^>]*>)[^<]*(</text>)',
        rf'\g<1>{public_repos}\g<2>',
        content
    )
    # Update Contributions
    content = re.sub(
        r'(<!-- CARD 2: CONTRIBUTIONS MADE -->[\s\S]*?<text x="50" y="38"[^>]*>)[^<]*(</text>)',
        rf'\g<1>{total_contributions}\g<2>',
        content
    )
    # Update Merged PRs
    content = re.sub(
        r'(<!-- CARD 3: TOTAL MERGED PULL REQUESTS -->[\s\S]*?<text x="50" y="38"[^>]*>)[^<]*(</text>)',
        rf'\g<1>{merged_prs}\g<2>',
        content
    )
    # Update Streak
    content = re.sub(
        r'(<!-- CARD 4: CONTRIBUTION STREAK -->[\s\S]*?<text x="50" y="38"[^>]*>)[^<]*(</text>)',
        rf'\g<1>{current_streak}d\g<2>',
        content
    )
    # Update Stars
    content = re.sub(
        r'(<!-- CARD 5: STARS GOT -->[\s\S]*?<text x="50" y="38"[^>]*>)[^<]*(</text>)',
        rf'\g<1>{total_stars}\g<2>',
        content
    )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {file_path}")

update_svg("swastik-github-analytics.svg")
update_svg("assets/swastik-github-analytics.svg")
