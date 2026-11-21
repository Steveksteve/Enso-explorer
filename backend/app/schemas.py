"""Schémas Pydantic : ce que l'API renvoie (contrat documenté dans OpenAPI)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["el_nino", "la_nina"]


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    provider: str
    url: str
    documentation_url: str
    version: str


class IndexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    region: str
    unit: str
    description: str
    source: SourceOut


class ImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_sha256: str
    file_last_modified: str | None
    extracted_at: date
    started_at: datetime
    finished_at: datetime | None
    status: str
    rows_read: int
    rows_inserted: int
    rows_updated: int
    rows_unchanged: int
    rows_rejected: int
    duplicates_in_file: int


class ObservationOut(BaseModel):
    season: str = Field(examples=["NDJ"])
    year: int = Field(examples=[1997])
    period: str = Field(description="Mois central de la saison, AAAA-MM", examples=["1997-12"])
    anomaly: float = Field(description="Anomalie RONI en °C", examples=[2.28])
    mean_sst: float | None = Field(
        description="SST moyenne Niño 3.4 en °C (absente pour le RONI)", examples=[None]
    )


class ObservationsResponse(BaseModel):
    index: str
    unit: str
    source: SourceOut
    last_import: ImportOut | None
    start: str | None
    end: str | None
    count: int
    items: list[ObservationOut]


class EpisodeOut(BaseModel):
    id: str = Field(examples=["EN-1997-05"])
    phase: Phase
    label: str
    start: str
    end: str
    start_season: str
    end_season: str
    n_seasons: int
    peak_anomaly: float
    peak_season: str
    mean_anomaly: float
    cumulative_anomaly: float
    intensity: str
    ongoing: bool
    truncated_start: bool


class EpisodeSeries(BaseModel):
    episode: EpisodeOut
    values: list[ObservationOut]


class ComparisonOut(BaseModel):
    index: str
    unit: str
    threshold: float
    min_seasons: int
    a: EpisodeSeries
    b: EpisodeSeries
    findings: list[str]
    limits: list[str]


class ErrorOut(BaseModel):
    detail: str
