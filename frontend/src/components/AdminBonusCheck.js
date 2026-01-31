import { useState, useEffect } from 'react';
import { Gift, Download, Calendar, Users, Package, RefreshCw, FileSpreadsheet, FileText, Search, Filter } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../App';

export default function AdminBonusCheck() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [staffList, setStaffList] = useState([]);
  const [products, setProducts] = useState([]);
  const [summary, setSummary] = useState({ total: 0, by_staff: [] });
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadStaffList();
    loadProducts();
    // Set default month to current month
    const now = new Date();
    setSelectedMonth(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
  }, []);

  useEffect(() => {
    if (selectedMonth) {
      loadSubmissions();
    }
  }, [selectedMonth, selectedStaff, selectedProduct]);

  const loadStaffList = async () => {
    try {
      const response = await api.get('/bonus-check/admin/staff-list');
      setStaffList(response.data);
    } catch (error) {
      console.error('Failed to load staff list:', error);
    }
  };

  const loadProducts = async () => {
    try {
      const response = await api.get('/bonus-check/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  };

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      const params = { month: selectedMonth };
      if (selectedStaff) params.staff_id = selectedStaff;
      if (selectedProduct) params.product_id = selectedProduct;
      
      const response = await api.get('/bonus-check/admin/all', { params });
      setSubmissions(response.data.submissions || []);
      setSummary({
        total: response.data.total || 0,
        by_staff: response.data.by_staff || []
      });
    } catch (error) {
      console.error('Failed to load submissions:', error);
      toast.error('Gagal memuat data submissions');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const params = { month: selectedMonth, format };
      if (selectedStaff) params.staff_id = selectedStaff;
      if (selectedProduct) params.product_id = selectedProduct;
      
      const response = await api.get('/bonus-check/admin/export', {
        params,
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bonus_check_${selectedMonth}.${format === 'csv' ? 'csv' : 'xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Export ${format.toUpperCase()} berhasil`);
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Gagal export data');
    } finally {
      setExporting(false);
    }
  };

  const getMonthOptions = () => {
    const options = [];
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const label = date.toLocaleDateString('id-ID', { year: 'numeric', month: 'long' });
      options.push({ value, label });
    }
    return options;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
              <Gift className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Customer Bonus Check</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Lihat dan export data submission cek bonus dari staff
              </p>
            </div>
          </div>
          
          {/* Export Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting || submissions.length === 0}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
              data-testid="export-csv-btn"
            >
              <FileText size={18} />
              Export CSV
            </button>
            <button
              onClick={() => handleExport('excel')}
              disabled={exporting || submissions.length === 0}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
              data-testid="export-excel-btn"
            >
              <FileSpreadsheet size={18} />
              Export Excel
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <Gift className="text-amber-600 dark:text-amber-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Total Submissions</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
              <Users className="text-indigo-600 dark:text-indigo-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Staff Aktif</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.by_staff.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <Calendar className="text-emerald-600 dark:text-emerald-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Periode</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">
                {getMonthOptions().find(m => m.value === selectedMonth)?.label || '-'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm mb-6">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Filter size={16} />
            Filter Data
          </h2>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                Bulan
              </label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-white"
                data-testid="month-filter"
              >
                {getMonthOptions().map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                Staff
              </label>
              <select
                value={selectedStaff}
                onChange={(e) => setSelectedStaff(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-white"
                data-testid="staff-filter"
              >
                <option value="">Semua Staff</option>
                {staffList.map(staff => (
                  <option key={staff.id} value={staff.id}>{staff.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                Produk
              </label>
              <select
                value={selectedProduct}
                onChange={(e) => setSelectedProduct(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-white"
                data-testid="product-filter"
              >
                <option value="">Semua Produk</option>
                {products.map(product => (
                  <option key={product.id} value={product.id}>{product.name}</option>
                ))}
              </select>
            </div>
            
            <div className="flex items-end">
              <button
                onClick={loadSubmissions}
                className="w-full px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Staff Summary */}
      {summary.by_staff.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm mb-6">
          <div className="p-4 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Users size={16} />
              Ringkasan per Staff
            </h2>
          </div>
          <div className="p-4">
            <div className="flex flex-wrap gap-2">
              {summary.by_staff.map(staff => (
                <div
                  key={staff.staff_id}
                  className="px-3 py-2 bg-slate-100 dark:bg-slate-700 rounded-lg flex items-center gap-2"
                >
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {staff.staff_name}
                  </span>
                  <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs font-semibold rounded-full">
                    {staff.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Submissions Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Search size={18} />
            Daftar Submissions
            {submissions.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-sm rounded-full">
                {submissions.length}
              </span>
            )}
          </h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
            Loading submissions...
          </div>
        ) : submissions.length === 0 ? (
          <div className="p-12 text-center">
            <Gift size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
            <h4 className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-1">Belum ada submission</h4>
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Belum ada staff yang submit cek bonus untuk periode ini
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="submissions-table">
              <thead className="bg-slate-50 dark:bg-slate-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">No</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Customer ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Produk</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Staff</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Tanggal Submit</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {submissions.map((sub, idx) => (
                  <tr key={sub.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                      {idx + 1}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">
                      {sub.customer_id}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                      <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-xs">
                        {sub.product_name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                      {sub.staff_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                      {new Date(sub.submitted_at).toLocaleString('id-ID')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-xs rounded-full">
                        Submitted
                      </span>
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
}
