import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Plus, Edit2, Trash2, Calendar, Package, TrendingUp, Save, X, UserPlus, RefreshCw, Download } from 'lucide-react';

export default function StaffOmsetCRM() {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [records, setRecords] = useState([]);
  const [ndpRdpStats, setNdpRdpStats] = useState(null);
  const [existingDates, setExistingDates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [formData, setFormData] = useState({
    customer_id: '',
    nominal: '',
    depo_kelipatan: '1',
    keterangan: ''
  });

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    if (selectedProduct) {
      loadRecords();
      loadExistingDates();
      loadNdpRdpStats();
    }
  }, [selectedProduct, selectedDate]);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
      if (response.data.length > 0) {
        setSelectedProduct(response.data[0].id);
      }
    } catch (error) {
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const loadRecords = async () => {
    if (!selectedProduct) return;
    
    try {
      const response = await api.get('/omset/record-types', {
        params: { product_id: selectedProduct, record_date: selectedDate }
      });
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load records');
    }
  };

  const loadNdpRdpStats = async () => {
    if (!selectedProduct) return;
    
    try {
      const response = await api.get('/omset/ndp-rdp', {
        params: { product_id: selectedProduct, record_date: selectedDate }
      });
      setNdpRdpStats(response.data);
    } catch (error) {
      console.error('Failed to load NDP/RDP stats');
    }
  };

  const loadExistingDates = async () => {
    if (!selectedProduct) return;
    
    try {
      const response = await api.get('/omset/dates', {
        params: { product_id: selectedProduct }
      });
      setExistingDates(response.data);
    } catch (error) {
      console.error('Failed to load dates');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.customer_id || !formData.nominal) {
      toast.error('Please fill required fields');
      return;
    }

    // Multiply nominal by 1000 (100 → 100,000)
    const actualNominal = parseFloat(formData.nominal) * 1000;

    try {
      if (editingRecord) {
        await api.put(`/omset/${editingRecord.id}`, {
          customer_name: formData.customer_id,
          customer_id: formData.customer_id,
          nominal: actualNominal,
          depo_kelipatan: parseFloat(formData.depo_kelipatan) || 1,
          keterangan: formData.keterangan
        });
        toast.success('Record updated');
      } else {
        await api.post('/omset', {
          product_id: selectedProduct,
          record_date: selectedDate,
          customer_name: formData.customer_id,
          customer_id: formData.customer_id,
          nominal: actualNominal,
          depo_kelipatan: parseFloat(formData.depo_kelipatan) || 1,
          keterangan: formData.keterangan
        });
        toast.success('Record added');
      }
      
      resetForm();
      loadRecords();
      loadExistingDates();
      loadNdpRdpStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save record');
    }
  };

  const handleEdit = (record) => {
    setEditingRecord(record);
    setFormData({
      customer_id: record.customer_id,
      nominal: (record.nominal / 1000).toString(),
      depo_kelipatan: record.depo_kelipatan.toString(),
      keterangan: record.keterangan || ''
    });
    setShowForm(true);
  };

  const handleDelete = async (recordId) => {
    if (!window.confirm('Are you sure you want to delete this record?')) return;
    
    try {
      await api.delete(`/omset/${recordId}`);
      toast.success('Record deleted');
      loadRecords();
      loadExistingDates();
      loadNdpRdpStats();
    } catch (error) {
      toast.error('Failed to delete record');
    }
  };

  const resetForm = () => {
    setFormData({
      customer_id: '',
      nominal: '',
      depo_kelipatan: '1',
      keterangan: ''
    });
    setEditingRecord(null);
    setShowForm(false);
  };

  const handleExport = () => {
    const token = localStorage.getItem('token');
    const params = new URLSearchParams({
      product_id: selectedProduct,
      record_date: selectedDate,
      token: token
    });
    
    // Use hidden iframe to trigger download (bypasses sandbox restrictions)
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/omset/export?${params}`;
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);
    
    // Clean up iframe after download starts
    setTimeout(() => {
      document.body.removeChild(iframe);
    }, 5000);
    
    toast.success('Download starting...');
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('id-ID').format(value);
  };

  const dailyTotal = records.reduce((sum, r) => sum + (r.depo_total || 0), 0);
  const totalForm = records.reduce((sum, r) => sum + (r.depo_kelipatan || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="staff-omset-crm">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">OMSET CRM</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Product</label>
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="select-product"
          >
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Date</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="select-date"
          />
        </div>
        <div className="flex items-end gap-2">
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            className="h-10 px-4 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2 transition-colors"
            data-testid="btn-add-record"
          >
            <Plus size={18} />
            Add Record
          </button>
          <button
            onClick={handleExport}
            className="h-10 px-4 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-2 transition-colors"
            data-testid="btn-export"
          >
            <Download size={18} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Existing Dates Quick Select */}
      {existingDates.length > 0 && (
        <div className="mb-6">
          <p className="text-sm text-slate-600 mb-2">Quick select previous dates:</p>
          <div className="flex flex-wrap gap-2">
            {existingDates.slice(0, 10).map(date => (
              <button
                key={date}
                onClick={() => setSelectedDate(date)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  date === selectedDate 
                    ? 'bg-indigo-600 text-white' 
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {new Date(date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Daily Summary with NDP/RDP */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <Calendar className="text-indigo-600" size={18} />
            <span className="text-xl font-bold text-slate-900">{totalForm}</span>
          </div>
          <p className="text-xs text-slate-600">Total Form</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="text-blue-600" size={18} />
            <span className="text-lg font-bold text-blue-700">{formatCurrency(dailyTotal)}</span>
          </div>
          <p className="text-xs text-slate-600">Total OMSET</p>
        </div>
        
        {/* NDP Stats */}
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 shadow-sm text-white">
          <div className="flex items-center justify-between mb-2">
            <UserPlus className="opacity-80" size={18} />
            <span className="text-xl font-bold">{ndpRdpStats?.ndp_count || 0}</span>
          </div>
          <p className="text-xs text-green-100">NDP (New Depo)</p>
          <p className="text-sm font-semibold mt-1">Rp {formatCurrency(ndpRdpStats?.ndp_total || 0)}</p>
        </div>
        
        {/* RDP Stats */}
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-4 shadow-sm text-white">
          <div className="flex items-center justify-between mb-2">
            <RefreshCw className="opacity-80" size={18} />
            <span className="text-xl font-bold">{ndpRdpStats?.rdp_count || 0}</span>
          </div>
          <p className="text-xs text-orange-100">RDP (Redepo)</p>
          <p className="text-sm font-semibold mt-1">Rp {formatCurrency(ndpRdpStats?.rdp_total || 0)}</p>
        </div>

        {/* Total Unique Customers */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <Package className="text-purple-600" size={18} />
            <span className="text-xl font-bold text-purple-700">
              {(ndpRdpStats?.ndp_count || 0) + (ndpRdpStats?.rdp_count || 0)}
            </span>
          </div>
          <p className="text-xs text-slate-600">Total Customers</p>
        </div>
      </div>

      {/* Add/Edit Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="record-form-modal">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">
                {editingRecord ? 'Edit Record' : 'Add New Record'}
              </h3>
              <button onClick={resetForm} className="text-slate-400 hover:text-slate-600">
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Customer ID *</label>
                <input
                  type="text"
                  value={formData.customer_id}
                  onChange={(e) => setFormData({...formData, customer_id: e.target.value})}
                  className="w-full h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Enter customer ID"
                  data-testid="input-customer-id"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Nominal (dalam ribuan) *</label>
                  <div className="relative">
                    <input
                      type="number"
                      value={formData.nominal}
                      onChange={(e) => setFormData({...formData, nominal: e.target.value})}
                      className="w-full h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="100 = 100.000"
                      data-testid="input-nominal"
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Contoh: 100 = Rp 100.000</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Kelipatan</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.depo_kelipatan}
                    onChange={(e) => setFormData({...formData, depo_kelipatan: e.target.value})}
                    className="w-full h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="1"
                    data-testid="input-kelipatan"
                  />
                </div>
              </div>

              {formData.nominal && (
                <div className="bg-indigo-50 rounded-lg p-3">
                  <p className="text-sm text-indigo-700">
                    Nominal: <span className="font-bold">Rp {formatCurrency((parseFloat(formData.nominal) || 0) * 1000)}</span>
                  </p>
                  <p className="text-sm text-indigo-700">
                    Depo Total: <span className="font-bold">Rp {formatCurrency((parseFloat(formData.nominal) || 0) * 1000 * (parseFloat(formData.depo_kelipatan) || 1))}</span>
                  </p>
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Keterangan</label>
                <textarea
                  value={formData.keterangan}
                  onChange={(e) => setFormData({...formData, keterangan: e.target.value})}
                  className="w-full h-20 px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  placeholder="Notes (optional)"
                  data-testid="input-keterangan"
                />
              </div>
              
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2 transition-colors"
                  data-testid="btn-save-record"
                >
                  <Save size={18} />
                  {editingRecord ? 'Update' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Records Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2">
            <Package className="text-indigo-600" size={18} />
            {products.find(p => p.id === selectedProduct)?.name} - {new Date(selectedDate).toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="omset-records-table">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">No</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Customer ID</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-700">Nominal</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-700">Kelipatan</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-700">Depo Total</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Keterangan</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {records.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                    No records for this date. Click "Add Record" to create one.
                  </td>
                </tr>
              ) : (
                records.map((record, idx) => (
                  <tr key={record.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm text-slate-900">{idx + 1}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${
                        record.record_type === 'NDP' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-orange-100 text-orange-800'
                      }`}>
                        {record.record_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{record.customer_id}</td>
                    <td className="px-4 py-3 text-sm text-right text-slate-900">Rp {formatCurrency(record.nominal)}</td>
                    <td className="px-4 py-3 text-sm text-right text-slate-600">{record.depo_kelipatan}x</td>
                    <td className="px-4 py-3 text-sm text-right font-semibold text-emerald-600">Rp {formatCurrency(record.depo_total)}</td>
                    <td className="px-4 py-3 text-sm text-slate-500">{record.keterangan || '-'}</td>
                    <td className="px-4 py-3 text-sm text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEdit(record)}
                          className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                          data-testid={`btn-edit-${record.id}`}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(record.id)}
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                          data-testid={`btn-delete-${record.id}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            {records.length > 0 && (
              <tfoot className="bg-slate-50 border-t border-slate-200">
                <tr>
                  <td colSpan={3} className="px-4 py-3 text-sm font-semibold text-slate-900">TOTAL</td>
                  <td className="px-4 py-3 text-sm text-right font-bold text-slate-900">{totalForm} Form</td>
                  <td className="px-4 py-3"></td>
                  <td className="px-4 py-3 text-sm text-right font-bold text-emerald-600">Rp {formatCurrency(dailyTotal)}</td>
                  <td colSpan={2}></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex gap-4 text-sm text-slate-600">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">NDP</span>
          <span>= New Depo (Customer baru)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-800">RDP</span>
          <span>= Redepo (Customer lama)</span>
        </div>
      </div>
    </div>
  );
}
