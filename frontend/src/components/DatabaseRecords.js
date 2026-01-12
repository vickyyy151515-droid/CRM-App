import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { User, CheckSquare, Square } from 'lucide-react';

export default function DatabaseRecords({ database, isStaff, onRequestSuccess }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [requestCount, setRequestCount] = useState('');
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    loadRecords();
  }, [database.id]);

  const loadRecords = async () => {
    try {
      const response = await api.get(`/databases/${database.id}/records`);
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load customer records');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRecord = (recordId) => {
    // Removed - staff cannot select specific records
  };

  const handleSelectAll = () => {
    // Removed - staff cannot select specific records
  };

  const handleRequest = async () => {
    const count = parseInt(requestCount);
    if (!count || count <= 0) {
      toast.error('Please enter a valid number');
      return;
    }

    if (count > availableCount) {
      toast.error(`Only ${availableCount} records available`);
      return;
    }

    setRequesting(true);
    try {
      await api.post('/download-requests', {
        database_id: database.id,
        record_count: count
      });
      toast.success(`Requested ${count} customer records!`);
      setRequestCount('');
      loadRecords();
      onRequestSuccess?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    } finally {
      setRequesting(false);
    }
  };

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

  const availableCount = records.filter(r => r.status === 'available').length;
  const requestedCount = records.filter(r => r.status === 'requested').length;
  const assignedCount = records.filter(r => r.status === 'assigned').length;

  if (loading) {
    return <div className="text-center py-8">Loading customer records...</div>;
  }

  const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">Customer Records</h3>
          <p className="text-sm text-slate-600 mt-1">
            {availableCount} available • {requestedCount} requested • {assignedCount} assigned
          </p>
        </div>
        {isStaff && availableCount > 0 && (
          <div className="flex gap-2">
            <button
              onClick={handleSelectAll}
              data-testid="select-all-records"
              className="text-slate-600 hover:bg-slate-100 hover:text-slate-900 px-4 py-2 rounded-md transition-colors text-sm"
            >
              {selectedRecords.length === availableCount ? 'Deselect All' : 'Select All Available'}
            </button>
            <button
              onClick={handleRequest}
              disabled={requesting || selectedRecords.length === 0}
              data-testid="request-selected-records"
              className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              Request {selectedRecords.length > 0 && `(${selectedRecords.length})`}
            </button>
          </div>
        )}
      </div>

      {records.length === 0 ? (
        <div className="text-center py-8 text-slate-600">No customer records found</div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full" data-testid="customer-records-table">
              <thead className="bg-slate-50">
                <tr>
                  {isStaff && <th className="px-4 py-3 text-left w-12"></th>}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">#</th>
                  {columns.map((col, idx) => (
                    <th key={idx} className="px-4 py-3 text-left text-xs font-semibold text-slate-700">
                      {col}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Status</th>
                  {!isStaff && <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Assigned To</th>}
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr
                    key={record.id}
                    className="border-b border-slate-100 hover:bg-slate-50"
                    data-testid={`record-row-${record.id}`}
                  >
                    {isStaff && (
                      <td className="px-4 py-3">
                        {record.status === 'available' && (
                          <button
                            onClick={() => handleSelectRecord(record.id)}
                            data-testid={`select-record-${record.id}`}
                            className="text-slate-600 hover:text-slate-900"
                          >
                            {selectedRecords.includes(record.id) ? (
                              <CheckSquare size={18} className="text-indigo-600" />
                            ) : (
                              <Square size={18} />
                            )}
                          </button>
                        )}
                      </td>
                    )}
                    <td className="px-4 py-3 text-sm text-slate-900 font-medium">{record.row_number}</td>
                    {columns.map((col, idx) => (
                      <td key={idx} className="px-4 py-3 text-sm text-slate-900">
                        {record.row_data[col] || '-'}
                      </td>
                    ))}
                    <td className="px-4 py-3 text-sm">{getStatusBadge(record.status)}</td>
                    {!isStaff && (
                      <td className="px-4 py-3 text-sm text-slate-600">
                        {record.assigned_to_name || '-'}
                      </td>
                    )}
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