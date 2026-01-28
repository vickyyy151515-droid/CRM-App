import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Calendar, Clock, CheckCircle, XCircle, User,
  CalendarOff, Thermometer, Filter, Timer
} from 'lucide-react';

const MONTH_NAMES = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

export default function AdminLeaveRequests() {
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [processingId, setProcessingId] = useState(null);
  const [adminNote, setAdminNote] = useState('');
  const [showNoteModal, setShowNoteModal] = useState(null);

  useEffect(() => {
    loadData();
  }, [statusFilter, selectedYear, selectedMonth]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {
        year: selectedYear,
        month: selectedMonth
      };
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      
      const response = await api.get('/leave/all-requests', { params });
      setRequests(response.data.requests);
      setPendingCount(response.data.pending_count);
    } catch (error) {
      console.error('Failed to load leave requests:', error);
      toast.error('Failed to load leave requests');
    } finally {
      setLoading(false);
    }
  };

  const processRequest = async (requestId, action) => {
    setProcessingId(requestId);
    try {
      await api.put(`/leave/request/${requestId}/action`, {
        action: action,
        admin_note: adminNote || null
      });
      toast.success(`Request ${action}ed successfully`);
      setShowNoteModal(null);
      setAdminNote('');
      loadData();
    } catch (error) {
      console.error('Failed to process request:', error);
      toast.error(error.response?.data?.detail || 'Failed to process request');
    } finally {
      setProcessingId(null);
    }
  };

  const cancelApprovedRequest = async (requestId) => {
    if (!window.confirm('Are you sure you want to cancel this approved leave request? The hours will be returned to the staff member.')) {
      return;
    }
    setProcessingId(requestId);
    try {
      const response = await api.put(`/leave/request/${requestId}/cancel`);
      toast.success(`Leave cancelled. ${response.data.hours_returned} hour(s) returned to ${response.data.staff_name}`);
      loadData();
    } catch (error) {
      console.error('Failed to cancel request:', error);
      toast.error(error.response?.data?.detail || 'Failed to cancel request');
    } finally {
      setProcessingId(null);
    }
  };

  const openNoteModal = (requestId, action) => {
    setShowNoteModal({ requestId, action });
    setAdminNote('');
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'approved':
        return <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1"><CheckCircle size={12} /> Approved</span>;
      case 'rejected':
        return <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium flex items-center gap-1"><XCircle size={12} /> Rejected</span>;
      case 'cancelled':
        return <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium flex items-center gap-1"><XCircle size={12} /> Cancelled</span>;
      default:
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium flex items-center gap-1"><Clock size={12} /> Pending</span>;
    }
  };

  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1];

  if (loading && requests.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-leave-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Leave Requests</h1>
          <p className="text-slate-500 text-sm mt-1">Manage staff off day and sick leave requests</p>
        </div>
        {pendingCount > 0 && (
          <div className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg flex items-center gap-2">
            <Clock size={18} />
            <span className="font-medium">{pendingCount} pending request(s)</span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={18} className="text-slate-500" />
          <span className="font-medium text-slate-700">Filters</span>
        </div>
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="all">All</option>
            </select>
          </div>
          {statusFilter !== 'pending' && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-1">Year</label>
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
                <label className="block text-sm font-medium text-slate-600 mb-1">Month</label>
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
            </>
          )}
        </div>
      </div>

      {/* Requests List */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Leave Requests</h3>
          <span className="text-sm text-slate-500">{requests.length} request(s)</span>
        </div>
        
        {requests.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Calendar size={48} className="mx-auto mb-3 opacity-30" />
            <p>No leave requests found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {requests.map((request) => (
              <div key={request.id} className="p-4 hover:bg-slate-50">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                      request.leave_type === 'off_day' ? 'bg-blue-100' : 'bg-red-100'
                    }`}>
                      {request.leave_type === 'off_day' 
                        ? <CalendarOff size={24} className="text-blue-600" />
                        : <Thermometer size={24} className="text-red-600" />
                      }
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-slate-800">
                          {request.leave_type === 'off_day' ? 'Off Day' : 'Sakit'}
                        </span>
                        {getStatusBadge(request.status)}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-sm text-slate-600">
                        <User size={14} />
                        <span className="font-medium">{request.staff_name}</span>
                      </div>
                      <div className="text-sm text-slate-500 mt-1">
                        <Calendar size={14} className="inline mr-1" />
                        {request.date}
                        {request.leave_type === 'sakit' && request.start_time && (
                          <span className="ml-2">
                            <Clock size={14} className="inline mr-1" />
                            {request.start_time} - {request.end_time}
                          </span>
                        )}
                      </div>
                      {request.reason && (
                        <div className="text-sm text-slate-500 mt-1 italic">
                          &quot;{request.reason}&quot;
                        </div>
                      )}
                      <div className="flex items-center gap-1 mt-2 text-xs text-slate-400">
                        <Timer size={12} />
                        <span>{request.hours_deducted} hours to be deducted</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end gap-2">
                    {request.status === 'pending' ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => openNoteModal(request.id, 'approve')}
                          disabled={processingId === request.id}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center gap-1"
                        >
                          <CheckCircle size={16} />
                          Approve
                        </button>
                        <button
                          onClick={() => openNoteModal(request.id, 'reject')}
                          disabled={processingId === request.id}
                          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-1"
                        >
                          <XCircle size={16} />
                          Reject
                        </button>
                      </div>
                    ) : (
                      <div className="text-right text-xs text-slate-500">
                        <div>{request.status === 'approved' ? 'Approved' : 'Rejected'} by</div>
                        <div className="font-medium">{request.reviewed_by_name}</div>
                        {request.reviewed_at && (
                          <div>{new Date(request.reviewed_at).toLocaleDateString()}</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                {request.admin_note && (
                  <div className="mt-3 p-2 bg-slate-50 rounded text-sm text-slate-600 ml-16">
                    <span className="font-medium">Note:</span> {request.admin_note}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Note Modal */}
      {showNoteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-xl font-bold text-slate-800">
                {showNoteModal.action === 'approve' ? 'Approve' : 'Reject'} Leave Request
              </h2>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Admin Note (Optional)
                </label>
                <textarea
                  value={adminNote}
                  onChange={(e) => setAdminNote(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder={`Add a note for the staff member...`}
                />
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowNoteModal(null);
                    setAdminNote('');
                  }}
                  className="flex-1 px-4 py-2 text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => processRequest(showNoteModal.requestId, showNoteModal.action)}
                  disabled={processingId === showNoteModal.requestId}
                  className={`flex-1 px-4 py-2 text-white rounded-lg transition-colors disabled:opacity-50 ${
                    showNoteModal.action === 'approve'
                      ? 'bg-green-600 hover:bg-green-700'
                      : 'bg-red-600 hover:bg-red-700'
                  }`}
                >
                  {processingId === showNoteModal.requestId 
                    ? 'Processing...' 
                    : showNoteModal.action === 'approve' ? 'Confirm Approve' : 'Confirm Reject'
                  }
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
