import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Users, 
  UserCheck, 
  Clock, 
  UserX, 
  RefreshCw,
  Circle,
  Activity,
  LogIn,
  LogOut
} from 'lucide-react';

export default function UserActivity() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadActivity = useCallback(async () => {
    try {
      const response = await api.get('/users/activity');
      setData(response.data);
      setLastRefresh(new Date());
    } catch (error) {
      toast.error('Failed to load user activity');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadActivity();
    
    // Auto-refresh every 30 seconds if enabled
    let interval;
    if (autoRefresh) {
      interval = setInterval(loadActivity, 30000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loadActivity, autoRefresh]);

  const formatTime = (isoString) => {
    if (!isoString) return '-';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('id-ID', { 
        timeZone: 'Asia/Jakarta',
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '-';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-emerald-500';
      case 'idle': return 'text-amber-500';
      case 'offline': return 'text-slate-400';
      default: return 'text-slate-400';
    }
  };

  const getStatusBg = (status) => {
    switch (status) {
      case 'online': return 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800';
      case 'idle': return 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800';
      case 'offline': return 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700';
      default: return 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700';
    }
  };

  const getStatusLabel = (status, idleMinutes) => {
    switch (status) {
      case 'online': return 'Online';
      case 'idle': return `Idle (${idleMinutes}m)`;
      case 'offline': return 'Offline';
      default: return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="user-activity-loading">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="user-activity-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Activity size={28} className="text-indigo-600" />
            User Activity Monitor
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Real-time user status and activity tracking
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            Auto-refresh
          </label>
          <button
            onClick={loadActivity}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            data-testid="btn-refresh"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-slate-100 dark:bg-slate-700 rounded-lg">
              <Users size={24} className="text-slate-600 dark:text-slate-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Total Users</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{data?.summary?.total || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg">
              <UserCheck size={24} className="text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Online</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{data?.summary?.online || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
              <Clock size={24} className="text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Idle</p>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{data?.summary?.idle || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-slate-100 dark:bg-slate-700 rounded-lg">
              <UserX size={24} className="text-slate-500 dark:text-slate-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Offline</p>
              <p className="text-2xl font-bold text-slate-600 dark:text-slate-400">{data?.summary?.offline || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Activity Thresholds Info */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <p className="text-sm text-blue-700 dark:text-blue-400">
          <strong>Status Thresholds:</strong> Users are marked as <span className="text-emerald-600 font-medium">Online</span> if active within {data?.thresholds?.idle_minutes || 5} minutes, 
          <span className="text-amber-600 font-medium"> Idle</span> if inactive for {data?.thresholds?.idle_minutes || 5}-{data?.thresholds?.offline_minutes || 30} minutes, 
          and <span className="text-slate-500 font-medium">Offline</span> after {data?.thresholds?.offline_minutes || 30} minutes.
        </p>
      </div>

      {/* User List */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900 dark:text-white">User Status</h2>
          {lastRefresh && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Last updated: {lastRefresh.toLocaleTimeString('id-ID')}
            </p>
          )}
        </div>
        
        <div className="divide-y divide-slate-100 dark:divide-slate-700">
          {data?.users?.map((user) => (
            <div 
              key={user.id} 
              className={`p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors`}
              data-testid={`user-row-${user.id}`}
            >
              <div className="flex items-center gap-4">
                {/* Status Indicator */}
                <div className="relative">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg ${
                    user.status === 'online' ? 'bg-emerald-500' :
                    user.status === 'idle' ? 'bg-amber-500' :
                    'bg-slate-400'
                  }`}>
                    {user.name?.charAt(0).toUpperCase() || '?'}
                  </div>
                  <div className={`absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-white dark:border-slate-800 ${
                    user.status === 'online' ? 'bg-emerald-500' :
                    user.status === 'idle' ? 'bg-amber-500' :
                    'bg-slate-400'
                  }`} />
                </div>
                
                {/* User Info */}
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-900 dark:text-white">{user.name}</p>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      user.role === 'admin' 
                        ? 'bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-400' 
                        : 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-400'
                    }`}>
                      {user.role}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
                </div>
              </div>
              
              {/* Status & Times */}
              <div className="flex items-center gap-6">
                {/* Status Badge */}
                <div className={`px-3 py-1.5 rounded-full border ${getStatusBg(user.status)}`}>
                  <div className="flex items-center gap-2">
                    <Circle size={8} className={`fill-current ${getStatusColor(user.status)}`} />
                    <span className={`text-sm font-medium ${getStatusColor(user.status)}`}>
                      {getStatusLabel(user.status, user.idle_minutes)}
                    </span>
                  </div>
                </div>
                
                {/* Activity Times */}
                <div className="text-right hidden md:block">
                  <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                    <LogIn size={12} />
                    <span>Login: {formatTime(user.last_login)}</span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mt-1">
                    <Activity size={12} />
                    <span>Active: {formatTime(user.last_activity)}</span>
                  </div>
                  {user.last_logout && (
                    <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mt-1">
                      <LogOut size={12} />
                      <span>Logout: {formatTime(user.last_logout)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {(!data?.users || data.users.length === 0) && (
            <div className="p-8 text-center text-slate-500 dark:text-slate-400">
              No users found
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-400">
        <div className="flex items-center gap-2">
          <Circle size={10} className="fill-emerald-500 text-emerald-500" />
          <span>Online - Active now</span>
        </div>
        <div className="flex items-center gap-2">
          <Circle size={10} className="fill-amber-500 text-amber-500" />
          <span>Idle - No recent activity</span>
        </div>
        <div className="flex items-center gap-2">
          <Circle size={10} className="fill-slate-400 text-slate-400" />
          <span>Offline - Logged out or inactive</span>
        </div>
      </div>
    </div>
  );
}
