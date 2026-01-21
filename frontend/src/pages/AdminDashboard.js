import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import UploadDatabase from '../components/UploadDatabase';
import DatabaseList from '../components/DatabaseList';
import DatabaseOverview from '../components/DatabaseOverview';
import DownloadRequests from '../components/DownloadRequests';
import DownloadHistory from '../components/DownloadHistory';
import CreateUser from '../components/CreateUser';
import ManageUsers from '../components/ManageUsers';
import ProductManagement from '../components/ProductManagement';
import AllAssignments from '../components/AllAssignments';
import StaffProgress from '../components/StaffProgress';
import AdminReservedMembers from '../components/AdminReservedMembers';
import AdminOmsetCRM from '../components/AdminOmsetCRM';
import AdminDBBonanza from '../components/AdminDBBonanza';
import AdminMemberWDCRM from '../components/AdminMemberWDCRM';
import AdvancedAnalytics from '../components/AdvancedAnalytics';
import ExportCenter from '../components/ExportCenter';
import ReportCRM from '../components/ReportCRM';
import BonusCalculation from '../components/BonusCalculation';
import AdminLeaveRequests from '../components/AdminLeaveRequests';
import LeaveCalendar from '../components/LeaveCalendar';
import AdminIzinMonitor from '../components/AdminIzinMonitor';
import Leaderboard from '../components/Leaderboard';
import DailySummary from '../components/DailySummary';
import ConversionFunnel from '../components/ConversionFunnel';
import CustomerRetention from '../components/CustomerRetention';
import ScheduledReports from './ScheduledReports';
import UserActivity from './UserActivity';
import OfficeInventory from '../components/OfficeInventory';
import AttendanceAdmin from './AttendanceAdmin';
import DataCleanup from './DataCleanup';
import { useLanguage } from '../contexts/LanguageContext';
import { LayoutDashboard, Upload, FileSpreadsheet, Clock, Users, Package, List, BarChart, UserCheck, DollarSign, UserCog, Gift, CreditCard, PieChart, Download, FileText, Calculator, CalendarOff, Calendar, Timer, Trophy, CalendarDays, Filter, Heart, Send, Boxes, Activity, ScanLine, Trash2 } from 'lucide-react';

