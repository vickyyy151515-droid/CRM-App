import { Filter, RefreshCw } from 'lucide-react';

/**
 * Analytics Period Filter Component
 * Provides period selection and product/staff filters for analytics pages
 * Used by AdvancedAnalytics, CustomerRetention, and similar pages
 */
export default function AnalyticsPeriodFilter({
  period,
  setPeriod,
  products = [],
  selectedProduct,
  setSelectedProduct,
  staff = [],
  selectedStaff,
  setSelectedStaff,
  showStaffFilter = true,
  onRefresh,
  loading = false,
  extraActions,
  testIdPrefix = 'analytics-filter'
}) {
  const periodOptions = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'week', label: 'Last 7 Days' },
    { value: 'month', label: 'Last 30 Days' },
    { value: 'quarter', label: 'Last 90 Days' },
    { value: 'year', label: 'Last Year' },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={`${testIdPrefix}-container`}>
      {/* Period Filter */}
      <select
        value={period}
        onChange={(e) => setPeriod(e.target.value)}
        className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        data-testid={`${testIdPrefix}-period`}
      >
        {periodOptions.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>

      {/* Product Filter */}
      <select
        value={selectedProduct}
        onChange={(e) => setSelectedProduct(e.target.value)}
        className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        data-testid={`${testIdPrefix}-product`}
      >
        <option value="">All Products</option>
        {products.map(p => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>

      {/* Staff Filter */}
      {showStaffFilter && (
        <select
          value={selectedStaff}
          onChange={(e) => setSelectedStaff(e.target.value)}
          className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid={`${testIdPrefix}-staff`}
        >
          <option value="">All Staff</option>
          {staff.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      )}

      {/* Refresh Button */}
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={loading}
          className="h-10 px-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
          title="Refresh data"
          data-testid={`${testIdPrefix}-refresh`}
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
        </button>
      )}

      {/* Extra Actions (e.g., Widget Settings) */}
      {extraActions}
    </div>
  );
}
