import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Users, TrendingUp, CheckCircle, XCircle, Clock, Package, MessageCircle, Target, Trophy, AlertTriangle, AlertOctagon, Flame } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const MONTH_NAMES_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MONTH_NAMES_ID = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

export default function StaffProgress() {
  const { t, isIndonesian } = useLanguage();
  const [databases, setDatabases] = useState([]);
  const [allRecords, setAllRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [products, setProducts] = useState([]);
  const [dateRange, setDateRange] = useState('all');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  
  // Target Progress State
  const [targetProgress, setTargetProgress] = useState(null);
  const [targetLoading, setTargetLoading] = useState(true);
  const [activeView, setActiveView] = useState('quality'); // 'quality' or 'targets'

  useEffect(() => {
    loadData();
    loadTargetProgress();
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
      toast.error(t('messages.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const loadTargetProgress = async () => {
    setTargetLoading(true);
    try {
      const response = await api.get('/admin/staff-target-progress');
      setTargetProgress(response.data);
    } catch (error) {
      console.error('Failed to load target progress:', error);
    } finally {
      setTargetLoading(false);
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
      // Check if either whatsapp or respond status was updated
      const whatsappDate = record.whatsapp_status_updated_at ? new Date(record.whatsapp_status_updated_at) : null;
      const respondDate = record.respond_status_updated_at ? new Date(record.respond_status_updated_at) : null;
      
      if (!whatsappDate && !respondDate) return false;
      
      // Use the most recent update date
      const updatedDate = whatsappDate && respondDate 
        ? (whatsappDate > respondDate ? whatsappDate : respondDate)
        : (whatsappDate || respondDate);
      
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
          // WhatsApp stats
          ada: 0,
          ceklis1: 0,
          tidak: 0,
          waNotChecked: 0,
          // Respond stats
          respondYa: 0,
          respondTidak: 0,
          respondNotChecked: 0
        };
      }
      staffStats[record.assigned_to].total++;
      
      // WhatsApp status
      if (record.whatsapp_status === 'ada') {
        staffStats[record.assigned_to].ada++;
      } else if (record.whatsapp_status === 'ceklis1') {
        staffStats[record.assigned_to].ceklis1++;
      } else if (record.whatsapp_status === 'tidak') {
        staffStats[record.assigned_to].tidak++;
      } else {
        staffStats[record.assigned_to].waNotChecked++;
      }
      
      // Respond status
      if (record.respond_status === 'ya') {
        staffStats[record.assigned_to].respondYa++;
      } else if (record.respond_status === 'tidak') {
        staffStats[record.assigned_to].respondTidak++;
      } else {
        staffStats[record.assigned_to].respondNotChecked++;
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
          ceklis1Today: 0,
          tidakToday: 0,
          respondYaToday: 0,
          respondTidakToday: 0
        };
      }
      staffDailyStats[record.assigned_to].checkedToday++;
      if (record.whatsapp_status === 'ada') {
        staffDailyStats[record.assigned_to].adaToday++;
      } else if (record.whatsapp_status === 'ceklis1') {
        staffDailyStats[record.assigned_to].ceklis1Today++;
      } else if (record.whatsapp_status === 'tidak') {
        staffDailyStats[record.assigned_to].tidakToday++;
      }
      if (record.respond_status === 'ya') {
        staffDailyStats[record.assigned_to].respondYaToday++;
      } else if (record.respond_status === 'tidak') {
        staffDailyStats[record.assigned_to].respondTidakToday++;
      }
    }
  });

  // Calculate database quality metrics
  const databaseStats = databases.map(db => {
    const dbRecords = allRecords.filter(r => r.database_id === db.id);
    const assignedRecords = dbRecords.filter(r => r.status === 'assigned');
    
    // WhatsApp stats
    const ada = assignedRecords.filter(r => r.whatsapp_status === 'ada').length;
    const ceklis1 = assignedRecords.filter(r => r.whatsapp_status === 'ceklis1').length;
    const tidak = assignedRecords.filter(r => r.whatsapp_status === 'tidak').length;
    const waChecked = ada + ceklis1 + tidak;
    const qualityRate = waChecked > 0 ? ((ada / waChecked) * 100).toFixed(1) : 0;
    const checkProgress = assignedRecords.length > 0 ? ((waChecked / assignedRecords.length) * 100).toFixed(1) : 0;
    
    // Respond stats
    const respondYa = assignedRecords.filter(r => r.respond_status === 'ya').length;
    const respondTidak = assignedRecords.filter(r => r.respond_status === 'tidak').length;
    const respondChecked = respondYa + respondTidak;
    const respondRate = respondChecked > 0 ? ((respondYa / respondChecked) * 100).toFixed(1) : 0;
    const respondProgress = assignedRecords.length > 0 ? ((respondChecked / assignedRecords.length) * 100).toFixed(1) : 0;

    return {
      ...db,
      totalRecords: dbRecords.length,
      assigned: assignedRecords.length,
      ada,
      ceklis1,
      tidak,
      waNotChecked: assignedRecords.length - waChecked,
      qualityRate: parseFloat(qualityRate),
      checkProgress: parseFloat(checkProgress),
      respondYa,
      respondTidak,
      respondNotChecked: assignedRecords.length - respondChecked,
      respondRate: parseFloat(respondRate),
      respondProgress: parseFloat(respondProgress)
    };
  }).filter(db => !selectedProduct || db.product_id === selectedProduct);

  // Overall statistics
  const totalAssigned = filteredRecords.filter(r => r.status === 'assigned').length;
  
  // WhatsApp overall
  const totalAda = filteredRecords.filter(r => r.whatsapp_status === 'ada').length;
  const totalCeklis1 = filteredRecords.filter(r => r.whatsapp_status === 'ceklis1').length;
  const totalTidak = filteredRecords.filter(r => r.whatsapp_status === 'tidak').length;
  const totalWaChecked = totalAda + totalCeklis1 + totalTidak;
  const overallQuality = totalWaChecked > 0 ? ((totalAda / totalWaChecked) * 100).toFixed(1) : 0;
  
  // Respond overall
  const totalRespondYa = filteredRecords.filter(r => r.respond_status === 'ya').length;
  const totalRespondTidak = filteredRecords.filter(r => r.respond_status === 'tidak').length;
  const totalRespondChecked = totalRespondYa + totalRespondTidak;
  const overallRespondRate = totalRespondChecked > 0 ? ((totalRespondYa / totalRespondChecked) * 100).toFixed(1) : 0;

  // Daily metrics
  const checkedInPeriod = dateFilteredRecords.length;
  const adaInPeriod = dateFilteredRecords.filter(r => r.whatsapp_status === 'ada').length;
  const ceklis1InPeriod = dateFilteredRecords.filter(r => r.whatsapp_status === 'ceklis1').length;
  const tidakInPeriod = dateFilteredRecords.filter(r => r.whatsapp_status === 'tidak').length;
  const periodQuality = checkedInPeriod > 0 ? ((adaInPeriod / checkedInPeriod) * 100).toFixed(1) : 0;
  
  // Respond period metrics
  const respondYaInPeriod = dateFilteredRecords.filter(r => r.respond_status === 'ya').length;
  const respondTidakInPeriod = dateFilteredRecords.filter(r => r.respond_status === 'tidak').length;
  const respondInPeriod = respondYaInPeriod + respondTidakInPeriod;
  const periodRespondRate = respondInPeriod > 0 ? ((respondYaInPeriod / respondInPeriod) * 100).toFixed(1) : 0;

  const getDateRangeLabel = () => {
    switch(dateRange) {
      case 'today': return t('staffProgress.today');
      case 'yesterday': return t('staffProgress.yesterday');
      case 'last7days': return t('staffProgress.last7Days');
      case 'last30days': return t('staffProgress.last30Days');
      case 'custom': return t('staffProgress.customRange');
      default: return t('staffProgress.allTime');
    }
  };

  const monthNames = isIndonesian ? MONTH_NAMES_ID : MONTH_NAMES_EN;

  // Render Target Progress View
  const renderTargetProgressView = () => {
    if (targetLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      );
    }

    if (!targetProgress) {
      return <div className="text-center py-12 text-slate-500">{isIndonesian ? 'Gagal memuat data' : 'Failed to load data'}</div>;
    }

    const { summary, staff_progress } = targetProgress;

    return (
      <div className="space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Users className="text-blue-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{isIndonesian ? 'Total Staff' : 'Total Staff'}</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total_staff}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                <Trophy className="text-emerald-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{isIndonesian ? 'Target Tercapai' : 'Target Achieved'}</p>
                <p className="text-2xl font-bold text-emerald-600">{summary.success_staff}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                <AlertTriangle className="text-orange-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{isIndonesian ? 'Peringatan' : 'Warning'}</p>
                <p className="text-2xl font-bold text-orange-600">{summary.warning_staff}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                <AlertOctagon className="text-red-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{isIndonesian ? 'Kritis' : 'Critical'}</p>
                <p className="text-2xl font-bold text-red-600">{summary.critical_staff}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Info Bar */}
        <div className="bg-slate-100 dark:bg-slate-700/50 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-slate-600 dark:text-slate-300">
            📅 {monthNames[targetProgress.month - 1]} {targetProgress.year} • {targetProgress.days_remaining} {isIndonesian ? 'hari tersisa' : 'days remaining'}
          </span>
          <span className="text-slate-600 dark:text-slate-300">
            🎯 {isIndonesian ? 'Target Harian' : 'Daily Target'}: {targetProgress.daily_ndp_target} NDP {isIndonesian ? 'atau' : 'or'} {targetProgress.daily_rdp_target} RDP • {isIndonesian ? 'Target Bulanan' : 'Monthly'}: {targetProgress.required_success_days} {isIndonesian ? 'hari' : 'days'}
          </span>
        </div>

        {/* Staff Progress Cards */}
        <div className="grid gap-4">
          {staff_progress.map((staff) => {
            const progress = Math.min(100, (staff.success_days / targetProgress.required_success_days) * 100);
            
            // Determine card style based on warning level
            let cardStyle = 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800';
            let progressBarColor = 'bg-blue-500';
            
            if (staff.warning_level === 3) {
              cardStyle = 'border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-900/20';
              progressBarColor = 'bg-red-500';
            } else if (staff.warning_level === 2) {
              cardStyle = 'border-orange-300 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20';
              progressBarColor = 'bg-orange-500';
            } else if (staff.success_days >= targetProgress.required_success_days) {
              cardStyle = 'border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20';
              progressBarColor = 'bg-emerald-500';
            }

            return (
              <div key={staff.staff_id} className={`rounded-xl border p-4 shadow-sm ${cardStyle}`}>
                <div className="flex flex-wrap items-center justify-between gap-4">
                  {/* Staff Info */}
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{staff.status_symbol}</span>
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-white">{staff.staff_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {isIndonesian ? 'Hari Ini' : 'Today'}: NDP {staff.today_ndp}/{targetProgress.daily_ndp_target} • RDP {staff.today_rdp}/{targetProgress.daily_rdp_target}
                        {staff.today_target_reached && <CheckCircle size={14} className="inline ml-1 text-emerald-500" />}
                      </p>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <p className="text-xl font-bold text-slate-900 dark:text-white">{staff.success_days}<span className="text-sm font-normal text-slate-500">/{targetProgress.required_success_days}</span></p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{isIndonesian ? 'Hari Sukses' : 'Success Days'}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-slate-900 dark:text-white">{staff.projected_success}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{isIndonesian ? 'Proyeksi' : 'Projected'}</p>
                    </div>
                    {staff.warning_level >= 2 && (
                      <div className="text-center">
                        <p className="text-sm text-slate-500 dark:text-slate-400">{isIndonesian ? 'Bulan Lalu' : 'Last Month'}</p>
                        <p className={`font-bold ${staff.prev_month_1_success < targetProgress.required_success_days ? 'text-red-500' : 'text-emerald-500'}`}>
                          {staff.prev_month_1_success}/{targetProgress.required_success_days}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mt-3">
                  <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-500 ${progressBarColor}`}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
                    <span>{Math.round(progress)}% {isIndonesian ? 'tercapai' : 'achieved'}</span>
                    {staff.success_days < targetProgress.required_success_days && (
                      <span>{isIndonesian ? `Butuh ${targetProgress.required_success_days - staff.success_days} hari lagi` : `Need ${targetProgress.required_success_days - staff.success_days} more`}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 text-sm">
          <p className="font-medium text-slate-700 dark:text-slate-300 mb-2">{isIndonesian ? 'Keterangan Status:' : 'Status Legend:'}</p>
          <div className="flex flex-wrap gap-4">
            <span className="flex items-center gap-1"><span>🏆</span> {isIndonesian ? 'Target Tercapai' : 'Target Achieved'}</span>
            <span className="flex items-center gap-1"><span>✓</span> {isIndonesian ? 'Di Jalur Yang Benar' : 'On Track'}</span>
            <span className="flex items-center gap-1"><span>📊</span> {isIndonesian ? 'Dalam Proses' : 'In Progress'}</span>
            <span className="flex items-center gap-1"><span>⚠️</span> {isIndonesian ? 'Gagal Bulan Lalu (1x)' : 'Failed Last Month (1x)'}</span>
            <span className="flex items-center gap-1"><span>🚨</span> {isIndonesian ? 'Gagal 2 Bulan Berturut' : '2 Consecutive Months Failed'}</span>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return <div className="text-center py-12 text-slate-600 dark:text-slate-400">{t('staffProgress.loadingStats')}</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">{t('staffProgress.title')}</h2>
      </div>

      {/* View Toggle Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 mb-6">
        <button
          onClick={() => setActiveView('quality')}
          className={`px-4 py-2 font-medium text-sm transition-colors ${
            activeView === 'quality'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-slate-600 dark:text-slate-400 hover:text-indigo-600'
          }`}
        >
          {isIndonesian ? 'Kualitas Database' : 'Database Quality'}
        </button>
        <button
          onClick={() => setActiveView('targets')}
          className={`px-4 py-2 font-medium text-sm transition-colors flex items-center gap-2 ${
            activeView === 'targets'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-slate-600 dark:text-slate-400 hover:text-indigo-600'
          }`}
        >
          <Target size={16} />
          {isIndonesian ? 'Target NDP/RDP' : 'NDP/RDP Targets'}
          {targetProgress?.summary?.critical_staff > 0 && (
            <span className="px-1.5 py-0.5 bg-red-500 text-white rounded-full text-xs">{targetProgress.summary.critical_staff}</span>
          )}
        </button>
      </div>

      {/* Conditional Rendering Based on Active View */}
      {activeView === 'targets' ? (
        renderTargetProgressView()
      ) : (
        <>
          {/* Original Quality View with Filters */}
          <div className="flex gap-3 mb-6">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="flex h-10 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            <option value="all">{t('staffProgress.allTime')}</option>
            <option value="today">{t('staffProgress.today')}</option>
            <option value="yesterday">{t('staffProgress.yesterday')}</option>
            <option value="last7days">{t('staffProgress.last7Days')}</option>
            <option value="last30days">{t('staffProgress.last30Days')}</option>
            <option value="custom">{t('staffProgress.customRange')}</option>
          </select>
          {dateRange === 'custom' && (
            <>
              <input
                type="date"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
                className="flex h-10 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm"
              />
              <input
                type="date"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
                className="flex h-10 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm"
              />
            </>
          )}
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="flex h-10 w-64 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          >
            <option value="">{t('myRecords.allProducts')}</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </div>

      {/* Daily/Period Performance Banner */}
      {dateRange !== 'all' && (
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 mb-6 text-white shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-2xl font-bold">{t('staffProgress.performance')} {getDateRangeLabel()}</h3>
              <p className="text-indigo-100 text-sm">Tracking progres real-time</p>
            </div>
            <Clock className="text-white opacity-50" size={48} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-9 gap-4">
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.totalChecked')}</p>
              <p className="text-2xl font-bold">{checkedInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.waAda')}</p>
              <p className="text-2xl font-bold">{adaInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">Ceklis 1</p>
              <p className="text-2xl font-bold">{ceklis1InPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.waTidak')}</p>
              <p className="text-2xl font-bold">{tidakInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.waQuality')}</p>
              <p className="text-2xl font-bold">{periodQuality}%</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4 border-l-2 border-white/30">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.respondYa')}</p>
              <p className="text-2xl font-bold">{respondYaInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.respondTidak')}</p>
              <p className="text-2xl font-bold">{respondTidakInPeriod}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-indigo-100 text-xs mb-1">{t('staffProgress.respondRate')}</p>
              <p className="text-2xl font-bold">{periodRespondRate}%</p>
            </div>
          </div>
        </div>
      )}

      {/* Overall Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <Users className="text-indigo-600" size={20} />
            <span className="text-2xl font-bold text-slate-900 dark:text-white">{totalAssigned}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">{t('staffProgress.totalAssigned')}</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <CheckCircle className="text-emerald-600" size={20} />
            <span className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">{totalAda}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">{t('staffProgress.waAda')}</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <CheckCircle className="text-amber-600" size={20} />
            <span className="text-2xl font-bold text-amber-700 dark:text-amber-400">{totalCeklis1}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">Ceklis 1</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <XCircle className="text-rose-600" size={20} />
            <span className="text-2xl font-bold text-rose-700 dark:text-rose-400">{totalTidak}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">{t('staffProgress.waTidak')}</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <MessageCircle className="text-blue-600" size={20} />
            <span className="text-2xl font-bold text-blue-700 dark:text-blue-400">{totalRespondYa}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">{t('staffProgress.respondYa')}</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <MessageCircle className="text-orange-600" size={20} />
            <span className="text-2xl font-bold text-orange-700 dark:text-orange-400">{totalRespondTidak}</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">{t('staffProgress.respondTidak')}</p>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="text-indigo-600" size={20} />
            <span className="text-2xl font-bold text-indigo-700 dark:text-indigo-400">{overallRespondRate}%</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">{t('staffProgress.responseRate')}</p>
          <div className="mt-2 w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
            <div 
              className="bg-indigo-600 h-1.5 rounded-full transition-all" 
              style={{width: `${overallRespondRate}%`}}
            ></div>
          </div>
        </div>
      </div>

      {/* Staff Progress */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <Users className="text-indigo-600" size={20} />
          {t('staffProgress.staffPerformance')}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.values(staffStats).map((staff, idx) => {
            const waCheckedCount = staff.ada + staff.ceklis1 + staff.tidak;
            const waProgressRate = ((waCheckedCount / staff.total) * 100).toFixed(1);
            const waQualityRate = waCheckedCount > 0 ? ((staff.ada / waCheckedCount) * 100).toFixed(1) : 0;
            
            const respondCheckedCount = staff.respondYa + staff.respondTidak;
            const respondProgressRate = ((respondCheckedCount / staff.total) * 100).toFixed(1);
            const respondRate = respondCheckedCount > 0 ? ((staff.respondYa / respondCheckedCount) * 100).toFixed(1) : 0;
            
            const dailyStats = staffDailyStats[Object.keys(staffStats)[idx]];

            return (
              <div key={idx} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/50 rounded-full flex items-center justify-center">
                    <Users className="text-indigo-600" size={18} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-900 dark:text-white">{staff.name}</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{staff.total} {t('staffProgress.customersAssigned')}</p>
                  </div>
                </div>

                {/* Daily Progress */}
                {dateRange !== 'all' && dailyStats && (
                  <div className="mb-4 p-3 bg-indigo-50 dark:bg-indigo-900/30 rounded-lg border border-indigo-100 dark:border-indigo-800">
                    <p className="text-xs font-semibold text-indigo-900 dark:text-indigo-300 mb-2">{getDateRangeLabel()}</p>
                    <div className="grid grid-cols-6 gap-1 text-center">
                      <div>
                        <p className="text-sm font-bold text-indigo-600 dark:text-indigo-400">{dailyStats.checkedToday}</p>
                        <p className="text-[10px] text-indigo-600 dark:text-indigo-400">Dicek</p>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{dailyStats.adaToday}</p>
                        <p className="text-[10px] text-emerald-600 dark:text-emerald-400">{t('staffProgress.waAda')}</p>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-amber-600 dark:text-amber-400">{dailyStats.ceklis1Today}</p>
                        <p className="text-[10px] text-amber-600 dark:text-amber-400">Ceklis 1</p>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-rose-600 dark:text-rose-400">{dailyStats.tidakToday}</p>
                        <p className="text-[10px] text-rose-600 dark:text-rose-400">{t('staffProgress.waTidak')}</p>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-blue-600 dark:text-blue-400">{dailyStats.respondYaToday}</p>
                        <p className="text-[10px] text-blue-600 dark:text-blue-400">Resp Ya</p>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-orange-600 dark:text-orange-400">{dailyStats.respondTidakToday}</p>
                        <p className="text-[10px] text-orange-600 dark:text-orange-400">Resp Tidak</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {/* WhatsApp Section */}
                  <div className="pb-3 border-b border-slate-100 dark:border-slate-700">
                    <p className="text-xs font-medium text-slate-500 mb-2">WhatsApp Status</p>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-slate-600 dark:text-slate-400">Check Progress</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{waProgressRate}%</span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 mb-2">
                      <div 
                        className="bg-emerald-500 h-2 rounded-full transition-all" 
                        style={{width: `${waProgressRate}%`}}
                      ></div>
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      <div className="text-center">
                        <p className="text-sm font-bold text-emerald-600">{staff.ada}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Ada</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-bold text-amber-600">{staff.ceklis1}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Ceklis 1</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-bold text-rose-600">{staff.tidak}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Tidak</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-bold text-slate-400">{staff.waNotChecked}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Pending</p>
                      </div>
                    </div>
                  </div>

                  {/* Respond Section */}
                  <div className="pb-3 border-b border-slate-100 dark:border-slate-700">
                    <p className="text-xs font-medium text-slate-500 mb-2">Respond Status</p>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-slate-600 dark:text-slate-400">Check Progress</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{respondProgressRate}%</span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 mb-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full transition-all" 
                        style={{width: `${respondProgressRate}%`}}
                      ></div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="text-center">
                        <p className="text-sm font-bold text-blue-600">{staff.respondYa}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Ya</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-bold text-orange-600">{staff.respondTidak}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Tidak</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-bold text-slate-400">{staff.respondNotChecked}</p>
                        <p className="text-[10px] text-slate-600 dark:text-slate-400">Pending</p>
                      </div>
                    </div>
                  </div>

                  {/* Quality Rates */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="text-center p-2 bg-emerald-50 rounded-lg">
                      <p className={`text-lg font-bold ${parseFloat(waQualityRate) >= 70 ? 'text-emerald-600' : parseFloat(waQualityRate) >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                        {waQualityRate}%
                      </p>
                      <p className="text-[10px] text-slate-600 dark:text-slate-400">WA Quality</p>
                    </div>
                    <div className="text-center p-2 bg-blue-50 rounded-lg">
                      <p className={`text-lg font-bold ${parseFloat(respondRate) >= 70 ? 'text-blue-600' : parseFloat(respondRate) >= 50 ? 'text-amber-600' : 'text-orange-600'}`}>
                        {respondRate}%
                      </p>
                      <p className="text-[10px] text-slate-600 dark:text-slate-400">Respond Rate</p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {Object.keys(staffStats).length === 0 && (
          <div className="text-center py-8 text-slate-600 dark:text-slate-400">{t('staffProgress.noStaffAssignments')}</div>
        )}
      </div>

      {/* Database Quality Report */}
      <div>
        <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <Package className="text-indigo-600" size={20} />
          {t('staffProgress.databaseQualityReport')}
        </h3>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.database')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.product')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.assigned')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.waAda')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.waTidak')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.waQualityRate')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.respondYa')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.respondTidak')}</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-200">{t('staffProgress.respondRate')}</th>
                </tr>
              </thead>
              <tbody>
                {databaseStats.map((db) => (
                  <tr key={db.id} className="border-b border-slate-100 hover:bg-slate-50 dark:hover:bg-slate-700">
                    <td className="px-3 py-3 text-sm text-slate-900 font-medium">{db.filename}</td>
                    <td className="px-3 py-3 text-sm">
                      <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold bg-indigo-50 text-indigo-700 border-indigo-200">
                        {db.product_name}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-sm text-slate-900 dark:text-white">{db.assigned}</td>
                    <td className="px-3 py-3 text-sm">
                      <span className="text-emerald-600 font-semibold">{db.ada}</span>
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <span className="text-rose-600 font-semibold">{db.tidak}</span>
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <span className={`font-semibold ${db.qualityRate >= 70 ? 'text-emerald-600' : db.qualityRate >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                        {db.qualityRate}%
                      </span>
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <span className="text-blue-600 font-semibold">{db.respondYa}</span>
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <span className="text-orange-600 font-semibold">{db.respondTidak}</span>
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <span className={`font-semibold ${db.respondRate >= 70 ? 'text-blue-600' : db.respondRate >= 50 ? 'text-amber-600' : 'text-orange-600'}`}>
                        {db.respondRate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
        </>
      )}
    </div>
  );
}
