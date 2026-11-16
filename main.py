import os
import re
import unicodedata
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_BASE = "https://oddslink.app/v1/sports"
KYIV = ZoneInfo("Europe/Kyiv")

# Официальные названия используем для поиска в данных API.
# Псевдонимы применяются только при выводе в Discord.
TEAM_ALIASES = {
    "Liverpool": "Ливерка",
    "Atletico Madrid": "Матрасники",
    "Atlético Madrid": "Матрасники",
    "Barcelona": "Варселона",
    "Real Madrid": "Реал Вардрид",
    "Shakhtar Donetsk": "Шлюхтар Донецк",
    "Шахтёр Донецк": "Шлюхтар Донецк",
    "Шахтер Донецк": "Шлюхтар Донецк",
}

# Клубы, за которыми следим независимо от турнира.
SOCCER_CLUBS = [
    "Dynamo Kyiv", "Dynamo Kiev", "Динамо Киев", "Динамо Київ",
    "Shakhtar Donetsk", "Шахтёр Донецк", "Шахтер Донецк",
    "Borussia Dortmund", "Боруссия Дортмунд",
    "Real Madrid", "Реал Мадрид",
    "Atletico Madrid", "Atlético Madrid", "Атлетико Мадрид",
    "Bayern Munich", "Bayern München", "Бавария",
    "Barcelona", "Барселона",
    "Manchester City", "Манчестер Сити",
    "Liverpool", "Ливерпуль",
    "Arsenal", "Арсенал",
    "The New Saints", "New Saints", "Нью-Сейнтс",
    "Paris Saint-Germain", "PSG", "ПСЖ",
]

# Европейские сборные + Аргентина и Бразилия.
NATIONAL_TEAMS = [
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan",
    "Belarus", "Belgium", "Bosnia", "Bosnia and Herzegovina",
    "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Czechia",
    "Denmark", "England", "Estonia", "Faroe Islands", "Finland",
    "France", "Georgia", "Germany", "Gibraltar", "Greece",
    "Hungary", "Iceland", "Ireland", "Israel", "Italy",
    "Kazakhstan", "Kosovo", "Latvia", "Liechtenstein", "Lithuania",
    "Luxembourg", "Malta", "Moldova", "Montenegro", "Netherlands",
    "North Macedonia", "Northern Ireland", "Norway", "Poland",
    "Portugal", "Romania", "Russia", "San Marino", "Scotland",
    "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden",
    "Switzerland", "Turkey", "Türkiye", "Ukraine", "Wales",
    "Argentina", "Brazil", "Brasil",
]

ALLOWED_COMPETITIONS = [
    "premier league ukraine", "ukraine premier league", "упл",
    "ukrainian cup", "ukraine cup", "кубок украины", "кубок україни",
    "champions league", "лига чемпионов",
    "europa league", "лига европы",
    "conference league", "лига конференций",
]

INTERNATIONAL_MARKERS = [
    "nations league", "uefa euro", "euro qualification",
    "european qualification", "world cup qualification",
    "world cup qualifiers", "international friendly",
    "international friendlies", "friendlies", "qualifier",
    "qualification",
]

# Ручной приоритет клубов — порядок здесь важнее любых рейтингов.
PRIORITY_TEAMS = [
    "Dynamo Kyiv", "Dynamo Kiev", "Динамо Киев", "Динамо Київ",
    "Shakhtar Donetsk", "Шахтёр Донецк", "Шахтер Донецк",
    "Borussia Dortmund", "Боруссия Дортмунд",
    "Real Madrid", "Реал Мадрид",
    "Atletico Madrid", "Atlético Madrid", "Атлетико Мадрид",
    "Bayern Munich", "Bayern München", "Бавария",
    "Barcelona", "Барселона",
    "Manchester City", "Манчестер Сити",
    "Liverpool", "Ливерпуль",
    "Arsenal", "Арсенал",
    "The New Saints", "New Saints", "Нью-Сейнтс",
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


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9а-я]+", " ", value.lower()).strip()


def contains_name(text, names):
    normalized_text = f" {normalize(text)} "
    return any(f" {normalize(name)} " in normalized_text for name in names)


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


def display_team(name):
    """Показывает прозвище, если оно задано; иначе исходное имя."""
    normalized = normalize(name)
    for original, nickname in TEAM_ALIASES.items():
        if normalize(original) == normalized:
            return nickname
    return name or "?"


def h2h_prices(event):
    # Среднее десятичных коэффициентов по доступным букмекерам.
    values = {}
    for book in event.get("bookmakers") or []:
        for market in book.get("markets") or []:
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes") or []:
                try:
                    price = float(outcome["price"])
                    if price > 1:
                        values.setdefault(normalize(outcome["name"]), []).append(price)
                except (KeyError, TypeError, ValueError):
                    pass
    return {name: sum(prices) / len(prices) for name, prices in values.items() if prices}


