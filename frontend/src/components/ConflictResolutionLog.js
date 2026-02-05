import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  RefreshCw, 
  AlertTriangle, 
  Users,
  Calendar,
  Database,
  ChevronLeft,
  ChevronRight,
  Filter,
  Download,
  TrendingUp,
  Clock
} from 'lucide-react';

export default function ConflictResolutionLog() {
  const [logData, setLogData] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [pageSize] = useState(20);
  const [filterStaff, setFilterStaff] = useState('');
  const [staffList, setStaffList] = useState([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        skip: (page * pageSize).toString()
      });
      
      if (filterStaff) {
        params.append('staff_id', filterStaff);
      }

      const [logRes, statsRes, staffRes] = await Promise.all([
        api.get(`/data-sync/conflict-resolution-log?${params}`),
        api.get('/data-sync/conflict-resolution-stats'),
        api.get('/users').catch(() => ({ data: [] }))
      ]);
      
      setLogData(logRes.data);
      setStats(statsRes.data);
      setStaffList(staffRes.data.filter(u => u.role === 'staff') || []);
    } catch (error) {
      console.error('Error loading conflict resolution log:', error);
      toast.error('Failed to load conflict resolution log');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filterStaff]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSourceBadgeColor = (source) => {
    switch (source) {
      case 'DB Bonanza':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300';
      case 'Member WD CRM':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  const exportToCSV = () => {
    if (!logData?.records?.length) {
      toast.error('No records to export');
      return;
    }

    const headers = ['Customer ID', 'Source', 'Database', 'Affected Staff', 'Reserved By', 'Invalidated At', 'Reason'];
    const rows = logData.records.map(r => [
      r.customer_id,
      r.source_type,
      r.database_name,
      r.affected_staff_name,
      r.reserved_by_staff_name,
      r.invalidated_at,
      r.invalid_reason
    ]);

    const csvContent = [headers, ...rows].map(row => row.map(cell => `"${cell || ''}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conflict-resolution-log-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Exported to CSV');
  };

  if (loading && !logData) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-amber-500" />
            Conflict Resolution Log
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Track all auto-invalidated records due to reservation conflicts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={exportToCSV} variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
          <Button onClick={loadData} variant="outline" disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20 border-red-200 dark:border-red-800">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-red-600 dark:text-red-400">Total Invalidated</p>
                  <p className="text-2xl font-bold text-red-700 dark:text-red-300">{stats.total_invalidated}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/20 dark:to-amber-800/20 border-amber-200 dark:border-amber-800">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-amber-600 dark:text-amber-400">Today</p>
                  <p className="text-2xl font-bold text-amber-700 dark:text-amber-300">{stats.today}</p>
                </div>
                <Clock className="w-8 h-8 text-amber-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-800">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-600 dark:text-blue-400">This Week</p>
                  <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{stats.this_week}</p>
                </div>
                <Calendar className="w-8 h-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-800">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-600 dark:text-green-400">This Month</p>
                  <p className="text-2xl font-bold text-green-700 dark:text-green-300">{stats.this_month}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-green-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Top Staff Cards */}
      {stats && (stats.top_affected_staff?.length > 0 || stats.top_reserved_by_staff?.length > 0) && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Most Affected Staff */}
          {stats.top_affected_staff?.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="w-4 h-4 text-red-500" />
                  Most Affected Staff
                </CardTitle>
                <CardDescription className="text-xs">Staff who lost the most records</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {stats.top_affected_staff.map((staff, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <span className="text-sm font-medium">{staff.name}</span>
                      <Badge variant="destructive">{staff.count} records</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Top Reserved By Staff */}
          {stats.top_reserved_by_staff?.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="w-4 h-4 text-green-500" />
                  Top Reserved By Staff
                </CardTitle>
                <CardDescription className="text-xs">Staff who made the most reservations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {stats.top_reserved_by_staff.map((staff, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <span className="text-sm font-medium">{staff.name}</span>
                      <Badge className="bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300">{staff.count} reservations</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter:</span>
            </div>
            <select
              value={filterStaff}
              onChange={(e) => { setFilterStaff(e.target.value); setPage(0); }}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              data-testid="filter-staff-select"
            >
              <option value="">All Staff</option>
              {staffList.map(staff => (
                <option key={staff.id} value={staff.id}>{staff.name}</option>
              ))}
            </select>
            {filterStaff && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => { setFilterStaff(''); setPage(0); }}
              >
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Log Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Database className="w-5 h-5" />
              Resolution History
            </span>
            {logData && (
              <span className="text-sm font-normal text-gray-500">
                Showing {logData.returned_count} of {logData.total_count} records
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {logData?.records?.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
              <p>No conflict resolutions found</p>
              <p className="text-sm">Records will appear here when reservations invalidate other staff assignments</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="conflict-log-table">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-3 px-2 font-medium text-gray-600 dark:text-gray-400">Customer ID</th>
                      <th className="text-left py-3 px-2 font-medium text-gray-600 dark:text-gray-400">Source</th>
                      <th className="text-left py-3 px-2 font-medium text-gray-600 dark:text-gray-400">Database</th>
                      <th className="text-left py-3 px-2 font-medium text-gray-600 dark:text-gray-400">Affected Staff</th>
                      <th className="text-left py-3 px-2 font-medium text-gray-600 dark:text-gray-400">Reserved By</th>
                      <th className="text-left py-3 px-2 font-medium text-gray-600 dark:text-gray-400">Invalidated At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logData?.records?.map((record, idx) => (
                      <tr 
                        key={record.record_id || idx} 
                        className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                      >
                        <td className="py-3 px-2 font-mono text-xs">{record.customer_id}</td>
                        <td className="py-3 px-2">
                          <Badge className={getSourceBadgeColor(record.source_type)}>
                            {record.source_type}
                          </Badge>
                        </td>
                        <td className="py-3 px-2 text-gray-700 dark:text-gray-300">{record.database_name}</td>
                        <td className="py-3 px-2">
                          <span className="text-red-600 dark:text-red-400 font-medium">
                            {record.affected_staff_name}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <span className="text-green-600 dark:text-green-400 font-medium">
                            {record.reserved_by_staff_name}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-gray-500 dark:text-gray-400 text-xs">
                          {formatDate(record.invalidated_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {logData && logData.total_count > pageSize && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Page {page + 1} of {Math.ceil(logData.total_count / pageSize)}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(0, p - 1))}
                      disabled={page === 0}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => p + 1)}
                      disabled={(page + 1) * pageSize >= logData.total_count}
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
