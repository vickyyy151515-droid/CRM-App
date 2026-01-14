import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Calendar, TrendingUp, Users, DollarSign, BarChart3, 
  Download, Filter, RefreshCw, ChevronDown, ChevronUp,
  FileSpreadsheet, PieChart, Activity, Target
} from 'lucide-react';

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC'];
const MONTH_NAMES = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

// Format number as Indonesian Rupiah
const formatRupiah = (num) => {
  if (!num) return 'Rp 0';
  return 'Rp ' + num.toLocaleString('id-ID');
};

// Format number with thousand separator
const formatNumber = (num) => {
  if (!num) return '0';
  return num.toLocaleString('id-ID');
};

export default function ReportCRM() {
  const [loading, setLoading] = useState(true);
  const [products, setProducts] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [activeTab, setActiveTab] = useState('yearly'); // yearly, monthly, daily, staff
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth());
  const [serverDate, setServerDate] = useState(null);
  
  // Report data
  const [yearlyData, setYearlyData] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [monthlyByStaff, setMonthlyByStaff] = useState([]);
  const [dailyData, setDailyData] = useState([]);
  const [dailyByStaff, setDailyByStaff] = useState([]);
  const [staffPerformance, setStaffPerformance] = useState([]);
  const [depositTiers, setDepositTiers] = useState({ '2x': 0, '3x': 0, '4x_plus': 0 });
  const [expandedMonths, setExpandedMonths] = useState({});
  const [expandedStaff, setExpandedStaff] = useState({});
  const [expandedProducts, setExpandedProducts] = useState({});
  const [expandedMonthlyStaff, setExpandedMonthlyStaff] = useState({});
  const CRM_EFFICIENCY_TARGET = 278000000; // Rp 278,000,000 = 100%

  // Fetch server time on mount
  useEffect(() => {
    const fetchServerTime = async () => {
      try {
        const response = await api.get('/server-time');
        setServerDate(response.data.date);
      } catch (error) {
        console.error('Failed to fetch server time');
        setServerDate(new Date().toISOString().split('T')[0]);
      }
    };
    fetchServerTime();
  }, []);

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  // Load report data when filters change
  useEffect(() => {
    if (serverDate) {
      loadReportData();
    }
  }, [selectedProduct, selectedStaff, selectedYear, selectedMonth, serverDate]);

  const loadInitialData = async () => {
    try {
      const [productsRes, staffRes] = await Promise.all([
        api.get('/products'),
        api.get('/staff-users')
      ]);
      setProducts(productsRes.data);
      setStaffList(staffRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadReportData = async () => {
    setLoading(true);
    try {
      // Build params
      const params = {};
      if (selectedProduct) params.product_id = selectedProduct;
      if (selectedStaff) params.staff_id = selectedStaff;
      params.year = selectedYear;
      params.month = selectedMonth + 1; // 1-indexed

      const response = await api.get('/report-crm/data', { params });
      const data = response.data;

      setYearlyData(data.yearly || []);
      setMonthlyData(data.monthly || []);
      setMonthlyByStaff(data.monthly_by_staff || []);
      setDailyData(data.daily || []);
      setDailyByStaff(data.daily_by_staff || []);
      setStaffPerformance(data.staff_performance || []);
      setDepositTiers(data.deposit_tiers || { '2x': 0, '3x': 0, '4x_plus': 0 });
    } catch (error) {
      console.error('Failed to load report data:', error);
      toast.error('Failed to load report data');
    } finally {
      setLoading(false);
    }
  };

  const toggleMonth = (month) => {
    setExpandedMonths(prev => ({ ...prev, [month]: !prev[month] }));
  };

  const toggleMonthlyStaff = (monthKey) => {
    setExpandedMonthlyStaff(prev => ({ ...prev, [monthKey]: !prev[monthKey] }));
  };

  const toggleStaff = (staffId) => {
    setExpandedStaff(prev => ({ ...prev, [staffId]: !prev[staffId] }));
  };

  const toggleProduct = (staffId, productId) => {
    const key = `${staffId}-${productId}`;
    setExpandedProducts(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const exportToExcel = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedProduct) params.append('product_id', selectedProduct);
      if (selectedStaff) params.append('staff_id', selectedStaff);
      params.append('year', selectedYear);
      
      window.open(`${api.defaults.baseURL}/report-crm/export?${params.toString()}`, '_blank');
      toast.success('Export started');
    } catch (error) {
      toast.error('Failed to export');
    }
  };

  // Calculate totals for yearly summary
  const yearlyTotals = yearlyData.reduce((acc, month) => ({
    new_id: acc.new_id + (month.new_id || 0),
    rdp: acc.rdp + (month.rdp || 0),
    total_form: acc.total_form + (month.total_form || 0),
    nominal: acc.nominal + (month.nominal || 0)
  }), { new_id: 0, rdp: 0, total_form: 0, nominal: 0 });

  // Get years for dropdown (current year and 2 previous)
  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1, currentYear - 2];

  if (loading && !yearlyData.length) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="report-crm-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="report-crm-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Report CRM</h1>
          <p className="text-slate-500 text-sm mt-1">Comprehensive OMSET reporting & analytics</p>
        </div>
        <button
          onClick={exportToExcel}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          data-testid="export-report-btn"
        >
          <FileSpreadsheet size={18} />
          Export Excel
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={18} className="text-slate-500" />
          <span className="font-medium text-slate-700">Filters</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Year</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              data-testid="year-filter"
            >
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Month (for Daily View)</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              data-testid="month-filter"
            >
              {MONTH_NAMES.map((name, idx) => (
                <option key={idx} value={idx}>{name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Product</label>
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              data-testid="product-filter"
            >
              <option value="">All Products</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Staff</label>
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              data-testid="staff-filter"
            >
              <option value="">All Staff</option>
              {staffList.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 overflow-x-auto">
        {[
          { id: 'yearly', label: 'Yearly Summary', icon: BarChart3 },
          { id: 'monthly', label: 'Monthly Detail', icon: Calendar },
          { id: 'daily', label: 'Daily Report', icon: Activity },
          { id: 'staff', label: 'Staff Performance', icon: Users }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon size={18} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Yearly Summary Tab */}
      {activeTab === 'yearly' && (
        <div className="space-y-6" data-testid="yearly-tab-content">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-4 text-white">
              <div className="flex items-center gap-2 mb-2">
                <Users size={20} className="opacity-80" />
                <span className="text-sm opacity-80">Total NDP</span>
              </div>
              <div className="text-2xl font-bold">{formatNumber(yearlyTotals.new_id)}</div>
              <div className="text-xs opacity-70 mt-1">New Depositors</div>
            </div>
            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 text-white">
              <div className="flex items-center gap-2 mb-2">
                <RefreshCw size={20} className="opacity-80" />
                <span className="text-sm opacity-80">Total RDP</span>
              </div>
              <div className="text-2xl font-bold">{formatNumber(yearlyTotals.rdp)}</div>
              <div className="text-xs opacity-70 mt-1">Re-Depositors</div>
            </div>
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-4 text-white">
              <div className="flex items-center gap-2 mb-2">
                <FileSpreadsheet size={20} className="opacity-80" />
                <span className="text-sm opacity-80">Total Form</span>
              </div>
              <div className="text-2xl font-bold">{formatNumber(yearlyTotals.total_form)}</div>
              <div className="text-xs opacity-70 mt-1">Submissions</div>
            </div>
            <div className="bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl p-4 text-white">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign size={20} className="opacity-80" />
                <span className="text-sm opacity-80">Total OMSET</span>
              </div>
              <div className="text-2xl font-bold">{formatRupiah(yearlyTotals.nominal)}</div>
              <div className="text-xs opacity-70 mt-1">Nominal Value</div>
            </div>
          </div>

          {/* Deposit Frequency Tiers */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <PieChart size={18} className="text-blue-600" />
              Deposit Frequency Analysis
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{formatNumber(depositTiers['2x'])}</div>
                <div className="text-sm text-slate-600 mt-1">2x Deposit</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{formatNumber(depositTiers['3x'])}</div>
                <div className="text-sm text-slate-600 mt-1">3x Deposit</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{formatNumber(depositTiers['4x_plus'])}</div>
                <div className="text-sm text-slate-600 mt-1">&gt;4x Deposit</div>
              </div>
            </div>
          </div>

          {/* Yearly Table */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800">Yearly Report {selectedYear}</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">BULAN</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-slate-600">NEW ID (NDP)</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-slate-600">ID RDP</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-slate-600">TOTAL FORM</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-slate-600">NOMINAL (OMSET)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {MONTHS.map((month, idx) => {
                    const data = yearlyData.find(d => d.month === idx + 1) || { new_id: 0, rdp: 0, total_form: 0, nominal: 0 };
                    return (
                      <tr key={month} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm font-medium text-slate-900">{month}</td>
                        <td className="px-4 py-3 text-sm text-right text-blue-600 font-medium">{formatNumber(data.new_id)}</td>
                        <td className="px-4 py-3 text-sm text-right text-green-600 font-medium">{formatNumber(data.rdp)}</td>
                        <td className="px-4 py-3 text-sm text-right text-purple-600 font-medium">{formatNumber(data.total_form)}</td>
                        <td className="px-4 py-3 text-sm text-right text-amber-600 font-medium">{formatRupiah(data.nominal)}</td>
                      </tr>
                    );
                  })}
                  <tr className="bg-slate-100 font-bold">
                    <td className="px-4 py-3 text-sm text-slate-900">TOTAL</td>
                    <td className="px-4 py-3 text-sm text-right text-blue-700">{formatNumber(yearlyTotals.new_id)}</td>
                    <td className="px-4 py-3 text-sm text-right text-green-700">{formatNumber(yearlyTotals.rdp)}</td>
                    <td className="px-4 py-3 text-sm text-right text-purple-700">{formatNumber(yearlyTotals.total_form)}</td>
                    <td className="px-4 py-3 text-sm text-right text-amber-700">{formatRupiah(yearlyTotals.nominal)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Monthly Detail Tab */}
      {activeTab === 'monthly' && (
        <div className="space-y-4" data-testid="monthly-tab-content">
          {MONTHS.map((month, idx) => {
            const monthData = monthlyData.filter(d => d.month === idx + 1);
            const monthTotals = monthData.reduce((acc, d) => ({
              new_id: acc.new_id + (d.new_id || 0),
              rdp: acc.rdp + (d.rdp || 0),
              total_form: acc.total_form + (d.total_form || 0),
              nominal: acc.nominal + (d.nominal || 0)
            }), { new_id: 0, rdp: 0, total_form: 0, nominal: 0 });
            const isExpanded = expandedMonths[month];
            
            return (
              <div key={month} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <button
                  onClick={() => toggleMonth(month)}
                  className="w-full px-4 py-3 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <span className="font-semibold text-slate-800">{MONTH_NAMES[idx]} {selectedYear}</span>
                    <div className="flex gap-4 text-sm">
                      <span className="text-blue-600">NDP: {formatNumber(monthTotals.new_id)}</span>
                      <span className="text-green-600">RDP: {formatNumber(monthTotals.rdp)}</span>
                      <span className="text-amber-600">{formatRupiah(monthTotals.nominal)}</span>
                    </div>
                  </div>
                  {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </button>
                
                {isExpanded && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-3 py-2 text-left text-slate-600">Tanggal</th>
                          <th className="px-3 py-2 text-right text-slate-600">NEW ID</th>
                          <th className="px-3 py-2 text-right text-slate-600">ID RDP</th>
                          <th className="px-3 py-2 text-right text-slate-600">TOTAL FORM</th>
                          <th className="px-3 py-2 text-right text-slate-600">NOMINAL</th>
                          <th className="px-3 py-2 text-right text-slate-600">AVG/DAY</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {monthData.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                              No data for this month
                            </td>
                          </tr>
                        ) : (
                          monthData.map((d, i) => (
                            <tr key={i} className="hover:bg-slate-50">
                              <td className="px-3 py-2 text-slate-900">{d.date}</td>
                              <td className="px-3 py-2 text-right text-blue-600">{formatNumber(d.new_id)}</td>
                              <td className="px-3 py-2 text-right text-green-600">{formatNumber(d.rdp)}</td>
                              <td className="px-3 py-2 text-right text-purple-600">{formatNumber(d.total_form)}</td>
                              <td className="px-3 py-2 text-right text-amber-600">{formatRupiah(d.nominal)}</td>
                              <td className="px-3 py-2 text-right text-slate-500">
                                {d.total_form > 0 ? formatRupiah(Math.round(d.nominal / d.total_form)) : '-'}
                              </td>
                            </tr>
                          ))
                        )}
                        {monthData.length > 0 && (
                          <tr className="bg-slate-100 font-semibold">
                            <td className="px-3 py-2 text-slate-900">TOTAL</td>
                            <td className="px-3 py-2 text-right text-blue-700">{formatNumber(monthTotals.new_id)}</td>
                            <td className="px-3 py-2 text-right text-green-700">{formatNumber(monthTotals.rdp)}</td>
                            <td className="px-3 py-2 text-right text-purple-700">{formatNumber(monthTotals.total_form)}</td>
                            <td className="px-3 py-2 text-right text-amber-700">{formatRupiah(monthTotals.nominal)}</td>
                            <td className="px-3 py-2 text-right text-slate-600">
                              {monthTotals.total_form > 0 ? formatRupiah(Math.round(monthTotals.nominal / monthTotals.total_form)) : '-'}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}

          {/* Grand Total for Monthly Detail */}
          {monthlyData.length > 0 && (
            <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl shadow-sm p-4 text-white">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-lg">Grand Total - {selectedYear}</span>
                <div className="flex gap-6 text-sm">
                  <span>NDP: <strong>{formatNumber(monthlyData.reduce((sum, d) => sum + (d.new_id || 0), 0))}</strong></span>
                  <span>RDP: <strong>{formatNumber(monthlyData.reduce((sum, d) => sum + (d.rdp || 0), 0))}</strong></span>
                  <span>Form: <strong>{formatNumber(monthlyData.reduce((sum, d) => sum + (d.total_form || 0), 0))}</strong></span>
                  <span className="text-amber-300 text-lg font-bold">
                    {formatRupiah(monthlyData.reduce((sum, d) => sum + (d.nominal || 0), 0))}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Daily Report Tab - Grouped by Staff and Product */}
      {activeTab === 'daily' && (
        <div className="space-y-4" data-testid="daily-tab-content">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">
                Daily Report - {MONTH_NAMES[selectedMonth]} {selectedYear}
              </h3>
              <span className="text-sm text-slate-500">{dailyByStaff.length} staff with data</span>
            </div>
          </div>

          {dailyByStaff.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center text-slate-500">
              No data for this month
            </div>
          ) : (
            dailyByStaff.map((staff) => {
              const isStaffExpanded = expandedStaff[staff.staff_id];
              const staffTotals = staff.totals;
              
              return (
                <div key={staff.staff_id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                  {/* Staff Header */}
                  <button
                    onClick={() => toggleStaff(staff.staff_id)}
                    className="w-full px-4 py-4 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-lg">
                        {staff.staff_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="text-left">
                        <div className="font-semibold text-slate-800">{staff.staff_name}</div>
                        <div className="text-sm text-slate-500">{staff.products.length} product(s)</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="flex gap-4 text-sm">
                          <span className="text-blue-600 font-medium">NDP: {formatNumber(staffTotals.new_id)}</span>
                          <span className="text-green-600 font-medium">RDP: {formatNumber(staffTotals.rdp)}</span>
                          <span className="text-purple-600 font-medium">Form: {formatNumber(staffTotals.total_form)}</span>
                        </div>
                        <div className="text-amber-600 font-bold text-lg">{formatRupiah(staffTotals.nominal)}</div>
                      </div>
                      {isStaffExpanded ? <ChevronUp size={24} className="text-slate-400" /> : <ChevronDown size={24} className="text-slate-400" />}
                    </div>
                  </button>

                  {/* Staff Content - Products */}
                  {isStaffExpanded && (
                    <div className="p-4 space-y-3 bg-slate-50">
                      {staff.products.map((product) => {
                        const productKey = `${staff.staff_id}-${product.product_id}`;
                        const isProductExpanded = expandedProducts[productKey];
                        const productTotals = product.totals;
                        
                        return (
                          <div key={product.product_id} className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                            {/* Product Header */}
                            <button
                              onClick={() => toggleProduct(staff.staff_id, product.product_id)}
                              className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors"
                            >
                              <div className="flex items-center gap-3">
                                <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                                  {product.product_name}
                                </span>
                                <span className="text-sm text-slate-500">{product.daily.length} day(s)</span>
                              </div>
                              <div className="flex items-center gap-4">
                                <div className="flex gap-3 text-sm">
                                  <span className="text-blue-600">NDP: {formatNumber(productTotals.new_id)}</span>
                                  <span className="text-green-600">RDP: {formatNumber(productTotals.rdp)}</span>
                                  <span className="text-amber-600 font-semibold">{formatRupiah(productTotals.nominal)}</span>
                                </div>
                                {isProductExpanded ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
                              </div>
                            </button>

                            {/* Product Daily Data */}
                            {isProductExpanded && (
                              <div className="border-t border-slate-200">
                                <table className="w-full text-sm">
                                  <thead className="bg-slate-50">
                                    <tr>
                                      <th className="px-4 py-2 text-left text-slate-600">Tanggal</th>
                                      <th className="px-4 py-2 text-right text-slate-600">NDP</th>
                                      <th className="px-4 py-2 text-right text-slate-600">RDP</th>
                                      <th className="px-4 py-2 text-right text-slate-600">Form</th>
                                      <th className="px-4 py-2 text-right text-slate-600">Nominal</th>
                                      <th className="px-4 py-2 text-right text-slate-600">AVG/Form</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-100">
                                    {product.daily.map((day, idx) => {
                                      const avgPerForm = day.total_form > 0 ? Math.round(day.nominal / day.total_form) : 0;
                                      return (
                                        <tr key={idx} className="hover:bg-slate-50">
                                          <td className="px-4 py-2 text-slate-900">{day.date}</td>
                                          <td className="px-4 py-2 text-right text-blue-600 font-medium">{formatNumber(day.new_id)}</td>
                                          <td className="px-4 py-2 text-right text-green-600 font-medium">{formatNumber(day.rdp)}</td>
                                          <td className="px-4 py-2 text-right text-purple-600 font-medium">{formatNumber(day.total_form)}</td>
                                          <td className="px-4 py-2 text-right text-amber-600 font-medium">{formatRupiah(day.nominal)}</td>
                                          <td className="px-4 py-2 text-right text-slate-500">{formatRupiah(avgPerForm)}</td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                  <tfoot className="bg-slate-100">
                                    <tr className="font-semibold">
                                      <td className="px-4 py-2 text-slate-900">Total</td>
                                      <td className="px-4 py-2 text-right text-blue-700">{formatNumber(productTotals.new_id)}</td>
                                      <td className="px-4 py-2 text-right text-green-700">{formatNumber(productTotals.rdp)}</td>
                                      <td className="px-4 py-2 text-right text-purple-700">{formatNumber(productTotals.total_form)}</td>
                                      <td className="px-4 py-2 text-right text-amber-700">{formatRupiah(productTotals.nominal)}</td>
                                      <td className="px-4 py-2 text-right text-slate-600">
                                        {productTotals.total_form > 0 ? formatRupiah(Math.round(productTotals.nominal / productTotals.total_form)) : '-'}
                                      </td>
                                    </tr>
                                  </tfoot>
                                </table>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Grand Total */}
          {dailyByStaff.length > 0 && (
            <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl shadow-sm p-4 text-white">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-lg">Grand Total - {MONTH_NAMES[selectedMonth]} {selectedYear}</span>
                <div className="flex gap-6 text-sm">
                  <span>NDP: <strong>{formatNumber(dailyByStaff.reduce((sum, s) => sum + s.totals.new_id, 0))}</strong></span>
                  <span>RDP: <strong>{formatNumber(dailyByStaff.reduce((sum, s) => sum + s.totals.rdp, 0))}</strong></span>
                  <span>Form: <strong>{formatNumber(dailyByStaff.reduce((sum, s) => sum + s.totals.total_form, 0))}</strong></span>
                  <span className="text-amber-300 text-lg font-bold">
                    {formatRupiah(dailyByStaff.reduce((sum, s) => sum + s.totals.nominal, 0))}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Staff Performance Tab */}
      {activeTab === 'staff' && (
        <div className="space-y-4" data-testid="staff-tab-content">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800">Staff Performance - {selectedYear}</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-slate-600">Staff</th>
                    <th className="px-4 py-3 text-right text-slate-600">NEW ID (NDP)</th>
                    <th className="px-4 py-3 text-right text-slate-600">ID RDP</th>
                    <th className="px-4 py-3 text-right text-slate-600">TOTAL FORM</th>
                    <th className="px-4 py-3 text-right text-slate-600">TOTAL OMSET</th>
                    <th className="px-4 py-3 text-right text-slate-600">AVG/FORM</th>
                    <th className="px-4 py-3 text-right text-slate-600">% NDP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {staffPerformance.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                        No staff data available
                      </td>
                    </tr>
                  ) : (
                    staffPerformance.map((staff, i) => {
                      const totalCustomers = (staff.new_id || 0) + (staff.rdp || 0);
                      const ndpPercent = totalCustomers > 0 ? ((staff.new_id || 0) / totalCustomers * 100).toFixed(1) : 0;
                      const avgPerForm = staff.total_form > 0 ? Math.round((staff.nominal || 0) / staff.total_form) : 0;
                      
                      return (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="px-4 py-3">
                            <div className="font-medium text-slate-900">{staff.staff_name}</div>
                          </td>
                          <td className="px-4 py-3 text-right text-blue-600 font-medium">{formatNumber(staff.new_id)}</td>
                          <td className="px-4 py-3 text-right text-green-600 font-medium">{formatNumber(staff.rdp)}</td>
                          <td className="px-4 py-3 text-right text-purple-600 font-medium">{formatNumber(staff.total_form)}</td>
                          <td className="px-4 py-3 text-right text-amber-600 font-medium">{formatRupiah(staff.nominal)}</td>
                          <td className="px-4 py-3 text-right text-slate-600">{formatRupiah(avgPerForm)}</td>
                          <td className="px-4 py-3 text-right">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              ndpPercent >= 50 ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
                            }`}>
                              {ndpPercent}%
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
                {staffPerformance.length > 0 && (
                  <tfoot className="bg-slate-100">
                    <tr className="font-bold">
                      <td className="px-4 py-3 text-slate-900">TOTAL</td>
                      <td className="px-4 py-3 text-right text-blue-700">
                        {formatNumber(staffPerformance.reduce((sum, s) => sum + (s.new_id || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right text-green-700">
                        {formatNumber(staffPerformance.reduce((sum, s) => sum + (s.rdp || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right text-purple-700">
                        {formatNumber(staffPerformance.reduce((sum, s) => sum + (s.total_form || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right text-amber-700">
                        {formatRupiah(staffPerformance.reduce((sum, s) => sum + (s.nominal || 0), 0))}
                      </td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">-</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
