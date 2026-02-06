import { Filter } from 'lucide-react';

/**
 * Omset Filter Panel Component
 * Provides date range, product, and staff filters for OMSET-related pages
 * Used by AdminOmsetCRM
 */
export default function OmsetFilterPanel({
  dateRange,
  setDateRange,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  products = [],
  selectedProduct,
  setSelectedProduct,
  staffList = [],
  selectedStaff,
  setSelectedStaff,
  showStaffFilter = true,
  testIdPrefix = 'omset-filter'
}) {
  const dateRangeOptions = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'last7', label: 'Last 7 Days' },
    { value: 'last30', label: 'Last 30 Days' },
    { value: 'thisMonth', label: 'This Month' },
    { value: 'all', label: 'All Time' },
    { value: 'custom', label: 'Custom Range' },
  ];

  return (
    <div 
      className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm mb-6"
      data-testid={`${testIdPrefix}-panel`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Filter className="text-indigo-600" size={18} />
        <h3 className="font-medium text-slate-900">Filters</h3>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Date Range */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Date Range</label>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid={`${testIdPrefix}-date-range`}
          >
            {dateRangeOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Custom Date Range */}
        {dateRange === 'custom' && (
          <>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                data-testid={`${testIdPrefix}-start-date`}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                data-testid={`${testIdPrefix}-end-date`}
              />
            </div>
          </>
        )}

        {/* Product Filter */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Product</label>
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid={`${testIdPrefix}-product`}
          >
            <option value="">All Products</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Staff Filter */}
        {showStaffFilter && (
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Staff</label>
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid={`${testIdPrefix}-staff`}
            >
              <option value="">All Staff</option>
              {staffList.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
