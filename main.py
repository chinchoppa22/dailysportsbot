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
    "Inter Milan": "Интер",
    "Internazionale": "Интер",
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
    "Inter Milan", "Internazionale", "Inter", "Интер Милан",
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



# Русские названия для популярных команд, сборных и турниров.
# Неизвестные английские названия ниже автоматически транслитерируются кириллицей.
RUSSIAN_NAMES = {
    # Клубы
    "Dynamo Kyiv": "Динамо Киев", "Dynamo Kiev": "Динамо Киев",
    "Shakhtar Donetsk": "Шлюхтар Донецк", "Borussia Dortmund": "Боруссия Дортмунд",
    "Real Madrid": "Реал Вардрид", "Atletico Madrid": "Матрасники",
    "Atlético Madrid": "Матрасники", "Bayern Munich": "Бавария",
    "Bayern München": "Бавария", "Barcelona": "Варселона",
    "Manchester City": "Манчестер Сити", "Liverpool": "Ливерка",
    "Arsenal": "Арсенал", "The New Saints": "Нью-Сейнтс",
    "New Saints": "Нью-Сейнтс", "Paris Saint-Germain": "ПСЖ", "PSG": "ПСЖ",
    "Inter Milan": "Интер", "Internazionale": "Интер", "Inter": "Интер",
    "Manchester United": "Манчестер Юнайтед", "Chelsea": "Челси",
    "Tottenham Hotspur": "Тоттенхэм", "Tottenham": "Тоттенхэм",
    "Newcastle United": "Ньюкасл", "Aston Villa": "Астон Вилла",
    "AC Milan": "Милан", "Milan": "Милан", "Juventus": "Ювентус",
    "Roma": "Рома", "Napoli": "Наполи", "Lazio": "Лацио",
    "Atalanta": "Аталанта", "Bayer Leverkusen": "Байер", "Leverkusen": "Байер",
    "RB Leipzig": "РБ Лейпциг", "Eintracht Frankfurt": "Айнтрахт",
    "Borussia Monchengladbach": "Боруссия Мёнхенгладбах",
    "Borussia Mönchengladbach": "Боруссия Мёнхенгладбах",
    "Ajax": "Аякс", "PSV": "ПСВ", "Feyenoord": "Фейеноорд",
    "Benfica": "Бенфика", "Porto": "Порту", "Sporting CP": "Спортинг",
    "Celtic": "Селтик", "Rangers": "Рейнджерс",
    # Сборные
    "Albania": "Албания", "Andorra": "Андорра", "Armenia": "Армения",
    "Austria": "Австрия", "Azerbaijan": "Азербайджан", "Belarus": "Беларусь",
    "Belgium": "Бельгия", "Bosnia and Herzegovina": "Босния и Герцеговина",
    "Bosnia": "Босния", "Bulgaria": "Болгария", "Croatia": "Хорватия",
    "Cyprus": "Кипр", "Czech Republic": "Чехия", "Czechia": "Чехия",
    "Denmark": "Дания", "England": "Англия", "Estonia": "Эстония",
    "Faroe Islands": "Фарерские острова", "Finland": "Финляндия",
    "France": "Франция", "Georgia": "Грузия", "Germany": "Германия",
    "Gibraltar": "Гибралтар", "Greece": "Греция", "Hungary": "Венгрия",
    "Iceland": "Исландия", "Ireland": "Ирландия", "Israel": "Израиль",
    "Italy": "Италия", "Kazakhstan": "Казахстан", "Kosovo": "Косово",
    "Latvia": "Латвия", "Liechtenstein": "Лихтенштейн", "Lithuania": "Литва",
    "Luxembourg": "Люксембург", "Malta": "Мальта", "Moldova": "Молдова",
    "Montenegro": "Черногория", "Netherlands": "Нидерланды",
    "North Macedonia": "Северная Македония", "Northern Ireland": "Северная Ирландия",
    "Norway": "Норвегия", "Poland": "Польша", "Portugal": "Португалия",
    "Romania": "Румыния", "Russia": "Россия", "San Marino": "Сан-Марино",
    "Scotland": "Шотландия", "Serbia": "Сербия", "Slovakia": "Словакия",
    "Slovenia": "Словения", "Spain": "Испания", "Sweden": "Швеция",
    "Switzerland": "Швейцария", "Turkey": "Турция", "Türkiye": "Турция",
    "Ukraine": "Украина", "Wales": "Уэльс", "Argentina": "Аргентина",
    "Brazil": "Бразилия", "Brasil": "Бразилия",
    # Турниры и лиги
    "UEFA Champions League": "Лига чемпионов УЕФА",
    "Champions League": "Лига чемпионов", "UEFA Europa League": "Лига Европы УЕФА",
    "Europa League": "Лига Европы", "UEFA Conference League": "Лига конференций УЕФА",
    "Conference League": "Лига конференций", "Ukrainian Premier League": "Украинская Премьер-лига",
    "Ukraine Premier League": "Украинская Премьер-лига", "Premier League Ukraine": "Украинская Премьер-лига",
    "Ukrainian Cup": "Кубок Украины", "Ukraine Cup": "Кубок Украины",
    "UEFA Nations League": "Лига наций УЕФА", "Nations League": "Лига наций",
    "FIFA World Cup": "Чемпионат мира", "World Cup": "Чемпионат мира",
    "UEFA European Championship": "Чемпионат Европы", "European Championship": "Чемпионат Европы",
    "Euro": "Евро", "International Friendly": "Международный товарищеский матч",
    "Friendlies": "Товарищеские матчи", "Premier League": "Английская Премьер-лига",
    "La Liga": "Чемпионат Испании", "Bundesliga": "Бундеслига",
    "Serie A": "Серия А", "Ligue 1": "Лига 1", "Eredivisie": "Эредивизи",
    "ATP Finals": "Итоговый турнир ATP", "WTA Finals": "Итоговый турнир WTA",
    "Australian Open": "Открытый чемпионат Австралии", "French Open": "Ролан Гаррос",
    "Roland Garros": "Ролан Гаррос", "Wimbledon": "Уимблдон",
    "US Open": "Открытый чемпионат США", "Davis Cup": "Кубок Дэвиса",
    "Billie Jean King Cup": "Кубок Билли Джин Кинг",
}

