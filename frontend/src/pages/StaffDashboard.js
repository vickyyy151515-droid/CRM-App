import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import StaffTargetBanner from '../components/StaffTargetBanner';
import DatabaseList from '../components/DatabaseList';
import MyRequests from '../components/MyRequests';
import MyAssignedRecords from '../components/MyAssignedRecords';
import StaffReservedMembers from '../components/StaffReservedMembers';
import StaffOmsetCRM from '../components/StaffOmsetCRM';
import StaffDBBonanza from '../components/StaffDBBonanza';
import StaffMemberWDCRM from '../components/StaffMemberWDCRM';
import StaffLeaveRequest from '../components/StaffLeaveRequest';
import StaffIzin from '../components/StaffIzin';
import Leaderboard from '../components/Leaderboard';
import StaffFollowups from '../components/StaffFollowups';
import DailySummary from '../components/DailySummary';
import ConversionFunnel from '../components/ConversionFunnel';
import CustomerRetention from '../components/CustomerRetention';
import MessageVariationGenerator from '../components/MessageVariationGenerator';
import StaffBonusProgress from '../components/StaffBonusProgress';
import StaffBonusCheck from '../components/StaffBonusCheck';
import { useLanguage } from '../contexts/LanguageContext';
import { LayoutDashboard, FileSpreadsheet, Clock, User, UserCheck, DollarSign, Gift, CreditCard, CalendarOff, Timer, Trophy, Bell, CalendarDays, Filter, Heart, Sparkles, Calculator, Award } from 'lucide-react';

