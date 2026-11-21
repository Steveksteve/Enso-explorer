"""Chargement du RONI dans PostgreSQL, avec traçabilité (table import_batch).

Usage :
    python -m etl.load --file ../data/raw/RONI.ascii.txt --extracted-at 2026-11-21 \
        --last-modified "Tue, 03 Nov 2026 19:31:48 GMT"
    python -m etl.load --download          # télécharge la version courante chez NOAA

Comportement :
  * Idempotent : un fichier déjà importé avec succès (même SHA-256) n'est pas réimporté
    (statut "skipped"), sauf avec --force.
  * Upsert : insertion des nouvelles saisons, mise à jour des valeurs révisées par NOAA,
    rien n'est modifié si la valeur est identique.
  * Tout se fait dans UNE transaction : en cas d'erreur, aucune observation n'est écrite
    et l'import est enregistré en "failed".
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ClimateIndex, ImportBatch, Observation, Source
from etl.transform import transform

log = logging.getLogger("etl")

RONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"

SOURCE_META = {
    "code": "NOAA_CPC_RONI",
    "name": "Relative Oceanic Niño Index (RONI)",
    "provider": "NOAA / NWS / Climate Prediction Center",
    "url": RONI_URL,
    "documentation_url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/",
    "version": "ERSST v6, moyenne glissante 3 mois, période de référence 1991–2020",
}
INDEX_META = {
    "code": "RONI",
    "name": "Relative Oceanic Niño Index",
    "region": "Niño 3.4 (5°N–5°S, 120°–170°W), relatif aux tropiques (20°N–20°S)",
    "unit": "°C",
    "description": (
        "Moyenne glissante sur 3 mois des anomalies de température de surface de la mer "
        "en Niño 3.4, moins l'anomalie moyenne de la bande tropicale 20°N–20°S, ajustée pour "
        "avoir la même variance que l'indice Niño 3.4. Seuils NOAA : ≥ +0,5 °C (El Niño) ou "
        "≤ −0,5 °C (La Niña) pendant au moins 5 saisons glissantes consécutives."
    ),
}


@dataclass
class LoadResult:
    import_id: int
    status: str
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    duplicates: int = 0


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_reference_data(session: Session) -> tuple[Source, ClimateIndex]:
    """Crée la source et l'indice s'ils n'existent pas encore (données de référence)."""
    source = session.scalar(select(Source).where(Source.code == SOURCE_META["code"]))
    if source is None:
        source = Source(**SOURCE_META)
        session.add(source)
        session.flush()
    index = session.scalar(select(ClimateIndex).where(ClimateIndex.code == INDEX_META["code"]))
    if index is None:
        index = ClimateIndex(**INDEX_META, source_id=source.id)
        session.add(index)
        session.flush()
    return source, index


def _to_decimal(value: float | None) -> Decimal | None:
    if value is None or value != value:  # NaN
        return None
    return Decimal(f"{value:.2f}")


