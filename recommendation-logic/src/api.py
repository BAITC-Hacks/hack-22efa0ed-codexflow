"""HTTP API for the deterministic contractor recommendation engine."""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.recommendation import (
    CALENDAR_START, CALENDAR_END, Outcome, RecommendationRequest,
    load_providers, recommend, validate_request_field,
)


DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "providers.csv"
PROVIDERS = load_providers(DATASET_PATH)

app = FastAPI(
    title="Event Contractor Matcher API",
    version="1.0.0",
    description="Детерминированный подбор до трёх свободных подрядчиков из каталога.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RecommendationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    city: str = Field(min_length=1, examples=["Алматы"])
    event_date: str = Field(
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", examples=["2026-11-14"],
        description=f"Дата в пределах {CALENDAR_START} — {CALENDAR_END}, включительно.",
        json_schema_extra={"format": "date"},
    )
    event_format: str = Field(min_length=1, examples=["корпоратив"])
    category: str = Field(min_length=1, examples=["Ведущий"])
    budget_kzt: int = Field(gt=0, examples=[500_000])
    duration_hours: int | float | None = Field(default=None, gt=0, examples=[4.5])
    language: str | None = Field(default=None, min_length=1, examples=["русский"])

    @field_validator("city", "event_date", "event_format", "category", "budget_kzt",
                     "duration_hours", "language", mode="before")
    @classmethod
    def validate_input(cls, value, info):
        return validate_request_field(info.field_name, value)

    def to_domain(self) -> RecommendationRequest:
        return RecommendationRequest(**self.model_dump())


class RecommendationCard(BaseModel):
    id: str
    name: str
    categories: list[str]
    city: str
    price_from_kzt: int
    synthetic: bool
    city_imputed: bool
    price_imputed: bool
    explanation: str


class RecommendationStats(BaseModel):
    catalog_candidates: int = Field(ge=0)
    eligible: int = Field(ge=0)
    rejected: dict[Literal["busy", "budget", "format", "duration", "language"], int] = Field(
        description="Число исключённых по каждой причине; один профиль может иметь несколько причин."
    )


class RecommendationResponse(BaseModel):
    outcome: Outcome
    cards: list[RecommendationCard] = Field(max_length=3)
    message: str
    stats: RecommendationStats


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "profiles_loaded": len(PROVIDERS)}


@app.get("/filters")
def filters() -> dict:
    """Values for frontend dropdowns; derived from the same source as matching."""
    return {
        "cities": sorted({provider.city for provider in PROVIDERS}),
        "categories": sorted({category for provider in PROVIDERS for category in provider.categories}),
        "event_formats": sorted(
            {event_format for provider in PROVIDERS for event_format in provider.event_formats}
        ),
        "languages": sorted({language for provider in PROVIDERS for language in provider.languages}),
        "event_date_range": {"min": CALENDAR_START, "max": CALENDAR_END},
    }


@app.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(payload: RecommendationPayload) -> dict:
    return recommend(PROVIDERS, payload.to_domain())
