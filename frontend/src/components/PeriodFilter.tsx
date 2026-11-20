import { useId, useState, type FormEvent } from 'react'
import type { Period } from '../types'
import { isValidMonth } from '../utils/format'

export const DATA_MIN = '1950-01'
export const DATA_MAX = '2026-09'

const PRESETS: { label: string; period: Period }[] = [
  { label: 'Toute la série', period: { start: DATA_MIN, end: DATA_MAX } },
  { label: '1982–1984', period: { start: '1982-01', end: '1984-12' } },
  { label: '1997–1999', period: { start: '1997-01', end: '1999-12' } },
  { label: '2014–2017', period: { start: '2014-01', end: '2017-12' } },
  { label: '2023–2024', period: { start: '2023-01', end: '2024-12' } },
  { label: 'Depuis 2020', period: { start: '2020-01', end: DATA_MAX } },
]

interface Props {
  value: Period
  onChange: (period: Period) => void
}

/** Filtre de période : saisie AAAA-MM validée côté client (et revalidée par l'API). */
export function PeriodFilter({ value, onChange }: Props) {
  const [draft, setDraft] = useState<Period>(value)
  const [error, setError] = useState<string | null>(null)
  const id = useId()

  function validate(period: Period): string | null {
    if (!isValidMonth(period.start) || !isValidMonth(period.end)) return 'Format attendu : AAAA-MM.'
    if (period.start > period.end) return 'Le début doit précéder la fin.'
    if (period.start < DATA_MIN || period.end > DATA_MAX) {
      return `Les données couvrent ${DATA_MIN} à ${DATA_MAX}.`
    }
    return null
  }

  function apply(period: Period) {
    const problem = validate(period)
    setError(problem)
    if (!problem) onChange(period)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    apply(draft)
  }

  return (
    <form className="period-filter" onSubmit={handleSubmit} aria-describedby={error ? `${id}-err` : undefined}>
      <fieldset>
        <legend>Période affichée</legend>
        <div className="period-inputs">
          <label htmlFor={`${id}-start`}>
            Début
            <input
              id={`${id}-start`}
              type="month"
              min={DATA_MIN}
              max={DATA_MAX}
              value={draft.start}
              onChange={(e) => setDraft({ ...draft, start: e.target.value })}
              aria-invalid={error ? true : undefined}
              required
            />
          </label>
          <label htmlFor={`${id}-end`}>
            Fin
            <input
              id={`${id}-end`}
              type="month"
              min={DATA_MIN}
              max={DATA_MAX}
              value={draft.end}
              onChange={(e) => setDraft({ ...draft, end: e.target.value })}
              aria-invalid={error ? true : undefined}
              required
            />
          </label>
          <button type="submit" className="btn btn-primary">
            Appliquer
          </button>
        </div>
        {error && (
          <p id={`${id}-err`} className="field-error" role="alert">
            {error}
          </p>
        )}
        <div className="presets" role="group" aria-label="Périodes prédéfinies">
          {PRESETS.map((preset) => {
            const active = preset.period.start === value.start && preset.period.end === value.end
            return (
              <button
                key={preset.label}
                type="button"
                className="btn btn-chip"
                aria-pressed={active}
                onClick={() => {
                  setDraft(preset.period)
                  apply(preset.period)
                }}
              >
                {preset.label}
              </button>
            )
          })}
        </div>
      </fieldset>
    </form>
  )
}
