import { Package, UserPlus, RotateCcw, History, Edit2, Trash2 } from 'lucide-react';
import { CONDITIONS, getCategoryIcon } from './constants';

export default function InventoryTable({ items, loading, onAssign, onReturn, onHistory, onEdit, onDelete }) {
  if (loading) {
    return <div className="text-center py-12 text-slate-500 dark:text-slate-400">Loading inventory...</div>;
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <Package className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
        <p className="text-slate-600 dark:text-slate-400">No inventory items found</p>
        <p className="text-sm text-slate-500 mt-2">Click &quot;Add Item&quot; to add your first item</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="bg-slate-50 dark:bg-slate-900/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300">Item</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300">Category</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300">Serial No.</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300">Condition</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300">Assigned To</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
            {items.map(item => {
              const CategoryIcon = getCategoryIcon(item.category);
              const conditionStyle = CONDITIONS.find(c => c.id === item.condition)?.color || '';
              return (
                <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50" data-testid={`inventory-row-${item.id}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                        <CategoryIcon size={16} className="text-slate-600 dark:text-slate-400" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white">{item.name}</p>
                        {item.description && (
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[200px]">{item.description}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 capitalize">{item.category}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 font-mono">{item.serial_number || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${conditionStyle}`}>
                      {item.condition}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {item.status === 'assigned' ? (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Assigned</span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">Available</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{item.assigned_to_name || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {item.status === 'available' ? (
                        <button onClick={() => onAssign(item)} className="p-1.5 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded transition-colors" title="Assign to staff" data-testid={`btn-assign-${item.id}`}>
                          <UserPlus size={16} />
                        </button>
                      ) : (
                        <button onClick={() => onReturn(item)} className="p-1.5 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/30 rounded transition-colors" title="Return item" data-testid={`btn-return-${item.id}`}>
                          <RotateCcw size={16} />
                        </button>
                      )}
                      <button onClick={() => onHistory(item)} className="p-1.5 text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors" title="View history" data-testid={`btn-history-${item.id}`}>
                        <History size={16} />
                      </button>
                      <button onClick={() => onEdit(item)} className="p-1.5 text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors" title="Edit" data-testid={`btn-edit-${item.id}`}>
                        <Edit2 size={16} />
                      </button>
                      <button onClick={() => onDelete(item)} disabled={item.status === 'assigned'} className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed" title={item.status === 'assigned' ? 'Return item first' : 'Delete'} data-testid={`btn-delete-${item.id}`}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
