import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Clock, CheckSquare, Square, Filter, Calendar, Users, Package, TrendingUp, RefreshCw } from 'lucide-react';

export default function DownloadRequests({ onUpdate }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequests, setSelectedRequests] = useState([]);
  const [bulkProcessing, setBulkProcessing] = useState(false);
  
  // Filter states
  const [staffList, setStaffList] = useState([]);
  const [productList, setProductList] = useState([]);
  const [filterStaff, setFilterStaff] = useState('');
  const [filterProduct, setFilterProduct] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  
  // Stats
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadStaffAndProducts();
  }, []);

  useEffect(() => {
    loadRequests();
    loadStats();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStaff, filterProduct, filterDateFrom, filterDateTo, filterStatus]);

  const loadStaffAndProducts = async () => {
    try {
      const [staffRes, productsRes] = await Promise.all([
        api.get('/users'),
        api.get('/products')
      ]);
      setStaffList(staffRes.data.filter(u => u.role === 'staff') || []);
      setProductList(productsRes.data || []);
    } catch (error) {
      console.error('Failed to load filters data');
    }
  };

  const loadRequests = async () => {
    try {
      const params = new URLSearchParams();
      if (filterStaff) params.append('staff_id', filterStaff);
      if (filterProduct) params.append('product_id', filterProduct);
      if (filterDateFrom) params.append('date_from', filterDateFrom);
      if (filterDateTo) params.append('date_to', filterDateTo);
      if (filterStatus) params.append('status', filterStatus);
      
      const response = await api.get(`/download-requests?${params}`);
      setRequests(response.data);
      setSelectedRequests([]);
    } catch (error) {
      toast.error('Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const params = new URLSearchParams();
      if (filterStaff) params.append('staff_id', filterStaff);
      if (filterProduct) params.append('product_id', filterProduct);
      if (filterDateFrom) params.append('date_from', filterDateFrom);
      if (filterDateTo) params.append('date_to', filterDateTo);
      
      const response = await api.get(`/download-requests/stats?${params}`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats');
    }
  };

  const clearFilters = () => {
    setFilterStaff('');
    setFilterProduct('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterStatus('');
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
  
  const hasActiveFilters = filterStaff || filterProduct || filterDateFrom || filterDateTo || filterStatus;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Download Requests</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`h-9 px-4 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
              showFilters || hasActiveFilters
                ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300'
            }`}
            data-testid="toggle-filters-btn"
          >
            <Filter size={16} />
            Filters {hasActiveFilters && `(${[filterStaff, filterProduct, filterDateFrom, filterDateTo, filterStatus].filter(Boolean).length})`}
          </button>
          <button
            onClick={() => { loadRequests(); loadStats(); }}
            className="h-9 px-3 text-sm font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 rounded-lg transition-colors"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 mb-6" data-testid="filters-panel">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                <Users size={14} className="inline mr-1" /> Staff
              </label>
              <select
                value={filterStaff}
                onChange={(e) => setFilterStaff(e.target.value)}
                className="w-full h-9 px-3 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                data-testid="filter-staff"
              >
                <option value="">All Staff</option>
                {staffList.map(staff => (
                  <option key={staff.id} value={staff.id}>{staff.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                <Package size={14} className="inline mr-1" /> Product
              </label>
              <select
                value={filterProduct}
                onChange={(e) => setFilterProduct(e.target.value)}
                className="w-full h-9 px-3 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                data-testid="filter-product"
              >
                <option value="">All Products</option>
                {productList.map(product => (
                  <option key={product.id} value={product.id}>{product.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                <Calendar size={14} className="inline mr-1" /> From Date
              </label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="w-full h-9 px-3 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                data-testid="filter-date-from"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                <Calendar size={14} className="inline mr-1" /> To Date
              </label>
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="w-full h-9 px-3 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                data-testid="filter-date-to"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full h-9 px-3 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                data-testid="filter-status"
              >
                <option value="">All Status</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
          
          {hasActiveFilters && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={clearFilters}
                className="h-8 px-3 text-sm font-medium text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              >
                Clear All Filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4 mb-6" data-testid="stats-cards">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase mb-1">
              {(filterDateFrom || filterDateTo) ? 'Filtered Total' : 'Total Requests'}
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats.total_requests}</div>
            {(filterDateFrom || filterDateTo) && (
              <div className="text-xs text-slate-400 mt-1">
                {filterDateFrom && filterDateTo 
                  ? `${filterDateFrom} - ${filterDateTo}`
                  : filterDateFrom 
                    ? `From ${filterDateFrom}`
                    : `Until ${filterDateTo}`
                }
              </div>
            )}
          </div>
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
            <div className="text-xs font-medium text-amber-600 dark:text-amber-400 uppercase mb-1">Pending</div>
            <div className="text-2xl font-bold text-amber-700 dark:text-amber-300">{stats.pending}</div>
          </div>
          <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4">
            <div className="text-xs font-medium text-emerald-600 dark:text-emerald-400 uppercase mb-1">Approved</div>
            <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{stats.approved}</div>
          </div>
          <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl p-4">
            <div className="text-xs font-medium text-rose-600 dark:text-rose-400 uppercase mb-1">Rejected</div>
            <div className="text-2xl font-bold text-rose-700 dark:text-rose-300">{stats.rejected}</div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
            <div className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase mb-1">Today</div>
            <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">{stats.today?.requests || 0}</div>
            <div className="text-xs text-blue-500">{stats.today?.records || 0} records</div>
          </div>
          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-xl p-4">
            <div className="text-xs font-medium text-purple-600 dark:text-purple-400 uppercase mb-1">This Week</div>
            <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">{stats.this_week?.requests || 0}</div>
            <div className="text-xs text-purple-500">{stats.this_week?.records || 0} records</div>
          </div>
          <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-4">
            <div className="text-xs font-medium text-indigo-600 dark:text-indigo-400 uppercase mb-1">This Month</div>
            <div className="text-2xl font-bold text-indigo-700 dark:text-indigo-300">{stats.this_month?.requests || 0}</div>
            <div className="text-xs text-indigo-500">{stats.this_month?.records || 0} records</div>
          </div>
        </div>
      )}

      {/* Results summary */}
      {hasActiveFilters && (
        <div className="mb-4 text-sm text-slate-600 dark:text-slate-400">
          Showing {requests.length} request{requests.length !== 1 ? 's' : ''} with current filters
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">Loading requests...</div>
      ) : (
        <div className="space-y-8">
          {pendingRequests.length > 0 && (
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <h3 className="text-xl font-semibold text-slate-900 dark:text-white flex items-center gap-2">
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