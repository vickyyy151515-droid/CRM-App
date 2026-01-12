import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Users, TrendingUp, CheckCircle, XCircle, Clock, Package } from 'lucide-react';

export default function StaffProgress() {
  const [databases, setDatabases] = useState([]);
  const [allRecords, setAllRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [products, setProducts] = useState([]);
  const [dateRange, setDateRange] = useState('all');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dbResponse, productsResponse] = await Promise.all([
        api.get('/databases'),
        api.get('/products')
      ]);
      
      setDatabases(dbResponse.data);
      setProducts(productsResponse.data);

      // Load all records from all databases
      const allRecordsPromises = dbResponse.data.map(db => 
        api.get(`/databases/${db.id}/records`)
      );
      const recordsResponses = await Promise.all(allRecordsPromises);
      const combinedRecords = recordsResponses.flatMap(res => res.data);
      setAllRecords(combinedRecords);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Filter records by product if selected
  const filteredRecords = selectedProduct 
    ? allRecords.filter(r => r.product_id === selectedProduct)
    : allRecords;

  // Filter by date range
  const getDateFilteredRecords = () => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    return filteredRecords.filter(record => {
      if (!record.whatsapp_status || !record.whatsapp_status_updated_at) return false;
      
      const updatedDate = new Date(record.whatsapp_status_updated_at);
      
      switch(dateRange) {
        case 'today':
          return updatedDate >= today;
        case 'yesterday':
          const yesterday = new Date(today);
          yesterday.setDate(yesterday.getDate() - 1);
          return updatedDate >= yesterday && updatedDate < today;
        case 'last7days':
          const last7days = new Date(today);
          last7days.setDate(last7days.getDate() - 7);
          return updatedDate >= last7days;
        case 'last30days':
          const last30days = new Date(today);
          last30days.setDate(last30days.getDate() - 30);
          return updatedDate >= last30days;
        case 'custom':
          if (!customStartDate || !customEndDate) return false;
          const start = new Date(customStartDate);
          const end = new Date(customEndDate);
          end.setHours(23, 59, 59, 999);
          return updatedDate >= start && updatedDate <= end;
        default:
          return true;
      }
    });
  };

  const dateFilteredRecords = getDateFilteredRecords();

  // Calculate staff statistics with date filter
  const staffStats = {};
  const staffDailyStats = {};
  
  // Overall stats (all time)
  filteredRecords.forEach(record => {
    if (record.status === 'assigned' && record.assigned_to) {
      if (!staffStats[record.assigned_to]) {
        staffStats[record.assigned_to] = {
          name: record.assigned_to_name,
          total: 0,
          ada: 0,
          tidak: 0,
          notChecked: 0
        };
      }
      staffStats[record.assigned_to].total++;
      if (record.whatsapp_status === 'ada') {
        staffStats[record.assigned_to].ada++;
      } else if (record.whatsapp_status === 'tidak') {
        staffStats[record.assigned_to].tidak++;
      } else {
        staffStats[record.assigned_to].notChecked++;
      }
    }
  });

  // Daily/filtered period stats
  dateFilteredRecords.forEach(record => {
    if (record.assigned_to) {
      if (!staffDailyStats[record.assigned_to]) {
        staffDailyStats[record.assigned_to] = {
          name: record.assigned_to_name,
          checkedToday: 0,
          adaToday: 0,
          tidakToday: 0
        };
      }
      staffDailyStats[record.assigned_to].checkedToday++;
      if (record.whatsapp_status === 'ada') {
        staffDailyStats[record.assigned_to].adaToday++;
      } else if (record.whatsapp_status === 'tidak') {
        staffDailyStats[record.assigned_to].tidakToday++;
      }
    }
  });

  // Calculate database quality metrics
  const databaseStats = databases.map(db => {
    const dbRecords = allRecords.filter(r => r.database_id === db.id);
    const assignedRecords = dbRecords.filter(r => r.status === 'assigned');
    const ada = assignedRecords.filter(r => r.whatsapp_status === 'ada').length;
    const tidak = assignedRecords.filter(r => r.whatsapp_status === 'tidak').length;
    const checked = ada + tidak;
    const qualityRate = checked > 0 ? ((ada / checked) * 100).toFixed(1) : 0;
    const checkProgress = assignedRecords.length > 0 ? ((checked / assignedRecords.length) * 100).toFixed(1) : 0;

    return {
      ...db,
      totalRecords: dbRecords.length,
      assigned: assignedRecords.length,
      ada,
      tidak,
      notChecked: assignedRecords.length - checked,
      qualityRate: parseFloat(qualityRate),
      checkProgress: parseFloat(checkProgress)
    };
  }).filter(db => !selectedProduct || db.product_id === selectedProduct);

  // Overall statistics
  const totalAssigned = filteredRecords.filter(r => r.status === 'assigned').length;
  const totalAda = filteredRecords.filter(r => r.whatsapp_status === 'ada').length;
  const totalTidak = filteredRecords.filter(r => r.whatsapp_status === 'tidak').length;
  const totalChecked = totalAda + totalTidak;
  const overallQuality = totalChecked > 0 ? ((totalAda / totalChecked) * 100).toFixed(1) : 0;
  const overallProgress = totalAssigned > 0 ? ((totalChecked / totalAssigned) * 100).toFixed(1) : 0;

  // Daily metrics
  const checkedInPeriod = dateFilteredRecords.length;
  const adaInPeriod = dateFilteredRecords.filter(r => r.whatsapp_status === 'ada').length;
  const tidakInPeriod = dateFilteredRecords.filter(r => r.whatsapp_status === 'tidak').length;
  const periodQuality = checkedInPeriod > 0 ? ((adaInPeriod / checkedInPeriod) * 100).toFixed(1) : 0;

  const getDateRangeLabel = () => {
    switch(dateRange) {
      case 'today': return 'Today';
      case 'yesterday': return 'Yesterday';
      case 'last7days': return 'Last 7 Days';
      case 'last30days': return 'Last 30 Days';
      case 'custom': return 'Custom Range';
      default: return 'All Time';
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-slate-600">Loading statistics...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Staff Progress & Database Quality</h2>
        <div className="flex gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="flex h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            <option value="all">All Time</option>
            <option value="today">Today</option>
            <option value="yesterday">Yesterday</option>
            <option value="last7days">Last 7 Days</option>
            <option value="last30days">Last 30 Days</option>
            <option value="custom">Custom Range</option>
          </select>
          {dateRange === 'custom' && (
            <>
              <input
                type="date"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
                className="flex h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              />
              <input
                type="date"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
                className="flex h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
              />
            </>
          )}
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="flex h-10 w-64 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            <option value="">All Products</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Daily/Period Performance Banner */}
      {dateRange !== 'all' && (
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 mb-6 text-white shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-2xl font-bold">{getDateRangeLabel()} Performance</h3>
              <p className="text-indigo-100 text-sm">Real-time progress tracking</p>
            </div>
            <Clock className="text-white opacity-50" size={48} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-sm mb-1">Checked {getDateRangeLabel()}</p>
              <p className="text-3xl font-bold">{checkedInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-sm mb-1">Ada</p>
              <p className="text-3xl font-bold">{adaInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-sm mb-1">Tidak</p>
              <p className="text-3xl font-bold">{tidakInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-sm mb-1">Quality Rate</p>
              <p className="text-3xl font-bold">{periodQuality}%</p>
            </div>
          </div>
        </div>
      )}

      {/* Overall Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <Users className="text-indigo-600" size={24} />
            <span className="text-3xl font-bold text-slate-900">{totalAssigned}</span>
          </div>
          <p className="text-sm text-slate-600">Total Assigned Customers</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <CheckCircle className="text-emerald-600" size={24} />
            <span className="text-3xl font-bold text-emerald-700">{totalAda}</span>
          </div>
          <p className="text-sm text-slate-600">WhatsApp Active (Ada)</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <XCircle className="text-rose-600" size={24} />
            <span className="text-3xl font-bold text-rose-700">{totalTidak}</span>
          </div>
          <p className="text-sm text-slate-600">WhatsApp Inactive (Tidak)</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="text-indigo-600" size={24} />
            <span className="text-3xl font-bold text-indigo-700">{overallQuality}%</span>
          </div>
          <p className="text-sm text-slate-600">Overall Quality Rate</p>
          <div className="mt-2 w-full bg-slate-200 rounded-full h-2">
            <div 
              className="bg-indigo-600 h-2 rounded-full transition-all" 
              style={{width: `${overallQuality}%`}}
            ></div>
          </div>
        </div>
      </div>

      {/* Staff Progress */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Users className="text-indigo-600" size={20} />
          Staff Performance
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.values(staffStats).map((staff, idx) => {
            const checkedCount = staff.ada + staff.tidak;
            const progressRate = ((checkedCount / staff.total) * 100).toFixed(1);
            const qualityRate = checkedCount > 0 ? ((staff.ada / checkedCount) * 100).toFixed(1) : 0;
            const dailyStats = staffDailyStats[Object.keys(staffStats)[idx]];

            return (
              <div key={idx} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <Users className="text-indigo-600" size={18} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-900">{staff.name}</h4>
                    <p className="text-xs text-slate-500">{staff.total} customers assigned</p>
                  </div>
                </div>

                {/* Daily Progress */}
                {dateRange !== 'all' && dailyStats && (
                  <div className="mb-4 p-3 bg-indigo-50 rounded-lg border border-indigo-100">
                    <p className="text-xs font-semibold text-indigo-900 mb-2">{getDateRangeLabel()}</p>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <p className="text-lg font-bold text-indigo-600">{dailyStats.checkedToday}</p>
                        <p className="text-xs text-indigo-600">Checked</p>
                      </div>
                      <div>
                        <p className="text-lg font-bold text-emerald-600">{dailyStats.adaToday}</p>
                        <p className="text-xs text-emerald-600">Ada</p>
                      </div>
                      <div>
                        <p className="text-lg font-bold text-rose-600">{dailyStats.tidakToday}</p>
                        <p className="text-xs text-rose-600">Tidak</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-slate-600">Check Progress</span>
                      <span className="font-semibold text-slate-900">{progressRate}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div 
                        className="bg-indigo-600 h-2 rounded-full transition-all" 
                        style={{width: `${progressRate}%`}}
                      ></div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100">
                    <div className="text-center">
                      <p className="text-lg font-bold text-emerald-600">{staff.ada}</p>
                      <p className="text-xs text-slate-600">Ada</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-rose-600">{staff.tidak}</p>
                      <p className="text-xs text-slate-600">Tidak</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-slate-400">{staff.notChecked}</p>
                      <p className="text-xs text-slate-600">Pending</p>
                    </div>
                  </div>

                  {checkedCount > 0 && (
                    <div className="pt-2 border-t border-slate-100">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-600">Quality Rate:</span>
                        <span className={`text-sm font-semibold ${parseFloat(qualityRate) >= 70 ? 'text-emerald-600' : parseFloat(qualityRate) >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                          {qualityRate}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        {Object.keys(staffStats).length === 0 && (
          <div className="text-center py-8 text-slate-600">No staff assignments yet</div>
        )}
      </div>

      {/* Database Quality Report */}
      <div>
        <h3 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Package className="text-indigo-600" size={20} />
          Database Quality Report
        </h3>
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Database</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Product</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Total Records</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Assigned</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Check Progress</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Ada</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Tidak</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700">Quality Rate</th>
                </tr>
              </thead>
              <tbody>
                {databaseStats.map((db) => (
                  <tr key={db.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm text-slate-900 font-medium">{db.filename}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200">
                        {db.product_name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-900">{db.totalRecords}</td>
                    <td className="px-4 py-3 text-sm text-slate-900">{db.assigned}</td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-200 rounded-full h-2">
                          <div 
                            className="bg-indigo-600 h-2 rounded-full" 
                            style={{width: `${db.checkProgress}%`}}
                          ></div>
                        </div>
                        <span className="text-xs text-slate-600">{db.checkProgress}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="text-emerald-600 font-semibold">{db.ada}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="text-rose-600 font-semibold">{db.tidak}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <span className={`font-semibold ${db.qualityRate >= 70 ? 'text-emerald-600' : db.qualityRate >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                          {db.qualityRate}%
                        </span>
                        {db.qualityRate >= 70 && <span className="text-emerald-600 text-xs">✓ Good</span>}
                        {db.qualityRate >= 50 && db.qualityRate < 70 && <span className="text-amber-600 text-xs">⚠ Fair</span>}
                        {db.qualityRate < 50 && db.qualityRate > 0 && <span className="text-rose-600 text-xs">✗ Poor</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
