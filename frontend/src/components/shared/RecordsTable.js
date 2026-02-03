import { Search, Check, X, Undo2 } from 'lucide-react';

/**
 * Records Table Component
 * Displays records in a table with filtering and selection
 */
export default function RecordsTable({
  records,
  columns,
  selectedRecords,
  onSelectRecord,
  onSelectAll,
  filterStatus,
  setFilterStatus,
  searchTerm,
  setSearchTerm,
  formatDate,
  onRecallRecords,
  hasAssignedSelected,
  testIdPrefix = 'records'
}) {
  // Filter out sensitive columns
  const HIDDEN_COLUMNS = ['rekening', 'rek', 'bank', 'no_rekening', 'norek', 'account'];
  const visibleColumns = columns.filter(col => 
    !HIDDEN_COLUMNS.some(hidden => col.toLowerCase().includes(hidden.toLowerCase()))
  );

  // Filter records
  const filteredRecords = records.filter(record => {
    if (!record || !record.row_data) return false;
    const matchesStatus = filterStatus === 'all' || record.status === filterStatus;
    const matchesSearch = searchTerm === '' || 
      Object.values(record.row_data || {}).some(val => 
        String(val || '').toLowerCase().includes(searchTerm.toLowerCase())
      );
    return matchesStatus && matchesSearch;
  });

  const handleSelectAll = () => {
    if (selectedRecords.length === filteredRecords.length) {
      onSelectRecord([]);
    } else {
      onSelectRecord(filteredRecords.map(r => r.id));
    }
  };

  const handleToggleRecord = (recordId) => {
    if (selectedRecords.includes(recordId)) {
      onSelectRecord(selectedRecords.filter(id => id !== recordId));
    } else {
      onSelectRecord([...selectedRecords, recordId]);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Filters */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <Search size={16} className="text-slate-400" />
          <input
            type="text"
            placeholder="Search records..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-9 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm w-48"
            data-testid={`${testIdPrefix}-search`}
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="h-9 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
          data-testid={`${testIdPrefix}-status-filter`}
        >
          <option value="all">All Status</option>
          <option value="available">Available</option>
          <option value="assigned">Assigned</option>
        </select>

        {/* Selection actions */}
        {selectedRecords.length > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm text-slate-500">
              {selectedRecords.length} selected
            </span>
            {hasAssignedSelected && (
              <button
                onClick={onRecallRecords}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-sm rounded-lg flex items-center gap-1.5"
                data-testid={`${testIdPrefix}-recall-btn`}
              >
                <Undo2 size={14} />
                Recall
              </button>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-900/50">
            <tr>
              <th className="p-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedRecords.length === filteredRecords.length && filteredRecords.length > 0}
                  onChange={handleSelectAll}
                  className="rounded"
                  data-testid={`${testIdPrefix}-select-all`}
                />
              </th>
              {visibleColumns.slice(0, 5).map(col => (
                <th key={col} className="p-3 text-left font-medium text-slate-700 dark:text-slate-300 whitespace-nowrap">
                  {col}
                </th>
              ))}
              <th className="p-3 text-left font-medium text-slate-700 dark:text-slate-300">Status</th>
              <th className="p-3 text-left font-medium text-slate-700 dark:text-slate-300">Assigned To</th>
              <th className="p-3 text-left font-medium text-slate-700 dark:text-slate-300">Validation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
            {filteredRecords.length === 0 ? (
              <tr>
                <td colSpan={visibleColumns.length + 4} className="p-8 text-center text-slate-500">
                  No records found
                </td>
              </tr>
            ) : (
              filteredRecords.map(record => (
                <tr key={record.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/30">
                  <td className="p-3">
                    <input
                      type="checkbox"
                      checked={selectedRecords.includes(record.id)}
                      onChange={() => handleToggleRecord(record.id)}
                      className="rounded"
                    />
                  </td>
                  {visibleColumns.slice(0, 5).map(col => (
                    <td key={col} className="p-3 text-slate-700 dark:text-slate-300 max-w-[200px] truncate">
                      {String(record.row_data?.[col] ?? '-')}
                    </td>
                  ))}
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      record.status === 'available'
                        ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300'
                        : 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
                    }`}>
                      {record.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-700 dark:text-slate-300">
                    {record.assigned_to_name || '-'}
                  </td>
                  <td className="p-3">
                    {record.validation_status === 'valid' ? (
                      <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                        <Check size={14} /> Valid
                      </span>
                    ) : record.validation_status === 'invalid' ? (
                      <span className="text-red-600 dark:text-red-400 flex items-center gap-1">
                        <X size={14} /> Invalid
                      </span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-700 text-sm text-slate-500">
        Showing {filteredRecords.length} of {records.length} records
      </div>
    </div>
  );
}
