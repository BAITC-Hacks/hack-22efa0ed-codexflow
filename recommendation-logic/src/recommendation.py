"""Deterministic contractor recommendation engine for the hackathon dataset."""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
from typing import Iterable, Literal


Outcome = Literal["matches", "category_absent", "no_match"]
CALENDAR_START = "2026-09-23"
CALENDAR_END = "2026-12-31"
REASON_ORDER = ("busy", "budget", "format", "duration", "language")
MAX_TEXT_LENGTH = 128
MAX_BUDGET_KZT = 1_000_000_000
MAX_DURATION_HOURS = 168


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    categories: tuple[str, ...]
    city: str
    price_from_kzt: int
    event_formats: tuple[str, ...]
    languages: tuple[str, ...]
    max_hours: int | None
    busy_dates: frozenset[str]
    description: str
    synthetic: bool
    city_imputed: bool = False
    price_imputed: bool = False


@dataclass(frozen=True)
class RecommendationRequest:
    city: str
    event_date: str
    event_format: str
    category: str
    budget_kzt: int
    duration_hours: float | int | None = None
    language: str | None = None


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split("|") if item.strip())


def load_providers(csv_path: str | Path) -> list[Provider]:
    """Load the supplied CSV without changing or inventing its source data."""
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return [
            Provider(
                id=row["id"],
                name=row["anon_name"],
                categories=_split(row["categories"]),
                city=row["city"],
                price_from_kzt=int(row["price_from_kzt"]),
                event_formats=_split(row["event_formats"]),
                languages=_split(row["languages"]),
                max_hours=int(row["max_hours"]) if row["max_hours"].strip() else None,
                busy_dates=frozenset(_split(row["busy_dates"])),
                description=row["description"].strip(),
                synthetic=row["synthetic"].strip().lower() == "true",
                city_imputed=row["city_imputed"].strip().lower() == "true",
                price_imputed=row["price_imputed"].strip().lower() == "true",
            )
            for row in rows
        ]


def validate_request_field(field: str, value):
    """Shared input policy used before API coercion and by direct callers."""
    if field in ("city", "event_format", "category", "language"):
        if field == "language" and value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field}: нужна непустая строка.")
        if len(value) > MAX_TEXT_LENGTH:
            raise ValueError(f"{field}: не более {MAX_TEXT_LENGTH} символов.")
        if any(unicodedata.category(ch) in ("Cs", "Cf") or
               (unicodedata.category(ch) == "Cc" and ch not in "\t\r\n") for ch in value):
            raise ValueError(f"{field}: недопустимые управляющие символы или Unicode.")
        return value.strip()
    if field == "event_date":
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Дата должна быть строкой в формате YYYY-MM-DD.")
        try:
            date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Указана несуществующая дата.") from error
        if not CALENDAR_START <= value <= CALENDAR_END:
            raise ValueError(f"Данные о занятости доступны только с {CALENDAR_START} по {CALENDAR_END}.")
    elif field == "budget_kzt":
        if type(value) is not int or not 0 < value <= MAX_BUDGET_KZT:
            raise ValueError(f"Бюджет должен быть целым числом от 1 до {MAX_BUDGET_KZT} тенге.")
    elif field == "duration_hours":
        if value is None:
            return None
        if type(value) not in (int, float) or value <= 0:
            raise ValueError("Длительность должна быть положительным числом часов.")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Длительность должна быть конечным числом часов.")
        if value > MAX_DURATION_HOURS:
            raise ValueError(f"Длительность не должна превышать {MAX_DURATION_HOURS} часов.")
    return value


def normalize_request(request: RecommendationRequest) -> RecommendationRequest:
    return replace(request, **{
        field: validate_request_field(field, value)
        for field, value in asdict(request).items()
    })


def _text_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _canonical_request(request: RecommendationRequest, providers: list[Provider]) -> RecommendationRequest:
    """Match case-insensitively while keeping catalog spelling in explanations."""
    values = {
        "city": {p.city for p in providers},
        "category": {v for p in providers for v in p.categories},
        "event_format": {v for p in providers for v in p.event_formats},
        "language": {v for p in providers for v in p.languages},
    }
    updates = {}
    for field, options in values.items():
        value = getattr(request, field)
        if value is not None:
            mapping = {_text_key(option): option for option in sorted(options, reverse=True)}
            updates[field] = mapping.get(_text_key(value), _text_key(value))
    return replace(request, **updates)


