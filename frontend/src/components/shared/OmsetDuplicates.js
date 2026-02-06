import { useState, useEffect, useCallback } from 'react';
import { api } from '../../App';
import { toast } from 'sonner';
import { Copy, Users, ChevronDown, ChevronUp, Package } from 'lucide-react';

export default function OmsetDuplicates() {
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [expandedRows, setExpandedRows] = useState({});

  const loadDuplicates = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const res = await api.get('/omset/duplicates', { params });
      setDuplicates(res.data.duplicates || []);
      setTotalRecords(res.data.total_records_involved || 0);
    } catch (err) {
      toast.error('Failed to load duplicates');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => { loadDuplicates(); }, [loadDuplicates]);

  const toggleRow = (idx) => setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));

  return (
    <div>
      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Start Date</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">End Date</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm" />
          </div>
          <button onClick={() => { setStartDate(''); setEndDate(''); }} className="px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">Clear (All Time)</button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-orange-100 dark:bg-orange-900/50 flex items-center justify-center">
            <Copy className="text-orange-600" size={20} />
          </div>
          <div>
            <p className="text-sm text-slate-500">Duplicate Groups</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">{duplicates.length}</p>
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
            <Users className="text-blue-600" size={20} />
          </div>
          <div>
            <p className="text-sm text-slate-500">Records Involved</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalRecords}</p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading duplicates...</div>
      ) : duplicates.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <Copy className="mx-auto text-slate-300 dark:text-slate-600 mb-3" size={48} />
          <p className="text-slate-600 dark:text-slate-400 font-medium">No duplicates found</p>
          <p className="text-sm text-slate-500 mt-1">No customers recorded by multiple staff for the same product</p>
        </div>
      ) : (
        <div className="space-y-3">
          {duplicates.map((dup, idx) => (
            <div key={idx} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <button onClick={() => toggleRow(idx)} className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/50 flex items-center justify-center">
                    <Copy size={14} className="text-orange-600" />
                  </div>
                  <div className="text-left">
                    <p className="font-semibold text-slate-900 dark:text-white">{dup.customer_id}</p>
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <Package size={12} /> {dup.product_name}
                      <span className="mx-1">•</span>
                      <Users size={12} /> {dup.staff_count} staff: {dup.staff_names.join(', ')}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{dup.total_records} records</p>
                    <p className="text-xs text-slate-500">Rp {(dup.total_depo || 0).toLocaleString('id-ID')}</p>
                  </div>
                  {expandedRows[idx] ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
                </div>
              </button>
              {expandedRows[idx] && (
                <div className="border-t border-slate-100 dark:border-slate-700">
                  <table className="min-w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900/50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-slate-600">Staff</th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-slate-600">Date</th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-slate-600">Customer</th>
                        <th className="px-4 py-2 text-right text-xs font-semibold text-slate-600">Depo</th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-slate-600">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                      {dup.records.map((r, ri) => (
                        <tr key={ri} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                          <td className="px-4 py-2 text-sm font-medium text-slate-900 dark:text-white">{r.staff_name}</td>
                          <td className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300">{r.record_date}</td>
                          <td className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300">{r.customer_id}</td>
                          <td className="px-4 py-2 text-sm text-right text-slate-600 dark:text-slate-300">Rp {(r.depo_total || 0).toLocaleString('id-ID')}</td>
                          <td className="px-4 py-2 text-sm text-slate-500 truncate max-w-[200px]">{r.keterangan || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
