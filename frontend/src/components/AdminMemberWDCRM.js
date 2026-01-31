import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Upload, Database, Users, Trash2, ChevronDown, ChevronUp, Check, X, Search, Shuffle, Package, Edit2, AlertTriangle, RefreshCw, Archive, Undo2, Settings, Play, RotateCcw } from 'lucide-react';

export default function AdminMemberWDCRM() {
  const [databases, setDatabases] = useState([]);
  const [products, setProducts] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadProductId, setUploadProductId] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [expandedDb, setExpandedDb] = useState(null);
  const [records, setRecords] = useState([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [selectedRecords, setSelectedRecords] = useState([]);
  const [selectedStaff, setSelectedStaff] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterProduct, setFilterProduct] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [randomQuantity, setRandomQuantity] = useState('');
  const [reservedNames, setReservedNames] = useState([]);
  const [editingProduct, setEditingProduct] = useState(null);
  const [newProductId, setNewProductId] = useState('');
  // Invalid records state
  const [invalidRecords, setInvalidRecords] = useState(null);
  const [showInvalidPanel, setShowInvalidPanel] = useState(false);
  const [processing, setProcessing] = useState(false);
  // Replacement modal state
  const [showReplaceModal, setShowReplaceModal] = useState(false);
  const [replaceStaffId, setReplaceStaffId] = useState(null);
  const [replaceStaffName, setReplaceStaffName] = useState('');
  const [replaceInvalidCount, setReplaceInvalidCount] = useState(0);
  const [replaceQuantity, setReplaceQuantity] = useState(0);
  // Archived/Invalid Database state
  const [activeTab, setActiveTab] = useState('databases');
  const [archivedRecords, setArchivedRecords] = useState(null);
  const [loadingArchived, setLoadingArchived] = useState(false);

  useEffect(() => {
    loadProducts();
    loadStaff();
    loadReservedNames();
    loadInvalidRecords();
  }, []);

  useEffect(() => {
    loadDatabases();
  }, [filterProduct]);

  useEffect(() => {
    if (activeTab === 'invalid') {
      loadArchivedRecords();
    }
  }, [activeTab]);

  const loadReservedNames = async () => {
    try {
      const response = await api.get('/reserved-members');
      const names = response.data.map(m => {
        const name = m.customer_name;
        return name ? String(name).toLowerCase().trim() : null;
      }).filter(Boolean);
      setReservedNames(names);
    } catch (error) {
      console.error('Failed to load reserved names');
    }
  };

  // Load invalid records from staff validation
  const loadInvalidRecords = async () => {
    try {
      const response = await api.get('/memberwd/admin/invalid-records');
      setInvalidRecords(response.data);
      // Auto-expand the invalid panel if there are invalid records
      if (response.data.total_invalid > 0) {
        setShowInvalidPanel(true);
      }
    } catch (error) {
      console.error('Failed to load invalid records:', error);
    }
  };

  // Load archived invalid records for "Invalid Database" tab
  const loadArchivedRecords = async () => {
    setLoadingArchived(true);
    try {
      const response = await api.get('/memberwd/admin/archived-invalid');
      setArchivedRecords(response.data);
    } catch (error) {
      console.error('Failed to load archived records:', error);
    } finally {
      setLoadingArchived(false);
    }
  };

  // Open replacement modal
  const openReplaceModal = (staffId, staffName, invalidCount) => {
    setReplaceStaffId(staffId);
    setReplaceStaffName(staffName);
    setReplaceInvalidCount(invalidCount);
    setReplaceQuantity(invalidCount); // Default to same number
    setShowReplaceModal(true);
  };

  // Process invalid records and optionally assign replacements
  const handleProcessInvalid = async () => {
    setProcessing(true);
    try {
      const response = await api.post(`/memberwd/admin/process-invalid/${replaceStaffId}`, {
        auto_assign_quantity: replaceQuantity
      });
      toast.success(response.data.message);
      setShowReplaceModal(false);
      loadInvalidRecords();
      loadDatabases();
      if (activeTab === 'invalid') {
        loadArchivedRecords();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process records');
    } finally {
      setProcessing(false);
    }
  };

  // Restore archived record back to available pool
  const handleRestoreRecord = async (recordId) => {
    if (!window.confirm('Kembalikan record ini ke pool yang tersedia?')) return;
    try {
      await api.post(`/memberwd/admin/archived-invalid/${recordId}/restore`);
      toast.success('Record dikembalikan ke pool');
      loadArchivedRecords();
      loadDatabases();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore record');
    }
  };

  // Permanently delete archived record
  const handleDeleteArchivedRecord = async (recordId) => {
    if (!window.confirm('Hapus record ini secara permanen? Tindakan ini tidak dapat dibatalkan.')) return;
    try {
      await api.delete(`/memberwd/admin/archived-invalid/${recordId}`);
      toast.success('Record dihapus permanen');
      loadArchivedRecords();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete record');
    }
  };

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products');
    }
  };

  const loadDatabases = async () => {
    try {
      const params = filterProduct ? `?product_id=${filterProduct}` : '';
      const response = await api.get(`/memberwd/databases${params}`);
      setDatabases(response.data);
    } catch (error) {
      toast.error('Failed to load databases');
    } finally {
      setLoading(false);
    }
  };

  const loadStaff = async () => {
    try {
      const response = await api.get('/memberwd/staff');
      setStaff(response.data);
    } catch (error) {
      console.error('Failed to load staff');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile || !uploadName.trim() || !uploadProductId) {
      toast.error('Please provide a name, select a product, and select a file');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('name', uploadName);
    formData.append('product_id', uploadProductId);

    try {
      await api.post('/memberwd/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Database uploaded successfully');
      setSelectedFile(null);
      setUploadName('');
      setUploadProductId('');
      loadDatabases();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload database');
    } finally {
      setUploading(false);
    }
  };

  const loadRecords = async (databaseId) => {
    if (expandedDb === databaseId) {
      setExpandedDb(null);
      setRecords([]);
      setSelectedRecords([]);
      return;
    }

    setLoadingRecords(true);
    setExpandedDb(databaseId);
    try {
      const response = await api.get(`/memberwd/databases/${databaseId}/records`);
      setRecords(response.data);
      setSelectedRecords([]);
    } catch (error) {
      toast.error('Failed to load records');
    } finally {
      setLoadingRecords(false);
    }
  };

  const handleDelete = async (databaseId) => {
    if (!window.confirm('Are you sure you want to delete this database and all its records?')) return;

    try {
      await api.delete(`/memberwd/databases/${databaseId}`);
      toast.success('Database deleted');
      loadDatabases();
      if (expandedDb === databaseId) {
        setExpandedDb(null);
        setRecords([]);
      }
    } catch (error) {
      toast.error('Failed to delete database');
    }
  };

  const handleEditProduct = (database) => {
    setEditingProduct(database.id);
    setNewProductId(database.product_id || '');
  };

  const handleSaveProduct = async (databaseId) => {
    if (!newProductId) {
      toast.error('Please select a product');
      return;
    }

    try {
      await api.patch(`/memberwd/databases/${databaseId}/product`, {
        product_id: newProductId
      });
      toast.success('Product updated successfully');
      setEditingProduct(null);
      loadDatabases();
      if (expandedDb === databaseId) {
        const response = await api.get(`/memberwd/databases/${databaseId}/records`);
        setRecords(response.data);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update product');
    }
  };

  const handleBulkDeleteRecords = async () => {
    if (selectedRecords.length === 0) {
      toast.error('Please select records to delete');
      return;
    }
    if (!window.confirm(`Are you sure you want to delete ${selectedRecords.length} records?`)) return;

    try {
      await api.delete('/bulk/memberwd-records', { data: { record_ids: selectedRecords } });
      toast.success(`${selectedRecords.length} records deleted`);
      setSelectedRecords([]);
      loadRecords(expandedDb);
      loadDatabases();
    } catch (error) {
      toast.error('Failed to delete records');
    }
  };

  const toggleSelectRecord = (recordId) => {
    setSelectedRecords(prev => 
      prev.includes(recordId) 
        ? prev.filter(id => id !== recordId)
        : [...prev, recordId]
    );
  };

  const selectAllAvailable = () => {
    const availableIds = filteredRecords
      .filter(r => r.status === 'available')
      .map(r => r.id);
    setSelectedRecords(availableIds);
  };

  const clearSelection = () => {
    setSelectedRecords([]);
  };

  const handleRandomAssign = async () => {
    const quantity = parseInt(randomQuantity);
    if (!selectedStaff || !quantity || quantity <= 0) {
      toast.error('Please select staff and enter a valid quantity');
      return;
    }

    // Get available records
    const availableRecords = records.filter(r => r.status === 'available');
    if (availableRecords.length === 0) {
      toast.error('No available records to assign');
      return;
    }

    if (quantity > availableRecords.length) {
      toast.error(`Only ${availableRecords.length} records available`);
      return;
    }

    // Detect the username field from the first record
    const columns = Object.keys(records[0]?.row_data || {});
    const usernameField = columns.find(col => 
      col.toLowerCase().includes('username') || 
      col.toLowerCase().includes('user') ||
      col.toLowerCase() === 'nama'
    ) || columns[0];

    setAssigning(true);
    try {
      const response = await api.post('/memberwd/assign-random', {
        database_id: expandedDb,
        staff_id: selectedStaff,
        quantity: quantity,
        username_field: usernameField
      });
      
      const data = response.data;
      let message = `${data.assigned_count} records assigned successfully!`;
      if (data.total_reserved_in_db > 0) {
        message += ` (${data.total_reserved_in_db} names in Reserved Members were automatically excluded)`;
      }
      toast.success(message);
      
      setRandomQuantity('');
      setSelectedStaff('');
      loadRecords(expandedDb);
      loadDatabases();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign records');
    } finally {
      setAssigning(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedStaff || selectedRecords.length === 0) {
      toast.error('Please select staff and records to assign');
      return;
    }

    setAssigning(true);
    try {
      await api.post('/memberwd/assign', {
        record_ids: selectedRecords,
        staff_id: selectedStaff
      });
      toast.success('Records assigned successfully');
      setSelectedRecords([]);
      setSelectedStaff('');
      loadRecords(expandedDb);
      loadDatabases();
    } catch (error) {
      toast.error('Failed to assign records');
    } finally {
      setAssigning(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Filter records
  const filteredRecords = records.filter(record => {
    const matchesStatus = filterStatus === 'all' || record.status === filterStatus;
    const matchesSearch = searchTerm === '' || 
      Object.values(record.row_data).some(val => 
        String(val).toLowerCase().includes(searchTerm.toLowerCase())
      );
    return matchesStatus && matchesSearch;
  });

  const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];
  
  // Filter out rekening/bank account columns (no longer needed)
  // EXCEPTION: 'nama_rekening' or 'nama rekening' is allowed because it's the customer's full name
  const HIDDEN_COLUMNS = ['rekening', 'rek', 'bank', 'no_rekening', 'norek', 'account'];
  const ALLOWED_COLUMNS = ['nama_rekening', 'nama rekening']; // Customer full name - allowed
  const visibleColumns = columns.filter(col => {
    const colLower = col.toLowerCase();
    // Allow if it's in the allowed list
    if (ALLOWED_COLUMNS.some(allowed => colLower === allowed.toLowerCase())) {
      return true;
    }
    // Otherwise filter out hidden columns
    return !HIDDEN_COLUMNS.some(hidden => colLower.includes(hidden.toLowerCase()));
  });

  return (
    <div data-testid="admin-db-memberwd">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">Member WD CRM</h2>

      {/* Invalid Records Alert Banner */}
      {invalidRecords && invalidRecords.total_invalid > 0 && (
        <div className="mb-6 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl overflow-hidden" data-testid="invalid-records-alert">
          <button
            onClick={() => setShowInvalidPanel(!showInvalidPanel)}
            className="w-full p-4 flex items-center justify-between hover:bg-red-100/50 dark:hover:bg-red-900/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
                <AlertTriangle className="text-red-600 dark:text-red-400" size={20} />
              </div>
              <div className="text-left">
                <h4 className="font-semibold text-red-800 dark:text-red-300">
                  {invalidRecords.total_invalid} Record Tidak Valid
                </h4>
                <p className="text-sm text-red-600 dark:text-red-400">
                  Staff telah menandai record ini sebagai tidak valid. Klik untuk detail dan tindakan.
                </p>
              </div>
            </div>
            {showInvalidPanel ? <ChevronUp className="text-red-600 dark:text-red-400" /> : <ChevronDown className="text-red-600 dark:text-red-400" />}
          </button>
          
          {showInvalidPanel && (
            <div className="border-t border-red-200 dark:border-red-800 p-4 space-y-4">
              {invalidRecords.by_staff?.map((staffGroup) => (
                <div key={staffGroup._id} className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                  <div className="p-3 bg-slate-50 dark:bg-slate-900/50 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-900 dark:text-white">{staffGroup.staff_name || 'Unknown Staff'}</span>
                      <span className="ml-2 px-2 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
                        {staffGroup.count} record tidak valid
                      </span>
                    </div>
                    <button
                      onClick={() => openReplaceModal(staffGroup._id, staffGroup.staff_name, staffGroup.count)}
                      disabled={processing}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                      data-testid={`replace-invalid-${staffGroup._id}`}
                    >
                      <RefreshCw size={14} />
                      Ganti dengan Record Baru
                    </button>
                  </div>
                  <div className="max-h-48 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700">
                    {staffGroup.records?.slice(0, 5).map((record, idx) => (
                      <div key={record.id || idx} className="p-3 text-sm">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <span className="font-medium text-slate-900 dark:text-white">
                              {Object.values(record.row_data || {}).slice(0, 2).join(' - ')}
                            </span>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                              Database: {record.database_name}
                            </p>
                          </div>
                          <span className="text-xs text-red-600 dark:text-red-400 italic">
                            {record.validation_reason || 'No reason'}
                          </span>
                        </div>
                      </div>
                    ))}
                    {staffGroup.records?.length > 5 && (
                      <div className="p-2 text-center text-xs text-slate-500 dark:text-slate-400">
                        +{staffGroup.records.length - 5} more records
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Replacement Modal */}
      {showReplaceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowReplaceModal(false)}>
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
              Ganti Record untuk {replaceStaffName}
            </h3>
            <div className="space-y-4">
              <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  <strong>{replaceInvalidCount}</strong> record tidak valid akan dipindahkan ke &quot;Database Invalid&quot;
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Berapa record baru yang ingin ditugaskan?
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={replaceQuantity}
                  onChange={(e) => setReplaceQuantity(parseInt(e.target.value) || 0)}
                  className="w-full h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Masukkan 0 jika tidak ingin menugaskan record baru
                </p>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowReplaceModal(false)}
                className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                Batal
              </button>
              <button
                onClick={handleProcessInvalid}
                disabled={processing}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {processing ? 'Memproses...' : 'Proses'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="mb-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('databases')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === 'databases'
                ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-b-0 border-slate-200 dark:border-slate-700'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
            data-testid="tab-databases"
          >
            <Database size={16} className="inline mr-2" />
            Databases
          </button>
          <button
            onClick={() => setActiveTab('invalid')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
              activeTab === 'invalid'
                ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-b-0 border-slate-200 dark:border-slate-700'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
            data-testid="tab-invalid"
          >
            <Archive size={16} />
            Database Invalid
            {archivedRecords?.total > 0 && (
              <span className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
                {archivedRecords.total}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Databases Tab Content */}
      {activeTab === 'databases' && (
        <>
          {/* Upload Section */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm mb-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Upload size={20} className="text-indigo-600" />
              Upload New Database
            </h3>
            <form onSubmit={handleUpload} className="flex flex-col md:flex-row gap-4">
              <input
                type="text"
                placeholder="Database name..."
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                className="flex-1 h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                data-testid="memberwd-db-name"
              />
              <select
                value={uploadProductId}
                onChange={(e) => setUploadProductId(e.target.value)}
                className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[180px]"
                data-testid="memberwd-product-select"
              >
                <option value="">Select Product...</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            className="flex-1 h-10 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm file:mr-4 file:py-1 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            data-testid="memberwd-file-input"
          />
          <button
            type="submit"
            disabled={uploading}
            className="h-10 px-6 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            data-testid="memberwd-upload-btn"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
      </div>

      {/* Filter by Product */}
      <div className="mb-6 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Package size={18} className="text-slate-500" />
          <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Filter by Product:</span>
        </div>
        <select
          value={filterProduct}
          onChange={(e) => setFilterProduct(e.target.value)}
          className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[200px]"
          data-testid="memberwd-filter-product"
        >
          <option value="">All Products</option>
          {products.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Databases List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12 text-slate-600 dark:text-slate-400">Loading databases...</div>
        ) : databases.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
            <Database className="mx-auto text-slate-300 mb-4" size={48} />
            <p className="text-slate-600 dark:text-slate-400">No databases uploaded yet</p>
          </div>
        ) : (
          databases.map(database => (
            <div key={database.id} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
              {/* Database Header */}
              <div 
                className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700"
                onClick={() => loadRecords(database.id)}
                data-testid={`memberwd-db-${database.id}`}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0">
                    <Database className="text-indigo-600" size={24} />
                  </div>
                  <div className="min-w-0">
                    <h4 className="font-semibold text-slate-900 dark:text-white truncate">{database.name}</h4>
                    <p className="text-sm text-slate-500 truncate">{database.filename}</p>
                    {editingProduct === database.id ? (
                      <div className="flex items-center gap-2 mt-1" onClick={(e) => e.stopPropagation()}>
                        <select
                          value={newProductId}
                          onChange={(e) => setNewProductId(e.target.value)}
                          className="h-7 px-2 rounded border border-purple-300 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
                        >
                          <option value="">Select...</option>
                          {products.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => handleSaveProduct(database.id)}
                          className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                        >
                          <Check size={14} />
                        </button>
                        <button
                          onClick={() => setEditingProduct(null)}
                          className="p-1 text-slate-400 hover:bg-slate-100 rounded"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                          <Package size={12} className="mr-1" />
                          {database.product_name || 'Unknown'}
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleEditProduct(database); }}
                          className="p-1 text-slate-400 hover:text-purple-600 hover:bg-purple-50 rounded"
                          title="Edit product"
                        >
                          <Edit2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 sm:gap-6">
                  <div className="text-right">
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      <span className="font-semibold text-slate-900 dark:text-white">{database.total_records}</span> total
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      <span className="text-emerald-600 font-medium">{database.available_count}</span> available • 
                      <span className="text-blue-600 font-medium ml-1">{database.assigned_count}</span> assigned
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(database.id); }}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    data-testid={`delete-memberwd-${database.id}`}
                  >
                    <Trash2 size={18} />
                  </button>
                  {expandedDb === database.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
              </div>

              {/* Expanded Records */}
              {expandedDb === database.id && (
                <div className="border-t border-slate-200 p-4">
                  {/* Random Assignment Controls */}
                  {(() => {
                    const columns = records.length > 0 ? Object.keys(records[0]?.row_data || {}) : [];
                    const usernameField = columns.find(col => 
                      col.toLowerCase().includes('username') || 
                      col.toLowerCase().includes('user') ||
                      col.toLowerCase() === 'nama'
                    ) || columns[0];
                    
                    const availableRecords = records.filter(r => r.status === 'available');
                    const eligibleRecords = availableRecords.filter(r => {
                      const username = r.row_data?.[usernameField];
                      if (!username) return true;
                      const usernameStr = String(username).toLowerCase().trim();
                      return !reservedNames.includes(usernameStr);
                    });
                    const reservedInDb = availableRecords.length - eligibleRecords.length;
                    
                    return (
                      <div className="mb-4 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg">
                        <h4 className="text-sm font-semibold text-purple-800 mb-3 flex items-center gap-2">
                          <Shuffle size={16} />
                          Quick Random Assignment
                        </h4>
                        <div className="flex flex-wrap items-center gap-3">
                          <select
                            value={selectedStaff}
                            onChange={(e) => setSelectedStaff(e.target.value)}
                            className="h-9 px-3 rounded-lg border border-purple-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                            data-testid="select-staff-random"
                          >
                            <option value="">Select Staff...</option>
                            {staff.map(s => (
                              <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                          </select>
                          <input
                            type="number"
                            placeholder="Qty"
                            value={randomQuantity}
                            onChange={(e) => setRandomQuantity(e.target.value)}
                            min="1"
                            max={eligibleRecords.length}
                            className="h-9 w-20 px-3 rounded-lg border border-purple-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                            data-testid="random-quantity-input"
                          />
                          <div className="text-sm">
                            <span className="text-purple-600 font-medium">{eligibleRecords.length}</span>
                            <span className="text-purple-500"> eligible</span>
                            {reservedInDb > 0 && (
                              <span className="text-amber-600 ml-1">
                                ({reservedInDb} excluded - in Reserved Members)
                              </span>
                            )}
                          </div>
                          <button
                            onClick={handleRandomAssign}
                            disabled={assigning || !selectedStaff || !randomQuantity}
                            className="h-9 px-4 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-2"
                            data-testid="random-assign-btn"
                          >
                            <Shuffle size={14} />
                            {assigning ? 'Assigning...' : 'Assign Random'}
                          </button>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Manual Assignment Controls */}
                  <div className="flex flex-wrap items-center gap-4 mb-4 p-4 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Users size={18} className="text-slate-500" />
                      <span className="text-sm text-slate-600 font-medium">Manual Selection:</span>
                    </div>
                    <button
                      onClick={selectAllAvailable}
                      className="h-9 px-4 text-sm font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                    >
                      Select All Available
                    </button>
                    <button
                      onClick={clearSelection}
                      className="h-9 px-4 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                    >
                      Clear Selection
                    </button>
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      <span className="font-semibold text-indigo-600">{selectedRecords.length}</span> selected
                    </span>
                    <button
                      onClick={handleAssign}
                      disabled={assigning || selectedRecords.length === 0 || !selectedStaff}
                      className="h-9 px-4 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors"
                      data-testid="assign-records-btn"
                    >
                      {assigning ? 'Assigning...' : 'Assign Selected'}
                    </button>
                    <button
                      onClick={handleBulkDeleteRecords}
                      disabled={selectedRecords.length === 0}
                      className="h-9 px-4 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-1"
                      data-testid="bulk-delete-records-btn"
                    >
                      <Trash2 size={14} />
                      Delete Selected
                    </button>
                  </div>

                  {/* Filters */}
                  <div className="flex flex-wrap items-center gap-4 mb-4">
                    <div className="relative flex-1 min-w-[200px] max-w-xs">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                      <input
                        type="text"
                        placeholder="Search records..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full h-9 pl-9 pr-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <select
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value)}
                      className="h-9 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="all">All Status</option>
                      <option value="available">Available</option>
                      <option value="assigned">Assigned</option>
                    </select>
                  </div>

                  {/* Records Table */}
                  {loadingRecords ? (
                    <div className="text-center py-8 text-slate-600 dark:text-slate-400">Loading records...</div>
                  ) : (
                    <div className="overflow-x-auto max-h-96 overflow-y-auto">
                      <table className="min-w-full border border-slate-200 rounded-lg">
                        <thead className="bg-slate-50 dark:bg-slate-900 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700 w-10">
                              <input
                                type="checkbox"
                                onChange={(e) => e.target.checked ? selectAllAvailable() : clearSelection()}
                                checked={selectedRecords.length > 0 && selectedRecords.length === filteredRecords.filter(r => r.status === 'available').length}
                                className="rounded border-slate-300"
                              />
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">#</th>
                            {visibleColumns.map(col => (
                              <th key={col} className="px-3 py-2 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{col}</th>
                            ))}
                            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">Status</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">Assigned To</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredRecords.map(record => (
                            <tr 
                              key={record.id} 
                              className={`border-b border-slate-100 hover:bg-slate-50 dark:hover:bg-slate-700 ${selectedRecords.includes(record.id) ? 'bg-indigo-50' : ''}`}
                            >
                              <td className="px-3 py-2">
                                {record.status === 'available' && (
                                  <input
                                    type="checkbox"
                                    checked={selectedRecords.includes(record.id)}
                                    onChange={() => toggleSelectRecord(record.id)}
                                    className="rounded border-slate-300"
                                  />
                                )}
                              </td>
                              <td className="px-3 py-2 text-sm text-slate-900 font-medium">{record.row_number}</td>
                              {visibleColumns.map(col => (
                                <td key={col} className="px-3 py-2 text-sm text-slate-700 dark:text-slate-200">{record.row_data[col] || '-'}</td>
                              ))}
                              <td className="px-3 py-2">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                  record.status === 'available' 
                                    ? 'bg-emerald-100 text-emerald-800' 
                                    : 'bg-blue-100 text-blue-800'
                                }`}>
                                  {record.status === 'available' ? 'Available' : 'Assigned'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-sm text-slate-600 dark:text-slate-400">
                                {record.assigned_to_name || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
        </>
      )}

      {/* Invalid Database Tab Content */}
      {activeTab === 'invalid' && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <Archive className="text-red-600 dark:text-red-400" size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Database Invalid</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Record yang ditandai tidak valid oleh staff dan telah diarsipkan
                  </p>
                </div>
              </div>
              <button
                onClick={loadArchivedRecords}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw size={18} className="text-slate-500 dark:text-slate-400" />
              </button>
            </div>
          </div>
          
          {loadingArchived ? (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400">
              Loading archived records...
            </div>
          ) : !archivedRecords || archivedRecords.total === 0 ? (
            <div className="p-12 text-center">
              <Archive size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
              <h4 className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-1">Tidak ada record invalid</h4>
              <p className="text-sm text-slate-400 dark:text-slate-500">
                Record invalid akan muncul di sini setelah diproses dari staff
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-200 dark:divide-slate-700">
              {archivedRecords.by_database?.map((dbGroup) => (
                <div key={dbGroup.database_id} className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Database size={16} className="text-slate-400" />
                      <span className="font-medium text-slate-900 dark:text-white">{dbGroup.database_name}</span>
                      <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs rounded">
                        {dbGroup.product_name}
                      </span>
                      <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
                        {dbGroup.count} records
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {dbGroup.records?.slice(0, 10).map((record) => (
                      <div
                        key={record.id}
                        className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-slate-900 dark:text-white text-sm">
                              {Object.values(record.row_data || {}).slice(0, 2).join(' - ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                            <span>Staff: {record.assigned_to_name || '-'}</span>
                            <span>Alasan: <span className="text-red-600 dark:text-red-400">{record.validation_reason || '-'}</span></span>
                            {record.archived_at && (
                              <span>Diarsipkan: {new Date(record.archived_at).toLocaleDateString('id-ID')}</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleRestoreRecord(record.id)}
                            className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors text-amber-600 dark:text-amber-400"
                            title="Kembalikan ke Pool"
                          >
                            <Undo2 size={16} />
                          </button>
                          <button
                            onClick={() => handleDeleteArchivedRecord(record.id)}
                            className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors text-red-600 dark:text-red-400"
                            title="Hapus Permanen"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                    {dbGroup.records?.length > 10 && (
                      <div className="text-center py-2 text-xs text-slate-500 dark:text-slate-400">
                        +{dbGroup.records.length - 10} more records
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
