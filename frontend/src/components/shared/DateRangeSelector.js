import { Calendar, ChevronDown } from 'lucide-react';

/**
 * Date Range Selector Component
 * Provides preset date ranges and custom date selection
 * Used by AdminOmsetCRM and analytics pages
 */
export default function DateRangeSelector({
  dateRange,
  setDateRange,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  showCustomDates = true,
  onRefresh,
  loading = false,
  testIdPrefix = 'date-range'
}) {
  const presets = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: 'custom', label: 'Custom Range' },
  ];

  return (
    <div className="flex flex-wrap items-center gap-3" data-testid={`${testIdPrefix}-selector`}>
      {/* Date Range Presets */}
      <div className="flex items-center gap-2">
        <Calendar size={18} className="text-slate-500" />
        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid={`${testIdPrefix}-preset`}
        >
          {presets.map(preset => (
            <option key={preset.value} value={preset.value}>{preset.label}</option>
          ))}
        </select>
      </div>

      {/* Custom Date Inputs */}
      {showCustomDates && dateRange === 'custom' && (
        <>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm"
            data-testid={`${testIdPrefix}-start`}
          />
          <span className="text-slate-500">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm"
            data-testid={`${testIdPrefix}-end`}
          />
        </>
      )}

      {/* Refresh Button */}
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={loading}
          className="h-10 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-2 text-sm font-medium disabled:opacity-50 transition-colors"
          data-testid={`${testIdPrefix}-refresh`}
        >
          {loading ? 'Loading...' : 'Apply'}
        </button>
      )}
    </div>
  );
}
