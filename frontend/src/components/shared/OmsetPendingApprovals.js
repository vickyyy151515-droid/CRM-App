import { useState, useEffect, useCallback } from 'react';
import { api } from '../../App';
import { toast } from 'sonner';
import { Clock, CheckCircle, XCircle, AlertTriangle, User } from 'lucide-react';

export default function OmsetPendingApprovals() {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});

  const loadPending = useCallback(async () => {
    try {
      const res = await api.get('/omset/pending');
      setPending(res.data);
    } catch (err) {
      toast.error('Failed to load pending records');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPending(); }, [loadPending]);

  const handleApprove = async (id) => {
    setActionLoading(prev => ({ ...prev, [id]: 'approve' }));
    try {
      await api.post(`/omset/${id}/approve`);
      toast.success('Record approved');
      setPending(prev => prev.filter(r => r.id !== id));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve');
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }));
    }
  };

  const handleDecline = async (id) => {
    if (!window.confirm('Decline and delete this record?')) return;
    setActionLoading(prev => ({ ...prev, [id]: 'decline' }));
    try {
      await api.post(`/omset/${id}/decline`);
      toast.success('Record declined and deleted');
      setPending(prev => prev.filter(r => r.id !== id));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to decline');
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }));
    }
  };

  if (loading) return <div className="text-center py-12 text-slate-500">Loading pending records...</div>;

  if (pending.length === 0) {
    return (
      <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
        <CheckCircle className="mx-auto text-emerald-400 mb-3" size={48} />
        <p className="text-slate-600 dark:text-slate-400 font-medium">No pending approvals</p>
        <p className="text-sm text-slate-500 mt-1">All omset records are approved</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        <AlertTriangle size={14} className="inline mr-1 text-amber-500" />
        These records need approval because the customer belongs to another staff's reserved list.
      </p>
      {pending.map(record => (
        <div key={record.id} className="bg-white dark:bg-slate-800 rounded-xl border border-amber-200 dark:border-amber-800 p-4" data-testid={`pending-${record.id}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Clock size={16} className="text-amber-500" />
                <span className="font-semibold text-slate-900 dark:text-white">{record.customer_id}</span>
                {record.customer_name && <span className="text-sm text-slate-500">({record.customer_name})</span>}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <span className="text-slate-500">Staff:</span>
                  <span className="ml-1 font-medium text-slate-700 dark:text-slate-300">{record.staff_name}</span>
                </div>
                <div>
                  <span className="text-slate-500">Product:</span>
                  <span className="ml-1 font-medium text-slate-700 dark:text-slate-300">{record.product_name}</span>
                </div>
                <div>
                  <span className="text-slate-500">Date:</span>
                  <span className="ml-1 font-medium text-slate-700 dark:text-slate-300">{record.record_date}</span>
                </div>
                <div>
                  <span className="text-slate-500">Depo:</span>
                  <span className="ml-1 font-medium text-slate-700 dark:text-slate-300">Rp {(record.depo_total || 0).toLocaleString('id-ID')}</span>
                </div>
              </div>
              {record.conflict_info && (
                <div className="mt-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 rounded-lg text-sm text-amber-700 dark:text-amber-400 flex items-center gap-1">
                  <User size={14} />
                  Reserved by: <strong>{record.conflict_info.reserved_by_staff_name}</strong>
                </div>
              )}
            </div>
            <div className="flex gap-2 ml-4">
              <button
                onClick={() => handleApprove(record.id)}
                disabled={!!actionLoading[record.id]}
                className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 text-sm flex items-center gap-1"
                data-testid={`approve-${record.id}`}
              >
                <CheckCircle size={14} />
                {actionLoading[record.id] === 'approve' ? '...' : 'Approve'}
              </button>
              <button
                onClick={() => handleDecline(record.id)}
                disabled={!!actionLoading[record.id]}
                className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm flex items-center gap-1"
                data-testid={`decline-${record.id}`}
              >
                <XCircle size={14} />
                {actionLoading[record.id] === 'decline' ? '...' : 'Decline'}
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
