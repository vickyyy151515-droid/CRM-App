import { Package } from 'lucide-react';

/**
 * Product Filter Component
 * Dropdown to filter databases/records by product
 * Used by both AdminDBBonanza and AdminMemberWDCRM
 */
export default function ProductFilter({
  filterProduct,
  setFilterProduct,
  products,
  testIdPrefix = 'filter'
}) {
  return (
    <div className="mb-6 flex items-center gap-4">
      <div className="flex items-center gap-2">
        <Package size={18} className="text-slate-500" />
        <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Filter by Product:
        </span>
      </div>
      <select
        value={filterProduct}
        onChange={(e) => setFilterProduct(e.target.value)}
        className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[200px]"
        data-testid={`${testIdPrefix}-product`}
      >
        <option value="">All Products</option>
        {products.map(p => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
    </div>
  );
}
