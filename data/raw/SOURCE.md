# Provenance du jeu de données ONI

| Champ | Valeur |
|---|---|
| Indice | ONI — Oceanic Niño Index |
| Producteur | NOAA / NWS / Climate Prediction Center (CPC) |
| Fichier | `oni.ascii.txt` |
| URL de téléchargement | https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt |
| Page de documentation | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/ |
| Version | ONI calculé sur ERSST **v6** (moyenne glissante sur 3 mois des anomalies de SST, région Niño 3.4 : 5°N–5°S, 120°–170°W, périodes de référence centrées de 30 ans mises à jour tous les 5 ans) |
| Date d'extraction | 2026-11-16 |
| `Last-Modified` HTTP du fichier | Tue, 03 Nov 2026 19:31:48 GMT |
| SHA-256 | `118c563331335c8649cdc2677e6be7ae89d1259d901345fcddbc2857af280f7f` |
| Taille | 23 050 octets, 921 observations + 1 ligne d'en-tête |
| Couverture | DJF 1950 → ASO 2026 |
| Colonnes | `SEAS` (saison de 3 mois), `YR` (année), `TOTAL` (SST moyenne, °C), `ANOM` (anomalie, °C) |
| Unité | degrés Celsius (°C) |

## Vérification de la version

Le fichier a été comparé automatiquement, valeur par valeur, avec la table publiée sur la page
« ONI (ERSSTv6) » de CPC (valeurs arrondies à 0,1 °C) : 921 saisons comparées, 918 identiques,
3 écarts uniquement dus à l'arrondi d'une valeur se terminant par 5 (DJF 1964 : 0,95 → 0,9 ;
JFM 2021 : −0,85 → −0,9 ; AMJ 2026 : 0,95 → 0,9).

## Points d'attention

* **ONI ≠ RONI.** Depuis la *NWS Public Information Statement 26-05* (2026), CPC utilise le
  RONI (Relative ONI) pour le suivi officiel de l'ENSO. L'ONI reste publié chaque mois et
  constitue l'indice historique de référence pour la région Niño 3.4. Ce projet n'utilise **que l'ONI**.
* Les valeurs récentes peuvent être révisées par NOAA (mise à jour de la période de référence,
  nouvelle version ERSST). L'ETL gère ces révisions (mise à jour + traçabilité de l'import).
* Les dernières saisons (2026) décrivent un épisode **en cours** : il ne doit pas être interprété
  comme un épisode terminé.
* L'année `YR` d'une saison est celle de son mois central : `DJF 1950` = déc. 1949 + janv. + févr. 1950,
  `NDJ 1950` = nov. + déc. 1950 + janv. 1951.
