import { AlertTriangle, ChevronDown, ChevronUp, RefreshCw, X } from 'lucide-react';

/**
 * Invalid Records Alert Banner Component
 * Displays a collapsible alert with invalid records grouped by staff
 * Used by both AdminDBBonanza and AdminMemberWDCRM
 */
export default function InvalidRecordsAlertBanner({
  invalidRecords,
  showInvalidPanel,
  setShowInvalidPanel,
  expandedInvalidStaff,
  toggleExpandInvalidStaff,
  onDismissAlerts,
  onOpenReplaceModal,
  processing,
  testIdPrefix = 'invalid'
}) {
  if (!invalidRecords || invalidRecords.total_invalid === 0) {
    return null;
  }

  return (
    <div 
      className="mb-6 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl overflow-hidden" 
      data-testid={`${testIdPrefix}-records-alert`}
    >
      <button
        onClick={() => setShowInvalidPanel(!showInvalidPanel)}
        className="w-full p-4 flex items-center justify-between hover:bg-red-100/50 dark:hover:bg-red-900/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
            <AlertTriangle className="text-red-600 dark:text-red-400" size={20} />
          </div>
          <div className="text-left">
            <h4 className="font-semibold text-red-800 dark:text-red-300">
              {invalidRecords.total_invalid} Record Tidak Valid
            </h4>
            <p className="text-sm text-red-600 dark:text-red-400">
              Staff telah menandai record ini sebagai tidak valid. Klik untuk detail dan tindakan.
            </p>
          </div>
        </div>
        {showInvalidPanel ? (
          <ChevronUp className="text-red-600 dark:text-red-400" />
        ) : (
          <ChevronDown className="text-red-600 dark:text-red-400" />
        )}
      </button>
      
      {showInvalidPanel && (
        <div className="border-t border-red-200 dark:border-red-800 p-4 space-y-4">
          {/* Dismiss All Button */}
          <div className="flex justify-end">
            <button
              onClick={onDismissAlerts}
              className="px-3 py-1.5 bg-slate-600 hover:bg-slate-700 text-white text-sm rounded-lg flex items-center gap-1.5"
              data-testid={`${testIdPrefix}-dismiss-alerts`}
            >
              <X size={14} />
              Dismiss All Invalid Alerts
            </button>
          </div>
          
          {invalidRecords.by_staff?.map((staffGroup) => (
            <div 
              key={staffGroup._id} 
              className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden"
            >
              <div className="p-3 bg-slate-50 dark:bg-slate-900/50 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {staffGroup.staff_name || 'Unknown Staff'}
                  </span>
                  <span className="ml-2 px-2 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
                    {staffGroup.count} record tidak valid
                  </span>
                </div>
                <button
                  onClick={() => onOpenReplaceModal(staffGroup._id, staffGroup.staff_name, staffGroup.count)}
                  disabled={processing}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                  data-testid={`${testIdPrefix}-replace-${staffGroup._id}`}
                >
                  <RefreshCw size={14} />
                  Ganti dengan Record Baru
                </button>
              </div>
              
              <div className="max-h-64 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700">
                {(expandedInvalidStaff[staffGroup._id] 
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
                    onClick={() => toggleExpandInvalidStaff(staffGroup._id)}
                    className="w-full p-2 text-center text-sm text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors cursor-pointer font-medium"
                  >
                    {expandedInvalidStaff[staffGroup._id] 
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