# Особые названия стран по просьбе пользователя.
RUSSIAN_NAMES.update({
    "Netherlands": "Нидеры",
    "Slovakia": "Словенско",
    "San Marino": "Легенды футбола",
    "Ukraine": "Урина",
})

# Флаги национальных сборных. Внутренние названия API не меняются.
NATIONAL_FLAGS = {
    "Albania": "🇦🇱", "Andorra": "🇦🇩", "Armenia": "🇦🇲",
    "Austria": "🇦🇹", "Azerbaijan": "🇦🇿", "Belarus": "🇧🇾",
    "Belgium": "🇧🇪", "Bosnia": "🇧🇦", "Bosnia and Herzegovina": "🇧🇦",
    "Bulgaria": "🇧🇬", "Croatia": "🇭🇷", "Cyprus": "🇨🇾",
    "Czech Republic": "🇨🇿", "Czechia": "🇨🇿", "Denmark": "🇩🇰",
    "England": "🏴", "Estonia": "🇪🇪", "Faroe Islands": "🇫🇴",
    "Finland": "🇫🇮", "France": "🇫🇷", "Georgia": "🇬🇪",
    "Germany": "🇩🇪", "Gibraltar": "🇬🇮", "Greece": "🇬🇷",
    "Hungary": "🇭🇺", "Iceland": "🇮🇸", "Ireland": "🇮🇪",
    "Israel": "🇮🇱", "Italy": "🇮🇹", "Kazakhstan": "🇰🇿",
    "Kosovo": "🇽🇰", "Latvia": "🇱🇻", "Liechtenstein": "🇱🇮",
    "Lithuania": "🇱🇹", "Luxembourg": "🇱🇺", "Malta": "🇲🇹",
    "Moldova": "🇲🇩", "Montenegro": "🇲🇪", "Netherlands": "🇳🇱",
    "North Macedonia": "🇲🇰", "Northern Ireland": "🇬🇧",
    "Norway": "🇳🇴", "Poland": "🇵🇱", "Portugal": "🇵🇹",
    "Romania": "🇷🇴", "Russia": "🇷🇺", "San Marino": "🇸🇲",
    "Scotland": "🏴", "Serbia": "🇷🇸", "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮", "Spain": "🇪🇸", "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭", "Turkey": "🇹🇷", "Türkiye": "🇹🇷",
    "Ukraine": "🇺🇦", "Wales": "🏴", "Argentina": "🇦🇷",
    "Brazil": "🇧🇷", "Brasil": "🇧🇷",
}

