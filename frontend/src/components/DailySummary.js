import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Calendar, Trophy, TrendingUp, Users, DollarSign, UserPlus, RefreshCcw, ChevronLeft, ChevronRight, Award, Target, Package, ChevronDown, ChevronUp } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function DailySummary({ isAdmin = false }) {
  const { t, language } = useLanguage();
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showHistory, setShowHistory] = useState(false);
  const [showProductBreakdown, setShowProductBreakdown] = useState(true);
  const [expandedStaff, setExpandedStaff] = useState({});

  const loadSummary = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/daily-summary?date=${selectedDate}`);
      setSummary(response.data);
    } catch (error) {
      toast.error(t('messages.somethingWrong'));
    } finally {
      setLoading(false);
    }
  }, [selectedDate, t]);

  const loadHistory = useCallback(async () => {
    try {
      const response = await api.get('/daily-summary/history?days=7');
      setHistory(response.data || []);
    } catch (error) {
      console.error('Failed to load history');
    }
  }, []);

  useEffect(() => {
    loadSummary();
    loadHistory();
  }, [loadSummary, loadHistory]);

  const formatCurrency = (amount) => {
    if (!amount) return 'Rp 0';
    if (amount >= 1000000000) {
      return `Rp ${(amount / 1000000000).toFixed(2)}B`;
    } else if (amount >= 1000000) {
      return `Rp ${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `Rp ${(amount / 1000).toFixed(0)}K`;
    }
    return `Rp ${amount.toLocaleString('id-ID')}`;
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    const locale = language === 'id' ? 'id-ID' : 'en-US';
    return date.toLocaleDateString(locale, { 
      weekday: 'long',
      day: 'numeric', 
      month: 'long',
      year: 'numeric'
    });
  };

  const formatShortDate = (dateStr) => {
    const date = new Date(dateStr);
    const locale = language === 'id' ? 'id-ID' : 'en-US';
    return date.toLocaleDateString(locale, { 
      day: 'numeric', 
      month: 'short'
    });
  };

  const navigateDate = (direction) => {
    const current = new Date(selectedDate);
    current.setDate(current.getDate() + direction);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (current <= today) {
      setSelectedDate(current.toISOString().split('T')[0]);
    }
  };

  const isToday = selectedDate === new Date().toISOString().split('T')[0];

  const toggleStaffExpand = (staffId) => {
    setExpandedStaff(prev => ({
      ...prev,
      [staffId]: !prev[staffId]
    }));
  };

  const getRankBadge = (rank, total) => {
    if (!rank) return null;
    
    if (rank === 1) {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300 border border-yellow-300">
          <Trophy size={16} /> #1 Top Performer!
        </span>
      );
    } else if (rank <= 3) {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 border border-emerald-300">
          <Award size={16} /> #{rank} of {total}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 dark:text-slate-400">
        #{rank} of {total}
      </span>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Daily Summary</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {isAdmin ? 'Team performance overview' : 'Your daily performance'}
          </p>
        </div>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            showHistory 
              ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300' 
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          {showHistory ? 'Hide History' : 'Show History'}
        </button>
      </div>

      {/* Date Navigator */}
      <div className="flex items-center justify-center gap-4 mb-6">
        <button
          onClick={() => navigateDate(-1)}
          className="p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 rounded-lg transition-colors"
        >
          <ChevronLeft size={24} />
        </button>
        <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <Calendar className="text-indigo-600" size={20} />
          <span className="font-semibold text-slate-900 dark:text-white">{formatDate(selectedDate)}</span>
          {isToday && (
            <span className="px-2 py-0.5 text-xs font-medium bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-full">Today</span>
          )}
        </div>
        <button
          onClick={() => navigateDate(1)}
          disabled={isToday}
          className="p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight size={24} />
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">Loading summary...</div>
      ) : !summary ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <Calendar className="mx-auto text-slate-300 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">No data available for this date</p>
        </div>
      ) : isAdmin ? (
        // Admin View
        <div>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-emerald-50 dark:from-emerald-900/30 to-teal-50 dark:to-teal-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="text-emerald-600" size={20} />
                <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">Total OMSET</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(summary.total_omset)}</p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 dark:from-blue-900/30 to-indigo-50 dark:to-indigo-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <UserPlus className="text-blue-600" size={20} />
                <span className="text-sm font-medium text-blue-700 dark:text-blue-400">Total NDP</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total_ndp || 0}</p>
            </div>
            <div className="bg-gradient-to-br from-violet-50 dark:from-violet-900/30 to-purple-50 dark:to-purple-900/30 border border-violet-200 dark:border-violet-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <RefreshCcw className="text-violet-600" size={20} />
                <span className="text-sm font-medium text-violet-700">Total RDP</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total_rdp || 0}</p>
            </div>
            <div className="bg-gradient-to-br from-amber-50 dark:from-amber-900/30 to-orange-50 dark:to-orange-900/30 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Users className="text-amber-600" size={20} />
                <span className="text-sm font-medium text-amber-700">Total Forms</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total_forms || 0}</p>
            </div>
          </div>

          {/* Top Performer */}
          {summary.top_performer && (
            <div className="bg-gradient-to-r from-yellow-50 dark:from-yellow-900/30 via-amber-50 dark:via-amber-900/30 to-orange-50 dark:to-orange-900/30 border border-yellow-200 dark:border-yellow-800 rounded-xl p-5 mb-6">
              <div className="flex items-center gap-3 mb-3">
                <Trophy className="text-yellow-600" size={24} />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Top Performer of the Day</h3>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.top_performer.staff_name}</p>
                  <p className="text-sm text-slate-600 mt-1">
                    {formatCurrency(summary.top_performer.omset)} • {summary.top_performer.ndp} NDP • {summary.top_performer.rdp} RDP
                  </p>
                </div>
                <div className="text-right">
                  <Trophy className="text-yellow-500 mx-auto" size={48} />
                </div>
              </div>
            </div>
          )}

          {/* Staff Breakdown */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden mb-6">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
              <h3 className="font-semibold text-slate-900 dark:text-white">Staff Performance Breakdown</h3>
              <p className="text-xs text-slate-500 mt-1">Click on a staff member to see their product breakdown</p>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {(summary.staff_breakdown || []).length === 0 ? (
                <div className="p-8 text-center text-slate-500 dark:text-slate-400">No staff data for this date</div>
              ) : (
                summary.staff_breakdown.map((staff, index) => (
                  <div key={staff.staff_id}>
                    <div 
                      className="p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer"
                      onClick={() => toggleStaffExpand(staff.staff_id)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                          index === 0 ? 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300' :
                          index === 1 ? 'bg-slate-200 text-slate-700' :
                          index === 2 ? 'bg-orange-100 text-orange-700' :
                          'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-white">{staff.staff_name}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{staff.form_count} forms submitted</p>
                        </div>
                        {staff.product_breakdown && staff.product_breakdown.length > 0 && (
                          expandedStaff[staff.staff_id] ? 
                            <ChevronUp size={18} className="text-slate-400" /> : 
                            <ChevronDown size={18} className="text-slate-400" />
                        )}
                      </div>
                      <div className="flex items-center gap-6 text-right">
                        <div>
                          <p className="font-bold text-emerald-600">{formatCurrency(staff.total_omset)}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">OMSET</p>
                        </div>
                        <div>
                          <p className="font-bold text-blue-600">{staff.ndp_count}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">NDP</p>
                        </div>
                        <div>
                          <p className="font-bold text-violet-600">{staff.rdp_count}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">RDP</p>
                        </div>
                      </div>
                    </div>
                    {/* Staff's Product Breakdown */}
                    {expandedStaff[staff.staff_id] && staff.product_breakdown && staff.product_breakdown.length > 0 && (
                      <div className="bg-slate-50 dark:bg-slate-900 border-t border-slate-100 px-4 py-3">
                        <p className="text-xs font-medium text-slate-500 mb-2 pl-12">Product Breakdown:</p>
                        <div className="pl-12 space-y-2">
                          {staff.product_breakdown.map((product) => (
                            <div key={product.product_id} className="flex items-center justify-between bg-white dark:bg-slate-800 rounded-lg p-3 border border-slate-200">
                              <div className="flex items-center gap-2">
                                <Package size={14} className="text-indigo-500" />
                                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{product.product_name}</span>
                              </div>
                              <div className="flex items-center gap-4 text-xs">
                                <span className="text-emerald-600 font-semibold">{formatCurrency(product.total_omset)}</span>
                                <span className="text-blue-600">{product.ndp_count} NDP</span>
                                <span className="text-violet-600">{product.rdp_count} RDP</span>
                                <span className="text-slate-500 dark:text-slate-400">{product.form_count} forms</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Overall Product Breakdown */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
            <div 
              className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex items-center justify-between cursor-pointer"
              onClick={() => setShowProductBreakdown(!showProductBreakdown)}
            >
              <div className="flex items-center gap-2">
                <Package className="text-indigo-600" size={20} />
                <h3 className="font-semibold text-slate-900 dark:text-white">Product Performance</h3>
              </div>
              {showProductBreakdown ? <ChevronUp size={20} className="text-slate-400" /> : <ChevronDown size={20} className="text-slate-400" />}
            </div>
            {showProductBreakdown && (
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {(summary.product_breakdown || []).length === 0 ? (
                  <div className="p-8 text-center text-slate-500 dark:text-slate-400">No product data for this date</div>
                ) : (
                  summary.product_breakdown.map((product, index) => (
                    <div key={product.product_id} className="p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700">
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                          index === 0 ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300' :
                          index === 1 ? 'bg-slate-200 text-slate-700' :
                          index === 2 ? 'bg-purple-100 text-purple-700' :
                          'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-white">{product.product_name}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{product.form_count} deposits</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 text-right">
                        <div>
                          <p className="font-bold text-emerald-600">{formatCurrency(product.total_omset)}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">OMSET</p>
                        </div>
                        <div>
                          <p className="font-bold text-blue-600">{product.ndp_count}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">NDP</p>
                        </div>
                        <div>
                          <p className="font-bold text-violet-600">{product.rdp_count}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">RDP</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        // Staff View
        <div>
          {/* My Rank */}
          {summary.my_rank && (
            <div className="flex justify-center mb-6">
              {getRankBadge(summary.my_rank, summary.total_staff)}
            </div>
          )}

          {/* My Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-emerald-50 dark:from-emerald-900/30 to-teal-50 dark:to-teal-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="text-emerald-600" size={20} />
                <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">My OMSET</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(summary.my_stats?.total_omset)}</p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 dark:from-blue-900/30 to-indigo-50 dark:to-indigo-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <UserPlus className="text-blue-600" size={20} />
                <span className="text-sm font-medium text-blue-700 dark:text-blue-400">My NDP</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.my_stats?.ndp_count || 0}</p>
            </div>
            <div className="bg-gradient-to-br from-violet-50 dark:from-violet-900/30 to-purple-50 dark:to-purple-900/30 border border-violet-200 dark:border-violet-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <RefreshCcw className="text-violet-600" size={20} />
                <span className="text-sm font-medium text-violet-700">My RDP</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.my_stats?.rdp_count || 0}</p>
            </div>
            <div className="bg-gradient-to-br from-amber-50 dark:from-amber-900/30 to-orange-50 dark:to-orange-900/30 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Target className="text-amber-600" size={20} />
                <span className="text-sm font-medium text-amber-700">My Forms</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.my_stats?.form_count || 0}</p>
            </div>
          </div>

          {/* Team Comparison */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 mb-6">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Team Comparison</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-sm text-slate-500 mb-1">Team Total OMSET</p>
                <p className="text-lg font-bold text-slate-900 dark:text-white">{formatCurrency(summary.team_total_omset)}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500 mb-1">Team NDP</p>
                <p className="text-lg font-bold text-slate-900 dark:text-white">{summary.team_total_ndp || 0}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500 mb-1">Team RDP</p>
                <p className="text-lg font-bold text-slate-900 dark:text-white">{summary.team_total_rdp || 0}</p>
              </div>
            </div>
          </div>

          {/* Top Performer */}
          {summary.top_performer && summary.top_performer.staff_id !== summary.my_stats?.staff_id && (
            <div className="bg-gradient-to-r from-yellow-50 dark:from-yellow-900/30 via-amber-50 dark:via-amber-900/30 to-orange-50 dark:to-orange-900/30 border border-yellow-200 dark:border-yellow-800 rounded-xl p-5 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <Trophy className="text-yellow-600" size={20} />
                <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">Today&apos;s Top Performer</span>
              </div>
              <p className="text-xl font-bold text-slate-900 dark:text-white">{summary.top_performer.staff_name}</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {formatCurrency(summary.top_performer.omset)} • {summary.top_performer.ndp} NDP • {summary.top_performer.rdp} RDP
              </p>
            </div>
          )}

          {/* My Product Breakdown */}
          {summary.my_stats?.product_breakdown && summary.my_stats.product_breakdown.length > 0 && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden mb-6">
              <div 
                className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex items-center justify-between cursor-pointer"
                onClick={() => setShowProductBreakdown(!showProductBreakdown)}
              >
                <div className="flex items-center gap-2">
                  <Package className="text-indigo-600" size={20} />
                  <h3 className="font-semibold text-slate-900 dark:text-white">My Product Performance</h3>
                </div>
                {showProductBreakdown ? <ChevronUp size={20} className="text-slate-400" /> : <ChevronDown size={20} className="text-slate-400" />}
              </div>
              {showProductBreakdown && (
                <div className="divide-y divide-slate-100 dark:divide-slate-700">
                  {summary.my_stats.product_breakdown.map((product, index) => (
                    <div key={product.product_id} className="p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700">
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                          index === 0 ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300' :
                          index === 1 ? 'bg-slate-200 text-slate-700' :
                          index === 2 ? 'bg-purple-100 text-purple-700' :
                          'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-white">{product.product_name}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{product.form_count} deposits</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 text-right">
                        <div>
                          <p className="font-bold text-emerald-600">{formatCurrency(product.total_omset)}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">OMSET</p>
                        </div>
                        <div>
                          <p className="font-bold text-blue-600">{product.ndp_count}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">NDP</p>
                        </div>
                        <div>
                          <p className="font-bold text-violet-600">{product.rdp_count}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">RDP</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Team Product Breakdown */}
          {summary.product_breakdown && summary.product_breakdown.length > 0 && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                <div className="flex items-center gap-2">
                  <Package className="text-slate-600" size={18} />
                  <h3 className="font-semibold text-slate-900 dark:text-white">Team Product Performance</h3>
                </div>
              </div>
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {summary.product_breakdown.map((product, index) => (
                  <div key={product.product_id} className="p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700">
                    <div className="flex items-center gap-4">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                        index === 0 ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300' :
                        'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                      }`}>
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white">{product.product_name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{product.form_count} deposits</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-right text-sm">
                      <span className="font-semibold text-emerald-600">{formatCurrency(product.total_omset)}</span>
                      <span className="text-blue-600">{product.ndp_count} NDP</span>
                      <span className="text-violet-600">{product.rdp_count} RDP</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* History Section */}
      {showHistory && history.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Last 7 Days</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {history.map((day) => (
              <div
                key={day.date}
                className={`bg-white border rounded-xl p-4 cursor-pointer transition-all hover:shadow-md ${
                  day.date === selectedDate ? 'ring-2 ring-indigo-500 border-indigo-300' : 'border-slate-200'
                }`}
                onClick={() => setSelectedDate(day.date)}
              >
                <p className="text-sm font-medium text-slate-900 mb-2">{formatShortDate(day.date)}</p>
                {isAdmin ? (
                  <div className="space-y-1">
                    <p className="text-lg font-bold text-emerald-600">{formatCurrency(day.total_omset)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {day.total_ndp} NDP • {day.total_rdp} RDP
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-lg font-bold text-emerald-600">{formatCurrency(day.my_stats?.total_omset)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {day.my_stats?.ndp_count || 0} NDP • {day.my_stats?.rdp_count || 0} RDP
                      {day.my_rank && ` • #${day.my_rank}`}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
