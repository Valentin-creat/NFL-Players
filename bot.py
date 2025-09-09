
# nfl-wiki-slack-bot / bot.py
# Hourly Wikipedia scanner -> Slack (Incoming Webhook)
#
# Setup:
#   - pip install -r requirements.txt
#   - export SLACK_WEBHOOK="https://hooks.slack.com/services/XXX/YYY/ZZZ"
#
# Notes:
#   - This scans the *last hour* of Wikipedia "recent changes"
#   - Filters for likely NFL player pages
#   - For each page, grabs a simple "team line" from the plaintext
#   - Posts a single batched message to Slack
#
import os
import requests
from datetime import datetime, timedelta, timezone

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "nfl-wiki-slack-bot/1.0 (contact: your-email@example.com)"
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "").strip()

if not SLACK_WEBHOOK:
    raise SystemExit("Missing SLACK_WEBHOOK env var")

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def looks_like_nfl_player(title: str) -> bool:
    """Very simple heuristic to narrow to NFL player articles."""
    tl = title.lower()
    return ("(american football)" in tl) or ("nfl" in tl) or ("football player" in tl)


def recent_changes_last_hour():
    """Yield all recent changes within the last hour, handling pagination."""
    now = datetime.now(timezone.utc)
    start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "action": "query",
        "list": "recentchanges",
        "rcstart": start,
        "rcend": end,
        "rcnamespace": 0,                # main articles
        "rctype": "edit|new",
        "rcprop": "title|ids|timestamp|comment|sizes|flags",
        "rclimit": "500",
        "format": "json"
    }

    rccontinue = None
    while True:
        if rccontinue:
            params["rccontinue"] = rccontinue
        r = session.get(WIKI_API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        changes = data.get("query", {}).get("recentchanges", [])
        for c in changes:
            yield c
        rccontinue = data.get("continue", {}).get("rccontinue")
        if not rccontinue:
            break


def fetch_plaintext(title: str) -> str:
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "format": "json"
    }
    r = session.get(WIKI_API, params=params, timeout=30)
    r.raise_for_status()
    pages = r.json()["query"]["pages"]
    return next(iter(pages.values())).get("extract", "") or ""


def parse_team_line(text: str) -> str:
    # Naive: scan for lines that likely contain team info
    keys = ["Current team", "Team(s)", "NFL team", "Roster status"]
    for line in text.splitlines():
        if any(k in line for k in keys):
            return line.strip()
    return ""


def post_to_slack(lines):
    if not lines:
        return
    # Batch into one message to avoid spam
    header = "*NFL Wikipedia Watch — last hour*"
    payload = {"text": header + "\n" + "\n".join(lines[:45])}
    resp = session.post(SLACK_WEBHOOK, json=payload, timeout=15)
    resp.raise_for_status()


def main():
    # Collect last change per title within the hour
    latest_by_title = {}
    for rc in recent_changes_last_hour():
        title = rc.get("title", "")
        ts = rc.get("timestamp", "")
        if not title:
            continue
        existing = latest_by_title.get(title)
        if (not existing) or (ts > existing.get("timestamp", "")):
            latest_by_title[title] = rc

    alerts = []
    for title, rc in latest_by_title.items():
        if not looks_like_nfl_player(title):
            continue
        text = fetch_plaintext(title)
        team_line = parse_team_line(text)
        pageid = rc.get("pageid", "")
        ts = rc.get("timestamp", "")
        url = f"https://en.wikipedia.org/?curid={pageid}" if pageid else f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        if team_line:
            alerts.append(f"• *{title}* — {team_line}\n{ts} | {url}")

    if not alerts:
        # Optional: send a quiet heartbeat so you know the job ran
        # Comment the next line if you don't want heartbeats
        alerts = ["No NFL player page updates detected in the past hour."]

    post_to_slack(alerts)


if __name__ == "__main__":
    main()
