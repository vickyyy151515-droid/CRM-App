/**
 * AttendanceAdmin - Admin page to view and manage attendance
 * Shows today's attendance, lateness, device management, and history
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Clock, CheckCircle, XCircle, AlertTriangle, Users, Smartphone, 
  Trash2, RefreshCw, Calendar, Download, ChevronDown, ChevronUp 
} from 'lucide-react';
import * as XLSX from 'xlsx';

export default function AttendanceAdmin() {
  const [loading, setLoading] = useState(true);
  const [todayData, setTodayData] = useState(null);
  const [devices, setDevices] = useState([]);
  const [showDevices, setShowDevices] = useState(false);
  const [historyData, setHistoryData] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });

  // Load today's attendance
  const loadTodayAttendance = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/today');
      setTodayData(response.data);
    } catch (error) {
      toast.error('Failed to load attendance data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load registered devices
  const loadDevices = useCallback(async () => {
    try {
      const response = await api.get('/attendance/admin/devices');
      setDevices(response.data.devices || []);
    } catch (error) {
      toast.error('Failed to load devices');
    }
  }, []);

  // Load history
  const loadHistory = useCallback(async () => {
    try {
      const response = await api.get(`/attendance/admin/records?start_date=${dateRange.start}&end_date=${dateRange.end}`);
      setHistoryData(response.data);
    } catch (error) {
      toast.error('Failed to load history');
    }
  }, [dateRange]);

  useEffect(() => {
    loadTodayAttendance();
    loadDevices();
  }, [loadTodayAttendance, loadDevices]);

  useEffect(() => {
    if (showHistory) {
      loadHistory();
    }
  }, [showHistory, loadHistory]);

  // Delete device
  const handleDeleteDevice = async (staffId, staffName) => {
    if (!window.confirm(`Remove device registration for ${staffName}? They will need to register again.`)) {
      return;
    }

    try {
      await api.delete(`/attendance/admin/device/${staffId}`);
      toast.success('Device registration removed');
      loadDevices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove device');
    }
  };

  // Export to Excel
  const handleExport = async () => {
    try {
      const response = await api.get(`/attendance/admin/export?start_date=${dateRange.start}&end_date=${dateRange.end}`);
      const records = response.data.records;

      if (!records || records.length === 0) {
        toast.error('No records to export');
        return;
      }

      const exportData = records.map(r => ({
        'Date': r.date,
        'Staff Name': r.staff_name,
        'Check-in Time': r.check_in_time,
        'Status': r.is_late ? 'Late' : 'On Time',
        'Late (minutes)': r.late_minutes || 0,
        'Device': r.device_name || 'Unknown'
      }));

      const ws = XLSX.utils.json_to_sheet(exportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Attendance');
      XLSX.writeFile(wb, `attendance_${dateRange.start}_to_${dateRange.end}.xlsx`);
      
      toast.success('Export complete!');
    } catch (error) {
      toast.error('Failed to export');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  const summary = todayData?.summary || {};

  return (
    <div className="space-y-6" data-testid="attendance-admin-page">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Attendance</h2>
          <p className="text-slate-600 dark:text-slate-400">Track staff attendance and manage devices</p>
        </div>
        <button
          onClick={loadTodayAttendance}
          className="p-2 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
        >
          <RefreshCw size={20} />
        </button>
      </div>

      {/* Today's Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg">
              <Users className="text-indigo-600 dark:text-indigo-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Total Staff</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total_staff || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg">
              <CheckCircle className="text-emerald-600 dark:text-emerald-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Checked In</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{summary.checked_in || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
              <Clock className="text-amber-600 dark:text-amber-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Late</p>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{summary.late || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-lg">
              <XCircle className="text-red-600 dark:text-red-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Not Checked In</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{summary.not_checked_in || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Today's Records */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Calendar size={18} />
            Today&apos;s Attendance - {todayData?.date}
          </h3>
        </div>
        <div className="p-4">
          {todayData?.records?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                    <th className="pb-2 font-medium">Staff</th>
                    <th className="pb-2 font-medium">Time</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Device</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {todayData.records.map((record, idx) => (
                    <tr key={idx} className="text-sm">
                      <td className="py-3 text-slate-900 dark:text-white font-medium">
                        {record.staff_name}
                      </td>
                      <td className="py-3 text-slate-600 dark:text-slate-300 font-mono">
                        {record.check_in_time}
                      </td>
                      <td className="py-3">
                        {record.is_late ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 rounded-full text-xs font-medium">
                            <Clock size={12} />
                            Late ({record.late_minutes}m)
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 rounded-full text-xs font-medium">
                            <CheckCircle size={12} />
                            On Time
                          </span>
                        )}
                      </td>
                      <td className="py-3 text-slate-500 dark:text-slate-400 text-xs">
                        {record.device_name || 'Unknown'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-500 dark:text-slate-400 text-center py-8">
              No attendance records yet today
            </p>
          )}

          {/* Not Checked In List */}
          {todayData?.not_checked_in?.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-500" />
                Not Checked In ({todayData.not_checked_in.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {todayData.not_checked_in.map((staff, idx) => (
                  <span 
                    key={idx}
                    className="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-full text-sm"
                  >
                    {staff.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Device Management */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setShowDevices(!showDevices)}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
        >
          <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Smartphone size={18} />
            Registered Devices ({devices.length})
          </h3>
          {showDevices ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        
        {showDevices && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700">
            {devices.length > 0 ? (
              <div className="space-y-2">
                {devices.map((device, idx) => (
                  <div 
                    key={idx}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">{device.staff_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {device.device_name} • Registered {new Date(device.registered_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteDevice(device.staff_id, device.staff_name)}
                      className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                      title="Remove device"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-500 dark:text-slate-400 text-center py-4">
                No devices registered yet
              </p>
            )}
          </div>
        )}
      </div>

      {/* History & Export */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
        >
          <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Calendar size={18} />
            Attendance History
          </h3>
          {showHistory ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        
        {showHistory && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700">
            {/* Date Range Selector */}
            <div className="flex flex-wrap gap-3 mb-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-600 dark:text-slate-400">From:</label>
                <input
                  type="date"
                  value={dateRange.start}
                  onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                  className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-600 dark:text-slate-400">To:</label>
                <input
                  type="date"
                  value={dateRange.end}
                  onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                  className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                />
              </div>
              <button
                onClick={loadHistory}
                className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
              >
                Load
              </button>
              <button
                onClick={handleExport}
                className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 flex items-center gap-1"
              >
                <Download size={14} />
                Export
              </button>
            </div>

            {/* History Table */}
            {historyData?.records?.length > 0 ? (
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-white dark:bg-slate-800">
                    <tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium">Date</th>
                      <th className="pb-2 font-medium">Staff</th>
                      <th className="pb-2 font-medium">Time</th>
                      <th className="pb-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                    {historyData.records.map((record, idx) => (
                      <tr key={idx}>
                        <td className="py-2 text-slate-600 dark:text-slate-300">{record.date}</td>
                        <td className="py-2 text-slate-900 dark:text-white">{record.staff_name}</td>
                        <td className="py-2 text-slate-600 dark:text-slate-300 font-mono">{record.check_in_time}</td>
                        <td className="py-2">
                          {record.is_late ? (
                            <span className="text-amber-600 dark:text-amber-400">Late ({record.late_minutes}m)</span>
                          ) : (
                            <span className="text-emerald-600 dark:text-emerald-400">On Time</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-slate-500 dark:text-slate-400 text-center py-4">
                {historyData ? 'No records found for selected period' : 'Click "Load" to view history'}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
