import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { User, Package } from 'lucide-react';

export default function MyAssignedRecords() {
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProducts();
    loadRecords();
  }, [selectedProduct]);

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
      const params = selectedProduct ? { product_id: selectedProduct } : {};
      const response = await api.get('/my-assigned-records', { params });
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load assigned records');
    } finally {
      setLoading(false);
    }
  };

  const handleWhatsAppStatusChange = async (recordId, status) => {
    try {
      await api.patch(`/customer-records/${recordId}/whatsapp-status`, {
        whatsapp_status: status
      });
      toast.success('WhatsApp status updated');
      loadRecords();
    } catch (error) {
      toast.error('Failed to update status');
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

  const groupedRecords = records.reduce((acc, record) => {
    const key = record.database_name;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(record);
    return acc;
  }, {});

  return (
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
        <div className="text-center py-12 text-slate-600">Loading your assigned customers...</div>
      ) : records.length === 0 ? (
        <div className="text-center py-12">
          <User className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600">No assigned customers yet</p>
          <p className="text-sm text-slate-500 mt-2">Request customer records from the Browse Databases page</p>
        </div>
      ) : (
        <div className="space-y-6" data-testid="assigned-records-list">
          {Object.entries(groupedRecords).map(([dbName, dbRecords]) => {
            const columns = dbRecords.length > 0 ? Object.keys(dbRecords[0].row_data) : [];
            
            return (
              <div key={dbName} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                      <Package className="text-indigo-600" size={20} />
                      {dbName}
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      {dbRecords.length} customer{dbRecords.length !== 1 ? 's' : ''} assigned
                      {dbRecords[0] && ` • ${dbRecords[0].product_name}`}
                    </p>
                  </div>
                </div>

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
                      </tr>
                    </thead>
                    <tbody>
                      {dbRecords.map((record) => (
                        <tr key={record.id} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="px-4 py-3 text-sm text-slate-900 font-medium">{record.row_number}</td>
                          {columns.map((col, idx) => {
                            const cellValue = record.row_data[col];
                            const isWhatsAppColumn = col.toLowerCase() === 'telpon';
                            
                            if (isWhatsAppColumn && cellValue) {
                              // Extract phone number from wa.me link or use as-is
                              let phoneNumber = cellValue;
                              if (cellValue.includes('wa.me/')) {
                                phoneNumber = cellValue.split('wa.me/')[1].split('?')[0];
                              }
                              // Remove any non-digit characters except +
                              phoneNumber = phoneNumber.replace(/[^\d+]/g, '');
                              
                              const whatsappUrl = `https://wa.me/${phoneNumber}`;
                              
                              const handleCopy = (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                
                                // Create a temporary textarea to copy from
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
                                  checked={record.whatsapp_status === 'tidak'}
                                  onChange={() => handleWhatsAppStatusChange(record.id, 'tidak')}
                                  data-testid={`whatsapp-tidak-${record.id}`}
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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
