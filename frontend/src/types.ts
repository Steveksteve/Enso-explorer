// Types du contrat de l'API (miroir des schémas Pydantic côté backend).

export type Phase = 'el_nino' | 'la_nina'

export interface Source {
  code: string
  name: string
  provider: string
  url: string
  documentation_url: string
  version: string
}

export interface ImportInfo {
  id: number
  file_name: string
  file_sha256: string
  file_last_modified: string | null
  extracted_at: string
  status: string
  rows_inserted: number
  rows_updated: number
}

export interface Observation {
  season: string
  year: number
  period: string // AAAA-MM (mois central de la saison)
  anomaly: number
  mean_sst: number | null
}

export interface ObservationsResponse {
  index: string
  unit: string
  source: Source
  last_import: ImportInfo | null
  start: string | null
  end: string | null
  count: number
  items: Observation[]
}

export interface Episode {
  id: string
  phase: Phase
  label: string
  start: string
  end: string
  start_season: string
  end_season: string
  n_seasons: number
  peak_anomaly: number
  peak_season: string
  mean_anomaly: number
  cumulative_anomaly: number
  intensity: string
  ongoing: boolean
  truncated_start: boolean
}

export interface EpisodeSeries {
  episode: Episode
  values: Observation[]
}

export interface Comparison {
  index: string
  unit: string
  threshold: number
  min_seasons: number
  a: EpisodeSeries
  b: EpisodeSeries
  findings: string[]
  limits: string[]
}

export interface Period {
  start: string // AAAA-MM
  end: string // AAAA-MM
}
