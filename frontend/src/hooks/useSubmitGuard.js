import { useState, useCallback } from 'react';

/**
 * Hook to prevent double-submit on forms.
 * Returns [isSubmitting, wrappedHandler] — the handler auto-guards against rapid double clicks.
 * 
 * Usage:
 *   const [isSubmitting, handleSave] = useSubmitGuard(async () => { await api.post(...) });
 *   <button disabled={isSubmitting} onClick={handleSave}>Save</button>
 */
export function useSubmitGuard(handler, delay = 1000) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const wrappedHandler = useCallback(async (...args) => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await handler(...args);
    } finally {
      setTimeout(() => setIsSubmitting(false), delay);
    }
  }, [handler, isSubmitting, delay]);

  return [isSubmitting, wrappedHandler];
}
