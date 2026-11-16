"""Schéma initial : source, climate_index, import_batch, observation.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

SEASONS = "'DJF', 'JFM', 'FMA', 'MAM', 'AMJ', 'MJJ', 'JJA', 'JAS', 'ASO', 'SON', 'OND', 'NDJ'"


def upgrade() -> None:
    op.create_table(
        "source",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("documentation_url", sa.String(500), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "climate_index",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("region", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_table(
        "import_batch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "index_id",
            sa.Integer(),
            sa.ForeignKey("climate_index.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("file_last_modified", sa.String(100), nullable=True),
        sa.Column("extracted_at", sa.Date(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rows_read", sa.Integer(), nullable=False),
        sa.Column("rows_inserted", sa.Integer(), nullable=False),
        sa.Column("rows_updated", sa.Integer(), nullable=False),
        sa.Column("rows_unchanged", sa.Integer(), nullable=False),
        sa.Column("rows_rejected", sa.Integer(), nullable=False),
        sa.Column("duplicates_in_file", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed', 'skipped')", name="ck_import_status"
        ),
        sa.CheckConstraint(
            "rows_read >= 0 AND rows_inserted >= 0 AND rows_updated >= 0 "
            "AND rows_unchanged >= 0 AND rows_rejected >= 0 AND duplicates_in_file >= 0",
            name="ck_import_counters_positive",
        ),
    )
    op.create_index("ix_import_batch_file_sha256", "import_batch", ["file_sha256"])
    op.create_table(
        "observation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "index_id",
            sa.Integer(),
            sa.ForeignKey("climate_index.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "import_id",
            sa.Integer(),
            sa.ForeignKey("import_batch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("season", sa.String(3), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("mean_sst", sa.Numeric(5, 2), nullable=True),
        sa.Column("anomaly", sa.Numeric(4, 2), nullable=False),
        # L'index unique (index_id, period) sert aussi aux requêtes filtrées par période.
        sa.UniqueConstraint("index_id", "period", name="uq_observation_index_period"),
        sa.UniqueConstraint("index_id", "season", "year", name="uq_observation_index_season_year"),
        sa.CheckConstraint(f"season IN ({SEASONS})", name="ck_observation_season"),
        sa.CheckConstraint("year BETWEEN 1850 AND 2100", name="ck_observation_year"),
        sa.CheckConstraint("anomaly BETWEEN -10 AND 10", name="ck_observation_anomaly_range"),
        sa.CheckConstraint(
            "mean_sst IS NULL OR mean_sst BETWEEN 0 AND 40", name="ck_observation_sst_range"
        ),
    )
    op.create_index("ix_observation_import_id", "observation", ["import_id"])


def downgrade() -> None:
    op.drop_index("ix_observation_import_id", table_name="observation")
    op.drop_table("observation")
    op.drop_index("ix_import_batch_file_sha256", table_name="import_batch")
    op.drop_table("import_batch")
    op.drop_table("climate_index")
    op.drop_table("source")
