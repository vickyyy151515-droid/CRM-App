import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Search, User, Package, FileSpreadsheet } from 'lucide-react';

export default function AllAssignments() {
  const [records, setRecords] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedDatabase, setSelectedDatabase] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProducts();
    loadDatabases();
  }, []);

  useEffect(() => {
    if (selectedDatabase) {
      loadRecords();
    }
  }, [selectedDatabase]);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products');
    }
  };

  const loadDatabases = async () => {
    try {
      const response = await api.get('/databases');
      setDatabases(response.data);
      if (response.data.length > 0) {
        setSelectedDatabase(response.data[0].id);
      }
    } catch (error) {
      toast.error('Failed to load databases');
    }
  };

  const loadRecords = async () => {
    if (!selectedDatabase) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/databases/${selectedDatabase}/records`);
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load records');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredDatabases = databases.filter(db => {
    if (selectedProduct && db.product_id !== selectedProduct) return false;
    if (search && !db.filename.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const selectedDbInfo = databases.find(db => db.id === selectedDatabase);
  const assignedRecords = records.filter(r => r.status === 'assigned');
  const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];

  const getStatusBadge = (status) => {
    const styles = {
      available: 'bg-emerald-100 text-emerald-700',
      requested: 'bg-amber-100 text-amber-700',
      assigned: 'bg-slate-100 text-slate-700'
    };
    return (
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">View All Assignments</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Filter by Product</label>
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            data-testid="filter-product"
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

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Search Database</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search databases..."
              className="flex h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Select Database</label>
          <select
            value={selectedDatabase}
            onChange={(e) => setSelectedDatabase(e.target.value)}
            data-testid="select-database"
            className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            {filteredDatabases.map((db) => (
              <option key={db.id} value={db.id}>
                {db.filename} ({db.total_records} records)
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedDbInfo && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <FileSpreadsheet className="text-indigo-600" size={24} />
                <h3 className="text-2xl font-semibold text-slate-900">{selectedDbInfo.filename}</h3>
                <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200">
                  {selectedDbInfo.product_name}
                </span>
              </div>
              {selectedDbInfo.description && (
                <p className="text-sm text-slate-600 mb-3">{selectedDbInfo.description}</p>
              )}
            </div>
          </div>
          
          <div className="grid grid-cols-4 gap-4 mt-4">
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-600 mb-1">Total Records</p>
              <p className="text-2xl font-bold text-slate-900">{selectedDbInfo.total_records}</p>
            </div>
            <div className="bg-emerald-50 rounded-lg p-3">
              <p className="text-xs text-emerald-600 mb-1">Available</p>
              <p className="text-2xl font-bold text-emerald-700">{records.filter(r => r.status === 'available').length}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3">
              <p className="text-xs text-amber-600 mb-1">Requested</p>
              <p className="text-2xl font-bold text-amber-700">{records.filter(r => r.status === 'requested').length}</p>
            </div>
            <div className="bg-indigo-50 rounded-lg p-3">
              <p className="text-xs text-indigo-600 mb-1">Assigned</p>
              <p className="text-2xl font-bold text-indigo-700">{assignedRecords.length}</p>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading records...</div>
      ) : records.length === 0 ? (
        <div className="text-center py-12 text-slate-600">No records found</div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full" data-testid="all-assignments-table">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">#</th>
                  {columns.map((col, idx) => (
                    <th key={idx} className="px-4 py-3 text-left text-xs font-semibold text-slate-700">
                      {col}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Assigned To</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Assigned Date</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">WhatsApp Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Respond Status</th>
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
                        
                        return (
                          <td key={idx} className="px-4 py-3 text-sm">
                            <span className="text-slate-900 font-medium">{phoneNumber}</span>
                          </td>
                        );
                      }
                      
                      return (
                        <td key={idx} className="px-4 py-3 text-sm text-slate-900">
                          {cellValue || '-'}
                        </td>
                      );
                    })}
                    <td className="px-4 py-3 text-sm">{getStatusBadge(record.status)}</td>
                    <td className="px-4 py-3 text-sm">
                      {record.assigned_to_name ? (
                        <div className="flex items-center gap-2">
                          <User className="text-indigo-600" size={14} />
                          <span className="text-slate-900">{record.assigned_to_name}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {formatDate(record.assigned_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {record.whatsapp_status === 'ada' && (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          Ada
                        </span>
                      )}
                      {record.whatsapp_status === 'tidak' && (
                        <span className="inline-flex items-center gap-1 text-rose-600 font-medium">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                          Tidak
                        </span>
                      )}
                      {!record.whatsapp_status && (
                        <span className="text-slate-400 text-xs">Not checked</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {record.respond_status === 'ya' && (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          Ya
                        </span>
                      )}
                      {record.respond_status === 'tidak' && (
                        <span className="inline-flex items-center gap-1 text-rose-600 font-medium">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                          Tidak
                        </span>
                      )}
                      {!record.respond_status && (
                        <span className="text-slate-400 text-xs">Not checked</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
