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
                              
                              // Format for WhatsApp using wa.me (universal, works on mobile and desktop)
                              const whatsappUrl = `https://wa.me/${phoneNumber}`;
                              
                              return (
                                <td key={idx} className="px-4 py-3 text-sm">
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-900">{phoneNumber}</span>
                                    <a
                                      href={whatsappUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-emerald-600 hover:text-emerald-700 transition-colors"
                                      data-testid={`whatsapp-link-${record.id}`}
                                      title="Open WhatsApp chat"
                                    >
                                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                                      </svg>
                                    </a>
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
