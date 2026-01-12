import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Clock, CheckCircle, XCircle, Download } from 'lucide-react';

export default function MyRequests({ onUpdate }) {
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

  const handleDownload = async (request) => {
    toast.info('Records have been assigned to you. Check "My Assigned Customers" tab.');
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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <Clock className="text-amber-600" size={20} />;
      case 'approved':
        return <CheckCircle className="text-emerald-600" size={20} />;
      case 'rejected':
        return <XCircle className="text-rose-600" size={20} />;
      default:
        return null;
    }
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

  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">My Download Requests</h2>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading requests...</div>
      ) : requests.length === 0 ? (
        <div className="text-center py-12">
          <Clock className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600">No requests yet</p>
          <p className="text-sm text-slate-500 mt-2">Request access to databases from the Browse Databases page</p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="my-requests-list">
          {requests.map((request) => (
            <div
              key={request.id}
              className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm"
              data-testid={`my-request-${request.id}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    {getStatusIcon(request.status)}
                    <h4 className="text-lg font-semibold text-slate-900">{request.database_name}</h4>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-600 mb-3">
                    <span className="font-medium">{request.record_count} customer records requested</span>
                    <span>•</span>
                    <span>Requested: {formatDate(request.requested_at)}</span>
                    {request.reviewed_at && (
                      <>
                        <span>•</span>
                        <span>Reviewed: {formatDate(request.reviewed_at)}</span>
                      </>
                    )}
                  </div>
                  {getStatusBadge(request.status)}
                  {request.status === 'approved' && (
                    <p className="text-sm text-emerald-600 mt-2">
                      ✓ Records assigned! View them in "My Assigned Customers" tab
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}