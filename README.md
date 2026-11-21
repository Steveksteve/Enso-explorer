# ENSO Explorer — El Niño / La Niña à partir de l'indice NOAA ONI

Application web pour explorer une série scientifique réelle : l'**Oceanic Niño Index (ONI)** publié
par NOAA / Climate Prediction Center. Elle importe la série dans PostgreSQL, l'expose par une API
FastAPI documentée, l'affiche sous forme de courbe interactive filtrable et compare deux épisodes
historiques avec une interprétation prudente.

Projet de rattrapage individuel — Katia Sakri.

| MVP | Où |
|---|---|
| 1. Import d'une série NOAA authentique dans PostgreSQL, source identifiée, doublons contrôlés | `backend/etl/`, `data/raw/SOURCE.md` |
| 2. API FastAPI documentée, filtre temporel, validation des entrées | `backend/app/api/v1.py`, `/api/docs` |
| 3. Courbe interactive React/TypeScript + filtre de période | `frontend/src/components/SeriesExplorer.tsx` |
| 4. Comparaison de deux épisodes + interprétation prudente | `backend/app/services/episodes.py`, `frontend/src/components/EpisodeComparison.tsx` |

## Données

* Indice : **ONI** (pas le RONI). Fichier `data/raw/oni.ascii.txt`, téléchargé le **2026-11-16** depuis
  <https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt> (Last-Modified NOAA : 03/11/2026).
* Version : ONI calculé sur **ERSST v6** (vérifié valeur par valeur contre la table CPC v6).
* 921 saisons glissantes de 3 mois, DJF 1950 → ASO 2026, unité °C.
* SHA-256 : `118c563331335c8649cdc2677e6be7ae89d1259d901345fcddbc2857af280f7f`.
* Détails, précautions et différence ONI/RONI : [`data/raw/SOURCE.md`](data/raw/SOURCE.md).

## Architecture

```
navigateur ──HTTPS──▶ Caddy ──┬── /         fichiers statiques React (build Vite)
                              └── /api/*  ─▶ FastAPI ──▶ PostgreSQL ◀── worker ETL (pandas)
```

```
backend/   app/ (FastAPI, modèles SQLAlchemy, services)  etl/ (transform + load)  alembic/  tests/
frontend/  src/ (composants React, client API typé, hooks, tests Vitest)
deploy/    Caddyfile, backup.sh
data/raw/  fichier NOAA + provenance
docs/      preuves de tests, captures, openapi.json
```

## Prérequis

* Python 3.11+ et Node.js 20+ (développement local), PostgreSQL 16
* ou Docker + Docker Compose (pile complète)

## Lancement local (sans Docker)

```bash
# 1. Base de données (PostgreSQL déjà installé)
createuser -P enso            # mot de passe : enso_dev (exemple de développement)
createdb -O enso enso

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://enso:enso_dev@localhost:5432/enso
alembic upgrade head                                   # crée le schéma
python -m etl.load --file ../data/raw/oni.ascii.txt --extracted-at 2026-11-16 \
       --last-modified "Tue, 03 Nov 2026 19:31:48 GMT"   # importe les 921 observations
uvicorn app.main:app --reload --port 8000              # API : http://localhost:8000/api/docs

# 3. Frontend (autre terminal)
cd frontend
npm install
npm run dev                                            # http://localhost:5173 (proxy /api -> :8000)
```

Relancer l'import du même fichier ne duplique rien (statut `skipped`). Pour récupérer la dernière
version NOAA : `python -m etl.load --download`.

## Lancement avec Docker Compose

```bash
cp .env.example .env        # puis changer POSTGRES_PASSWORD et DATABASE_URL
docker compose up -d --build
docker compose run --rm etl # import des données
# https://localhost  (certificat local de Caddy à accepter)  —  API : https://localhost/api/docs
```

## Variables d'environnement

