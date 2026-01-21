/**
 * AttendanceAdmin - Admin dashboard for viewing attendance records and managing TOTP
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Users, Clock, CheckCircle, AlertTriangle, RefreshCw, 
  Calendar, UserX, Shield, Search, ChevronDown,
  ChevronUp, Key, Trash2
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
  }, [activeTab, fetchHistory]);

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
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        {['today', 'history', 'totp-setup'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium capitalize transition-colors ${
              activeTab === tab 
                ? 'text-indigo-600 border-b-2 border-indigo-600' 
                : 'text-slate-600 dark:text-slate-400 hover:text-indigo-600'
            }`}
            data-testid={`tab-${tab}`}
          >
            {tab === 'totp-setup' ? 'TOTP Setup Status' : tab.charAt(0).toUpperCase() + tab.slice(1)}
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
    </div>
  );
}
