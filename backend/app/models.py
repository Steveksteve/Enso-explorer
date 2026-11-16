"""Modèle de données : Source, ClimateIndex (Indice), ImportBatch (Import), Observation.

Cardinalités :
  Source 1 ── 0..* ClimateIndex   (une source publie un ou plusieurs indices)
  Source 1 ── 0..* ImportBatch    (chaque import lit un fichier d'une source)
  ClimateIndex 1 ── 0..* ImportBatch
  ClimateIndex 1 ── 0..* Observation
  ImportBatch 1 ── 0..* Observation  (l'import qui a écrit en dernier la valeur)
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

SEASONS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ")
_SEASONS_SQL = ", ".join(f"'{s}'" for s in SEASONS)


class Source(Base):
    __tablename__ = "source"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    documentation_url: Mapped[str] = mapped_column(String(500))
    version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    indices: Mapped[list["ClimateIndex"]] = relationship(back_populates="source")


class ClimateIndex(Base):
    __tablename__ = "climate_index"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id", ondelete="RESTRICT"))

    source: Mapped[Source] = relationship(back_populates="indices")


class ImportBatch(Base):
    __tablename__ = "import_batch"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed', 'skipped')", name="ck_import_status"
        ),
        CheckConstraint(
            "rows_read >= 0 AND rows_inserted >= 0 AND rows_updated >= 0 "
            "AND rows_unchanged >= 0 AND rows_rejected >= 0 AND duplicates_in_file >= 0",
            name="ck_import_counters_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id", ondelete="RESTRICT"))
    index_id: Mapped[int] = mapped_column(ForeignKey("climate_index.id", ondelete="RESTRICT"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    file_last_modified: Mapped[str | None] = mapped_column(String(100))
    extracted_at: Mapped[date] = mapped_column(Date)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    rows_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_in_file: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship()
    index: Mapped[ClimateIndex] = relationship()


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        # Contrôle des doublons au niveau SQL : une seule valeur par indice et par saison.
        UniqueConstraint("index_id", "period", name="uq_observation_index_period"),
        UniqueConstraint("index_id", "season", "year", name="uq_observation_index_season_year"),
        CheckConstraint(f"season IN ({_SEASONS_SQL})", name="ck_observation_season"),
        CheckConstraint("year BETWEEN 1850 AND 2100", name="ck_observation_year"),
        CheckConstraint("anomaly BETWEEN -10 AND 10", name="ck_observation_anomaly_range"),
        CheckConstraint(
            "mean_sst IS NULL OR mean_sst BETWEEN 0 AND 40", name="ck_observation_sst_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("climate_index.id", ondelete="CASCADE"))
    import_id: Mapped[int] = mapped_column(
        ForeignKey("import_batch.id", ondelete="RESTRICT"), index=True
    )
    season: Mapped[str] = mapped_column(String(3))
    year: Mapped[int] = mapped_column(SmallInteger)
    # 1er jour du mois central de la saison (DJF 1998 -> 1998-01-01) : sert au tri et au filtre.
    period: Mapped[date] = mapped_column(Date)
    mean_sst: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    anomaly: Mapped[Decimal] = mapped_column(Numeric(4, 2))

    index: Mapped[ClimateIndex] = relationship()
    import_batch: Mapped[ImportBatch] = relationship()
