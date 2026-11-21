import { useState } from 'react'
import { fetchObservations } from '../api/client'
import { useAsync } from '../hooks/useAsync'
import type { Period } from '../types'
import { formatAnomaly, formatMonth, summarize } from '../utils/format'
import { DataTable } from './DataTable'
import { IndexChart } from './IndexChart'
import { PeriodFilter } from './PeriodFilter'
import { StatusMessage } from './StatusMessage'

const DEFAULT_PERIOD: Period = { start: '1980-01', end: '2026-09' }

/** Fonctionnalité MVP n°3 : courbe interactive + filtre de période. */
export function SeriesExplorer() {
  const [period, setPeriod] = useState<Period>(DEFAULT_PERIOD)
  const query = useAsync((signal) => fetchObservations(period, signal), [period.start, period.end])
  const data = query.data
  const summary = data ? summarize(data.items) : null

  return (
    <section aria-labelledby="explorer-title" className="card">
      <h2 id="explorer-title">Explorer l'indice RONI</h2>
      <PeriodFilter value={period} onChange={setPeriod} />
      <StatusMessage status={query.status} error={query.error} onRetry={query.reload}
        loadingLabel="Chargement des observations…" />

      {data && (
        <div aria-busy={query.status === 'loading'}>
          <p className="summary" aria-live="polite" data-testid="series-summary">
            {summary ? (
              <>
                <strong>{summary.count} saisons</strong> de {formatMonth(data.items[0].period)} à{' '}
                {formatMonth(data.items[data.items.length - 1].period)} · maximum{' '}
                {formatAnomaly(summary.max.anomaly, data.unit)} ({summary.max.season} {summary.max.year}) · minimum{' '}
                {formatAnomaly(summary.min.anomaly, data.unit)} ({summary.min.season} {summary.min.year})
              </>
            ) : (
              'Aucune observation sur cette période.'
            )}
          </p>
          {data.items.length > 0 && (
            <>
              <IndexChart
                items={data.items}
                unit={data.unit}
                title={`Anomalie de température de surface – région Niño 3.4 (${data.unit})`}
                description={`Indice ${data.index} : moyenne glissante sur 3 mois. Les zones colorées indiquent les seuils NOAA de ±0,5 ${data.unit}.`}
              />
              <DataTable items={data.items} unit={data.unit} />
            </>
          )}
          <p className="source-note">
            Source : <a href={data.source.documentation_url} target="_blank" rel="noreferrer">{data.source.provider}</a>
            {' '}— {data.source.name}, {data.source.version}.
            {data.last_import && (
              <> Fichier extrait le {data.last_import.extracted_at}
                {data.last_import.file_last_modified && ` (publié par NOAA le ${data.last_import.file_last_modified})`}.</>
            )}
          </p>
        </div>
      )}
    </section>
  )
}
