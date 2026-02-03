import { Database, ChevronDown, ChevronUp, Users, Trash2, Edit2, Package } from 'lucide-react';

/**
 * Database Card Component
 * Expandable card showing database info and stats
 */
export default function DatabaseCard({
  database,
  isExpanded,
  onToggleExpand,
  onDelete,
  onEditProduct,
  products,
  editingProduct,
  setEditingProduct,
  newProductId,
  setNewProductId,
  onSaveProduct,
  reservedNames = [],
  testIdPrefix = 'db'
}) {
  // Get reserved count for this database's product
  const reservedCount = database.excluded_count || 0;

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
      {/* Header - clickable to expand */}
      <div
        onClick={() => onToggleExpand(database.id)}
        className="p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900/30 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="text-indigo-600 dark:text-indigo-400" size={24} />
            <div>
              <h4 className="font-semibold text-slate-900 dark:text-white">{database.name}</h4>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {database.total_records} records total
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Product Badge */}
            {editingProduct === database.id ? (
              <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                <select
                  value={newProductId}
                  onChange={(e) => setNewProductId(e.target.value)}
                  className="h-8 px-2 text-sm rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                >
                  <option value="">No Product</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                <button
                  onClick={(e) => { e.stopPropagation(); onSaveProduct(database.id); }}
                  className="px-2 py-1 bg-indigo-600 text-white text-sm rounded"
                >
                  Save
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setEditingProduct(null); }}
                  className="px-2 py-1 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-sm rounded"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 text-sm rounded-lg flex items-center gap-1">
                  <Package size={14} />
                  {database.product_name || 'No Product'}
                </span>
                <button
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    onEditProduct(database.id, database.product_id);
                  }}
                  className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                  data-testid={`${testIdPrefix}-edit-product-${database.id}`}
                >
                  <Edit2 size={14} />
                </button>
              </div>
            )}

            {/* Stats */}
            <div className="flex items-center gap-3 text-sm">
              <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 rounded-lg">
                {database.available_count} available
              </span>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-lg">
                {database.assigned_count} assigned
              </span>
              {database.archived_count > 0 && (
                <span className="px-2 py-1 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded-lg">
                  {database.archived_count} archived
                </span>
              )}
              {reservedCount > 0 && (
                <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 rounded-lg">
                  {reservedCount} excluded
                </span>
              )}
            </div>

            {/* Delete button */}
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(database.id); }}
              className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
              data-testid={`${testIdPrefix}-delete-${database.id}`}
            >
              <Trash2 size={18} />
            </button>

            {/* Expand icon */}
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </div>
        </div>
      </div>
    </div>
  );
}
