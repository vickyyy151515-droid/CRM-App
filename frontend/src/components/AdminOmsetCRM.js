import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Calendar, Package, DollarSign, TrendingUp, Users, ChevronDown, ChevronUp, UserPlus, RefreshCw, Download, Trash2, Clock, RotateCcw, AlertTriangle } from 'lucide-react';
import OmsetFilterPanel from './shared/OmsetFilterPanel';
import ViewModeToggle from './shared/ViewModeToggle';
import OmsetStatsGrid, { formatCurrency } from './shared/OmsetStatsGrid';
import TrashSection from './shared/TrashSection';

// Helper function to get local date in YYYY-MM-DD format (fallback only)
const getLocalDateString = (date = new Date()) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export default function AdminOmsetCRM() {
  const [products, setProducts] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [dateRange, setDateRange] = useState('today');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [records, setRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedDates, setExpandedDates] = useState({});
  const [expandedCustomers, setExpandedCustomers] = useState({});
  const [viewMode, setViewMode] = useState('summary');
  const [serverDate, setServerDate] = useState(null); // Jakarta timezone date from server
  const [deletingRecord, setDeletingRecord] = useState(null);
  const [trashRecords, setTrashRecords] = useState([]);
  const [showTrash, setShowTrash] = useState(false);
  const [restoringRecord, setRestoringRecord] = useState(null);

  // Fetch server time (Jakarta timezone) on mount
  useEffect(() => {
    const fetchServerTime = async () => {
      try {
        const response = await api.get('/server-time');
        setServerDate(response.data.date); // YYYY-MM-DD in Jakarta timezone
      } catch (error) {
        console.error('Failed to fetch server time, using local time as fallback');
        setServerDate(getLocalDateString());
      }
    };
    fetchServerTime();
  }, []);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (serverDate) {
      loadData();
    }
  }, [selectedProduct, selectedStaff, dateRange, startDate, endDate, serverDate]);

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

  const getDateParams = useCallback(() => {
    // Use server date (Jakarta timezone) as the reference point
    const todayStr = serverDate || getLocalDateString();
    
    // Parse server date to calculate other dates
    const [year, month, day] = todayStr.split('-').map(Number);
    const today = new Date(year, month - 1, day);
    
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;
    
    const last7 = new Date(today);
    last7.setDate(last7.getDate() - 7);
    const last7Str = `${last7.getFullYear()}-${String(last7.getMonth() + 1).padStart(2, '0')}-${String(last7.getDate()).padStart(2, '0')}`;
    
    const last30 = new Date(today);
    last30.setDate(last30.getDate() - 30);
    const last30Str = `${last30.getFullYear()}-${String(last30.getMonth() + 1).padStart(2, '0')}-${String(last30.getDate()).padStart(2, '0')}`;
    
    const thisMonth = new Date(year, month - 1, 1);
    const thisMonthStr = `${thisMonth.getFullYear()}-${String(thisMonth.getMonth() + 1).padStart(2, '0')}-01`;
    
    switch (dateRange) {
      case 'today':
        return { start_date: todayStr, end_date: todayStr };
      case 'yesterday':
        return { start_date: yesterdayStr, end_date: yesterdayStr };
      case 'last7':
        return { start_date: last7Str, end_date: todayStr };
      case 'last30':
        return { start_date: last30Str, end_date: todayStr };
      case 'thisMonth':
        return { start_date: thisMonthStr, end_date: todayStr };
      case 'custom':
        return { start_date: startDate, end_date: endDate };
      default:
        return {};
    }
  }, [serverDate, dateRange, startDate, endDate]);

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

  const handleExportDetails = () => {
    const dateParams = getDateParams();
    const token = localStorage.getItem('token');
    const params = new URLSearchParams({
      ...dateParams,
      ...(selectedProduct && { product_id: selectedProduct }),
      ...(selectedStaff && { staff_id: selectedStaff }),
      token: token
    });
    
    // Use hidden iframe to trigger download (bypasses sandbox restrictions)
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/omset/export?${params}`;
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);
    
    // Clean up iframe after download starts
    setTimeout(() => {
      document.body.removeChild(iframe);
    }, 5000);
    
    toast.success('Download starting...');
  };

  const handleExportSummary = async () => {
    try {
      const dateParams = getDateParams();
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        ...dateParams,
        ...(selectedProduct && { product_id: selectedProduct }),
        token: token
      });
      
      toast.success('Preparing download...');
      
      // Use fetch to download the file
      const url = `${process.env.REACT_APP_BACKEND_URL}/api/omset/export-summary?${params}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      
      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'omset_summary.csv';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) filename = match[1];
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success('Download complete!');
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Failed to export summary');
    }
  };

  const toggleDateExpand = (date) => {
    setExpandedDates(prev => ({ ...prev, [date]: !prev[date] }));
  };

  const toggleCustomerExpand = (customerKey) => {
    setExpandedCustomers(prev => ({ ...prev, [customerKey]: !prev[customerKey] }));
  };

  const handleDeleteOmsetRecord = async (recordId, customerInfo) => {
    const confirmMsg = `Delete this OMSET record?\n\nCustomer: ${customerInfo.customer_id}\nAmount: Rp ${formatCurrency(customerInfo.amount)}\nTime: ${customerInfo.time}\n\nYou can restore it from the Trash.`;
    
    if (!window.confirm(confirmMsg)) {
      return;
    }

    setDeletingRecord(recordId);
    try {
      await api.delete(`/omset/${recordId}`);
      toast.success('OMSET record moved to trash - you can restore it if needed');
      // Refresh the data
      loadData();
      loadTrash(); // Also refresh trash
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete record');
    } finally {
      setDeletingRecord(null);
    }
  };

  // Load trash records
  const loadTrash = useCallback(async () => {
    try {
      const response = await api.get('/omset/trash?limit=20');
      setTrashRecords(response.data.records || []);
    } catch (error) {
      console.error('Error loading trash:', error);
    }
  }, []);

  // Load trash on mount
  useEffect(() => {
    loadTrash();
  }, [loadTrash]);

  // Restore a deleted record
  const handleRestoreRecord = async (recordId, recordInfo) => {
    setRestoringRecord(recordId);
    try {
      await api.post(`/omset/restore/${recordId}`);
      toast.success(`Restored OMSET for ${recordInfo.customer_id}`);
      loadData(); // Refresh main data
      loadTrash(); // Refresh trash
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore record');
    } finally {
      setRestoringRecord(null);
    }
  };

  // Permanently delete from trash
  const handlePermanentDelete = async (recordId) => {
    if (!window.confirm('Permanently delete this record? This cannot be undone!')) {
      return;
    }
    
    try {
      await api.delete(`/omset/trash/${recordId}`);
      toast.success('Record permanently deleted');
      loadTrash();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete');
    }
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
      <OmsetFilterPanel
        dateRange={dateRange}
        setDateRange={setDateRange}
        startDate={startDate}
        setStartDate={setStartDate}
        endDate={endDate}
        setEndDate={setEndDate}
        products={products}
        selectedProduct={selectedProduct}
        setSelectedProduct={setSelectedProduct}
        staffList={staffList}
        selectedStaff={selectedStaff}
        setSelectedStaff={setSelectedStaff}
      />

      {/* Overall Summary - OMSET per Product + NDP/RDP */}
      <OmsetStatsGrid summary={summary} />

      {/* View Toggle and Export */}
      <ViewModeToggle
        viewMode={viewMode}
        setViewMode={setViewMode}
        onExportSummary={handleExportSummary}
        onExportDetails={handleExportDetails}
      />

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

      {/* Detail View - Records by Date (Aggregated by Customer) */}
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
                const isExpanded = expandedDates[date] !== false;
                
                // Get NDP/RDP stats for this date from summary
                const daySummary = summary?.daily.find(d => d.date === date);
                
                // Aggregate records by customer, but keep individual records for expansion
                const customerData = {};
                dateRecords.forEach(record => {
                  const key = `${date}_${record.customer_id}_${record.staff_id}_${record.product_id}`;
                  if (!customerData[key]) {
                    customerData[key] = {
                      key,
                      customer_id: record.customer_id,
                      staff_name: record.staff_name,
                      staff_id: record.staff_id,
                      product_name: record.product_name,
                      product_id: record.product_id,
                      total_depo: 0,
                      records: []
                    };
                  }
                  customerData[key].total_depo += record.depo_total || 0;
                  customerData[key].records.push(record);
                });
                
                const aggregatedCustomers = Object.values(customerData).sort((a, b) => b.total_depo - a.total_depo);

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
                            <span className="text-sm text-slate-500">{aggregatedCustomers.length} customers</span>
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
                      <div className="border-t border-slate-200">
                        <table className="w-full">
                          <thead className="bg-slate-50">
                            <tr>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700 w-8"></th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">No</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Staff</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Product</th>
                              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-700">Customer ID</th>
                              <th className="px-4 py-2 text-center text-xs font-semibold text-slate-700">Deposits</th>
                              <th className="px-4 py-2 text-right text-xs font-semibold text-slate-700">Total OMSET</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {aggregatedCustomers.map((customer, idx) => {
                              const isCustomerExpanded = expandedCustomers[customer.key];
                              return (
                                <React.Fragment key={customer.key}>
                                  {/* Customer Row */}
                                  <tr 
                                    className={`hover:bg-slate-50 cursor-pointer ${isCustomerExpanded ? 'bg-indigo-50' : ''}`}
                                    onClick={() => toggleCustomerExpand(customer.key)}
                                  >
                                    <td className="px-4 py-2 text-center">
                                      {customer.records.length > 1 ? (
                                        isCustomerExpanded ? 
                                          <ChevronUp size={16} className="text-indigo-600" /> : 
                                          <ChevronDown size={16} className="text-slate-400" />
                                      ) : (
                                        <span className="text-slate-300">-</span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-sm text-slate-600">{idx + 1}</td>
                                    <td className="px-4 py-2 text-sm font-medium text-slate-900">{customer.staff_name}</td>
                                    <td className="px-4 py-2">
                                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
                                        {customer.product_name}
                                      </span>
                                    </td>
                                    <td className="px-4 py-2 text-sm text-slate-900 font-mono">{customer.customer_id}</td>
                                    <td className="px-4 py-2 text-center">
                                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                        customer.records.length > 1 
                                          ? 'bg-amber-100 text-amber-800' 
                                          : 'bg-slate-100 text-slate-600'
                                      }`}>
                                        {customer.records.length}x
                                      </span>
                                    </td>
                                    <td className="px-4 py-2 text-sm text-right font-semibold text-emerald-600">
                                      Rp {formatCurrency(customer.total_depo)}
                                    </td>
                                  </tr>
                                  
                                  {/* Expanded Individual Records */}
                                  {isCustomerExpanded && (
                                    <tr>
                                      <td colSpan={7} className="p-0">
                                        <div className="bg-slate-50 border-y border-slate-200">
                                          <div className="px-6 py-2 bg-slate-100 border-b border-slate-200">
                                            <span className="text-xs font-semibold text-slate-600">
                                              Individual Deposits for {customer.customer_id}
                                            </span>
                                          </div>
                                          <table className="w-full">
                                            <thead className="bg-slate-100/50">
                                              <tr>
                                                <th className="px-6 py-1.5 text-left text-xs font-medium text-slate-500">Time</th>
                                                <th className="px-4 py-1.5 text-left text-xs font-medium text-slate-500">Customer Name</th>
                                                <th className="px-4 py-1.5 text-right text-xs font-medium text-slate-500">Nominal</th>
                                                <th className="px-4 py-1.5 text-center text-xs font-medium text-slate-500">Multiplier</th>
                                                <th className="px-4 py-1.5 text-right text-xs font-medium text-slate-500">Total</th>
                                                <th className="px-4 py-1.5 text-left text-xs font-medium text-slate-500">Notes</th>
                                                <th className="px-4 py-1.5 text-center text-xs font-medium text-slate-500 w-16">Action</th>
                                              </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100">
                                              {customer.records
                                                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                                                .map((record, rIdx) => (
                                                  <tr key={record.id} className="hover:bg-white">
                                                    <td className="px-6 py-2 text-sm text-slate-600">
                                                      <span className="inline-flex items-center gap-1">
                                                        <Clock size={12} className="text-slate-400" />
                                                        {new Date(record.created_at).toLocaleTimeString('id-ID', { 
                                                          hour: '2-digit', 
                                                          minute: '2-digit' 
                                                        })}
                                                      </span>
                                                    </td>
                                                    <td className="px-4 py-2 text-sm text-slate-700">{record.customer_name}</td>
                                                    <td className="px-4 py-2 text-sm text-right text-slate-900">
                                                      Rp {formatCurrency(record.nominal)}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm text-center text-slate-600">
                                                      {record.depo_kelipatan}x
                                                    </td>
                                                    <td className="px-4 py-2 text-sm text-right font-medium text-emerald-600">
                                                      Rp {formatCurrency(record.depo_total)}
                                                    </td>
                                                    <td className="px-4 py-2 text-sm text-slate-500 max-w-[150px] truncate">
                                                      {record.keterangan || '-'}
                                                    </td>
                                                    <td className="px-4 py-2 text-center">
                                                      <button
                                                        onClick={(e) => {
                                                          e.stopPropagation();
                                                          handleDeleteOmsetRecord(record.id, {
                                                            customer_id: record.customer_id,
                                                            amount: record.depo_total,
                                                            time: new Date(record.created_at).toLocaleTimeString('id-ID', { 
                                                              hour: '2-digit', 
                                                              minute: '2-digit' 
                                                            })
                                                          });
                                                        }}
                                                        disabled={deletingRecord === record.id}
                                                        className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                                                        title="Delete this OMSET record"
                                                        data-testid={`delete-omset-${record.id}`}
                                                      >
                                                        {deletingRecord === record.id ? (
                                                          <RefreshCw size={16} className="animate-spin" />
                                                        ) : (
                                                          <Trash2 size={16} />
                                                        )}
                                                      </button>
                                                    </td>
                                                  </tr>
                                                ))}
                                            </tbody>
                                          </table>
                                        </div>
                                      </td>
                                    </tr>
                                  )}
                                </React.Fragment>
                              );
                            })}
                          </tbody>
                          <tfoot className="bg-slate-50 border-t border-slate-200">
                            <tr>
                              <td colSpan={6} className="px-4 py-2 text-sm font-semibold text-slate-900">DAY TOTAL</td>
                              <td className="px-4 py-2 text-sm text-right font-bold text-emerald-600">Rp {formatCurrency(dayTotal)}</td>
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

      {/* Trash Section */}
      <TrashSection
        showTrash={showTrash}
        setShowTrash={setShowTrash}
        trashRecords={trashRecords}
        onRefresh={loadTrash}
        onRestore={handleRestoreRecord}
        onPermanentDelete={handlePermanentDelete}
        restoringId={restoringRecord}
      />

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
