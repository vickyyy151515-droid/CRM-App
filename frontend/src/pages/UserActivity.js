import { useState, useEffect, useRef } from 'react';
import { api } from '../App';
import { useLanguage } from '../contexts/LanguageContext';
import { Users, RefreshCw, Circle, Clock, Moon } from 'lucide-react';

/**
 * User Activity Page - READ-ONLY
 * 
 * CRITICAL: This page only READS data. It does NOT affect anyone's status.
 * - Admin viewing this page = NO effect on staff status
 * - All status calculations happen on the backend based on timestamps
 */
export default function UserActivity() {
  const { t } = useLanguage();
  const [users, setUsers] = useState([]);
  const [summary, setSummary] = useState({ total: 0, online: 0, idle: 0, offline: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef(null);

  const loadActivity = async () => {
    try {
      setError(null);
      const response = await api.get('/users/activity');
      setUsers(response.data.users || []);
      setSummary(response.data.summary || { total: 0, online: 0, idle: 0, offline: 0 });
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load activity data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActivity();
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(loadActivity, 30000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
        return <Circle className="w-3 h-3 fill-green-500 text-green-500" />;
      case 'idle':
        return <Clock className="w-3 h-3 text-yellow-500" />;
      default:
        return <Moon className="w-3 h-3 text-slate-400" />;
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      online: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      idle: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      offline: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
    };
    
    const labels = {
      online: 'Online',
      idle: 'Idle',
      offline: 'Offline'
    };
    
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] || styles.offline}`}>
        {getStatusIcon(status)}
        {labels[status] || 'Offline'}
      </span>
    );
  };

  const formatTime = (isoString) => {
    if (!isoString) return '-';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('id-ID', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '-';
    }
  };

  const formatMinutes = (minutes) => {
    if (minutes === null || minutes === undefined) return '-';
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${Math.floor(minutes)} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const getRoleBadge = (role) => {
    const styles = {
      master_admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      admin: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      staff: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
    };
    
    const labels = {
      master_admin: 'Master Admin',
      admin: 'Admin',
      staff: 'Staff'
    };
    
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[role] || styles.staff}`}>
        {labels[role] || role}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="user-activity-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
            <Users className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              {t('userActivity.title') || 'User Activity'}
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('userActivity.subtitle') || 'Monitor staff and admin activity status'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-slate-300 dark:border-slate-600"
              data-testid="auto-refresh-checkbox"
            />
            Auto-refresh
          </label>
          <button
            onClick={loadActivity}
            className="flex items-center gap-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 transition-colors"
            data-testid="refresh-btn"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
          <p className="text-sm text-slate-500 dark:text-slate-400">Total Users</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white" data-testid="total-users">
            {summary.total}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-green-200 dark:border-green-900">
          <p className="text-sm text-green-600 dark:text-green-400">Online</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400" data-testid="online-count">
            {summary.online}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-yellow-200 dark:border-yellow-900">
          <p className="text-sm text-yellow-600 dark:text-yellow-400">Idle</p>
          <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400" data-testid="idle-count">
            {summary.idle}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
          <p className="text-sm text-slate-500 dark:text-slate-400">Offline</p>
          <p className="text-2xl font-bold text-slate-600 dark:text-slate-400" data-testid="offline-count">
            {summary.offline}
          </p>
        </div>
      </div>

      {/* Status Legend */}
      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 flex items-center gap-6 text-sm">
        <span className="text-slate-500 dark:text-slate-400">Status:</span>
        <span className="flex items-center gap-1.5">
          <Circle className="w-2.5 h-2.5 fill-green-500 text-green-500" />
          Online (active &lt; 5 min)
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="w-2.5 h-2.5 text-yellow-500" />
          Idle (5-30 min)
        </span>
        <span className="flex items-center gap-1.5">
          <Moon className="w-2.5 h-2.5 text-slate-400" />
          Offline (60+ min or logged out)
        </span>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-900/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                User
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Role
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Last Activity
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Last Logout
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {users.map((user) => (
              <tr 
                key={user.id} 
                className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                data-testid={`user-row-${user.id}`}
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{user.name}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p>
                  </div>
                </td>
                <td className="px-4 py-3">
                  {getRoleBadge(user.role)}
                </td>
                <td className="px-4 py-3">
                  {getStatusBadge(user.status)}
                </td>
                <td className="px-4 py-3">
                  <div>
                    <p className="text-sm text-slate-900 dark:text-white">
                      {formatMinutes(user.minutes_since_activity)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {formatTime(user.last_activity)}
                    </p>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                  {formatTime(user.last_logout)}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                  No users found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Last Refresh Info */}
      {lastRefresh && (
        <p className="text-xs text-slate-400 dark:text-slate-500 text-right">
          Last updated: {lastRefresh.toLocaleTimeString()}
          {autoRefresh && ' (auto-refresh every 30s)'}
        </p>
      )}
    </div>
  );
}
