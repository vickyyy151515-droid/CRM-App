import { Filter, Package, Users } from 'lucide-react';

/**
 * Analytics Filter Bar Component
 * Common filter controls for analytics pages
 * Used by AdvancedAnalytics, CustomerRetention, ReportCRM
 */
export default function AnalyticsFilterBar({
  // Period filter
  period,
  setPeriod,
  showPeriod = true,
  periodOptions = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: 'quarter', label: 'This Quarter' },
    { value: 'year', label: 'This Year' },
  ],
  
  // Product filter
  selectedProduct,
  setSelectedProduct,
  products = [],
  showProduct = true,
  
  // Staff filter
  selectedStaff,
  setSelectedStaff,
  staff = [],
  showStaff = true,
  
  // Date range filter
  dateRange,
  setDateRange,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  showDateRange = false,
  
  // Custom slots
  children,
  
  // Styling
  className = '',
  testIdPrefix = 'analytics-filter'
}) {
  return (
    <div className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 mb-6 ${className}`}>
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
          <Filter size={18} />
          <span className="text-sm font-medium">Filters</span>
        </div>
        
        {/* Period Filter */}
        {showPeriod && (
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid={`${testIdPrefix}-period`}
          >
            {periodOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        )}
        
        {/* Date Range Filter */}
        {showDateRange && dateRange === 'custom' && (
          <>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm"
              data-testid={`${testIdPrefix}-start-date`}
            />
            <span className="text-slate-400">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm"
              data-testid={`${testIdPrefix}-end-date`}
            />
          </>
        )}
        
        {/* Product Filter */}
        {showProduct && products.length > 0 && (
          <div className="flex items-center gap-2">
            <Package size={16} className="text-slate-400" />
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid={`${testIdPrefix}-product`}
            >
              <option value="">All Products</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        )}
        
        {/* Staff Filter */}
        {showStaff && staff.length > 0 && (
          <div className="flex items-center gap-2">
            <Users size={16} className="text-slate-400" />
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid={`${testIdPrefix}-staff`}
            >
              <option value="">All Staff</option>
              {staff.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        )}
        
        {/* Custom Controls */}
        {children}
      </div>
    </div>
  );
}
