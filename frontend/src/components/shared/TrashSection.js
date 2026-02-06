import { Trash2, ChevronUp, ChevronDown, AlertTriangle, RefreshCw, RotateCcw } from 'lucide-react';

/**
 * Format currency with thousand separators
 */
const formatCurrency = (num) => {
  if (!num && num !== 0) return '0';
  return Math.round(num).toLocaleString('id-ID');
};

/**
 * Trash Section Component
 * Reusable component for displaying and managing deleted records
 * Used by AdminOmsetCRM and similar pages
 */
export default function TrashSection({
  showTrash,
  setShowTrash,
  trashRecords = [],
  onRefresh,
  onRestore,
  onPermanentDelete,
  restoringId = null,
  renderRecordInfo,
  title = 'Recently Deleted',
  testIdPrefix = 'trash'
}) {
  return (
    <div className="mt-6" data-testid={`${testIdPrefix}-section`}>
      {/* Toggle Button */}
      <button
        onClick={() => setShowTrash(!showTrash)}
        className="flex items-center gap-2 text-sm text-slate-600 hover:text-indigo-600 transition-colors"
        data-testid={`${testIdPrefix}-toggle`}
      >
        <Trash2 size={16} />
        {title} ({trashRecords.length})
        {showTrash ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      {/* Trash Content */}
      {showTrash && (
        <div className="mt-3 bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-amber-100 border-b border-amber-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="text-amber-600" size={18} />
              <span className="font-medium text-amber-800">Trash - {title}</span>
            </div>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="text-amber-700 hover:text-amber-900"
                title="Refresh"
                data-testid={`${testIdPrefix}-refresh`}
              >
                <RefreshCw size={16} />
              </button>
            )}
          </div>
          
          {/* Records List */}
          {trashRecords.length === 0 ? (
            <div className="p-6 text-center text-amber-700">
              No deleted records
            </div>
          ) : (
            <div className="divide-y divide-amber-200">
              {trashRecords.map((record) => (
                <div 
                  key={record.id} 
                  className="px-4 py-3 flex items-center justify-between hover:bg-amber-100/50"
                  data-testid={`${testIdPrefix}-record-${record.id}`}
                >
                  {/* Record Info - Custom render or default */}
                  <div className="flex-1 min-w-0">
                    {renderRecordInfo ? (
                      renderRecordInfo(record)
                    ) : (
                      <DefaultRecordInfo record={record} />
                    )}
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2 ml-4">
                    {onRestore && (
                      <button
                        onClick={() => onRestore(record.id, record)}
                        disabled={restoringId === record.id}
                        className="flex items-center gap-1 px-3 py-1.5 bg-emerald-100 hover:bg-emerald-200 text-emerald-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                        title="Restore this record"
                        data-testid={`${testIdPrefix}-restore-${record.id}`}
                      >
                        {restoringId === record.id ? (
                          <RefreshCw size={14} className="animate-spin" />
                        ) : (
                          <RotateCcw size={14} />
                        )}
                        Restore
                      </button>
                    )}
                    {onPermanentDelete && (
                      <button
                        onClick={() => onPermanentDelete(record.id)}
                        className="p-1.5 text-red-500 hover:bg-red-100 rounded transition-colors"
                        title="Permanently delete"
                        data-testid={`${testIdPrefix}-delete-${record.id}`}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Default Record Info display (for OMSET records)
 */
function DefaultRecordInfo({ record }) {
  return (
    <>
      <div className="flex items-center gap-3">
        <span className="font-medium text-amber-900">{record.customer_id}</span>
        <span className="text-xs px-2 py-0.5 bg-amber-200 text-amber-800 rounded">
          {record.product_name}
        </span>
      </div>
      <div className="text-sm text-amber-700 mt-1">
        <span>{record.staff_name}</span>
        <span className="mx-2">•</span>
        <span>Rp {formatCurrency(record.depo_total || 0)}</span>
        <span className="mx-2">•</span>
        <span>{record.record_date}</span>
      </div>
      {record.deleted_at && (
        <div className="text-xs text-amber-600 mt-1">
          Deleted by {record.deleted_by_name} on {new Date(record.deleted_at).toLocaleString('id-ID')}
        </div>
      )}
    </>
  );
}

export { DefaultRecordInfo };
