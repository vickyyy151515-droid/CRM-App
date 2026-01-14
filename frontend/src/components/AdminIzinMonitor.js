import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Timer, Clock, Users, AlertTriangle, 
  CheckCircle, RefreshCw, Calendar, ChevronDown, ChevronUp
} from 'lucide-react';

export default function AdminIzinMonitor() {
  const [loading, setLoading] = useState(true);
  const [todayData, setTodayData] = useState(null);
  const [expandedStaff, setExpandedStaff] = useState({});

  useEffect(() => {
    loadData();
    // Auto refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

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

  const toggleExpand = (staffId) => {
    setExpandedStaff(prev => ({
      ...prev,
      [staffId]: !prev[staffId]
    }));
  };

  const formatTime = (timeStr) => {
    if (!timeStr) return '-';
    return timeStr.slice(0, 5);
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

  return (
    <div className="space-y-6" data-testid="admin-izin-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Monitor Izin Staff</h1>
          <p className="text-slate-500 text-sm mt-1">Pantau izin keluar sementara staff hari ini</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
              <Users size={24} className="text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">
                {todayData?.staff_summary?.length || 0}
              </div>
              <div className="text-sm text-slate-500">Staff dengan Izin</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${onBreakCount > 0 ? 'bg-orange-100' : 'bg-green-100'}`}>
              <Timer size={24} className={onBreakCount > 0 ? 'text-orange-600' : 'text-green-600'} />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{onBreakCount}</div>
              <div className="text-sm text-slate-500">Sedang Izin</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${exceededCount > 0 ? 'bg-red-100' : 'bg-green-100'}`}>
              <AlertTriangle size={24} className={exceededCount > 0 ? 'text-red-600' : 'text-green-600'} />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{exceededCount}</div>
              <div className="text-sm text-slate-500">Melebihi Batas</div>
            </div>
          </div>
        </div>
      </div>

      {/* Staff List */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar size={20} className="text-slate-600" />
            <h3 className="font-semibold text-slate-800">Riwayat Izin Hari Ini</h3>
          </div>
          <div className="text-sm text-slate-500">
            Batas: {todayData?.daily_limit || 30} menit/hari
          </div>
        </div>

        <div className="divide-y divide-slate-100">
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
                      ${staff.is_on_break ? 'bg-orange-100' : staff.exceeded_limit ? 'bg-red-100' : 'bg-green-100'}
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
                      <div className="font-medium text-slate-800">{staff.staff_name}</div>
                      <div className="text-sm text-slate-500">
                        {staff.records.length} kali izin
                        {staff.is_on_break && <span className="text-orange-600 ml-2">• Sedang Izin</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className={`font-semibold ${staff.exceeded_limit ? 'text-red-600' : 'text-slate-700'}`}>
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
                          ${!record.end_time ? 'bg-orange-50 border border-orange-200' : 'bg-slate-50'}
                        `}
                      >
                        <div className="flex items-center gap-2">
                          <Clock size={16} className="text-slate-400" />
                          <span className="text-sm text-slate-600">
                            {formatTime(record.start_time)} - {record.end_time ? formatTime(record.end_time) : 'Berlangsung'}
                          </span>
                        </div>
                        <span className={`text-sm font-medium ${!record.end_time ? 'text-orange-600' : 'text-slate-700'}`}>
                          {record.duration_minutes ? `${record.duration_minutes.toFixed(1)} menit` : 'Aktif'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-center py-12 text-slate-500">
              <Timer size={48} className="mx-auto mb-3 opacity-30" />
              <p>Belum ada staff yang mengambil izin hari ini</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