def load_bytes(
    session: Session,
    content: bytes,
    *,
    file_name: str,
    extracted_at: date,
    last_modified: str | None = None,
    force: bool = False,
) -> LoadResult:
    source, index = ensure_reference_data(session)
    digest = sha256_hex(content)

    already = session.scalar(
        select(ImportBatch).where(
            ImportBatch.file_sha256 == digest,
            ImportBatch.index_id == index.id,
            ImportBatch.status == "success",
        )
    )
    batch = ImportBatch(
        source_id=source.id,
        index_id=index.id,
        file_name=file_name,
        file_sha256=digest,
        file_last_modified=last_modified,
        extracted_at=extracted_at,
        status="running",
    )
    session.add(batch)
    session.flush()

    if already is not None and not force:
        batch.status = "skipped"
        batch.message = f"Fichier identique déjà importé (import #{already.id})"
        batch.finished_at = datetime.now(UTC)
        session.commit()
        log.info(batch.message)
        return LoadResult(import_id=batch.id, status="skipped")

    frame, report = transform(content.decode("utf-8"))
    batch.rows_read = report.rows_read
    batch.rows_rejected = report.rows_rejected
    batch.duplicates_in_file = report.duplicates

    existing = {
        obs.period: obs
        for obs in session.scalars(select(Observation).where(Observation.index_id == index.id))
    }
    inserted = updated = unchanged = 0
    for row in frame.itertuples(index=False):
        anomaly = _to_decimal(row.anomaly)
        mean_sst = _to_decimal(row.mean_sst)
        current = existing.get(row.period)
        if current is None:
            session.add(
                Observation(
                    index_id=index.id,
                    import_id=batch.id,
                    season=row.season,
                    year=int(row.year),
                    period=row.period,
                    anomaly=anomaly,
                    mean_sst=mean_sst,
                )
            )
            inserted += 1
        elif current.anomaly != anomaly or current.mean_sst != mean_sst:
            # Révision NOAA : on met à jour et on trace l'import responsable.
            current.anomaly = anomaly
            current.mean_sst = mean_sst
            current.import_id = batch.id
            updated += 1
        else:
            unchanged += 1

    batch.rows_inserted, batch.rows_updated, batch.rows_unchanged = inserted, updated, unchanged
    batch.status = "success"
    batch.finished_at = datetime.now(UTC)
    batch.message = report.summary()
    if report.rejections:
        batch.message += " | " + "; ".join(report.rejections[:20])
    session.commit()
    log.info("Import #%s terminé : %s", batch.id, batch.message)
    return LoadResult(
        import_id=batch.id,
        status="success",
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        rejected=report.rows_rejected,
        duplicates=report.duplicates,
    )


def record_failure(session: Session, file_name: str, digest: str, extracted_at: date, err: str):
    """Après un rollback, trace l'échec dans une nouvelle transaction."""
    source, index = ensure_reference_data(session)
    session.add(
        ImportBatch(
            source_id=source.id,
            index_id=index.id,
            file_name=file_name,
            file_sha256=digest,
            extracted_at=extracted_at,
            status="failed",
            finished_at=datetime.now(UTC),
            message=err[:2000],
        )
    )
    session.commit()


def download(url: str = RONI_URL, timeout: int = 30) -> tuple[bytes, str | None]:
    if not url.startswith("https://"):
        raise ValueError("Seules les URL https:// sont acceptées")
    request = urllib.request.Request(  # noqa: S310 (schéma https vérifié ci-dessus)
        url, headers={"User-Agent": "enso-explorer-etl/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https vérifié)
        return response.read(), response.headers.get("Last-Modified")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import de l'indice NOAA RONI dans PostgreSQL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Fichier RONI.ascii.txt local")
    group.add_argument("--download", action="store_true", help="Télécharger depuis NOAA CPC")
    parser.add_argument(
        "--extracted-at",
        type=date.fromisoformat,
        default=None,
        help="Date d'extraction AAAA-MM-JJ (par défaut : aujourd'hui)",
    )
    parser.add_argument("--last-modified", default=None, help="En-tête HTTP Last-Modified")
    parser.add_argument("--force", action="store_true", help="Réimporter même si déjà importé")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.download:
        content, last_modified = download()
        file_name = "RONI.ascii.txt"
    else:
        content, last_modified = args.file.read_bytes(), args.last_modified
        file_name = args.file.name
    extracted_at = args.extracted_at or date.today()

    with SessionLocal() as session:
        try:
            result = load_bytes(
                session,
                content,
                file_name=file_name,
                extracted_at=extracted_at,
                last_modified=last_modified,
                force=args.force,
            )
        except Exception as exc:  # noqa: BLE001 — on trace tout échec avant de quitter
            session.rollback()
            record_failure(session, file_name, sha256_hex(content), extracted_at, repr(exc))
            log.exception("Import échoué")
            return 1
    print(
        f"Import #{result.import_id} [{result.status}] inséré={result.inserted} "
        f"mis à jour={result.updated} inchangé={result.unchanged} rejeté={result.rejected} "
        f"doublons={result.duplicates}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
