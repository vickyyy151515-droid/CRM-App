import { X, Plus, Layers, Copy, Trash2, CheckCircle } from 'lucide-react';
import { CATEGORIES, CONDITIONS } from './constants';

export default function InventoryBulkAddModal({ show, bulkItems, staff, saving, onUpdateItem, onAddRow, onRemoveRow, onDuplicateRow, onApplyStaffToAll, onSubmit, onClose }) {
  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden" data-testid="bulk-add-modal">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Layers size={20} /> Bulk Add Inventory Items
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Add multiple items and assign to staff at once</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="px-6 py-3 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700 flex items-center gap-4 flex-wrap">
            <span className="text-sm font-medium text-slate-600 dark:text-slate-300">Quick Actions:</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Assign all to:</span>
              <select onChange={(e) => onApplyStaffToAll(e.target.value)} className="px-3 py-1.5 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white" data-testid="bulk-assign-all-staff">
                <option value="">Select staff...</option>
                {staff.map(s => (<option key={s.id} value={s.id}>{s.name}</option>))}
              </select>
            </div>
            <button type="button" onClick={onAddRow} className="px-3 py-1.5 text-sm bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900 flex items-center gap-1" data-testid="btn-add-bulk-row">
              <Plus size={14} /> Add Row
            </button>
          </div>
          <div className="p-6 max-h-[50vh] overflow-y-auto">
            <div className="space-y-3">
              <div className="grid grid-cols-12 gap-2 text-xs font-semibold text-slate-600 dark:text-slate-400 px-2">
                <div className="col-span-3">Item Name *</div>
                <div className="col-span-2">Category</div>
                <div className="col-span-2">Serial No.</div>
                <div className="col-span-1">Condition</div>
                <div className="col-span-3">Assign to Staff</div>
                <div className="col-span-1">Actions</div>
              </div>
              {bulkItems.map((item, index) => (
                <div key={index} className="grid grid-cols-12 gap-2 items-center bg-slate-50 dark:bg-slate-700/50 p-2 rounded-lg" data-testid={`bulk-row-${index}`}>
                  <div className="col-span-3">
                    <input type="text" value={item.name} onChange={(e) => onUpdateItem(index, 'name', e.target.value)} placeholder="e.g., MacBook Pro" className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white" data-testid={`bulk-name-${index}`} />
                  </div>
                  <div className="col-span-2">
                    <select value={item.category} onChange={(e) => onUpdateItem(index, 'category', e.target.value)} className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white" data-testid={`bulk-category-${index}`}>
                      {CATEGORIES.map(c => (<option key={c.id} value={c.id}>{c.name}</option>))}
                    </select>
                  </div>
                  <div className="col-span-2">
                    <input type="text" value={item.serial_number} onChange={(e) => onUpdateItem(index, 'serial_number', e.target.value)} placeholder="SN-123" className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono" data-testid={`bulk-serial-${index}`} />
                  </div>
                  <div className="col-span-1">
                    <select value={item.condition} onChange={(e) => onUpdateItem(index, 'condition', e.target.value)} className="w-full px-2 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white" data-testid={`bulk-condition-${index}`}>
                      {CONDITIONS.map(c => (<option key={c.id} value={c.id}>{c.name}</option>))}
                    </select>
                  </div>
                  <div className="col-span-3">
                    <select value={item.staff_id} onChange={(e) => onUpdateItem(index, 'staff_id', e.target.value)} className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white" data-testid={`bulk-staff-${index}`}>
                      <option value="">Not assigned</option>
                      {staff.map(s => (<option key={s.id} value={s.id}>{s.name}</option>))}
                    </select>
                  </div>
                  <div className="col-span-1 flex items-center justify-center gap-1">
                    <button type="button" onClick={() => onDuplicateRow(index)} className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded transition-colors" title="Duplicate row" data-testid={`bulk-duplicate-${index}`}>
                      <Copy size={14} />
                    </button>
                    <button type="button" onClick={() => onRemoveRow(index)} disabled={bulkItems.length === 1} className="p-1.5 text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed" title="Remove row" data-testid={`bulk-remove-${index}`}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50 flex items-center justify-between">
            <div className="text-sm text-slate-600 dark:text-slate-400">
              <span className="font-medium">{bulkItems.filter(i => i.name.trim()).length}</span> items ready to add
              {bulkItems.filter(i => i.staff_id).length > 0 && (
                <span className="ml-2">• <span className="font-medium">{bulkItems.filter(i => i.staff_id).length}</span> will be assigned</span>
              )}
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition-colors">Cancel</button>
              <button type="submit" disabled={saving || bulkItems.filter(i => i.name.trim()).length === 0} className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors flex items-center gap-2" data-testid="btn-submit-bulk">
                {saving ? 'Adding...' : (<><CheckCircle size={16} /> Add {bulkItems.filter(i => i.name.trim()).length} Items</>)}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
