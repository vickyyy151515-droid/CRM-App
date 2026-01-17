import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Calendar, Clock, AlertCircle, CheckCircle, XCircle, 
  Plus, Trash2, Timer, CalendarOff, Thermometer
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const MONTH_NAMES = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

export default function StaffLeaveRequest() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState(null);
  const [requests, setRequests] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  
  // Form state
  const [formData, setFormData] = useState({
    leave_type: 'off_day',
    date: '',
    start_time: '',
    end_time: '',
    reason: ''
  });

  useEffect(() => {
    loadData();
  }, [selectedYear, selectedMonth]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [balanceRes, requestsRes] = await Promise.all([
        api.get('/leave/balance', { params: { year: selectedYear, month: selectedMonth } }),
        api.get('/leave/my-requests', { params: { year: selectedYear, month: selectedMonth } })
      ]);
      setBalance(balanceRes.data);
      setRequests(requestsRes.data);
    } catch (error) {
      console.error('Failed to load leave data:', error);
      toast.error('Failed to load leave data');
    } finally {
      setLoading(false);
    }
  };

  const calculateHours = () => {
    if (formData.leave_type === 'off_day') return 12;
    if (formData.start_time && formData.end_time) {
      const [startH, startM] = formData.start_time.split(':').map(Number);
      const [endH, endM] = formData.end_time.split(':').map(Number);
      const startMinutes = startH * 60 + startM;
      const endMinutes = endH * 60 + endM;
      return Math.max(0, (endMinutes - startMinutes) / 60);
    }
    return 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.date) {
      toast.error('Please select a date');
      return;
    }
    
    if (formData.leave_type === 'sakit' && (!formData.start_time || !formData.end_time)) {
      toast.error('Please select start and end time for sick leave');
      return;
    }
    
    const hoursNeeded = calculateHours();
    const pendingHours = requests
      .filter(r => r.status === 'pending')
      .reduce((sum, r) => sum + (r.hours_deducted || 0), 0);
    const availableHours = (balance?.remaining_hours || 0) - pendingHours;
    
    if (hoursNeeded > availableHours) {
      toast.error(`${t('staffLeave.insufficientBalance')} ${availableHours} ${t('staffLeave.hours')}`);
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post('/leave/request', {
        leave_type: formData.leave_type,
        date: formData.date,
        start_time: formData.leave_type === 'sakit' ? formData.start_time : null,
        end_time: formData.leave_type === 'sakit' ? formData.end_time : null,
        reason: formData.reason || null
      });
      toast.success(t('staffLeave.requestSubmitted'));
      setShowForm(false);
      setFormData({ leave_type: 'off_day', date: '', start_time: '', end_time: '', reason: '' });
      loadData();
    } catch (error) {
      console.error('Failed to submit request:', error);
      toast.error(error.response?.data?.detail || t('messages.saveFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const cancelRequest = async (requestId) => {
    if (!window.confirm(t('staffLeave.cancelRequest'))) return;
    
    try {
      await api.delete(`/leave/request/${requestId}`);
      toast.success(t('staffLeave.requestCancelled'));
      loadData();
    } catch (error) {
      toast.error(t('messages.deleteFailed'));
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'approved':
        return <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1"><CheckCircle size={12} /> {t('staffLeave.approved')}</span>;
      case 'rejected':
        return <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium flex items-center gap-1"><XCircle size={12} /> Ditolak</span>;
      default:
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium flex items-center gap-1"><Clock size={12} /> {t('staffProgress.pending')}</span>;
    }
  };

  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1];
  const hoursToDeduct = calculateHours();

  if (loading && !balance) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="staff-leave-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('staffLeave.title')}</h1>
          <p className="text-slate-500 text-sm mt-1">{t('staffLeave.subtitle')}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          data-testid="new-request-btn"
        >
          <Plus size={18} />
          {t('staffLeave.newRequest')}
        </button>
      </div>

      {/* Month Filter */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">{t('staffLeave.year')}</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">{t('staffLeave.month')}</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {MONTH_NAMES.map((name, idx) => (
                <option key={idx} value={idx + 1}>{name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Leave Balance Card */}
      {balance && (
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl shadow-lg p-6 text-white">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h3 className="text-lg font-semibold opacity-90">{t('staffLeave.leaveBalance')} - {MONTH_NAMES[selectedMonth - 1]} {selectedYear}</h3>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-bold">{balance.remaining_hours}</span>
                <span className="text-xl opacity-80">/ {balance.total_hours} {t('staffLeave.hours')}</span>
              </div>
            </div>
            <div className="flex gap-6">
              <div className="text-center">
                <Timer size={24} className="mx-auto mb-1 opacity-70" />
                <div className="text-2xl font-bold">{balance.used_hours}</div>
                <div className="text-xs opacity-70">{t('staffLeave.hoursUsed')}</div>
              </div>
              <div className="text-center">
                <CheckCircle size={24} className="mx-auto mb-1 opacity-70" />
                <div className="text-2xl font-bold">{balance.approved_requests}</div>
                <div className="text-xs opacity-70">{t('staffLeave.approved')}</div>
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mt-4">
            <div className="h-3 bg-white/20 rounded-full overflow-hidden">
              <div 
                className="h-full bg-white/80 transition-all duration-500"
                style={{ width: `${(balance.used_hours / balance.total_hours) * 100}%` }}
              />
            </div>
            <div className="flex justify-between mt-1 text-xs opacity-70">
              <span>0 {t('staffLeave.hours')}</span>
              <span>{balance.total_hours} {t('staffLeave.hours')}</span>
            </div>
          </div>
        </div>
      )}

      {/* Request Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-xl font-bold text-slate-800">{t('staffLeave.newRequest')}</h2>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {/* Leave Type */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">{t('staffLeave.leaveType')}</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, leave_type: 'off_day' }))}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      formData.leave_type === 'off_day'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <CalendarOff size={24} className={`mx-auto mb-2 ${formData.leave_type === 'off_day' ? 'text-blue-600' : 'text-slate-400'}`} />
                    <div className={`font-medium ${formData.leave_type === 'off_day' ? 'text-blue-700' : 'text-slate-600'}`}>{t('staffLeave.offDay')}</div>
                    <div className="text-xs text-slate-500 mt-1">{t('staffLeave.hoursDeducted')}</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, leave_type: 'sakit' }))}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      formData.leave_type === 'sakit'
                        ? 'border-red-500 bg-red-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <Thermometer size={24} className={`mx-auto mb-2 ${formData.leave_type === 'sakit' ? 'text-red-600' : 'text-slate-400'}`} />
                    <div className={`font-medium ${formData.leave_type === 'sakit' ? 'text-red-700' : 'text-slate-600'}`}>{t('staffLeave.sakit')}</div>
                    <div className="text-xs text-slate-500 mt-1">{t('staffLeave.hoursByRange')}</div>
                  </button>
                </div>
              </div>

              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('staffLeave.date')}</label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              {/* Time Range (for Sakit) */}
              {formData.leave_type === 'sakit' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">{t('staffLeave.startTime')}</label>
                    <input
                      type="time"
                      value={formData.start_time}
                      onChange={(e) => setFormData(prev => ({ ...prev, start_time: e.target.value }))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">{t('staffLeave.endTime')}</label>
                    <input
                      type="time"
                      value={formData.end_time}
                      onChange={(e) => setFormData(prev => ({ ...prev, end_time: e.target.value }))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                </div>
              )}

              {/* Reason */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('staffLeave.reason')}</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData(prev => ({ ...prev, reason: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={2}
                  placeholder={t('staffLeave.reasonOptional')}
                />
              </div>

              {/* Hours Summary */}
              <div className="p-3 bg-slate-100 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">{t('staffLeave.hoursToDeduct')}</span>
                  <span className="text-lg font-bold text-slate-800">{hoursToDeduct} {t('staffLeave.hours')}</span>
                </div>
                {balance && (
                  <div className="flex justify-between items-center mt-1 text-xs text-slate-500">
                    <span>{t('staffLeave.remainingAfter')}</span>
                    <span className={balance.remaining_hours - hoursToDeduct < 0 ? 'text-red-600' : ''}>
                      {Math.max(0, balance.remaining_hours - hoursToDeduct)} {t('staffLeave.hours')}
                    </span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 px-4 py-2 text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
                >
                  {t('staffLeave.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {submitting ? t('staffLeave.submitting') : t('staffLeave.submitRequest')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Requests List */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
          <h3 className="font-semibold text-slate-800">{t('staffLeave.myLeaveRequests')}</h3>
        </div>
        
        {requests.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Calendar size={48} className="mx-auto mb-3 opacity-30" />
            <p>{t('staffLeave.noRequestsMonth')}</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {requests.map((request) => (
              <div key={request.id} className="p-4 hover:bg-slate-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                      request.leave_type === 'off_day' ? 'bg-blue-100' : 'bg-red-100'
                    }`}>
                      {request.leave_type === 'off_day' 
                        ? <CalendarOff size={24} className="text-blue-600" />
                        : <Thermometer size={24} className="text-red-600" />
                      }
                    </div>
                    <div>
                      <div className="font-medium text-slate-800">
                        {request.leave_type === 'off_day' ? 'Off Day' : 'Sakit'}
                      </div>
                      <div className="text-sm text-slate-500">
                        {request.date}
                        {request.leave_type === 'sakit' && request.start_time && (
                          <span> • {request.start_time} - {request.end_time}</span>
                        )}
                      </div>
                      {request.reason && (
                        <div className="text-xs text-slate-400 mt-1">{request.reason}</div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-sm font-medium text-slate-600">{request.hours_deducted} hours</div>
                      {getStatusBadge(request.status)}
                    </div>
                    {request.status === 'pending' && (
                      <button
                        onClick={() => cancelRequest(request.id)}
                        className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="Cancel request"
                      >
                        <Trash2 size={18} />
                      </button>
                    )}
                  </div>
                </div>
                {request.admin_note && (
                  <div className="mt-2 p-2 bg-slate-50 rounded text-sm text-slate-600">
                    <span className="font-medium">Admin note:</span> {request.admin_note}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
