import os
import json
import re
import unicodedata
import requests
import time as time_module
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API_BASE = "https://oddslink.app/v1/sports"
SPORTS_API_BASE = "https://api.sportsapi.app/v2"
KYIV = ZoneInfo("Europe/Kyiv")
SPORTS_API_MIN_INTERVAL = 6.1  # Free plan: 10 requests per minute.
_sports_api_last_request = 0.0
_sports_api_cache = {}

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


def discord_send(content, date_label=None):
    """Send the daily digest in chunks and attach the banner to the first message."""
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel = os.environ["DISCORD_CHANNEL_ID"]

    # Keep every Discord message below the 2,000-character content limit.
    chunks = []
    remaining = content
    while len(remaining) > 1850:
        split_at = remaining.rfind("\n\n", 0, 1850)
        if split_at < 500:
            split_at = remaining.rfind("\n", 0, 1850)
        if split_at < 1:
            split_at = 1850
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)

    banner_path = os.path.join(os.path.dirname(__file__), "haaland_banner.png")
    for index, chunk in enumerate(chunks):
        payload = {"content": chunk}
        files = None
        data = None

        if index == 0 and os.path.isfile(banner_path):
            payload["embeds"] = [{
                "title": "🏆 BEZUMNIY HAALAND",
                "description": (
                    f"СПОРТИВНАЯ АФИША · {date_label}\n"
                    "Футбол • Теннис • Коэффициенты букмекеров\n"
                    "🕒 Время указано по Киеву"
                ),
                "color": 0x5C91C9,
                "image": {"url": "attachment://haaland_banner.png"},
                "footer": {"text": "DAILY SPORTS DIGEST"},
            }]
            data = {"payload_json": json.dumps(payload, ensure_ascii=False)}
            files = {
                "files[0]": (
                    "haaland_banner.png",
                    open(banner_path, "rb"),
                    "image/png",
                )
            }

        try:
            if files:
                response = requests.post(
                    f"https://discord.com/api/v10/channels/{channel}/messages",
                    headers={"Authorization": f"Bot {token}"},
                    data=data,
                    files=files,
                    timeout=60,
                )
            else:
                response = requests.post(
                    f"https://discord.com/api/v10/channels/{channel}/messages",
                    headers={
                        "Authorization": f"Bot {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30,
                )
            response.raise_for_status()
        finally:
            if files:
                files["files[0]"][1].close()


def _ansi_odds(value, color_code):
    return f"\x1b[{color_code}m{value:.2f}\x1b[0m"


def colored_price_text(event, tennis=False):
    """Format odds with muted ANSI colors: favorite green, draw gray, outsider red."""
    prices = h2h_prices(event)
    if not prices:
        return "Коэффициенты недоступны"

    home = prices.get(normalize(event.get("home_team", "")))
    away = prices.get(normalize(event.get("away_team", "")))
    if home is None or away is None:
        return "Коэффициенты недоступны"

    # ANSI 2;32/2;31 are deliberately dim rather than vivid.
    if home < away:
        home_color, away_color = "2;32", "2;31"
    elif away < home:
        home_color, away_color = "2;31", "2;32"
    else:
        home_color = away_color = "2;37"

    if tennis:
        text = (
            f"П1 {_ansi_odds(home, home_color)}  ·  "
            f"П2 {_ansi_odds(away, away_color)}"
        )
    else:
        draw = next((v for k, v in prices.items() if k in ("draw", "tie")), None)
        if draw is None:
            return "Коэффициенты недоступны"
        text = (
            f"П1 {_ansi_odds(home, home_color)}  ·  "
            f"X {_ansi_odds(draw, '2;37')}  ·  "
            f"П2 {_ansi_odds(away, away_color)}"
        )

    return f"```ansi\n{text}\n```"


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


def sports_api_get(path, params=None, cache=True):
    """GET SportsAPI v2. The free plan is limited to 10 requests/minute."""
    global _sports_api_last_request
    key = os.environ.get("TENNIS_API_KEY")
    if not key:
        print("TENNIS_API_KEY is missing; tennis enrichment is disabled.")
        return None

    cache_key = (path, tuple(sorted((params or {}).items())))
    if cache and cache_key in _sports_api_cache:
        return _sports_api_cache[cache_key]

    elapsed = time_module.monotonic() - _sports_api_last_request
    if _sports_api_last_request and elapsed < SPORTS_API_MIN_INTERVAL:
        time_module.sleep(SPORTS_API_MIN_INTERVAL - elapsed)

    try:
        response = requests.get(
            f"{SPORTS_API_BASE}{path}",
            params=params or {},
            headers={"Authorization": f"Bearer {key}"},
            timeout=45,
        )
        _sports_api_last_request = time_module.monotonic()
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if cache:
            _sports_api_cache[cache_key] = data
        return data
    except requests.RequestException as exc:
        print(f"SportsAPI request failed for {path}: {exc}")
        return None
    except (ValueError, AttributeError) as exc:
        print(f"SportsAPI returned invalid JSON for {path}: {exc}")
        return None


def _ranking_map(tour, limit):
    rows = sports_api_get(f"/rankings/{tour}") or []
    result = {}
    for row in rows:
        player = row.get("team") or {}
        player_id = player.get("id")
        position = row.get("position")
        if player_id and isinstance(position, int) and position <= limit:
            result[int(player_id)] = {
                "position": position,
                "name": player.get("name", ""),
                "tour": tour.upper(),
            }
    return result


def _is_priority_tennis_player(name):
    return contains_name(name, TENNIS_PRIORITY)


def get_sportsapi_tennis_fixtures(target_day, odds_events):
    """Get ATP/WTA fixtures, filter by ATP top 20 / WTA top 30 and priority players."""
    if not os.environ.get("TENNIS_API_KEY"):
        print("TENNIS_API_KEY is missing; using OddsLink priority-player fallback.")
        return []
    categories = sports_api_get("/categories", {"sport": "tennis"}) or []
    atp_rankings = _ranking_map("atp", 20)
    wta_rankings = _ranking_map("wta", 30)
    rankings = {**atp_rankings, **wta_rankings}

    tours = []
    for category in categories:
        name = str(category.get("name") or "").strip()
        normalized = normalize(name)
        if normalized == "atp" or normalized.startswith("atp "):
            tours.append((category, "ATP"))
        elif normalized == "wta" or normalized.startswith("wta "):
            tours.append((category, "WTA"))

    # Kyiv's calendar day overlaps two UTC dates (depending on daylight saving).
    local_start = datetime.combine(target_day, datetime.min.time(), tzinfo=KYIV)
    local_end = local_start + timedelta(days=1) - timedelta(seconds=1)
    utc_dates = sorted({
        local_start.astimezone(timezone.utc).date().isoformat(),
        local_end.astimezone(timezone.utc).date().isoformat(),
    })

    odds_lookup = {}
    for odds_event in odds_events:
        h = normalize(odds_event.get("home_team", ""))
        a = normalize(odds_event.get("away_team", ""))
        odds_lookup[(h, a)] = odds_event
        odds_lookup[(a, h)] = odds_event

    results = {}
    for category, tour in tours:
        category_id = category.get("id")
        if not category_id:
            continue
        for utc_date in utc_dates:
            fixtures = sports_api_get(
                "/fixtures", {"date": utc_date, "category": category_id}
            ) or []
            for fixture in fixtures:
                start_time = fixture.get("startTime")
                home_obj = fixture.get("home") or {}
                away_obj = fixture.get("away") or {}
                home_name = home_obj.get("name") or ""
                away_name = away_obj.get("name") or ""
                if not start_time or not home_name or not away_name:
                    continue
                try:
                    if local_day(start_time) != target_day:
                        continue
                except (TypeError, ValueError):
                    continue

                home_id = home_obj.get("id")
                away_id = away_obj.get("id")
                home_rank = rankings.get(int(home_id)) if home_id else None
                away_rank = rankings.get(int(away_id)) if away_id else None
                ranked_player = bool(home_rank or away_rank)
                priority_player = (
                    _is_priority_tennis_player(home_name)
                    or _is_priority_tennis_player(away_name)
                )
                if not (ranked_player or priority_player):
                    continue

                fixture_id = fixture.get("id") or (normalize(home_name), normalize(away_name), start_time)
                if fixture_id in results:
                    continue
                league = fixture.get("league") or {}
                odds = odds_lookup.get((normalize(home_name), normalize(away_name)), {})
                surface = fixture.get("surface") or {}
                results[fixture_id] = {
                    "home_team": home_name,
                    "away_team": away_name,
                    "commence_time": start_time,
                    "league": {"title": league.get("name") or category.get("name") or "Теннис"},
                    "bookmakers": odds.get("bookmakers", []),
                    "_sportsapi_fixture_id": fixture.get("id"),
                    "_sportsapi_home_id": home_id,
                    "_sportsapi_away_id": away_id,
                    "_sportsapi_home_rank": home_rank,
                    "_sportsapi_away_rank": away_rank,
                    "_sportsapi_tour": tour,
                    "_sportsapi_surface": surface.get("name") if isinstance(surface, dict) else None,
                }

    return list(results.values())


def _form_string(side_data):
    if not isinstance(side_data, dict):
        return "нет данных"
    recent = side_data.get("lastFixtures") or []
    symbols = []
    for match in recent[-5:]:
        result = str(match.get("result") or "").lower()
        if result == "win":
            symbols.append("В")
        elif result == "loss":
            symbols.append("П")
        elif result == "draw":
            symbols.append("Н")
    return "–".join(symbols) if symbols else "нет данных"


def _player_surface_summary(player_id, surface_name=None):
    if not player_id:
        return ""
    year = datetime.now(KYIV).year
    rows = sports_api_get(
        f"/teams/{player_id}/year-statistics", {"year": year}
    ) or []
    if not rows:
        return ""

    selected = []
    if surface_name:
        wanted = normalize(surface_name)
        selected = [
            row for row in rows
            if normalize((row.get("surface") or {}).get("name", "")) == wanted
        ]
    if not selected:
        selected = rows

    bits = []
    for row in selected[:3]:
        surface = (row.get("surface") or {}).get("name") or "покрытие"
        matches = row.get("matches")
        wins = row.get("wins")
        if isinstance(matches, int) and matches > 0 and isinstance(wins, int):
            pct = round(100 * wins / matches)
            bits.append(f"{surface}: {wins}/{matches} побед ({pct}%)")
    return "; ".join(bits)


def tennis_match_analysis(event):
    fixture_id = event.get("_sportsapi_fixture_id")
    if not fixture_id:
        return "Аналитика SportsAPI недоступна для этого матча."

    form_data = sports_api_get(f"/fixtures/{fixture_id}/form") or {}
    home_form = _form_string(form_data.get("home"))
    away_form = _form_string(form_data.get("away"))

    h2h_data = sports_api_get(f"/fixtures/{fixture_id}/h2h")
    h2h_text = "личные встречи: нет подтверждённых данных"
    if isinstance(h2h_data, dict):
        home_wins = h2h_data.get("homeWins")
        away_wins = h2h_data.get("awayWins")
        if isinstance(home_wins, int) and isinstance(away_wins, int):
            h2h_text = f"личные встречи: {home_wins}–{away_wins}"

    surface = event.get("_sportsapi_surface")
    home_surface = _player_surface_summary(event.get("_sportsapi_home_id"), surface)
    away_surface = _player_surface_summary(event.get("_sportsapi_away_id"), surface)

    details = [f"Форма: {home_form} / {away_form}", h2h_text]
    if home_surface or away_surface:
        details.append(f"Покрытия: {home_surface or 'нет данных'} | {away_surface or 'нет данных'}")
    return "\n".join(details)


def tennis_sort_key(event):
    home_rank = event.get("_sportsapi_home_rank") or {}
    away_rank = event.get("_sportsapi_away_rank") or {}
    rank_values = [x.get("position") for x in (home_rank, away_rank) if x.get("position")]
    text = f"{event.get('home_team', '')} {event.get('away_team', '')}"
    priority = next((idx for idx, name in enumerate(TENNIS_PRIORITY)
                     if contains_name(text, [name])), 999)
    return (0 if priority < 999 else 1, priority, min(rank_values or [999]), event.get("commence_time", ""))



FOOTBALL_API_BASE = "https://v3.football.api-sports.io"


def football_api_get(endpoint, params=None):
    """Fetch one API-Football v3 resource. Missing/failed data never breaks the poster."""
    key = os.environ.get("FOOTBALL_API_KEY")
    if not key:
        print("FOOTBALL_API_KEY is missing; football enrichment is disabled.")
        return []
    try:
        response = requests.get(
            f"{FOOTBALL_API_BASE}/{endpoint.lstrip('/')}",
            params=params or {},
            headers={"x-apisports-key": key},
            timeout=35,
        )
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors") if isinstance(payload, dict) else None
        if errors:
            print(f"API-Football {endpoint} returned errors: {errors}")
            return []
        data = payload.get("response") if isinstance(payload, dict) else None
        return data if isinstance(data, list) else []
    except requests.RequestException as exc:
        print(f"API-Football request failed for {endpoint}: {exc}")
        return []
    except (ValueError, AttributeError) as exc:
        print(f"API-Football returned invalid JSON for {endpoint}: {exc}")
        return []


def _football_fixture_key(home, away):
    return tuple(sorted((normalize(home), normalize(away))))


def enrich_football_matches(target_day, soccer_events):
    """Attach verified form, prediction, absences and table data to matched fixtures.

    Daily budget is deliberately modest: one fixture list, one injuries list,
    up to 10 predictions and up to 4 standings requests.
    """
    if not soccer_events or not os.environ.get("FOOTBALL_API_KEY"):
        return

    fixtures = football_api_get(
        "fixtures", {"date": target_day.isoformat(), "timezone": "Europe/Kyiv"}
    )
    fixture_map = {}
    for fixture in fixtures:
        teams = fixture.get("teams") or {}
        home = (teams.get("home") or {}).get("name")
        away = (teams.get("away") or {}).get("name")
        if home and away:
            fixture_map[_football_fixture_key(home, away)] = fixture

    matched = []
    for event in soccer_events:
        key = _football_fixture_key(event.get("home_team", ""), event.get("away_team", ""))
        fixture = fixture_map.get(key)
        if fixture:
            event["_api_football_fixture"] = fixture
            matched.append(event)

    if not matched:
        print("API-Football: no exact team-pair matches found for today's selected fixtures.")
        return

    # One daily call for absences; the API labels confirmed absences separately
    # from questionable cases, so the message preserves that distinction.
    injuries = football_api_get(
        "injuries", {"date": target_day.isoformat(), "timezone": "Europe/Kyiv"}
    )
    injuries_by_fixture = {}
    for item in injuries:
        fixture_id = (item.get("fixture") or {}).get("id")
        if fixture_id:
            injuries_by_fixture.setdefault(fixture_id, []).append(item)
    for event in matched:
        fixture_id = (event.get("_api_football_fixture", {}).get("fixture") or {}).get("id")
        event["_api_football_injuries"] = injuries_by_fixture.get(fixture_id, [])

    # Predictions include API-Football's form/comparison data. Limit calls so
    # the free daily quota remains available for future runs.
    for event in matched[:5]:
        fixture_id = (event.get("_api_football_fixture", {}).get("fixture") or {}).get("id")
        if fixture_id:
            rows = football_api_get("predictions", {"fixture": fixture_id})
            event["_api_football_prediction"] = rows[0] if rows else None

    # Standings are useful only where the API returns a real league table.
    league_requests = []
    for event in matched:
        league = (event.get("_api_football_fixture", {}).get("league") or {})
        league_id, season = league.get("id"), league.get("season")
        if league_id and season and (league_id, season) not in league_requests:
            league_requests.append((league_id, season))
    standings_map = {}
    for league_id, season in league_requests[:4]:
        rows = football_api_get("standings", {"league": league_id, "season": season})
        for row in rows:
            league_data = row.get("league") or {}
            for group in league_data.get("standings") or []:
                for team_row in group:
                    team_id = (team_row.get("team") or {}).get("id")
                    if team_id:
                        standings_map[(league_id, team_id)] = team_row
    for event in matched:
        fixture = event.get("_api_football_fixture") or {}
        league = fixture.get("league") or {}
        teams = fixture.get("teams") or {}
        for side in ("home", "away"):
            team_id = (teams.get(side) or {}).get("id")
            event.setdefault("_api_football_standings", {})[side] = standings_map.get(
                (league.get("id"), team_id)
            )


def _api_form_text(value):
    value = str(value or "").upper()
    mapping = {"W": "В", "L": "П", "D": "Н"}
    result = "".join(mapping.get(ch, "") for ch in value if ch in mapping)
    return result or "нет данных"


def _market_percentages(event):
    prices = h2h_prices(event)
    home = prices.get(normalize(event.get("home_team", "")))
    away = prices.get(normalize(event.get("away_team", "")))
    draw = next((v for k, v in prices.items() if k in ("draw", "tie")), None)
    if not home or not away:
        return None
    implied = [1 / home, 1 / away]
    if draw:
        implied.insert(1, 1 / draw)
    total = sum(implied)
    return [round(value / total * 100) for value in implied]


def football_match_analysis(event):
    fixture = event.get("_api_football_fixture")
    if not fixture:
        return "API-Football: подтверждённая карточка матча не найдена."

    bits = []
    teams = fixture.get("teams") or {}
    home_obj, away_obj = teams.get("home") or {}, teams.get("away") or {}
    prediction = event.get("_api_football_prediction") or {}
    prediction_data = prediction.get("predictions") or {}
    percent = prediction_data.get("percent") or {}
    if any(percent.get(key) for key in ("home", "draw", "away")):
        bits.append(
            "оценка API: " + " / ".join(
                str(percent.get(key) or "—") for key in ("home", "draw", "away")
            ) + " (П1 / X / П2)"
        )

    prediction_teams = prediction.get("teams") or {}
    home_last = (prediction_teams.get("home") or {}).get("last_5") or {}
    away_last = (prediction_teams.get("away") or {}).get("last_5") or {}
    if home_last or away_last:
        bits.append(
            f"форма 5 матчей: {_api_form_text(home_last.get('form'))} / "
            f"{_api_form_text(away_last.get('form'))}"
        )

    standings = event.get("_api_football_standings") or {}
    table_bits = []
    for side, obj in (("home", home_obj), ("away", away_obj)):
        row = standings.get(side)
        if row:
            table_bits.append(
                f"{obj.get('name', side)}: {row.get('rank', '?')} место, "
                f"{row.get('points', '?')} очк."
            )
    if table_bits:
        bits.append("таблица: " + "; ".join(table_bits))

    absence_bits = []
    for item in event.get("_api_football_injuries") or []:
        player = item.get("player") or {}
        team = item.get("team") or {}
        player_name = player.get("name")
        if not player_name:
            continue
        kind = str(player.get("type") or "").strip()
        reason = str(player.get("reason") or "").strip()
        status = "под вопросом" if "question" in kind.lower() else "отсутствует"
        detail = f"{player_name} ({team.get('name') or 'команда'}: {status}"
        if reason:
            detail += f", {reason}"
        detail += ")"
        absence_bits.append(detail)
    if absence_bits:
        bits.append("кадры: " + "; ".join(absence_bits[:4]))
    else:
        bits.append("кадры: API не вернул записей об отсутствии; это не подтверждает, что их точно нет")

    market = _market_percentages(event)
    if market:
        labels = "П1 / X / П2" if len(market) == 3 else "П1 / П2"
        bits.append(f"рынок без маржи букмекеров (примерно): {' / '.join(str(value) + '%' for value in market)} ({labels})")

    advice = prediction_data.get("advice")
    if advice:
        bits.append(f"модель API: {advice}")
    if not bits:
        return "API-Football найден, но подробная статистика для матча не вернулась."
    return "\n".join(bits)



def _decimal_odds(event, tennis=False):
    prices = h2h_prices(event)
    home = prices.get(normalize(event.get("home_team", "")))
    away = prices.get(normalize(event.get("away_team", "")))

    if not home or not away:
        return None

    if tennis:
        return [(home, "home"), (away, "away")]

    draw = next((v for k, v in prices.items() if k in ("draw", "tie")), None)
    result = [(home, "home")]
    if draw:
        result.append((draw, "draw"))
    result.append((away, "away"))
    return result


def _football_prediction_probs(event):
    prediction = event.get("_api_football_prediction") or {}
    percent = (prediction.get("predictions") or {}).get("percent") or {}
    result = {}

    for key in ("home", "draw", "away"):
        raw = str(percent.get(key) or "").replace("%", "").strip()
        try:
            result[key] = float(raw)
        except (TypeError, ValueError):
            pass

    return result


def _favorite_candidates(events, tennis=False):
    candidates = []

    for event in events:
        odds = _decimal_odds(event, tennis=tennis)
        if not odds:
            continue

        odds = sorted(odds, key=lambda item: item[0])
        favorite_price, favorite_side = odds[0]

        if favorite_side == "draw" or favorite_price >= 2.00:
            continue

        if tennis:
            home_rank = (event.get("_sportsapi_home_rank") or {}).get("position")
            away_rank = (event.get("_sportsapi_away_rank") or {}).get("position")

            rank_gap = 0
            if home_rank and away_rank:
                rank_gap = abs(home_rank - away_rank)

            confidence = (1 / favorite_price) * 100
            if rank_gap:
                confidence += min(rank_gap, 40) * 0.20

            disagreement = False

        else:
            probs = _football_prediction_probs(event)
            confidence = (1 / favorite_price) * 100

            predicted = probs.get(favorite_side)
            disagreement = predicted is not None and predicted < 45

            if predicted is not None:
                confidence = 0.55 * confidence + 0.45 * predicted

        candidates.append({
            "event": event,
            "tennis": tennis,
            "price": favorite_price,
            "side": favorite_side,
            "confidence": confidence,
            "disagreement": disagreement,
        })

    return candidates


def _candidate_names(candidate):
    event = candidate["event"]

    if candidate["tennis"]:
        return (
            display_tennis_player(event.get("home_team", "?")),
            display_tennis_player(event.get("away_team", "?")),
        )

    return (
        display_team(event.get("home_team", "?")),
        display_team(event.get("away_team", "?")),
    )


def build_daily_analysis(soccer, tennis):
    football = _favorite_candidates(soccer, tennis=False)
    tennis_picks = _favorite_candidates(tennis, tennis=True)
    all_candidates = football + tennis_picks

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "🧠 **BEZUMNIY HAALAND DUMAYET...**",
        "",
    ]

    if not all_candidates:
        lines += [
            "«Сегодня источники не дали достаточно надёжных коэффициентов, чтобы выделить фаворитов.",
            "Не буду изображать ясновидящего: лучше пропустить сомнительный вариант, чем продавать вам воздух».",
            "",
        ]
        return lines

    strong = sorted(
        [item for item in all_candidates if not item["disagreement"]],
        key=lambda item: item["confidence"],
        reverse=True,
    )[:2]

    risky = [item for item in all_candidates if item["disagreement"]]

    if not risky:
        risky = [
            item for item in all_candidates
            if 1.55 <= item["price"] < 2.00
        ]

    risky = sorted(risky, key=lambda item: item["price"])[:2]

    lines.append(
        "«Так, мужики, Холланд изучил сегодняшнюю движуху. "
        "Вот что тут интереснее всего.»"
    )
    lines.append("")

    if strong:
        lines.append("🧱 **Самые убедительные фавориты**")

        for item in strong:
            home, away = _candidate_names(item)
            favourite = home if item["side"] == "home" else away
            opponent = away if item["side"] == "home" else home
            sport = "теннис" if item["tennis"] else "футбол"

            lines.append(
                f"• {favourite} против {opponent} — выглядит сильнее "
                f"(коэффициент около {item['price']:.2f}; {sport})."
            )

        lines.append("")

    if risky:
        lines.append("⚠️ **Где фаворит может подвести**")

        for item in risky:
            home, away = _candidate_names(item)
            favourite = home if item["side"] == "home" else away
            opponent = away if item["side"] == "home" else home

            reason = (
                "прогноз API не подтверждает преимущество"
                if item["disagreement"]
                else "матч выглядит достаточно близким — лёгкой прогулки не жду"
            )

            lines.append(
                f"• {favourite} против {opponent} — {reason}."
            )

        lines.append("")

    else:
        lines.append("⚠️ **Опасные места**")
        lines.append(
            "«Явного конфликта между рынком и моделью не вижу, "
            "но это не делает фаворитов гарантией»."
        )
        lines.append("")

    lines.append(
        "«Мой вердикт: выбираем на эмоциях и кэфах, так как вы - ЛУДОМАНЫ. "
        "Бетон в спорте есть — даже самый очевидный андердог умеет дать говна»."
    )
    lines.append("")

    lines.append(
        "*Это краткая оценка по доступным данным API, "
        "а не гарантия исхода. ладно я наебал - это пиздец бетон. тот кто создал бота ебаный гений (миша)*"
    )

    return lines


