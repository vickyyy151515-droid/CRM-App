import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { Target, Flame, AlertTriangle, AlertOctagon, Trophy, CheckCircle } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const MONTH_NAMES_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MONTH_NAMES_ID = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

export default function StaffTargetBanner() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { t, isIndonesian } = useLanguage();

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
        <div className="h-16 bg-slate-200 dark:bg-slate-700 rounded"></div>
      </div>
    );
  }

  if (!data) return null;

  const monthNames = isIndonesian ? MONTH_NAMES_ID : MONTH_NAMES_EN;

  // Softer dark mode compatible colors
  const getBannerStyle = () => {
    if (data.warning_level === 3) {
      // Very serious - 2 consecutive months failed (softer red)
      return 'bg-gradient-to-r from-red-500/90 to-red-600/90 dark:from-red-600/80 dark:to-red-700/80 text-white border-red-600 dark:border-red-700';
    }
    if (data.warning_level === 2) {
      // Hard warning - failed last month (softer orange)
      return 'bg-gradient-to-r from-orange-400/90 to-orange-500/90 dark:from-orange-500/80 dark:to-orange-600/80 text-white border-orange-500 dark:border-orange-600';
    }
    if (data.today_target_reached) {
      // Today's target reached (softer green)
      return 'bg-gradient-to-r from-emerald-400/90 to-emerald-500/90 dark:from-emerald-500/80 dark:to-emerald-600/80 text-white border-emerald-500 dark:border-emerald-600';
    }
    if (data.warning_level === 1) {
      // Soft warning (softer amber)
      return 'bg-gradient-to-r from-amber-300/90 to-amber-400/90 dark:from-amber-500/70 dark:to-amber-600/70 text-slate-800 dark:text-white border-amber-400 dark:border-amber-600';
    }
    // Default - in progress (softer blue)
    return 'bg-gradient-to-r from-blue-400/90 to-indigo-500/90 dark:from-blue-500/70 dark:to-indigo-600/70 text-white border-blue-500 dark:border-indigo-600';
  };

  // Get status icon
  const getStatusIcon = () => {
    if (data.warning_level === 3) return <AlertOctagon className="flex-shrink-0" size={22} />;
    if (data.warning_level === 2) return <AlertTriangle className="flex-shrink-0" size={22} />;
    if (data.success_days >= data.required_success_days) return <Trophy className="flex-shrink-0" size={22} />;
    if (data.today_target_reached) return <CheckCircle className="flex-shrink-0" size={22} />;
    return <Target className="flex-shrink-0" size={22} />;
  };

  // Translated status texts
  const getStatusText = () => {
    if (data.warning_level === 3) return isIndonesian ? 'Gagal 2 Bulan Berturut' : '2nd Consecutive Miss';
    if (data.warning_level === 2) return isIndonesian ? 'Bulan Lalu Tidak Tercapai' : 'Previous Month Missed';
    if (data.success_days >= data.required_success_days) return isIndonesian ? 'Target Bulanan Tercapai!' : 'Monthly Target Achieved!';
    if (data.today_target_reached) return isIndonesian ? 'Target Harian Tercapai' : 'Daily Target Reached';
    if (data.projected_success >= data.required_success_days) return isIndonesian ? 'Di Jalur Yang Benar' : 'On Track';
    return isIndonesian ? 'Dalam Proses' : 'In Progress';
  };

  // Translated warning messages
  const getWarningMessage = () => {
    if (data.warning_level === 3) {
      return isIndonesian 
        ? `⚠️ SERIUS: Kamu sudah tidak mencapai target ${data.required_success_days} hari selama 2 bulan berturut-turut. Perlu perbaikan segera!`
        : `⚠️ SERIOUS: You've missed the ${data.required_success_days}-day target for 2 consecutive months. Immediate improvement required!`;
    }
    if (data.warning_level === 2) {
      return isIndonesian
        ? `⚠️ PERINGATAN: Bulan lalu target tidak tercapai (${data.prev_month_1_success} hari). Jangan sampai terulang!`
        : `⚠️ WARNING: You missed the ${data.required_success_days}-day target last month (${data.prev_month_1_success} days). Don't let it happen again!`;
    }
    if (data.warning_level === 1) {
      const daysNeeded = data.required_success_days - data.success_days;
      if (daysNeeded > data.days_remaining) {
        return isIndonesian
          ? `⚠️ Kamu butuh ${daysNeeded} hari sukses lagi tapi hanya tersisa ${data.days_remaining} hari!`
          : `⚠️ You need ${daysNeeded} more successful days but only ${data.days_remaining} days left!`;
      }
      return isIndonesian
        ? `📢 ${data.days_remaining} hari tersisa! Butuh ${daysNeeded} hari sukses lagi untuk mencapai target ${data.required_success_days} hari.`
        : `📢 ${data.days_remaining} days left! Need ${daysNeeded} more successful day(s) to reach ${data.required_success_days}-day target.`;
    }
    return null;
  };

  // Progress percentage for the month
  const monthProgress = Math.min(100, (data.success_days / data.required_success_days) * 100);

  return (
    <div className={`rounded-xl border shadow-md mb-4 overflow-hidden transition-all ${getBannerStyle()}`} data-testid="staff-target-banner">
      {/* Main Banner Content */}
      <div className="p-3 sm:p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Left: Status Icon and Main Message */}
          <div className="flex items-center gap-3 min-w-0">
            {getStatusIcon()}
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-lg font-bold">{data.status_symbol}</span>
                <span className="font-semibold text-sm sm:text-base truncate">{getStatusText()}</span>
                {data.streak > 1 && (
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-white/20 dark:bg-white/10 rounded-full text-xs font-medium">
                    <Flame size={14} /> {data.streak} {isIndonesian ? 'hari berturut!' : 'day streak!'}
                  </span>
                )}
              </div>
              {getWarningMessage() && (
                <p className="text-xs sm:text-sm opacity-90 mt-0.5">{getWarningMessage()}</p>
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
                {data.today_reached_via === 'ndp' && <CheckCircle size={16} />}
              </div>
              <p className="text-xs opacity-80">{isIndonesian ? 'NDP Hari Ini' : 'NDP Today'}</p>
            </div>

            {/* Today's RDP */}
            <div className="text-center">
              <div className="flex items-center gap-1">
                <span className={`text-lg sm:text-xl font-bold ${data.today_rdp >= data.daily_rdp_target ? '' : 'opacity-80'}`}>
                  {data.today_rdp}
                </span>
                <span className="text-xs opacity-70">/{data.daily_rdp_target}</span>
                {data.today_reached_via === 'rdp' && <CheckCircle size={16} />}
              </div>
              <p className="text-xs opacity-80">{isIndonesian ? 'RDP Hari Ini' : 'RDP Today'}</p>
            </div>

            {/* Monthly Progress */}
            <div className="text-center min-w-[80px]">
              <div className="flex items-center gap-1 justify-center">
                <span className="text-lg sm:text-xl font-bold">{data.success_days}</span>
                <span className="text-xs opacity-70">/{data.required_success_days}</span>
                {data.success_days >= data.required_success_days && <Trophy size={16} />}
              </div>
              <p className="text-xs opacity-80">{isIndonesian ? `Hari ${monthNames[data.current_month - 1]}` : `${monthNames[data.current_month - 1]} Days`}</p>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs opacity-80 mb-1">
            <span>{isIndonesian ? 'Progres Target Bulanan' : 'Monthly Target Progress'}</span>
            <span>
              {isIndonesian 
                ? `${data.days_remaining} hari tersisa • Proyeksi: ${data.projected_success} hari`
                : `${data.days_remaining} days remaining • Projected: ${data.projected_success} days`}
            </span>
          </div>
          <div className="h-2 bg-white/20 dark:bg-white/10 rounded-full overflow-hidden">
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
                ? (isIndonesian ? '🎉 Target bulanan tercapai!' : '🎉 Monthly target achieved!') 
                : (isIndonesian ? `Butuh ${data.required_success_days - data.success_days} hari lagi` : `Need ${data.required_success_days - data.success_days} more day(s)`)}
            </span>
            <span className="opacity-70">{Math.round(monthProgress)}%</span>
          </div>
        </div>
      </div>

      {/* Footer hint - only show if target not reached today */}
      {!data.today_target_reached && (
        <div className="bg-black/10 dark:bg-black/20 px-4 py-2 text-xs text-center opacity-90">
          {isIndonesian 
            ? `💡 Capai ${data.daily_ndp_target} NDP atau ${data.daily_rdp_target} RDP hari ini untuk dihitung sebagai hari sukses!`
            : `💡 Reach ${data.daily_ndp_target} NDP or ${data.daily_rdp_target} RDP today to count as a successful day!`}
        </div>
      )}
    </div>
  );
}
