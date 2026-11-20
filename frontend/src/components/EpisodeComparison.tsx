import { useId, useMemo, useState, type FormEvent } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchComparison, fetchEpisodes } from '../api/client'
import { useAsync } from '../hooks/useAsync'
import type { Comparison, Episode } from '../types'
import { formatAnomaly, halfStepTicks } from '../utils/format'
import { StatusMessage } from './StatusMessage'

const DEFAULT_PAIR = { a: 'EN-1997-05', b: 'EN-2014-10' }

function EpisodeSelect({ id, label, value, episodes, onChange }: {
  id: string; label: string; value: string; episodes: Episode[]; onChange: (v: string) => void
}) {
  const groups: [string, Episode[]][] = [
    ['El Niño', episodes.filter((e) => e.phase === 'el_nino')],
    ['La Niña', episodes.filter((e) => e.phase === 'la_nina')],
  ]
  return (
    <label htmlFor={id}>
      {label}
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {groups.map(([name, list]) => (
          <optgroup key={name} label={name}>
            {list.map((e) => (
              <option key={e.id} value={e.id}>
                {e.label} — pic {formatAnomaly(e.peak_anomaly)}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  )
}

function MetricsTable({ data }: { data: Comparison }) {
  const a = data.a.episode
  const b = data.b.episode
  const rows: [string, string, string][] = [
    ['Période (saisons)', `${a.start_season} → ${a.end_season}`, `${b.start_season} → ${b.end_season}`],
    ['Durée au-delà du seuil', `${a.n_seasons} saisons`, `${b.n_seasons} saisons`],
    ['Pic', `${formatAnomaly(a.peak_anomaly, data.unit)} (${a.peak_season})`, `${formatAnomaly(b.peak_anomaly, data.unit)} (${b.peak_season})`],
    ['Anomalie moyenne', formatAnomaly(a.mean_anomaly, data.unit), formatAnomaly(b.mean_anomaly, data.unit)],
    ['Anomalie cumulée', formatAnomaly(a.cumulative_anomaly, data.unit), formatAnomaly(b.cumulative_anomaly, data.unit)],
    ['Classe indicative (pic)', a.intensity, b.intensity],
    ['Statut', a.ongoing ? 'en cours' : a.truncated_start ? 'début avant 1950 possible' : 'terminé',
      b.ongoing ? 'en cours' : b.truncated_start ? 'début avant 1950 possible' : 'terminé'],
  ]
  return (
    <div className="table-scroll">
      <table className="metrics">
        <caption>Indicateurs calculés sur l'ONI (seuil ±{data.threshold.toString().replace('.', ',')} {data.unit}, au moins {data.min_seasons} saisons)</caption>
        <thead>
          <tr><th scope="col">Indicateur</th><th scope="col">{a.label}</th><th scope="col">{b.label}</th></tr>
        </thead>
        <tbody>
          {rows.map(([name, va, vb]) => (
            <tr key={name}><th scope="row">{name}</th><td>{va}</td><td>{vb}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OverlayChart({ data }: { data: Comparison }) {
  // Les deux épisodes sont alignés sur leur 1re saison au-dessus du seuil (rang 1, 2, 3…).
  const rows = useMemo(() => {
    const n = Math.max(data.a.values.length, data.b.values.length)
    return Array.from({ length: n }, (_, i) => ({
      rank: i + 1,
      a: data.a.values[i]?.anomaly ?? null,
      b: data.b.values[i]?.anomaly ?? null,
    }))
  }, [data])
  const all = [...data.a.values, ...data.b.values].map((v) => v.anomaly)
  const ticks = halfStepTicks(Math.min(0, ...all), Math.ceil(Math.max(0, ...all) * 2) / 2)
  return (
    <figure className="chart" aria-labelledby="overlay-title">
      <figcaption>
        <h4 id="overlay-title">Évolution comparée depuis le début de chaque épisode</h4>
      </figcaption>
      <div className="chart-area chart-small">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 10, right: 16, bottom: 28, left: 8 }} accessibilityLayer>
            <CartesianGrid stroke="#d9dde3" strokeDasharray="2 4" />
            <XAxis dataKey="rank" tick={{ fill: '#3c4450', fontSize: 12 }}
              label={{ value: 'Saison depuis le début de l’épisode', position: 'insideBottom', offset: -18, fill: '#3c4450', fontSize: 12 }} />
            <YAxis domain={[ticks[0], ticks[ticks.length - 1]]} ticks={ticks} interval={0} tickFormatter={(v: number) => v.toFixed(1).replace('.', ',')} tick={{ fill: '#3c4450', fontSize: 12 }} width={48} />
            <ReferenceLine y={0} stroke="#5b6573" />
            <Tooltip formatter={(v) => formatAnomaly(Number(v), data.unit)} labelFormatter={(r) => `Saison n° ${r}`} />
            <Legend verticalAlign="top" />
            {/* Couleur ET motif de trait différents : lisible sans distinguer les couleurs */}
            <Line dataKey="a" name={data.a.episode.label} stroke="#b3261e" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} connectNulls={false} />
            <Line dataKey="b" name={data.b.episode.label} stroke="#1b4f8a" strokeWidth={2} strokeDasharray="7 4" dot={{ r: 3 }} isAnimationActive={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

/** Fonctionnalité MVP n°4 : comparaison de deux épisodes historiques + interprétation prudente. */
export function EpisodeComparison() {
  const id = useId()
  const episodes = useAsync((signal) => fetchEpisodes(signal), [])
  const [draft, setDraft] = useState(DEFAULT_PAIR)
  const [pair, setPair] = useState(DEFAULT_PAIR)
  const [formError, setFormError] = useState<string | null>(null)
  const comparison = useAsync((signal) => fetchComparison(pair.a, pair.b, signal), [pair.a, pair.b])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (draft.a === draft.b) {
      setFormError('Choisissez deux épisodes différents.')
      return
    }
    setFormError(null)
    setPair(draft)
  }

  return (
    <section aria-labelledby="compare-title" className="card">
      <h2 id="compare-title">Comparer deux épisodes historiques</h2>
      <p className="muted">
        Épisode = au moins 5 saisons glissantes consécutives avec ONI ≥ +0,5 °C (El Niño) ou ≤ −0,5 °C (La Niña).
      </p>
      <StatusMessage status={episodes.status} error={episodes.error} onRetry={episodes.reload}
        loadingLabel="Chargement des épisodes…" />
      {episodes.data && (
        <form className="compare-form" onSubmit={submit}>
          <EpisodeSelect id={`${id}-a`} label="Épisode A" value={draft.a} episodes={episodes.data}
            onChange={(a) => setDraft({ ...draft, a })} />
          <EpisodeSelect id={`${id}-b`} label="Épisode B" value={draft.b} episodes={episodes.data}
            onChange={(b) => setDraft({ ...draft, b })} />
          <button type="submit" className="btn btn-primary">Comparer</button>
          {formError && <p className="field-error" role="alert">{formError}</p>}
        </form>
      )}

      <StatusMessage status={comparison.status} error={comparison.error} onRetry={comparison.reload}
        loadingLabel="Calcul de la comparaison…" />
      {comparison.data && (
        <div className="comparison" aria-live="polite">
          <MetricsTable data={comparison.data} />
          <OverlayChart data={comparison.data} />
          <h3>Interprétation</h3>
          <ul className="findings">
            {comparison.data.findings.map((f) => <li key={f}>{f}</li>)}
          </ul>
          <h3>Limites de cette comparaison</h3>
          <ul className="limits">
            {comparison.data.limits.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </div>
      )}
    </section>
  )
}
