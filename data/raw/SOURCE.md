# Provenance du jeu de données RONI

| Champ | Valeur |
|---|---|
| Indice | RONI — Relative Oceanic Niño Index |
| Producteur | NOAA / NWS / Climate Prediction Center (CPC) |
| Fichier | `RONI.ascii.txt` |
| URL de téléchargement | https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt |
| Page de documentation | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/ |
| Version | RONI calculé sur ERSST **v6**, période de référence **1991–2020** |
| Définition | Moyenne glissante sur 3 mois des anomalies de SST de la région Niño 3.4 (5°N–5°S, 120°–170°W), moins l'anomalie moyenne de la bande tropicale (20°N–20°S), puis ajustée pour avoir la même variance que l'indice Niño 3.4 d'origine |
| Statut | Indice utilisé par NOAA pour le suivi **officiel** de l'ENSO depuis la *NWS Public Information Statement 26-05* (2026) |
| Date d'extraction | 2026-11-21 |
| `Last-Modified` HTTP du fichier | Tue, 03 Nov 2026 19:31:48 GMT |
| SHA-256 | `1297887f581b6190e459cbbf8bdec9a703ff65c1a229e2de4dd94285254f35c8` |
| Taille | 14 752 octets, 921 observations + 1 ligne d'en-tête |
| Couverture | DJF 1950 → ASO 2026 |
| Colonnes | `SEAS` (saison de 3 mois), `YR` (année), `ANOM` (anomalie relative, °C) |
| Unité | degrés Celsius (°C) |

## Vérification de la version

Le fichier a été comparé automatiquement, valeur par valeur, avec la table publiée sur la page RONI
(ERSSTv6) de CPC (valeurs arrondies à 0,1 °C) : 921 saisons comparées, 914 identiques, 7 écarts
uniquement dus à l'arrondi d'une valeur se terminant par 5 (ex. FMA 1984 : −0,45 → −0,5 ;
OND 2022 : −1,05 → −1,1).

## Points d'attention

* **RONI ≠ ONI.** L'ONI est l'anomalie brute de Niño 3.4 ; le RONI retire l'anomalie moyenne des
  tropiques, donc l'effet du réchauffement global de l'océan. Ce projet n'utilise **que le RONI**.
* Contrairement au fichier ONI, le fichier RONI ne contient **pas** de SST moyenne (`TOTAL`) :
  la colonne `mean_sst` est vide en base.
* Les valeurs récentes peuvent être révisées par NOAA jusqu'à deux mois après leur publication
  (filtre haute fréquence d'ERSST v6). L'ETL gère ces révisions (mise à jour + traçabilité).
* Au dernier point disponible (ASO 2026), 4 saisons consécutives dépassent +0,5 °C (MJJ → ASO 2026) :
  ce n'est **pas encore** un épisode El Niño au sens de la règle des 5 saisons.
* L'année `YR` d'une saison est celle de son mois central : `DJF 1950` = déc. 1949 + janv. + févr. 1950,
  `NDJ 1950` = nov. + déc. 1950 + janv. 1951.
