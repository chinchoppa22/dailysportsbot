# Daily Sports Bot

This repository publishes a daily football and tennis fixture digest to Discord using OddsLink.

## Files
- `main.py` — fetches OddsLink odds and posts the daily digest.
- `requirements.txt` — Python dependency.
- `.github/workflows/daily.yml` — scheduled GitHub Actions workflow.

## Required GitHub Actions secrets
- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID`
- `ODDS_API_KEY`

The workflow has UTC schedules at 21:00 and 22:00. The script checks `Europe/Kyiv` and publishes only when the local time is around midnight, covering winter/summer time changes. GitHub scheduled runs can be delayed.

## Important limitations of this first version
- Football filtering uses requested teams and competition-name matching; it is not yet a complete official FIFA/UEFA ranking integration.
- Tennis filtering currently includes the individually prioritized players only; ATP Top 20 / WTA Top 30 ranking feeds and tournament-category metadata are a later enhancement.
- The AI review is not enabled yet. It requires a separate LLM API key and may incur usage charges.
- Odds are averaged across available bookmaker prices for each outcome. If a complete market is unavailable, the script displays that odds are unavailable.
