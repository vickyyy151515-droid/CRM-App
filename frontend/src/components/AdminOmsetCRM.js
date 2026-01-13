import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Calendar, Package, DollarSign, TrendingUp, Users, Filter, ChevronDown, ChevronUp, UserPlus, RefreshCw } from 'lucide-react';

export default function AdminOmsetCRM() {
  const [products, setProducts] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [dateRange, setDateRange] = useState('today');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [records, setRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedDates, setExpandedDates] = useState({});
  const [viewMode, setViewMode] = useState('summary');

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadData();
  }, [selectedProduct, selectedStaff, dateRange, startDate, endDate]);

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

  const getDateParams = () => {
    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    const last7 = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];
    const last30 = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
    const thisMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
    
    switch (dateRange) {
      case 'today':
        return { start_date: today, end_date: today };
      case 'yesterday':
        return { start_date: yesterday, end_date: yesterday };
      case 'last7':
        return { start_date: last7, end_date: today };
      case 'last30':
        return { start_date: last30, end_date: today };
      case 'thisMonth':
        return { start_date: thisMonth, end_date: today };
      case 'custom':
        return { start_date: startDate, end_date: endDate };
      default:
        return {};
    }
  };

  const loadData = async () => {
    try {
      const dateParams = getDateParams();
      const params = {
        ...dateParams,
        ...(selectedProduct && { product_id: selectedProduct }),
        ...(selectedStaff && { staff_id: selectedStaff })
      };

      const [recordsRes, summaryRes] = await Promise.all([
        api.get('/omset', { params }),
        api.get('/omset/summary', { params })
      ]);

      setRecords(recordsRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('id-ID').format(value || 0);
  };

  const toggleDateExpand = (date) => {
    setExpandedDates(prev => ({ ...prev, [date]: !prev[date] }));
  };

  // Group records by date
  const recordsByDate = records.reduce((acc, record) => {
    const date = record.record_date;
    if (!acc[date]) acc[date] = [];
    acc[date].push(record);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="admin-omset-crm">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">OMSET CRM - Admin View</h2>

      {/* Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="text-indigo-600" size={18} />
          <h3 className="font-medium text-slate-900">Filters</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Date Range</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="today">Today</option>
              <option value="yesterday">Yesterday</option>
              <option value="last7">Last 7 Days</option>
              <option value="last30">Last 30 Days</option>
              <option value="thisMonth">This Month</option>
              <option value="all">All Time</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>
          {dateRange === 'custom' && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Product</label>
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Products</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Staff</label>
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Staff</option>
              {staffList.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Overall Summary - OMSET per Product + NDP/RDP */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
          {summary.by_product.length === 0 ? (
            <div className="col-span-full bg-white border border-slate-200 rounded-xl p-6 text-center text-slate-500">
              No OMSET data for selected filters
            </div>
          ) : (
            <>
              {summary.by_product.map((product, idx) => {
                const colors = [
                  'from-indigo-500 to-indigo-600',
                  'from-blue-500 to-blue-600',
                  'from-purple-500 to-purple-600',
                  'from-cyan-500 to-cyan-600',
                  'from-teal-500 to-teal-600'
                ];
                const colorClass = colors[idx % colors.length];
                
                return (
                  <div key={product.product_id} className={`bg-gradient-to-br ${colorClass} rounded-xl p-4 text-white shadow-lg`}>
                    <div className="flex items-center justify-between mb-2">
                      <Package className="opacity-80" size={20} />
                      <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{product.count} rec</span>
                    </div>
                    <p className="text-white/80 text-xs font-medium mb-1">{product.product_name}</p>
                    <p className="text-xl font-bold">Rp {formatCurrency(product.total_depo)}</p>
                  </div>
                );
              })}
              
              {/* NDP Card */}
              <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 text-white shadow-lg">
                <div className="flex items-center justify-between mb-2">
                  <UserPlus className="opacity-80" size={20} />
                  <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{summary.total.total_ndp} NDP</span>
                </div>
                <p className="text-white/80 text-xs font-medium mb-1">Total NDP (New Depo)</p>
                <p className="text-xl font-bold">{summary.total.total_ndp}</p>
              </div>
              
              {/* RDP Card */}
              <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-4 text-white shadow-lg">
                <div className="flex items-center justify-between mb-2">
                  <RefreshCw className="opacity-80" size={20} />
                  <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{summary.total.total_rdp} RDP</span>
                </div>
                <p className="text-white/80 text-xs font-medium mb-1">Total RDP (Redepo)</p>
                <p className="text-xl font-bold">{summary.total.total_rdp}</p>
              </div>
              
              {/* Grand Total Card */}
              <div className="bg-gradient-to-br from-slate-700 to-slate-800 rounded-xl p-4 text-white shadow-lg">
                <div className="flex items-center justify-between mb-2">
                  <TrendingUp className="opacity-80" size={20} />
                  <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{summary.total.total_records} total</span>
                </div>
                <p className="text-white/80 text-xs font-medium mb-1">GRAND TOTAL</p>
                <p className="text-xl font-bold">Rp {formatCurrency(summary.total.total_depo)}</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* View Toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setViewMode('summary')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'summary' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Summary View
        </button>
        <button
          onClick={() => setViewMode('details')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'details' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Detail View
        </button>
      </div>

      {viewMode === 'summary' && summary && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Daily Summary with NDP/RDP */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Calendar className="text-indigo-600" size={18} />
                Daily Summary
              </h3>
            </div>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Date</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-700">Rec</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-green-700">NDP</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-orange-700">RDP</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-700">OMSET</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.daily.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-slate-500">No data</td>
                    </tr>
                  ) : (
                    summary.daily.map(day => (
                      <tr key={day.date} className="hover:bg-slate-50">
                        <td className="px-3 py-2 text-sm text-slate-900">
                          {new Date(day.date).toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short' })}
                        </td>
                        <td className="px-3 py-2 text-sm text-right text-slate-600">{day.count}</td>
                        <td className="px-3 py-2 text-sm text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">
                            {day.ndp_count}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-800">
                            {day.rdp_count}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-right font-semibold text-emerald-600">Rp {formatCurrency(day.total_depo)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Staff Summary with NDP/RDP */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Users className="text-indigo-600" size={18} />
                Staff Performance
              </h3>
            </div>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700">Staff</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-700">Rec</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-green-700">NDP</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-orange-700">RDP</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-700">OMSET</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.by_staff.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-slate-500">No data</td>
                    </tr>
                  ) : (
                    summary.by_staff.map(staff => (
                      <tr key={staff.staff_id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 text-sm font-medium text-slate-900">{staff.staff_name}</td>
                        <td className="px-3 py-2 text-sm text-right text-slate-600">{staff.count}</td>
                        <td className="px-3 py-2 text-sm text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">
                            {staff.ndp_count}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-800">
                            {staff.rdp_count}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-right font-semibold text-emerald-600">Rp {formatCurrency(staff.total_depo)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Product Summary with NDP/RDP */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden lg:col-span-2">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Package className="text-indigo-600" size={18} />
                Product Summary
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Product</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-slate-700">Records</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-green-700">NDP</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-orange-700">RDP</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-slate-700">Total OMSET</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.by_product.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-slate-500">No data</td>
                    </tr>
                  ) : (
                    summary.by_product.map(product => (
                      <tr key={product.product_id} className="hover:bg-slate-50">
                        <td className="px-4 py-2">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                            {product.product_name}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-sm text-right text-slate-600">{product.count}</td>
                        <td className="px-4 py-2 text-sm text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">
                            {product.ndp_count}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-sm text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-800">
                            {product.rdp_count}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-sm text-right font-semibold text-emerald-600">Rp {formatCurrency(product.total_depo)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Detail View - Records by Date */}
      {viewMode === 'details' && (
        <div className="space-y-4">
          {Object.keys(recordsByDate).length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
              No records found for the selected filters.
            </div>
          ) : (
            Object.entries(recordsByDate)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([date, dateRecords]) => {
                const dayTotal = dateRecords.reduce((sum, r) => sum + (r.depo_total || 0), 0);
                const dayNominal = dateRecords.reduce((sum, r) => sum + (r.nominal || 0), 0);
                const isExpanded = expandedDates[date] !== false;
                
                // Get NDP/RDP stats for this date from summary
                const daySummary = summary?.daily.find(d => d.date === date);

                return (
                  <div key={date} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                    <button
                      onClick={() => toggleDateExpand(date)}
                      className="w-full px-6 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <Calendar className="text-indigo-600" size={20} />
                        <div className="text-left">
                          <p className="font-semibold text-slate-900">
                            {new Date(date).toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                          </p>
                          <div className="flex items-center gap-3 mt-1">
                            <span className="text-sm text-slate-500">{dateRecords.length} records</span>
                            {daySummary && (
                              <>
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">
                                  {daySummary.ndp_count} NDP
                                </span>
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-800">
                                  {daySummary.rdp_count} RDP
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <p className="text-sm text-slate-500">Total OMSET</p>
                          <p className="font-bold text-emerald-600">Rp {formatCurrency(dayTotal)}</p>
                        </div>
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead className="bg-slate-50 border-t border-slate-200">
                            <tr>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">No</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Staff</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Product</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Customer ID</th>
                              <th className="px-4 py-2 text-right text-xs font-semibold text-slate-700">Nominal</th>
                              <th className="px-4 py-2 text-right text-xs font-semibold text-slate-700">Kelipatan</th>
                              <th className="px-4 py-2 text-right text-xs font-semibold text-slate-700">Depo Total</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Notes</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {dateRecords.map((record, idx) => (
                              <tr key={record.id} className="hover:bg-slate-50">
                                <td className="px-4 py-2 text-sm text-slate-600">{idx + 1}</td>
                                <td className="px-4 py-2 text-sm font-medium text-slate-900">{record.staff_name}</td>
                                <td className="px-4 py-2">
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
                                    {record.product_name}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-sm text-slate-900">{record.customer_id}</td>
                                <td className="px-4 py-2 text-sm text-right text-slate-900">Rp {formatCurrency(record.nominal)}</td>
                                <td className="px-4 py-2 text-sm text-right text-slate-600">{record.depo_kelipatan}x</td>
                                <td className="px-4 py-2 text-sm text-right font-semibold text-emerald-600">Rp {formatCurrency(record.depo_total)}</td>
                                <td className="px-4 py-2 text-sm text-slate-500">{record.keterangan || '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-slate-50 border-t border-slate-200">
                            <tr>
                              <td colSpan={4} className="px-4 py-2 text-sm font-semibold text-slate-900">DAY TOTAL</td>
                              <td className="px-4 py-2 text-sm text-right font-bold text-slate-900">Rp {formatCurrency(dayNominal)}</td>
                              <td></td>
                              <td className="px-4 py-2 text-sm text-right font-bold text-emerald-600">Rp {formatCurrency(dayTotal)}</td>
                              <td></td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })
          )}
        </div>
      )}

      {/* Legend */}
      <div className="mt-6 flex gap-4 text-sm text-slate-600">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">NDP</span>
          <span>= New Depo (Customer baru)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-800">RDP</span>
          <span>= Redepo (Customer lama)</span>
        </div>
      </div>
    </div>
  );
}
