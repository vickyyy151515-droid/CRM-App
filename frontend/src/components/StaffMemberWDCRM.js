import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Gift, FileSpreadsheet, Calendar, Package } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function StaffMemberWDCRM() {
  const { t } = useLanguage();
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterProduct, setFilterProduct] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    loadRecords();
  }, [filterProduct]);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products');
    }
  };

  const loadRecords = async () => {
    try {
      const params = filterProduct ? `?product_id=${filterProduct}` : '';
      const response = await api.get(`/memberwd/staff/records${params}`);
      setRecords(response.data);
    } catch (error) {
      toast.error(t('messages.loadFailed'));
    } finally {
      setLoading(false);
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

  // Group records by database
  const groupedRecords = records.reduce((acc, record) => {
    const dbName = record.database_name;
    if (!acc[dbName]) {
      acc[dbName] = [];
    }
    acc[dbName].push(record);
    return acc;
  }, {});

  // Filter records
  const filteredGroupedRecords = Object.entries(groupedRecords).reduce((acc, [dbName, dbRecords]) => {
    const filtered = dbRecords.filter(record => 
      searchTerm === '' || 
      Object.values(record.row_data).some(val => 
        String(val).toLowerCase().includes(searchTerm.toLowerCase())
      )
    );
    if (filtered.length > 0) {
      acc[dbName] = filtered;
    }
    return acc;
  }, {});

  const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];
  
  // Filter out sensitive columns for staff users (rekening/bank account info)
  const HIDDEN_COLUMNS_FOR_STAFF = ['rekening', 'rek', 'bank', 'no_rekening', 'norek', 'account'];
  const visibleColumns = columns.filter(col => 
    !HIDDEN_COLUMNS_FOR_STAFF.some(hidden => col.toLowerCase().includes(hidden.toLowerCase()))
  );

  return (
    <div data-testid="staff-db-memberwd">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">{t('dbRecords.memberWdTitle')}</h2>

      {/* Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <input
          type="text"
          placeholder={t('dbRecords.searchRecords')}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 max-w-md h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          data-testid="memberwd-search"
        />
        <div className="flex items-center gap-2">
          <Package size={18} className="text-slate-500 dark:text-slate-400" />
          <select
            value={filterProduct}
            onChange={(e) => setFilterProduct(e.target.value)}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[180px]"
            data-testid="memberwd-filter-product"
          >
            <option value="">{t('dbRecords.allProducts')}</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">{t('dbRecords.loadingRecords')}</div>
      ) : records.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <Gift className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">{t('dbRecords.noMemberWdYet')}</p>
          <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">{t('dbRecords.adminWillAssign')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(filteredGroupedRecords).map(([dbName, dbRecords]) => (
            <div key={dbName} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                      <FileSpreadsheet className="text-indigo-600 dark:text-indigo-400" size={20} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white">{dbName}</h3>
                      <div className="flex items-center gap-2">
                        <p className="text-sm text-slate-500 dark:text-slate-400">{dbRecords.length} {t('dbRecords.recordsAssigned')}</p>
                        {dbRecords[0]?.product_name && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300">
                            <Package size={10} className="mr-1" />
                            {dbRecords[0].product_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400">
                    <Calendar size={14} />
                    {t('dbRecords.assigned')}: {formatDate(dbRecords[0]?.assigned_at)}
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-50 dark:bg-slate-900/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">#</th>
                      {visibleColumns.map(col => (
                        <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dbRecords.map(record => (
                      <tr key={record.id} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50">
                        <td className="px-4 py-3 text-sm text-slate-900 dark:text-white font-medium">{record.row_number}</td>
                        {visibleColumns.map(col => (
                          <td key={col} className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">{record.row_data[col] || '-'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
