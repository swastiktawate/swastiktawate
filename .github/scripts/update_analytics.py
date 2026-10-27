import os
import re
import json
import urllib.request

USERNAME = "swastiktawate"
TOKEN = os.environ.get("GITHUB_TOKEN")

headers = {
    "User-Agent": "GitHub-Analytics-Updater",
    "Accept": "application/vnd.github.v3+json",
}
if TOKEN:
    headers["Authorization"] = f"token {TOKEN}"

def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def fetch_graphql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        headers=headers,
        data=json.dumps({"query": query}).encode("utf-8"),
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def get_stats():
    # 1. Repos & Stars
    user_data = fetch_json(f"https://api.github.com/users/{USERNAME}")
    repos_count = user_data.get("public_repos", 16)

    repos_data = fetch_json(f"https://api.github.com/users/{USERNAME}/repos?per_page=100")
    stars_count = sum(r.get("stargazers_count", 0) for r in repos_data)

    # 2. Merged PRs
    merged_data = fetch_json(f"https://api.github.com/search/issues?q=author:{USERNAME}+type:pr+is:merged")
    merged_prs = merged_data.get("total_count", 8)

    # 3. Contributions & Streak
    gql_query = f"""
    query {{
      user(login: "{USERNAME}") {{
        contributionsCollection {{
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                contributionCount
                date
              }}
            }}
          }}
        }}
      }}
    }}
    """
    total_contribs = 57
    streak = 10
    try:
        gql_res = fetch_graphql(gql_query)
        cal = gql_res.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {})
        total_contribs = cal.get("totalContributions", 57)
        
        days = []
        for w in cal.get("weeks", []):
            for d in w.get("contributionDays", []):
                days.append(d)
        
        # Calculate current streak
        rev = list(reversed(days))
        cur_streak = 0
        for d in rev:
            if d["contributionCount"] > 0:
                cur_streak += 1
            elif cur_streak == 0 and d == rev[0]:
                continue
            else:
                break
        streak = max(cur_streak, 1)
    except Exception as e:
        print("GraphQL error (using fallback):", e)

    return {
        "repos": repos_count,
        "contribs": f"{total_contribs}+",
        "merged_prs": merged_prs,
        "streak": f"{streak}d",
        "stars": stars_count,
    }

def update_svg(filepath, stats):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Card 1: Repos
    content = re.sub(
        r'(<!-- CARD 1: REPOSITORIES -->.*?<!-- Big Value -->\s*<text[^>]*>)(.*?)(</text>)',
        rf'\g<1>{stats["repos"]}\g<3>',
        content,
        flags=re.DOTALL
    )
    # Card 2: Contributions
    content = re.sub(
        r'(<!-- CARD 2: CONTRIBUTIONS MADE -->.*?<!-- Big Value -->\s*<text[^>]*>)(.*?)(</text>)',
        rf'\g<1>{stats["contribs"]}\g<3>',
        content,
        flags=re.DOTALL
    )
    # Card 3: Merged PRs
    content = re.sub(
        r'(<!-- CARD 3: MERGED PULL REQUESTS -->.*?<!-- Big Value -->\s*<text[^>]*>)(.*?)(</text>)',
        rf'\g<1>{stats["merged_prs"]}\g<3>',
        content,
        flags=re.DOTALL
    )
    # Card 4: Streak
    content = re.sub(
        r'(<!-- CARD 4: CONTRIBUTION STREAK.*?<!-- Big Value -->\s*<text[^>]*>)(.*?)(</text>)',
        rf'\g<1>{stats["streak"]}\g<3>',
        content,
        flags=re.DOTALL
    )
    # Card 5: Stars
    content = re.sub(
        r'(<!-- CARD 5: STARS GOT.*?<!-- Big Value -->\s*<text[^>]*>)(.*?)(</text>)',
        rf'\g<1>{stats["stars"]}\g<3>',
        content,
        flags=re.DOTALL
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {filepath} with: {stats}")

if __name__ == "__main__":
    stats = get_stats()
    update_svg("swastik-github-analytics.svg", stats)
    update_svg("assets/swastik-github-analytics.svg", stats)
