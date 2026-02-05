import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, RefreshCw, Bell, X, Activity } from 'lucide-react';

/**
 * Proactive Monitoring Alert Component
 * Shows real-time alerts when data inconsistencies are detected
 * Can be placed in admin dashboard or header
 */
export default function ProactiveMonitoringAlert({
  api,
  onViewDetails,
  autoRefreshInterval = 300000, // 5 minutes default
  compact = false,
  className = ''
}) {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const response = await api.get('/data-sync/health-check');
      setHealthData(response.data);
      setLastChecked(new Date());
      setDismissed(false);
    } catch (error) {
      console.error('Health check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    
    // Set up auto-refresh
    if (autoRefreshInterval > 0) {
      const interval = setInterval(checkHealth, autoRefreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefreshInterval]);

  if (dismissed || !healthData) {
    return null;
  }

  const { health_score, issues } = healthData;
  const hasIssues = issues && issues.length > 0;
  const criticalIssues = issues?.filter(i => i.severity === 'critical') || [];
  const warningIssues = issues?.filter(i => i.severity === 'warning') || [];

  // Don't show anything if health is perfect
  if (health_score === 100 && !hasIssues) {
    return null;
  }

  // Compact mode - just show icon with badge
  if (compact) {
    return (
      <div className={`relative ${className}`}>
        <button
          onClick={onViewDetails}
          className={`p-2 rounded-lg transition-colors ${
            criticalIssues.length > 0
              ? 'bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900/50 dark:text-red-400'
              : warningIssues.length > 0
              ? 'bg-amber-100 text-amber-600 hover:bg-amber-200 dark:bg-amber-900/50 dark:text-amber-400'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-400'
          }`}
          title={`Data Health: ${health_score}% - ${issues?.length || 0} issues`}
          data-testid="health-alert-compact"
        >
          <Activity size={20} />
          {hasIssues && (
            <span className={`absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center text-xs font-bold rounded-full ${
              criticalIssues.length > 0
                ? 'bg-red-500 text-white'
                : 'bg-amber-500 text-white'
            }`}>
              {issues.length}
            </span>
          )}
        </button>
      </div>
    );
  }

  // Full alert banner
  return (
    <div
      className={`rounded-xl border p-4 ${
        criticalIssues.length > 0
          ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
          : warningIssues.length > 0
          ? 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800'
          : 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
      } ${className}`}
      data-testid="health-alert-banner"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`p-2 rounded-lg ${
            criticalIssues.length > 0
              ? 'bg-red-100 dark:bg-red-900/50'
              : warningIssues.length > 0
              ? 'bg-amber-100 dark:bg-amber-900/50'
              : 'bg-blue-100 dark:bg-blue-900/50'
          }`}>
            {criticalIssues.length > 0 ? (
              <AlertTriangle className="text-red-600 dark:text-red-400" size={24} />
            ) : warningIssues.length > 0 ? (
              <Bell className="text-amber-600 dark:text-amber-400" size={24} />
            ) : (
              <Activity className="text-blue-600 dark:text-blue-400" size={24} />
            )}
          </div>

          {/* Content */}
          <div>
            <h4 className={`font-semibold ${
              criticalIssues.length > 0
                ? 'text-red-800 dark:text-red-300'
                : warningIssues.length > 0
                ? 'text-amber-800 dark:text-amber-300'
                : 'text-blue-800 dark:text-blue-300'
            }`}>
              {criticalIssues.length > 0
                ? `🚨 Critical: ${criticalIssues.length} Data Issue${criticalIssues.length > 1 ? 's' : ''} Detected`
                : warningIssues.length > 0
                ? `⚠️ Warning: ${warningIssues.length} Data Issue${warningIssues.length > 1 ? 's' : ''} Found`
                : `Data Health: ${health_score}%`
              }
            </h4>
            
            {/* Issue summary */}
            <div className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              {criticalIssues.length > 0 && (
                <ul className="list-disc list-inside">
                  {criticalIssues.slice(0, 3).map((issue, idx) => (
                    <li key={idx}>{issue.message}</li>
                  ))}
                  {criticalIssues.length > 3 && (
                    <li>...and {criticalIssues.length - 3} more</li>
                  )}
                </ul>
              )}
              {criticalIssues.length === 0 && warningIssues.length > 0 && (
                <ul className="list-disc list-inside">
                  {warningIssues.slice(0, 3).map((issue, idx) => (
                    <li key={idx}>{issue.message}</li>
                  ))}
                  {warningIssues.length > 3 && (
                    <li>...and {warningIssues.length - 3} more</li>
                  )}
                </ul>
              )}
            </div>

            {/* Actions */}
            <div className="mt-3 flex items-center gap-3">
              <button
                onClick={onViewDetails}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  criticalIssues.length > 0
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : warningIssues.length > 0
                    ? 'bg-amber-600 hover:bg-amber-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
                data-testid="view-details-btn"
              >
                View Details & Fix
              </button>
              
              <button
                onClick={checkHealth}
                disabled={loading}
                className="px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-1"
                data-testid="refresh-health-btn"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
              
              {lastChecked && (
                <span className="text-xs text-slate-500 dark:text-slate-500">
                  Last checked: {lastChecked.toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Dismiss button */}
        <button
          onClick={() => setDismissed(true)}
          className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          title="Dismiss until next check"
          data-testid="dismiss-alert-btn"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
