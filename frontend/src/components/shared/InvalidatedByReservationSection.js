import { useState } from 'react';
import { ChevronDown, ChevronUp, UserX, Package, AlertTriangle } from 'lucide-react';

/**
 * Invalidated By Reservation Section
 * Shows records that were taken from the staff because another staff reserved the customer
 * Used by MyAssignedRecords, StaffDBBonanza, StaffMemberWDCRM
 */
export default function InvalidatedByReservationSection({
  records = [],
  showSection,
  setShowSection,
  title = 'Records Taken by Reservation',
  emptyMessage = 'No records were taken from you',
  testIdPrefix = 'invalidated'
}) {
  if (records.length === 0) {
    return null;
  }

  return (
    <div 
      className="mb-6 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl overflow-hidden"
      data-testid={`${testIdPrefix}-section`}
    >
      <button
        onClick={() => setShowSection(!showSection)}
        className="w-full p-4 flex items-center justify-between hover:bg-amber-100/50 dark:hover:bg-amber-900/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
            <UserX className="text-amber-600 dark:text-amber-400" size={20} />
          </div>
          <div className="text-left">
            <h4 className="font-semibold text-amber-800 dark:text-amber-300">
              {records.length} {title}
            </h4>
            <p className="text-sm text-amber-600 dark:text-amber-400">
              These records were assigned to you but another staff has reserved the customer
            </p>
          </div>
        </div>
        {showSection ? (
          <ChevronUp className="text-amber-600 dark:text-amber-400" />
        ) : (
          <ChevronDown className="text-amber-600 dark:text-amber-400" />
        )}
      </button>

      {showSection && (
        <div className="border-t border-amber-200 dark:border-amber-800 p-4">
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {records.map((record, idx) => (
              <div
                key={record.id || idx}
                className="p-3 bg-white dark:bg-slate-800 rounded-lg border border-amber-200 dark:border-amber-700"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Customer Info */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-slate-900 dark:text-white">
                        {record.customer_name || record.row_data?.name || record.row_data?.customer_name || 'Unknown Customer'}
                      </span>
                      {record.customer_id && (
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          ({record.customer_id})
                        </span>
                      )}
                    </div>
                    
                    {/* Product Info */}
                    {record.product_name && (
                      <div className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400 mb-1">
                        <Package size={14} />
                        <span>{record.product_name}</span>
                      </div>
                    )}
                    
                    {/* Database Info */}
                    {record.database_name && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Database: {record.database_name}
                      </p>
                    )}
                    
                    {/* Row Data Preview */}
                    {record.row_data && (
                      <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        {Object.entries(record.row_data).slice(0, 3).map(([key, value]) => (
                          <span key={key} className="mr-3">
                            <span className="font-medium">{key}:</span> {value}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* Reason Badge */}
                  <div className="flex flex-col items-end gap-1">
                    <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs rounded-full">
                      Reserved by other
                    </span>
                    {record.invalid_reason && (
                      <span className="text-xs text-amber-600 dark:text-amber-400 text-right max-w-[150px] truncate" title={record.invalid_reason}>
                        {record.invalid_reason}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {records.length === 0 && (
            <div className="text-center py-4 text-amber-600 dark:text-amber-400">
              {emptyMessage}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
