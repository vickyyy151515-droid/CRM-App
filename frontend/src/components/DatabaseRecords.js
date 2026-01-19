import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { User } from 'lucide-react';

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
  
  // Filter out sensitive columns for staff users
  const HIDDEN_COLUMNS_FOR_STAFF = ['rekening', 'rek', 'bank', 'no_rekening', 'norek', 'account'];
  const visibleColumns = isStaff 
    ? columns.filter(col => !HIDDEN_COLUMNS_FOR_STAFF.some(hidden => col.toLowerCase().includes(hidden.toLowerCase())))
    : columns;

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
          <div className="flex gap-3 items-center">
            <div className="flex items-center gap-2">
              <label htmlFor="request-count" className="text-sm font-medium text-slate-700">
                Request:
              </label>
              <input
                id="request-count"
                type="number"
                min="1"
                max={availableCount}
                value={requestCount}
                onChange={(e) => setRequestCount(e.target.value)}
                placeholder="Enter number"
                data-testid="request-count-input"
                className="w-32 h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              />
              <span className="text-sm text-slate-600">of {availableCount}</span>
            </div>
            <button
              onClick={handleRequest}
              disabled={requesting || !requestCount}
              data-testid="submit-request-button"
              className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2.5 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {requesting ? 'Submitting...' : 'Submit Request'}
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
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">#</th>
                  {visibleColumns.map((col, idx) => (
                    <th key={idx} className="px-4 py-3 text-left text-xs font-semibold text-slate-700">
                      {col}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Status</th>
                  {!isStaff && <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Assigned To</th>}
                  {!isStaff && <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">WhatsApp Status</th>}
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr
                    key={record.id}
                    className="border-b border-slate-100 hover:bg-slate-50"
                    data-testid={`record-row-${record.id}`}
                  >
                    <td className="px-4 py-3 text-sm text-slate-900 font-medium">{record.row_number}</td>
                    {visibleColumns.map((col, idx) => {
                      const cellValue = record.row_data[col];
                      const isWhatsAppColumn = col.toLowerCase() === 'telpon';
                      
                      if (isWhatsAppColumn && cellValue) {
                        // Extract phone number from wa.me link or use as-is
                        let phoneNumber = cellValue;
                        if (cellValue.includes('wa.me/')) {
                          phoneNumber = cellValue.split('wa.me/')[1].split('?')[0];
                        }
                        // Remove any non-digit characters except +
                        phoneNumber = phoneNumber.replace(/[^\d+]/g, '');
                        
                        const whatsappUrl = `https://wa.me/${phoneNumber}`;
                        
                        const handleCopy = (e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          
                          // Create a temporary textarea to copy from
                          const textarea = document.createElement('textarea');
                          textarea.value = whatsappUrl;
                          textarea.style.position = 'fixed';
                          textarea.style.opacity = '0';
                          document.body.appendChild(textarea);
                          textarea.select();
                          
                          try {
                            document.execCommand('copy');
                            toast.success('WhatsApp link copied! Paste in browser address bar');
                          } catch (err) {
                            toast.error('Failed to copy');
                          } finally {
                            document.body.removeChild(textarea);
                          }
                        };
                        
                        return (
                          <td key={idx} className="px-4 py-3 text-sm">
                            <div className="flex items-center gap-2">
                              <span className="text-slate-900 font-medium">{phoneNumber}</span>
                              <button
                                onClick={handleCopy}
                                data-testid={`copy-number-${record.id}`}
                                title="Copy WhatsApp link"
                                className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 p-1.5 rounded transition-colors"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                              </button>
                            </div>
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
                    {!isStaff && (
                      <td className="px-4 py-3 text-sm text-slate-600">
                        {record.assigned_to_name || '-'}
                      </td>
                    )}
                    {!isStaff && (
                      <td className="px-4 py-3 text-sm">
                        {record.whatsapp_status === 'ada' && (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Ada
                          </span>
                        )}
                        {record.whatsapp_status === 'ceklis1' && (
                          <span className="inline-flex items-center gap-1 text-amber-600 font-medium">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clipRule="evenodd" />
                            </svg>
                            Ceklis 1
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