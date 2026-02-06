import { X, Clock, RotateCcw } from 'lucide-react';
import { formatDate } from './constants';

export default function InventoryHistoryModal({ show, item, history, onClose }) {
  if (!show || !item) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-lg max-h-[80vh] overflow-hidden" data-testid="history-modal">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Assignment History</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>
        <div className="p-6">
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 mb-4">
            <p className="font-medium text-slate-900 dark:text-white">{item.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{item.serial_number || 'No serial number'}</p>
          </div>
          {history.length === 0 ? (
            <p className="text-center text-slate-500 dark:text-slate-400 py-4">No assignment history</p>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {history.map((record) => (
                <div key={record.id} className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-slate-900 dark:text-white">{record.staff_name}</span>
                    {record.returned_at ? (
                      <span className="text-xs px-2 py-1 bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 rounded">Returned</span>
                    ) : (
                      <span className="text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded">Current</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1">
                    <p><Clock size={12} className="inline mr-1" /> Assigned: {formatDate(record.assigned_at)}</p>
                    {record.returned_at && (
                      <p><RotateCcw size={12} className="inline mr-1" /> Returned: {formatDate(record.returned_at)} ({record.return_condition})</p>
                    )}
                    {record.notes && <p className="italic">{record.notes}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
