"""Tests complémentaires : règle de détection des épisodes et idempotence de l'ETL."""

from datetime import date

from sqlalchemy import func, select

from app.models import ImportBatch, Observation
from app.services.episodes import Point, detect_episodes
from etl.load import load_bytes

SEASONS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ")


def series(values, start_year=2000):
    return [
        Point(date(start_year + i // 12, i % 12 + 1, 1), SEASONS[i % 12], start_year + i // 12, v)
        for i, v in enumerate(values)
    ]


def test_five_consecutive_seasons_make_an_episode():
    episodes = detect_episodes(series([0.0, 0.5, 0.8, 1.2, 0.9, 0.6, 0.2, 0.0]))
    assert len(episodes) == 1
    ep = episodes[0]
    assert (ep.phase, ep.n_seasons, ep.peak.anomaly, ep.intensity) == ("el_nino", 5, 1.2, "modéré")
    assert ep.ongoing is False


def test_four_seasons_are_not_enough():
    assert detect_episodes(series([0.0, -0.6, -0.9, -0.7, -0.5, 0.1])) == []


def test_episode_reaching_end_of_data_is_flagged_ongoing():
    episodes = detect_episodes(series([0.1, -0.5, -0.8, -1.1, -1.0, -0.9]))
    assert episodes[0].ongoing is True
    assert episodes[0].phase == "la_nina"


def test_etl_is_idempotent_and_tracks_revisions(session_factory, oni_text):
    with session_factory() as session:
        before = session.scalar(select(func.count()).select_from(Observation))
        # 1) même fichier : ignoré
        same = load_bytes(
            session, oni_text.encode(), file_name="oni.ascii.txt", extracted_at=date(2026, 11, 16)
        )
        assert same.status == "skipped"
        # 2) fichier révisé (une valeur modifiée) : 1 mise à jour, rien d'inséré
        revised = oni_text.replace("  ASO 2026  29.23   2.46", "  ASO 2026  29.25   2.48")
        result = load_bytes(
            session, revised.encode(), file_name="oni.ascii.txt", extracted_at=date(2026, 11, 17)
        )
        assert (result.status, result.inserted, result.updated) == ("success", 0, 1)
        assert session.scalar(select(func.count()).select_from(Observation)) == before
        obs = session.scalar(select(Observation).where(Observation.period == date(2026, 9, 1)))
        assert float(obs.anomaly) == 2.48
        assert obs.import_id == result.import_id  # traçabilité de la révision
        # remise en état pour les autres tests
        load_bytes(
            session,
            oni_text.encode(),
            file_name="oni.ascii.txt",
            extracted_at=date(2026, 11, 16),
            force=True,
        )
        assert session.scalar(select(func.count()).select_from(ImportBatch)) >= 3
