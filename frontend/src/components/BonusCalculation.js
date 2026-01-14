import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  DollarSign, Users, Calendar, ChevronDown, ChevronUp, 
  Download, TrendingUp, Award, Target, FileSpreadsheet,
  Settings, X, Plus, Trash2, Save, RotateCcw
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

export default function BonusCalculation() {
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [bonusData, setBonusData] = useState(null);
  const [expandedStaff, setExpandedStaff] = useState({});
  const [showSettings, setShowSettings] = useState(false);
  const [editConfig, setEditConfig] = useState(null);
  const [savingConfig, setSavingConfig] = useState(false);

  useEffect(() => {
    loadBonusData();
  }, [selectedYear, selectedMonth]);

  const loadBonusData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/bonus-calculation/data', {
        params: { year: selectedYear, month: selectedMonth }
      });
      setBonusData(response.data);
    } catch (error) {
      console.error('Failed to load bonus data:', error);
      toast.error('Failed to load bonus data');
    } finally {
      setLoading(false);
    }
  };

  const toggleStaff = (staffId) => {
    setExpandedStaff(prev => ({ ...prev, [staffId]: !prev[staffId] }));
  };

  const exportToExcel = () => {
    window.open(`${api.defaults.baseURL}/bonus-calculation/export?year=${selectedYear}&month=${selectedMonth}`, '_blank');
    toast.success('Export started');
  };

  const openSettings = () => {
    if (bonusData?.bonus_config) {
      setEditConfig(JSON.parse(JSON.stringify(bonusData.bonus_config)));
    }
    setShowSettings(true);
  };

  const saveConfig = async () => {
    setSavingConfig(true);
    try {
      await api.put('/bonus-calculation/config', editConfig);
      toast.success('Bonus configuration saved!');
      setShowSettings(false);
      loadBonusData(); // Reload data with new config
    } catch (error) {
      console.error('Failed to save config:', error);
      toast.error('Failed to save configuration');
    } finally {
      setSavingConfig(false);
    }
  };

  const resetConfig = async () => {
    if (!window.confirm('Reset to default configuration? This cannot be undone.')) return;
    
    setSavingConfig(true);
    try {
      const response = await api.post('/bonus-calculation/config/reset');
      setEditConfig(response.data.config);
      toast.success('Configuration reset to defaults!');
      loadBonusData();
    } catch (error) {
      console.error('Failed to reset config:', error);
      toast.error('Failed to reset configuration');
    } finally {
      setSavingConfig(false);
    }
  };

  // Main tier handlers
  const addMainTier = () => {
    setEditConfig(prev => ({
      ...prev,
      main_tiers: [...prev.main_tiers, { threshold: 0, bonus: 0 }]
    }));
  };

  const updateMainTier = (index, field, value) => {
    setEditConfig(prev => ({
      ...prev,
      main_tiers: prev.main_tiers.map((tier, i) => 
        i === index ? { ...tier, [field]: Number(value) } : tier
      )
    }));
  };

  const removeMainTier = (index) => {
    setEditConfig(prev => ({
      ...prev,
      main_tiers: prev.main_tiers.filter((_, i) => i !== index)
    }));
  };

  // NDP tier handlers
  const updateNdpTier = (index, field, value) => {
    setEditConfig(prev => ({
      ...prev,
      ndp_tiers: prev.ndp_tiers.map((tier, i) => 
        i === index ? { ...tier, [field]: field === 'label' ? value : (value === '' ? null : Number(value)) } : tier
      )
    }));
  };

  // RDP tier handlers
  const updateRdpTier = (index, field, value) => {
    setEditConfig(prev => ({
      ...prev,
      rdp_tiers: prev.rdp_tiers.map((tier, i) => 
        i === index ? { ...tier, [field]: field === 'label' ? value : (value === '' ? null : Number(value)) } : tier
      )
    }));
  };

  // Get years for dropdown
  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1, currentYear - 2];

  if (loading && !bonusData) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="bonus-calculation-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const bonusConfig = bonusData?.bonus_config || { main_tiers: [], ndp_tiers: [], rdp_tiers: [] };

  return (
    <div className="space-y-6" data-testid="bonus-calculation-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">CRM Bonus Calculation</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Automatic monthly bonus calculation for staff</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={openSettings}
            className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors"
            data-testid="settings-btn"
          >
            <Settings size={18} />
            Settings
          </button>
          <button
            onClick={exportToExcel}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            data-testid="export-bonus-btn"
          >
            <FileSpreadsheet size={18} />
            Export Excel
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">Year</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100"
              data-testid="year-filter"
            >
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">Month</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100"
              data-testid="month-filter"
            >
              {MONTH_NAMES.map((name, idx) => (
                <option key={idx} value={idx + 1}>{name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Bonus Tiers Reference */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main Bonus Tiers */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
          <h3 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
            <Award size={18} className="text-amber-500 dark:text-amber-400" />
            Main Bonus Tiers
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
        </div>

        {/* NDP Bonus Tiers */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
          <h3 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
            <Users size={18} className="text-blue-500 dark:text-blue-400" />
            Daily NDP Bonus
          </h3>
          <div className="space-y-2 text-sm">
            {bonusConfig.ndp_tiers.map((tier, idx) => (
              <div key={idx} className={`flex justify-between p-2 rounded text-slate-700 dark:text-slate-300 ${idx === 0 ? 'bg-blue-50 dark:bg-blue-900/30' : 'bg-blue-50/50 dark:bg-blue-900/20'}`}>
                <span>{tier.label} NDP/day</span>
                <span className="font-bold text-blue-600 dark:text-blue-400">${tier.bonus.toFixed(2)}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">*Total NDP from all products per day</p>
        </div>

        {/* RDP Bonus Tiers */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
          <h3 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
            <TrendingUp size={18} className="text-green-500 dark:text-green-400" />
            Daily RDP Bonus
          </h3>
          <div className="space-y-2 text-sm">
            {bonusConfig.rdp_tiers.map((tier, idx) => (
              <div key={idx} className={`flex justify-between p-2 rounded text-slate-700 dark:text-slate-300 ${idx === 0 ? 'bg-green-50 dark:bg-green-900/30' : 'bg-green-50/50 dark:bg-green-900/20'}`}>
                <span>{tier.label} RDP/day</span>
                <span className="font-bold text-green-600 dark:text-green-400">${tier.bonus.toFixed(2)}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">*Total RDP from all products per day</p>
        </div>
      </div>

      {/* Grand Total Summary */}
      {bonusData && bonusData.grand_total && (
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl shadow-lg p-6 text-white">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h3 className="text-lg font-semibold opacity-90">Grand Total - {MONTH_NAMES[selectedMonth - 1]} {selectedYear}</h3>
              <div className="text-3xl font-bold mt-1">{formatUSD(bonusData.grand_total.total_bonus)}</div>
            </div>
            <div className="flex gap-6 text-sm">
              <div className="text-center">
                <div className="opacity-70">Total Nominal</div>
                <div className="font-bold">{formatRupiah(bonusData.grand_total.total_nominal)}</div>
              </div>
              <div className="text-center">
                <div className="opacity-70">Main Bonus</div>
                <div className="font-bold">{formatUSD(bonusData.grand_total.main_bonus)}</div>
              </div>
              <div className="text-center">
                <div className="opacity-70">NDP Bonus</div>
                <div className="font-bold">{formatUSD(bonusData.grand_total.ndp_bonus_total)}</div>
              </div>
              <div className="text-center">
                <div className="opacity-70">RDP Bonus</div>
                <div className="font-bold">{formatUSD(bonusData.grand_total.rdp_bonus_total)}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Staff Bonus Cards */}
      <div className="space-y-4">
        <h2 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
          <Users size={20} />
          Staff Bonus Breakdown
        </h2>
        
        {!bonusData || bonusData.staff_bonuses.length === 0 ? (
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center text-slate-500 dark:text-slate-400">
            No bonus data for this month
          </div>
        ) : (
          bonusData.staff_bonuses.map((staff) => {
            const isExpanded = expandedStaff[staff.staff_id];
            
            return (
              <div key={staff.staff_id} className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                {/* Staff Header */}
                <button
                  onClick={() => toggleStaff(staff.staff_id)}
                  className="w-full px-4 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center font-bold text-xl">
                      {staff.staff_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="text-left">
                      <div className="font-semibold text-slate-800 dark:text-white text-lg">{staff.staff_name}</div>
                      <div className="text-sm text-slate-500 dark:text-slate-400">{staff.days_worked} days worked</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-sm text-slate-500 dark:text-slate-400">Total Bonus</div>
                      <div className="text-2xl font-bold text-green-600 dark:text-green-400">{formatUSD(staff.total_bonus)}</div>
                    </div>
                    {isExpanded ? <ChevronUp size={24} className="text-slate-400" /> : <ChevronDown size={24} className="text-slate-400" />}
                  </div>
                </button>

                {/* Staff Details */}
                {isExpanded && (
                  <div className="border-t border-slate-200 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-900/50">
                    {/* Bonus Breakdown */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
                        <div className="text-sm text-slate-500 dark:text-slate-400 mb-1">Total Nominal</div>
                        <div className="text-xl font-bold text-slate-800 dark:text-white">{formatRupiah(staff.total_nominal)}</div>
                      </div>
                      <div className="bg-amber-50 dark:bg-amber-900/30 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
                        <div className="text-sm text-amber-700 dark:text-amber-300 mb-1">Main Bonus</div>
                        <div className="text-xl font-bold text-amber-600 dark:text-amber-400">{formatUSD(staff.main_bonus)}</div>
                      </div>
                      <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                        <div className="text-sm text-blue-700 dark:text-blue-300 mb-1">NDP Bonus</div>
                        <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{formatUSD(staff.ndp_bonus_total)}</div>
                        <div className="text-xs text-blue-500 dark:text-blue-400 mt-1">
                          {Object.entries(staff.ndp_bonus_days).map(([label, count]) => (
                            <span key={label} className="mr-2">{count} days {label}</span>
                          ))}
                        </div>
                      </div>
                      <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4 border border-green-200 dark:border-green-800">
                        <div className="text-sm text-green-700 dark:text-green-300 mb-1">RDP Bonus</div>
                        <div className="text-xl font-bold text-green-600 dark:text-green-400">{formatUSD(staff.rdp_bonus_total)}</div>
                        <div className="text-xs text-green-500 dark:text-green-400 mt-1">
                          {Object.entries(staff.rdp_bonus_days).map(([label, count]) => (
                            <span key={label} className="mr-2">{count} days {label}</span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Daily Breakdown Table */}
                    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                      <div className="px-4 py-2 bg-slate-100 dark:bg-slate-700 border-b border-slate-200 dark:border-slate-600">
                        <h4 className="font-medium text-slate-700 dark:text-slate-200">Daily Breakdown</h4>
                      </div>
                      <div className="overflow-x-auto max-h-64">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50 dark:bg-slate-700 sticky top-0">
                            <tr>
                              <th className="px-4 py-2 text-left text-slate-600 dark:text-slate-300">Date</th>
                              <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-300">NDP</th>
                              <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-300">NDP Bonus</th>
                              <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-300">RDP</th>
                              <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-300">RDP Bonus</th>
                              <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-300">Day Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                            {staff.daily_breakdown.map((day, idx) => (
                              <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                                <td className="px-4 py-2 text-slate-900 dark:text-slate-100">{day.date}</td>
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
                                  {formatUSD(day.ndp_bonus + day.rdp_bonus)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-slate-100 dark:bg-slate-700">
                            <tr className="font-semibold">
                              <td className="px-4 py-2 text-slate-900 dark:text-white">Total</td>
                              <td className="px-4 py-2 text-right text-blue-700 dark:text-blue-400">
                                {staff.daily_breakdown.reduce((sum, d) => sum + d.ndp, 0)}
                              </td>
                              <td className="px-4 py-2 text-right text-blue-700 dark:text-blue-400">
                                {formatUSD(staff.ndp_bonus_total)}
                              </td>
                              <td className="px-4 py-2 text-right text-green-700 dark:text-green-400">
                                {staff.daily_breakdown.reduce((sum, d) => sum + d.rdp, 0)}
                              </td>
                              <td className="px-4 py-2 text-right text-green-700 dark:text-green-400">
                                {formatUSD(staff.rdp_bonus_total)}
                              </td>
                              <td className="px-4 py-2 text-right text-slate-900 dark:text-white">
                                {formatUSD(staff.ndp_bonus_total + staff.rdp_bonus_total)}
                              </td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>

                    {/* Total Bonus Summary */}
                    <div className="mt-4 bg-gradient-to-r from-slate-800 to-slate-700 rounded-lg p-4 text-white">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">Total Bonus for {staff.staff_name}</span>
                        <div className="flex items-center gap-4">
                          <span className="text-sm opacity-70">
                            {formatUSD(staff.main_bonus)} + {formatUSD(staff.ndp_bonus_total)} + {formatUSD(staff.rdp_bonus_total)}
                          </span>
                          <span className="text-2xl font-bold text-green-400">{formatUSD(staff.total_bonus)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && editConfig && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
              <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Settings size={24} />
                Bonus Configuration Settings
              </h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors text-slate-600 dark:text-slate-400"
              >
                <X size={24} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
              <div className="space-y-8">
                {/* Main Bonus Tiers */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                      <Award size={20} className="text-amber-500 dark:text-amber-400" />
                      Main Bonus Tiers (Monthly Total Nominal)
                    </h3>
                    <button
                      onClick={addMainTier}
                      className="flex items-center gap-1 px-3 py-1.5 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900 transition-colors text-sm"
                    >
                      <Plus size={16} />
                      Add Tier
                    </button>
                  </div>
                  <div className="space-y-3">
                    {editConfig.main_tiers
                      .sort((a, b) => b.threshold - a.threshold)
                      .map((tier, idx) => (
                        <div key={idx} className="flex items-center gap-4 p-3 bg-amber-50 dark:bg-amber-900/30 rounded-lg">
                          <div className="flex-1">
                            <label className="block text-xs text-amber-700 dark:text-amber-300 mb-1">Threshold (Rp)</label>
                            <input
                              type="number"
                              value={tier.threshold}
                              onChange={(e) => {
                                const realIdx = editConfig.main_tiers.findIndex(t => t === tier);
                                updateMainTier(realIdx, 'threshold', e.target.value);
                              }}
                              className="w-full px-3 py-2 border border-amber-300 dark:border-amber-700 rounded-lg focus:ring-2 focus:ring-amber-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                              placeholder="e.g., 280000000"
                            />
                          </div>
                          <div className="w-32">
                            <label className="block text-xs text-amber-700 dark:text-amber-300 mb-1">Bonus ($)</label>
                            <input
                              type="number"
                              value={tier.bonus}
                              onChange={(e) => {
                                const realIdx = editConfig.main_tiers.findIndex(t => t === tier);
                                updateMainTier(realIdx, 'bonus', e.target.value);
                              }}
                              className="w-full px-3 py-2 border border-amber-300 dark:border-amber-700 rounded-lg focus:ring-2 focus:ring-amber-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                              placeholder="e.g., 100"
                            />
                          </div>
                          <button
                            onClick={() => {
                              const realIdx = editConfig.main_tiers.findIndex(t => t === tier);
                              removeMainTier(realIdx);
                            }}
                            className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 rounded-lg transition-colors mt-5"
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      ))}
                  </div>
                </div>

                {/* NDP Bonus Tiers */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                    <Users size={20} className="text-blue-500 dark:text-blue-400" />
                    Daily NDP Bonus Tiers
                  </h3>
                  <div className="space-y-3">
                    {editConfig.ndp_tiers.map((tier, idx) => (
                      <div key={idx} className="flex items-center gap-4 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                        <div className="w-24">
                          <label className="block text-xs text-blue-700 dark:text-blue-300 mb-1">Min NDP</label>
                          <input
                            type="number"
                            value={tier.min}
                            onChange={(e) => updateNdpTier(idx, 'min', e.target.value)}
                            className="w-full px-3 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                          />
                        </div>
                        <div className="w-24">
                          <label className="block text-xs text-blue-700 dark:text-blue-300 mb-1">Max NDP</label>
                          <input
                            type="number"
                            value={tier.max || ''}
                            onChange={(e) => updateNdpTier(idx, 'max', e.target.value)}
                            className="w-full px-3 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            placeholder="∞"
                          />
                        </div>
                        <div className="w-24">
                          <label className="block text-xs text-blue-700 dark:text-blue-300 mb-1">Bonus ($)</label>
                          <input
                            type="number"
                            step="0.5"
                            value={tier.bonus}
                            onChange={(e) => updateNdpTier(idx, 'bonus', e.target.value)}
                            className="w-full px-3 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-blue-700 dark:text-blue-300 mb-1">Label</label>
                          <input
                            type="text"
                            value={tier.label}
                            onChange={(e) => updateNdpTier(idx, 'label', e.target.value)}
                            className="w-full px-3 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            placeholder="e.g., >10"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">*Leave Max empty for &quot;greater than&quot; condition</p>
                </div>

                {/* RDP Bonus Tiers */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                    <TrendingUp size={20} className="text-green-500 dark:text-green-400" />
                    Daily RDP Bonus Tiers
                  </h3>
                  <div className="space-y-3">
                    {editConfig.rdp_tiers.map((tier, idx) => (
                      <div key={idx} className="flex items-center gap-4 p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
                        <div className="w-24">
                          <label className="block text-xs text-green-700 dark:text-green-300 mb-1">Min RDP</label>
                          <input
                            type="number"
                            value={tier.min}
                            onChange={(e) => updateRdpTier(idx, 'min', e.target.value)}
                            className="w-full px-3 py-2 border border-green-300 dark:border-green-700 rounded-lg focus:ring-2 focus:ring-green-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                          />
                        </div>
                        <div className="w-24">
                          <label className="block text-xs text-green-700 dark:text-green-300 mb-1">Max RDP</label>
                          <input
                            type="number"
                            value={tier.max || ''}
                            onChange={(e) => updateRdpTier(idx, 'max', e.target.value)}
                            className="w-full px-3 py-2 border border-green-300 dark:border-green-700 rounded-lg focus:ring-2 focus:ring-green-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            placeholder="∞"
                          />
                        </div>
                        <div className="w-24">
                          <label className="block text-xs text-green-700 dark:text-green-300 mb-1">Bonus ($)</label>
                          <input
                            type="number"
                            step="0.5"
                            value={tier.bonus}
                            onChange={(e) => updateRdpTier(idx, 'bonus', e.target.value)}
                            className="w-full px-3 py-2 border border-green-300 dark:border-green-700 rounded-lg focus:ring-2 focus:ring-green-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-green-700 dark:text-green-300 mb-1">Label</label>
                          <input
                            type="text"
                            value={tier.label}
                            onChange={(e) => updateRdpTier(idx, 'label', e.target.value)}
                            className="w-full px-3 py-2 border border-green-300 dark:border-green-700 rounded-lg focus:ring-2 focus:ring-green-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            placeholder="e.g., >15"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">*Leave Max empty for &quot;greater than&quot; condition</p>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
              <button
                onClick={resetConfig}
                disabled={savingConfig}
                className="flex items-center gap-2 px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <RotateCcw size={18} />
                Reset to Defaults
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={saveConfig}
                  disabled={savingConfig}
                  className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  <Save size={18} />
                  {savingConfig ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
