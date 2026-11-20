import type { Observation } from '../types'
import { formatAnomaly, formatMonth } from '../utils/format'

interface Props {
  items: Observation[]
  unit: string
}

/** Alternative textuelle au graphique (accessibilité) : repliée par défaut. */
export function DataTable({ items, unit }: Props) {
  return (
    <details className="data-table">
      <summary>Afficher les {items.length} valeurs sous forme de tableau</summary>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Tableau des valeurs ONI">
        <table>
          <caption className="sr-only">Valeurs ONI de la période sélectionnée</caption>
          <thead>
            <tr>
              <th scope="col">Saison</th>
              <th scope="col">Mois central</th>
              <th scope="col">Anomalie ({unit})</th>
              <th scope="col">SST moyenne ({unit})</th>
            </tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.period}>
                <th scope="row">{o.season} {o.year}</th>
                <td>{formatMonth(o.period)}</td>
                <td className="num">{formatAnomaly(o.anomaly, unit)}</td>
                <td className="num">{o.mean_sst?.toFixed(2).replace('.', ',') ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
