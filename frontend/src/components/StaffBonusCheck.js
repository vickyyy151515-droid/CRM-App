import { useState, useEffect } from 'react';
import { Search, Gift, CheckCircle, XCircle, Calendar, Package, User, RefreshCw, Clock } from 'lucide-react';
import { toast } from 'sonner';
import api from '../api';

export default function StaffBonusCheck() {
  const [customerId, setCustomerId] = useState('');
  const [productId, setProductId] = useState('');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submissions, setSubmissions] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState('');

  useEffect(() => {
    loadProducts();
    loadSubmissions();
    // Set default month to current month
    const now = new Date();
    setSelectedMonth(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
  }, []);

  useEffect(() => {
    if (selectedMonth) {
      loadSubmissions();
    }
  }, [selectedMonth]);

  const loadProducts = async () => {
    try {
      const response = await api.get('/bonus-check/products');
      setProducts(response.data);
      if (response.data.length > 0) {
        setProductId(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  };

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      const response = await api.get('/bonus-check/my-submissions', {
        params: { month: selectedMonth }
      });
      setSubmissions(response.data.submissions || []);
    } catch (error) {
      console.error('Failed to load submissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!customerId.trim()) {
      toast.error('Masukkan ID Customer');
      return;
    }
    
    if (!productId) {
      toast.error('Pilih produk');
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post('/bonus-check/submit', {
        customer_id: customerId.trim(),
        product_id: productId
      });
      
      if (response.data.success) {
        toast.success(response.data.message);
        setCustomerId('');
        loadSubmissions();
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal submit cek bonus');
    } finally {
      setSubmitting(false);
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
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
            <Gift className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Cek Bonus Member</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Submit customer untuk pengecekan bonus bulanan
            </p>
          </div>
        </div>
      </div>

      {/* Submit Form */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm mb-6">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Search size={20} />
            Submit Cek Bonus
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Masukkan ID customer yang ingin dicek bonus-nya. Customer harus ada di daftar Reserved Member Anda.
          </p>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                <User size={14} className="inline mr-1" />
                ID Customer
              </label>
              <input
                type="text"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="Masukkan ID Customer"
                className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-slate-900 dark:text-white placeholder-slate-400"
                data-testid="customer-id-input"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                <Package size={14} className="inline mr-1" />
                Produk
              </label>
              <select
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-slate-900 dark:text-white"
                data-testid="product-select"
              >
                {products.map(product => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="flex items-end">
              <button
                type="submit"
                disabled={submitting}
                className="w-full px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-medium rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="submit-bonus-check-btn"
              >
                {submitting ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" />
                    Memproses...
                  </>
                ) : (
                  <>
                    <CheckCircle size={18} />
                    Submit Cek Bonus
                  </>
                )}
              </button>
            </div>
          </div>
          
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <strong>Catatan:</strong> Customer harus sudah ada di daftar Reserved Member Anda dan belum expired (30 hari sejak approval).
              Setiap customer hanya bisa disubmit 1x per bulan.
            </p>
          </div>
        </form>
      </div>

      {/* Submissions List */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Calendar size={20} />
              Riwayat Submission
            </h2>
            <div className="flex items-center gap-3">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-white"
                data-testid="month-filter"
              >
                {getMonthOptions().map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <button
                onClick={loadSubmissions}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw size={18} className={`text-slate-500 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            Loading submissions...
          </div>
        ) : submissions.length === 0 ? (
          <div className="p-12 text-center">
            <Gift size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
            <h4 className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-1">Belum ada submission</h4>
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Submit customer untuk cek bonus di form di atas
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 dark:bg-slate-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">No</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Customer ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Produk</th>
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
                      {sub.product_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                      <div className="flex items-center gap-1">
                        <Clock size={14} />
                        {new Date(sub.submitted_at).toLocaleString('id-ID')}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-xs rounded-full">
                        <CheckCircle size={12} />
                        Submitted
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        
        {submissions.length > 0 && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Total: <span className="font-semibold text-slate-900 dark:text-white">{submissions.length}</span> submission bulan ini
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
