import { useState, useEffect, useMemo } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { User, Package, ChevronLeft, FileSpreadsheet, Edit2, Check, X, Search, ExternalLink, Pin } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function MyAssignedRecords() {
  const { t } = useLanguage();
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [editingBatchId, setEditingBatchId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadProducts();
    loadBatches();
  }, []);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products');
    }
  };

  const loadBatches = async () => {
    try {
      const response = await api.get('/my-request-batches');
      setBatches(response.data);
    } catch (error) {
      toast.error('Failed to load request batches');
    } finally {
      setLoading(false);
    }
  };

  const handleEditTitle = (e, batch) => {
    e.stopPropagation();
    setEditingBatchId(batch.id);
    setEditTitle(batch.custom_title || batch.database_name);
  };

  const handleSaveTitle = async (e, batchId) => {
    e.stopPropagation();
    try {
      await api.patch(`/my-request-batches/${batchId}/title`, { title: editTitle });
      toast.success(t('myRecords.titleUpdated'));
      setEditingBatchId(null);
      loadBatches();
    } catch (error) {
      toast.error(t('messages.saveFailed'));
    }
  };

  const handleCancelEdit = (e) => {
    e.stopPropagation();
    setEditingBatchId(null);
    setEditTitle('');
  };

  const handleTogglePin = async (e, batchId, currentPinned) => {
    e.stopPropagation();
    try {
      await api.patch(`/my-request-batches/${batchId}/pin`, { is_pinned: !currentPinned });
      toast.success(!currentPinned ? t('myRecords.batchPinned') : t('myRecords.batchUnpinned'));
      loadBatches();
    } catch (error) {
      toast.error(t('messages.saveFailed'));
    }
  };

  const loadBatchRecords = async (batchId) => {
    if (editingBatchId) return; // Don't navigate while editing
    setLoadingRecords(true);
    try {
      const response = await api.get('/my-assigned-records-by-batch', { params: { request_id: batchId } });
      setRecords(response.data);
      setSelectedBatch(batches.find(b => b.id === batchId));
    } catch (error) {
      toast.error('Failed to load records');
    } finally {
      setLoadingRecords(false);
    }
  };

  const handleWhatsAppStatusChange = async (recordId, status) => {
    try {
      // Find current record to check if we're toggling off
      const currentRecord = records.find(r => r.id === recordId);
      const newStatus = currentRecord?.whatsapp_status === status ? null : status;
      
      await api.patch(`/customer-records/${recordId}/whatsapp-status`, {
        whatsapp_status: newStatus
      });
      toast.success(newStatus ? t('myRecords.whatsappStatusUpdated') : t('myRecords.whatsappStatusCleared'));
      if (selectedBatch) {
        loadBatchRecords(selectedBatch.id);
      }
    } catch (error) {
      toast.error(t('messages.saveFailed'));
    }
  };

  const handleRespondStatusChange = async (recordId, status) => {
    try {
      // Find current record to check if we're toggling off
      const currentRecord = records.find(r => r.id === recordId);
      const newStatus = currentRecord?.respond_status === status ? null : status;
      
      await api.patch(`/customer-records/${recordId}/respond-status`, {
        respond_status: newStatus
      });
      toast.success(newStatus ? t('myRecords.respondStatusUpdated') : t('myRecords.respondStatusCleared'));
      if (selectedBatch) {
        loadBatchRecords(selectedBatch.id);
      }
    } catch (error) {
      toast.error(t('messages.saveFailed'));
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Filter records based on search term
  const filteredRecords = useMemo(() => {
    if (!searchTerm.trim()) return records;
    
    const search = searchTerm.toLowerCase().trim();
    return records.filter(record => {
      // Search in all row_data fields
      const rowDataValues = Object.values(record.row_data || {});
      return rowDataValues.some(value => 
        value && String(value).toLowerCase().includes(search)
      );
    });
  }, [records, searchTerm]);

  // Filter batches by product
  const filteredBatches = selectedProduct 
    ? batches.filter(b => b.product_name === products.find(p => p.id === selectedProduct)?.name)
    : batches;

  // Render batch list view
  const renderBatchList = () => (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">{t('myRecords.title')}</h2>

      <div className="mb-6">
        <select
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
          data-testid="filter-assigned-product"
          className="flex h-10 w-64 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white px-3 py-2 text-sm ring-offset-white dark:ring-offset-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
        >
          <option value="">{t('myRecords.allProducts')}</option>
          {products.map((product) => (
            <option key={product.id} value={product.id}>
              {product.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">{t('myRecords.loadingBatches')}</div>
      ) : filteredBatches.length === 0 ? (
        <div className="text-center py-12">
          <User className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">{t('myRecords.noAssignedYet')}</p>
          <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">{t('myRecords.requestFromBrowse')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="batch-list">
          {filteredBatches.map((batch, index) => (
            <div
              key={batch.id}
              onClick={() => loadBatchRecords(batch.id)}
              className={`bg-white dark:bg-slate-800 border rounded-xl p-5 shadow-sm hover:shadow-md cursor-pointer transition-all group relative ${
                batch.is_pinned
                  ? 'border-yellow-400 dark:border-yellow-500 ring-1 ring-yellow-200 dark:ring-yellow-800'
                  : batch.is_legacy 
                    ? 'border-amber-200 dark:border-amber-800 hover:border-amber-400 dark:hover:border-amber-600' 
                    : 'border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600'
              }`}
              data-testid={`batch-card-${batch.id}`}
            >
              {/* Pinned indicator */}
              {batch.is_pinned && (
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center shadow-sm">
                  <Pin size={12} className="text-yellow-900" />
                </div>
              )}
              
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold ${
                    batch.is_pinned
                      ? 'bg-yellow-100 text-yellow-700'
                      : batch.is_legacy 
                        ? 'bg-amber-100 text-amber-600' 
                        : 'bg-indigo-100 text-indigo-600'
                  }`}>
                    {batch.is_pinned ? <Pin size={18} /> : batch.is_legacy ? '★' : `#${filteredBatches.filter(b => !b.is_legacy && !b.is_pinned).length - filteredBatches.filter(b => !b.is_legacy && !b.is_pinned).indexOf(batch)}`}
                  </div>
                  <div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      batch.is_pinned
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300'
                        : batch.is_legacy 
                          ? 'bg-amber-100 text-amber-800' 
                          : 'bg-indigo-100 text-indigo-800'
                    }`}>
                      {batch.product_name}
                    </span>
                    {batch.is_legacy && (
                      <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                        Legacy
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {editingBatchId !== batch.id && (
                    <>
                      {/* Pin button */}
                      <button
                        onClick={(e) => handleTogglePin(e, batch.id, batch.is_pinned)}
                        className={`p-1.5 rounded transition-colors ${
                          batch.is_pinned 
                            ? 'text-yellow-500 hover:text-yellow-700 hover:bg-yellow-50 dark:hover:bg-yellow-900/30' 
                            : 'text-slate-400 hover:text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/30 opacity-0 group-hover:opacity-100'
                        }`}
                        title={batch.is_pinned ? t('myRecords.unpin') : t('myRecords.pin')}
                        data-testid={`pin-batch-${batch.id}`}
                      >
                        <Pin size={16} className={batch.is_pinned ? 'fill-current' : ''} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(`/batch/${batch.id}`, '_blank');
                        }}
                        className={`p-1.5 rounded transition-colors opacity-0 group-hover:opacity-100 ${
                          batch.is_legacy 
                            ? 'text-amber-400 hover:text-amber-600 hover:bg-amber-50' 
                            : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50'
                        }`}
                        title={t('myRecords.openInNewTab')}
                        data-testid={`open-new-tab-${batch.id}`}
                      >
                        <ExternalLink size={16} />
                      </button>
                      <ChevronLeft className={`rotate-180 transition-colors ${
                        batch.is_legacy 
                          ? 'text-amber-400 group-hover:text-amber-600' 
                          : 'text-slate-400 group-hover:text-indigo-600'
                      }`} size={20} />
                    </>
                  )}}
                </div>
              </div>
              
              {/* Editable Title */}
              {editingBatchId === batch.id ? (
                <div className="mb-2" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="flex-1 h-8 px-2 text-sm font-semibold border border-indigo-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      autoFocus
                      data-testid="edit-batch-title-input"
                    />
                    <button
                      onClick={(e) => handleSaveTitle(e, batch.id)}
                      className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded transition-colors"
                      data-testid="save-batch-title"
                    >
                      <Check size={18} />
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="p-1.5 text-slate-400 hover:bg-slate-100 rounded transition-colors"
                      data-testid="cancel-edit-title"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>
              ) : (
                <h3 className="font-semibold text-slate-900 mb-2 flex items-center gap-2 group/title">
                  <FileSpreadsheet size={16} className="text-slate-500" />
                  <span className="flex-1">{batch.custom_title || batch.database_name}</span>
                  <button
                    onClick={(e) => handleEditTitle(e, batch)}
                    className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                    title={t('myRecords.editTitle')}
                    data-testid={`edit-title-${batch.id}`}
                  >
                    <Edit2 size={14} />
                  </button>
                </h3>
              )}
              
              <div className="space-y-1.5 text-sm">
                <div className="flex items-center justify-between text-slate-600">
                  <span>{t('myRecords.records')}:</span>
                  <span className="font-semibold text-slate-900">{batch.record_count} {t('myRecords.customers')}</span>
                </div>
                
                {/* WhatsApp Status Counts */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-2">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span className="text-slate-600">{t('myRecords.ada')}:</span>
                  </div>
                  <span className="font-semibold text-emerald-600">{batch.ada_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                    <span className="text-slate-600">{t('myRecords.ceklis1')}:</span>
                  </div>
                  <span className="font-semibold text-amber-600">{batch.ceklis1_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                    <span className="text-slate-600">{t('myRecords.tidak')}:</span>
                  </div>
                  <span className="font-semibold text-rose-600">{batch.tidak_count || 0}</span>
                </div>
                
                {/* Respond Status Counts */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-2">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    <span className="text-slate-600">{t('myRecords.respondYa')}:</span>
                  </div>
                  <span className="font-semibold text-blue-600">{batch.respond_ya_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                    <span className="text-slate-600">{t('myRecords.respondTidak')}:</span>
                  </div>
                  <span className="font-semibold text-slate-500">{batch.respond_tidak_count || 0}</span>
                </div>
                
                {batch.is_legacy && (
                  <div className="text-xs text-amber-600 mt-2 pt-2 border-t border-slate-100">
                    {t('myRecords.assignedBefore')}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // Render records view for selected batch
  const renderRecordsView = () => {
    const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];
    
    return (
      <div>
        <div className="mb-6">
          <button
            onClick={() => {
              setSelectedBatch(null);
              setRecords([]);
              setSearchTerm('');
            }}
            className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
            data-testid="back-to-batches"
          >
            <ChevronLeft size={20} />
            {t('myRecords.backToAll')}
          </button>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Package className="text-indigo-600 dark:text-indigo-400" size={20} />
                {selectedBatch.custom_title || selectedBatch.database_name}
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                {filteredRecords.length === records.length 
                  ? `${records.length} ${t('myRecords.customers')}`
                  : `${filteredRecords.length} dari ${records.length} ${t('myRecords.customers')}`
                }
                {` • ${selectedBatch.product_name}`}
              </p>
            </div>
            
            {/* Search Bar */}
            <div className="relative w-full sm:w-72">
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

          {loadingRecords ? (
            <div className="text-center py-12 text-slate-600 dark:text-slate-400">{t('myRecords.loadingRecords')}</div>
          ) : records.length === 0 ? (
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
                    <tr key={record.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-3 text-sm text-slate-900 font-medium">{record.row_number}</td>
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
                                <span className="text-slate-900 font-medium">{phoneNumber}</span>
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
                          <td key={idx} className="px-4 py-3 text-sm text-slate-900">
                            {cellValue || '-'}
                          </td>
                        );
                      })}
                      <td className="px-4 py-3 text-sm text-slate-600">
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
    );
  };

  return (
    <div data-testid="my-assigned-records">
      {selectedBatch ? renderRecordsView() : renderBatchList()}
    </div>
  );
}
