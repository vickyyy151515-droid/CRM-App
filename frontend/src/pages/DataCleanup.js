/**
 * DataCleanup - Admin page to clean up orphaned records from deleted users
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Trash2, RefreshCw, AlertTriangle, Database, User, 
  DollarSign, Calendar, CheckCircle, XCircle, Search
} from 'lucide-react';

export default function DataCleanup() {
  const [loading, setLoading] = useState(true);
  const [staffRecords, setStaffRecords] = useState([]);
  const [deletingId, setDeletingId] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all'); // all, orphaned, active

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/staff-record-summary');
      setStaffRecords(response.data.staff_records || []);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load staff record summary');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDeleteRecords = async (staffId, staffName) => {
    const confirmMsg = `Are you sure you want to DELETE ALL RECORDS for "${staffName}"?\n\nThis will permanently remove:\n- All OMSET records\n- All DB Bonanza records\n- All Member WD records\n- All attendance records\n\nThis action CANNOT be undone!`;
    
    if (!window.confirm(confirmMsg)) {
      return;
    }

    // Double confirmation for safety
    const doubleConfirm = window.prompt(`Type "${staffName}" to confirm deletion:`);
    if (doubleConfirm !== staffName) {
      toast.error('Deletion cancelled - name did not match');
      return;
    }

    setDeletingId(staffId);
    try {
      const response = await api.delete(`/admin/staff-records/${staffId}`);
      toast.success(`Deleted ${response.data.deleted.omset_records} OMSET, ${response.data.deleted.bonanza_records} Bonanza, ${response.data.deleted.memberwd_records} Member WD records`);
      loadData(); // Refresh the list
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete records');
    } finally {
      setDeletingId(null);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  // Filter staff records
  const filteredRecords = staffRecords.filter(record => {
    const matchesSearch = 
      record.staff_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.staff_id?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilter = 
      filterType === 'all' ||
      (filterType === 'orphaned' && !record.user_exists) ||
      (filterType === 'active' && record.user_exists);
    
    return matchesSearch && matchesFilter;
  });

  const orphanedCount = staffRecords.filter(r => !r.user_exists).length;
  const orphanedRecords = staffRecords.filter(r => !r.user_exists).reduce((sum, r) => sum + r.omset_count, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="data-cleanup">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Cleanup</h1>
          <p className="text-slate-600 dark:text-slate-400">Remove records from deleted or test users</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
          data-testid="refresh-btn"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {/* Warning Banner */}
      {orphanedCount > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-amber-600 shrink-0 mt-0.5" size={24} />
            <div>
              <h3 className="font-semibold text-amber-800 dark:text-amber-400">Orphaned Records Found</h3>
              <p className="text-amber-700 dark:text-amber-300 text-sm mt-1">
                Found <strong>{orphanedCount} staff</strong> with <strong>{orphanedRecords} records</strong> whose user accounts no longer exist.
                These records may be from deleted users or test accounts.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            placeholder="Search by name, email, or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            data-testid="search-input"
          />
        </div>
        <div className="flex gap-2">
          {[
            { value: 'all', label: 'All Staff' },
            { value: 'orphaned', label: `Orphaned (${orphanedCount})`, danger: true },
            { value: 'active', label: 'Active Users' }
          ].map(filter => (
            <button
              key={filter.value}
              onClick={() => setFilterType(filter.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === filter.value
                  ? filter.danger 
                    ? 'bg-red-600 text-white'
                    : 'bg-indigo-600 text-white'
                  : filter.danger
                    ? 'bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300'
              }`}
              data-testid={`filter-${filter.value}`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* Staff Records Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="staff-records-table">
            <thead className="bg-slate-50 dark:bg-slate-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Staff</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Status</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-700 dark:text-slate-300">OMSET Records</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-700 dark:text-slate-300">Total Nominal</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Date Range</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-700 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {filteredRecords.map((record) => (
                <tr 
                  key={record.staff_id} 
                  className={`hover:bg-slate-50 dark:hover:bg-slate-700/50 ${
                    !record.user_exists ? 'bg-red-50/50 dark:bg-red-900/10' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        record.user_exists 
                          ? 'bg-emerald-100 dark:bg-emerald-900/30' 
                          : 'bg-red-100 dark:bg-red-900/30'
                      }`}>
                        <User className={record.user_exists ? 'text-emerald-600' : 'text-red-600'} size={18} />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white">{record.staff_name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {record.user_email || <span className="text-red-500">No user account</span>}
                        </p>
                        <p className="text-xs text-slate-400 font-mono">{record.staff_id.slice(0, 20)}...</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {record.user_exists ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 rounded-full text-xs font-medium">
                        <CheckCircle size={12} />
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-full text-xs font-medium">
                        <XCircle size={12} />
                        Orphaned
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex items-center gap-1 text-slate-900 dark:text-white font-medium">
                      <Database size={14} className="text-slate-400" />
                      {record.omset_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                      <DollarSign size={14} />
                      {formatCurrency(record.total_nominal)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300">
                      <Calendar size={14} className="text-slate-400" />
                      {record.first_record || 'N/A'} - {record.last_record || 'N/A'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleDeleteRecords(record.staff_id, record.staff_name)}
                      disabled={deletingId === record.staff_id}
                      className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        record.user_exists
                          ? 'bg-amber-100 hover:bg-amber-200 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                          : 'bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}
                      data-testid={`delete-${record.staff_id}`}
                    >
                      {deletingId === record.staff_id ? (
                        <RefreshCw className="animate-spin" size={14} />
                      ) : (
                        <Trash2 size={14} />
                      )}
                      Delete Records
                    </button>
                  </td>
                </tr>
              ))}
              
              {filteredRecords.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                    {searchTerm || filterType !== 'all' 
                      ? 'No records match your filters' 
                      : 'No staff records found'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
        <h3 className="font-semibold text-blue-800 dark:text-blue-400 mb-2">About Data Cleanup</h3>
        <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
          <li>• <strong>Orphaned records</strong> are from users whose accounts have been deleted</li>
          <li>• <strong>Deleting records</strong> will remove ALL OMSET, DB Bonanza, and Member WD entries for that staff</li>
          <li>• This action is <strong>permanent</strong> and cannot be undone</li>
          <li>• Records from active users can also be deleted if needed (e.g., test data)</li>
        </ul>
      </div>
    </div>
  );
}
