import type { Observation } from '../types'

const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']

/** +2,37 °C (signe toujours affiché, virgule décimale française) */
export function formatAnomaly(value: number, unit = '°C'): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}${Math.abs(value).toFixed(2).replace('.', ',')} ${unit}`
}

/** "1997-12" -> "déc. 1997" */
export function formatMonth(period: string): string {
  const [year, month] = period.split('-')
  return `${MONTHS[Number(month) - 1]} ${year}`
}

export function isValidMonth(value: string): boolean {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value)
}

export interface SeriesSummary {
  count: number
  max: Observation
  min: Observation
  mean: number
}

export function summarize(items: Observation[]): SeriesSummary | null {
  if (items.length === 0) return null
  let max = items[0]
  let min = items[0]
  let sum = 0
  for (const item of items) {
    if (item.anomaly > max.anomaly) max = item
    if (item.anomaly < min.anomaly) min = item
    sum += item.anomaly
  }
  return { count: items.length, max, min, mean: Math.round((sum / items.length) * 100) / 100 }
}

/** Graduations régulières tous les 0,5 °C entre min et max (inclus). */
export function halfStepTicks(min: number, max: number): number[] {
  const ticks: number[] = []
  for (let v = Math.floor(min * 2) / 2; v <= max + 1e-9; v += 0.5) ticks.push(Math.round(v * 10) / 10)
  return ticks
}
