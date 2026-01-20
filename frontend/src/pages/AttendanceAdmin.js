import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Calendar, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Users,
  Download,
  RefreshCw,
  Smartphone,
  Trash2,
  Filter
} from 'lucide-react';
import * as XLSX from 'xlsx';

export default function AttendanceAdmin() {
  const [activeTab, setActiveTab] = useState('today');
  const [todayData, setTodayData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    start: new Date().toISOString().split('T')[0].slice(0, 8) + '01',
    end: new Date().toISOString().split('T')[0]
  });
  const [selectedStaff, setSelectedStaff] = useState('');
  const [staffList, setStaffList] = useState([]);

  const loadTodayData = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/today');
      setTodayData(response.data);
      
      // Extract unique staff list
      const staff = response.data.staff.map(s => ({ id: s.staff_id, name: s.name }));
      setStaffList(staff);
    } catch (error) {
      toast.error('Failed to load today\'s attendance');
    }
  }, []);

  const loadHistoryData = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end
      });
      if (selectedStaff) {
        params.append('staff_id', selectedStaff);
      }
      
      const response = await api.get(`/attendance/admin/records?${params}`);
      setHistoryData(response.data);
    } catch (error) {
      toast.error('Failed to load attendance history');
    }
  }, [dateRange, selectedStaff]);

  const loadDevices = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/devices');
      setDevices(response.data.devices);
    } catch (error) {
      toast.error('Failed to load devices');
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([loadTodayData(), loadDevices()]);
      setLoading(false);
    };
    loadData();
  }, [loadTodayData, loadDevices]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistoryData();
    }
  }, [activeTab, loadHistoryData]);

  const resetDevice = async (staffId, staffName) => {
    if (!window.confirm(`Are you sure you want to reset device registration for ${staffName}? They will need to register their phone again.`)) {
      return;
    }

    try {
      await api.delete(`/attendance/admin/device/${staffId}`);
      toast.success(`Device reset for ${staffName}`);
      loadDevices();
    } catch (error) {
      toast.error('Failed to reset device');
    }
  };

  const exportToExcel = async () => {
    try {
      const response = await api.get(`/attendance/admin/export?start_date=${dateRange.start}&end_date=${dateRange.end}`);
      
      const wb = XLSX.utils.book_new();
      const ws = XLSX.utils.json_to_sheet(response.data.data);
      XLSX.utils.book_append_sheet(wb, ws, 'Attendance');
      XLSX.writeFile(wb, `attendance_${dateRange.start}_to_${dateRange.end}.xlsx`);
      
      toast.success('Export successful');
    } catch (error) {
      toast.error('Failed to export data');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'on_time':
        return (
          <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400 text-xs font-medium rounded-full">
            On Time
          </span>
        );
      case 'late':
        return (
          <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400 text-xs font-medium rounded-full">
            Late
          </span>
        );
      case 'not_checked_in':
        return (
          <span className="px-2 py-1 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-400 text-xs font-medium rounded-full">
            Not Checked In
          </span>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="attendance-admin-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Calendar size={28} className="text-indigo-600" />
            Attendance Management
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Track staff attendance and manage device registrations
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        {['today', 'history', 'devices'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab === 'today' && "Today's Attendance"}
            {tab === 'history' && 'History'}
            {tab === 'devices' && 'Registered Devices'}
          </button>
        ))}
      </div>

      {/* Today's Attendance Tab */}
      {activeTab === 'today' && todayData && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                  <Users size={20} className="text-slate-600 dark:text-slate-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Total Staff</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{todayData.summary.total_staff}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg">
                  <CheckCircle size={20} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">On Time</p>
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{todayData.summary.on_time}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
                  <AlertTriangle size={20} className="text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Late</p>
                  <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{todayData.summary.late}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-lg">
                  <XCircle size={20} className="text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Not Checked In</p>
                  <p className="text-2xl font-bold text-red-600 dark:text-red-400">{todayData.summary.not_checked_in}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Shift Info */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-center gap-3">
            <Clock size={20} className="text-blue-600" />
            <div>
              <span className="font-medium text-blue-800 dark:text-blue-300">Shift: {todayData.shift_start} - 23:00</span>
              <span className="mx-2 text-blue-600">•</span>
              <span className="text-blue-700 dark:text-blue-400">Current Time: {todayData.current_time}</span>
            </div>
          </div>

          {/* Staff List */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900 dark:text-white">Staff Attendance - {todayData.date}</h2>
              <button
                onClick={loadTodayData}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <RefreshCw size={18} className="text-slate-500" />
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Staff</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Check-in Time</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Status</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Minutes Late</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {todayData.staff.map(staff => (
                    <tr key={staff.staff_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-slate-900 dark:text-white">{staff.name}</p>
                          <p className="text-sm text-slate-500">{staff.email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {staff.checked_in ? (
                          <span className="font-mono text-slate-900 dark:text-white">{staff.check_in_time}</span>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {getStatusBadge(staff.status)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {staff.status === 'late' ? (
                          <span className="text-amber-600 font-medium">+{staff.minutes_late} min</span>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          {/* Filters */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Start Date</label>
                <input
                  type="date"
                  value={dateRange.start}
                  onChange={e => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                  className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">End Date</label>
                <input
                  type="date"
                  value={dateRange.end}
                  onChange={e => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                  className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Staff</label>
                <select
                  value={selectedStaff}
                  onChange={e => setSelectedStaff(e.target.value)}
                  className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="">All Staff</option>
                  {staffList.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={loadHistoryData}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Filter size={18} />
                Apply Filter
              </button>
              <button
                onClick={exportToExcel}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                <Download size={18} />
                Export Excel
              </button>
            </div>
          </div>

          {/* Summary */}
          {historyData && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 text-center">
                <p className="text-sm text-slate-500">Total Records</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{historyData.summary.total_records}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 text-center">
                <p className="text-sm text-slate-500">On Time</p>
                <p className="text-2xl font-bold text-emerald-600">{historyData.summary.on_time}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 text-center">
                <p className="text-sm text-slate-500">Late</p>
                <p className="text-2xl font-bold text-amber-600">{historyData.summary.late}</p>
              </div>
            </div>
          )}

          {/* Records Table */}
          {historyData && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 dark:bg-slate-900">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Staff</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Check-in</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                    {historyData.records.map((record, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                        <td className="px-6 py-3 font-mono text-slate-900 dark:text-white">{record.date}</td>
                        <td className="px-6 py-3 text-slate-900 dark:text-white">{record.staff_name}</td>
                        <td className="px-6 py-3 text-center font-mono text-slate-900 dark:text-white">{record.check_in_hour}</td>
                        <td className="px-6 py-3 text-center">{getStatusBadge(record.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {historyData.records.length === 0 && (
                <div className="p-8 text-center text-slate-500">
                  No attendance records found for the selected period
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Devices Tab */}
      {activeTab === 'devices' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Smartphone size={20} className="text-indigo-600" />
                Registered Devices ({devices.length})
              </h2>
              <button
                onClick={loadDevices}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <RefreshCw size={18} className="text-slate-500" />
              </button>
            </div>
            
            {devices.length > 0 ? (
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {devices.map(device => (
                  <div key={device.staff_id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">{device.staff_name}</p>
                      <p className="text-sm text-slate-500">{device.device_name}</p>
                      <p className="text-xs text-slate-400">Registered: {new Date(device.registered_at).toLocaleDateString('id-ID')}</p>
                    </div>
                    <button
                      onClick={() => resetDevice(device.staff_id, device.staff_name)}
                      className="flex items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                    >
                      <Trash2 size={16} />
                      Reset
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500">
                No devices registered yet
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <h3 className="font-semibold text-amber-800 dark:text-amber-300 mb-2">Device Reset Info</h3>
            <p className="text-sm text-amber-700 dark:text-amber-400">
              Resetting a device will require the staff member to register their phone again. 
              Use this if a staff member gets a new phone or loses their device.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