def _description_excerpt(description: str, limit: int = 160) -> str:
    text = " ".join(description.split())
    # Extract a complete experience fact even from a paragraph without punctuation.
    experience = re.search(r"\bОпыт\s+[^.!?;]{0,60}?\b\d+\s+(?:лет|года?|год)\b", text, re.IGNORECASE)
    if experience and len(experience.group()) <= limit:
        return experience.group()
    # Never cut a sentence or a number halfway through. If no short statement
    # exists, use structured profile facts in the card instead of a broken quote.
    for sentence in re.split(r"[.!?](?:\s+|$)", text):
        sentence = sentence.strip()
        if len(sentence.split()) >= 3 and len(sentence) <= limit:
            return sentence
    return ""


def _rejection_reasons(provider: Provider, request: RecommendationRequest) -> set[str]:
    reasons: set[str] = set()
    if request.event_date in provider.busy_dates:
        reasons.add("busy")
    if provider.price_from_kzt > request.budget_kzt:
        reasons.add("budget")
    if _text_key(request.event_format) not in {_text_key(v) for v in provider.event_formats}:
        reasons.add("format")
    if request.duration_hours is not None and provider.max_hours is not None:
        if provider.max_hours < request.duration_hours:
            reasons.add("duration")
    if request.language is not None and _text_key(request.language) not in {_text_key(v) for v in provider.languages}:
        reasons.add("language")
    return reasons


def description_evidence(description: str, limit: int = 180) -> list[str]:
    """Complete source facts, excluding greetings, generic praise and unsafe markup."""
    text = " ".join(description.split())
    fragments = re.split(r"[.!?](?:\s+|$)", text)
    experience = re.search(r"\bОпыт\s+[^.!?;]{0,60}?\b\d+\s+(?:лет|года?|год)\b", text, re.IGNORECASE)
    if experience:
        fragments.insert(0, experience.group())
    rejected = (r"топ[-\s]?\d|лучш|востребован|идеальн|безупреч|гарантир|0 развод|меня зовут|всем привет|всегда ваш|отличный выбор"
                r"|незабываем|профессионалы своего дела|любовь к музыке|сверкаем|^мы\s*[—–-]")
    result = []
    for fragment in fragments:
        fragment = fragment.strip()
        if (3 <= len(fragment.split()) and len(fragment) <= limit
                and not re.search(rejected, fragment, re.IGNORECASE)
                and not re.search(r"[<>.!?]", fragment) and fragment not in result):
            result.append(fragment)
    return result


def _relevant_evidence(provider: Provider, request: RecommendationRequest) -> str:
    candidates = description_evidence(provider.description)
    if not candidates:
        return ""
    format_stems = {"свадьба": ("свад", "невест", "молодож"), "корпоратив": ("корпоратив", "бизнес", "команд", "тимбилдинг"),
                    "конференция": ("конференц", "форум", "презентац"), "той": ("той", "традиц"),
                    "юбилей": ("юбил",), "день рождения": ("день рождения",)}
    concrete = ("опыт", "лет", "заказ", "сезонн", "палитр", "букет", "казахск", "английск", "русск",
                "репортаж", "документаль", "позирован", "панорам", "гостей", "кейтеринг", "парковк",
                "террас", "кухн", "европейск", "традици", "телевиден", "сценари", "оборудован",
                "вокалист", "квартет", "барабанщик", "гитарист", "перкуссионист", "брасс", "саксофон")
    def score(text):
        key = text.casefold()
        return (sum(3 for stem in format_stems.get(request.event_format, ()) if stem in key)
                + sum(2 for stem in concrete if stem in key) + (4 if re.search(r"\d", key) else 0))
    # Stable tie-break by source position, never by random wording or model output.
    return max(candidates, key=score)


def _evidence_heading(evidence: str) -> str:
    """Editorial framing only: the quoted fact remains unchanged and attributed."""
    text = evidence.casefold()
    if 'состав' in text and any(word in text for word in ('вокалист', 'музыкант', 'квартет')):
        return 'Музыкальный состав'
    if 'палитр' in text:
        return 'Оформление под вашу палитру'
    if 'опыт' in text and 'свад' in text:
        return 'Опыт именно в свадьбах'
    if 'язык' in text:
        return 'Языки общения с гостями'
    if 'стиль' in text or 'подача' in text:
        return 'Стиль и подача'
    if 'заказ' in text and re.search(r'\d', text):
        return 'Практика в цифрах'
    if any(stem in text for stem in ('панорам', 'террас', 'интерьер')):
        return 'Атмосфера площадки'
    if any(stem in text for stem in ('репортаж', 'позирован', 'съёмк', 'съемк')):
        return 'Взгляд на ваше событие'
    if 'сценари' in text:
        return 'Подход к сценарию'
    return 'Деталь, на которую стоит обратить внимание'


