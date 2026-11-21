import type { Observation } from '../types'
import { formatAnomaly, formatMonth } from '../utils/format'

interface Props {
  items: Observation[]
  unit: string
}

/** Alternative textuelle au graphique (accessibilité) : repliée par défaut. */
export function DataTable({ items, unit }: Props) {
  // Le RONI ne publie pas de SST moyenne : la colonne n'apparaît que si la donnée existe.
  const hasSst = items.some((o) => o.mean_sst !== null)
  return (
    <details className="data-table">
      <summary>Afficher les {items.length} valeurs sous forme de tableau</summary>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Tableau des valeurs RONI">
        <table>
          <caption className="sr-only">Valeurs RONI de la période sélectionnée</caption>
          <thead>
            <tr>
              <th scope="col">Saison</th>
              <th scope="col">Mois central</th>
              <th scope="col">Anomalie ({unit})</th>
              {hasSst && <th scope="col">SST moyenne ({unit})</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.period}>
                <th scope="row">{o.season} {o.year}</th>
                <td>{formatMonth(o.period)}</td>
                <td className="num">{formatAnomaly(o.anomaly, unit)}</td>
                {hasSst && <td className="num">{o.mean_sst?.toFixed(2).replace('.', ',') ?? '—'}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
