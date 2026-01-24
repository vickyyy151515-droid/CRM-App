import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { UserPlus, Search, Clock, CheckCircle, Users, Package, Phone, Copy } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function StaffReservedMembers() {
  const { t } = useLanguage();
  const [members, setMembers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [customerId, setCustomerId] = useState('');  // Renamed from customerName
  const [phoneNumber, setPhoneNumber] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [productFilter, setProductFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [membersRes, productsRes] = await Promise.all([
        api.get('/reserved-members'),
        api.get('/products')
      ]);
      setMembers(membersRes.data);
      setProducts(productsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestReservation = async (e) => {
    e.preventDefault();
    if (!customerId.trim()) {
      toast.error('Please enter a customer ID');
      return;
    }
    if (!selectedProduct) {
      toast.error('Please select a product');
      return;
    }
    if (!phoneNumber.trim()) {
      toast.error('Please enter customer phone number');
      return;
    }

    setSubmitting(true);
    try {
      await api.post('/reserved-members', {
        customer_id: customerId.trim(),
        phone_number: phoneNumber.trim(),
        product_id: selectedProduct
      });
      toast.success('Reservation request submitted! Waiting for admin approval.');
      setCustomerId('');
      setPhoneNumber('');
      setSelectedProduct('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  // Get all approved members for display
  const approvedMembers = members.filter(m => m.status === 'approved');
  const pendingMembers = members.filter(m => m.status === 'pending');

  const displayMembers = filter === 'my-requests' ? pendingMembers : approvedMembers.filter(m => {
    // Support both customer_id (new) and customer_name (legacy data)
    const customerIdentifier = m.customer_id || m.customer_name || '';
    const matchesSearch = customerIdentifier.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          m.staff_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (m.product_name || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesProduct = !productFilter || m.product_id === productFilter;
    return matchesSearch && matchesProduct;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="staff-reserved-members">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">Reserved Member CRM</h2>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Users className="text-indigo-600" size={20} />
            <span className="text-2xl font-bold text-slate-900 dark:text-white">{approvedMembers.length}</span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">Total Reserved Customers</p>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Clock className="text-amber-600" size={20} />
            <span className="text-2xl font-bold text-slate-900 dark:text-white">{pendingMembers.length}</span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">My Pending Requests</p>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <CheckCircle className="text-emerald-600" size={20} />
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {approvedMembers.filter(m => m.created_by_name === m.staff_name).length}
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">Self-Requested Approved</p>
        </div>
      </div>

      {/* Request New Reservation Form */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm mb-6">
        <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <UserPlus size={20} className="text-indigo-600" />
          Request New Reservation
        </h3>
        <p className="text-slate-600 dark:text-slate-400 text-sm mb-4">
          Enter the customer details below. Your request will be sent to admin for approval.
        </p>
        <form onSubmit={handleRequestReservation} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Customer ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                placeholder="Enter customer ID"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                data-testid="input-customer-id"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                placeholder="e.g., 081234567890"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                data-testid="input-phone-number"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Product <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedProduct}
                onChange={(e) => setSelectedProduct(e.target.value)}
                className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                data-testid="select-product"
              >
                <option value="">Select Product</option>
                {products.map(product => (
                  <option key={product.id} value={product.id}>{product.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={submitting}
                className="w-full px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                data-testid="btn-request-reservation"
              >
                <UserPlus size={18} />
                {submitting ? 'Submitting...' : 'Request'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search by customer, staff or product..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            data-testid="search-reservations"
          />
        </div>
        <select
          value={productFilter}
          onChange={(e) => setProductFilter(e.target.value)}
          className="px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
          data-testid="filter-product"
        >
          <option value="">All Products</option>
          {products.map(product => (
            <option key={product.id} value={product.id}>{product.name}</option>
          ))}
        </select>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === 'all' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
            }`}
            data-testid="filter-all"
          >
            All Reserved
          </button>
          <button
            onClick={() => setFilter('my-requests')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === 'my-requests' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
            }`}
            data-testid="filter-my-requests"
          >
            My Pending Requests
          </button>
        </div>
      </div>

      {/* Reservations Table */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full" data-testid="reservations-table">
          <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Customer Name</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Phone</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Product</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Reserved By</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Status</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
            {displayMembers.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-slate-500 dark:text-slate-400">
                  {filter === 'my-requests' ? 'No pending requests' : 'No reservations found'}
                </td>
              </tr>
            ) : (
              displayMembers.map(member => (
                <tr key={member.id} className="hover:bg-slate-50 dark:hover:bg-slate-700" data-testid={`reservation-row-${member.id}`}>
                  <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{member.customer_id || member.customer_name}</td>
                  <td className="px-6 py-4">
                    {member.phone_number ? (
                      <div className="flex items-center gap-2">
                        <Phone size={14} className="text-emerald-600" />
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">{member.phone_number}</span>
                        <button
                          onClick={() => {
                            let phoneNum = member.phone_number;
                            if (phoneNum.includes('wa.me/')) {
                              phoneNum = phoneNum.split('wa.me/')[1].split('?')[0];
                            }
                            phoneNum = phoneNum.replace(/[^\d+]/g, '');
                            const whatsappUrl = `https://wa.me/${phoneNum}`;
                            navigator.clipboard.writeText(whatsappUrl).then(() => {
                              toast.success('WhatsApp link copied!');
                            }).catch(() => {
                              toast.error('Failed to copy');
                            });
                          }}
                          className="p-1 text-emerald-600 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 rounded transition-colors"
                          title="Copy WhatsApp link"
                          data-testid={`copy-phone-${member.id}`}
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                    ) : (
                      <span className="text-slate-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300">
                      <Package size={12} className="mr-1" />
                      {member.product_name || 'Unknown'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-600 dark:text-slate-400">{member.staff_name}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      member.status === 'approved' 
                        ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300' 
                        : 'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300'
                    }`}>
                      {member.status === 'approved' ? 'Reserved' : 'Pending Approval'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500 dark:text-slate-400 text-sm">
                    {new Date(member.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
        <p className="text-blue-800 dark:text-blue-300 text-sm">
          <strong>Note:</strong> All approved reserved customers are visible to all staff members. 
          If you try to request a customer that's already reserved by another staff in the same product, 
          the system will notify you.
        </p>
      </div>
    </div>
  );
}