def _card(provider: Provider, request: RecommendationRequest, *, description_signal: str | None = None) -> dict:
    if description_signal is None:
        description_signal = _relevant_evidence(provider, request)
    if description_signal:
        first_sentence = f"{_evidence_heading(description_signal)} — в профиле: «{description_signal}»."
    else:
        first_sentence = f"В профиле указаны языки: {', '.join(provider.languages)}"
        if provider.max_hours is not None:
            first_sentence += f"; время на площадке — до {provider.max_hours} ч"
        first_sentence += "; подробностей о стиле работы в каталоге недостаточно."

    conditions = f"Для формата «{request.event_format}» в городе «{provider.city}» дата {request.event_date} свободна по календарю"
    if request.language:
        language_forms = {"русский": "русском", "казахский": "казахском", "английский": "английском"}
        language = language_forms.get(_text_key(request.language))
        conditions += f", работает на {language} языке" if language else f", язык работы — {request.language}"
    details = [conditions]
    money = lambda value: f"{value:,}".replace(",", " ")
    gap = request.budget_kzt - provider.price_from_kzt
    price = f"цена от {money(provider.price_from_kzt)} ₸"
    price += f" — на {money(gap)} ₸ ниже лимита {money(request.budget_kzt)} ₸" if gap else " совпадает с вашим лимитом"
    details.append(price)
    if request.duration_hours is not None:
        hours = str(request.duration_hours).removesuffix(".0").replace(".", ",")
        if provider.max_hours is not None:
            details.append(f"лимит {provider.max_hours} ч покрывает запрос на {hours} ч")
        else:
            details.append("услуга не привязана к часам присутствия, сроки выполнения нужно согласовать")
    details.append("итоговую стоимость нужно уточнить")
    return {
        "id": provider.id,
        "name": provider.name,
        "categories": list(provider.categories),
        "city": provider.city,
        "price_from_kzt": provider.price_from_kzt,
        "synthetic": provider.synthetic,
        "city_imputed": provider.city_imputed,
        "price_imputed": provider.price_imputed,
        "explanation": first_sentence + " " + "; ".join(details) + ".",
    }


def explanation_with_evidence(provider: Provider, request: RecommendationRequest, evidence: str) -> str:
    """Render a caller-verified source excerpt; hard facts still come from the engine."""
    canonical = _canonical_request(normalize_request(request), [provider])
    if evidence not in description_evidence(provider.description):
        evidence = _relevant_evidence(provider, canonical)
    return _card(provider, canonical, description_signal=evidence)["explanation"]


def _reason_sentence(counts: Counter[str]) -> str:
    labels = {
        "busy": "заняты на выбранную дату",
        "budget": "не укладываются в бюджет",
        "format": "не берут этот формат",
        "duration": "не подходят по длительности",
        "language": "не работают на выбранном языке",
    }
    parts = [f"{counts[key]} {labels[key]}" for key in REASON_ORDER if counts[key]]
    return "; ".join(parts) + "." if parts else ""


def _profile_count(count: int) -> str:
    suffix = "профилей" if 11 <= count % 100 <= 14 else (
        "профиль" if count % 10 == 1 else "профиля" if count % 10 in (2, 3, 4) else "профилей"
    )
    return f"{count} {suffix}"


