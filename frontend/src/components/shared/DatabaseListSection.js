import { useState } from 'react';
import { Database, ChevronDown, ChevronUp, Users, Trash2, Edit2, Package, Search, Shuffle, Check, X } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Database List Section Component
 * Renders the list of databases with expandable records
 * Used by AdminDBBonanza and AdminMemberWDCRM
 */
export default function DatabaseListSection({
  api,
  databases,
  loading,
  products,
  staff,
  reservedNames = [],
  moduleType = 'bonanza', // 'bonanza' or 'memberwd'
  onDataRefresh,
  testIdPrefix = 'db'
}) {
  // Local state for expanded database
  const [expandedDb, setExpandedDb] = useState(null);
  const [records, setRecords] = useState([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [selectedRecords, setSelectedRecords] = useState([]);
  const [selectedStaff, setSelectedStaff] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [randomQuantity, setRandomQuantity] = useState('');
  const [editingProduct, setEditingProduct] = useState(null);
  const [newProductId, setNewProductId] = useState('');
  const [columns, setColumns] = useState([]);

  const apiPrefix = moduleType === 'bonanza' ? '/bonanza' : '/memberwd';
  
  const HIDDEN_COLUMNS = ['rekening', 'rek', 'bank', 'no_rekening', 'norek', 'account'];
  const visibleColumns = columns.filter(col => 
    !HIDDEN_COLUMNS.some(hidden => col.toLowerCase().includes(hidden.toLowerCase()))
  );

  // Load records for a database
  const loadRecords = async (databaseId) => {
    if (expandedDb === databaseId) {
      setExpandedDb(null);
      setRecords([]);
      setColumns([]);
      return;
    }

    try {
      setLoadingRecords(true);
      setExpandedDb(databaseId);
      const response = await api.get(`${apiPrefix}/databases/${databaseId}/records`);
      setRecords(response.data);
      // Extract columns from first record
      if (response.data.length > 0) {
        const firstRecord = response.data[0];
        setColumns(Object.keys(firstRecord.row_data || {}));
      }
      setSelectedRecords([]);
    } catch (error) {
      toast.error('Failed to load records');
    } finally {
      setLoadingRecords(false);
    }
  };

  // Delete database
  const handleDelete = async (databaseId) => {
    if (!window.confirm('Are you sure you want to delete this database? All records will be lost.')) return;
    try {
      await api.delete(`${apiPrefix}/databases/${databaseId}`);
      toast.success('Database deleted');
      if (onDataRefresh) onDataRefresh();
    } catch (error) {
      toast.error('Failed to delete database');
    }
  };

  // Edit product
  const handleEditProduct = (databaseId, currentProductId) => {
    setEditingProduct(databaseId);
    setNewProductId(currentProductId || '');
  };

  const handleSaveProduct = async (databaseId) => {
    try {
      await api.patch(`${apiPrefix}/databases/${databaseId}/product`, {
        product_id: newProductId
      });
      toast.success('Product updated');
      setEditingProduct(null);
      if (onDataRefresh) onDataRefresh();
    } catch (error) {
      toast.error('Failed to update product');
    }
  };

  // Record selection
  const toggleSelectRecord = (recordId) => {
    setSelectedRecords(prev => 
      prev.includes(recordId) 
        ? prev.filter(id => id !== recordId)
        : [...prev, recordId]
    );
  };

  const selectAll = () => {
    const availableRecords = filteredRecords.filter(r => r.status === 'available');
    setSelectedRecords(availableRecords.map(r => r.id));
  };

  const clearSelection = () => setSelectedRecords([]);

  // Random selection
  const selectRandom = () => {
    const qty = parseInt(randomQuantity);
    if (!qty || qty < 1) {
      toast.error('Please enter a valid quantity');
      return;
    }
    const availableRecords = filteredRecords.filter(r => r.status === 'available');
    if (qty > availableRecords.length) {
      toast.error(`Only ${availableRecords.length} records available`);
      return;
    }
    const shuffled = [...availableRecords].sort(() => Math.random() - 0.5);
    setSelectedRecords(shuffled.slice(0, qty).map(r => r.id));
    toast.success(`Selected ${qty} random records`);
  };

  // Assign records
  const handleAssign = async () => {
    if (!selectedStaff || selectedRecords.length === 0) {
      toast.error('Please select staff and records');
      return;
    }
    try {
      setAssigning(true);
      await api.post(`${apiPrefix}/assign`, {
        record_ids: selectedRecords,
        staff_id: selectedStaff
      });
      toast.success(`Assigned ${selectedRecords.length} records`);
      setSelectedRecords([]);
      setSelectedStaff('');
      loadRecords(expandedDb);
      if (onDataRefresh) onDataRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign records');
    } finally {
      setAssigning(false);
    }
  };

  // Filter records
  const filteredRecords = records.filter(record => {
    if (filterStatus !== 'all' && record.status !== filterStatus) return false;
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      const rowData = record.row_data || {};
      return Object.values(rowData).some(val => 
        String(val).toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="text-center py-12 text-slate-600 dark:text-slate-400">
        Loading databases...
      </div>
    );
  }

  if (databases.length === 0) {
    return (
      <div className="text-center py-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <Database className="mx-auto text-slate-300 mb-4" size={48} />
        <p className="text-slate-600 dark:text-slate-400">No databases uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {databases.map(database => (
        <div 
          key={database.id} 
          className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden"
        >
          {/* Database Header */}
          <div 
            className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700"
            onClick={() => loadRecords(database.id)}
            data-testid={`${testIdPrefix}-${database.id}`}
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                <Database className="text-indigo-600 dark:text-indigo-400" size={24} />
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 dark:text-white">{database.name}</h4>
                <p className="text-sm text-slate-500">{database.total_records || database.record_count} records</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 flex-wrap">
              {/* Product Badge */}
              {editingProduct === database.id ? (
                <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                  <select
                    value={newProductId}
                    onChange={(e) => setNewProductId(e.target.value)}
                    className="h-8 px-2 text-sm rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  >
                    <option value="">No Product</option>
                    {products.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleSaveProduct(database.id); }}
                    className="p-1.5 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingProduct(null); }}
                    className="p-1.5 bg-slate-500 text-white rounded hover:bg-slate-600"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <div 
                  className="flex items-center gap-1 px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 text-sm rounded-lg cursor-pointer hover:bg-purple-200 dark:hover:bg-purple-900"
                  onClick={(e) => { e.stopPropagation(); handleEditProduct(database.id, database.product_id); }}
                >
                  <Package size={14} />
                  {database.product_name || 'No Product'}
                  <Edit2 size={12} className="ml-1" />
                </div>
              )}
              
              {/* Stats */}
              <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-sm rounded-lg">
                {database.available_count} available
              </span>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-sm rounded-lg">
                {database.assigned_count} assigned
              </span>
              {database.archived_count > 0 && (
                <span className="px-2 py-1 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-sm rounded-lg">
                  {database.archived_count} archived
                </span>
              )}
              {database.excluded_count > 0 && (
                <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-sm rounded-lg">
                  {database.excluded_count} excluded
                </span>
              )}
              
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(database.id); }}
                className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                data-testid={`${testIdPrefix}-delete-${database.id}`}
              >
                <Trash2 size={18} />
              </button>
              {expandedDb === database.id ? <ChevronUp /> : <ChevronDown />}
            </div>
          </div>

          {/* Expanded Records Panel */}
          {expandedDb === database.id && (
            <div className="border-t border-slate-200 dark:border-slate-700 p-4">
              {loadingRecords ? (
                <div className="text-center py-8 text-slate-600 dark:text-slate-400">
                  Loading records...
                </div>
              ) : (
                <>
                  {/* Filter and Action Bar */}
                  <div className="flex flex-wrap items-center gap-3 mb-4">
                    {/* Search */}
                    <div className="relative flex-1 min-w-[200px]">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                      <input
                        type="text"
                        placeholder="Search records..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                      />
                    </div>
                    
                    {/* Status Filter */}
                    <select
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value)}
                      className="h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                    >
                      <option value="all">All Status</option>
                      <option value="available">Available</option>
                      <option value="assigned">Assigned</option>
                      <option value="invalid">Invalid</option>
                    </select>

                    {/* Random Selection */}
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        placeholder="Qty"
                        value={randomQuantity}
                        onChange={(e) => setRandomQuantity(e.target.value)}
                        className="w-20 h-10 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                      />
                      <button
                        onClick={selectRandom}
                        className="h-10 px-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 text-sm"
                      >
                        <Shuffle size={16} />
                        Random
                      </button>
                    </div>

                    {/* Selection Actions */}
                    <button
                      onClick={selectAll}
                      className="h-10 px-3 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-300 dark:hover:bg-slate-600"
                    >
                      Select All Available
                    </button>
                    {selectedRecords.length > 0 && (
                      <button
                        onClick={clearSelection}
                        className="h-10 px-3 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-300 dark:hover:bg-slate-600"
                      >
                        Clear ({selectedRecords.length})
                      </button>
                    )}
                  </div>

                  {/* Assignment Panel */}
                  {selectedRecords.length > 0 && (
                    <div className="mb-4 p-3 bg-indigo-50 dark:bg-indigo-900/30 rounded-lg flex flex-wrap items-center gap-3">
                      <Users size={18} className="text-indigo-600 dark:text-indigo-400" />
                      <span className="text-sm font-medium text-indigo-800 dark:text-indigo-300">
                        {selectedRecords.length} selected
                      </span>
                      <select
                        value={selectedStaff}
                        onChange={(e) => setSelectedStaff(e.target.value)}
                        className="h-9 px-3 rounded border border-indigo-200 dark:border-indigo-700 bg-white dark:bg-slate-800 text-sm flex-1 min-w-[180px]"
                      >
                        <option value="">Select Staff...</option>
                        {staff.map(s => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                      <button
                        onClick={handleAssign}
                        disabled={assigning || !selectedStaff}
                        className="h-9 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
                      >
                        {assigning ? 'Assigning...' : 'Assign'}
                      </button>
                    </div>
                  )}

                  {/* Records Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-slate-50 dark:bg-slate-900/50">
                          <th className="w-10 p-2">
                            <input
                              type="checkbox"
                              checked={selectedRecords.length === filteredRecords.filter(r => r.status === 'available').length && selectedRecords.length > 0}
                              onChange={(e) => e.target.checked ? selectAll() : clearSelection()}
                              className="rounded border-slate-300"
                            />
                          </th>
                          <th className="p-2 text-left font-medium text-slate-600 dark:text-slate-400">Status</th>
                          {visibleColumns.slice(0, 5).map(col => (
                            <th key={col} className="p-2 text-left font-medium text-slate-600 dark:text-slate-400">
                              {col}
                            </th>
                          ))}
                          <th className="p-2 text-left font-medium text-slate-600 dark:text-slate-400">Staff</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                        {filteredRecords.slice(0, 100).map(record => (
                          <tr 
                            key={record.id}
                            className={`hover:bg-slate-50 dark:hover:bg-slate-900/30 ${
                              selectedRecords.includes(record.id) ? 'bg-indigo-50 dark:bg-indigo-900/20' : ''
                            }`}
                          >
                            <td className="p-2">
                              <input
                                type="checkbox"
                                checked={selectedRecords.includes(record.id)}
                                onChange={() => toggleSelectRecord(record.id)}
                                disabled={record.status !== 'available'}
                                className="rounded border-slate-300 disabled:opacity-50"
                              />
                            </td>
                            <td className="p-2">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                record.status === 'available' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300' :
                                record.status === 'assigned' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300' :
                                record.status === 'invalid' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                                'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                              }`}>
                                {record.status}
                              </span>
                            </td>
                            {visibleColumns.slice(0, 5).map(col => (
                              <td key={col} className="p-2 text-slate-700 dark:text-slate-300 max-w-[200px] truncate">
                                {record.row_data?.[col] || '-'}
                              </td>
                            ))}
                            <td className="p-2 text-slate-700 dark:text-slate-300">
                              {record.staff_name || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {filteredRecords.length > 100 && (
                      <div className="text-center py-2 text-sm text-slate-500">
                        Showing first 100 of {filteredRecords.length} records
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