# Для клубов используем ровно один цветной значок.
CLUB_BADGES = {
     "Dynamo Kyiv": "🔵", "Dynamo Kiev": "🔵", "Динамо Киев": "🔵", "Динамо Київ": "🔵",
     "Shakhtar Donetsk": "🟠", "Шахтёр Донецк": "🟠", "Шахтер Донецк": "🟠",
    "Borussia Dortmund": "🟡", "Боруссия Дортмунд": "🟡",
     "Real Madrid": "⚪", "Реал Мадрид": "⚪",
    "Atletico Madrid": "🔴", "Atlético Madrid": "🔴", "Атлетико Мадрид": "🔴",
     "Bayern Munich": "🔴", "Bayern München": "🔴", "Бавария": "🔴",
    "Barcelona": "🔵", "Барселона": "🔵",
     "Manchester City": "🩵", "Манчестер Сити": "🩵",
    "Liverpool": "🔴", "Ливерпуль": "🔴", "Arsenal": "🔴", "Арсенал": "🔴",
    "The New Saints": "🟢", "New Saints": "🟢",
     "Paris Saint-Germain": "🔵", "PSG": "🔵", "ПСЖ": "🔵",
     "Inter Milan": "🔵", "Internazionale": "🔵", "Inter": "🔵", "Интер": "🔵",
}

TENNIS_PLAYER_NAMES = {
    "Anna Kalinskaya": "Анна Калинская",
    "Mirra Andreeva": "Мирра Андреева",
    "Iva Jovic": "Ива Йович", "Iva Jović": "Ива Йович",
    "Elena Rybakina": "Елена Рыбакина",
    "Alexander Zverev": "Александр Зверев",
    "Carlos Alcaraz": "Карлос Алькарас",
    "Jannik Sinner": "Янник Синнер",
    "Daniil Medvedev": "Даниил Медведев",
}
TENNIS_PLAYER_FLAGS = {
    "Anna Kalinskaya": "🇷🇺", "Mirra Andreeva": "🇷🇺",
    "Iva Jovic": "🇺🇸", "Iva Jović": "🇺🇸",
    "Elena Rybakina": "🇰🇿", "Alexander Zverev": "🇩🇪",
    "Carlos Alcaraz": "🇪🇸", "Jannik Sinner": "🇮🇹",
    "Daniil Medvedev": "🇷🇺",
}


# Приближённая транслитерация для редких названий, которых нет в словаре.
_TRANSLIT = {
    "shch": "щ", "sch": "щ", "zh": "ж", "kh": "х", "ch": "ч",
    "sh": "ш", "yu": "ю", "ya": "я", "yo": "ё", "ts": "ц",
    "th": "т", "ph": "ф", "ck": "к", "qu": "кв",
}

def transliterate_to_russian(value):
    text = str(value or "?")
    result = []
    i = 0
    lower = text.lower()
    while i < len(text):
        if text[i].isspace() or text[i] in "-–—'’.&()/":
            result.append(text[i])
            i += 1
            continue
        matched = False
        for latin, cyrillic in _TRANSLIT.items():
            if lower.startswith(latin, i):
                piece = cyrillic
                if text[i].isupper():
                    piece = piece.capitalize()
                result.append(piece)
                i += len(latin)
                matched = True
                break
        if matched:
            continue
        char = lower[i]
        letter_map = {
            "a":"а", "b":"б", "c":"к", "d":"д", "e":"е", "f":"ф",
            "g":"г", "h":"х", "i":"и", "j":"дж", "k":"к", "l":"л",
            "m":"м", "n":"н", "o":"о", "p":"п", "r":"р", "s":"с",
            "t":"т", "u":"у", "v":"в", "w":"в", "x":"кс", "y":"й", "z":"з",
        }
        piece = letter_map.get(char, text[i])
        if text[i].isupper():
            piece = piece.capitalize()
        result.append(piece)
        i += 1
    return "".join(result)


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


