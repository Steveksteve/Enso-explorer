"""Transformation pure (sans base de données) du fichier NOAA `RONI.ascii.txt`.

Entrée : texte brut au format NOAA CPC, RONI (3 colonnes) ou ONI (4 colonnes) :
    "SEAS   YR  ANOM"                 "SEAS  YR   TOTAL   ANOM"
    "DJF  1950 -1.19"                 "DJF 1950  25.01  -1.32"
Sortie : DataFrame propre (season, year, period, mean_sst, anomaly) + rapport de contrôle.

Ces fonctions ne touchent ni au réseau ni à la base : elles sont testables isolément.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

SEASONS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ")
# Mois central de chaque saison glissante : DJF -> janvier (1), ..., NDJ -> décembre (12).
CENTRAL_MONTH = {season: i + 1 for i, season in enumerate(SEASONS)}

MIN_YEAR, MAX_YEAR = 1850, 2100
MAX_ABS_ANOMALY = 10.0  # garde-fou physique : une anomalie ONI réelle reste < 3 °C
MISSING_SENTINELS = (-99.9, -99.99, -999.0)  # valeurs "manquantes" usuelles des fichiers NOAA

# Formats NOAA acceptés : RONI (sans SST moyenne) et ONI (avec SST moyenne "TOTAL")
RONI_COLUMNS = ["SEAS", "YR", "ANOM"]
ONI_COLUMNS = ["SEAS", "YR", "TOTAL", "ANOM"]


class NoaaFormatError(ValueError):
    """Le fichier ne ressemble pas au format NOAA attendu (mauvais fichier ou format modifié)."""


@dataclass
class TransformReport:
    rows_read: int = 0
    rows_valid: int = 0
    rows_rejected: int = 0
    duplicates: int = 0
    conflicting_duplicates: int = 0
    missing_periods: int = 0
    rejections: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"lues={self.rows_read} valides={self.rows_valid} rejetées={self.rows_rejected} "
            f"doublons={self.duplicates} (dont conflictuels={self.conflicting_duplicates}) "
            f"périodes manquantes={self.missing_periods}"
        )


def parse_noaa_text(text: str) -> pd.DataFrame:
    """Lit le texte NOAA en DataFrame brut (toutes les colonnes en texte, rien n'est corrigé)."""
    if not text or not text.strip():
        raise NoaaFormatError("Fichier vide")
    frame = pd.read_csv(io.StringIO(text), sep=r"\s+", dtype=str, engine="python")
    columns = list(frame.columns)
    if columns == RONI_COLUMNS:
        frame.insert(2, "TOTAL", None)  # le RONI ne publie pas de SST moyenne
    elif columns != ONI_COLUMNS:
        raise NoaaFormatError(
            f"En-tête inattendu {columns} ; attendu {RONI_COLUMNS} (RONI) ou {ONI_COLUMNS} (ONI)"
        )
    return frame.rename(
        columns={"SEAS": "season", "YR": "year", "TOTAL": "mean_sst", "ANOM": "anomaly"}
    )


def clean_observations(raw: pd.DataFrame) -> tuple[pd.DataFrame, TransformReport]:
    """Valide, convertit, déduplique et trie les observations.

    Règles :
      * saison inconnue, année hors [1850, 2100] ou non entière -> rejet ("date invalide")
      * anomalie absente, valeur sentinelle NOAA ou |anomalie| > 10 °C -> rejet
      * doublon (même saison + même année) -> on garde la DERNIÈRE occurrence du fichier
        (NOAA ajoute les révisions en fin de fichier) et on compte le doublon ;
        si les valeurs diffèrent, le doublon est signalé comme conflictuel.
    """
    report = TransformReport(rows_read=len(raw))
    df = raw.copy()
    df["line"] = np.arange(2, len(df) + 2)  # n° de ligne dans le fichier (en-tête = ligne 1)

    df["season"] = df["season"].astype(str).str.strip().str.upper()
    df["year_num"] = pd.to_numeric(df["year"], errors="coerce")
    df["mean_sst"] = pd.to_numeric(df["mean_sst"], errors="coerce")
    df["anomaly"] = pd.to_numeric(df["anomaly"], errors="coerce")

    for sentinel in MISSING_SENTINELS:
        df.loc[np.isclose(df["anomaly"], sentinel), "anomaly"] = np.nan
        df.loc[np.isclose(df["mean_sst"], sentinel), "mean_sst"] = np.nan

    bad_season = ~df["season"].isin(SEASONS)
    bad_year = (
        df["year_num"].isna()
        | (df["year_num"] % 1 != 0)
        | (df["year_num"] < MIN_YEAR)
        | (df["year_num"] > MAX_YEAR)
    )
    bad_anomaly = df["anomaly"].isna() | (df["anomaly"].abs() > MAX_ABS_ANOMALY)

    reasons = np.select(
        [bad_season, bad_year, bad_anomaly],
        ["saison inconnue", "date invalide (année)", "anomalie manquante ou hors bornes"],
        default="",
    )
    rejected = reasons != ""
    for line, reason, season, year in zip(
        df.loc[rejected, "line"],
        reasons[rejected],
        df.loc[rejected, "season"],
        df.loc[rejected, "year"],
        strict=True,
    ):
        report.rejections.append(f"ligne {line} ({season} {year}) : {reason}")
    report.rows_rejected = int(rejected.sum())

    df = df.loc[~rejected].copy()
    df["year"] = df["year_num"].astype(int)
    df["anomaly"] = df["anomaly"].round(2)
    df["mean_sst"] = df["mean_sst"].round(2)

    # --- Doublons ---
    key = ["season", "year"]
    dup_mask = df.duplicated(subset=key, keep="last")
    report.duplicates = int(dup_mask.sum())
    if report.duplicates:
        distinct_values = df.groupby(key)[["anomaly", "mean_sst"]].nunique(dropna=False)
        report.conflicting_duplicates = int((distinct_values.max(axis=1) > 1).sum())
    df = df.loc[~dup_mask]

    # --- Période : 1er jour du mois central ---
    df["period"] = [
        date(int(y), CENTRAL_MONTH[s], 1) for s, y in zip(df["season"], df["year"], strict=True)
    ]
    df = df.sort_values("period").reset_index(drop=True)

    # --- Continuité (information, pas un rejet) ---
    if len(df) > 1:
        months = np.array([p.year * 12 + p.month for p in df["period"]])
        report.missing_periods = int((np.diff(months) - 1).clip(min=0).sum())

    report.rows_valid = len(df)
    return df[["season", "year", "period", "mean_sst", "anomaly"]], report


def transform(text: str) -> tuple[pd.DataFrame, TransformReport]:
    """Raccourci : parse + clean."""
    return clean_observations(parse_noaa_text(text))
