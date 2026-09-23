"""Deterministic contractor recommendation engine for the hackathon dataset."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
from typing import Iterable, Literal


Outcome = Literal["matches", "category_absent", "no_match"]
CALENDAR_START = "2026-09-23"
CALENDAR_END = "2026-12-31"
REASON_ORDER = ("busy", "budget", "format", "duration", "language")


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
        if type(value) is not int or value <= 0:
            raise ValueError("Бюджет должен быть положительным целым числом в тенге.")
    elif field == "duration_hours":
        if value is None:
            return None
        if type(value) not in (int, float) or value <= 0:
            raise ValueError("Длительность должна быть положительным числом часов.")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Длительность должна быть конечным числом часов.")
    return value


def normalize_request(request: RecommendationRequest) -> RecommendationRequest:
    return replace(request, **{
        field: validate_request_field(field, value)
        for field, value in asdict(request).items()
    })


def _description_excerpt(description: str, limit: int = 110) -> str:
    signal = " ".join(description.split(".", 1)[0].split())
    if len(signal) <= limit:
        return signal
    # A displayed ellipsis makes the quotation's truncation explicit.
    words = signal[:limit + 1].rsplit(" ", 1)
    return (words[0].rstrip(" ,;:") + "…") if len(words) > 1 else ""


def _rejection_reasons(provider: Provider, request: RecommendationRequest) -> set[str]:
    reasons: set[str] = set()
    if request.event_date in provider.busy_dates:
        reasons.add("busy")
    if provider.price_from_kzt > request.budget_kzt:
        reasons.add("budget")
    if request.event_format not in provider.event_formats:
        reasons.add("format")
    if request.duration_hours is not None and provider.max_hours is not None:
        if provider.max_hours < request.duration_hours:
            reasons.add("duration")
    if request.language is not None and request.language not in provider.languages:
        reasons.add("language")
    return reasons


def _card(provider: Provider, request: RecommendationRequest) -> dict:
    first_sentence = f"Свободен {request.event_date} и берёт формат «{request.event_format}»"
    if request.language:
        first_sentence += f", работает на {request.language}"
    first_sentence += "."

    details = [
        f"Цена от {provider.price_from_kzt:,} ₸ укладывается в бюджет {request.budget_kzt:,} ₸.".replace(
            ",", " "
        ).rstrip("."),
    ]
    if request.duration_hours and provider.max_hours is not None:
        hours = str(request.duration_hours).removesuffix(".0").replace(".", ",")
        details.append(f"готов работать до {provider.max_hours} ч при запросе на {hours} ч")
    description_signal = _description_excerpt(provider.description)
    if description_signal:
        details.append(f"в профиле отмечено: «{description_signal}»")
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


def recommend(
    providers: Iterable[Provider], request: RecommendationRequest
) -> dict:
    """Return one of the three user-visible outcomes required by the brief."""
    request = normalize_request(request)
    scoped = [
        provider
        for provider in providers
        if provider.city == request.city and request.category in provider.categories
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
    for provider in scoped:
        reasons = _rejection_reasons(provider, request)
        if reasons:
            rejected.update(key for key in REASON_ORDER if key in reasons)
        else:
            eligible.append(provider)

    if not eligible:
        return {
            "outcome": "no_match",
            "cards": [],
            "message": (
                f"В каталоге есть {len(scoped)} подрядчик(а) этой категории, "
                f"но никто не проходит условия: {_reason_sentence(rejected)}"
            ),
            "stats": {"catalog_candidates": len(scoped), "eligible": 0, "rejected": dict(rejected)},
        }

    # Lower starting price is preferable after every hard requirement is met.
    # ID is the permanent tie-breaker: the same input always gives the same order.
    ranked = sorted(eligible, key=lambda provider: (provider.price_from_kzt, provider.id))
    cards = [_card(provider, request) for provider in ranked[:3]]
    message = f"Подобрано {len(cards)} из {len(eligible)} подходящих подрядчиков."
    if len(eligible) < 3:
        rejected_message = _reason_sentence(rejected)
        if rejected_message:
            message += f" Меньше трёх, потому что {rejected_message}"
        else:
            message += " Меньше трёх, потому что в этой категории всего столько доступных профилей."

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
