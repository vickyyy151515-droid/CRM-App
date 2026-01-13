import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Clock, CheckSquare, Square } from 'lucide-react';

export default function DownloadRequests({ onUpdate }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequests, setSelectedRequests] = useState([]);
  const [bulkProcessing, setBulkProcessing] = useState(false);

  useEffect(() => {
    loadRequests();
  }, []);

  const loadRequests = async () => {
    try {
      const response = await api.get('/download-requests');
      setRequests(response.data);
      setSelectedRequests([]);
    } catch (error) {
      toast.error('Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id) => {
    try {
      await api.patch(`/download-requests/${id}/approve`);
      toast.success('Request approved!');
      loadRequests();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve request');
    }
  };

  const handleReject = async (id) => {
    try {
      await api.patch(`/download-requests/${id}/reject`);
      toast.success('Request rejected');
      loadRequests();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject request');
    }
  };

  const toggleSelectRequest = (id) => {
    setSelectedRequests(prev => 
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    );
  };

  const selectAllPending = () => {
    const pendingIds = requests.filter(r => r.status === 'pending').map(r => r.id);
    setSelectedRequests(pendingIds);
  };

  const clearSelection = () => {
    setSelectedRequests([]);
  };

  const handleBulkAction = async (action) => {
    if (selectedRequests.length === 0) {
      toast.error('Please select requests first');
      return;
    }
    
    setBulkProcessing(true);
    try {
      const response = await api.post('/bulk/requests', {
        request_ids: selectedRequests,
        action: action
      });
      toast.success(response.data.message);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.warning(err));
      }
      loadRequests();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} requests`);
    } finally {
      setBulkProcessing(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'border-transparent bg-amber-100 text-amber-700',
      approved: 'border-transparent bg-emerald-100 text-emerald-700',
      rejected: 'border-transparent bg-rose-100 text-rose-700'
    };

    return (
      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const pendingRequests = requests.filter(r => r.status === 'pending');
  const reviewedRequests = requests.filter(r => r.status !== 'pending');

  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Download Requests</h2>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading requests...</div>
      ) : (
        <div className="space-y-8">
          {pendingRequests.length > 0 && (
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <h3 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                  <Clock className="text-amber-600" size={20} />
                  Pending Requests ({pendingRequests.length})
                </h3>
                
                {/* Bulk Actions */}
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={selectAllPending}
                    className="h-9 px-3 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Select All
                  </button>
                  <button
                    onClick={clearSelection}
                    className="h-9 px-3 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Clear
                  </button>
                  <span className="text-sm text-slate-500">
                    {selectedRequests.length} selected
                  </span>
                  <button
                    onClick={() => handleBulkAction('approve')}
                    disabled={bulkProcessing || selectedRequests.length === 0}
                    className="h-9 px-4 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-1"
                    data-testid="bulk-approve-btn"
                  >
                    <CheckCircle size={14} />
                    Bulk Approve
                  </button>
                  <button
                    onClick={() => handleBulkAction('reject')}
                    disabled={bulkProcessing || selectedRequests.length === 0}
                    className="h-9 px-4 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-1"
                    data-testid="bulk-reject-btn"
                  >
                    <XCircle size={14} />
                    Bulk Reject
                  </button>
                </div>
              </div>
              
              <div className="space-y-4" data-testid="pending-requests-list">
                {pendingRequests.map((request) => (
                  <div
                    key={request.id}
                    className={`bg-white border rounded-xl p-4 sm:p-6 shadow-sm transition-colors ${
                      selectedRequests.includes(request.id) ? 'border-indigo-400 bg-indigo-50/50' : 'border-slate-200'
                    }`}
                    data-testid={`request-item-${request.id}`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <button
                          onClick={() => toggleSelectRequest(request.id)}
                          className="mt-1 text-slate-400 hover:text-indigo-600"
                        >
                          {selectedRequests.includes(request.id) ? (
                            <CheckSquare size={20} className="text-indigo-600" />
                          ) : (
                            <Square size={20} />
                          )}
                        </button>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-lg font-semibold text-slate-900 mb-1 truncate">{request.database_name}</h4>
                          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 mb-3">
                            <span className="font-medium">{request.record_count} records</span>
                            <span className="hidden sm:inline">•</span>
                            <span>By: <strong>{request.requested_by_name}</strong></span>
                            <span className="hidden sm:inline">•</span>
                            <span className="text-xs">{formatDate(request.requested_at)}</span>
                          </div>
                          {getStatusBadge(request.status)}
                        </div>
                      </div>

                      <div className="flex gap-2 ml-8 sm:ml-4">
                        <button
                          onClick={() => handleApprove(request.id)}
                          data-testid={`approve-request-${request.id}`}
                          className="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border border-emerald-200 font-medium px-3 py-2 rounded-md transition-colors flex items-center gap-1 text-sm"
                        >
                          <CheckCircle size={16} />
                          <span className="hidden sm:inline">Approve</span>
                        </button>
                        <button
                          onClick={() => handleReject(request.id)}
                          data-testid={`reject-request-${request.id}`}
                          className="bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 font-medium px-3 py-2 rounded-md transition-colors flex items-center gap-1 text-sm"
                        >
                          <XCircle size={16} />
                          <span className="hidden sm:inline">Reject</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {reviewedRequests.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold text-slate-900 mb-4">Request History</h3>
              <div className="space-y-4" data-testid="reviewed-requests-list">
                {reviewedRequests.map((request) => (
                  <div
                    key={request.id}
                    className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-slate-900 mb-1">{request.database_name}</h4>
                        <div className="flex items-center gap-3 text-sm text-slate-600 mb-2">
                          <span className="font-medium">{request.record_count} customer records</span>
                          <span>•</span>
                          <span>Requested by: <strong>{request.requested_by_name}</strong></span>
                          <span>•</span>
                          <span>{formatDate(request.requested_at)}</span>
                        </div>
                        {request.reviewed_at && (
                          <div className="text-sm text-slate-600 mb-3">
                            Reviewed by <strong>{request.reviewed_by_name}</strong> on {formatDate(request.reviewed_at)}
                          </div>
                        )}
                        {getStatusBadge(request.status)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {requests.length === 0 && (
            <div className="text-center py-12">
              <Clock className="mx-auto text-slate-300 mb-4" size={64} />
              <p className="text-slate-600">No download requests yet</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}