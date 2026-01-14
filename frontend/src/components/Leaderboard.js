import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Trophy, Medal, Target, TrendingUp, Users, DollarSign, UserPlus, RefreshCcw, Settings, Save, RotateCcw } from 'lucide-react';

export default function Leaderboard({ isAdmin = false }) {
  const [leaderboard, setLeaderboard] = useState([]);
  const [targets, setTargets] = useState({ monthly_omset: 0, daily_ndp: 0, daily_rdp: 0 });
  const [period, setPeriod] = useState('month');
  const [activeTab, setActiveTab] = useState('omset');
  const [loading, setLoading] = useState(true);
  const [showTargetEditor, setShowTargetEditor] = useState(false);
  const [editTargets, setEditTargets] = useState({ monthly_omset: 0, daily_ndp: 0, daily_rdp: 0 });
  const [periodInfo, setPeriodInfo] = useState({ year: 2026, month: 1, today: '' });

  const loadLeaderboard = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/leaderboard?period=${period}`);
      setLeaderboard(response.data.leaderboard || []);
      setTargets(response.data.targets || { monthly_omset: 0, daily_ndp: 0, daily_rdp: 0 });
      setPeriodInfo({
        year: response.data.year,
        month: response.data.month,
        today: response.data.today
      });
    } catch (error) {
      toast.error('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    loadLeaderboard();
  }, [loadLeaderboard]);

  const handleSaveTargets = async () => {
    try {
      await api.put('/leaderboard/targets', editTargets);
      toast.success('Targets updated successfully');
      setTargets(editTargets);
      setShowTargetEditor(false);
    } catch (error) {
      toast.error('Failed to update targets');
    }
  };

  const handleResetTargets = async () => {
    if (!window.confirm('Reset targets to default values?')) return;
    try {
      const response = await api.post('/leaderboard/targets/reset');
      toast.success('Targets reset to defaults');
      setTargets(response.data.targets);
      setEditTargets(response.data.targets);
      setShowTargetEditor(false);
    } catch (error) {
      toast.error('Failed to reset targets');
    }
  };

  const formatCurrency = (amount) => {
    if (amount >= 1000000000) {
      return `Rp ${(amount / 1000000000).toFixed(2)}B`;
    } else if (amount >= 1000000) {
      return `Rp ${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `Rp ${(amount / 1000).toFixed(0)}K`;
    }
    return `Rp ${amount.toLocaleString('id-ID')}`;
  };

  const formatCurrencyFull = (amount) => {
    return `Rp ${amount.toLocaleString('id-ID')}`;
  };

  const getMonthName = (month) => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[month - 1];
  };

  const getRankIcon = (rank) => {
    if (rank === 1) return <Trophy className="text-yellow-500" size={20} />;
    if (rank === 2) return <Medal className="text-gray-400" size={20} />;
    if (rank === 3) return <Medal className="text-amber-600" size={20} />;
    return <span className="text-slate-500 font-medium w-5 text-center">{rank}</span>;
  };

  const getRankBg = (rank) => {
    if (rank === 1) return 'bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/30 dark:to-amber-900/30 border-yellow-200 dark:border-yellow-800';
    if (rank === 2) return 'bg-gradient-to-r from-slate-50 to-gray-50 dark:from-slate-800 dark:to-gray-800 border-gray-200 dark:border-gray-700';
    if (rank === 3) return 'bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-900/30 dark:to-amber-900/30 border-orange-200 dark:border-orange-800';
    return 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700';
  };

  const calculateProgress = (current, target) => {
    if (target <= 0) return 0;
    return Math.min((current / target) * 100, 100);
  };

  const getProgressColor = (progress) => {
    if (progress >= 100) return 'bg-emerald-500';
    if (progress >= 75) return 'bg-blue-500';
    if (progress >= 50) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const sortedLeaderboard = [...leaderboard].sort((a, b) => {
    if (activeTab === 'omset') return b.total_omset - a.total_omset;
    if (activeTab === 'ndp') return b.total_ndp - a.total_ndp;
    if (activeTab === 'rdp') return b.total_rdp - a.total_rdp;
    return 0;
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Staff Leaderboard</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {period === 'month' 
              ? `${getMonthName(periodInfo.month)} ${periodInfo.year}` 
              : 'All Time'} Rankings
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadLeaderboard}
            className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RefreshCcw size={16} />
          </button>
          {isAdmin && (
            <button
              onClick={() => {
                setEditTargets(targets);
                setShowTargetEditor(true);
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
              data-testid="edit-targets-btn"
            >
              <Settings size={16} />
              Edit Targets
            </button>
          )}
        </div>
      </div>

      {/* Target Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="text-emerald-600 dark:text-emerald-400" size={18} />
            <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">Monthly OMSET Target</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(targets.monthly_omset)}</p>
        </div>
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <UserPlus className="text-blue-600 dark:text-blue-400" size={18} />
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Daily NDP Target</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{targets.daily_ndp} NDP/day</p>
        </div>
        <div className="bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-900/30 dark:to-purple-900/30 border border-violet-200 dark:border-violet-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <RefreshCcw className="text-violet-600 dark:text-violet-400" size={18} />
            <span className="text-sm font-medium text-violet-700 dark:text-violet-300">Daily RDP Target</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{targets.daily_rdp} RDP/day</p>
        </div>
      </div>

      {/* Period Toggle & Tabs */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        {/* Ranking Tabs */}
        <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('omset')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'omset' 
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <DollarSign size={16} className="inline mr-1" />
            OMSET
          </button>
          <button
            onClick={() => setActiveTab('ndp')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'ndp' 
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <UserPlus size={16} className="inline mr-1" />
            NDP
          </button>
          <button
            onClick={() => setActiveTab('rdp')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'rdp' 
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <RefreshCcw size={16} className="inline mr-1" />
            RDP
          </button>
        </div>

        {/* Period Toggle */}
        <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => setPeriod('month')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              period === 'month' 
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            This Month
          </button>
          <button
            onClick={() => setPeriod('all')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              period === 'all' 
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            All Time
          </button>
        </div>
      </div>

      {/* Leaderboard List */}
      {loading ? (
        <div className="text-center py-12 text-slate-600 dark:text-slate-400">Loading leaderboard...</div>
      ) : sortedLeaderboard.length === 0 ? (
        <div className="text-center py-12">
          <Users className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={64} />
          <p className="text-slate-600 dark:text-slate-400">No data available</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="leaderboard-list">
          {sortedLeaderboard.map((staff, index) => {
            const rank = index + 1;
            const omsetProgress = calculateProgress(staff.total_omset, targets.monthly_omset);
            const ndpProgress = calculateProgress(staff.avg_daily_ndp, targets.daily_ndp);
            const rdpProgress = calculateProgress(staff.avg_daily_rdp, targets.daily_rdp);
            
            return (
              <div
                key={staff.staff_id}
                className={`border rounded-xl p-4 transition-all hover:shadow-md ${getRankBg(rank)}`}
                data-testid={`leaderboard-item-${staff.staff_id}`}
              >
                <div className="flex items-center gap-4">
                  {/* Rank */}
                  <div className="flex items-center justify-center w-10 h-10 rounded-full bg-white shadow-sm">
                    {getRankIcon(rank)}
                  </div>

                  {/* Staff Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-slate-900 truncate">{staff.staff_name}</h3>
                      {rank <= 3 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          rank === 1 ? 'bg-yellow-100 text-yellow-700' :
                          rank === 2 ? 'bg-gray-100 text-gray-700' :
                          'bg-orange-100 text-orange-700'
                        }`}>
                          #{rank}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500">{staff.days_worked} days worked</p>
                  </div>

                  {/* Stats */}
                  <div className="hidden md:flex items-center gap-6">
                    {/* OMSET */}
                    <div className="text-center">
                      <p className={`text-lg font-bold ${activeTab === 'omset' ? 'text-emerald-600' : 'text-slate-700'}`}>
                        {formatCurrency(staff.total_omset)}
                      </p>
                      <p className="text-xs text-slate-500">OMSET</p>
                    </div>
                    
                    {/* NDP */}
                    <div className="text-center">
                      <p className={`text-lg font-bold ${activeTab === 'ndp' ? 'text-blue-600' : 'text-slate-700'}`}>
                        {staff.total_ndp}
                      </p>
                      <p className="text-xs text-slate-500">NDP</p>
                    </div>
                    
                    {/* RDP */}
                    <div className="text-center">
                      <p className={`text-lg font-bold ${activeTab === 'rdp' ? 'text-violet-600' : 'text-slate-700'}`}>
                        {staff.total_rdp}
                      </p>
                      <p className="text-xs text-slate-500">RDP</p>
                    </div>

                    {/* Today Stats */}
                    <div className="text-center border-l pl-6">
                      <p className="text-sm font-medium text-slate-900">
                        {staff.today_ndp}/{staff.today_rdp}
                      </p>
                      <p className="text-xs text-slate-500">Today NDP/RDP</p>
                    </div>
                  </div>
                </div>

                {/* Progress Bars */}
                <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* OMSET Progress */}
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-600">Monthly OMSET</span>
                      <span className="font-medium">{omsetProgress.toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${getProgressColor(omsetProgress)} transition-all duration-500`}
                        style={{ width: `${omsetProgress}%` }}
                      />
                    </div>
                  </div>

                  {/* NDP Progress */}
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-600">Avg Daily NDP</span>
                      <span className="font-medium">{staff.avg_daily_ndp.toFixed(1)} / {targets.daily_ndp}</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${getProgressColor(ndpProgress)} transition-all duration-500`}
                        style={{ width: `${ndpProgress}%` }}
                      />
                    </div>
                  </div>

                  {/* RDP Progress */}
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-600">Avg Daily RDP</span>
                      <span className="font-medium">{staff.avg_daily_rdp.toFixed(1)} / {targets.daily_rdp}</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${getProgressColor(rdpProgress)} transition-all duration-500`}
                        style={{ width: `${rdpProgress}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Mobile Stats */}
                <div className="md:hidden mt-3 grid grid-cols-4 gap-2 text-center">
                  <div>
                    <p className="text-sm font-bold text-emerald-600">{formatCurrency(staff.total_omset)}</p>
                    <p className="text-xs text-slate-500">OMSET</p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-blue-600">{staff.total_ndp}</p>
                    <p className="text-xs text-slate-500">NDP</p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-violet-600">{staff.total_rdp}</p>
                    <p className="text-xs text-slate-500">RDP</p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-700">{staff.today_ndp}/{staff.today_rdp}</p>
                    <p className="text-xs text-slate-500">Today</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Target Editor Modal */}
      {showTargetEditor && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <h3 className="text-xl font-semibold text-slate-900 mb-4">Edit Targets</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Monthly OMSET Target (Rp)
                </label>
                <input
                  type="number"
                  value={editTargets.monthly_omset}
                  onChange={(e) => setEditTargets({ ...editTargets, monthly_omset: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 100000000"
                />
                <p className="text-xs text-slate-500 mt-1">{formatCurrencyFull(editTargets.monthly_omset)}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Daily NDP Target
                </label>
                <input
                  type="number"
                  value={editTargets.daily_ndp}
                  onChange={(e) => setEditTargets({ ...editTargets, daily_ndp: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 10"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Daily RDP Target
                </label>
                <input
                  type="number"
                  value={editTargets.daily_rdp}
                  onChange={(e) => setEditTargets({ ...editTargets, daily_rdp: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 15"
                />
              </div>
            </div>

            <div className="flex items-center justify-between mt-6">
              <button
                onClick={handleResetTargets}
                className="flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <RotateCcw size={16} />
                Reset to Default
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowTargetEditor(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveTargets}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
                >
                  <Save size={16} />
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
