import { EpisodeComparison } from './components/EpisodeComparison'
import { SeriesExplorer } from './components/SeriesExplorer'

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main">Aller au contenu</a>
      <header className="site-header">
        <div className="container">
          <h1>ENSO Explorer</h1>
          <p className="tagline">
            Explorer les épisodes El Niño et La Niña à partir de l'indice NOAA RONI (Relative Oceanic Niño Index)
          </p>
        </div>
      </header>
      <main id="main" className="container" tabIndex={-1}>
        <SeriesExplorer />
        <EpisodeComparison />
      </main>
      <footer className="site-footer">
        <div className="container">
          <p>
            Données : NOAA Climate Prediction Center, indice RONI (ERSST v6). Application pédagogique —
            aucune prévision climatique. Les valeurs les plus récentes peuvent être révisées par NOAA.
          </p>
        </div>
      </footer>
    </>
  )
}
