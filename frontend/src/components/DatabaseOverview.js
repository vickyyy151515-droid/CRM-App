import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Search, FileSpreadsheet, RefreshCw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function DatabaseOverview() {
  const { t } = useLanguage();
  const [databases, setDatabases] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');

  const loadProducts = useCallback(async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  }, []);

  const loadDatabases = useCallback(async (showRefresh = false) => {
    try {
      if (showRefresh) setRefreshing(true);
      
      const params = {};
      if (search) params.search = search;
      if (selectedProduct) params.product_id = selectedProduct;
      
      const response = await api.get('/databases/with-stats', { params });
      setDatabases(response.data);
    } catch (error) {
      toast.error('Failed to load databases');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [search, selectedProduct]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  useEffect(() => {
    loadDatabases();
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => loadDatabases(false), 30000);
    return () => clearInterval(interval);
  }, [loadDatabases]);

  const handleRefresh = () => {
    loadDatabases(true);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
          {t('database.overview')}
        </h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          data-testid="refresh-databases-btn"
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          {t('common.refresh')}
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('database.searchDatabases')}
            data-testid="search-overview-input"
            className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 pl-10 pr-3 py-2 text-sm text-slate-900 dark:text-slate-100 ring-offset-white placeholder:text-slate-500 dark:placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          />
        </div>
        <div>
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            data-testid="filter-overview-product"
            className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            <option value="">{t('database.allProducts')}</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">{t('common.loading')}</div>
      ) : databases.length === 0 ? (
        <div className="text-center py-12">
          <FileSpreadsheet className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">{t('database.noDatabases')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4" data-testid="database-overview-list">
          {databases.map((db) => (
            <DatabaseCard key={db.id} database={db} t={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function DatabaseCard({ database, t }) {
  const db = database;
  
  return (
    <div
      className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm hover:shadow-md transition-all"
      data-testid={`database-overview-${db.id}`}
    >
      {/* Header - Filename and Product Badge */}
      <div className="flex items-center gap-3 mb-4">
        <FileSpreadsheet className="text-indigo-600 dark:text-indigo-400 flex-shrink-0" size={20} />
        <h3 className="text-base font-semibold text-slate-900 dark:text-white truncate" data-testid="database-overview-filename">
          {db.filename}
        </h3>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800 flex-shrink-0">
          {db.product_name}
        </span>
      </div>

      {/* Stats Cards - Matching the image layout */}
      <div className="grid grid-cols-5 gap-3">
        {/* Total Records */}
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 border border-slate-100 dark:border-slate-700">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">{t('database.totalRecords')}</p>
          <p className="text-xl font-bold text-slate-900 dark:text-white" data-testid="stat-total">
            {db.total_records}
          </p>
        </div>

        {/* Available - Green */}
        <div className="bg-emerald-50 dark:bg-emerald-900/30 rounded-lg p-3 border border-emerald-100 dark:border-emerald-800">
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">{t('database.availableCount')}</p>
          <p className="text-xl font-bold text-emerald-700 dark:text-emerald-400" data-testid="stat-available">
            {db.available_count}
          </p>
        </div>

        {/* Excluded - Red/Pink */}
        <div className="bg-rose-50 dark:bg-rose-900/30 rounded-lg p-3 border border-rose-100 dark:border-rose-800">
          <p className="text-xs text-rose-600 dark:text-rose-400 mb-1">Excluded</p>
          <p className="text-xl font-bold text-rose-700 dark:text-rose-400" data-testid="stat-excluded">
            {db.excluded_count || 0}
          </p>
        </div>

        {/* Requested - Yellow/Orange */}
        <div className="bg-amber-50 dark:bg-amber-900/30 rounded-lg p-3 border border-amber-100 dark:border-amber-800">
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">{t('database.requestedCount')}</p>
          <p className="text-xl font-bold text-amber-700 dark:text-amber-400" data-testid="stat-requested">
            {db.requested_count}
          </p>
        </div>

        {/* Assigned - Purple */}
        <div className="bg-violet-50 dark:bg-violet-900/30 rounded-lg p-3 border border-violet-100 dark:border-violet-800">
          <p className="text-xs text-violet-600 dark:text-violet-400 mb-1">{t('database.assignedCount')}</p>
          <p className="text-xl font-bold text-violet-700 dark:text-violet-400" data-testid="stat-assigned">
            {db.assigned_count}
          </p>
        </div>
      </div>
    </div>
  );
}
