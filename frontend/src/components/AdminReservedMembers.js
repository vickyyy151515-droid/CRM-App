import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { UserPlus, Check, X, Trash2, ArrowRight, Search, Users, Clock, CheckCircle, Package, Upload, FileText, Phone, Copy, RotateCcw, Archive } from 'lucide-react';

export default function AdminReservedMembers({ onUpdate }) {
  const [members, setMembers] = useState([]);
  const [deletedMembers, setDeletedMembers] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active'); // 'active' or 'deleted'
  const [customerId, setCustomerId] = useState('');  // Renamed from customerName
  const [phoneNumber, setPhoneNumber] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [productFilter, setProductFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [moveModal, setMoveModal] = useState({ open: false, member: null });
  const [newStaffId, setNewStaffId] = useState('');
  
  // Bulk add state
  const [showBulkAdd, setShowBulkAdd] = useState(false);
  const [bulkCustomerIds, setBulkCustomerIds] = useState('');  // Renamed from bulkCustomerNames
  const [bulkStaff, setBulkStaff] = useState('');
  const [bulkProduct, setBulkProduct] = useState('');
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [membersRes, staffRes, productsRes, deletedRes] = await Promise.all([
        api.get('/reserved-members'),
        api.get('/staff-users'),
        api.get('/products'),
        api.get('/reserved-members/deleted').catch(() => ({ data: [] }))
      ]);
      setMembers(membersRes.data);
      setStaffList(staffRes.data);
      setProducts(productsRes.data);
      setDeletedMembers(deletedRes.data || []);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!customerId.trim() || !selectedStaff || !selectedProduct) {
      toast.error('Please fill all fields');
      return;
    }

    setSubmitting(true);
    try {
      await api.post('/reserved-members', {
        customer_id: customerId.trim(),
        phone_number: phoneNumber.trim() || null,
        staff_id: selectedStaff,
        product_id: selectedProduct
      });
      toast.success('Customer reserved successfully');
      setCustomerId('');
      setPhoneNumber('');
      setSelectedStaff('');
      setSelectedProduct('');
      loadData();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add reserved member');
    } finally {
      setSubmitting(false);
    }
  };

  const handleBulkAdd = async (e) => {
    e.preventDefault();
    if (!bulkCustomerIds.trim() || !bulkStaff || !bulkProduct) {
      toast.error('Please fill all fields');
      return;
    }

    // Parse customer IDs (one per line)
    const ids = bulkCustomerIds
      .split('\n')
      .map(id => id.trim())
      .filter(id => id.length > 0);

    if (ids.length === 0) {
      toast.error('Please enter at least one customer ID');
      return;
    }

    setBulkSubmitting(true);
    setBulkResult(null);
    try {
      const response = await api.post('/reserved-members/bulk', {
        customer_ids: ids,
        staff_id: bulkStaff,
        product_id: bulkProduct
      });
      
      setBulkResult(response.data);
      
      if (response.data.added_count > 0) {
        toast.success(`Successfully added ${response.data.added_count} reservations`);
        loadData();
        onUpdate?.();
      }
      
      if (response.data.skipped_count > 0) {
        toast.warning(`${response.data.skipped_count} IDs were skipped (duplicates)`);
      }
      
      // Clear the form on success
      if (response.data.added_count > 0) {
        setBulkCustomerIds('');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to bulk add members');
    } finally {
      setBulkSubmitting(false);
    }
  };

  const handleApprove = async (memberId) => {
    try {
      await api.patch(`/reserved-members/${memberId}/approve`);
      toast.success('Request approved');
      loadData();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  const handleReject = async (memberId) => {
    try {
      await api.patch(`/reserved-members/${memberId}/reject`);
      toast.success('Request rejected');
      loadData();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject');
    }
  };

  const handleDelete = async (memberId) => {
    if (!window.confirm('Are you sure you want to delete this reservation?')) return;
    
    try {
      await api.delete(`/reserved-members/${memberId}`);
      toast.success('Reservation deleted');
      loadData();
      onUpdate?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleMove = async () => {
    if (!newStaffId) {
      toast.error('Please select a staff member');
      return;
    }
    
    try {
      await api.patch(`/reserved-members/${moveModal.member.id}/move?new_staff_id=${newStaffId}`);
      toast.success('Reservation moved successfully');
      setMoveModal({ open: false, member: null });
      setNewStaffId('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to move');
    }
  };

  const filteredMembers = members.filter(m => {
    const matchesFilter = filter === 'all' || m.status === filter;
    const matchesProduct = !productFilter || m.product_id === productFilter;
    // Support both customer_id (new) and customer_name (legacy data)
    const customerIdentifier = m.customer_id || m.customer_name || '';
    const matchesSearch = customerIdentifier.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          m.staff_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (m.product_name || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesProduct && matchesSearch;
  });

  const pendingCount = members.filter(m => m.status === 'pending').length;
  const approvedCount = members.filter(m => m.status === 'approved').length;

  // Restore deleted member
  const handleRestoreDeleted = async (memberId) => {
    if (!window.confirm('Restore this member back to active reserved members?')) return;
    try {
      await api.post(`/reserved-members/deleted/${memberId}/restore`);
      toast.success('Member restored successfully');
      loadData();
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore member');
    }
  };

  // Permanently delete archived member
  const handlePermanentDelete = async (memberId) => {
    if (!window.confirm('Permanently delete this archived member? This cannot be undone.')) return;
    try {
      await api.delete(`/reserved-members/deleted/${memberId}`);
      toast.success('Member permanently deleted');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete member');
    }
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  // State for cleanup
  const [runningCleanup, setRunningCleanup] = useState(false);

  // Manually trigger the grace period cleanup
  const handleRunCleanup = async () => {
    if (!window.confirm('Run grace period cleanup now?\n\nThis will:\n- Check all approved reserved members\n- Move members without OMSET past the grace period to "Deleted - No Omset"\n\nContinue?')) {
      return;
    }
    
    setRunningCleanup(true);
    try {
      const response = await api.post('/scheduled-reports/reserved-member-cleanup-run');
      const data = response.data;
      
      // Build detailed message
      let message = `Cleanup completed!\n\n`;
      message += `• Warnings sent: ${data.warnings_sent || 0}\n`;
      message += `• Members removed: ${data.members_removed || 0}`;
      
      if (data.members_removed > 0) {
        toast.success(message);
      } else {
        toast.info(message || 'No members needed to be cleaned up');
      }
      
      // Reload data to reflect changes
      loadData();
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to run cleanup');
    } finally {
      setRunningCleanup(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="admin-reserved-members">
      {/* Header with Title and Action Button */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Reserved Member CRM</h2>
        <button
          onClick={handleRunCleanup}
          disabled={runningCleanup}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300 text-white rounded-lg flex items-center gap-2 transition-colors font-medium"
          data-testid="run-cleanup-btn"
        >
          {runningCleanup ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Running...
            </>
          ) : (
            <>
              <RotateCcw size={18} />
              Run Cleanup Now
            </>
          )}
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Users className="text-indigo-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{members.length}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Total Reservations</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Clock className="text-amber-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{pendingCount}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Pending Requests</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <CheckCircle className="text-emerald-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{approvedCount}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Approved</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <Archive className="text-red-600" size={20} />
            <span className="text-2xl font-bold text-slate-900">{deletedMembers.length}</span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Deleted (No Omset)</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('active')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            activeTab === 'active'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Users size={16} className="inline mr-2" />
          Active Members ({members.length})
        </button>
        <button
          onClick={() => setActiveTab('deleted')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            activeTab === 'deleted'
              ? 'bg-red-600 text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Archive size={16} className="inline mr-2" />
          Deleted - No Omset ({deletedMembers.length})
        </button>
      </div>

      {activeTab === 'active' && (
        <>
          {/* Add New Reservation Form */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm mb-6">
        <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <UserPlus size={20} className="text-indigo-600" />
          Add New Reservation
        </h3>
        <form onSubmit={handleAddMember} className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <input
            type="text"
            placeholder="Customer ID *"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            className="px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            data-testid="input-customer-id"
          />
          <input
            type="text"
            placeholder="Phone Number"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            className="px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            data-testid="input-phone-number"
          />
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            data-testid="select-product"
          >
            <option value="">Select Product *</option>
            {products.map(product => (
              <option key={product.id} value={product.id}>{product.name}</option>
            ))}
          </select>
          <select
            value={selectedStaff}
            onChange={(e) => setSelectedStaff(e.target.value)}
            className="px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            data-testid="select-staff"
          >
            <option value="">Select Staff *</option>
            {staffList.map(staff => (
              <option key={staff.id} value={staff.id}>{staff.name}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={submitting}
            className="md:col-span-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            data-testid="btn-add-reservation"
          >
            <UserPlus size={18} />
            {submitting ? 'Adding...' : 'Add Reservation'}
          </button>
        </form>
      </div>

      {/* Bulk Add Section */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm mb-6 overflow-hidden">
        <button
          onClick={() => setShowBulkAdd(!showBulkAdd)}
          className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          data-testid="btn-toggle-bulk-add"
        >
          <div className="flex items-center gap-3">
            <Upload size={20} className="text-emerald-600" />
            <span className="text-lg font-medium text-slate-900 dark:text-white">Bulk Add Reservations</span>
            <span className="text-sm text-slate-500 dark:text-slate-400">(Add multiple customers at once)</span>
          </div>
          <span className={`transform transition-transform ${showBulkAdd ? 'rotate-180' : ''}`}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </span>
        </button>
        
        {showBulkAdd && (
          <div className="px-6 pb-6 border-t border-slate-200 dark:border-slate-700">
            <div className="pt-4">
              <form onSubmit={handleBulkAdd} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Product
                    </label>
                    <select
                      value={bulkProduct}
                      onChange={(e) => setBulkProduct(e.target.value)}
                      className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                      data-testid="bulk-select-product"
                    >
                      <option value="">Select Product</option>
                      {products.map(product => (
                        <option key={product.id} value={product.id}>{product.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Staff
                    </label>
                    <select
                      value={bulkStaff}
                      onChange={(e) => setBulkStaff(e.target.value)}
                      className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                      data-testid="bulk-select-staff"
                    >
                      <option value="">Select Staff</option>
                      {staffList.map(staff => (
                        <option key={staff.id} value={staff.id}>{staff.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    Customer IDs <span className="text-slate-400 font-normal">(one per line)</span>
                  </label>
                  <textarea
                    value={bulkCustomerIds}
                    onChange={(e) => setBulkCustomerIds(e.target.value)}
                    placeholder="user123&#10;user456&#10;user789&#10;..."
                    rows={8}
                    className="w-full px-4 py-3 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono text-sm resize-y"
                    data-testid="bulk-textarea-ids"
                  />
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {bulkCustomerIds.split('\n').filter(n => n.trim()).length} customer ID(s) entered
                  </p>
                </div>
                
                <div className="flex items-center gap-4">
                  <button
                    type="submit"
                    disabled={bulkSubmitting || !bulkProduct || !bulkStaff || !bulkCustomerIds.trim()}
                    className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                    data-testid="btn-bulk-add"
                  >
                    <Upload size={18} />
                    {bulkSubmitting ? 'Processing...' : 'Bulk Add All'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setBulkCustomerIds('');
                      setBulkResult(null);
                    }}
                    className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </form>
              
              {/* Bulk Add Results */}
              {bulkResult && (
                <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700" data-testid="bulk-result">
                  <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                    <FileText size={16} />
                    Bulk Add Results
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Total Processed:</span>
                      <span className="ml-2 font-semibold text-slate-900 dark:text-white">{bulkResult.total_processed}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Added:</span>
                      <span className="ml-2 font-semibold text-emerald-600">{bulkResult.added_count}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Skipped:</span>
                      <span className="ml-2 font-semibold text-amber-600">{bulkResult.skipped_count}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Staff:</span>
                      <span className="ml-2 font-semibold text-slate-900 dark:text-white">{bulkResult.staff_name}</span>
                    </div>
                  </div>
                  
                  {bulkResult.skipped?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                      <p className="text-xs font-medium text-amber-600 mb-2">Skipped IDs (already reserved):</p>
                      <div className="max-h-32 overflow-y-auto">
                        {bulkResult.skipped.map((item, idx) => (
                          <p key={idx} className="text-xs text-slate-600 dark:text-slate-400">
                            • {item.customer_id} - <span className="text-slate-400">{item.reason}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
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
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="search-reservations"
          />
        </div>
        <select
          value={productFilter}
          onChange={(e) => setProductFilter(e.target.value)}
          className="px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
          data-testid="filter-product"
        >
          <option value="">All Products</option>
          {products.map(product => (
            <option key={product.id} value={product.id}>{product.name}</option>
          ))}
        </select>
        <div className="flex gap-2">
          {['all', 'pending', 'approved'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filter === f 
                  ? 'bg-indigo-600 text-white' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              data-testid={`filter-${f}`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Reservations Table */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full min-w-[1100px]" data-testid="reservations-table">
          <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Customer ID</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Phone</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Product</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Staff</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Last Deposit</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Days Since</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Status</th>
              <th className="text-right px-6 py-4 text-sm font-medium text-slate-600 dark:text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
            {filteredMembers.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-slate-500 dark:text-slate-400">
                  No reservations found
                </td>
              </tr>
            ) : (
              filteredMembers.map(member => (
                <tr key={member.id} className="hover:bg-slate-50 dark:hover:bg-slate-700" data-testid={`reservation-row-${member.id}`}>
                  <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{member.customer_id || member.customer_name}</td>
                  <td className="px-6 py-4">
                    {member.phone_number ? (
                      <div className="flex items-center gap-2">
                        <Phone size={14} className="text-emerald-600" />
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium text-sm">{member.phone_number}</span>
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
                  <td className="px-6 py-4 text-slate-600 dark:text-slate-400">
                    {member.last_omset_date ? formatDate(member.last_omset_date) : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {member.days_since_last_omset !== null && member.days_since_last_omset !== undefined ? (
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                        member.days_since_last_omset > 21 
                          ? 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
                          : member.days_since_last_omset > 14
                          ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300'
                          : 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300'
                      }`}>
                        {member.days_since_last_omset} days
                      </span>
                    ) : (
                      <span className="text-slate-400 text-sm">No deposit</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      member.status === 'approved' 
                        ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300' 
                        : 'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300'
                    }`}>
                      {member.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-600 dark:text-slate-400">{member.created_by_name}</td>
                  <td className="px-6 py-4 text-slate-500 dark:text-slate-400 text-sm">
                    {new Date(member.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {member.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(member.id)}
                            className="p-2 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                            title="Approve"
                            data-testid={`btn-approve-${member.id}`}
                          >
                            <Check size={18} />
                          </button>
                          <button
                            onClick={() => handleReject(member.id)}
                            className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                            title="Reject"
                            data-testid={`btn-reject-${member.id}`}
                          >
                            <X size={18} />
                          </button>
                        </>
                      )}
                      {member.status === 'approved' && (
                        <button
                          onClick={() => setMoveModal({ open: true, member })}
                          className="p-2 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
                          title="Move to another staff"
                          data-testid={`btn-move-${member.id}`}
                        >
                          <ArrowRight size={18} />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(member.id)}
                        className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                        title="Delete"
                        data-testid={`btn-delete-${member.id}`}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

        </>
      )}

      {activeTab === 'deleted' && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-red-50 dark:bg-red-900/20">
            <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Archive size={18} className="text-red-600" />
              Deleted Reserved Members (No Omset)
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              These members were automatically removed because the assigned staff had no OMSET within the grace period.
            </p>
          </div>
          
          {deletedMembers.length === 0 ? (
            <div className="p-8 text-center text-slate-500">
              No deleted members found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase">Customer ID</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase">Staff</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase">Product</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase">Deleted At</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase">Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {deletedMembers.map((member) => (
                    <tr key={member.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3">
                        <span className="font-medium text-slate-900 dark:text-white">
                          {member.customer_id || member.customer_name}
                        </span>
                        {member.phone_number && (
                          <p className="text-xs text-slate-500">{member.phone_number}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
                        {member.staff_name || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-300">
                          {member.product_name || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                        {formatDate(member.deleted_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300">
                          {member.deleted_reason === 'no_omset_grace_period' 
                            ? `No Omset (${member.grace_days_used || 0} days)`
                            : member.deleted_reason || 'No Omset'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleRestoreDeleted(member.id)}
                            className="p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                            title="Restore to Active"
                          >
                            <RotateCcw size={16} />
                          </button>
                          <button
                            onClick={() => handlePermanentDelete(member.id)}
                            className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                            title="Delete Permanently"
                          >
                            <Trash2 size={16} />
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
      )}

      {/* Move Modal */}
      {moveModal.open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="move-modal">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Move Reservation</h3>
            <p className="text-slate-600 mb-4">
              Move <span className="font-medium">{moveModal.member?.customer_id || moveModal.member?.customer_name}</span> to another staff member.
            </p>
            <select
              value={newStaffId}
              onChange={(e) => setNewStaffId(e.target.value)}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white mb-4"
              data-testid="select-new-staff"
            >
              <option value="">Select New Staff</option>
              {staffList.filter(s => s.id !== moveModal.member?.staff_id).map(staff => (
                <option key={staff.id} value={staff.id}>{staff.name}</option>
              ))}
            </select>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setMoveModal({ open: false, member: null }); setNewStaffId(''); }}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                data-testid="btn-cancel-move"
              >
                Cancel
              </button>
              <button
                onClick={handleMove}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                data-testid="btn-confirm-move"
              >
                Move
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
