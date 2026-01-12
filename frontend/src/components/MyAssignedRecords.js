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
              <div key={dbName} className=\"bg-white border border-slate-200 rounded-xl p-6 shadow-sm\">
                <div className=\"flex items-center justify-between mb-4\">
                  <div>
                    <h3 className=\"text-xl font-semibold text-slate-900 flex items-center gap-2\">
                      <Package className=\"text-indigo-600\" size={20} />
                      {dbName}
                    </h3>
                    <p className=\"text-sm text-slate-600 mt-1\">
                      {dbRecords.length} customer{dbRecords.length !== 1 ? 's' : ''} assigned
                      {dbRecords[0] && ` \u2022 ${dbRecords[0].product_name}`}
                    </p>
                  </div>
                </div>

                <div className=\"overflow-x-auto\">
                  <table className=\"min-w-full border border-slate-200 rounded-lg\">
                    <thead className=\"bg-slate-50\">
                      <tr>
                        <th className=\"px-4 py-3 text-left text-xs font-semibold text-slate-700\">#</th>
                        {columns.map((col, idx) => (
                          <th key={idx} className=\"px-4 py-3 text-left text-xs font-semibold text-slate-700\">
                            {col}
                          </th>
                        ))}
                        <th className=\"px-4 py-3 text-left text-xs font-semibold text-slate-700\">Assigned Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dbRecords.map((record) => (
                        <tr key={record.id} className=\"border-b border-slate-100 hover:bg-slate-50\">
                          <td className=\"px-4 py-3 text-sm text-slate-900 font-medium\">{record.row_number}</td>
                          {columns.map((col, idx) => (
                            <td key={idx} className=\"px-4 py-3 text-sm text-slate-900\">
                              {record.row_data[col] || '-'}
                            </td>
                          ))}
                          <td className=\"px-4 py-3 text-sm text-slate-600\">
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
