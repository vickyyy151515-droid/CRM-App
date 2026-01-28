/**
 * AttendanceAdmin - Admin dashboard for viewing attendance records and managing TOTP
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Users, Clock, CheckCircle, AlertTriangle, RefreshCw, 
  Calendar, UserX, Shield, Search, ChevronDown,
  ChevronUp, Key, Trash2, DollarSign, CreditCard, XCircle, Ban,
  Plus, Settings, Edit2
} from 'lucide-react';

export default function AttendanceAdmin() {
  const [loading, setLoading] = useState(true);
  const [todayData, setTodayData] = useState(null);
  const [totpStatus, setTotpStatus] = useState([]);
  const [historyData, setHistoryData] = useState(null);
  const [activeTab, setActiveTab] = useState('today');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedStaff, setExpandedStaff] = useState(null);
  const [resettingTotp, setResettingTotp] = useState(null);
  
  // Fee & Payment state
  const [feeData, setFeeData] = useState(null);
  const [feeYear, setFeeYear] = useState(new Date().getFullYear());
  const [feeMonth, setFeeMonth] = useState(new Date().getMonth() + 1);
  const [expandedFeeStaff, setExpandedFeeStaff] = useState(null);
  const [processingFee, setProcessingFee] = useState(null);
  const [waiveModal, setWaiveModal] = useState(null);
  const [waiveReason, setWaiveReason] = useState('');
  const [installmentModal, setInstallmentModal] = useState(null);
  const [installmentMonths, setInstallmentMonths] = useState(2);
  
  // New: Manual fee & payment state
  const [staffList, setStaffList] = useState([]);
  const [manualFeeModal, setManualFeeModal] = useState(false);
  const [manualFeeStaffId, setManualFeeStaffId] = useState('');
  const [manualFeeAmount, setManualFeeAmount] = useState('');
  const [manualFeeReason, setManualFeeReason] = useState('');
  const [paymentModal, setPaymentModal] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentCurrency, setPaymentCurrency] = useState('USD');
  const [paymentNote, setPaymentNote] = useState('');
  const [currencyModal, setCurrencyModal] = useState(false);
  const [thbRate, setThbRate] = useState(3100);
  const [idrRate, setIdrRate] = useState(16700);

  // Fetch today's attendance
  const fetchTodayAttendance = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/today');
      setTodayData(response.data);
    } catch (error) {
      console.error('Error fetching today attendance:', error);
      toast.error('Failed to load today\'s attendance');
    }
  }, []);

  // Fetch TOTP setup status
  const fetchTotpStatus = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/totp-status');
      setTotpStatus(response.data.staff || []);
    } catch (error) {
      console.error('Error fetching TOTP status:', error);
    }
  }, []);

  // Fetch attendance history
  const fetchHistory = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await api.get(`/attendance/admin/records?${params}`);
      setHistoryData(response.data);
    } catch (error) {
      console.error('Error fetching history:', error);
      toast.error('Failed to load attendance history');
    }
  }, [startDate, endDate]);

  // Fetch fee summary
  const fetchFees = useCallback(async () => {
    try {
      const response = await api.get(`/attendance/admin/fees/summary?year=${feeYear}&month=${feeMonth}`);
      setFeeData(response.data);
    } catch (error) {
      console.error('Error fetching fees:', error);
      toast.error('Failed to load fee data');
    }
  }, [feeYear, feeMonth]);

  // Initial data fetch
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchTodayAttendance(), fetchTotpStatus()]);
      setLoading(false);
    };
    loadData();
  }, [fetchTodayAttendance, fetchTotpStatus]);

  // Fetch history when tab changes or dates change
  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
    if (activeTab === 'fee-payment') {
      fetchFees();
    }
  }, [activeTab, fetchHistory, fetchFees]);

  // Reset staff TOTP
  const handleResetTotp = async (staffId, staffName) => {
    if (!window.confirm(`Reset authenticator for ${staffName}? They will need to set up again.`)) {
      return;
    }

    setResettingTotp(staffId);
    try {
      await api.delete(`/attendance/admin/totp/${staffId}`);
      toast.success(`Authenticator reset for ${staffName}`);
      fetchTotpStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset authenticator');
    } finally {
      setResettingTotp(null);
    }
  };

  // Waive fee for a specific date
  const handleWaiveFee = async (staffId, date) => {
    if (!waiveReason.trim()) {
      toast.error('Please provide a reason for waiving the fee');
      return;
    }
    setProcessingFee(`${staffId}-${date}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/waive?date=${date}`, {
        reason: waiveReason
      });
      toast.success('Fee waived successfully');
      setWaiveModal(null);
      setWaiveReason('');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to waive fee');
    } finally {
      setProcessingFee(null);
    }
  };

  // Setup installment plan
  const handleSetupInstallment = async (staffId) => {
    setProcessingFee(`installment-${staffId}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/installment?year=${feeYear}&month=${feeMonth}`, {
        num_months: installmentMonths
      });
      toast.success(`Installment plan created for ${installmentMonths} month(s)`);
      setInstallmentModal(null);
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to setup installment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Cancel installment plan
  const handleCancelInstallment = async (staffId) => {
    if (!window.confirm('Cancel this installment plan?')) return;
    setProcessingFee(`cancel-installment-${staffId}`);
    try {
      await api.delete(`/attendance/admin/fees/${staffId}/installment?year=${feeYear}&month=${feeMonth}`);
      toast.success('Installment plan cancelled');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel installment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Record payment for installment
  const handleRecordPayment = async (staffId, paymentMonth) => {
    setProcessingFee(`pay-${staffId}-${paymentMonth}`);
    try {
      await api.post(`/attendance/admin/fees/${staffId}/pay?year=${feeYear}&month=${feeMonth}&payment_month=${paymentMonth}`);
      toast.success('Payment recorded successfully');
      fetchFees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setProcessingFee(null);
    }
  };

  // Filter staff by search
  const filteredTotpStatus = totpStatus.filter(staff => 
    staff.staff_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    staff.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="attendance-admin">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Attendance Management</h1>
          <p className="text-slate-600 dark:text-slate-400">TOTP-based attendance tracking</p>
        </div>
        <button
          onClick={() => { fetchTodayAttendance(); fetchTotpStatus(); }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
          data-testid="refresh-attendance-btn"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
        {['today', 'history', 'totp-setup', 'fee-payment'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium capitalize transition-colors whitespace-nowrap ${
              activeTab === tab 
                ? 'text-indigo-600 border-b-2 border-indigo-600' 
                : 'text-slate-600 dark:text-slate-400 hover:text-indigo-600'
            }`}
            data-testid={`tab-${tab}`}
          >
            {tab === 'totp-setup' ? 'TOTP Setup Status' : tab === 'fee-payment' ? 'Fee & Payment' : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Today Tab */}
      {activeTab === 'today' && todayData && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Users className="text-blue-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Total Staff</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{todayData.summary.total_staff}</p>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                  <CheckCircle className="text-emerald-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Checked In</p>
                  <p className="text-2xl font-bold text-emerald-600">{todayData.summary.checked_in}</p>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                  <Clock className="text-amber-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Late</p>
                  <p className="text-2xl font-bold text-amber-600">{todayData.summary.late}</p>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                  <UserX className="text-red-600" size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Not Checked In</p>
                  <p className="text-2xl font-bold text-red-600">{todayData.summary.not_checked_in}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Today's Records Table */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-700">
              <h3 className="font-semibold text-slate-900 dark:text-white">Today's Attendance ({todayData.date})</h3>
            </div>
            
            {todayData.records.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full" data-testid="today-attendance-table">
                  <thead className="bg-slate-50 dark:bg-slate-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Staff</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Check-in Time</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Late (min)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {todayData.records.map((record, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                        <td className="px-4 py-3 text-slate-900 dark:text-white">{record.staff_name}</td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300 font-mono">{record.check_in_time}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            record.is_late 
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' 
                              : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                          }`}>
                            {record.is_late ? 'Late' : 'On Time'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                          {record.is_late ? record.late_minutes : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                No check-ins recorded today yet
              </div>
            )}
          </div>

          {/* Not Checked In List */}
          {todayData.not_checked_in.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-red-50 dark:bg-red-900/20">
                <h3 className="font-semibold text-red-700 dark:text-red-400 flex items-center gap-2">
                  <AlertTriangle size={18} />
                  Not Yet Checked In ({todayData.not_checked_in.length})
                </h3>
              </div>
              <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                {todayData.not_checked_in.map((staff, idx) => (
                  <div key={idx} className="px-3 py-2 bg-slate-50 dark:bg-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-300">
                    {staff.name}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {/* Date Filters */}
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
            <div className="flex flex-wrap gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="history-start-date"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="history-end-date"
                />
              </div>
              <button
                onClick={fetchHistory}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-2"
                data-testid="filter-history-btn"
              >
                <Search size={18} />
                Filter
              </button>
            </div>
          </div>

          {/* History Table */}
          {historyData && (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  Attendance History ({historyData.total_records} records)
                </h3>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {historyData.start_date} to {historyData.end_date}
                </span>
              </div>
              
              {historyData.records.length > 0 ? (
                <div className="overflow-x-auto max-h-[500px]">
                  <table className="w-full" data-testid="history-attendance-table">
                    <thead className="bg-slate-50 dark:bg-slate-900 sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Date</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Staff</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Check-in</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Status</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Late (min)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                      {historyData.records.map((record, idx) => (
                        <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                          <td className="px-4 py-3 text-slate-900 dark:text-white font-mono text-sm">{record.date}</td>
                          <td className="px-4 py-3 text-slate-900 dark:text-white">{record.staff_name}</td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300 font-mono">{record.check_in_time}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              record.is_late 
                                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' 
                                : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                            }`}>
                              {record.is_late ? 'Late' : 'On Time'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                            {record.is_late ? record.late_minutes : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                  No records found for selected date range
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TOTP Setup Status Tab */}
      {activeTab === 'totp-setup' && (
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input
              type="text"
              placeholder="Search staff..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              data-testid="search-staff-input"
            />
          </div>

          {/* Staff TOTP Status Cards */}
          <div className="grid gap-3">
            {filteredTotpStatus.map((staff) => (
              <div 
                key={staff.staff_id} 
                className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden"
              >
                <div 
                  className="p-4 flex justify-between items-center cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50"
                  onClick={() => setExpandedStaff(expandedStaff === staff.staff_id ? null : staff.staff_id)}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      staff.is_verified 
                        ? 'bg-emerald-100 dark:bg-emerald-900/30' 
                        : staff.is_setup 
                          ? 'bg-amber-100 dark:bg-amber-900/30'
                          : 'bg-slate-100 dark:bg-slate-700'
                    }`}>
                      {staff.is_verified ? (
                        <Shield className="text-emerald-600" size={20} />
                      ) : staff.is_setup ? (
                        <Key className="text-amber-600" size={20} />
                      ) : (
                        <UserX className="text-slate-400" size={20} />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">{staff.staff_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{staff.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      staff.is_verified 
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : staff.is_setup 
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
                    }`}>
                      {staff.is_verified ? 'Verified' : staff.is_setup ? 'Pending Verify' : 'Not Setup'}
                    </span>
                    {expandedStaff === staff.staff_id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedStaff === staff.staff_id && (
                  <div className="px-4 pb-4 pt-2 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                    <div className="flex justify-between items-center">
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        {staff.setup_date && (
                          <span>Setup date: {new Date(staff.setup_date).toLocaleDateString()}</span>
                        )}
                      </div>
                      {staff.is_setup && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResetTotp(staff.staff_id, staff.staff_name);
                          }}
                          disabled={resettingTotp === staff.staff_id}
                          className="flex items-center gap-2 px-3 py-1.5 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 rounded-lg text-sm"
                          data-testid={`reset-totp-${staff.staff_id}`}
                        >
                          {resettingTotp === staff.staff_id ? (
                            <RefreshCw className="animate-spin" size={16} />
                          ) : (
                            <Trash2 size={16} />
                          )}
                          Reset Authenticator
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {filteredTotpStatus.length === 0 && (
              <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                {searchQuery ? 'No staff found matching your search' : 'No staff members found'}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fee & Payment Tab */}
      {activeTab === 'fee-payment' && (
        <div className="space-y-6">
          {/* Month/Year Selector */}
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Year</label>
              <select
                value={feeYear}
                onChange={(e) => setFeeYear(Number(e.target.value))}
                className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                {[2024, 2025, 2026, 2027].map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Month</label>
              <select
                value={feeMonth}
                onChange={(e) => setFeeMonth(Number(e.target.value))}
                className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((m, idx) => (
                  <option key={idx} value={idx + 1}>{m}</option>
                ))}
              </select>
            </div>
            <button
              onClick={fetchFees}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
            >
              <RefreshCw size={18} />
              Refresh
            </button>
          </div>

          {/* Global Summary Cards */}
          {feeData && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                      <Clock className="text-red-600" size={24} />
                    </div>
                    <div>
                      <p className="text-sm text-slate-600 dark:text-slate-400">Total Late Minutes</p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">{feeData.total_late_minutes}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                      <DollarSign className="text-amber-600" size={24} />
                    </div>
                    <div>
                      <p className="text-sm text-slate-600 dark:text-slate-400">This Month's Fees</p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">${feeData.total_fees_this_month.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                      <CreditCard className="text-emerald-600" size={24} />
                    </div>
                    <div>
                      <p className="text-sm text-slate-600 dark:text-slate-400">Total Collected (All Time)</p>
                      <p className="text-2xl font-bold text-emerald-600">${feeData.total_collected_all_time.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <Users className="text-blue-600" size={24} />
                    </div>
                    <div>
                      <p className="text-sm text-slate-600 dark:text-slate-400">Staff with Fees</p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">{feeData.staff_count_with_fees}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-slate-100 dark:bg-slate-700/50 rounded-lg p-3 text-center text-sm text-slate-600 dark:text-slate-300">
                💰 Fee Rate: <span className="font-bold">${feeData.fee_per_minute}/minute</span> of lateness
              </div>

              {/* Staff Fee Cards */}
              <div className="space-y-4">
                {feeData.staff_fees.length > 0 ? (
                  feeData.staff_fees.map((staff) => (
                    <div 
                      key={staff.staff_id}
                      className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden"
                    >
                      {/* Staff Header */}
                      <div 
                        className="p-4 flex justify-between items-center cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50"
                        onClick={() => setExpandedFeeStaff(expandedFeeStaff === staff.staff_id ? null : staff.staff_id)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                            <DollarSign className="text-red-600" size={20} />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900 dark:text-white">{staff.staff_name}</p>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                              {staff.late_days} late day(s) • {staff.total_late_minutes} min total
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="text-lg font-bold text-red-600">${staff.total_fee.toLocaleString()}</p>
                            {staff.installment && (
                              <p className="text-xs text-emerald-600">
                                Installment: ${staff.installment.monthly_amount.toFixed(2)}/mo × {staff.installment.num_months}
                              </p>
                            )}
                          </div>
                          {expandedFeeStaff === staff.staff_id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                        </div>
                      </div>

                      {/* Expanded Details */}
                      {expandedFeeStaff === staff.staff_id && (
                        <div className="border-t border-slate-200 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-900/50">
                          {/* Action Buttons */}
                          <div className="flex flex-wrap gap-2 mb-4">
                            {!staff.installment ? (
                              <button
                                onClick={() => setInstallmentModal(staff)}
                                className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
                              >
                                <CreditCard size={16} />
                                Setup Installment
                              </button>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleCancelInstallment(staff.staff_id)}
                                  disabled={processingFee === `cancel-installment-${staff.staff_id}`}
                                  className="flex items-center gap-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm disabled:opacity-50"
                                >
                                  <Ban size={16} />
                                  Cancel Installment
                                </button>
                                {/* Payment buttons for each installment month */}
                                {[...Array(staff.installment.num_months)].map((_, idx) => {
                                  const payMonth = idx + 1;
                                  const isPaid = staff.installment.paid_months?.includes(payMonth);
                                  return (
                                    <button
                                      key={payMonth}
                                      onClick={() => !isPaid && handleRecordPayment(staff.staff_id, payMonth)}
                                      disabled={isPaid || processingFee === `pay-${staff.staff_id}-${payMonth}`}
                                      className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ${
                                        isPaid 
                                          ? 'bg-emerald-100 text-emerald-700 cursor-not-allowed' 
                                          : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                      }`}
                                    >
                                      <CheckCircle size={16} />
                                      {isPaid ? `Month ${payMonth} Paid` : `Pay Month ${payMonth} ($${staff.installment.monthly_amount.toFixed(2)})`}
                                    </button>
                                  );
                                })}
                              </>
                            )}
                          </div>

                          {/* Late Records Table */}
                          <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Late Records:</p>
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead className="bg-slate-100 dark:bg-slate-800">
                                <tr>
                                  <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Date</th>
                                  <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Check-in</th>
                                  <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Late (min)</th>
                                  <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Fee</th>
                                  <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-300">Action</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                {staff.records.map((record, idx) => (
                                  <tr key={idx}>
                                    <td className="px-3 py-2 text-slate-900 dark:text-white font-mono">{record.date}</td>
                                    <td className="px-3 py-2 text-slate-600 dark:text-slate-300 font-mono">{record.check_in_time}</td>
                                    <td className="px-3 py-2 text-amber-600 font-medium">{record.late_minutes}</td>
                                    <td className="px-3 py-2 text-red-600 font-medium">${record.fee}</td>
                                    <td className="px-3 py-2">
                                      <button
                                        onClick={() => setWaiveModal({ staffId: staff.staff_id, date: record.date, staffName: staff.staff_name, fee: record.fee })}
                                        className="flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-gray-700 dark:text-slate-300 rounded text-xs"
                                      >
                                        <XCircle size={14} />
                                        Waive
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="bg-white dark:bg-slate-800 rounded-xl p-8 text-center text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                    <CheckCircle className="mx-auto mb-2 text-emerald-500" size={32} />
                    <p>No lateness fees for this month! 🎉</p>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Waive Fee Modal */}
          {waiveModal && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Waive Fee</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                  Waive ${waiveModal.fee} fee for <strong>{waiveModal.staffName}</strong> on {waiveModal.date}?
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Reason for waiving <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={waiveReason}
                    onChange={(e) => setWaiveReason(e.target.value)}
                    placeholder="e.g., Emergency situation, system error, etc."
                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    rows={3}
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => { setWaiveModal(null); setWaiveReason(''); }}
                    className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleWaiveFee(waiveModal.staffId, waiveModal.date)}
                    disabled={processingFee === `${waiveModal.staffId}-${waiveModal.date}`}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                  >
                    {processingFee === `${waiveModal.staffId}-${waiveModal.date}` ? 'Processing...' : 'Waive Fee'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Installment Setup Modal */}
          {installmentModal && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Setup Installment Plan</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                  Total fee for <strong>{installmentModal.staff_name}</strong>: <span className="text-red-600 font-bold">${installmentModal.total_fee}</span>
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Number of Months (max 2)
                  </label>
                  <select
                    value={installmentMonths}
                    onChange={(e) => setInstallmentMonths(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  >
                    <option value={1}>1 month (${installmentModal.total_fee.toFixed(2)})</option>
                    <option value={2}>2 months (${(installmentModal.total_fee / 2).toFixed(2)}/month)</option>
                  </select>
                </div>
                <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-3 mb-4">
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Monthly payment: <strong>${(installmentModal.total_fee / installmentMonths).toFixed(2)}</strong>
                  </p>
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => setInstallmentModal(null)}
                    className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleSetupInstallment(installmentModal.staff_id)}
                    disabled={processingFee === `installment-${installmentModal.staff_id}`}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {processingFee === `installment-${installmentModal.staff_id}` ? 'Processing...' : 'Create Plan'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
