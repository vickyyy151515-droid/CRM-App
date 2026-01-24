import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Search, Eye, Trash2, FileSpreadsheet, Users, AlertTriangle, X, Wrench, CheckCircle, RefreshCw, Zap, Settings } from 'lucide-react';
import DatabasePreview from './DatabasePreview';
import DatabaseRecords from './DatabaseRecords';

export default function DatabaseList({ onUpdate, isStaff = false }) {
  const [databases, setDatabases] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedDb, setSelectedDb] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showRecords, setShowRecords] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null); // For custom confirm modal
  const [fixingData, setFixingData] = useState(false);
  const [showFixModal, setShowFixModal] = useState(false);
  const [fixCheckResult, setFixCheckResult] = useState(null);
  
  // Recovery modal state
  const [showRecoveryModal, setShowRecoveryModal] = useState(false);
  const [recoveryCheckResult, setRecoveryCheckResult] = useState(null);
  const [recovering, setRecovering] = useState(false);
  
  // Auto-approve settings state
  const [autoApproveEnabled, setAutoApproveEnabled] = useState(false);
  const [autoApproveLoading, setAutoApproveLoading] = useState(false);
  const [showAutoApproveSettings, setShowAutoApproveSettings] = useState(false);
  const [maxRecordsLimit, setMaxRecordsLimit] = useState('');

  useEffect(() => {
    loadProducts();
    if (!isStaff) {
      loadAutoApproveSettings();
    }
  }, [isStaff]);

  useEffect(() => {
    loadDatabases();
  }, [search, selectedProduct]);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      toast.error('Failed to load products');
    }
  };

  const loadDatabases = async (retryCount = 0) => {
    try {
      const params = {};
      if (search) params.search = search;
      if (selectedProduct) params.product_id = selectedProduct;
      
      const response = await api.get('/databases', { params, timeout: 15000 });
      setDatabases(response.data);
    } catch (error) {
      console.error('Error loading databases:', error);
      // Retry once on network error
      if (retryCount < 1 && (error.code === 'ECONNABORTED' || error.message?.includes('Network') || !error.response)) {
        console.log('Retrying database load...');
        setTimeout(() => loadDatabases(retryCount + 1), 1000);
        return;
      }
      toast.error(error.response?.data?.detail || 'Failed to load databases. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/databases/${id}`);
      toast.success('Database deleted successfully');
      setDeleteConfirm(null);
      loadDatabases();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete database');
    }
  };

  const handleRequestDownload = async (database) => {
    try {
      const response = await api.get(`/databases/${database.id}/records`);
      setSelectedDb({...database, records: response.data});
      setShowRecords(true);
    } catch (error) {
      toast.error('Failed to load records');
    }
  };

  const handlePreview = async (database) => {
    try {
      const response = await api.get(`/databases/${database.id}`);
      setSelectedDb(response.data);
      setShowPreview(true);
    } catch (error) {
      toast.error('Failed to load preview');
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

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const checkFixStatus = async () => {
    try {
      setFixingData(true);
      const response = await api.get('/records/fix-requested-status');
      setFixCheckResult(response.data);
      setShowFixModal(true);
    } catch (error) {
      toast.error('Failed to check data status');
    } finally {
      setFixingData(false);
    }
  };

  const runDataFix = async () => {
    try {
      setFixingData(true);
      const response = await api.post('/records/fix-requested-status');
      toast.success(`Fixed ${response.data.total_processed} records: ${response.data.fixed_to_assigned} assigned, ${response.data.fixed_to_available} returned to available`);
      setShowFixModal(false);
      setFixCheckResult(null);
      loadDatabases();
      onUpdate?.();
    } catch (error) {
      toast.error('Failed to fix data');
    } finally {
      setFixingData(false);
    }
  };

  // Recovery functions for wrongly available records
  const checkRecoveryNeeded = async () => {
    try {
      setRecovering(true);
      const response = await api.get('/records/recover-approved-requests');
      setRecoveryCheckResult(response.data);
      setShowRecoveryModal(true);
    } catch (error) {
      toast.error('Failed to check recovery status');
    } finally {
      setRecovering(false);
    }
  };

  const runRecovery = async () => {
    try {
      setRecovering(true);
      const response = await api.post('/records/recover-approved-requests');
      if (response.data.total_recovered > 0) {
        toast.success(`Recovered ${response.data.total_recovered} records for ${response.data.requests_processed} staff members`);
      } else {
        toast.info('No records needed recovery');
      }
      setShowRecoveryModal(false);
      setRecoveryCheckResult(null);
      loadDatabases();
      onUpdate?.();
    } catch (error) {
      toast.error('Failed to recover records');
    } finally {
      setRecovering(false);
    }
  };

  // Auto-approve functions
  const loadAutoApproveSettings = async () => {
    try {
      const response = await api.get('/settings/auto-approve');
      setAutoApproveEnabled(response.data.enabled);
      setMaxRecordsLimit(response.data.max_records_per_request?.toString() || '');
    } catch (error) {
      console.error('Failed to load auto-approve settings');
    }
  };

  const toggleAutoApprove = async () => {
    try {
      setAutoApproveLoading(true);
      const newValue = !autoApproveEnabled;
      await api.put('/settings/auto-approve', {
        enabled: newValue,
        max_records_per_request: maxRecordsLimit ? parseInt(maxRecordsLimit) : null
      });
      setAutoApproveEnabled(newValue);
      toast.success(`Auto-approve ${newValue ? 'enabled' : 'disabled'}`);
    } catch (error) {
      toast.error('Failed to update auto-approve setting');
    } finally {
      setAutoApproveLoading(false);
    }
  };

  const saveAutoApproveSettings = async () => {
    try {
      setAutoApproveLoading(true);
      await api.put('/settings/auto-approve', {
        enabled: autoApproveEnabled,
        max_records_per_request: maxRecordsLimit ? parseInt(maxRecordsLimit) : null
      });
      toast.success('Auto-approve settings saved');
      setShowAutoApproveSettings(false);
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setAutoApproveLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
          {isStaff ? 'Available Databases' : 'Manage Databases'}
        </h2>
        {!isStaff && (
          <div className="flex items-center gap-2">
            <button
              onClick={checkRecoveryNeeded}
              disabled={recovering}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded-lg hover:bg-emerald-200 dark:hover:bg-emerald-900/50 transition-colors text-sm font-medium disabled:opacity-50"
              data-testid="recover-data-btn"
            >
              <RefreshCw size={16} className={recovering ? 'animate-spin' : ''} />
              {recovering ? 'Checking...' : 'Recover Staff Records'}
            </button>
            <button
              onClick={checkFixStatus}
              disabled={fixingData}
              className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors text-sm font-medium disabled:opacity-50"
              data-testid="fix-data-btn"
            >
              <Wrench size={16} />
              {fixingData ? 'Checking...' : 'Fix Stuck Records'}
            </button>
          </div>
        )}
      </div>

      <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search databases..."
            data-testid="search-databases-input"
            className="flex h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          />
        </div>
        <div>
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            data-testid="filter-product-select"
            className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            <option value="">All Products</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading databases...</div>
      ) : databases.length === 0 ? (
        <div className="text-center py-12">
          <FileSpreadsheet className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600">No databases found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4" data-testid="database-list">
          {databases.map((db) => (
            <div
              key={db.id}
              className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-all"
              data-testid={`database-item-${db.id}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <FileSpreadsheet className="text-indigo-600" size={20} />
                    <h3 className="text-lg font-semibold text-slate-900" data-testid="database-filename">{db.filename}</h3>
                    <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-slate-100 text-slate-700">
                      {db.file_type.toUpperCase()}
                    </span>
                    <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200">
                      {db.product_name}
                    </span>
                  </div>
                  {db.description && (
                    <p className="text-sm text-slate-600 mb-3">{db.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-slate-500 mb-2">
                    <span>Size: {formatFileSize(db.file_size)}</span>
                    <span>•</span>
                    <span>Uploaded by {db.uploaded_by_name}</span>
                    <span>•</span>
                    <span>{formatDate(db.uploaded_at)}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Users className="text-indigo-600" size={16} />
                    <span className="font-medium text-slate-900">{db.total_records || 0} customer records</span>
                  </div>
                </div>

                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handlePreview(db)}
                    data-testid={`preview-database-${db.id}`}
                    className="text-slate-600 hover:bg-slate-100 hover:text-slate-900 px-4 py-2 rounded-md transition-colors flex items-center gap-2"
                  >
                    <Eye size={16} />
                    Preview
                  </button>
                  {isStaff ? (
                    <button
                      onClick={() => handleRequestDownload(db)}
                      data-testid={`request-download-${db.id}`}
                      className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-4 py-2 rounded-md transition-all active:scale-95 flex items-center gap-2"
                    >
                      <Users size={16} />
                      View Records
                    </button>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirm(db)}
                      data-testid={`delete-database-${db.id}`}
                      className="text-rose-600 hover:bg-rose-50 px-4 py-2 rounded-md transition-colors flex items-center gap-2"
                    >
                      <Trash2 size={16} />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showPreview && selectedDb && (
        <DatabasePreview
          database={selectedDb}
          onClose={() => {
            setShowPreview(false);
            setSelectedDb(null);
          }}
        />
      )}

      {showRecords && selectedDb && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="records-modal">
          <div className="bg-white rounded-xl shadow-2xl max-w-7xl w-full max-h-[85vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-slate-200">
              <div>
                <h3 className="text-2xl font-semibold text-slate-900">{selectedDb.filename}</h3>
                <p className="text-sm text-slate-600 mt-1">Enter how many customer records you want to request</p>
              </div>
              <button
                onClick={() => {
                  setShowRecords(false);
                  setSelectedDb(null);
                  loadDatabases();
                  onUpdate?.();
                }}
                data-testid="close-records-button"
                className="text-slate-400 hover:text-slate-600 p-2"
              >
                <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-auto p-6">
              <DatabaseRecords
                database={selectedDb}
                isStaff={isStaff}
                onRequestSuccess={() => {
                  setShowRecords(false);
                  setSelectedDb(null);
                  loadDatabases();
                  onUpdate?.();
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="delete-confirm-modal">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center">
                <AlertTriangle className="text-rose-600 dark:text-rose-400" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Delete Database</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">This action cannot be undone</p>
              </div>
            </div>
            
            <p className="text-slate-600 dark:text-slate-300 mb-2">
              Are you sure you want to delete this database?
            </p>
            <p className="text-sm font-medium text-slate-900 dark:text-white bg-slate-100 dark:bg-slate-700 px-3 py-2 rounded-lg mb-6">
              {deleteConfirm.filename}
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                data-testid="cancel-delete-btn"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm.id)}
                className="px-4 py-2 bg-rose-600 text-white hover:bg-rose-700 rounded-lg transition-colors flex items-center gap-2"
                data-testid="confirm-delete-btn"
              >
                <Trash2 size={16} />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fix Stuck Records Modal */}
      {showFixModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="fix-data-modal">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-lg w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <Wrench className="text-amber-600 dark:text-amber-400" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Fix Stuck Records</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Records stuck in "requested" status</p>
              </div>
            </div>
            
            {fixCheckResult && (
              <div className="mb-6">
                {fixCheckResult.total_requested_records === 0 || fixCheckResult.count === 0 ? (
                  <div className="flex items-center gap-3 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                    <CheckCircle className="text-emerald-600 dark:text-emerald-400" size={24} />
                    <div>
                      <p className="font-medium text-emerald-800 dark:text-emerald-300">All Clear!</p>
                      <p className="text-sm text-emerald-600 dark:text-emerald-400">No records are stuck in "requested" status.</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                      <p className="font-medium text-amber-800 dark:text-amber-300 mb-2">
                        Found {fixCheckResult.total_requested_records} stuck records
                      </p>
                      {fixCheckResult.orphan_records_no_request_id > 0 && (
                        <p className="text-sm text-amber-600 dark:text-amber-400">
                          • {fixCheckResult.orphan_records_no_request_id} orphan records (no request ID)
                        </p>
                      )}
                      {fixCheckResult.related_requests?.length > 0 && (
                        <div className="text-sm text-amber-600 dark:text-amber-400 mt-2">
                          <p className="font-medium">Related requests:</p>
                          {fixCheckResult.related_requests.map((req, i) => (
                            <p key={i}>• {req.requested_by_name}: {req.status}</p>
                          ))}
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Click "Fix Now" to:
                    </p>
                    <ul className="text-sm text-slate-600 dark:text-slate-400 list-disc list-inside space-y-1">
                      <li>Move approved requests → <span className="text-emerald-600 font-medium">Assigned</span></li>
                      <li>Return rejected/orphan → <span className="text-blue-600 font-medium">Available</span></li>
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowFixModal(false);
                  setFixCheckResult(null);
                }}
                className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                Close
              </button>
              {fixCheckResult && (fixCheckResult.total_requested_records > 0 || fixCheckResult.count > 0) && (
                <button
                  onClick={runDataFix}
                  disabled={fixingData}
                  className="px-4 py-2 bg-amber-600 text-white hover:bg-amber-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                  data-testid="confirm-fix-btn"
                >
                  <Wrench size={16} />
                  {fixingData ? 'Fixing...' : 'Fix Now'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Recovery Modal for wrongly available records */}
      {showRecoveryModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="recovery-modal">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <RefreshCw className="text-emerald-600 dark:text-emerald-400" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Recover Staff Records</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Re-assign records from approved requests</p>
              </div>
            </div>
            
            {recoveryCheckResult && (
              <div className="mb-6">
                {recoveryCheckResult.requests_needing_recovery === 0 ? (
                  <div className="flex items-center gap-3 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                    <CheckCircle className="text-emerald-600 dark:text-emerald-400" size={24} />
                    <div>
                      <p className="font-medium text-emerald-800 dark:text-emerald-300">All Clear!</p>
                      <p className="text-sm text-emerald-600 dark:text-emerald-400">
                        All {recoveryCheckResult.total_approved_requests} approved requests have their records properly assigned.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                      <p className="font-medium text-emerald-800 dark:text-emerald-300 mb-2">
                        Found {recoveryCheckResult.requests_needing_recovery} requests needing recovery
                      </p>
                      <p className="text-sm text-emerald-600 dark:text-emerald-400 mb-3">
                        These staff members have approved requests but their records are not properly assigned:
                      </p>
                      <div className="max-h-48 overflow-y-auto space-y-2">
                        {recoveryCheckResult.details.map((detail, i) => (
                          <div key={i} className="text-sm bg-white dark:bg-slate-700 p-2 rounded border border-emerald-100 dark:border-slate-600">
                            <p className="font-medium text-slate-900 dark:text-white">{detail.staff_name}</p>
                            <p className="text-slate-600 dark:text-slate-400">
                              {detail.database_name}: {detail.not_assigned_count}/{detail.total_records} records need recovery
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-500">
                              Current statuses: {detail.sample_statuses.join(', ')}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Click "Recover Now" to re-assign these records to the staff who had their requests approved.
                    </p>
                  </div>
                )}
              </div>
            )}
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowRecoveryModal(false);
                  setRecoveryCheckResult(null);
                }}
                className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                Close
              </button>
              {recoveryCheckResult && recoveryCheckResult.requests_needing_recovery > 0 && (
                <button
                  onClick={runRecovery}
                  disabled={recovering}
                  className="px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                  data-testid="confirm-recover-btn"
                >
                  <RefreshCw size={16} className={recovering ? 'animate-spin' : ''} />
                  {recovering ? 'Recovering...' : 'Recover Now'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}