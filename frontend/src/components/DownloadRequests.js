import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Clock } from 'lucide-react';

export default function DownloadRequests({ onUpdate }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRequests();
  }, []);

  const loadRequests = async () => {
    try {
      const response = await api.get('/download-requests');
      setRequests(response.data);
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
              <h3 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <Clock className="text-amber-600" size={20} />
                Pending Requests ({pendingRequests.length})
              </h3>
              <div className="space-y-4" data-testid="pending-requests-list">
                {pendingRequests.map((request) => (
                  <div
                    key={request.id}
                    className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm"
                    data-testid={`request-item-${request.id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-slate-900 mb-1">{request.database_name}</h4>
                        <div className="flex items-center gap-3 text-sm text-slate-600 mb-3">
                          <span>Requested by: <strong>{request.requested_by_name}</strong></span>
                          <span>•</span>
                          <span>{formatDate(request.requested_at)}</span>
                        </div>
                        {getStatusBadge(request.status)}
                      </div>

                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleApprove(request.id)}
                          data-testid={`approve-request-${request.id}`}
                          className="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border border-emerald-200 font-medium px-4 py-2 rounded-md transition-colors flex items-center gap-2"
                        >
                          <CheckCircle size={16} />
                          Approve
                        </button>
                        <button
                          onClick={() => handleReject(request.id)}
                          data-testid={`reject-request-${request.id}`}
                          className="bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 font-medium px-4 py-2 rounded-md transition-colors flex items-center gap-2"
                        >
                          <XCircle size={16} />
                          Reject
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
                    className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-slate-900 mb-1">{request.database_name}</h4>
                        <div className="flex items-center gap-3 text-sm text-slate-600 mb-2">
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