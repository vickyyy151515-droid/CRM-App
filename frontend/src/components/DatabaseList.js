import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Search, Eye, Trash2, FileSpreadsheet, Users, AlertTriangle, X } from 'lucide-react';
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

  useEffect(() => {
    loadProducts();
  }, []);

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

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
          {isStaff ? 'Available Databases' : 'Manage Databases'}
        </h2>
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
                      onClick={() => handleDelete(db.id)}
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
    </div>
  );
}