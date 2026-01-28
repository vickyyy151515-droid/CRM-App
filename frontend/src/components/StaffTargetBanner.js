import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { Target, TrendingUp, Flame, AlertTriangle, AlertOctagon, Trophy, CheckCircle, XCircle } from 'lucide-react';

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export default function StaffTargetBanner() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  const fetchProgress = useCallback(async () => {
    try {
      const response = await api.get('/staff/target-progress');
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch target progress:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProgress();
    // Refresh every 5 minutes
    const interval = setInterval(fetchProgress, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchProgress]);

  if (loading) {
    return (
      <div className="bg-slate-100 dark:bg-slate-800/50 rounded-lg p-3 mb-4 animate-pulse">
        <div className="h-12 bg-slate-200 dark:bg-slate-700 rounded"></div>
      </div>
    );
  }

  if (!data) return null;

  // Determine banner color based on warning level and today's status
  const getBannerStyle = () => {
    if (data.warning_level === 3) {
      // Very serious - 2 consecutive months failed
      return 'bg-gradient-to-r from-red-600 to-red-700 text-white border-red-800';
    }
    if (data.warning_level === 2) {
      // Hard warning - failed last month
      return 'bg-gradient-to-r from-orange-500 to-orange-600 text-white border-orange-700';
    }
    if (data.today_target_reached) {
      // Today's target reached
      return 'bg-gradient-to-r from-emerald-500 to-emerald-600 text-white border-emerald-700';
    }
    if (data.warning_level === 1) {
      // Soft warning
      return 'bg-gradient-to-r from-amber-400 to-amber-500 text-slate-900 border-amber-600';
    }
    // Default - in progress
    return 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white border-indigo-700';
  };

  // Get status icon
  const getStatusIcon = () => {
    if (data.warning_level === 3) return <AlertOctagon className="flex-shrink-0" size={24} />;
    if (data.warning_level === 2) return <AlertTriangle className="flex-shrink-0" size={24} />;
    if (data.success_days >= data.required_success_days) return <Trophy className="flex-shrink-0" size={24} />;
    if (data.today_target_reached) return <CheckCircle className="flex-shrink-0" size={24} />;
    return <Target className="flex-shrink-0" size={24} />;
  };

  // Progress percentage for the month
  const monthProgress = Math.min(100, (data.success_days / data.required_success_days) * 100);

  return (
    <div className={`rounded-xl border-2 shadow-lg mb-4 overflow-hidden transition-all ${getBannerStyle()}`}>
      {/* Main Banner Content */}
      <div className="p-3 sm:p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Left: Status Icon and Main Message */}
          <div className="flex items-center gap-3 min-w-0">
            {getStatusIcon()}
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-lg font-bold">{data.status_symbol}</span>
                <span className="font-semibold text-sm sm:text-base truncate">{data.status_text}</span>
                {data.streak > 1 && (
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-white/20 rounded-full text-xs font-medium">
                    <Flame size={14} /> {data.streak} day streak!
                  </span>
                )}
              </div>
              {data.warning_message && (
                <p className="text-xs sm:text-sm opacity-90 mt-0.5">{data.warning_message}</p>
              )}
            </div>
          </div>

          {/* Right: Today's Progress */}
          <div className="flex items-center gap-4 flex-wrap">
            {/* Today's NDP */}
            <div className="text-center">
              <div className="flex items-center gap-1">
                <span className={`text-lg sm:text-xl font-bold ${data.today_ndp >= data.daily_ndp_target ? '' : 'opacity-80'}`}>
                  {data.today_ndp}
                </span>
                <span className="text-xs opacity-70">/{data.daily_ndp_target}</span>
                {data.today_reached_via === 'ndp' && <CheckCircle size={16} className="text-white" />}
              </div>
              <p className="text-xs opacity-80">NDP Today</p>
            </div>

            {/* Today's RDP */}
            <div className="text-center">
              <div className="flex items-center gap-1">
                <span className={`text-lg sm:text-xl font-bold ${data.today_rdp >= data.daily_rdp_target ? '' : 'opacity-80'}`}>
                  {data.today_rdp}
                </span>
                <span className="text-xs opacity-70">/{data.daily_rdp_target}</span>
                {data.today_reached_via === 'rdp' && <CheckCircle size={16} className="text-white" />}
              </div>
              <p className="text-xs opacity-80">RDP Today</p>
            </div>

            {/* Monthly Progress */}
            <div className="text-center min-w-[80px]">
              <div className="flex items-center gap-1 justify-center">
                <span className="text-lg sm:text-xl font-bold">{data.success_days}</span>
                <span className="text-xs opacity-70">/{data.required_success_days}</span>
                {data.success_days >= data.required_success_days && <Trophy size={16} />}
              </div>
              <p className="text-xs opacity-80">{MONTH_NAMES[data.current_month - 1]} Days</p>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs opacity-80 mb-1">
            <span>Monthly Target Progress</span>
            <span>{data.days_remaining} days remaining • Projected: {data.projected_success} days</span>
          </div>
          <div className="h-2 bg-white/20 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${
                data.success_days >= data.required_success_days 
                  ? 'bg-white' 
                  : monthProgress >= 70 
                    ? 'bg-white/90' 
                    : 'bg-white/70'
              }`}
              style={{ width: `${monthProgress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs mt-1">
            <span className="opacity-70">
              {data.success_days >= data.required_success_days 
                ? '🎉 Monthly target achieved!' 
                : `Need ${data.required_success_days - data.success_days} more day(s)`}
            </span>
            <span className="opacity-70">{Math.round(monthProgress)}%</span>
          </div>
        </div>
      </div>

      {/* Footer hint - only show if target not reached today */}
      {!data.today_target_reached && (
        <div className="bg-black/10 px-4 py-2 text-xs text-center opacity-90">
          💡 Reach <strong>{data.daily_ndp_target} NDP</strong> or <strong>{data.daily_rdp_target} RDP</strong> today to count as a successful day!
        </div>
      )}
    </div>
  );
}