def russian_display_name(name):
    """Переводит известные названия; неизвестные английские транслитерирует."""
    value = str(name or "?").strip()
    normalized = normalize(value)
    for original, russian in RUSSIAN_NAMES.items():
        if normalize(original) == normalized:
            return russian
    # Сначала сохраняем уже заданные авторские прозвища.
    for original, nickname in TEAM_ALIASES.items():
        if normalize(original) == normalized:
            return nickname
    # Если в названии есть кириллица, не портим его транслитерацией.
    if re.search(r"[а-яё]", value, re.IGNORECASE):
        return value
    # Сохраняем спортивные аббревиатуры и переводим остальное.
    value = re.sub(r"\b(ATP|WTA|ITF|FIFA|UEFA|FC|SC|CF|AC|BC)\b", lambda m: m.group(1), value, flags=re.I)
    return transliterate_to_russian(value)


def _mapped_value(name, mapping):
    normalized = normalize(name)
    for original, value in mapping.items():
        if normalize(original) == normalized:
            return value
    return None


def display_team(name):
    value = str(name or "?").strip()
    # Сначала проверяем сборные: у них отображается государственный флаг.
    flag = _mapped_value(value, NATIONAL_FLAGS)
    if flag:
        return f"{flag} {russian_display_name(value)}"
    # Затем клубы: один цветной значок перед названием.
    badge = _mapped_value(value, CLUB_BADGES)
    if badge:
        return f"{badge} {russian_display_name(value)}"
    # Для остальных названий не придумываем флаг или цвет клуба.
    return f"⚽ {russian_display_name(value)}"


def display_tennis_player(name):
    value = str(name or "?").strip()
    russian = _mapped_value(value, TENNIS_PLAYER_NAMES) or russian_display_name(value)
    flag = _mapped_value(value, TENNIS_PLAYER_FLAGS)
    return f"{flag} {russian}" if flag else russian


def display_competition(name):
    return russian_display_name(name)


def discord_send(content):
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel = os.environ["DISCORD_CHANNEL_ID"]
    # Discord ограничивает текст одного сообщения 2000 символами.
    # Отправляем несколькими частями только если афиша действительно длинная.
    chunks = []
    remaining = content
    while len(remaining) > 1900:
        split_at = remaining.rfind("\n\n", 0, 1900)
        if split_at < 500:
            split_at = remaining.rfind("\n", 0, 1900)
        if split_at < 1:
            split_at = 1900
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)

    for chunk in chunks:
        response = requests.post(
            f"https://discord.com/api/v10/channels/{channel}/messages",
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
            },
            json={"content": chunk},
            timeout=30,
        )
        response.raise_for_status()


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
        f"🏆 **BEZUMNIY HAALAND**",
        f"**СПОРТИВНАЯ АФИША · {today.strftime('%d.%m.%Y')}**",
        "🕒 Время указано по Киеву.",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "⚽ **ФУТБОЛ**",
        "",
    ]

    if soccer:
        # Группируем матчи по турнирам, сохраняя порядок приоритетов.
        grouped_soccer = {}
        for event in soccer[:25]:
            league = (event.get("league") or {}).get("title") or "Турнир"
            grouped_soccer.setdefault(display_competition(league), []).append(event)

        for competition, events in grouped_soccer.items():
            lines.append(f"🏆 **{competition.upper()}**")
            for event in events:
                home = display_team(event.get("home_team", "?"))
                away = display_team(event.get("away_team", "?"))
                lines.append(
                    f"`{format_time(event['commence_time'])}`  {home} — {away}"
                )
                lines.append(f"　`{price_text(event)}`")
                lines.append("")
    else:
        lines.append("Сегодня подходящих матчей из выбранного списка нет.")
        lines.append("")

    lines += ["━━━━━━━━━━━━━━━━━━━━", "🎾 **ТЕННИС**", ""]

    if tennis:
        for event in tennis[:20]:
            tournament = (
                (event.get("league") or {}).get("title")
                or event.get("sport_title")
                or "Турнир"
            )
            home = display_tennis_player(event.get("home_team", "?"))
            away = display_tennis_player(event.get("away_team", "?"))
            prices = price_text(event, tennis=True)
            lines.append(
                f"**{display_competition(tournament)}** · "
                f"`{format_time(event['commence_time'])}`"
            )
            lines.append(f"{home} — {away}")
            lines.append(f"`П1 {prices.split(' · ')[0]} · П2 {prices.split(' · ')[1]}`"
                         if prices != "Коэффициенты недоступны"
                         else prices)
            lines.append("")
    else:
        lines.append("Матчи выбранных игроков на сегодня не найдены.")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
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
