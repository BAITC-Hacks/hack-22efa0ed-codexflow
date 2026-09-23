"""HTTP API for the deterministic contractor recommendation engine."""

from pathlib import Path
import sys
from typing import Literal

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from contractor_assistant.chat import assistant_turn
from src.ai_explanations import get_explainer

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
    expose_headers=["X-Explanation-Source", "X-AI-Reason"],
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


class AssistantContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    city: str | None = None
    event_date: str | None = None
    event_format: str | None = None
    category: str | None = None
    budget_kzt: int | None = None
    duration_hours: int | float | None = None
    language: str | None = None


class AssistantChatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    message: str = Field(max_length=2000)
    context: AssistantContext = Field(default_factory=AssistantContext)


class AssistantChatResponse(BaseModel):
    reply: str
    context: AssistantContext
    complete: bool
    recommendation: RecommendationResponse | None = None


@app.post("/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(payload: AssistantChatPayload) -> dict:
    """Parse a chat turn, request missing details, and reuse the catalog matcher."""
    turn = assistant_turn(PROVIDERS, payload.message, payload.context.model_dump())
    result = turn.get("recommendation")
    if turn.get("complete") and result:
        context = turn["context"]
        request = RecommendationRequest(
            city=context["city"], event_date=context["event_date"],
            event_format=context["event_format"], category=context["category"],
            budget_kzt=context["budget_kzt"], duration_hours=context.get("duration_hours"),
            language=context.get("language"),
        )
        result, _, _ = await get_explainer().enhance(result, PROVIDERS, request)
        turn["recommendation"] = result
    return turn


@app.get("/assistant-assets/widget.js", include_in_schema=False)
def assistant_widget_js():
    return FileResponse(REPOSITORY_ROOT / "contractor_assistant" / "widget.js",
                        media_type="application/javascript")


@app.get("/assistant-assets/widget.css", include_in_schema=False)
def assistant_widget_css():
    return FileResponse(REPOSITORY_ROOT / "contractor_assistant" / "widget.css",
                        media_type="text/css")


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
async def get_recommendations(payload: RecommendationPayload, response: Response,
                              ai_explanations: bool = Query(default=False)) -> dict:
    request = payload.to_domain()
    result = recommend(PROVIDERS, request)
    source, reason = "rules", "not_requested"
    if ai_explanations:
        result, source, reason = await get_explainer().enhance(result, PROVIDERS, request)
    response.headers["X-Explanation-Source"] = source
    response.headers["X-AI-Reason"] = reason
    return result


# Only expose the public frontend directory, never the repository or its .git.
FRONTEND_PATH = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_PATH.is_dir():
    app.mount("/ui", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
