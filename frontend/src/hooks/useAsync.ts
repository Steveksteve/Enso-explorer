import { useCallback, useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'idle'; data: null; error: null }
  | { status: 'loading'; data: T | null; error: null }
  | { status: 'success'; data: T; error: null }
  | { status: 'error'; data: T | null; error: string }

/**
 * Exécute une requête asynchrone quand `deps` change.
 * - annule la requête précédente (AbortController) pour éviter les réponses dans le désordre ;
 * - expose `reload` pour le bouton « Réessayer ».
 * `enabled = false` : ne lance rien (ex. comparaison tant que deux épisodes ne sont pas choisis).
 */
export function useAsync<T>(
  task: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
  enabled = true,
): AsyncState<T> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle', data: null, error: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    setState((prev) => ({ status: 'loading', data: prev.data, error: null }))
    task(controller.signal)
      .then((data) => setState({ status: 'success', data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof Error ? error.message : 'Erreur inconnue'
        setState((prev) => ({ status: 'error', data: prev.data, error: message }))
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps explicites fournies par l'appelant
  }, [...deps, attempt, enabled])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { ...state, reload }
}
