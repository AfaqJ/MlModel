from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


Decision = Literal["auto_accept", "review_required"]
Source = Literal["model", "product_lookup"]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_id: str | None = Field(default=None, max_length=128)
    item_text: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=512)
    provider: str = Field(default="", max_length=256)
    invoice_metadata: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=3, ge=1, le=10)
    return_debug: bool = False


class BatchPredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str | None = Field(default=None, max_length=128)
    items: list[PredictRequest]
    top_k: int = Field(default=3, ge=1, le=10)


class Prediction(BaseModel):
    code: str
    name: str
    score: float


class Confidence(BaseModel):
    top1: float
    margin: float
    entropy: float


class PredictResponse(BaseModel):
    input_id: str | None
    model_version: str
    source: Source
    predictions: list[Prediction]
    confidence: Confidence
    decision: Decision
    reason: str | None
    latency_ms: int
    debug: dict[str, Any] | None = None


class RowError(BaseModel):
    input_id: str | None
    error: dict[str, str]


class BatchPredictResponse(BaseModel):
    batch_id: str | None
    model_version: str
    results: list[PredictResponse | RowError]
    summary: dict[str, int]
    latency_ms: int
