import { RefreshCw, AlertTriangle, X, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

/**
 * Invalid Records Panel Component
 * Shows staff members with invalid records that need processing
 */
export default function InvalidRecordsPanel({
  invalidRecords,
  showPanel,
  onTogglePanel,
  onOpenReplaceModal,
  onDismissAlerts,
  testIdPrefix = 'invalid'
}) {
  const [expandedStaff, setExpandedStaff] = useState({});

  const toggleExpandStaff = (staffId) => {
    setExpandedStaff(prev => ({
      ...prev,
      [staffId]: !prev[staffId]
    }));
  };

  if (!invalidRecords || invalidRecords.total_invalid === 0) {
    return null;
  }

  return (
    <div className="mb-6 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl overflow-hidden" data-testid={`${testIdPrefix}-panel`}>
      <button
        onClick={onTogglePanel}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-amber-100/50 dark:hover:bg-amber-900/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <AlertTriangle className="text-amber-600 dark:text-amber-400" size={20} />
          <span className="font-semibold text-amber-800 dark:text-amber-200">
            {invalidRecords.total_invalid} Invalid Records from Staff Validation
          </span>
        </div>
        {showPanel ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
      </button>

      {showPanel && (
        <div className="px-6 pb-4">
          <p className="text-sm text-amber-700 dark:text-amber-300 mb-4">
            These records have been marked as invalid by staff and need your attention.
          </p>

          {/* Dismiss orphaned alerts button */}
          {invalidRecords.by_staff?.some(g => g.records?.some(r => r.status !== 'assigned')) && (
            <div className="mb-4 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-300">
                Some invalid alerts are for records that are no longer assigned (recalled/reassigned)
              </span>
              <button
                onClick={onDismissAlerts}
                className="px-3 py-1.5 bg-slate-600 hover:bg-slate-700 text-white text-sm rounded-lg flex items-center gap-1.5"
                data-testid={`${testIdPrefix}-dismiss-btn`}
              >
                <X size={14} />
                Dismiss Orphaned Alerts
              </button>
            </div>
          )}

          {invalidRecords.by_staff?.map((staffGroup) => (
            <div key={staffGroup._id} className="mb-3 bg-white dark:bg-slate-800 rounded-lg border border-amber-200 dark:border-amber-800 overflow-hidden">
              <div className="px-4 py-3 bg-amber-100/50 dark:bg-amber-900/30 flex items-center justify-between">
                <div>
                  <span className="font-medium text-slate-900 dark:text-white">{staffGroup.staff_name || 'Unknown'}</span>
                  <span className="ml-2 text-sm text-amber-600 dark:text-amber-400">
                    ({staffGroup.count || staffGroup.records?.length || 0} invalid)
                  </span>
                </div>
                <button
                  onClick={() => onOpenReplaceModal(
                    staffGroup._id, 
                    staffGroup.staff_name || 'Unknown',
                    staffGroup.count || staffGroup.records?.length || 0
                  )}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                  data-testid={`${testIdPrefix}-replace-${staffGroup._id}`}
                >
                  <RefreshCw size={14} />
                  Ganti dengan Record Baru
                </button>
              </div>
              <div className="max-h-64 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700">
                {(expandedStaff[staffGroup._id] 
                  ? staffGroup.records 
                  : staffGroup.records?.slice(0, 3)
                )?.map((record, idx) => (
                  <div key={record.id || idx} className="p-3 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-slate-900 dark:text-white">
                          {Object.values(record.row_data || {}).slice(0, 2).join(' - ')}
                        </span>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          Database: {record.database_name}
                        </p>
                      </div>
                      <span className="text-xs text-red-600 dark:text-red-400 italic">
                        {record.validation_reason || 'No reason'}
                      </span>
                    </div>
                  </div>
                ))}
                {staffGroup.records?.length > 3 && (
                  <button
                    onClick={() => toggleExpandStaff(staffGroup._id)}
                    className="w-full p-2 text-center text-sm text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors cursor-pointer font-medium"
                  >
                    {expandedStaff[staffGroup._id] 
                      ? '▲ Show less' 
                      : `▼ +${staffGroup.records.length - 3} more records`}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
