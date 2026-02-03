/**
 * Replace Modal Component
 * Modal for processing invalid records and assigning replacements
 */
export default function ReplaceModal({
  show,
  onClose,
  staffName,
  invalidCount,
  replaceQuantity,
  onReplaceQuantityChange,
  onProcess,
  processing
}) {
  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md shadow-xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Ganti Record untuk {staffName}
        </h3>
        <div className="space-y-4">
          <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <strong>{invalidCount}</strong> record tidak valid akan dipindahkan ke &quot;Database Invalid&quot;
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Berapa record baru yang ingin ditugaskan?
            </label>
            <input
              type="number"
              min="0"
              max="100"
              value={replaceQuantity}
              onChange={(e) => onReplaceQuantityChange(parseInt(e.target.value) || 0)}
              className="w-full h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              data-testid="replace-quantity-input"
            />
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Masukkan 0 jika tidak ingin menugaskan record baru
            </p>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Batal
          </button>
          <button
            onClick={onProcess}
            disabled={processing}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
            data-testid="replace-process-btn"
          >
            {processing ? 'Memproses...' : 'Proses'}
          </button>
        </div>
      </div>
    </div>
  );
}
