
# NFL Wikipedia → Slack Bot (Hourly)

Scans Wikipedia **recent changes** for the **last hour**, looks for likely NFL player pages, grabs a simple "team line" (e.g., *Current team* / *Team(s)*) and posts a summary to Slack via **Incoming Webhook**.

## Quick start
1. Create a Slack App → enable **Incoming Webhooks** → add to your channel → copy the Webhook URL.
2. Fork/clone this repo.
3. In GitHub: **Settings → Secrets and variables → Actions → New repository secret** → `SLACK_WEBHOOK` with your webhook URL.
4. The included GitHub Action runs **hourly** (cron `0 * * * *`). You can also run locally:

   ```bash
   pip install -r requirements.txt
   export SLACK_WEBHOOK="https://hooks.slack.com/services/XXX/YYY/ZZZ"
   python bot.py
   ```

## Notes
- Uses a simple heuristic to detect NFL player pages (title contains “(American football)” or “NFL”).
- No persistent state is required; it only examines the last hour window.
- For richer accuracy, you can upgrade the parsing to read the article **infobox** or query **Wikidata P54** (member of sports team).
- Be courteous: we include a descriptive **User-Agent** and modest timeouts.

## Customize
- Edit `looks_like_nfl_player()` to tighten/loosen filters.
- Modify `parse_team_line()` if you want different fields.
- Switch to Slack **Block Kit** by building a `blocks` payload in `post_to_slack()`.
