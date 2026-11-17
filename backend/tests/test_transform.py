"""TEST DE DONNÉES (minimal obligatoire n°1) : transformation Python des observations NOAA."""

from datetime import date

import pytest

from etl.transform import OniFormatError, parse_oni_text, transform

HEADER = " SEAS  YR   TOTAL   ANOM\n"


def test_real_noaa_file_is_parsed_completely(oni_text):
    frame, report = transform(oni_text)
    assert report.rows_read == 921
    assert report.rows_rejected == 0
    assert report.duplicates == 0
    assert report.missing_periods == 0
    first, last = frame.iloc[0], frame.iloc[-1]
    assert (first.season, first.year, first.period, first.anomaly) == (
        "DJF",
        1950,
        date(1950, 1, 1),
        -1.32,
    )
    assert (last.season, last.year, last.period) == ("ASO", 2026, date(2026, 9, 1))
    # Valeur de référence du pic El Niño 1997-98 (NDJ 1997 = mois central décembre 1997)
    ndj_1997 = frame.loc[frame.period == date(1997, 12, 1)].iloc[0]
    assert ndj_1997.anomaly == pytest.approx(2.37)


def test_duplicates_are_removed_and_last_value_kept():
    text = (
        HEADER
        + "  DJF 1998  28.85   2.22\n"
        + "  JFM 1998  28.76   1.91\n"
        + "  DJF 1998  28.85   2.22\n"  # doublon identique
        + "  JFM 1998  28.80   1.95\n"  # doublon conflictuel (révision) -> on garde celui-ci
    )
    frame, report = transform(text)
    assert len(frame) == 2
    assert report.duplicates == 2
    assert report.conflicting_duplicates == 1
    assert frame.loc[frame.season == "JFM", "anomaly"].item() == pytest.approx(1.95)


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("  DJF 19X7  28.85   2.22\n", "date invalide"),
        ("  DJF 2200  28.85   2.22\n", "date invalide"),
        ("  XYZ 1998  28.85   2.22\n", "saison inconnue"),
        ("  DJF 1998  28.85  -99.90\n", "anomalie manquante"),
        ("  DJF 1998  28.85  15.00\n", "anomalie manquante ou hors bornes"),
    ],
)
def test_invalid_rows_are_rejected_with_a_reason(line, reason):
    frame, report = transform(HEADER + "  NDJ 1997  28.96   2.37\n" + line)
    assert len(frame) == 1
    assert report.rows_rejected == 1
    assert reason in report.rejections[0]
    assert "ligne 3" in report.rejections[0]


def test_period_uses_central_month_of_the_season():
    frame, _ = transform(HEADER + "  NDJ 1997  28.96   2.37\n  DJF 1998  28.85   2.22\n")
    assert list(frame.period) == [date(1997, 12, 1), date(1998, 1, 1)]


def test_gap_in_series_is_reported():
    frame, report = transform(HEADER + "  DJF 1998  28.85   2.22\n  AMJ 1998  28.13   0.40\n")
    assert len(frame) == 2
    assert report.missing_periods == 3  # JFM, FMA, MAM absents


def test_unexpected_header_is_refused():
    with pytest.raises(OniFormatError):
        parse_oni_text("Year Month Value\n1998 1 2.2\n")
    with pytest.raises(OniFormatError):
        parse_oni_text("   \n")


def test_lowercase_season_is_accepted():
    frame, report = transform(HEADER + "  djf 1998  28.85   2.22\n")
    assert report.rows_rejected == 0
    assert frame.iloc[0].season == "DJF"