def price_text(event, tennis=False):
    prices = h2h_prices(event)
    if not prices:
        return "Коэффициенты недоступны"

    home = normalize(event.get("home_team", ""))
    away = normalize(event.get("away_team", ""))

    if tennis:
        if home in prices and away in prices:
            return f"{prices[home]:.2f} · {prices[away]:.2f}"
        return "Коэффициенты недоступны"

    draw = next((v for k, v in prices.items() if k in ("draw", "tie")), None)
    if home in prices and away in prices and draw is not None:
        return f"П1 {prices[home]:.2f} · X {draw:.2f} · П2 {prices[away]:.2f}"
    return "Коэффициенты недоступны"


def is_national_team_match(event):
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    league = (event.get("league") or {}).get("title", "")
    international = contains_name(league, INTERNATIONAL_MARKERS)
    both_national = (
        contains_name(home, NATIONAL_TEAMS)
        and contains_name(away, NATIONAL_TEAMS)
    )
    return international and both_national


def is_soccer_relevant(event):
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    league = (event.get("league") or {}).get("title", "")

    # Из клубов берём только команды из заданного списка.
    selected_club = (
        contains_name(home, SOCCER_CLUBS)
        or contains_name(away, SOCCER_CLUBS)
    )

    # Из турниров берём УПЛ, Кубок Украины и три еврокубка.
    selected_competition = contains_name(league, ALLOWED_COMPETITIONS)

    # Сборные — только европейские, Аргентина и Бразилия,
    # и только когда обе команды распознаны как сборные.
    national_match = is_national_team_match(event)

    return selected_club or selected_competition or national_match


def soccer_sort_key(event):
    text = f"{event.get('home_team', '')} {event.get('away_team', '')}"
    for idx, name in enumerate(PRIORITY_TEAMS):
        if contains_name(text, [name]):
            return (0, idx, event.get("commence_time", ""))
    return (1, 999, event.get("commence_time", ""))


def is_tennis_relevant(event):
    text = f"{event.get('home_team', '')} {event.get('away_team', '')}"
    return contains_name(text, TENNIS_PRIORITY)


def tennis_sort_key(event):
    text = f"{event.get('home_team', '')} {event.get('away_team', '')}"
    for idx, name in enumerate(TENNIS_PRIORITY):
        if contains_name(text, [name]):
            return (idx, event.get("commence_time", ""))
    return (999, event.get("commence_time", ""))


def discord_send(content):
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel = os.environ["DISCORD_CHANNEL_ID"]
    response = requests.post(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        },
        json={"content": content[:1900]},
        timeout=30,
    )
    response.raise_for_status()


def main():
    now = datetime.now(KYIV)
    manual_run = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    # Автоматический запуск публикует только около полуночи по Киеву.
    if not manual_run and (now.hour != 0 or now.minute > 10):
        print(f"Not Kyiv midnight ({now.isoformat()}); skipping.")
        return

    today = now.date()

    soccer = [
        event for event in get_fixtures("soccer")
        if event.get("commence_time")
        and local_day(event["commence_time"]) == today
        and is_soccer_relevant(event)
    ]
    tennis = [
        event for event in get_fixtures("tennis")
        if event.get("commence_time")
        and local_day(event["commence_time"]) == today
        and is_tennis_relevant(event)
    ]

    soccer.sort(key=soccer_sort_key)
    tennis.sort(key=tennis_sort_key)

    lines = [
        f"🏆 **BEZUMNIY HAALAND — СПОРТИВНАЯ АФИША {today.strftime('%d.%m.%Y')}**",
        "Время указано по Киеву.",
        "",
        "⚽ **ФУТБОЛ**",
    ]

    if soccer:
        for event in soccer[:25]:
            league = (event.get("league") or {}).get("title") or "Турнир"
            home = display_team(event.get("home_team", "?"))
            away = display_team(event.get("away_team", "?"))
            lines.append(f"**{format_time(event['commence_time'])}** · {league}")
            lines.append(f"{home} — {away}")
            lines.append(f"Коэффициенты: {price_text(event)}")
    else:
        lines.append("Сегодня подходящих матчей из выбранного списка нет.")

    lines += ["", "🎾 **ТЕННИС**"]

    if tennis:
        for event in tennis[:20]:
            tournament = (
                (event.get("league") or {}).get("title")
                or event.get("sport_title")
                or "Турнир"
            )
            home = display_team(event.get("home_team", "?"))
            away = display_team(event.get("away_team", "?"))
            prices = price_text(event, tennis=True)
            if prices != "Коэффициенты недоступны":
                price_line = f"Коэффициенты (П1 · П2): {prices}"
            else:
                price_line = prices
            lines.append(f"**{format_time(event['commence_time'])}** · {tournament}")
            lines.append(f"{home} — {away}")
            lines.append(price_line)
    else:
        lines.append("Матчи выбранных игроков на сегодня не найдены.")

    lines += [
        "",
        "🧠 **BEZUMNIY HAALAND DUMAYET...**",
        "Аналитическая рубрика будет подключена следующим этапом. "
        "Никаких выдуманных травм, судей или статистики — только проверяемые данные.",
    ]

    discord_send("\n".join(lines))
    print(
        f"Published: {len(soccer)} football fixtures, "
        f"{len(tennis)} tennis fixtures."
    )


if __name__ == "__main__":
    main()
