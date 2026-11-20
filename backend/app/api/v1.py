"""Routes de l'API v1 (préfixe /api/v1). Lecture seule : aucune route ne modifie les données."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import ClimateIndex, ImportBatch, Observation
from app.schemas import (
    ComparisonOut,
    EpisodeOut,
    EpisodeSeries,
    ErrorOut,
    ImportOut,
    IndexOut,
    ObservationOut,
    ObservationsResponse,
    Phase,
    SourceOut,
)
from app.services.episodes import (
    MIN_SEASONS,
    THRESHOLD,
    Episode,
    Point,
    detect_episodes,
    interpret,
)

router = APIRouter(prefix="/api/v1")

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
IndexCode = Annotated[str, Path(pattern=r"^[A-Za-z0-9]{2,10}$", examples=["ONI"])]
MonthParam = Annotated[
    str | None,
    Query(pattern=MONTH_PATTERN, description="Mois AAAA-MM (inclus)", examples=["1997-01"]),
]
EpisodeId = Annotated[
    str, Query(pattern=r"^(EN|LN)-\d{4}-(0[1-9]|1[0-2])$", examples=["EN-1997-05"])
]

NOT_FOUND = {404: {"model": ErrorOut, "description": "Ressource introuvable"}}


def _month_to_date(value: str | None) -> date | None:
    if value is None:
        return None
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def _get_index(session: Session, code: str) -> ClimateIndex:
    index = session.scalar(
        select(ClimateIndex)
        .options(selectinload(ClimateIndex.source))
        .where(ClimateIndex.code == code.upper())
    )
    if index is None:
        raise HTTPException(status_code=404, detail=f"Indice inconnu : {code}")
    return index


def _obs_out(o: Observation | Point) -> ObservationOut:
    mean_sst = getattr(o, "mean_sst", None)
    return ObservationOut(
        season=o.season,
        year=o.year,
        period=o.period.strftime("%Y-%m"),
        anomaly=float(o.anomaly),
        mean_sst=float(mean_sst) if mean_sst is not None else None,
    )


def _episode_out(ep: Episode) -> EpisodeOut:
    return EpisodeOut(
        id=ep.id,
        phase=ep.phase,
        label=ep.label,
        start=ep.start.period.strftime("%Y-%m"),
        end=ep.end.period.strftime("%Y-%m"),
        start_season=f"{ep.start.season} {ep.start.year}",
        end_season=f"{ep.end.season} {ep.end.year}",
        n_seasons=ep.n_seasons,
        peak_anomaly=ep.peak.anomaly,
        peak_season=f"{ep.peak.season} {ep.peak.year}",
        mean_anomaly=ep.mean_anomaly,
        cumulative_anomaly=ep.cumulative_anomaly,
        intensity=ep.intensity,
        ongoing=ep.ongoing,
        truncated_start=ep.truncated_start,
    )


def _episodes_for(session: Session, index: ClimateIndex) -> list[Episode]:
    rows = session.execute(
        select(Observation.period, Observation.season, Observation.year, Observation.anomaly)
        .where(Observation.index_id == index.id)
        .order_by(Observation.period)
    ).all()
    points = [Point(r.period, r.season, r.year, float(r.anomaly)) for r in rows]
    return detect_episodes(points)


@router.get("/health", tags=["système"], summary="État de l'API et de la base")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Base de données indisponible") from exc
    return {"status": "ok", "database": "ok"}


@router.get(
    "/indices",
    response_model=list[IndexOut],
    tags=["indices"],
    summary="Liste des indices disponibles et de leur source",
)
def list_indices(session: Session = Depends(get_session)):
    return session.scalars(
        select(ClimateIndex).options(selectinload(ClimateIndex.source)).order_by(ClimateIndex.code)
    ).all()


@router.get(
    "/indices/{code}/observations",
    response_model=ObservationsResponse,
    responses={**NOT_FOUND, 422: {"description": "Paramètre invalide (format ou début > fin)"}},
    tags=["observations"],
    summary="Observations d'un indice, filtrées par période",
)
def list_observations(
    code: IndexCode,
    start: MonthParam = None,
    end: MonthParam = None,
    session: Session = Depends(get_session),
):
    """Renvoie les saisons dont le **mois central** est compris entre `start` et `end` inclus.

    Exemple : `start=1997-01&end=1998-12` renvoie DJF 1997 (janvier) à NDJ 1998 (décembre).
    """
    start_d, end_d = _month_to_date(start), _month_to_date(end)
    if start_d and end_d and start_d > end_d:
        raise HTTPException(status_code=422, detail="La date de début doit précéder la date de fin")
    index = _get_index(session, code)

    # Requête paramétrée construite par SQLAlchemy (aucune concaténation de chaîne SQL).
    query = select(Observation).where(Observation.index_id == index.id)
    if start_d:
        query = query.where(Observation.period >= start_d)
    if end_d:
        query = query.where(Observation.period <= end_d)
    observations = session.scalars(query.order_by(Observation.period)).all()

    last_import = session.scalar(
        select(ImportBatch)
        .where(ImportBatch.index_id == index.id, ImportBatch.status == "success")
        .order_by(ImportBatch.id.desc())
        .limit(1)
    )
    return ObservationsResponse(
        index=index.code,
        unit=index.unit,
        source=SourceOut.model_validate(index.source),
        last_import=ImportOut.model_validate(last_import) if last_import else None,
        start=start,
        end=end,
        count=len(observations),
        items=[_obs_out(o) for o in observations],
    )


@router.get(
    "/indices/{code}/episodes",
    response_model=list[EpisodeOut],
    responses=NOT_FOUND,
    tags=["épisodes"],
    summary="Épisodes El Niño / La Niña détectés (seuil ±0,5 °C, ≥ 5 saisons)",
)
def list_episodes(
    code: IndexCode,
    phase: Annotated[Phase | None, Query(description="Filtrer une phase")] = None,
    session: Session = Depends(get_session),
):
    index = _get_index(session, code)
    episodes = _episodes_for(session, index)
    return [_episode_out(e) for e in episodes if phase is None or e.phase == phase]


@router.get(
    "/indices/{code}/episodes/compare",
    response_model=ComparisonOut,
    responses={**NOT_FOUND, 422: {"description": "Identifiants invalides ou identiques"}},
    tags=["épisodes"],
    summary="Compare deux épisodes historiques avec une interprétation prudente",
)
def compare_episodes(
    code: IndexCode,
    a: EpisodeId,
    b: EpisodeId,
    session: Session = Depends(get_session),
):
    if a == b:
        raise HTTPException(status_code=422, detail="Choisir deux épisodes différents")
    index = _get_index(session, code)
    by_id = {e.id: e for e in _episodes_for(session, index)}
    missing = [x for x in (a, b) if x not in by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"Épisode introuvable : {', '.join(missing)}")
    ep_a, ep_b = by_id[a], by_id[b]
    findings, limits = interpret(ep_a, ep_b)
    return ComparisonOut(
        index=index.code,
        unit=index.unit,
        threshold=THRESHOLD,
        min_seasons=MIN_SEASONS,
        a=EpisodeSeries(episode=_episode_out(ep_a), values=[_obs_out(p) for p in ep_a.points]),
        b=EpisodeSeries(episode=_episode_out(ep_b), values=[_obs_out(p) for p in ep_b.points]),
        findings=findings,
        limits=limits,
    )


@router.get(
    "/imports",
    response_model=list[ImportOut],
    tags=["traçabilité"],
    summary="Derniers imports ETL (provenance des données)",
)
def list_imports(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    session: Session = Depends(get_session),
):
    return session.scalars(select(ImportBatch).order_by(ImportBatch.id.desc()).limit(limit)).all()
