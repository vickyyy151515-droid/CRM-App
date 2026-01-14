import { useState, useEffect, useRef } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Clock, LogOut, LogIn, Timer, AlertTriangle, 
  CheckCircle, History, RefreshCw
} from 'lucide-react';

export default function StaffIzin() {
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [todayRecords, setTodayRecords] = useState([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    loadData();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Update elapsed time every second when on break
  useEffect(() => {
    if (status?.is_on_break) {
      timerRef.current = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setElapsedTime(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status?.is_on_break]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statusRes, recordsRes] = await Promise.all([
        api.get('/izin/status'),
        api.get('/izin/today')
      ]);
      setStatus(statusRes.data);
      setTodayRecords(recordsRes.data.records || []);
      
      // Set initial elapsed time if on break
      if (statusRes.data.is_on_break) {
        setElapsedTime(statusRes.data.elapsed_minutes * 60);
      }
    } catch (error) {
      console.error('Failed to load izin data:', error);
      toast.error('Gagal memuat data izin');
    } finally {
      setLoading(false);
    }
  };

  const handleIzin = async () => {
    setActionLoading(true);
    try {
      const response = await api.post('/izin/start');
      toast.success(response.data.message);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal memulai izin');
    } finally {
      setActionLoading(false);
    }
  };

  const handleKembali = async () => {
    setActionLoading(true);
    try {
      const response = await api.post('/izin/end');
      toast.success(response.data.message);
      
      if (response.data.exceeded_limit) {
        toast.warning(`Anda telah melebihi batas izin harian (${response.data.total_minutes_today.toFixed(1)} menit)`);
      }
      
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal mengakhiri izin');
    } finally {
      setActionLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTimeString = (timeStr) => {
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

  const progressPercent = status ? Math.min(100, (status.total_minutes_used / status.daily_limit) * 100) : 0;
  const isExceeded = status?.total_minutes_used > status?.daily_limit;

  return (
    <div className="space-y-6" data-testid="izin-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Izin</h1>
          <p className="text-slate-500 text-sm mt-1">Keluar sementara dalam jam kerja (maksimal 30 menit/hari)</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {/* Main Action Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6">
          {/* Status Display */}
          <div className="text-center mb-8">
            {status?.is_on_break ? (
              <div className="space-y-4">
                <div className="w-24 h-24 mx-auto bg-orange-100 rounded-full flex items-center justify-center animate-pulse">
                  <Timer size={48} className="text-orange-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-orange-700">Sedang Izin</h2>
                  <p className="text-slate-500 text-sm mt-1">Mulai: {formatTimeString(status.active_izin?.start_time)}</p>
                </div>
                <div className="text-5xl font-mono font-bold text-orange-600">
                  {formatTime(elapsedTime)}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="w-24 h-24 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle size={48} className="text-green-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-green-700">Siap Bekerja</h2>
                  <p className="text-slate-500 text-sm mt-1">Klik "Izin" jika perlu keluar sebentar</p>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-center gap-4">
            <button
              onClick={handleIzin}
              disabled={status?.is_on_break || actionLoading}
              data-testid="izin-button"
              className={`
                flex items-center gap-3 px-8 py-4 rounded-xl font-semibold text-lg transition-all
                ${status?.is_on_break 
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                  : 'bg-orange-500 hover:bg-orange-600 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
                }
              `}
            >
              <LogOut size={24} />
              Izin
            </button>
            
            <button
              onClick={handleKembali}
              disabled={!status?.is_on_break || actionLoading}
              data-testid="kembali-button"
              className={`
                flex items-center gap-3 px-8 py-4 rounded-xl font-semibold text-lg transition-all
                ${!status?.is_on_break 
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                  : 'bg-green-500 hover:bg-green-600 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
                }
              `}
            >
              <LogIn size={24} />
              Kembali
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="px-6 pb-6">
          <div className="bg-slate-100 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-slate-600">Penggunaan Hari Ini</span>
              <span className={`text-sm font-bold ${isExceeded ? 'text-red-600' : 'text-slate-700'}`}>
                {status?.total_minutes_used?.toFixed(1) || 0} / {status?.daily_limit || 30} menit
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  isExceeded ? 'bg-red-500' : progressPercent > 80 ? 'bg-orange-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(100, progressPercent)}%` }}
              />
            </div>
            {isExceeded && (
              <div className="flex items-center gap-2 mt-2 text-red-600 text-sm">
                <AlertTriangle size={16} />
                <span>Batas harian terlampaui! Admin telah diberitahu.</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Today's History */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-2">
          <History size={20} className="text-slate-600" />
          <h3 className="font-semibold text-slate-800">Riwayat Hari Ini</h3>
        </div>
        <div className="p-6">
          {todayRecords.length > 0 ? (
            <div className="space-y-3">
              {todayRecords.map((record, index) => (
                <div 
                  key={record.id}
                  className={`
                    flex items-center justify-between p-4 rounded-lg border
                    ${!record.end_time ? 'bg-orange-50 border-orange-200' : 'bg-slate-50 border-slate-200'}
                  `}
                >
                  <div className="flex items-center gap-3">
                    <div className={`
                      w-10 h-10 rounded-full flex items-center justify-center
                      ${!record.end_time ? 'bg-orange-200' : 'bg-slate-200'}
                    `}>
                      <Clock size={20} className={!record.end_time ? 'text-orange-600' : 'text-slate-600'} />
                    </div>
                    <div>
                      <div className="font-medium text-slate-800">
                        Izin #{todayRecords.length - index}
                      </div>
                      <div className="text-sm text-slate-500">
                        {formatTimeString(record.start_time)} - {record.end_time ? formatTimeString(record.end_time) : 'Sedang berlangsung'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {record.duration_minutes ? (
                      <span className="font-semibold text-slate-700">
                        {record.duration_minutes.toFixed(1)} menit
                      </span>
                    ) : (
                      <span className="text-orange-600 font-medium animate-pulse">
                        Aktif
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <Clock size={48} className="mx-auto mb-3 opacity-30" />
              <p>Belum ada riwayat izin hari ini</p>
            </div>
          )}
        </div>
      </div>

      {/* Info Card */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
        <h4 className="font-semibold text-blue-800 mb-2">Informasi</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Maksimal total izin per hari: <strong>30 menit</strong></li>
          <li>• Klik "Izin" saat akan keluar, dan "Kembali" saat sudah kembali</li>
          <li>• Jika melebihi batas, admin akan mendapat notifikasi</li>
          <li>• Waktu izin dihitung secara otomatis</li>
        </ul>
      </div>
    </div>
  );
}
