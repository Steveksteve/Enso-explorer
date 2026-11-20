"""TEST API (minimal obligatoire n°2) : route filtrée par période + entrées invalides."""

import pytest


def test_observations_filtered_by_period(client):
    response = client.get(
        "/api/v1/indices/ONI/observations",
        params={
            "start": "1997-01",
            "end": "1998-12",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["index"] == "ONI"
    assert body["unit"] == "°C"
    assert body["count"] == 24
    assert body["items"][0] == {
        "season": "DJF",
        "year": 1997,
        "period": "1997-01",
        "anomaly": -0.41,
        "mean_sst": 26.23,
    }
    assert body["items"][-1]["period"] == "1998-12"
    peak = max(body["items"], key=lambda item: item["anomaly"])
    assert (peak["season"], peak["year"], peak["anomaly"]) == ("NDJ", 1997, 2.37)
    # Traçabilité : source et dernier import visibles dans la réponse
    assert body["source"]["url"].startswith("https://www.cpc.ncep.noaa.gov/")
    assert body["last_import"]["file_sha256"] == (
        "118c563331335c8649cdc2677e6be7ae89d1259d901345fcddbc2857af280f7f"
    )


def test_without_filter_returns_whole_series(client):
    body = client.get("/api/v1/indices/oni/observations").json()  # code insensible à la casse
    assert body["count"] == 921


@pytest.mark.parametrize(
    "params",
    [
        {"start": "1997-13"},  # mois inexistant
        {"start": "97-01"},  # mauvais format
        {"end": "1998-12-01"},  # jour non attendu
        {"start": "1997-01'; DROP TABLE observation;--"},  # tentative d'injection
    ],
)
def test_invalid_period_format_returns_422(client, params):
    response = client.get("/api/v1/indices/ONI/observations", params=params)
    assert response.status_code == 422


def test_start_after_end_returns_422(client):
    response = client.get(
        "/api/v1/indices/ONI/observations", params={"start": "1999-01", "end": "1998-01"}
    )
    assert response.status_code == 422
    assert "début" in response.json()["detail"]


def test_unknown_index_returns_404(client):
    assert client.get("/api/v1/indices/RONI/observations").status_code == 404


def test_episodes_and_comparison(client):
    episodes = client.get("/api/v1/indices/ONI/episodes", params={"phase": "el_nino"}).json()
    ids = {e["id"] for e in episodes}
    assert {"EN-1997-05", "EN-2014-10"} <= ids
    assert all(e["phase"] == "el_nino" for e in episodes)

    response = client.get(
        "/api/v1/indices/ONI/episodes/compare", params={"a": "EN-1997-05", "b": "EN-2014-10"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["a"]["episode"]["peak_anomaly"] == 2.37
    assert body["b"]["episode"]["peak_anomaly"] == 2.59
    assert len(body["a"]["values"]) == body["a"]["episode"]["n_seasons"]
    assert body["findings"] and body["limits"]


def test_comparison_errors(client):
    url = "/api/v1/indices/ONI/episodes/compare"
    assert client.get(url, params={"a": "EN-1997-05", "b": "EN-1997-05"}).status_code == 422
    assert client.get(url, params={"a": "EN-1997-05", "b": "EN-1900-01"}).status_code == 404
    assert client.get(url, params={"a": "bad", "b": "EN-1997-05"}).status_code == 422


def test_openapi_is_published(client):
    spec = client.get("/api/openapi.json").json()
    assert "/api/v1/indices/{code}/observations" in spec["paths"]


def test_start_only_returns_values_from_that_month(client):
    body = client.get("/api/v1/indices/ONI/observations", params={"start": "2026-01"}).json()
    assert body["items"][0]["period"] == "2026-01"
    assert body["count"] == 9
