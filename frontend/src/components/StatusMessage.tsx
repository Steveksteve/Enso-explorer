interface Props {
  status: 'idle' | 'loading' | 'success' | 'error'
  error: string | null
  onRetry?: () => void
  loadingLabel?: string
}

/** États de chargement et d'erreur, annoncés aux lecteurs d'écran. */
export function StatusMessage({ status, error, onRetry, loadingLabel = 'Chargement…' }: Props) {
  if (status === 'loading') {
    return (
      <p className="status status-loading" role="status">
        {loadingLabel}
      </p>
    )
  }
  if (status === 'error') {
    return (
      <div className="status status-error" role="alert">
        <p>
          <strong>Erreur :</strong> {error}
        </p>
        {onRetry && (
          <button type="button" className="btn" onClick={onRetry}>
            Réessayer
          </button>
        )}
      </div>
    )
  }
  return null
}
