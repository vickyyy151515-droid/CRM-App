import { X } from 'lucide-react';
import { CONDITIONS } from './constants';

export default function InventoryReturnModal({ show, item, returnData, setReturnData, saving, onSubmit, onClose }) {
  if (!show || !item) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-md" data-testid="return-modal">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Return Item</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>
        <form onSubmit={onSubmit} className="p-6 space-y-4">
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
            <p className="text-sm text-slate-500 dark:text-slate-400">Item</p>
            <p className="font-medium text-slate-900 dark:text-white">{item.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Currently with: {item.assigned_to_name}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Return Condition</label>
            <select value={returnData.condition} onChange={(e) => setReturnData({ ...returnData, condition: e.target.value })} className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white" data-testid="select-return-condition">
              {CONDITIONS.map(c => (<option key={c.id} value={c.id}>{c.name}</option>))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Notes</label>
            <textarea value={returnData.notes} onChange={(e) => setReturnData({ ...returnData, notes: e.target.value })} className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white" rows={2} placeholder="Return notes (damage, issues, etc.)..." data-testid="input-return-notes" />
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={onClose} className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50" data-testid="btn-confirm-return">
              {saving ? 'Returning...' : 'Return Item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
