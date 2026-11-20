import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Observation } from '../types'
import { formatAnomaly, formatMonth, halfStepTicks } from '../utils/format'

interface Props {
  items: Observation[]
  unit: string
  title: string
  description: string
}

const COLORS = { line: '#1b4f8a', warm: '#b3261e', cold: '#1565c0' }

function yearTicks(items: Observation[]): string[] {
  // Une graduation par année (ou tous les 5/10 ans sur les longues périodes) pour rester lisible.
  const january = items.filter((o) => o.period.endsWith('-01')).map((o) => o.period)
  const step = january.length > 40 ? 10 : january.length > 12 ? 5 : 1
  return january.filter((p) => Number(p.slice(0, 4)) % step === 0)
}

/**
 * Courbe ONI. Accessibilité :
 *  - <figure> + titre et description reliés par aria-labelledby / aria-describedby ;
 *  - accessibilityLayer de Recharts : navigation au clavier (flèches) dans le graphique ;
 *  - zones El Niño / La Niña distinguées par la couleur ET par des libellés texte ;
 *  - tableau de données équivalent fourni à côté (composant DataTable).
 */
export function OniChart({ items, unit, title, description }: Props) {
  const values = items.map((o) => o.anomaly)
  const bound = Math.max(2.5, ...values.map((v) => Math.ceil(Math.abs(v) * 2) / 2))
  const yTicks = halfStepTicks(-bound, bound)

  return (
    <figure className="chart" aria-labelledby="chart-title" aria-describedby="chart-desc">
      <figcaption>
        <h3 id="chart-title">{title}</h3>
        <p id="chart-desc" className="muted">
          {description}
        </p>
      </figcaption>
      <div className="chart-area" data-testid="oni-chart" data-points={items.length}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={items} margin={{ top: 10, right: 16, bottom: 28, left: 8 }} accessibilityLayer>
            <ReferenceArea y1={0.5} y2={bound} fill={COLORS.warm} fillOpacity={0.07} ifOverflow="hidden" />
            <ReferenceArea y1={-bound} y2={-0.5} fill={COLORS.cold} fillOpacity={0.07} ifOverflow="hidden" />
            <CartesianGrid stroke="#d9dde3" strokeDasharray="2 4" />
            <XAxis
              dataKey="period"
              ticks={yearTicks(items)}
              tickFormatter={(p: string) => p.slice(0, 4)}
              tick={{ fill: '#3c4450', fontSize: 12 }}
              label={{ value: 'Mois central de la saison de 3 mois', position: 'insideBottom', offset: -18, fill: '#3c4450', fontSize: 12 }}
            />
            <YAxis
              domain={[-bound, bound]}
              ticks={yTicks}
              interval={0}
              tickFormatter={(v: number) => v.toFixed(1).replace('.', ',')}
              tick={{ fill: '#3c4450', fontSize: 12 }}
              width={56}
              label={{ value: `Anomalie ONI (${unit})`, angle: -90, position: 'insideLeft', offset: 4, fill: '#3c4450', fontSize: 12, style: { textAnchor: 'middle' } }}
            />
            <ReferenceLine y={0} stroke="#5b6573" />
            <ReferenceLine y={0.5} stroke={COLORS.warm} strokeDasharray="6 4" />
            <ReferenceLine y={-0.5} stroke={COLORS.cold} strokeDasharray="6 4" />
            <Tooltip
              formatter={(value) => [formatAnomaly(Number(value), unit), 'Anomalie ONI']}
              labelFormatter={(label, payload) => {
                const obs = payload?.[0]?.payload as Observation | undefined
                return obs ? `${obs.season} ${obs.year} (centre : ${formatMonth(obs.period)})` : String(label)
              }}
            />
            <Line
              type="monotone"
              dataKey="anomaly"
              name="Anomalie ONI"
              stroke={COLORS.line}
              strokeWidth={2}
              dot={items.length <= 48}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <ul className="legend" aria-label="Légende">
        <li><span className="swatch swatch-line" aria-hidden="true" /> Anomalie ONI ({unit})</li>
        <li><span className="swatch swatch-warm" aria-hidden="true" /> Zone El Niño (≥ +0,5 {unit}, seuil en tirets rouges)</li>
        <li><span className="swatch swatch-cold" aria-hidden="true" /> Zone La Niña (≤ −0,5 {unit}, seuil en tirets bleus)</li>
      </ul>
    </figure>
  )
}
