"""Détection et comparaison d'épisodes El Niño / La Niña à partir de l'ONI.

Règle utilisée (NOAA CPC, table historique ONI) :
  El Niño : ONI ≥ +0,5 °C pendant au moins 5 saisons glissantes consécutives
  La Niña : ONI ≤ −0,5 °C pendant au moins 5 saisons glissantes consécutives

Choix documenté : le seuil est appliqué aux valeurs à 2 décimales du fichier NOAA, alors que
la table colorée de NOAA utilise des valeurs arrondies à 0,1 °C. Les bornes d'un épisode
peuvent donc différer d'une saison avec la table NOAA (ex. une saison à +0,46 °C).

Classe d'intensité (facultative, descriptive) : selon le pic |ONI| —
  faible [0,5 ; 1,0[, modéré [1,0 ; 1,5[, fort [1,5 ; 2,0[, très fort ≥ 2,0.
C'est une convention de lecture répandue, PAS une classification officielle NOAA.
Le terme « Super El Niño » n'est volontairement pas utilisé.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

THRESHOLD = 0.5
MIN_SEASONS = 5
INTENSITY_CLASSES = ((2.0, "très fort"), (1.5, "fort"), (1.0, "modéré"), (0.5, "faible"))


@dataclass(frozen=True)
class Point:
    period: date
    season: str
    year: int
    anomaly: float


@dataclass(frozen=True)
class Episode:
    id: str
    phase: str  # "el_nino" | "la_nina"
    points: tuple[Point, ...]
    ongoing: bool  # l'épisode atteint la fin des données : durée = borne minimale
    truncated_start: bool = False  # l'épisode commence avec les données (avant 1950 ?)

    @property
    def start(self) -> Point:
        return self.points[0]

    @property
    def end(self) -> Point:
        return self.points[-1]

    @property
    def n_seasons(self) -> int:
        return len(self.points)

    @property
    def peak(self) -> Point:
        # pic = valeur la plus éloignée de 0 dans le sens de la phase
        if self.phase == "el_nino":
            return max(self.points, key=lambda p: p.anomaly)
        return min(self.points, key=lambda p: p.anomaly)

    @property
    def mean_anomaly(self) -> float:
        return round(sum(p.anomaly for p in self.points) / self.n_seasons, 2)

    @property
    def cumulative_anomaly(self) -> float:
        return round(sum(p.anomaly for p in self.points), 2)

    @property
    def intensity(self) -> str:
        peak = abs(self.peak.anomaly)
        for limit, label in INTENSITY_CLASSES:
            if peak >= limit:
                return label
        return "sous le seuil"

    @property
    def label(self) -> str:
        name = "El Niño" if self.phase == "el_nino" else "La Niña"
        years = (
            f"{self.start.period.year}"
            if self.start.period.year == self.end.period.year
            else f"{self.start.period.year}–{self.end.period.year}"
        )
        return f"{name} {years}" + (" (en cours)" if self.ongoing else "")


def _phase_of(anomaly: float, threshold: float) -> str | None:
    if anomaly >= threshold:
        return "el_nino"
    if anomaly <= -threshold:
        return "la_nina"
    return None


def _consecutive(a: date, b: date) -> bool:
    return (b.year * 12 + b.month) - (a.year * 12 + a.month) == 1


def detect_episodes(
    points: list[Point], threshold: float = THRESHOLD, min_seasons: int = MIN_SEASONS
) -> list[Episode]:
    """Parcourt la série triée et retient les séquences continues assez longues."""
    points = sorted(points, key=lambda p: p.period)
    episodes: list[Episode] = []
    run: list[Point] = []
    run_phase: str | None = None

    first_period = points[0].period if points else None

    def close_run(is_last: bool) -> None:
        if run_phase and len(run) >= min_seasons:
            prefix = "EN" if run_phase == "el_nino" else "LN"
            start = run[0].period
            episodes.append(
                Episode(
                    id=f"{prefix}-{start.year}-{start.month:02d}",
                    phase=run_phase,
                    points=tuple(run),
                    ongoing=is_last,
                    truncated_start=run[0].period == first_period,
                )
            )

    for i, point in enumerate(points):
        phase = _phase_of(point.anomaly, threshold)
        continues = (
            phase is not None
            and phase == run_phase
            and run
            and _consecutive(run[-1].period, point.period)
        )
        if continues:
            run.append(point)
        else:
            close_run(is_last=False)
            run, run_phase = ([point], phase) if phase else ([], None)
        if i == len(points) - 1:
            close_run(is_last=True)
    return episodes


def _fmt(value: float) -> str:
    return f"{value:+.2f}".replace(".", ",") + " °C"


def interpret(a: Episode, b: Episode) -> tuple[list[str], list[str]]:
    """Produit une interprétation prudente (constats chiffrés) et la liste des limites."""
    findings: list[str] = []
    pa, pb = a.peak, b.peak
    findings.append(
        f"{a.label} atteint son pic à {_fmt(pa.anomaly)} ({pa.season} {pa.year}), "
        f"contre {_fmt(pb.anomaly)} ({pb.season} {pb.year}) pour {b.label}."
    )
    diff = abs(abs(pa.anomaly) - abs(pb.anomaly))
    if a.phase != b.phase:
        findings.append(
            "Les deux épisodes sont de phases opposées : seule l'amplitude absolue est comparable."
        )
    diff_txt = f"{diff:.2f}".replace(".", ",")
    if diff < 0.2:
        findings.append(
            f"L'écart d'amplitude au pic ({diff_txt} °C) est faible : il est du même ordre que les "
            "révisions possibles de l'indice (version ERSST, période de référence). On ne peut pas "
            "conclure qu'un épisode est plus intense que l'autre sur ce seul critère."
        )
    else:
        stronger = a if abs(pa.anomaly) > abs(pb.anomaly) else b
        nuance = "nettement plus forte" if diff >= 0.5 else "légèrement plus forte"
        findings.append(
            f"Sur cet indice, {stronger.label} présente une anomalie maximale {nuance} "
            f"(écart de {diff_txt} °C au pic)."
        )
    findings.append(
        f"Durée au-delà du seuil de ±0,5 °C : {a.n_seasons} saisons glissantes pour {a.label}, "
        f"{b.n_seasons} pour {b.label} (soit environ {a.n_seasons + 2} et {b.n_seasons + 2} mois "
        "calendaires couverts). Anomalie moyenne sur l'épisode : "
        f"{_fmt(a.mean_anomaly)} contre {_fmt(b.mean_anomaly)}."
    )
    for ep in (a, b):
        if ep.truncated_start:
            findings.append(
                f"{ep.label} commence avec le début de la série (1950) : l'épisode a pu débuter "
                "avant, sa durée réelle est donc inconnue (borne minimale)."
            )
        if ep.ongoing:
            findings.append(
                f"{ep.label} n'est pas terminé dans les données : sa durée est une borne minimale "
                "et ses dernières valeurs peuvent encore être révisées par NOAA."
            )

    limits = [
        "L'ONI ne mesure que la température de surface de la mer dans la région Niño 3.4 : "
        "il ne décrit ni la réponse de l'atmosphère, ni les impacts régionaux "
        "(pluies, sécheresses, températures).",
        "Classe d'intensité (faible, modéré, fort, très fort) = convention de lecture fondée sur "
        "le pic de l'ONI, pas une classification officielle NOAA. Le terme « Super El Niño » "
        "n'est pas utilisé.",
        "Les anomalies sont calculées par rapport à des périodes de référence de 30 ans mises à "
        "jour tous les 5 ans : comparer des épisodes éloignés dans le temps reste approximatif.",
        "Chaque valeur est une moyenne sur 3 mois : les variations mensuelles sont lissées.",
        "Aucune prévision n'est produite par cette application.",
    ]
    return findings, limits
