// Client HTTP unique : toutes les requêtes passent ici (URL de base, erreurs, annulation).
import type { Comparison, Episode, ObservationsResponse, Period } from '../types'

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''
const INDEX = 'ONI'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function getJson<T>(path: string, params: Record<string, string>, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams(params).toString()
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}${query ? `?${query}` : ''}`, {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, "Impossible de joindre l'API. Vérifiez votre connexion ou réessayez.")
  }
  if (!response.ok) {
    let detail = `Erreur ${response.status}`
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
        detail = body.detail
      } else if (response.status === 422) {
        detail = 'Paramètres invalides.'
      }
    } catch {
      /* corps non JSON : on garde le message générique */
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

export function fetchObservations(period: Period, signal?: AbortSignal) {
  return getJson<ObservationsResponse>(
    `/api/v1/indices/${INDEX}/observations`,
    { start: period.start, end: period.end },
    signal,
  )
}

export function fetchEpisodes(signal?: AbortSignal) {
  return getJson<Episode[]>(`/api/v1/indices/${INDEX}/episodes`, {}, signal)
}

export function fetchComparison(a: string, b: string, signal?: AbortSignal) {
  return getJson<Comparison>(`/api/v1/indices/${INDEX}/episodes/compare`, { a, b }, signal)
}
