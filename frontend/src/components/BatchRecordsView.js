import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { api } from '../App';
import { toast } from 'sonner';
import { Package, Search, X, ArrowLeft, ExternalLink } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function BatchRecordsView() {
  const { t } = useLanguage();
  const { batchId } = useParams();
  const [searchParams] = useSearchParams();
  const [batch, setBatch] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadBatchData = useCallback(async () => {
    if (!batchId) return;
    
    setLoading(true);
    try {
      // Load batch info and records
      const [batchesRes, recordsRes] = await Promise.all([
        api.get('/my-request-batches'),
        api.get('/my-assigned-records-by-batch', { params: { request_id: batchId } })
      ]);
      
      const currentBatch = batchesRes.data.find(b => b.id === batchId);
      setBatch(currentBatch);
      setRecords(recordsRes.data);
    } catch (error) {
      toast.error(t('messages.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [batchId, t]);

  useEffect(() => {
    loadBatchData();
  }, [loadBatchData]);

  const handleWhatsAppStatusChange = async (recordId, status) => {
    try {
      const currentRecord = records.find(r => r.id === recordId);
      const newStatus = currentRecord?.whatsapp_status === status ? null : status;
      
      await api.patch(`/customer-records/${recordId}/whatsapp-status`, {
        whatsapp_status: newStatus
      });
      toast.success(newStatus ? t('myRecords.whatsappStatusUpdated') : t('myRecords.whatsappStatusCleared'));
      loadBatchData();
    } catch (error) {
      toast.error(t('messages.saveFailed'));
    }
  };

  const handleRespondStatusChange = async (recordId, status) => {
    try {
      const currentRecord = records.find(r => r.id === recordId);
      const newStatus = currentRecord?.respond_status === status ? null : status;
      
      await api.patch(`/customer-records/${recordId}/respond-status`, {
        respond_status: newStatus
      });
      toast.success(newStatus ? t('myRecords.respondStatusUpdated') : t('myRecords.respondStatusCleared'));
      loadBatchData();
    } catch (error) {
      toast.error(t('messages.saveFailed'));
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  // Filter records based on search term
  const filteredRecords = useMemo(() => {
    if (!searchTerm.trim()) return records;
    
    const search = searchTerm.toLowerCase().trim();
    return records.filter(record => {
      const rowDataValues = Object.values(record.row_data || {});
      return rowDataValues.some(value => 
        value && String(value).toLowerCase().includes(search)
      );
    });
  }, [records, searchTerm]);

  const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-slate-600 dark:text-slate-400">{t('myRecords.loadingRecords')}</p>
        </div>
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Package className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">{t('myRecords.noRecordsFound')}</p>
          <a 
            href="/" 
            className="mt-4 inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium"
          >
            <ArrowLeft size={18} />
            {t('myRecords.backToAll')}
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <a 
            href="/" 
            className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium transition-colors mb-4"
          >
            <ArrowLeft size={18} />
            {t('myRecords.backToAll')}
          </a>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                  batch.is_legacy ? 'bg-amber-100 text-amber-600' : 'bg-indigo-100 text-indigo-600'
                }`}>
                  <Package size={24} />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                    {batch.custom_title || batch.database_name}
                  </h1>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      batch.is_legacy 
                        ? 'bg-amber-100 text-amber-800' 
                        : 'bg-indigo-100 text-indigo-800'
                    }`}>
                      {batch.product_name}
                    </span>
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      • {filteredRecords.length === records.length 
                          ? `${records.length} ${t('myRecords.customers')}`
                          : `${filteredRecords.length} dari ${records.length} ${t('myRecords.customers')}`
                        }
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Search Bar */}
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="text"
                placeholder={t('myRecords.searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 pl-10 pr-10 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400"
                data-testid="search-records-input"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                  data-testid="clear-search"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>

          {/* Stats Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
            <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('myRecords.records')}</p>
              <p className="text-xl font-bold text-slate-900 dark:text-white">{batch.record_count}</p>
            </div>
            <div className="bg-emerald-50 dark:bg-emerald-900/30 rounded-lg p-3">
              <p className="text-xs text-emerald-600 dark:text-emerald-400">{t('myRecords.ada')}</p>
              <p className="text-xl font-bold text-emerald-700 dark:text-emerald-300">{batch.ada_count || 0}</p>
            </div>
            <div className="bg-amber-50 dark:bg-amber-900/30 rounded-lg p-3">
              <p className="text-xs text-amber-600 dark:text-amber-400">{t('myRecords.ceklis1')}</p>
              <p className="text-xl font-bold text-amber-700 dark:text-amber-300">{batch.ceklis1_count || 0}</p>
            </div>
            <div className="bg-rose-50 dark:bg-rose-900/30 rounded-lg p-3">
              <p className="text-xs text-rose-600 dark:text-rose-400">{t('myRecords.tidak')}</p>
              <p className="text-xl font-bold text-rose-700 dark:text-rose-300">{batch.tidak_count || 0}</p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-3">
              <p className="text-xs text-blue-600 dark:text-blue-400">{t('myRecords.respondYa')}</p>
              <p className="text-xl font-bold text-blue-700 dark:text-blue-300">{batch.respond_ya_count || 0}</p>
            </div>
            <div className="bg-slate-100 dark:bg-slate-600 rounded-lg p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('myRecords.respondTidak')}</p>
              <p className="text-xl font-bold text-slate-700 dark:text-slate-200">{batch.respond_tidak_count || 0}</p>
            </div>
          </div>

          {/* Records Table */}
          {records.length === 0 ? (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">{t('myRecords.noRecordsFound')}</div>
          ) : filteredRecords.length === 0 ? (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
              <Search className="mx-auto text-slate-300 dark:text-slate-600 mb-3" size={48} />
              <p>{t('myRecords.noCustomersMatch')} &quot;{searchTerm}&quot;</p>
              <button 
                onClick={() => setSearchTerm('')}
                className="mt-2 text-indigo-600 hover:text-indigo-800 text-sm font-medium"
              >
                {t('myRecords.clearSearch')}
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border border-slate-200 dark:border-slate-700 rounded-lg">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">#</th>
                    {columns.map((col, idx) => (
                      <th key={idx} className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">
                        {col}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">{t('myRecords.assignedDate')}</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">{t('myRecords.whatsappAdaTidak')}</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">{t('myRecords.respondYaTidak')}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecords.map((record) => (
                    <tr key={record.id} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">
                      <td className="px-4 py-3 text-sm text-slate-900 dark:text-white font-medium">{record.row_number}</td>
                      {columns.map((col, idx) => {
                        const cellValue = record.row_data[col];
                        const isWhatsAppColumn = col.toLowerCase() === 'telpon';
                        
                        if (isWhatsAppColumn && cellValue) {
                          let phoneNumber = cellValue;
                          if (cellValue.includes('wa.me/')) {
                            phoneNumber = cellValue.split('wa.me/')[1].split('?')[0];
                          }
                          phoneNumber = phoneNumber.replace(/[^\d+]/g, '');
                          
                          const whatsappUrl = `https://wa.me/${phoneNumber}`;
                          
                          const handleCopy = (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            
                            const textarea = document.createElement('textarea');
                            textarea.value = whatsappUrl;
                            textarea.style.position = 'fixed';
                            textarea.style.opacity = '0';
                            document.body.appendChild(textarea);
                            textarea.select();
                            
                            try {
                              document.execCommand('copy');
                              toast.success(t('myRecords.linkCopied'));
                            } catch (err) {
                              toast.error(t('messages.somethingWrong'));
                            } finally {
                              document.body.removeChild(textarea);
                            }
                          };
                          
                          return (
                            <td key={idx} className="px-4 py-3 text-sm">
                              <div className="flex items-center gap-2">
                                <span className="text-slate-900 dark:text-white font-medium">{phoneNumber}</span>
                                <button
                                  onClick={handleCopy}
                                  data-testid={`copy-number-${record.id}`}
                                  title={t('myRecords.copyWhatsappLink')}
                                  className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 p-1.5 rounded transition-colors"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                </button>
                              </div>
                            </td>
                          );
                        }
                        
                        return (
                          <td key={idx} className="px-4 py-3 text-sm text-slate-900 dark:text-white">
                            {cellValue || '-'}
                          </td>
                        );
                      })}
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                        {formatDate(record.assigned_at)}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleWhatsAppStatusChange(record.id, 'ada')}
                            data-testid={`whatsapp-ada-${record.id}`}
                            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                              record.whatsapp_status === 'ada'
                                ? 'bg-emerald-500 text-white ring-2 ring-emerald-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 hover:text-emerald-700 dark:hover:text-emerald-400'
                            }`}
                          >
                            {t('myRecords.ada')}
                          </button>
                          <button
                            onClick={() => handleWhatsAppStatusChange(record.id, 'ceklis1')}
                            data-testid={`whatsapp-ceklis1-${record.id}`}
                            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                              record.whatsapp_status === 'ceklis1'
                                ? 'bg-amber-500 text-white ring-2 ring-amber-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-amber-100 dark:hover:bg-amber-900/30 hover:text-amber-700 dark:hover:text-amber-400'
                            }`}
                          >
                            {t('myRecords.ceklis1')}
                          </button>
                          <button
                            onClick={() => handleWhatsAppStatusChange(record.id, 'tidak')}
                            data-testid={`whatsapp-tidak-${record.id}`}
                            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                              record.whatsapp_status === 'tidak'
                                ? 'bg-rose-500 text-white ring-2 ring-rose-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-rose-100 dark:hover:bg-rose-900/30 hover:text-rose-700 dark:hover:text-rose-400'
                            }`}
                          >
                            {t('myRecords.tidak')}
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleRespondStatusChange(record.id, 'ya')}
                            data-testid={`respond-ya-${record.id}`}
                            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                              record.respond_status === 'ya'
                                ? 'bg-emerald-500 text-white ring-2 ring-emerald-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 hover:text-emerald-700 dark:hover:text-emerald-400'
                            }`}
                          >
                            Ya
                          </button>
                          <button
                            onClick={() => handleRespondStatusChange(record.id, 'tidak')}
                            data-testid={`respond-tidak-${record.id}`}
                            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                              record.respond_status === 'tidak'
                                ? 'bg-rose-500 text-white ring-2 ring-rose-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-rose-100 dark:hover:bg-rose-900/30 hover:text-rose-700 dark:hover:text-rose-400'
                            }`}
                          >
                            {t('myRecords.tidak')}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
