import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  DollarSign, Users, Calendar, ChevronDown, ChevronUp, 
  Download, TrendingUp, Award, Target, FileSpreadsheet
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

  return (
    <div className="space-y-6" data-testid="bonus-calculation-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">CRM Bonus Calculation</h1>
          <p className="text-slate-500 text-sm mt-1">Automatic monthly bonus calculation for staff</p>
        </div>
        <button
          onClick={exportToExcel}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          data-testid="export-bonus-btn"
        >
          <FileSpreadsheet size={18} />
          Export Excel
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Year</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              data-testid="year-filter"
            >
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Month</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <Award size={18} className="text-amber-500" />
            Main Bonus Tiers
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between p-2 bg-amber-50 rounded">
              <span>≥ Rp 280.000.000</span>
              <span className="font-bold text-amber-600">$100</span>
            </div>
            <div className="flex justify-between p-2 bg-amber-50/70 rounded">
              <span>≥ Rp 210.000.000</span>
              <span className="font-bold text-amber-600">$75</span>
            </div>
            <div className="flex justify-between p-2 bg-amber-50/50 rounded">
              <span>≥ Rp 140.000.000</span>
              <span className="font-bold text-amber-600">$50</span>
            </div>
            <div className="flex justify-between p-2 bg-amber-50/30 rounded">
              <span>≥ Rp 100.000.000</span>
              <span className="font-bold text-amber-600">$30</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-50 rounded">
              <span>≥ Rp 70.000.000</span>
              <span className="font-bold text-amber-600">$20</span>
            </div>
          </div>
        </div>

        {/* NDP Bonus Tiers */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <Users size={18} className="text-blue-500" />
            Daily NDP Bonus
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between p-2 bg-blue-50 rounded">
              <span>&gt;10 NDP/day</span>
              <span className="font-bold text-blue-600">$5.00</span>
            </div>
            <div className="flex justify-between p-2 bg-blue-50/50 rounded">
              <span>8-10 NDP/day</span>
              <span className="font-bold text-blue-600">$2.50</span>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-3">*Total NDP from all products per day</p>
        </div>

        {/* RDP Bonus Tiers */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <TrendingUp size={18} className="text-green-500" />
            Daily RDP Bonus
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between p-2 bg-green-50 rounded">
              <span>&gt;15 RDP/day</span>
              <span className="font-bold text-green-600">$5.00</span>
            </div>
            <div className="flex justify-between p-2 bg-green-50/50 rounded">
              <span>12-15 RDP/day</span>
              <span className="font-bold text-green-600">$2.50</span>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-3">*Total RDP from all products per day</p>
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
        <h2 className="font-semibold text-slate-800 flex items-center gap-2">
          <Users size={20} />
          Staff Bonus Breakdown
        </h2>
        
        {!bonusData || bonusData.staff_bonuses.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center text-slate-500">
            No bonus data for this month
          </div>
        ) : (
          bonusData.staff_bonuses.map((staff) => {
            const isExpanded = expandedStaff[staff.staff_id];
            
            return (
              <div key={staff.staff_id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                {/* Staff Header */}
                <button
                  onClick={() => toggleStaff(staff.staff_id)}
                  className="w-full px-4 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center font-bold text-xl">
                      {staff.staff_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="text-left">
                      <div className="font-semibold text-slate-800 text-lg">{staff.staff_name}</div>
                      <div className="text-sm text-slate-500">{staff.days_worked} days worked</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-sm text-slate-500">Total Bonus</div>
                      <div className="text-2xl font-bold text-green-600">{formatUSD(staff.total_bonus)}</div>
                    </div>
                    {isExpanded ? <ChevronUp size={24} className="text-slate-400" /> : <ChevronDown size={24} className="text-slate-400" />}
                  </div>
                </button>

                {/* Staff Details */}
                {isExpanded && (
                  <div className="border-t border-slate-200 p-4 bg-slate-50">
                    {/* Bonus Breakdown */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                      <div className="bg-white rounded-lg p-4 border border-slate-200">
                        <div className="text-sm text-slate-500 mb-1">Total Nominal</div>
                        <div className="text-xl font-bold text-slate-800">{formatRupiah(staff.total_nominal)}</div>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
                        <div className="text-sm text-amber-700 mb-1">Main Bonus</div>
                        <div className="text-xl font-bold text-amber-600">{formatUSD(staff.main_bonus)}</div>
                      </div>
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <div className="text-sm text-blue-700 mb-1">NDP Bonus</div>
                        <div className="text-xl font-bold text-blue-600">{formatUSD(staff.ndp_bonus_total)}</div>
                        <div className="text-xs text-blue-500 mt-1">
                          {staff.ndp_bonus_days.above_10} days &gt;10 • {staff.ndp_bonus_days['8_10']} days 8-10
                        </div>
                      </div>
                      <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                        <div className="text-sm text-green-700 mb-1">RDP Bonus</div>
                        <div className="text-xl font-bold text-green-600">{formatUSD(staff.rdp_bonus_total)}</div>
                        <div className="text-xs text-green-500 mt-1">
                          {staff.rdp_bonus_days.above_15} days &gt;15 • {staff.rdp_bonus_days['12_15']} days 12-15
                        </div>
                      </div>
                    </div>

                    {/* Daily Breakdown Table */}
                    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                      <div className="px-4 py-2 bg-slate-100 border-b border-slate-200">
                        <h4 className="font-medium text-slate-700">Daily Breakdown</h4>
                      </div>
                      <div className="overflow-x-auto max-h-64">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50 sticky top-0">
                            <tr>
                              <th className="px-4 py-2 text-left text-slate-600">Date</th>
                              <th className="px-4 py-2 text-right text-slate-600">NDP</th>
                              <th className="px-4 py-2 text-right text-slate-600">NDP Bonus</th>
                              <th className="px-4 py-2 text-right text-slate-600">RDP</th>
                              <th className="px-4 py-2 text-right text-slate-600">RDP Bonus</th>
                              <th className="px-4 py-2 text-right text-slate-600">Day Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {staff.daily_breakdown.map((day, idx) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-4 py-2 text-slate-900">{day.date}</td>
                                <td className="px-4 py-2 text-right">
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    day.ndp > 10 ? 'bg-blue-100 text-blue-700' :
                                    day.ndp >= 8 ? 'bg-blue-50 text-blue-600' :
                                    'text-slate-600'
                                  }`}>
                                    {day.ndp}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-right text-blue-600 font-medium">
                                  {day.ndp_bonus > 0 ? formatUSD(day.ndp_bonus) : '-'}
                                </td>
                                <td className="px-4 py-2 text-right">
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    day.rdp > 15 ? 'bg-green-100 text-green-700' :
                                    day.rdp >= 12 ? 'bg-green-50 text-green-600' :
                                    'text-slate-600'
                                  }`}>
                                    {day.rdp}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-right text-green-600 font-medium">
                                  {day.rdp_bonus > 0 ? formatUSD(day.rdp_bonus) : '-'}
                                </td>
                                <td className="px-4 py-2 text-right font-bold text-slate-800">
                                  {formatUSD(day.ndp_bonus + day.rdp_bonus)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-slate-100">
                            <tr className="font-semibold">
                              <td className="px-4 py-2 text-slate-900">Total</td>
                              <td className="px-4 py-2 text-right text-blue-700">
                                {staff.daily_breakdown.reduce((sum, d) => sum + d.ndp, 0)}
                              </td>
                              <td className="px-4 py-2 text-right text-blue-700">
                                {formatUSD(staff.ndp_bonus_total)}
                              </td>
                              <td className="px-4 py-2 text-right text-green-700">
                                {staff.daily_breakdown.reduce((sum, d) => sum + d.rdp, 0)}
                              </td>
                              <td className="px-4 py-2 text-right text-green-700">
                                {formatUSD(staff.rdp_bonus_total)}
                              </td>
                              <td className="px-4 py-2 text-right text-slate-900">
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
    </div>
  );
}
