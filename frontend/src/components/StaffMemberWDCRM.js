import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Gift, FileSpreadsheet, Calendar } from 'lucide-react';

export default function StaffMemberWDCRM() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadRecords();
  }, []);

  const loadRecords = async () => {
    try {
      const response = await api.get('/memberwd/staff/records');
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load records');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Group records by database
  const groupedRecords = records.reduce((acc, record) => {
    const dbName = record.database_name;
    if (!acc[dbName]) {
      acc[dbName] = [];
    }
    acc[dbName].push(record);
    return acc;
  }, {});

  // Filter records
  const filteredGroupedRecords = Object.entries(groupedRecords).reduce((acc, [dbName, dbRecords]) => {
    const filtered = dbRecords.filter(record => 
      searchTerm === '' || 
      Object.values(record.row_data).some(val => 
        String(val).toLowerCase().includes(searchTerm.toLowerCase())
      )
    );
    if (filtered.length > 0) {
      acc[dbName] = filtered;
    }
    return acc;
  }, {});

  const columns = records.length > 0 ? Object.keys(records[0].row_data) : [];

  return (
    <div data-testid="staff-db-memberwd">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">DB MemberWD</h2>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search records..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full max-w-md h-10 px-4 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid="memberwd-search"
        />
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading your records...</div>
      ) : records.length === 0 ? (
        <div className="text-center py-12 bg-white border border-slate-200 rounded-xl">
          <Gift className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600">No MemberWD records assigned to you yet</p>
          <p className="text-sm text-slate-500 mt-2">Admin will assign records to you when available</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(filteredGroupedRecords).map(([dbName, dbRecords]) => (
            <div key={dbName} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                      <FileSpreadsheet className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{dbName}</h3>
                      <p className="text-sm text-slate-500">{dbRecords.length} records assigned to you</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-sm text-slate-500">
                    <Calendar size={14} />
                    Assigned: {formatDate(dbRecords[0]?.assigned_at)}
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">#</th>
                      {columns.map(col => (
                        <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-slate-700">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dbRecords.map(record => (
                      <tr key={record.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-900 font-medium">{record.row_number}</td>
                        {columns.map(col => (
                          <td key={col} className="px-4 py-3 text-sm text-slate-700">{record.row_data[col] || '-'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
