/**
 * StaffBonusProgress - Staff-facing bonus view
 * Shows bonus configuration (how it's calculated) and staff's own progress only
 * Staff cannot see other staff's bonus data
 */
import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  DollarSign, Calendar, ChevronDown, ChevronUp, 
  TrendingUp, Award, Target, Users, Info, RefreshCw
} from 'lucide-react';

const MONTH_NAMES = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

// Format number as Indonesian Rupiah
const formatRupiah = (num) => {
  if (!num) return 'Rp 0';
  return 'Rp ' + num.toLocaleString('id-ID');
};

// Format number as USD
const formatUSD = (num) => {
  if (!num) return '$0';
  return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};

export default function StaffBonusProgress() {
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [bonusData, setBonusData] = useState(null);
  const [showDailyBreakdown, setShowDailyBreakdown] = useState(false);
  const [showHowItWorks, setShowHowItWorks] = useState(false);

  useEffect(() => {
    loadMyBonus();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedYear, selectedMonth]);

  const loadMyBonus = async () => {
    setLoading(true);
    try {
      const response = await api.get('/bonus-calculation/my-bonus', {
        params: { year: selectedYear, month: selectedMonth }
      });
      setBonusData(response.data);
    } catch (error) {
      console.error('Failed to load bonus data:', error);
      toast.error('Gagal memuat data bonus');
    } finally {
      setLoading(false);
    }
  };

  // Get years for dropdown
  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1, currentYear - 2];

  if (loading && !bonusData) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="staff-bonus-loading">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  const bonusConfig = bonusData?.bonus_config || { main_tiers: [], ndp_tiers: [], rdp_tiers: [] };

  return (
    <div className="space-y-6" data-testid="staff-bonus-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Bonus Saya</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Lihat progress bonus bulanan kamu</p>
        </div>
        <button
          onClick={() => setShowHowItWorks(!showHowItWorks)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900 transition-colors"
          data-testid="how-it-works-btn"
        >
          <Info size={18} />
          {showHowItWorks ? 'Sembunyikan Cara Kerja' : 'Cara Kerja Bonus'}
        </button>
      </div>

      {/* How Bonus Works Section */}
      {showHowItWorks && (
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 rounded-xl border border-indigo-200 dark:border-indigo-800 p-6">
          <h2 className="text-lg font-bold text-indigo-900 dark:text-indigo-100 mb-4 flex items-center gap-2">
            <Info size={20} />
            Cara Menghitung Bonus
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Main Bonus Tiers */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
              <h3 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
                <Award size={18} className="text-amber-500 dark:text-amber-400" />
                Bonus Utama (Total Nominal Bulanan)
              </h3>
              <div className="space-y-2 text-sm">
                {bonusConfig.main_tiers
                  .sort((a, b) => b.threshold - a.threshold)
                  .map((tier, idx) => (
                    <div key={idx} className={`flex justify-between p-2 rounded text-slate-700 dark:text-slate-300 ${idx === 0 ? 'bg-amber-50 dark:bg-amber-900/30' : 'bg-slate-50 dark:bg-slate-700/50'}`}>
                      <span>≥ {formatRupiah(tier.threshold)}</span>
                      <span className="font-bold text-amber-600 dark:text-amber-400">${tier.bonus}</span>
                    </div>
                  ))}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">*Berdasarkan total omset bulanan kamu</p>
            </div>

            {/* NDP Bonus Tiers */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
              <h3 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
                <Users size={18} className="text-blue-500 dark:text-blue-400" />
                Bonus NDP Harian
              </h3>
              <div className="space-y-2 text-sm">
                {bonusConfig.ndp_tiers.map((tier, idx) => (
                  <div key={idx} className={`flex justify-between p-2 rounded text-slate-700 dark:text-slate-300 ${idx === 0 ? 'bg-blue-50 dark:bg-blue-900/30' : 'bg-blue-50/50 dark:bg-blue-900/20'}`}>
                    <span>{tier.label} NDP/hari</span>
                    <span className="font-bold text-blue-600 dark:text-blue-400">${tier.bonus.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">*Total NDP dari semua produk per hari</p>
            </div>

            {/* RDP Bonus Tiers */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
              <h3 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
                <TrendingUp size={18} className="text-green-500 dark:text-green-400" />
                Bonus RDP Harian
              </h3>
              <div className="space-y-2 text-sm">
                {bonusConfig.rdp_tiers.map((tier, idx) => (
                  <div key={idx} className={`flex justify-between p-2 rounded text-slate-700 dark:text-slate-300 ${idx === 0 ? 'bg-green-50 dark:bg-green-900/30' : 'bg-green-50/50 dark:bg-green-900/20'}`}>
                    <span>{tier.label} RDP/hari</span>
                    <span className="font-bold text-green-600 dark:text-green-400">${tier.bonus.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">*Total RDP dari semua produk per hari</p>
            </div>
          </div>

          <div className="mt-4 p-4 bg-white/50 dark:bg-slate-800/50 rounded-lg">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>Total Bonus = Bonus Utama + Total Bonus NDP Harian + Total Bonus RDP Harian</strong>
            </p>
          </div>
        </div>
      )}

      {/* Month/Year Filter */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">Tahun</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100"
              data-testid="year-filter"
            >
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">Bulan</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100"
              data-testid="month-filter"
            >
              {MONTH_NAMES.map((name, idx) => (
                <option key={idx} value={idx + 1}>{name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={loadMyBonus}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50"
            data-testid="refresh-btn"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* My Bonus Summary */}
      {bonusData && (
        <>
          {/* Total Bonus Card */}
          <div className="bg-gradient-to-r from-emerald-600 to-green-600 rounded-xl shadow-lg p-6 text-white">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h3 className="text-lg font-semibold opacity-90">Total Bonus Kamu - {MONTH_NAMES[selectedMonth - 1]} {selectedYear}</h3>
                <div className="text-4xl font-bold mt-2">{formatUSD(bonusData.total_bonus)}</div>
                <p className="text-sm opacity-75 mt-1">{bonusData.days_worked} hari kerja</p>
              </div>
              <div className="flex items-center gap-2">
                <DollarSign size={48} className="opacity-30" />
              </div>
            </div>
          </div>

          {/* Bonus Breakdown Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
              <div className="text-sm text-slate-500 dark:text-slate-400 mb-1">Total Nominal</div>
              <div className="text-xl font-bold text-slate-800 dark:text-white">{formatRupiah(bonusData.total_nominal)}</div>
            </div>
            <div className="bg-amber-50 dark:bg-amber-900/30 rounded-xl p-4 border border-amber-200 dark:border-amber-800">
              <div className="text-sm text-amber-700 dark:text-amber-300 mb-1 flex items-center gap-1">
                <Award size={14} />
                Bonus Utama
              </div>
              <div className="text-xl font-bold text-amber-600 dark:text-amber-400">{formatUSD(bonusData.main_bonus)}</div>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/30 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
              <div className="text-sm text-blue-700 dark:text-blue-300 mb-1 flex items-center gap-1">
                <Users size={14} />
                Bonus NDP
              </div>
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{formatUSD(bonusData.ndp_bonus_total)}</div>
              <div className="text-xs text-blue-500 dark:text-blue-400 mt-1">
                {Object.entries(bonusData.ndp_bonus_days || {}).map(([label, count]) => (
                  count > 0 && <span key={label} className="mr-2">{count} hari {label}</span>
                ))}
              </div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/30 rounded-xl p-4 border border-green-200 dark:border-green-800">
              <div className="text-sm text-green-700 dark:text-green-300 mb-1 flex items-center gap-1">
                <TrendingUp size={14} />
                Bonus RDP
              </div>
              <div className="text-xl font-bold text-green-600 dark:text-green-400">{formatUSD(bonusData.rdp_bonus_total)}</div>
              <div className="text-xs text-green-500 dark:text-green-400 mt-1">
                {Object.entries(bonusData.rdp_bonus_days || {}).map(([label, count]) => (
                  count > 0 && <span key={label} className="mr-2">{count} hari {label}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Daily Breakdown Toggle */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <button
              onClick={() => setShowDailyBreakdown(!showDailyBreakdown)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              data-testid="toggle-daily-breakdown"
            >
              <span className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                <Calendar size={18} />
                Rincian Harian
              </span>
              {showDailyBreakdown ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>

            {showDailyBreakdown && (
              <div className="border-t border-slate-200 dark:border-slate-700">
                {bonusData.daily_breakdown?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 dark:bg-slate-700">
                        <tr>
                          <th className="px-4 py-3 text-left text-slate-600 dark:text-slate-300">Tanggal</th>
                          <th className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">NDP</th>
                          <th className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">Bonus NDP</th>
                          <th className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">RDP</th>
                          <th className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">Bonus RDP</th>
                          <th className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">Total Hari</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                        {bonusData.daily_breakdown.map((day, idx) => (
                          <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                            <td className="px-4 py-2 text-slate-900 dark:text-slate-100 font-mono">{day.date}</td>
                            <td className="px-4 py-2 text-right">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                day.ndp_bonus > 0 ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300' : 'text-slate-600 dark:text-slate-400'
                              }`}>
                                {day.ndp}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-right text-blue-600 dark:text-blue-400 font-medium">
                              {day.ndp_bonus > 0 ? formatUSD(day.ndp_bonus) : '-'}
                            </td>
                            <td className="px-4 py-2 text-right">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                day.rdp_bonus > 0 ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300' : 'text-slate-600 dark:text-slate-400'
                              }`}>
                                {day.rdp}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-right text-green-600 dark:text-green-400 font-medium">
                              {day.rdp_bonus > 0 ? formatUSD(day.rdp_bonus) : '-'}
                            </td>
                            <td className="px-4 py-2 text-right font-bold text-slate-800 dark:text-white">
                              {day.ndp_bonus + day.rdp_bonus > 0 ? formatUSD(day.ndp_bonus + day.rdp_bonus) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-slate-100 dark:bg-slate-700">
                        <tr className="font-semibold">
                          <td className="px-4 py-2 text-slate-900 dark:text-white">Total</td>
                          <td className="px-4 py-2 text-right text-blue-700 dark:text-blue-400">
                            {bonusData.daily_breakdown.reduce((sum, d) => sum + d.ndp, 0)}
                          </td>
                          <td className="px-4 py-2 text-right text-blue-700 dark:text-blue-400">
                            {formatUSD(bonusData.ndp_bonus_total)}
                          </td>
                          <td className="px-4 py-2 text-right text-green-700 dark:text-green-400">
                            {bonusData.daily_breakdown.reduce((sum, d) => sum + d.rdp, 0)}
                          </td>
                          <td className="px-4 py-2 text-right text-green-700 dark:text-green-400">
                            {formatUSD(bonusData.rdp_bonus_total)}
                          </td>
                          <td className="px-4 py-2 text-right text-slate-900 dark:text-white">
                            {formatUSD(bonusData.ndp_bonus_total + bonusData.rdp_bonus_total)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                    Belum ada data untuk bulan ini
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Total Summary */}
          <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <span className="font-semibold">Perhitungan Total Bonus</span>
              <div className="flex items-center gap-4">
                <span className="text-sm opacity-70">
                  {formatUSD(bonusData.main_bonus)} + {formatUSD(bonusData.ndp_bonus_total)} + {formatUSD(bonusData.rdp_bonus_total)}
                </span>
                <span className="text-2xl font-bold text-green-400">{formatUSD(bonusData.total_bonus)}</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* No data state */}
      {!bonusData && !loading && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center text-slate-500 dark:text-slate-400">
          <DollarSign size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg">Belum ada data bonus untuk bulan ini</p>
          <p className="text-sm mt-1">Data akan muncul setelah kamu mencatat omset</p>
        </div>
      )}
    </div>
  );
}
