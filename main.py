import os
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API_BASE = "https://oddslink.app/v1/sports"
KYIV = ZoneInfo("Europe/Kyiv")

SOCCER_TEAMS = [
    "Dynamo Kyiv", "Dynamo Kiev", "Динамо Киев", "Shakhtar Donetsk", "Шахтёр Донецк", "Шахтер Донецк",
    "Borussia Dortmund", "Боруссия Дортмунд", "Real Madrid", "Реал Мадрид",
    "Atletico Madrid", "Atlético Madrid", "Атлетико Мадрид", "Bayern Munich", "Bayern München", "Бавария",
    "Barcelona", "Барселона", "Manchester City", "Манчестер Сити", "Liverpool", "Ливерпуль",
    "Arsenal", "Арсенал", "The New Saints", "New Saints", "Нью-Сейнтс", "Paris Saint-Germain", "PSG", "ПСЖ",
]
SOCCER_COMPETITIONS = [
    "premier league ukraine", "ukraine premier league", "упл", "ukrainian cup", "кубок украины",
    "champions league", "лига чемпионов", "europa league", "лига европы",
    "conference league", "лига конференций",
    "euro", "world cup", "nations league", "qualifier", "qualification",
    "international friendly", "friendlies", "world cup qualification",
]
PRIORITY_TEAMS = [
    "Динамо Киев", "Dynamo Kyiv", "Dynamo Kiev",
    "Шахтёр Донецк", "Шахтер Донецк", "Shakhtar Donetsk",
    "Боруссия Дортмунд", "Borussia Dortmund", "Реал Мадрид", "Real Madrid",
    "Атлетико Мадрид", "Atletico Madrid", "Atlético Madrid",
    "Бавария", "Bayern Munich", "Bayern München", "Барселона", "Barcelona",
    "Манчестер Сити", "Manchester City", "Ливерпуль", "Liverpool",
    "Арсенал", "Arsenal", "Нью-Сейнтс", "The New Saints", "New Saints",
]
TENNIS_PRIORITY = [
    "Anna Kalinskaya", "Анна Калинская",
    "Mirra Andreeva", "Мирра Андреева",
    "Iva Jovic", "Iva Jović", "Ива Йович",
    "Elena Rybakina", "Елена Рыбакина",
    "Alexander Zverev", "Александр Зверев",
    "Carlos Alcaraz", "Карлос Алькарас",
    "Jannik Sinner", "Янник Синнер",
    "Daniil Medvedev", "Даниил Медведев",
]