export default function StaffDashboard({ user, onLogout }) {
  const { t, setDefaultLanguageForRole } = useLanguage();
  const [activeTab, setActiveTab] = useState('databases');
  const [stats, setStats] = useState({
    totalDatabases: 0,
    myRequests: 0,
    myDownloads: 0
  });
  const [notificationCounts, setNotificationCounts] = useState({
    bonanza_new: 0,
    memberwd_new: 0
  });
  
  // Activity tracking for auto-logout
  const lastActivityRef = useRef(null);
  const AUTO_LOGOUT_MS = 60 * 60 * 1000; // 60 minutes in milliseconds
  const WARNING_BEFORE_MS = 5 * 60 * 1000; // Show warning 5 minutes before
  
  // Initialize lastActivityRef on mount
  useEffect(() => {
    lastActivityRef.current = Date.now();
  }, []);
  
  // Auto-set language to Indonesian for staff users
  useEffect(() => {
    if (user?.role === 'staff') {
      setDefaultLanguageForRole('staff');
    }
  }, [user?.role, setDefaultLanguageForRole]);

  // ==================== ACTIVITY TRACKING ====================
  // Send heartbeat on click - tracks ONLY this user's activity
  // This is INDEPENDENT - does not affect any other user
  
  const sendHeartbeat = useCallback(async () => {
    try {
      await api.post('/auth/heartbeat');
      lastActivityRef.current = Date.now();
    } catch (error) {
      // Silently fail - don't disrupt user experience
      console.debug('Heartbeat failed:', error.message);
    }
  }, []);

  // Track clicks as activity and send heartbeat (debounced)
  useEffect(() => {
    let debounceTimer = null;
    
    const handleClick = () => {
      // Update local activity time immediately
      lastActivityRef.current = Date.now();
      
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

  // Auto-logout check - runs every minute
  useEffect(() => {
    const checkInactivity = () => {
      // Skip if not initialized yet
      if (!lastActivityRef.current) return;
      
      const timeSinceActivity = Date.now() - lastActivityRef.current;
      
      // Auto-logout if inactive for 60 minutes
      if (timeSinceActivity >= AUTO_LOGOUT_MS) {
        toast.error('Sesi Anda telah berakhir karena tidak ada aktivitas selama 60 menit.');
        onLogout();
        return;
      }
      
      // Show warning 5 minutes before auto-logout
      const timeRemaining = AUTO_LOGOUT_MS - timeSinceActivity;
      if (timeRemaining <= WARNING_BEFORE_MS && timeRemaining > WARNING_BEFORE_MS - 60000) {
        const minutesRemaining = Math.ceil(timeRemaining / 60000);
        toast.warning(`Sesi Anda akan berakhir dalam ${minutesRemaining} menit. Klik di mana saja untuk tetap masuk.`, {
          duration: 10000,
          id: 'session-warning'
        });
      }
    };
    
    // Check every minute
    const interval = setInterval(checkInactivity, 60000);
    
    return () => clearInterval(interval);
  }, [onLogout, AUTO_LOGOUT_MS, WARNING_BEFORE_MS]);

  // Load notification counts
  const loadNotificationCounts = useCallback(async () => {
    try {
      const response = await api.get('/staff/notifications/summary');
      setNotificationCounts(response.data);
    } catch (error) {
      console.error('Error loading notification counts:', error);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const [databases, requests, history] = await Promise.all([
        api.get('/databases'),
        api.get('/download-requests'),
        api.get('/download-history')
      ]);

      setStats({
        totalDatabases: databases.data.length,
        myRequests: requests.data.length,
        myDownloads: history.data.length
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadNotificationCounts();
  }, [loadStats, loadNotificationCounts]);

  // Mark page as viewed when user navigates to bonanza or memberwd
  useEffect(() => {
    const markAsViewed = async (pageType) => {
      try {
        await api.post(`/staff/notifications/mark-viewed/${pageType}`);
        // Refresh notification counts after marking as viewed
        loadNotificationCounts();
      } catch (error) {
        console.error('Error marking page as viewed:', error);
      }
    };

    if (activeTab === 'bonanza') {
      markAsViewed('bonanza');
    } else if (activeTab === 'memberwd') {
      markAsViewed('memberwd');
    }
  }, [activeTab, loadNotificationCounts]);

  const renderContent = () => {
    switch (activeTab) {
      case 'databases':
        return (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm" data-testid="stat-available-databases">
                <div className="flex items-center justify-between mb-3">
                  <FileSpreadsheet className="text-indigo-600 dark:text-indigo-400" size={24} />
                  <span className="text-2xl font-bold text-slate-900 dark:text-white">{stats.totalDatabases}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{t('database.availableDatabases') || 'Available Databases'}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm" data-testid="stat-my-requests">
                <div className="flex items-center justify-between mb-3">
                  <Clock className="text-amber-600 dark:text-amber-400" size={24} />
                  <span className="text-2xl font-bold text-slate-900 dark:text-white">{stats.myRequests}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{t('nav.myRequests')}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm" data-testid="stat-my-downloads">
                <div className="flex items-center justify-between mb-3">
                  <LayoutDashboard className="text-emerald-600 dark:text-emerald-400" size={24} />
                  <span className="text-2xl font-bold text-slate-900 dark:text-white">{stats.myDownloads}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400">{t('database.myDownloads') || 'My Downloads'}</p>
              </div>
            </div>
            <DatabaseList isStaff={true} onUpdate={loadStats} />
          </div>
        );
      case 'requests':
        return <MyRequests onUpdate={loadStats} />;
      case 'assigned':
        return <MyAssignedRecords />;
      case 'reserved':
        return <StaffReservedMembers />;
      case 'omset':
        return <StaffOmsetCRM />;
      case 'bonanza':
        return <StaffDBBonanza />;
      case 'memberwd':
        return <StaffMemberWDCRM />;
      case 'leave':
        return <StaffLeaveRequest />;
      case 'izin':
        return <StaffIzin />;
      case 'leaderboard':
        return <Leaderboard isAdmin={false} />;
      case 'followups':
        return <StaffFollowups />;
      case 'daily-summary':
        return <DailySummary isAdmin={false} />;
      case 'funnel':
        return <ConversionFunnel isAdmin={false} />;
      case 'retention':
        return <CustomerRetention isAdmin={false} />;
      case 'message-generator':
        return <MessageVariationGenerator />;
      case 'my-bonus':
        return <StaffBonusProgress />;
      default:
        return null;
    }
  };

  const menuItems = useMemo(() => [
    { id: 'databases', label: t('nav.browseDatabases'), icon: FileSpreadsheet },
    { id: 'leaderboard', label: t('nav.leaderboard'), icon: Trophy },
    { id: 'my-bonus', label: t('nav.myBonus') || 'Bonus Saya', icon: Calculator },
    { id: 'daily-summary', label: t('nav.dailySummary'), icon: CalendarDays },
    { id: 'funnel', label: t('nav.conversionFunnel'), icon: Filter },
    { id: 'retention', label: t('nav.customerRetention'), icon: Heart },
    { id: 'followups', label: t('nav.followUpReminders'), icon: Bell },
    { id: 'message-generator', label: t('nav.messageGenerator') || 'Variasi Pesan', icon: Sparkles },
    { id: 'requests', label: t('nav.myRequests'), icon: Clock },
    { id: 'assigned', label: t('nav.myAssignedCustomers'), icon: User },
    { id: 'reserved', label: t('nav.reservedMembers'), icon: UserCheck },
    { id: 'omset', label: t('nav.omsetCRM'), icon: DollarSign },
    { id: 'bonanza', label: t('nav.dbBonanza'), icon: Gift, badge: notificationCounts.bonanza_new },
    { id: 'memberwd', label: t('nav.memberWDCRM'), icon: CreditCard, badge: notificationCounts.memberwd_new },
    { id: 'leave', label: t('nav.offDaySakit'), icon: CalendarOff },
    { id: 'izin', label: t('nav.izin'), icon: Timer }
  ], [t, notificationCounts]);

  return (
    <DashboardLayout
      user={user}
      onLogout={onLogout}
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      menuItems={menuItems}
    >
      {/* Target Progress Banner - Always visible at top */}
      <StaffTargetBanner />
      
      {/* Main Content */}
      {renderContent()}
    </DashboardLayout>
  );
}