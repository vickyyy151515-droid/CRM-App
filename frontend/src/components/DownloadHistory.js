import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Download } from 'lucide-react';

export default function DownloadHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const response = await api.get('/download-history');
      setHistory(response.data);
    } catch (error) {
      toast.error('Failed to load download history');
    } finally {
      setLoading(false);
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

  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Download History</h2>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading history...</div>
      ) : history.length === 0 ? (
        <div className="text-center py-12">
          <Download className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600">No downloads yet</p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="download-history-list">
          {history.map((item) => (
            <div
              key={item.id}
              className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm"
              data-testid={`history-item-${item.id}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-slate-900 mb-1">{item.database_name}</h4>
                  <div className="flex items-center gap-3 text-sm text-slate-600">
                    <span>Downloaded by: <strong>{item.downloaded_by_name}</strong></span>
                    <span>•</span>
                    <span>{formatDate(item.downloaded_at)}</span>
                  </div>
                </div>
                <Download className="text-emerald-600" size={20} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}