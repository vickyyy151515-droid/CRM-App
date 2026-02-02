import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Gift, FileSpreadsheet, Calendar, Package, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function StaffDBBonanza() {
  const { t } = useLanguage();
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterProduct, setFilterProduct] = useState('');
  const [selectedRecords, setSelectedRecords] = useState([]);
  const [showInvalidModal, setShowInvalidModal] = useState(false);
  const [invalidReason, setInvalidReason] = useState('');
  const [processing, setProcessing] = useState(false);

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
      const response = await api.get(`/bonanza/staff/records${params}`);
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

  // Toggle record selection
  const toggleRecordSelection = (recordId) => {
    setSelectedRecords(prev => 
      prev.includes(recordId) 
        ? prev.filter(id => id !== recordId)
        : [...prev, recordId]
    );
  };

  // Select all records in a database
  const selectAllInDatabase = (dbRecords) => {
    const unvalidatedRecords = dbRecords.filter(r => !r.validation_status);
    const recordIds = unvalidatedRecords.map(r => r.id);
    const allSelected = recordIds.every(id => selectedRecords.includes(id));
    
    if (allSelected) {
      setSelectedRecords(prev => prev.filter(id => !recordIds.includes(id)));
    } else {
      setSelectedRecords(prev => [...new Set([...prev, ...recordIds])]);
    }
  };

  // Mark records as valid
  const handleMarkValid = async () => {
    if (selectedRecords.length === 0) {
      toast.warning('Pilih record terlebih dahulu');
      return;
    }
    
    setProcessing(true);
    try {
      await api.post('/bonanza/staff/validate', {
        record_ids: selectedRecords,
        is_valid: true
      });
      toast.success(`${selectedRecords.length} record ditandai valid`);
      setSelectedRecords([]);
      loadRecords();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal memvalidasi');
    } finally {
      setProcessing(false);
    }
  };

  // Mark records as invalid
  const handleMarkInvalid = async () => {
    if (selectedRecords.length === 0) {
      toast.warning('Pilih record terlebih dahulu');
      return;
    }
    
    if (!invalidReason.trim()) {
      toast.warning('Masukkan alasan tidak valid');
      return;
    }
    
    setProcessing(true);
    try {
      const response = await api.post('/bonanza/staff/validate', {
        record_ids: selectedRecords,
        is_valid: false,
        reason: invalidReason
      });
      
      // Show appropriate message based on auto-replace result
      const data = response.data;
      if (data.auto_replaced > 0) {
        toast.success(`${selectedRecords.length} record ditandai tidak valid. ${data.auto_replaced} record baru otomatis ditugaskan!`);
      } else if (data.replacement_failed > 0) {
        toast.warning(`${selectedRecords.length} record ditandai tidak valid. ${data.replacement_message || 'Record pengganti tidak tersedia.'}`);
      } else {
        toast.success(`${selectedRecords.length} record ditandai tidak valid. Admin akan diberitahu.`);
      }
      
      setSelectedRecords([]);
      setShowInvalidModal(false);
      setInvalidReason('');
      loadRecords();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal memvalidasi');
    } finally {
      setProcessing(false);
    }
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

  // Get validation status badge
  const getValidationBadge = (record) => {
    if (!record.validation_status) return null;
    if (record.validation_status === 'validated') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300">
          <CheckCircle size={12} /> Valid
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300">
        <XCircle size={12} /> Invalid
      </span>
    );
  };

  return (
    <div data-testid="staff-db-bonanza">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">{t('dbRecords.title')}</h2>

      {/* Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <input
          type="text"
          placeholder={t('dbRecords.searchRecords')}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 max-w-md h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          data-testid="bonanza-search"
        />
        <div className="flex items-center gap-2">
          <Package size={18} className="text-slate-500 dark:text-slate-400" />
          <select
            value={filterProduct}
            onChange={(e) => setFilterProduct(e.target.value)}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[180px]"
            data-testid="bonanza-filter-product"
          >
            <option value="">{t('dbRecords.allProducts')}</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Validation Actions Bar */}
      {selectedRecords.length > 0 && (
        <div className="mb-4 p-3 bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-800 rounded-xl flex items-center justify-between flex-wrap gap-3">
          <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
            {selectedRecords.length} record dipilih
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleMarkValid}
              disabled={processing}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm flex items-center gap-2 disabled:opacity-50"
              data-testid="btn-mark-valid"
            >
              <CheckCircle size={16} />
              Tandai Valid
            </button>
            <button
              onClick={() => setShowInvalidModal(true)}
              disabled={processing}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm flex items-center gap-2 disabled:opacity-50"
              data-testid="btn-mark-invalid"
            >
              <XCircle size={16} />
              Tandai Tidak Valid
            </button>
            <button
              onClick={() => setSelectedRecords([])}
              className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-sm"
            >
              Batal
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">{t('dbRecords.loadingRecords')}</div>
      ) : records.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <Gift className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">{t('dbRecords.noRecordsYet')}</p>
          <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">{t('dbRecords.adminWillAssign')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Validation Guide */}
          <div className="p-4 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" size={20} />
              <div className="text-sm text-amber-800 dark:text-amber-200">
                <p className="font-semibold mb-1">Validasi Database</p>
                <p>Pilih record dan tandai sebagai <strong>Valid</strong> jika data benar, atau <strong>Tidak Valid</strong> jika ada masalah. Admin akan diberitahu untuk record yang tidak valid dan akan memberikan pengganti.</p>
              </div>
            </div>
          </div>

          {Object.entries(filteredGroupedRecords).map(([dbName, dbRecords]) => {
            const unvalidatedRecords = dbRecords.filter(r => !r.validation_status);
            const allUnvalidatedSelected = unvalidatedRecords.length > 0 && unvalidatedRecords.every(r => selectedRecords.includes(r.id));
            
            return (
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
                    <div className="flex items-center gap-3">
                      {unvalidatedRecords.length > 0 && (
                        <button
                          onClick={() => selectAllInDatabase(dbRecords)}
                          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                        >
                          {allUnvalidatedSelected ? 'Batalkan Pilih Semua' : 'Pilih Semua Belum Validasi'}
                        </button>
                      )}
                      <div className="flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400">
                        <Calendar size={14} />
                        {t('dbRecords.assigned')}: {formatDate(dbRecords[0]?.assigned_at)}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300 w-10">
                          <input
                            type="checkbox"
                            checked={allUnvalidatedSelected && unvalidatedRecords.length > 0}
                            onChange={() => selectAllInDatabase(dbRecords)}
                            className="rounded border-slate-300 dark:border-slate-600"
                          />
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">#</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Status</th>
                        {visibleColumns.map(col => (
                          <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dbRecords.map(record => (
                        <tr 
                          key={record.id} 
                          className={`border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 ${
                            record.validation_status === 'invalid' ? 'bg-red-50/50 dark:bg-red-900/10' : ''
                          } ${
                            record.validation_status === 'validated' ? 'bg-green-50/50 dark:bg-green-900/10' : ''
                          }`}
                        >
                          <td className="px-4 py-3">
                            {!record.validation_status && (
                              <input
                                type="checkbox"
                                checked={selectedRecords.includes(record.id)}
                                onChange={() => toggleRecordSelection(record.id)}
                                className="rounded border-slate-300 dark:border-slate-600"
                              />
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-900 dark:text-white font-medium">{record.row_number}</td>
                          <td className="px-4 py-3">
                            {getValidationBadge(record)}
                            {!record.validation_status && (
                              <span className="text-xs text-slate-400">Belum divalidasi</span>
                            )}
                          </td>
                          {visibleColumns.map(col => (
                            <td key={col} className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">{record.row_data[col] || '-'}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Invalid Reason Modal */}
      {showInvalidModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-md" data-testid="invalid-reason-modal">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <XCircle className="text-red-500" size={20} />
                Tandai Tidak Valid
              </h3>
            </div>
            <div className="p-6">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                {selectedRecords.length} record akan ditandai tidak valid. Admin akan diberitahu dan akan memberikan pengganti.
              </p>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Alasan Tidak Valid <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={invalidReason}
                  onChange={(e) => setInvalidReason(e.target.value)}
                  placeholder="Contoh: Data tidak lengkap, nomor tidak aktif, sudah tidak bermain lagi, dll"
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  rows={3}
                  data-testid="invalid-reason-input"
                />
              </div>
            </div>
            <div className="p-6 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => { setShowInvalidModal(false); setInvalidReason(''); }}
                className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg"
              >
                Batal
              </button>
              <button
                onClick={handleMarkInvalid}
                disabled={processing || !invalidReason.trim()}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50 flex items-center gap-2"
                data-testid="btn-confirm-invalid"
              >
                {processing ? 'Memproses...' : 'Konfirmasi Tidak Valid'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
