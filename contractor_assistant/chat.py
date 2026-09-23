"""Разбор коротких русскоязычных сообщений и диалоговый подбор из каталога."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable

from src.recommendation import Provider, RecommendationRequest, recommend


DATE_MIN = date(2026, 9, 23)
DATE_MAX = date(2026, 12, 31)
REQUIRED = ("city", "event_date", "event_format", "category", "budget_kzt")
MONTHS = {
    "января": 1, "январь": 1, "февраля": 2, "февраль": 2, "марта": 3, "март": 3,
    "апреля": 4, "апрель": 4, "мая": 5, "май": 5, "июня": 6, "июнь": 6,
    "июля": 7, "июль": 7, "августа": 8, "август": 8, "сентября": 9, "сентябрь": 9,
    "октября": 10, "октябрь": 10, "ноября": 11, "ноябрь": 11, "декабря": 12, "декабрь": 12,
}
MONTH_NAMES = ("января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря")


def _norm(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def _find_choice(text: str, choices: Iterable[str],
                 aliases: dict[str, tuple[str, ...]] | None = None) -> str | None:
    value = _norm(text)
    hits: list[tuple[int, str]] = []
    for choice in choices:
        terms = (choice, *((aliases or {}).get(choice, ())))
        for term in terms:
            term = _norm(term)
            if term and term in value:
                hits.append((len(term), choice))
    return max(hits)[1] if hits else None


def _parse_date(text: str) -> str | None:
    value = _norm(text)
    match = re.search(r"(?<!\d)(20\d{2})-(\d{1,2})-(\d{1,2})(?!\d)", value)
    if match:
        year, month, day = map(int, match.groups())
    else:
        match = re.search(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](20\d{2})(?!\d)", value)
        if match:
            day, month, year = map(int, match.groups())
        else:
            month_pattern = "|".join(sorted(MONTHS, key=len, reverse=True))
            match = re.search(rf"(?<!\d)(\d{{1,2}})\s+({month_pattern})(?:\s+(20\d{{2}}))?", value)
            if not match:
                return None
            day = int(match.group(1))
            month = MONTHS[match.group(2)]
            year = int(match.group(3) or 2026)
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _parse_budget(text: str) -> int | None:
    pattern = re.compile(
        r"(?<!\w)([+-]?\d{1,3}(?:[ \u00a0]\d{3})+|[+-]?\d{1,9}(?:[.,]\d+)?)"
        r"\s*(млн(?:ов)?|миллион(?:а|ов)?|тыс(?:яч[а-я]*)?\.?|тысяч[а-я]*|к|k|₸|тг|тенге)?",
        re.IGNORECASE,
    )
    candidates: list[tuple[int, int]] = []
    value = _norm(text)
    for match in pattern.finditer(value):
        raw, unit = match.groups()
        unit = (unit or "").strip().rstrip(".")
        before = value[max(0, match.start() - 30):match.start()]
        has_budget = bool(re.search(r"(бюджет\w*|лимит)\s*(?:до\s*)?$", before))
        has_ceiling = bool(re.search(r"до\s*$", before))
        if not (unit or has_budget or has_ceiling):
            continue
        amount = float(raw.replace(" ", "").replace("\u00a0", "").replace(",", "."))
        if unit.startswith(("млн", "миллион")):
            amount *= 1_000_000
        elif unit.startswith("тыс") or unit in {"к", "k"}:
            amount *= 1_000
        score = (4 if has_budget else 0) + (3 if unit else 0) + (1 if has_ceiling else 0)
        candidates.append((score, int(amount)))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _parse_duration(text: str) -> float | None:
    match = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:ч\.?|час(?:а|ов)?)\b", _norm(text))
    return float(match.group(1).replace(",", ".")) if match else None


def _aliases(providers: list[Provider]) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]],
                                                   dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    city_aliases = {"Алматы": ("алмате",), "Астана": ("астане", "астану"),
                    "Зарубежье": ("за рубежом", "за границей")}
    category_aliases = {
        "Ведущий": ("ведущ",), "Ведущий церемонии": ("ведущ церемон",),
        "Банкетный зал": ("банкетн зал",), "Загородная площадка": ("загородн площадк",),
        "Подарки и сувениры": ("подарк", "сувенир"), "Фото и видеобудки": ("фотобуд", "видеобуд"),
        "Лайв-бэнд": ("лайв бэнд",), "Национальный ансамбль": ("национальн ансамбл",),
        "Танцевальный коллектив": ("танцевальн коллектив",), "Шоу-программа": ("шоу программ",),
    }
    format_aliases = {
        "свадьба": ("свадьб",), "корпоратив": ("корпоратив",), "конференция": ("конференц",),
        "юбилей": ("юбиле",), "день рождения": ("дня рождения", "днем рождения", "день рожд", "дн рождения"),
    }
    language_aliases = {
        "русский": ("русском", "русски", "русскоязыч"),
        "казахский": ("казахском", "казахски", "казахскоязыч"),
        "английский": ("английском", "английски", "англоязыч"),
    }
    return city_aliases, category_aliases, format_aliases, language_aliases


def _clean_context(providers: list[Provider], context: dict[str, Any] | None) -> dict[str, Any]:
    state = {key: None for key in (*REQUIRED, "duration_hours", "language")}
    if not isinstance(context, dict):
        return state
    state.update({key: context.get(key) for key in state if key in context})
    cities = {provider.city for provider in providers}
    categories = {value for provider in providers for value in provider.categories}
    formats = {value for provider in providers for value in provider.event_formats}
    languages = {value for provider in providers for value in provider.languages}
    city_aliases, category_aliases, format_aliases, language_aliases = _aliases(providers)
    for key, options, aliases in (
        ("city", cities, city_aliases), ("category", categories, category_aliases),
        ("event_format", formats, format_aliases), ("language", languages, language_aliases),
    ):
        value = state.get(key)
        state[key] = _find_choice(value, options, aliases) if isinstance(value, str) else None
    raw_date = state.get("event_date")
    state["event_date"] = _parse_date(raw_date) if isinstance(raw_date, str) else None
    budget = state.get("budget_kzt")
    state["budget_kzt"] = budget if type(budget) is int and budget > 0 else None
    duration = state.get("duration_hours")
    state["duration_hours"] = duration if type(duration) in (int, float) and duration > 0 else None
    return state


def _display_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {MONTH_NAMES[parsed.month - 1]} {parsed.year}"


def _missing_reply(state: dict[str, Any]) -> str:
    known = []
    if state.get("city"):
        known.append(state["city"])
    if state.get("event_date"):
        known.append(_display_date(state["event_date"]))
    if state.get("event_format"):
        known.append(state["event_format"])
    prefix = "Понял: " + ", ".join(known) + ". " if known else ""
    missing = [field for field in REQUIRED if state.get(field) is None]
    if missing == ["category", "budget_kzt"]:
        return prefix + (
            "Какую категорию подрядчика ищем — например, ведущего, фотографа или флориста — и какой бюджет в ₸? "
            "После этого покажу до трёх подходящих вариантов."
        )
    labels = {"city": "город", "event_date": "дату", "event_format": "формат события",
              "category": "категорию подрядчика", "budget_kzt": "бюджет в тенге"}
    ask = ", ".join(labels[field] for field in missing)
    return prefix + f"Чтобы подобрать подрядчиков, уточните, пожалуйста: {ask}."


def assistant_turn(providers: Iterable[Provider], message: str,
                   context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract slots, ask for missing details, and call the canonical matcher when valid."""
    provider_list = list(providers)
    state = _clean_context(provider_list, context)
    text = message.strip() if isinstance(message, str) else ""
    cities = {provider.city for provider in provider_list}
    categories = {item for provider in provider_list for item in provider.categories}
    formats = {item for provider in provider_list for item in provider.event_formats}
    languages = {item for provider in provider_list for item in provider.languages}
    city_aliases, category_aliases, format_aliases, language_aliases = _aliases(provider_list)
    extracted = {
        "city": _find_choice(text, cities, city_aliases),
        "event_date": _parse_date(text),
        "event_format": _find_choice(text, formats, format_aliases),
        "category": _find_choice(text, categories, category_aliases),
        "budget_kzt": _parse_budget(text),
        "duration_hours": _parse_duration(text),
        "language": _find_choice(text, languages, language_aliases),
    }
    invalid_budget = extracted["budget_kzt"] is not None and extracted["budget_kzt"] <= 0
    for key, value in extracted.items():
        if key == "budget_kzt" and value is not None and value <= 0:
            state[key] = None
        elif value is not None:
            state[key] = value

    if not text and all(state.get(field) is None for field in REQUIRED):
        return {"reply": "Напишите город, дату и повод мероприятия. Я уточню остальное и подберу подрядчиков.",
                "context": state, "complete": False, "recommendation": None}

    event_date = state.get("event_date")
    if event_date:
        day = date.fromisoformat(event_date)
        if not DATE_MIN <= day <= DATE_MAX:
            state["event_date"] = None
            return {"reply": "Календарь доступности в каталоге покрывает даты с 23.09.2026 по 31.12.2026. "
                            "Назовите дату в этом диапазоне.",
                    "context": state, "complete": False, "recommendation": None}
    if state.get("budget_kzt") is None and re.search(r"(бюджет|лимит)", _norm(text)) and re.search(r"\b0\b", text):
        return {"reply": "Бюджет должен быть больше нуля. Какую максимальную сумму в тенге заложить?",
                "context": state, "complete": False, "recommendation": None}

    if any(state.get(field) is None for field in REQUIRED):
        return {"reply": _missing_reply(state), "context": state, "complete": False, "recommendation": None}

    request = RecommendationRequest(
        city=state["city"], event_date=state["event_date"], event_format=state["event_format"],
        category=state["category"], budget_kzt=state["budget_kzt"],
        duration_hours=state.get("duration_hours"), language=state.get("language"),
    )
    try:
        result = recommend(provider_list, request)
    except (TypeError, ValueError):
        state["event_date"] = None
        return {"reply": "Не смог проверить дату или бюджет. Уточните дату в диапазоне 23.09.2026–31.12.2026 "
                        "и положительный бюджет в тенге.",
                "context": state, "complete": False, "recommendation": None}

    reply = result["message"]
    if result["outcome"] == "no_match":
        reply += " Попробуйте изменить дату или бюджет."
    elif result["outcome"] == "category_absent":
        reply += " Можно выбрать другую категорию или город."
    return {"reply": reply, "context": state, "complete": True, "recommendation": result}
