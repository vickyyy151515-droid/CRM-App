import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { AlertCircle, Clock, CheckCircle2, Phone, RefreshCw, Filter, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export default function StaffFollowups() {
  const [followups, setFollowups] = useState([]);
  const [summary, setSummary] = useState({
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    deposited: 0
  });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [expandedRecords, setExpandedRecords] = useState({});

  const loadFollowups = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filter !== 'all') {
        params.urgency = filter;
      }
      const response = await api.get('/followups', { params });
      setFollowups(response.data.followups || []);
      setSummary(response.data.summary || {
        total: 0, critical: 0, high: 0, medium: 0, low: 0, deposited: 0
      });
    } catch (error) {
      toast.error('Failed to load follow-ups');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadFollowups();
    // Auto-refresh every 5 minutes
    const interval = setInterval(loadFollowups, 300000);
    return () => clearInterval(interval);
  }, [loadFollowups]);

  const toggleExpand = (recordId) => {
    setExpandedRecords(prev => ({
      ...prev,
      [recordId]: !prev[recordId]
    }));
  };

  const getUrgencyBadge = (urgency) => {
    switch (urgency) {
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 border border-red-200">
            <AlertCircle size={12} />
            7+ days
          </span>
        );
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-700 border border-orange-200">
            <Clock size={12} />
            3+ days
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-700 border border-yellow-200">
            <Clock size={12} />
            1+ day
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700 border border-green-200">
            <CheckCircle2 size={12} />
            Today
          </span>
        );
    }
  };

  const getUrgencyBorder = (urgency) => {
    switch (urgency) {
      case 'critical': return 'border-l-4 border-l-red-500';
      case 'high': return 'border-l-4 border-l-orange-500';
      case 'medium': return 'border-l-4 border-l-yellow-500';
      default: return 'border-l-4 border-l-green-500';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', { 
      day: 'numeric', 
      month: 'short',
      year: 'numeric'
    });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Follow-up Reminders</h2>
          <p className="text-sm text-slate-500 mt-1">
            Customers who responded "Ya" but haven't deposited yet
          </p>
        </div>
        <button
          onClick={loadFollowups}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div 
          className={`bg-white border rounded-xl p-4 cursor-pointer transition-all ${filter === 'all' ? 'ring-2 ring-indigo-500 border-indigo-300' : 'border-slate-200 hover:border-slate-300'}`}
          onClick={() => setFilter('all')}
        >
          <p className="text-2xl font-bold text-slate-900">{summary.total}</p>
          <p className="text-sm text-slate-600">Total Pending</p>
        </div>
        <div 
          className={`bg-red-50 border rounded-xl p-4 cursor-pointer transition-all ${filter === 'critical' ? 'ring-2 ring-red-500 border-red-300' : 'border-red-200 hover:border-red-300'}`}
          onClick={() => setFilter('critical')}
        >
          <p className="text-2xl font-bold text-red-700">{summary.critical}</p>
          <p className="text-sm text-red-600">Critical (7+ days)</p>
        </div>
        <div 
          className={`bg-orange-50 border rounded-xl p-4 cursor-pointer transition-all ${filter === 'high' ? 'ring-2 ring-orange-500 border-orange-300' : 'border-orange-200 hover:border-orange-300'}`}
          onClick={() => setFilter('high')}
        >
          <p className="text-2xl font-bold text-orange-700">{summary.high}</p>
          <p className="text-sm text-orange-600">High (3+ days)</p>
        </div>
        <div 
          className={`bg-yellow-50 border rounded-xl p-4 cursor-pointer transition-all ${filter === 'medium' ? 'ring-2 ring-yellow-500 border-yellow-300' : 'border-yellow-200 hover:border-yellow-300'}`}
          onClick={() => setFilter('medium')}
        >
          <p className="text-2xl font-bold text-yellow-700">{summary.medium}</p>
          <p className="text-sm text-yellow-600">Medium (1+ day)</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <p className="text-2xl font-bold text-emerald-700">{summary.deposited}</p>
          <p className="text-sm text-emerald-600">Deposited ✓</p>
        </div>
      </div>

      {/* Follow-ups List */}
      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading follow-ups...</div>
      ) : followups.length === 0 ? (
        <div className="text-center py-12 bg-white border border-slate-200 rounded-xl">
          <CheckCircle2 className="mx-auto text-emerald-400 mb-4" size={64} />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">All caught up!</h3>
          <p className="text-slate-600">
            {filter === 'all' 
              ? 'No customers waiting for follow-up' 
              : `No ${filter} priority follow-ups`}
          </p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="followups-list">
          {followups.map((followup) => (
            <div
              key={followup.record_id}
              className={`bg-white border border-slate-200 rounded-xl overflow-hidden transition-all hover:shadow-md ${getUrgencyBorder(followup.urgency)}`}
              data-testid={`followup-${followup.record_id}`}
            >
              {/* Main Row */}
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    {/* Urgency Badge */}
                    {getUrgencyBadge(followup.urgency)}
                    
                    {/* Customer Info */}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-900 truncate">
                        {followup.customer_display}
                      </h3>
                      <p className="text-sm text-slate-500 truncate">
                        {followup.product_name} • {followup.database_name}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    {/* Days Since */}
                    <div className="text-right hidden sm:block">
                      <p className="text-sm font-medium text-slate-900">
                        {followup.days_since_response} day{followup.days_since_response !== 1 ? 's' : ''} ago
                      </p>
                      <p className="text-xs text-slate-500">
                        Responded: {formatDate(followup.respond_date)}
                      </p>
                    </div>
                    
                    {/* WhatsApp Status */}
                    {followup.whatsapp_status && (
                      <span className={`hidden md:inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                        followup.whatsapp_status === 'ada' 
                          ? 'bg-green-100 text-green-700' 
                          : followup.whatsapp_status === 'ceklis1'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        <Phone size={12} />
                        {followup.whatsapp_status === 'ada' ? 'WA Ada' : 
                         followup.whatsapp_status === 'ceklis1' ? 'Ceklis 1' : 'Tidak Ada'}
                      </span>
                    )}
                    
                    {/* Expand Button */}
                    <button
                      onClick={() => toggleExpand(followup.record_id)}
                      className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                    >
                      {expandedRecords[followup.record_id] ? (
                        <ChevronUp size={20} />
                      ) : (
                        <ChevronDown size={20} />
                      )}
                    </button>
                  </div>
                </div>
                
                {/* Mobile: Days Since */}
                <div className="mt-2 sm:hidden">
                  <p className="text-sm text-slate-600">
                    <span className="font-medium">{followup.days_since_response} day{followup.days_since_response !== 1 ? 's' : ''}</span> since response
                  </p>
                </div>
              </div>
              
              {/* Expanded Details */}
              {expandedRecords[followup.record_id] && (
                <div className="px-4 pb-4 border-t border-slate-100 bg-slate-50">
                  <div className="pt-3">
                    <h4 className="text-sm font-medium text-slate-700 mb-2">Customer Details</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(followup.row_data || {}).slice(0, 6).map(([key, value]) => (
                        <div key={key} className="bg-white rounded-lg p-2 border border-slate-200">
                          <p className="text-xs text-slate-500 truncate">{key}</p>
                          <p className="text-sm font-medium text-slate-900 truncate">{value || '-'}</p>
                        </div>
                      ))}
                    </div>
                    
                    {/* Action Hint */}
                    <div className="mt-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                      <p className="text-sm text-indigo-700">
                        <strong>Tip:</strong> Contact this customer and record their deposit in <strong>OMSET CRM</strong> when they deposit.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
