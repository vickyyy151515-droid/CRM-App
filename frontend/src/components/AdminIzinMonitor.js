import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Timer, Clock, Users, AlertTriangle, 
  CheckCircle, RefreshCw, Calendar, ChevronDown, ChevronUp, History, Filter
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function AdminIzinMonitor() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [todayData, setTodayData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [expandedStaff, setExpandedStaff] = useState({});
  const [expandedHistory, setExpandedHistory] = useState({});
  const [activeTab, setActiveTab] = useState('today'); // 'today' or 'history'
  const [staffList, setStaffList] = useState([]);
  const [selectedStaff, setSelectedStaff] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    loadData();
    loadStaffList();
    // Auto refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStaffList = async () => {
    try {
      const response = await api.get('/staff-users');
      setStaffList(response.data);
    } catch (error) {
      console.error('Failed to load staff list');
    }
  };

  const loadData = async () => {
    try {
      const response = await api.get('/izin/admin/today');
      setTodayData(response.data);
    } catch (error) {
      console.error('Failed to load izin data:', error);
      toast.error('Gagal memuat data izin');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedStaff) params.append('staff_id', selectedStaff);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await api.get(`/izin/admin/history?${params}`);
      setHistoryData(response.data);
    } catch (error) {
      console.error('Failed to load history:', error);
      toast.error('Gagal memuat riwayat izin');
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab, selectedStaff, startDate, endDate]);

  const toggleExpand = (staffId) => {
    setExpandedStaff(prev => ({
      ...prev,
      [staffId]: !prev[staffId]
    }));
  };

  const toggleHistoryExpand = (key) => {
    setExpandedHistory(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const formatTime = (timeStr) => {
    if (!timeStr) return '-';
    return timeStr.slice(0, 5);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  };

  // Group history records by date
  const getGroupedHistory = () => {
    if (!historyData?.records) return [];
    
    const grouped = {};
    for (const record of historyData.records) {
      const date = record.date;
      if (!grouped[date]) {
        grouped[date] = {
          date,
          records: [],
          totalMinutes: 0,
          staffBreakdown: {}
        };
      }
      grouped[date].records.push(record);
      if (record.duration_minutes) {
        grouped[date].totalMinutes += record.duration_minutes;
      }
      
      // Track per-staff breakdown
      const staffId = record.staff_id;
      if (!grouped[date].staffBreakdown[staffId]) {
        grouped[date].staffBreakdown[staffId] = {
          staff_name: record.staff_name,
          total_minutes: 0,
          records: []
        };
      }
      grouped[date].staffBreakdown[staffId].records.push(record);
      if (record.duration_minutes) {
        grouped[date].staffBreakdown[staffId].total_minutes += record.duration_minutes;
      }
    }
    
    return Object.values(grouped).sort((a, b) => b.date.localeCompare(a.date));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const onBreakCount = todayData?.staff_summary?.filter(s => s.is_on_break).length || 0;
  const exceededCount = todayData?.staff_summary?.filter(s => s.exceeded_limit).length || 0;
  const groupedHistory = getGroupedHistory();

  return (
    <div className="space-y-6" data-testid="admin-izin-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Monitor Izin Staff</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Pantau izin keluar sementara staff</p>
        </div>
        <button
          onClick={() => { loadData(); if (activeTab === 'history') loadHistory(); }}
          className="flex items-center gap-2 px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab('today')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'today'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <div className="flex items-center gap-2">
            <Calendar size={18} />
            Hari Ini
          </div>
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'history'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <div className="flex items-center gap-2">
            <History size={18} />
            Riwayat Harian
          </div>
        </button>
      </div>

      {/* Summary Cards - Only show on today tab */}
      {activeTab === 'today' && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Users size={24} className="text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">
                  {todayData?.staff_summary?.length || 0}
                </div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Staff dengan Izin</div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${onBreakCount > 0 ? 'bg-orange-100 dark:bg-orange-900/30' : 'bg-green-100 dark:bg-green-900/30'}`}>
                <Timer size={24} className={onBreakCount > 0 ? 'text-orange-600' : 'text-green-600'} />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{onBreakCount}</div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Sedang Izin</div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${exceededCount > 0 ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30'}`}>
                <AlertTriangle size={24} className={exceededCount > 0 ? 'text-red-600' : 'text-green-600'} />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{exceededCount}</div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Melebihi Batas</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TODAY TAB CONTENT */}
      {activeTab === 'today' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar size={20} className="text-slate-600 dark:text-slate-400" />
              <h3 className="font-semibold text-slate-800 dark:text-white">Riwayat Izin Hari Ini</h3>
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">
              Batas: {todayData?.daily_limit || 30} menit/hari
            </div>
          </div>

          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {todayData?.staff_summary?.length > 0 ? (
              todayData.staff_summary.map((staff) => (
                <div key={staff.staff_id} className="p-4">
                  <div 
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => toggleExpand(staff.staff_id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`
                        w-10 h-10 rounded-full flex items-center justify-center
                        ${staff.is_on_break ? 'bg-orange-100 dark:bg-orange-900/30' : staff.exceeded_limit ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30'}
                      `}>
                        {staff.is_on_break ? (
                          <Timer size={20} className="text-orange-600 animate-pulse" />
                        ) : staff.exceeded_limit ? (
                          <AlertTriangle size={20} className="text-red-600" />
                        ) : (
                          <CheckCircle size={20} className="text-green-600" />
                        )}
                      </div>
                      <div>
                        <div className="font-medium text-slate-800 dark:text-white">{staff.staff_name}</div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          {staff.records.length} kali izin
                          {staff.is_on_break && <span className="text-orange-600 ml-2">• Sedang Izin</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className={`font-semibold ${staff.exceeded_limit ? 'text-red-600' : 'text-slate-700 dark:text-slate-300'}`}>
                          {staff.total_minutes.toFixed(1)} menit
                        </div>
                        {staff.exceeded_limit && (
                          <div className="text-xs text-red-500">Melebihi batas!</div>
                        )}
                      </div>
                      {expandedStaff[staff.staff_id] ? (
                        <ChevronUp size={20} className="text-slate-400" />
                      ) : (
                        <ChevronDown size={20} className="text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedStaff[staff.staff_id] && (
                    <div className="mt-4 ml-13 space-y-2">
                      {staff.records.map((record, idx) => (
                        <div 
                          key={record.id}
                          className={`
                            flex items-center justify-between p-3 rounded-lg
                            ${!record.end_time ? 'bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800' : 'bg-slate-50 dark:bg-slate-700'}
                          `}
                        >
                          <div className="flex items-center gap-2">
                            <Clock size={16} className="text-slate-400" />
                            <span className="text-sm text-slate-600 dark:text-slate-300">
                              {formatTime(record.start_time)} - {record.end_time ? formatTime(record.end_time) : 'Berlangsung'}
                            </span>
                          </div>
                          <span className={`text-sm font-medium ${!record.end_time ? 'text-orange-600' : 'text-slate-700 dark:text-slate-300'}`}>
                            {record.duration_minutes ? `${record.duration_minutes.toFixed(1)} menit` : 'Aktif'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                <Timer size={48} className="mx-auto mb-3 opacity-30" />
                <p>Belum ada staff yang mengambil izin hari ini</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* HISTORY TAB CONTENT */}
      {activeTab === 'history' && (
        <>
          {/* Filters */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-2 mb-4">
              <Filter size={18} className="text-slate-500" />
              <span className="font-medium text-slate-700 dark:text-white">Filter</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Staff</label>
                <select
                  value={selectedStaff}
                  onChange={(e) => setSelectedStaff(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Semua Staff</option>
                  {staffList.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Dari Tanggal</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Sampai Tanggal</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* History List grouped by date */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History size={20} className="text-slate-600 dark:text-slate-400" />
                <h3 className="font-semibold text-slate-800 dark:text-white">Riwayat Izin Harian</h3>
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400">
                {groupedHistory.length} hari tercatat
              </div>
            </div>

            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {groupedHistory.length > 0 ? (
                groupedHistory.map((dayData) => (
                  <div key={dayData.date} className="p-4">
                    <div 
                      className="flex items-center justify-between cursor-pointer"
                      onClick={() => toggleHistoryExpand(dayData.date)}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                          <Calendar size={20} className="text-indigo-600" />
                        </div>
                        <div>
                          <div className="font-medium text-slate-800 dark:text-white">{formatDate(dayData.date)}</div>
                          <div className="text-sm text-slate-500 dark:text-slate-400">
                            {dayData.records.length} izin dari {Object.keys(dayData.staffBreakdown).length} staff
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className={`font-semibold ${dayData.totalMinutes > (todayData?.daily_limit || 30) ? 'text-red-600' : 'text-slate-700 dark:text-slate-300'}`}>
                            {dayData.totalMinutes.toFixed(1)} menit total
                          </div>
                        </div>
                        {expandedHistory[dayData.date] ? (
                          <ChevronUp size={20} className="text-slate-400" />
                        ) : (
                          <ChevronDown size={20} className="text-slate-400" />
                        )}
                      </div>
                    </div>

                    {/* Expanded Day Details */}
                    {expandedHistory[dayData.date] && (
                      <div className="mt-4 space-y-3">
                        {Object.values(dayData.staffBreakdown).map((staffData) => (
                          <div key={staffData.staff_name} className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${staffData.total_minutes > (todayData?.daily_limit || 30) ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30'}`}>
                                  {staffData.total_minutes > (todayData?.daily_limit || 30) ? (
                                    <AlertTriangle size={16} className="text-red-600" />
                                  ) : (
                                    <CheckCircle size={16} className="text-green-600" />
                                  )}
                                </div>
                                <span className="font-medium text-slate-700 dark:text-slate-200">{staffData.staff_name}</span>
                              </div>
                              <span className={`text-sm font-semibold ${staffData.total_minutes > (todayData?.daily_limit || 30) ? 'text-red-600' : 'text-slate-600 dark:text-slate-300'}`}>
                                {staffData.total_minutes.toFixed(1)} menit
                                {staffData.total_minutes > (todayData?.daily_limit || 30) && (
                                  <span className="ml-1 text-xs text-red-500">(Melebihi!)</span>
                                )}
                              </span>
                            </div>
                            <div className="space-y-1">
                              {staffData.records.map((record) => (
                                <div key={record.id} className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400 pl-10">
                                  <div className="flex items-center gap-2">
                                    <Clock size={14} />
                                    <span>{formatTime(record.start_time)} - {record.end_time ? formatTime(record.end_time) : 'Tidak selesai'}</span>
                                  </div>
                                  <span>{record.duration_minutes ? `${record.duration_minutes.toFixed(1)} menit` : '-'}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                  <History size={48} className="mx-auto mb-3 opacity-30" />
                  <p>Tidak ada riwayat izin ditemukan</p>
                  <p className="text-sm mt-1">Coba ubah filter untuk melihat data</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
