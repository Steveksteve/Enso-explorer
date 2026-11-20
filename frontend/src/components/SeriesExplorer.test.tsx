/**
 * TEST FRONTEND (minimal obligatoire n°3) : un changement de période actualise la courbe et les valeurs.
 * Le fetch est simulé, mais il répond avec les VRAIES valeurs du fichier NOAA du dépôt,
 * filtrées comme le fait l'API (mois central compris entre start et end).
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Observation } from '../types'
import { SeriesExplorer } from './SeriesExplorer'

const SEASONS = ['DJF', 'JFM', 'FMA', 'MAM', 'AMJ', 'MJJ', 'JJA', 'JAS', 'ASO', 'SON', 'OND', 'NDJ']
const ALL: Observation[] = readFileSync(resolve(__dirname, '../../../data/raw/oni.ascii.txt'), 'utf8')
  .trim().split('\n').slice(1)
  .map((line) => {
    const [season, year, total, anom] = line.trim().split(/\s+/)
    const month = String(SEASONS.indexOf(season) + 1).padStart(2, '0')
    return { season, year: Number(year), period: `${year}-${month}`, anomaly: Number(anom), mean_sst: Number(total) }
  })

function fakeApi(url: string): Response {
  const params = new URL(url, 'http://test').searchParams
  const start = params.get('start') ?? '0000-00'
  const end = params.get('end') ?? '9999-99'
  const items = ALL.filter((o) => o.period >= start && o.period <= end)
  const body = {
    index: 'ONI', unit: '°C', start, end, count: items.length, items, last_import: null,
    source: { code: 'NOAA_CPC_ONI', name: 'Oceanic Niño Index (ONI)', provider: 'NOAA CPC',
      url: 'https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt',
      documentation_url: 'https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/', version: 'ERSST v6' },
  }
  return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn(async (input: RequestInfo | URL) => fakeApi(String(input)))
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

describe('SeriesExplorer', () => {
  it('actualise la courbe et les valeurs quand la période change', async () => {
    render(<SeriesExplorer />)
    const summary = await screen.findByTestId('series-summary')
    await waitFor(() => expect(summary).toHaveTextContent('561 saisons'))
    expect(screen.getByTestId('oni-chart')).toHaveAttribute('data-points', '561')

    fireEvent.change(screen.getByLabelText('Début'), { target: { value: '1997-01' } })
    fireEvent.change(screen.getByLabelText('Fin'), { target: { value: '1998-12' } })
    await userEvent.click(screen.getByRole('button', { name: 'Appliquer' }))

    // 1) la bonne requête est envoyée à l'API
    await waitFor(() => expect(String(fetchMock.mock.lastCall?.[0])).toContain('start=1997-01&end=1998-12'))
    // 2) le résumé et la courbe reflètent la nouvelle période (vraies valeurs NOAA)
    await waitFor(() => expect(screen.getByTestId('series-summary')).toHaveTextContent('24 saisons'))
    expect(screen.getByTestId('series-summary')).toHaveTextContent('maximum +2,37 °C (NDJ 1997)')
    expect(screen.getByTestId('oni-chart')).toHaveAttribute('data-points', '24')
    // 3) le tableau accessible contient bien 24 lignes de données
    const table = screen.getByRole('region', { name: 'Tableau des valeurs ONI' })
    expect(within(table).getAllByRole('row')).toHaveLength(25) // + ligne d'en-tête
  })

  it('applique un préréglage de période au clic', async () => {
    render(<SeriesExplorer />)
    await screen.findByTestId('series-summary')
    await userEvent.click(screen.getByRole('button', { name: '2014–2017' }))
    await waitFor(() => expect(screen.getByTestId('series-summary')).toHaveTextContent('48 saisons'))
    expect(screen.getByTestId('series-summary')).toHaveTextContent('maximum +2,59 °C (NDJ 2015)')
    expect(screen.getByRole('button', { name: '2014–2017' })).toHaveAttribute('aria-pressed', 'true')
  })

  it("refuse une période incohérente sans appeler l'API", async () => {
    render(<SeriesExplorer />)
    await screen.findByTestId('series-summary')
    const callsBefore = fetchMock.mock.calls.length
    fireEvent.change(screen.getByLabelText('Début'), { target: { value: '2000-01' } })
    fireEvent.change(screen.getByLabelText('Fin'), { target: { value: '1990-01' } })
    await userEvent.click(screen.getByRole('button', { name: 'Appliquer' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Le début doit précéder la fin.')
    expect(fetchMock.mock.calls.length).toBe(callsBefore)
  })

  it("affiche une erreur et permet de réessayer si l'API échoue", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Base de données indisponible' }), { status: 503 }))
    render(<SeriesExplorer />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Base de données indisponible')
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    await waitFor(() => expect(screen.getByTestId('series-summary')).toHaveTextContent('561 saisons'))
  })
})