def get_fixtures(sport):
    key = os.environ["ODDS_API_KEY"]
    response = requests.get(
        f"{API_BASE}/{sport}/odds",
        params={"markets": "h2h", "oddsFormat": "decimal", "dateFormat": "iso"},
        headers={"X-API-Key": key},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(data["error"])
    return data if isinstance(data, list) else []

def local_day(iso_time):
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    return dt.astimezone(KYIV).date()

def format_time(iso_time):
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    return dt.astimezone(KYIV).strftime("%H:%M")

def h2h_prices(event):
    # Average decimal prices across bookmakers for each outcome.
    values = {}
    books = event.get("bookmakers") or []
    for book in books:
        for market in book.get("markets") or []:
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes") or []:
                try:
                    price = float(outcome["price"])
                    if price > 1:
                        values.setdefault(outcome["name"], []).append(price)
                except (KeyError, TypeError, ValueError):
                    pass
    return {name: sum(prices) / len(prices) for name, prices in values.items() if prices}

def price_text(event, tennis=False):
    prices = h2h_prices(event)
    if not prices:
        return "Коэффициенты недоступны"
    if tennis:
        a, b = event.get("home_team", ""), event.get("away_team", "")
        return f"{a} — {prices[a]:.2f} | {b} — {prices[b]:.2f}" if a in prices and b in prices else "Коэффициенты недоступны"
    home, away = event.get("home_team", ""), event.get("away_team", "")
    draw = next((v for k, v in prices.items() if k.lower() in ("draw", "tie")), None)
    if home in prices and away in prices and draw is not None:
        return f"П1 {prices[home]:.2f} · X {draw:.2f} · П2 {prices[away]:.2f}"
    return "Коэффициенты недоступны"

def is_soccer_relevant(event):
    home, away = event.get("home_team", ""), event.get("away_team", "")
    league = ((event.get("league") or {}).get("title") or "").lower()
    text = f"{home} {away}".lower()
    team_match = any(t.lower() in text for t in SOCCER_TEAMS)
    comp_match = any(c in league for c in SOCCER_COMPETITIONS)
    # National-team games are included when the competition name clearly indicates international football.
    return team_match or comp_match

def soccer_sort_key(event):
    text = f"{event.get('home_team','')} {event.get('away_team','')}".lower()
    for idx, name in enumerate(PRIORITY_TEAMS):
        if name.lower() in text:
            return (0, idx, event.get("commence_time", ""))
    return (1, 999, event.get("commence_time", ""))

def is_tennis_relevant(event):
    text = f"{event.get('home_team','')} {event.get('away_team','')}".lower()
    return any(name.lower() in text for name in TENNIS_PRIORITY)

def discord_send(content):
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel = os.environ["DISCORD_CHANNEL_ID"]
    response = requests.post(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
        json={"content": content[:1900]},
        timeout=30,
    )
    response.raise_for_status()

def main():
    now = datetime.now(KYIV)
    # GitHub Actions has two UTC schedules for winter/summer time.
    # Only the run that actually lands at 00:00 Kyiv time publishes.
    if now.hour != 0 or now.minute > 10:
        print(f"Not Kyiv midnight ({now.isoformat()}); skipping.")
        return

    today = now.date()
    soccer = [e for e in get_fixtures("soccer")
              if e.get("commence_time") and local_day(e["commence_time"]) == today
              and is_soccer_relevant(e)]
    tennis = [e for e in get_fixtures("tennis")
              if e.get("commence_time") and local_day(e["commence_time"]) == today
              and is_tennis_relevant(e)]

    soccer.sort(key=soccer_sort_key)
    tennis.sort(key=lambda e: (
        next((i for i, name in enumerate(TENNIS_PRIORITY)
              if name.lower() in f"{e.get('home_team','')} {e.get('away_team','')}".lower()), 999),
        e.get("commence_time", "")
    ))

    lines = [f"🏆 **СПОРТИВНАЯ АФИША — {today.strftime('%d.%m.%Y')}**",
             "Время указано по Киеву.", ""]
    lines.append("⚽ **ФУТБОЛ**")
    if soccer:
        for e in soccer[:25]:
            league = (e.get("league") or {}).get("title", "Турнир")
            lines.append(f"**{format_time(e['commence_time'])}** · {league}")
            lines.append(f"{e.get('home_team','?')} — {e.get('away_team','?')}")
            lines.append(f"Коэффициенты: {price_text(e)}")
    else:
        lines.append("Подходящих матчей на сегодня не найдено.")

    lines += ["", "🎾 **ТЕННИС**"]
    if tennis:
        for e in tennis[:20]:
            tournament = (e.get("league") or {}).get("title") or e.get("sport_title") or "Турнир"
            lines.append(f"**{format_time(e['commence_time'])}** · {tournament}")
            lines.append(f"{e.get('home_team','?')} — {e.get('away_team','?')}")
            lines.append(f"Коэффициенты: {price_text(e, tennis=True)}")
    else:
        lines.append("Матчи выбранных игроков на сегодня не найдены.")

    lines += ["", "🧠 **АНАЛИТИЧЕСКИЙ КОММЕНТАРИЙ**",
              "ИИ-рецензия будет подключена отдельным этапом. Это не прогноз с гарантией результата и не рекомендация ставить."]
    discord_send("\n".join(lines))
    print(f"Published: {len(soccer)} football fixtures, {len(tennis)} tennis fixtures.")

if __name__ == "__main__":
    main()