def _no_match_message(rejections: list[tuple[Provider, set[str]]], request: RecommendationRequest,
                      counts: Counter[str]) -> str:
    messages = []
    for reason in REASON_ORDER:
        group = [p for p, reasons in rejections if reasons == {reason}]
        if not group:
            continue
        count = len(group)
        singular = count % 10 == 1 and count % 100 != 11
        intro = f"По остальным условиям {'подходит' if singular else 'подходят'} {_profile_count(count)}, но "
        if reason == "busy":
            detail = f"{'он занят' if singular else 'все они заняты'} на {request.event_date}"
        elif reason == "budget":
            minimum = f"{min(p.price_from_kzt for p in group):,}".replace(",", " ")
            budget = f"{request.budget_kzt:,}".replace(",", " ")
            detail = f"цена от {minimum} ₸ выше бюджета {budget} ₸"
        elif reason == "format":
            detail = f"{'он не берёт' if singular else 'они не берут'} формат «{request.event_format}»"
        elif reason == "duration":
            detail = "доступная длительность меньше запрошенной"
        else:
            detail = f"язык «{request.language}» не указан в профиле" if singular else f"язык «{request.language}» не указан в профилях"
        messages.append(intro + detail + ".")
    if messages:
        advice = []
        if any(reasons == {"busy"} for _, reasons in rejections):
            advice.append("проверить другую дату")
        if any(reasons == {"budget"} for _, reasons in rejections):
            advice.append("увеличить бюджет до указанной стартовой цены")
        if advice:
            messages.append("Можно " + " или ".join(advice) + "; после изменения условий нужен новый подбор.")
        return " ".join(messages)
    return (f"В выбранном городе найдено профилей этой категории: {len(rejections)}, "
            f"но каждый не проходит несколько условий. Причины могут пересекаться: {_reason_sentence(counts)}")


def recommend(
    providers: Iterable[Provider], request: RecommendationRequest
) -> dict:
    """Return one of the three user-visible outcomes required by the brief."""
    request = normalize_request(request)
    providers = list(providers)
    request = _canonical_request(request, providers)
    scoped = [
        provider
        for provider in providers
        if _text_key(provider.city) == _text_key(request.city)
        and _text_key(request.category) in {_text_key(v) for v in provider.categories}
    ]
    if not scoped:
        return {
            "outcome": "category_absent",
            "cards": [],
            "message": f"В городе «{request.city}» нет подрядчиков категории «{request.category}».",
            "stats": {"catalog_candidates": 0, "eligible": 0, "rejected": {}},
        }

    rejected: Counter[str] = Counter()
    eligible: list[Provider] = []
    rejections: list[tuple[Provider, set[str]]] = []
    for provider in scoped:
        reasons = _rejection_reasons(provider, request)
        if reasons:
            rejections.append((provider, reasons))
            rejected.update(key for key in REASON_ORDER if key in reasons)
        else:
            eligible.append(provider)

    if not eligible:
        return {
            "outcome": "no_match",
            "cards": [],
            "message": _no_match_message(rejections, request, rejected),
            "stats": {"catalog_candidates": len(scoped), "eligible": 0, "rejected": dict(rejected)},
        }

    # Lower starting price is preferable after every hard requirement is met.
    # ID is the permanent tie-breaker: the same input always gives the same order.
    ranked = sorted(eligible, key=lambda provider: (provider.price_from_kzt, provider.id))
    cards = [_card(provider, request) for provider in ranked[:3]]
    message = f"Подобрано {len(cards)} из {len(eligible)} подходящих подрядчиков."
    if len(cards) > 1:
        message += " Порядок — по возрастанию цены «от», а не по оценке качества; при равной цене — по ID."
    otherwise_busy = sum(reasons == {"busy"} for _, reasons in rejections)
    if otherwise_busy:
        message += f" Ещё {_profile_count(otherwise_busy)} не показано из-за занятости на {request.event_date}; остальные условия выполнены."
    if len(eligible) < 3:
        rejected_message = _reason_sentence(rejected)
        if rejected_message:
            message += f" Меньше трёх, потому что {rejected_message}"
        else:
            message += " Меньше трёх, потому что в этой категории всего столько доступных профилей."
    # Never invent distinctions merely to satisfy an explanation-uniqueness test.
    masked = []
    for card in cards:
        text = card["explanation"]
        for candidate in cards:
            text = re.sub(re.escape(candidate["name"]), "[имя]", text, flags=re.IGNORECASE)
        masked.append(text)
    if len(set(masked)) < len(masked):
        message += " У части карточек совпадают описанные условия и особенности: данных каталога недостаточно, чтобы обоснованно различить их."

    return {
        "outcome": "matches",
        "cards": cards,
        "message": message,
        "stats": {
            "catalog_candidates": len(scoped),
            "eligible": len(eligible),
            "rejected": dict(rejected),
        },
    }


def serialize_provider(provider: Provider) -> dict:
    """Useful later for an API endpoint without exposing implementation details."""
    data = asdict(provider)
    data["categories"] = list(provider.categories)
    data["event_formats"] = list(provider.event_formats)
    data["languages"] = list(provider.languages)
    data["busy_dates"] = sorted(provider.busy_dates)
    return data
