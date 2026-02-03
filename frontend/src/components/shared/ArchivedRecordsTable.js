import { Undo2, Archive } from 'lucide-react';

/**
 * Archived Records Table Component
 * Shows archived/invalid records with restore functionality
 */
export default function ArchivedRecordsTable({
  archivedRecords,
  loading,
  onRestore,
  formatDate,
  testIdPrefix = 'archived'
}) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-8 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-slate-500">Loading archived records...</p>
      </div>
    );
  }

  if (!archivedRecords || archivedRecords.total === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-8 text-center">
        <Archive className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">No Archived Records</h3>
        <p className="text-slate-500 dark:text-slate-400">
          Records marked as invalid will appear here after processing.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h3 className="font-semibold text-slate-900 dark:text-white">
          Archived Invalid Records ({archivedRecords.total})
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          These records were marked as invalid and archived. You can restore them to the available pool.
        </p>
      </div>

      <div className="divide-y divide-slate-100 dark:divide-slate-700 max-h-[600px] overflow-y-auto">
        {archivedRecords.records?.map((record) => (
          <div key={record.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-900/30">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-900 dark:text-white">
                  {Object.values(record.row_data || {}).slice(0, 3).join(' - ')}
                </div>
                <div className="mt-1 flex flex-wrap gap-2 text-sm">
                  <span className="text-slate-500 dark:text-slate-400">
                    Database: <span className="text-slate-700 dark:text-slate-300">{record.database_name || 'Unknown'}</span>
                  </span>
                  <span className="text-slate-500 dark:text-slate-400">
                    Staff: <span className="text-slate-700 dark:text-slate-300">{record.assigned_to_name || 'Unknown'}</span>
                  </span>
                  <span className="text-slate-500 dark:text-slate-400">
                    Archived: <span className="text-slate-700 dark:text-slate-300">{formatDate(record.archived_at)}</span>
                  </span>
                </div>
                {record.validation_reason && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400 italic">
                    Reason: {record.validation_reason}
                  </p>
                )}
              </div>
              <button
                onClick={() => onRestore(record.id)}
                className="ml-4 px-3 py-1.5 bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-900/50 dark:hover:bg-emerald-900 text-emerald-700 dark:text-emerald-300 text-sm rounded-lg flex items-center gap-1.5 transition-colors"
                data-testid={`${testIdPrefix}-restore-${record.id}`}
              >
                <Undo2 size={14} />
                Restore
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