def main():
    now = datetime.now(KYIV)
    manual_run = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    # Автоматический запуск публикует только около полуночи по Киеву.
    if not manual_run and now.hour != 0:
        print(f"Not Kyiv midnight ({now.isoformat()}); skipping.")
        return

    today = now.date()

    soccer = [
        event for event in get_fixtures("soccer")
        if event.get("commence_time")
        and local_day(event["commence_time"]) == today
        and is_soccer_relevant(event)
    ]
    odds_tennis = get_fixtures("tennis")
    tennis = get_sportsapi_tennis_fixtures(today, odds_tennis)
    if not tennis:
        # Safe fallback: OddsLink still supplies matches for the eight manually prioritised players.
        tennis = [
            event for event in odds_tennis
            if event.get("commence_time")
            and local_day(event["commence_time"]) == today
            and contains_name(
                f"{event.get('home_team', '')} {event.get('away_team', '')}",
                TENNIS_PRIORITY,
            )
        ]
        print("SportsAPI returned no matching tennis fixtures; using OddsLink priority-player fallback.")

    soccer.sort(key=soccer_sort_key)
    tennis.sort(key=tennis_sort_key)
    enrich_football_matches(today, soccer)

    lines = [
        "🕒 **Время указано по Киеву.**",
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
                lines.append(colored_price_text(event))
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
            home_rank = event.get("_sportsapi_home_rank") or {}
            away_rank = event.get("_sportsapi_away_rank") or {}
            rank_bits = []
            if home_rank.get("position"):
                rank_bits.append(f"{home_rank.get('tour')} #{home_rank['position']}")
            if away_rank.get("position"):
                rank_bits.append(f"{away_rank.get('tour')} #{away_rank['position']}")
            tournament_line = (
                f"**{display_competition(tournament)}** · ` {event.get('_sportsapi_tour', '')} "
                f"{format_time(event['commence_time'])}`"
            )
            if rank_bits:
                tournament_line += " · " + " / ".join(rank_bits)
            lines.append(tournament_line)
            lines.append(f"{home} — {away}")
            lines.append(colored_price_text(event, tennis=True))
            analysis_text = tennis_match_analysis(event)
            lines.append(f"_{analysis_text}_")
            lines.append("")
    else:
        lines.append("Матчи выбранных игроков на сегодня не найдены.")
        lines.append("")

    lines += build_daily_analysis(soccer, tennis)

    discord_send("\n".join(lines), today.strftime("%d.%m.%Y"))
    print(
        f"Published: {len(soccer)} football fixtures, "
        f"{len(tennis)} tennis fixtures."
    )


if __name__ == "__main__":
    main()