export default function AdminDashboard({ user, onLogout }) {
  const { t, language } = useLanguage();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState({
    pendingRequests: 0,
    pendingReservations: 0,
    totalOmsetYear: 0,
    omsetYear: new Date().getFullYear(),
    monthlyAth: { date: null, amount: 0 }
  });

  const loadStats = useCallback(async () => {
    try {
      const [requests, reservations, omsetStats] = await Promise.all([
        api.get('/download-requests'),
        api.get('/reserved-members'),
        api.get('/omset/dashboard-stats')
      ]);

      setStats({
        pendingRequests: requests.data.filter(r => r.status === 'pending').length,
        pendingReservations: reservations.data.filter(r => r.status === 'pending').length,
        totalOmsetYear: omsetStats.data.total_omset_year || 0,
        omsetYear: omsetStats.data.year || new Date().getFullYear(),
        monthlyAth: omsetStats.data.monthly_ath || { date: null, amount: 0 }
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  }, []);

  useEffect(() => {
    loadStats();
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, [loadStats]);

  // ==================== ACTIVITY TRACKING ====================
  // Send heartbeat on click - tracks admin/master admin activity
  // This is INDEPENDENT - only updates THIS user's activity
  
  const sendHeartbeat = useCallback(async () => {
    try {
      await api.post('/auth/heartbeat');
    } catch (error) {
      console.debug('Heartbeat failed:', error.message);
    }
  }, []);

  // Track clicks as activity and send heartbeat (debounced)
  useEffect(() => {
    let debounceTimer = null;
    
    const handleClick = () => {
      // Debounce heartbeat to avoid flooding server (send max once per 5 seconds)
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(sendHeartbeat, 5000);
    };
    
    // Listen for clicks anywhere in the app
    document.addEventListener('click', handleClick);
    
    // Send initial heartbeat on mount
    sendHeartbeat();
    
    return () => {
      document.removeEventListener('click', handleClick);
      if (debounceTimer) clearTimeout(debounceTimer);
    };
  }, [sendHeartbeat]);

  // Format currency to Indonesian Rupiah
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

  // Format date to readable format
  const formatAthDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white mb-6">{t('dashboard.title')}</h2>
            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              {/* Pending DB Requests */}
              <div 
                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm cursor-pointer hover:border-amber-300 dark:hover:border-amber-600 transition-colors" 
                data-testid="stat-pending-requests"
                onClick={() => setActiveTab('requests')}
              >
                <div className="flex items-center justify-between mb-3">
                  <Clock className="text-amber-600 dark:text-amber-400" size={24} />
                  <span className="text-2xl font-bold text-slate-900 dark:text-white">{stats.pendingRequests}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{t('dashboard.pendingRequests')}</p>
              </div>
              
              {/* Pending Reservations */}
              <div 
                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm cursor-pointer hover:border-amber-300 dark:hover:border-amber-600 transition-colors" 
                data-testid="stat-pending-reservations"
                onClick={() => setActiveTab('reserved')}
              >
                <div className="flex items-center justify-between mb-3">
                  <UserCheck className="text-amber-600 dark:text-amber-400" size={24} />
                  <span className="text-2xl font-bold text-slate-900 dark:text-white">{stats.pendingReservations}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{t('dashboard.pendingReservations')}</p>
              </div>
              
              {/* Monthly ATH Card */}
              <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/30 dark:to-orange-900/30 border border-amber-200 dark:border-amber-800 rounded-xl p-6 shadow-sm" data-testid="stat-monthly-ath">
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
                    <BarChart className="text-amber-600 dark:text-amber-400" size={20} />
                  </div>
                  <span className="text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/50 px-2 py-1 rounded-full">
                    {stats.monthlyAth.date ? formatAthDate(stats.monthlyAth.date) : t('common.noData')}
                  </span>
                </div>
                <p className="text-xl font-bold text-slate-900 dark:text-white mt-2">{formatCurrency(stats.monthlyAth.amount)}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{t('dashboard.monthlyATH')}</p>
              </div>
              
              {/* OMSET Year Card */}
              <div 
                className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-6 shadow-sm cursor-pointer hover:border-emerald-300 dark:hover:border-emerald-600 transition-colors" 
                data-testid="stat-omset-year"
                onClick={() => setActiveTab('omset')}
              >
                <div className="flex items-center justify-between mb-3">
                  <DollarSign className="text-emerald-600 dark:text-emerald-400" size={24} />
                </div>
                <p className="text-xl font-bold text-slate-900 dark:text-white">{formatCurrency(stats.totalOmsetYear)}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{t('dashboard.omsetYear')} {stats.omsetYear}</p>
              </div>
            </div>
            {/* Real-time Database Overview with Record Stats */}
            <DatabaseOverview />
          </div>
        );
      case 'upload':
        return <UploadDatabase onUploadSuccess={loadStats} />;
      case 'databases':
        return <DatabaseList onUpdate={loadStats} />;
      case 'requests':
        return <DownloadRequests onUpdate={loadStats} />;
      case 'history':
        return <DownloadHistory />;
      case 'users':
        return <CreateUser currentUser={user} />;
      case 'manage-users':
        return <ManageUsers currentUser={user} />;
      case 'products':
        return <ProductManagement />;
      case 'assignments':
        return <AllAssignments />;
      case 'progress':
        return <StaffProgress />;
      case 'reserved':
        return <AdminReservedMembers onUpdate={loadStats} />;
      case 'omset':
        return <AdminOmsetCRM />;
      case 'bonanza':
        return <AdminDBBonanza />;
      case 'memberwd':
        return <AdminMemberWDCRM />;
      case 'analytics':
        return <AdvancedAnalytics />;
      case 'export':
        return <ExportCenter />;
      case 'report':
        return <ReportCRM />;
      case 'bonus':
        return <BonusCalculation />;
      case 'leave':
        return <AdminLeaveRequests />;
      case 'leave-calendar':
        return <LeaveCalendar />;
      case 'izin-monitor':
        return <AdminIzinMonitor />;
      case 'leaderboard':
        return <Leaderboard isAdmin={true} />;
      case 'daily-summary':
        return <DailySummary isAdmin={true} />;
      case 'funnel':
        return <ConversionFunnel isAdmin={true} />;
      case 'retention':
        return <CustomerRetention isAdmin={true} />;
      case 'scheduled-reports':
        return <ScheduledReports />;
      case 'user-activity':
        return <UserActivity />;
      case 'attendance':
        return <AttendanceAdmin />;
      case 'inventory':
        return <OfficeInventory />;
      default:
        return null;
    }
  };

  const allMenuItems = useMemo(() => [
    { id: 'overview', label: t('nav.overview'), icon: LayoutDashboard, badge: 0 },
    { id: 'leaderboard', label: t('nav.leaderboard'), icon: Trophy, badge: 0 },
    { id: 'daily-summary', label: t('nav.dailySummary'), icon: CalendarDays, badge: 0 },
    { id: 'funnel', label: t('nav.conversionFunnel'), icon: Filter, badge: 0 },
    { id: 'retention', label: t('nav.customerRetention'), icon: Heart, badge: 0 },
    { id: 'analytics', label: t('nav.advancedAnalytics'), icon: PieChart, badge: 0 },
    { id: 'export', label: t('nav.exportCenter'), icon: Download, badge: 0 },
    { id: 'scheduled-reports', label: t('nav.scheduledReports') || 'Scheduled Reports', icon: Send, badge: 0 },
    { id: 'user-activity', label: t('nav.userActivity') || 'User Activity', icon: Activity, badge: 0 },
    { id: 'attendance', label: t('nav.attendance') || 'Attendance', icon: ScanLine, badge: 0 },
    { id: 'report', label: t('nav.reportCRM'), icon: FileText, badge: 0 },
    { id: 'bonus', label: t('nav.bonusCalculation'), icon: Calculator, badge: 0 },
    { id: 'leave', label: t('nav.leaveRequests'), icon: CalendarOff, badge: 0 },
    { id: 'leave-calendar', label: t('nav.leaveCalendar'), icon: Calendar, badge: 0 },
    { id: 'izin-monitor', label: t('nav.monitorIzin'), icon: Timer, badge: 0 },
    { id: 'progress', label: t('nav.staffProgress'), icon: BarChart, badge: 0 },
    { id: 'omset', label: t('nav.omsetCRM'), icon: DollarSign, badge: 0 },
    { id: 'reserved', label: t('nav.reservedMembers'), icon: UserCheck, badge: stats.pendingReservations },
    { id: 'bonanza', label: t('nav.dbBonanza'), icon: Gift, badge: 0 },
    { id: 'memberwd', label: t('nav.memberWDCRM'), icon: CreditCard, badge: 0 },
    { id: 'upload', label: t('nav.uploadDatabase'), icon: Upload, badge: 0 },
    { id: 'databases', label: t('nav.manageDatabases'), icon: FileSpreadsheet, badge: 0 },
    { id: 'assignments', label: t('nav.viewAssignments'), icon: List, badge: 0 },
    { id: 'requests', label: t('nav.downloadRequests'), icon: Clock, badge: stats.pendingRequests },
    { id: 'history', label: t('nav.downloadHistory'), icon: LayoutDashboard, badge: 0 },
    { id: 'products', label: t('nav.productManagement'), icon: Package, badge: 0 },
    { id: 'inventory', label: t('nav.officeInventory') || 'Office Inventory', icon: Boxes, badge: 0 },
    { id: 'manage-users', label: t('nav.userManagement'), icon: UserCog, badge: 0 },
    { id: 'users', label: t('nav.createUser'), icon: Users, badge: 0 }
  ], [t, language, stats.pendingReservations, stats.pendingRequests]);

  // Filter out blocked pages for admin users (master_admin has full access)
  const menuItems = useMemo(() => {
    if (user.role === 'master_admin') {
      return allMenuItems;
    }
    const blockedPages = user.blocked_pages || [];
    return allMenuItems.filter(item => !blockedPages.includes(item.id));
  }, [allMenuItems, user.role, user.blocked_pages]);

  // Handle user profile update
  const handleUserUpdate = (updatedUser) => {
    // Force page reload to refresh user data
    window.location.reload();
  };

  return (
    <DashboardLayout
      user={user}
      onLogout={onLogout}
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      menuItems={menuItems}
      onUserUpdate={handleUserUpdate}
    >
      {renderContent()}
    </DashboardLayout>
  );
}
