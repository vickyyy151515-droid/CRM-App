import { DollarSign, UserPlus, RefreshCw, TrendingUp } from 'lucide-react';

/**
 * Summary Stats Cards Component
 * Displays key metrics in card format
 * Used by AdminOmsetCRM, DailySummary, and analytics pages
 */
export default function SummaryStatsCards({
  stats = {},
  loading = false,
  testIdPrefix = 'stats'
}) {
  // Default card definitions - can be customized via props
  const defaultCards = [
    {
      key: 'total_omset',
      label: 'Total OMSET',
      icon: DollarSign,
      color: 'emerald',
      format: 'currency',
      value: stats.total_omset || 0
    },
    {
      key: 'ndp_count',
      label: 'NDP (New Deposit)',
      icon: UserPlus,
      color: 'blue',
      format: 'number',
      value: stats.ndp_count || stats.total_ndp || 0
    },
    {
      key: 'rdp_count',
      label: 'RDP (Repeat Deposit)',
      icon: RefreshCw,
      color: 'purple',
      format: 'number',
      value: stats.rdp_count || stats.total_rdp || 0
    },
    {
      key: 'total_customers',
      label: 'Total Customers',
      icon: TrendingUp,
      color: 'amber',
      format: 'number',
      value: stats.total_customers || (stats.ndp_count || 0) + (stats.rdp_count || 0)
    }
  ];

  const colorClasses = {
    emerald: 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400',
    blue: 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400',
    purple: 'bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400',
    amber: 'bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400',
    indigo: 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400',
    red: 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400',
  };

  const formatValue = (value, format) => {
    if (loading) return '...';
    if (format === 'currency') {
      return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(value);
    }
    return new Intl.NumberFormat('id-ID').format(value);
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid={`${testIdPrefix}-cards`}>
      {defaultCards.map(card => {
        const Icon = card.icon;
        return (
          <div
            key={card.key}
            className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4"
            data-testid={`${testIdPrefix}-${card.key}`}
          >
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClasses[card.color]}`}>
                <Icon size={24} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-500 dark:text-slate-400 truncate">{card.label}</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white truncate">
                  {formatValue(card.value, card.format)}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Custom Stats Card for flexible usage
 */
export function StatsCard({
  label,
  value,
  icon: Icon,
  color = 'indigo',
  format = 'number',
  loading = false,
  testId
}) {
  const colorClasses = {
    emerald: 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400',
    blue: 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400',
    purple: 'bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400',
    amber: 'bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400',
    indigo: 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400',
    red: 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400',
  };

  const formatValue = () => {
    if (loading) return '...';
    if (format === 'currency') {
      return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(value);
    }
    if (format === 'percent') {
      return `${value.toFixed(1)}%`;
    }
    return new Intl.NumberFormat('id-ID').format(value);
  };

  return (
    <div
      className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4"
      data-testid={testId}
    >
      <div className="flex items-center gap-3">
        {Icon && (
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClasses[color]}`}>
            <Icon size={24} />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-500 dark:text-slate-400 truncate">{label}</p>
          <p className="text-xl font-bold text-slate-900 dark:text-white truncate">
            {formatValue()}
          </p>
        </div>
      </div>
    </div>
  );
}
