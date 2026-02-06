/**
 * Widget Card Component
 * Reusable container for analytics widgets/charts
 * Used by AdvancedAnalytics, CustomerRetention, and dashboards
 */
export function WidgetCard({
  title,
  subtitle,
  icon: Icon,
  iconColor = 'text-indigo-600',
  children,
  loading = false,
  emptyMessage,
  emptyIcon: EmptyIcon,
  className = '',
  headerAction,
  testId
}) {
  return (
    <div 
      className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm ${className}`}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          {Icon && <Icon size={20} className={iconColor} />}
          {title}
        </h3>
        {headerAction}
      </div>
      
      {subtitle && (
        <p className="text-sm text-slate-500 dark:text-slate-400 -mt-2 mb-4">{subtitle}</p>
      )}
      
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : children ? (
        children
      ) : emptyMessage ? (
        <div className="h-64 flex items-center justify-center text-slate-500 dark:text-slate-400">
          <div className="text-center">
            {EmptyIcon && <EmptyIcon size={48} className="mx-auto mb-2 opacity-30" />}
            <p>{emptyMessage}</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Metric Card Component
 * Reusable card for displaying single metrics/KPIs
 */
export function MetricCard({
  title,
  value,
  icon: Icon,
  iconColor = 'text-blue-600',
  gradient = 'from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30',
  borderColor = 'border-blue-200 dark:border-blue-800',
  textColor = 'text-blue-700 dark:text-blue-400',
  subtitle,
  className = '',
  testId
}) {
  return (
    <div 
      className={`bg-gradient-to-br ${gradient} border ${borderColor} rounded-xl p-5 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className={iconColor} size={20} />}
        <span className={`text-sm font-medium ${textColor}`}>{title}</span>
      </div>
      <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      {subtitle && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>
      )}
    </div>
  );
}

/**
 * Tab Navigation Component
 * Reusable tab buttons for analytics views
 */
export function ViewTabs({
  tabs,
  activeTab,
  setActiveTab,
  testIdPrefix = 'view-tabs'
}) {
  return (
    <div className="flex gap-2 mb-6 flex-wrap" data-testid={`${testIdPrefix}-container`}>
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === tab.id 
              ? tab.activeClass || 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
          }`}
          data-testid={`${testIdPrefix}-${tab.id}`}
        >
          {tab.icon && <tab.icon size={16} />}
          {tab.label}
          {tab.badge !== undefined && tab.badge > 0 && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${tab.badgeClass || 'bg-indigo-500 text-white'}`}>
              {tab.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

/**
 * Metric Cards Grid
 * Grid layout for multiple metric cards
 */
export function MetricsGrid({
  metrics,
  columns = 4,
  className = ''
}) {
  const colClass = {
    2: 'grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
    5: 'grid-cols-2 md:grid-cols-5',
    6: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-6'
  }[columns] || 'grid-cols-2 md:grid-cols-4';

  return (
    <div className={`grid ${colClass} gap-4 ${className}`}>
      {metrics.map((metric, idx) => (
        <MetricCard key={metric.id || idx} {...metric} />
      ))}
    </div>
  );
}

export default WidgetCard;