| Variable | Rôle | Exemple |
|---|---|---|
| `DATABASE_URL` | Connexion SQLAlchemy (API + ETL) | `postgresql+psycopg://enso:***@db:5432/enso` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Initialisation du conteneur PostgreSQL | `enso` / `enso` / *secret* |
| `CORS_ORIGINS` | Origines autorisées (dev uniquement) | `http://localhost:5173` |
| `LOG_LEVEL` | Niveau de journalisation | `INFO` |
| `DOMAIN`, `ACME_EMAIL` | Nom de domaine et contact Let's Encrypt (Caddy) | `localhost` |

Aucun secret n'est versionné : `.env` est dans `.gitignore`, seul `.env.example` est commité.

## API (extrait)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/v1/health` | État API + base |
| GET | `/api/v1/indices` | Indices disponibles et leur source |
| GET | `/api/v1/indices/ONI/observations?start=1997-01&end=1998-12` | Observations filtrées (mois central, AAAA-MM) |
| GET | `/api/v1/indices/ONI/episodes?phase=el_nino` | Épisodes détectés |
| GET | `/api/v1/indices/ONI/episodes/compare?a=EN-1997-05&b=EN-2014-10` | Comparaison + interprétation |
| GET | `/api/v1/imports` | Historique des imports (traçabilité) |

Codes : `200`, `404` (indice / épisode inconnu), `422` (format invalide, début > fin, épisodes identiques),
`503` (base indisponible). Contrat complet : `docs/openapi.json` ou `/api/docs`.

## Tests

```bash
cd backend && pytest                       # 25 tests (SQLite en mémoire par défaut)
TEST_DATABASE_URL=postgresql+psycopg://enso:enso_dev@localhost:5432/enso_test pytest   # sur PostgreSQL
cd frontend && npm test                    # 4 tests Vitest
```

| Test minimal exigé | Fichier |
|---|---|
| Données : transformation Python (doublons, date invalide…) | `backend/tests/test_transform.py` |
| API : route filtrée par période + entrée invalide | `backend/tests/test_api.py` |
| Frontend : un changement de période actualise la courbe | `frontend/src/components/SeriesExplorer.test.tsx` |

Résultats réellement exécutés le 16/11/2026 : `docs/preuves/pytest.txt`, `docs/preuves/vitest.txt`,
`docs/preuves/lint-backend.txt`. Qualité : `ruff` (Python), `oxlint` + `tsc` strict (TypeScript),
pipeline CI GitHub Actions (`.github/workflows/ci.yml`).

## Méthode scientifique et limites

* Épisode = au moins 5 saisons glissantes consécutives avec ONI ≥ +0,5 °C (El Niño) ou ≤ −0,5 °C
  (La Niña), règle NOAA CPC. Le seuil est appliqué aux valeurs à 2 décimales (NOAA colore sa table
  sur des valeurs arrondies à 0,1 °C : les bornes peuvent différer d'une saison).
* Classe d'intensité selon le pic (faible / modéré / fort / très fort, paliers 0,5 – 1,0 – 1,5 – 2,0 °C) :
  convention de lecture, **pas** une classification officielle NOAA. « Super El Niño » n'est pas utilisé.
* L'épisode 2026 est **en cours** dans les données, et l'épisode La Niña 1950 commence avec la série :
  leurs durées sont des bornes minimales (signalées dans l'interface).
* Aucune prévision climatique.

## Utilisation de l'IA

Outil utilisé : **Claude (Anthropic)**, via l'application Claude, pour :

* la **recherche d'informations** (données NOAA, différence ONI / RONI, version ERSST, seuils El Niño / La Niña) ;
* la **consultation sur les décisions** techniques à prendre et pour combler des manques d'information ;
* la génération d'une **base de code de départ**, que j'ai ensuite reprise, relue, modifiée et testée
  (voir l'historique Git).

Les choix sont justifiés dans le dossier de conception (section 8) ; je suis en mesure de les expliquer
et de modifier le code.

## Licence des données

Les données NOAA sont des données publiques du gouvernement américain. Source à citer :
NOAA Climate Prediction Center, *Oceanic Niño Index (ONI)*.
