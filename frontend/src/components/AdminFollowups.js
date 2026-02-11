import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { AlertCircle, Clock, CheckCircle2, RefreshCw, Filter, ChevronDown, ChevronUp, Package, Database, Users, Phone } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function AdminFollowups() {
  const { t } = useLanguage();
  const [followups, setFollowups] = useState([]);
  const [summary, setSummary] = useState({
    total: 0, critical: 0, high: 0, medium: 0, low: 0, deposited: 0
  });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [expandedRecords, setExpandedRecords] = useState({});

  // Filters
  const [staffList, setStaffList] = useState([]);
  const [selectedStaff, setSelectedStaff] = useState('all');
  const [products, setProducts] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('all');
  const [selectedDatabase, setSelectedDatabase] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  // Load staff list
  useEffect(() => {
    const loadStaff = async () => {
      try {
        const res = await api.get('/users');
        setStaffList((res.data || []).filter(u => u.role === 'staff'));
      } catch { /* ignore */ }
    };
    loadStaff();
  }, []);

  // Load filter options
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const params = {};
        if (selectedStaff !== 'all') params.staff_id = selectedStaff;
        const res = await api.get('/followups/filters', { params });
        setProducts(res.data.products || []);
        setDatabases(res.data.databases || []);
      } catch { /* ignore */ }
    };
    loadFilters();
  }, [selectedStaff]);

  const loadFollowups = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filter !== 'all') params.urgency = filter;
      if (selectedStaff !== 'all') params.staff_id = selectedStaff;
      if (selectedProduct !== 'all') params.product_id = selectedProduct;
      if (selectedDatabase !== 'all') params.database_id = selectedDatabase;
      const res = await api.get('/followups', { params });
      setFollowups(res.data.followups || []);
      setSummary(res.data.summary || { total: 0, critical: 0, high: 0, medium: 0, low: 0, deposited: 0 });
    } catch {
      toast.error('Failed to load follow-ups');
    } finally {
      setLoading(false);
    }
  }, [filter, selectedStaff, selectedProduct, selectedDatabase]);

  useEffect(() => {
    loadFollowups();
  }, [loadFollowups]);

  useEffect(() => {
    setSelectedProduct('all');
    setSelectedDatabase('all');
  }, [selectedStaff]);

  useEffect(() => {
    setSelectedDatabase('all');
  }, [selectedProduct]);

  const toggleExpand = (recordId) => {
    setExpandedRecords(prev => ({ ...prev, [recordId]: !prev[recordId] }));
  };

  const filteredDatabases = selectedProduct === 'all'
    ? databases
    : databases.filter(db => db.product_id === selectedProduct);

  const getUrgencyBadge = (urgency) => {
    switch (urgency) {
      case 'critical':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700"><AlertCircle size={12} />7+ days</span>;
      case 'high':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-700"><Clock size={12} />3+ days</span>;
      case 'medium':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-700"><Clock size={12} />1+ day</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700"><CheckCircle2 size={12} />Today</span>;
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
    return new Date(dateStr).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const activeFiltersCount = (selectedStaff !== 'all' ? 1 : 0) + (selectedProduct !== 'all' ? 1 : 0) + (selectedDatabase !== 'all' ? 1 : 0);

  // Group followups by staff
  const groupedByStaff = {};
  followups.forEach(f => {
    const sid = f.staff_id || 'unknown';
    if (!groupedByStaff[sid]) {
      groupedByStaff[sid] = { staff_name: f.staff_name || 'Unknown', items: [] };
    }
    groupedByStaff[sid].items.push(f);
  });

  return (
    <div data-testid="admin-followups">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Follow-up Reminders</h2>
          <p className="text-sm text-slate-500 mt-1">View and monitor all staff follow-up reminders</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              showFilters || activeFiltersCount > 0
                ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
            data-testid="admin-followup-toggle-filters"
          >
            <Filter size={16} />
            Filter
            {activeFiltersCount > 0 && (
              <span className="bg-indigo-600 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[20px]">{activeFiltersCount}</span>
            )}
          </button>
          <button
            onClick={loadFollowups}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
            data-testid="admin-followup-refresh"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-6" data-testid="admin-followup-filters">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
                <Users size={14} /> Staff
              </label>
              <select
                value={selectedStaff}
                onChange={e => setSelectedStaff(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                data-testid="admin-followup-staff-filter"
              >
                <option value="all">All Staff</option>
                {staffList.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
                <Package size={14} /> Product
              </label>
              <select
                value={selectedProduct}
                onChange={e => setSelectedProduct(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="all">All Products</option>
                {products.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
                <Database size={14} /> Database
              </label>
              <select
                value={selectedDatabase}
                onChange={e => setSelectedDatabase(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="all">All Databases</option>
                {filteredDatabases.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {[
          { label: 'Total', value: summary.total, color: 'slate', onClick: () => setFilter('all') },
          { label: 'Critical (7+d)', value: summary.critical, color: 'red', onClick: () => setFilter(filter === 'critical' ? 'all' : 'critical') },
          { label: 'High (3+d)', value: summary.high, color: 'orange', onClick: () => setFilter(filter === 'high' ? 'all' : 'high') },
          { label: 'Medium (1+d)', value: summary.medium, color: 'yellow', onClick: () => setFilter(filter === 'medium' ? 'all' : 'medium') },
          { label: 'Deposited', value: summary.deposited, color: 'emerald', onClick: null },
        ].map(card => (
          <div
            key={card.label}
            onClick={card.onClick}
            className={`rounded-xl border p-4 transition-all ${
              card.onClick ? 'cursor-pointer hover:shadow-md' : ''
            } ${
              (card.label === 'Total' && filter === 'all') ||
              (card.label.startsWith('Critical') && filter === 'critical') ||
              (card.label.startsWith('High') && filter === 'high') ||
              (card.label.startsWith('Medium') && filter === 'medium')
                ? `border-${card.color}-400 bg-${card.color}-50 ring-2 ring-${card.color}-200`
                : 'border-slate-200 bg-white'
            }`}
          >
            <p className="text-xs font-medium text-slate-500 uppercase">{card.label}</p>
            <p className={`text-2xl font-bold text-${card.color}-600 mt-1`}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Followup List */}
      {loading ? (
        <div className="text-center py-12">
          <RefreshCw className="animate-spin mx-auto text-slate-400" size={32} />
          <p className="text-sm text-slate-500 mt-2">Loading...</p>
        </div>
      ) : followups.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
          <CheckCircle2 size={48} className="mx-auto text-emerald-400 mb-3" />
          <p className="text-lg font-medium text-slate-700">No pending follow-ups</p>
          <p className="text-sm text-slate-500">All staff are up to date</p>
        </div>
      ) : selectedStaff === 'all' ? (
        /* Grouped by staff view */
        <div className="space-y-6">
          {Object.entries(groupedByStaff).map(([staffId, group]) => (
            <div key={staffId} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users size={16} className="text-slate-500" />
                  <span className="font-semibold text-slate-800">{group.staff_name}</span>
                  <span className="text-xs bg-slate-200 text-slate-600 rounded-full px-2 py-0.5">{group.items.length}</span>
                </div>
              </div>
              <div className="divide-y divide-slate-100">
                {group.items.map(followup => (
                  <FollowupRow
                    key={followup.record_id}
                    followup={followup}
                    expanded={expandedRecords[followup.record_id]}
                    onToggle={() => toggleExpand(followup.record_id)}
                    getUrgencyBadge={getUrgencyBadge}
                    getUrgencyBorder={getUrgencyBorder}
                    formatDate={formatDate}
                    showStaff={false}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Single staff flat list */
        <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
          {followups.map(followup => (
            <FollowupRow
              key={followup.record_id}
              followup={followup}
              expanded={expandedRecords[followup.record_id]}
              onToggle={() => toggleExpand(followup.record_id)}
              getUrgencyBadge={getUrgencyBadge}
              getUrgencyBorder={getUrgencyBorder}
              formatDate={formatDate}
              showStaff={false}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FollowupRow({ followup, expanded, onToggle, getUrgencyBadge, getUrgencyBorder, formatDate, showStaff }) {
  const rowData = followup.row_data || {};
  const displayFields = Object.entries(rowData).filter(([key]) =>
    !['_id', 'id', 'record_id', 'assigned_to', 'status', 'assigned_at'].includes(key)
  );

  return (
    <div className={`${getUrgencyBorder(followup.urgency)}`}>
      <div
        className="px-5 py-3 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-4 min-w-0">
          <div className="min-w-0">
            <p className="font-medium text-slate-900 truncate">{followup.customer_display}</p>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
              <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{followup.product_name}</span>
              <span>{followup.database_name}</span>
              {showStaff && <span className="text-indigo-600 font-medium">{followup.staff_name}</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {getUrgencyBadge(followup.urgency)}
          <span className="text-xs text-slate-400">{formatDate(followup.respond_date)}</span>
          {expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
        </div>
      </div>
      {expanded && displayFields.length > 0 && (
        <div className="px-5 pb-3 bg-slate-50 border-t border-slate-100">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 py-2">
            {displayFields.slice(0, 9).map(([key, value]) => (
              <div key={key} className="text-xs">
                <span className="text-slate-400">{key}:</span>
                <span className="ml-1 text-slate-700 font-medium">{String(value || '-')}</span>
              </div>
            ))}
          </div>
          {followup.whatsapp_status && (
            <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
              <Phone size={12} /> WhatsApp: {followup.whatsapp_status}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
