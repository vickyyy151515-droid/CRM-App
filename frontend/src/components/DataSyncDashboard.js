import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Wrench,
  Activity,
  Database,
  Users,
  Calendar,
  Bell,
  FileText,
  Clock,
  Shield,
  Zap
} from 'lucide-react';

export default function DataSyncDashboard() {
  const [healthData, setHealthData] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [repairing, setRepairing] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [healthRes, syncRes, logRes] = await Promise.all([
        api.get('/data-sync/health-check'),
        api.get('/data-sync/sync-status'),
        api.get('/data-sync/activity-log?limit=10')
      ]);
      
      setHealthData(healthRes.data);
      setSyncStatus(syncRes.data);
      setActivityLog(logRes.data.logs || []);
    } catch (error) {
      console.error('Error loading data sync info:', error);
      toast.error('Failed to load data sync status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRepair = async (repairType) => {
    setRepairing(true);
    try {
      const res = await api.post(`/data-sync/repair?repair_type=${repairType}`);
      toast.success(`Repair completed: ${repairType}`);
      // Reload data after repair
      await loadData();
    } catch (error) {
      console.error('Repair error:', error);
      toast.error('Repair failed');
    } finally {
      setRepairing(false);
    }
  };

  const getHealthColor = (score) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'synced':
      case 'active':
      case 'healthy':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'partial':
      case 'warning':
      case 'needs_attention':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'not_synced':
      case 'needs_repair':
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-500" />;
    }
  };

  const getSeverityBadge = (severity) => {
    const colors = {
      high: 'bg-red-100 text-red-800 border-red-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-blue-100 text-blue-800 border-blue-200'
    };
    return colors[severity] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('id-ID', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Data Sync Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Monitor and repair data synchronization across all features
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            onClick={async () => {
              try {
                const res = await api.post('/data-sync/proactive-check');
                if (res.data.notifications_sent > 0) {
                  toast.success(`Sent ${res.data.notifications_sent} notifications to admins`);
                } else {
                  toast.info('No critical issues - no notifications needed');
                }
                await loadData();
              } catch (error) {
                toast.error('Failed to run proactive check');
              }
            }}
            variant="outline"
            className="text-amber-600 border-amber-300 hover:bg-amber-50"
            data-testid="proactive-check-btn"
          >
            <Bell className="w-4 h-4 mr-2" />
            Run Proactive Check
          </Button>
          <Button onClick={loadData} variant="outline" disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Health Score Card */}
      {healthData && (
        <Card className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-6">
                <div className="relative">
                  <svg className="w-24 h-24 transform -rotate-90">
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      stroke="currentColor"
                      strokeWidth="8"
                      fill="none"
                      className="text-gray-200 dark:text-gray-700"
                    />
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      stroke="currentColor"
                      strokeWidth="8"
                      fill="none"
                      strokeDasharray={`${healthData.health_score * 2.51} 251`}
                      className={getHealthColor(healthData.health_score)}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-2xl font-bold ${getHealthColor(healthData.health_score)}`}>
                      {healthData.health_score}%
                    </span>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    System Health
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                    Status: {healthData.status}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Last checked: {formatDate(healthData.checked_at)}
                  </p>
                </div>
              </div>
              
              {/* Quick Stats */}
              <div className="grid grid-cols-4 gap-4">
                {healthData.stats?.collections && (
                  <>
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <Users className="w-5 h-5 mx-auto text-blue-500 mb-1" />
                      <p className="text-lg font-semibold">{healthData.stats.collections.users || 0}</p>
                      <p className="text-xs text-gray-500">Users</p>
                    </div>
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <Database className="w-5 h-5 mx-auto text-purple-500 mb-1" />
                      <p className="text-lg font-semibold">{healthData.stats.collections.reserved_members || 0}</p>
                      <p className="text-xs text-gray-500">Reserved</p>
                    </div>
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <FileText className="w-5 h-5 mx-auto text-green-500 mb-1" />
                      <p className="text-lg font-semibold">{healthData.stats.collections.omset_records || 0}</p>
                      <p className="text-xs text-gray-500">Omset</p>
                    </div>
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <Bell className="w-5 h-5 mx-auto text-orange-500 mb-1" />
                      <p className="text-lg font-semibold">{healthData.stats.collections.notifications || 0}</p>
                      <p className="text-xs text-gray-500">Notif</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sync Features Status */}
      {syncStatus && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center">
                  <Zap className="w-5 h-5 mr-2 text-yellow-500" />
                  Feature Sync Status
                </CardTitle>
                <CardDescription>
                  {syncStatus.synced_features}/{syncStatus.total_features} features properly synchronized
                </CardDescription>
              </div>
              {syncStatus.synced_features < syncStatus.total_features && (
                <Button 
                  onClick={() => handleRepair('all')}
                  disabled={repairing}
                  size="sm"
                >
                  <Wrench className="w-4 h-4 mr-2" />
                  {repairing ? 'Repairing...' : 'Sync All'}
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              {syncStatus.features?.map((feature, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(feature.status)}
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{feature.feature}</p>
                      <p className="text-sm text-gray-500">{feature.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="outline" className={
                      feature.status === 'synced' || feature.status === 'active' 
                        ? 'bg-green-50 text-green-700 border-green-200'
                        : feature.status === 'partial' 
                        ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
                        : 'bg-red-50 text-red-700 border-red-200'
                    }>
                      {feature.status}
                    </Badge>
                    <p className="text-xs text-gray-400 mt-1">{feature.details}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Issues and Warnings */}
      {healthData && (healthData.issues?.length > 0 || healthData.warnings?.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="w-5 h-5 mr-2 text-yellow-500" />
              Issues Detected
            </CardTitle>
            <CardDescription>
              {healthData.issues?.length || 0} issues, {healthData.warnings?.length || 0} warnings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {/* Critical and Medium Issues */}
              {healthData.issues?.map((issue, idx) => (
                <div 
                  key={`issue-${idx}`}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    {issue.severity === 'high' ? (
                      <XCircle className="w-5 h-5 text-red-500" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    )}
                    <div>
                      <div className="flex items-center space-x-2">
                        <p className="font-medium text-gray-900 dark:text-white">{issue.message}</p>
                        <Badge className={getSeverityBadge(issue.severity)}>
                          {issue.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500">
                        Type: {issue.type.replace(/_/g, ' ')} | Count: {issue.count}
                      </p>
                    </div>
                  </div>
                  {issue.auto_fixable && (
                    <Button 
                      size="sm" 
                      onClick={() => handleRepair(issue.type)}
                      disabled={repairing}
                    >
                      <Wrench className="w-4 h-4 mr-1" />
                      Fix
                    </Button>
                  )}
                </div>
              ))}
              
              {/* Warnings */}
              {healthData.warnings?.map((warning, idx) => (
                <div 
                  key={`warning-${idx}`}
                  className="flex items-center justify-between p-4 border rounded-lg bg-yellow-50 dark:bg-yellow-900/20"
                >
                  <div className="flex items-center space-x-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{warning.message}</p>
                      <p className="text-sm text-gray-500">
                        Type: {warning.type.replace(/_/g, ' ')}
                      </p>
                    </div>
                  </div>
                  {warning.auto_fixable && (
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleRepair(warning.type)}
                      disabled={repairing}
                    >
                      <Wrench className="w-4 h-4 mr-1" />
                      Fix
                    </Button>
                  )}
                </div>
              ))}
              
              {healthData.issues?.length === 0 && healthData.warnings?.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle2 className="w-12 h-12 mx-auto text-green-500 mb-2" />
                  <p>No issues detected. All data is properly synchronized.</p>
                </div>
              )}
            </div>
            
            {/* Repair All Button */}
            {(healthData.issues?.length > 0 || healthData.warnings?.length > 0) && (
              <div className="mt-4 pt-4 border-t">
                <Button 
                  onClick={() => handleRepair('all')}
                  disabled={repairing}
                  className="w-full"
                >
                  <Shield className="w-4 h-4 mr-2" />
                  {repairing ? 'Repairing...' : 'Repair All Issues'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Scheduler Status */}
      {healthData?.stats?.scheduler && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Clock className="w-5 h-5 mr-2 text-blue-500" />
              Scheduled Jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Daily Reports</span>
                  <Badge variant={healthData.stats.scheduler.reports_enabled ? 'default' : 'secondary'}>
                    {healthData.stats.scheduler.reports_enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500">
                  Last sent: {formatDate(healthData.stats.scheduler.last_report_sent) || 'Never'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">At-Risk Alerts</span>
                  <Badge variant={healthData.stats.scheduler.atrisk_enabled ? 'default' : 'secondary'}>
                    {healthData.stats.scheduler.atrisk_enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500">
                  Last sent: {formatDate(healthData.stats.scheduler.last_atrisk_sent) || 'Never'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Activity Log */}
      {activityLog.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="w-5 h-5 mr-2 text-purple-500" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {activityLog.map((log, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div>
                    <p className="text-sm font-medium">{log.type?.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-gray-500">
                      By: {log.performed_by_name || 'System'}
                    </p>
                  </div>
                  <p className="text-xs text-gray-400">{formatDate(log.performed_at)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
