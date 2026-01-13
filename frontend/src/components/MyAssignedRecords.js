import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { User, Package, Calendar, ChevronLeft, FileSpreadsheet, Clock } from 'lucide-react';

export default function MyAssignedRecords() {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);

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

  const loadBatchRecords = async (batchId) => {
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
      await api.patch(`/customer-records/${recordId}/whatsapp-status`, {
        whatsapp_status: status
      });
      toast.success('WhatsApp status updated');
      if (selectedBatch) {
        loadBatchRecords(selectedBatch.id);
      }
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleRespondStatusChange = async (recordId, status) => {
    try {
      await api.patch(`/customer-records/${recordId}/respond-status`, {
        respond_status: status
      });
      toast.success('Respond status updated');
      if (selectedBatch) {
        loadBatchRecords(selectedBatch.id);
      }
    } catch (error) {
      toast.error('Failed to update status');
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

  const formatShortDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  // Filter batches by product
  const filteredBatches = selectedProduct 
    ? batches.filter(b => b.product_name === products.find(p => p.id === selectedProduct)?.name)
    : batches;

  // Render batch list view
  const renderBatchList = () => (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">My Assigned Customers</h2>

      <div className="mb-6">
        <select
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
          data-testid="filter-assigned-product"
          className="flex h-10 w-64 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
        >
          <option value="">All Products</option>
          {products.map((product) => (
            <option key={product.id} value={product.id}>
              {product.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading your data batches...</div>
      ) : filteredBatches.length === 0 ? (
        <div className="text-center py-12">
          <User className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600">No assigned customers yet</p>
          <p className="text-sm text-slate-500 mt-2">Request customer records from the Browse Databases page</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="batch-list">
          {filteredBatches.map((batch, index) => (
            <div
              key={batch.id}
              onClick={() => loadBatchRecords(batch.id)}
              className={`bg-white border rounded-xl p-5 shadow-sm hover:shadow-md cursor-pointer transition-all group ${
                batch.is_legacy 
                  ? 'border-amber-200 hover:border-amber-400' 
                  : 'border-slate-200 hover:border-indigo-300'
              }`}
              data-testid={`batch-card-${batch.id}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold ${
                    batch.is_legacy 
                      ? 'bg-amber-100 text-amber-600' 
                      : 'bg-indigo-100 text-indigo-600'
                  }`}>
                    {batch.is_legacy ? '★' : `#${filteredBatches.filter(b => !b.is_legacy).length - filteredBatches.filter(b => !b.is_legacy).indexOf(batch)}`}
                  </div>
                  <div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      batch.is_legacy 
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
                <ChevronLeft className={`rotate-180 transition-colors ${
                  batch.is_legacy 
                    ? 'text-amber-400 group-hover:text-amber-600' 
                    : 'text-slate-400 group-hover:text-indigo-600'
                }`} size={20} />
              </div>
              
              <h3 className="font-semibold text-slate-900 mb-2 flex items-center gap-2">
                <FileSpreadsheet size={16} className="text-slate-500" />
                {batch.database_name}
              </h3>
              
              <div className="space-y-1.5 text-sm">
                <div className="flex items-center justify-between text-slate-600">
                  <span>Records:</span>
                  <span className="font-semibold text-slate-900">{batch.record_count} customers</span>
                </div>
                
                {/* WhatsApp Status Counts */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-2">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span className="text-slate-600">Ada:</span>
                  </div>
                  <span className="font-semibold text-emerald-600">{batch.ada_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                    <span className="text-slate-600">Ceklis 1:</span>
                  </div>
                  <span className="font-semibold text-amber-600">{batch.ceklis1_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                    <span className="text-slate-600">Tidak:</span>
                  </div>
                  <span className="font-semibold text-rose-600">{batch.tidak_count || 0}</span>
                </div>
                
                {batch.is_legacy && (
                  <div className="text-xs text-amber-600 mt-2 pt-2 border-t border-slate-100">
                    Assigned before batch tracking
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
            }}
            className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
            data-testid="back-to-batches"
          >
            <ChevronLeft size={20} />
            Back to All Batches
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                <Package className="text-indigo-600" size={20} />
                {selectedBatch.database_name}
              </h3>
              <p className="text-sm text-slate-600 mt-1">
                {records.length} customer{records.length !== 1 ? 's' : ''} assigned
                {` • ${selectedBatch.product_name}`}
                {` • Approved: ${formatShortDate(selectedBatch.approved_at)}`}
              </p>
            </div>
          </div>

          {loadingRecords ? (
            <div className="text-center py-12 text-slate-600">Loading records...</div>
          ) : records.length === 0 ? (
            <div className="text-center py-12 text-slate-500">No records found in this batch</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border border-slate-200 rounded-lg">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">#</th>
                    {columns.map((col, idx) => (
                      <th key={idx} className="px-4 py-3 text-left text-xs font-semibold text-slate-700">
                        {col}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Assigned Date</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">WhatsApp Ada/Tidak</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Respond Ya/Tidak</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
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
                              toast.success('WhatsApp link copied! Paste in browser address bar');
                            } catch (err) {
                              toast.error('Failed to copy');
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
                                  title="Copy WhatsApp link"
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
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name={`whatsapp-${record.id}`}
                              checked={record.whatsapp_status === 'ada'}
                              onChange={() => handleWhatsAppStatusChange(record.id, 'ada')}
                              data-testid={`whatsapp-ada-${record.id}`}
                              className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
                            />
                            <span className="text-sm text-slate-700">Ada</span>
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name={`whatsapp-${record.id}`}
                              checked={record.whatsapp_status === 'ceklis1'}
                              onChange={() => handleWhatsAppStatusChange(record.id, 'ceklis1')}
                              data-testid={`whatsapp-ceklis1-${record.id}`}
                              className="w-4 h-4 text-amber-600 focus:ring-amber-500"
                            />
                            <span className="text-sm text-slate-700">Ceklis 1</span>
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name={`whatsapp-${record.id}`}
                              checked={record.whatsapp_status === 'tidak'}
                              onChange={() => handleWhatsAppStatusChange(record.id, 'tidak')}
                              data-testid={`whatsapp-tidak-${record.id}`}
                              className="w-4 h-4 text-rose-600 focus:ring-rose-500"
                            />
                            <span className="text-sm text-slate-700">Tidak</span>
                          </label>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name={`respond-${record.id}`}
                              checked={record.respond_status === 'ya'}
                              onChange={() => handleRespondStatusChange(record.id, 'ya')}
                              data-testid={`respond-ya-${record.id}`}
                              className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
                            />
                            <span className="text-sm text-slate-700">Ya</span>
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name={`respond-${record.id}`}
                              checked={record.respond_status === 'tidak'}
                              onChange={() => handleRespondStatusChange(record.id, 'tidak')}
                              data-testid={`respond-tidak-${record.id}`}
                              className="w-4 h-4 text-rose-600 focus:ring-rose-500"
                            />
                            <span className="text-sm text-slate-700">Tidak</span>
                          </label>
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
