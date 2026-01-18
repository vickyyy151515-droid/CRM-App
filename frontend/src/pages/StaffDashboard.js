import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../App';
import DashboardLayout from '../components/DashboardLayout';
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
import { useLanguage } from '../contexts/LanguageContext';
import { LayoutDashboard, FileSpreadsheet, Clock, User, UserCheck, DollarSign, Gift, CreditCard, CalendarOff, Timer, Trophy, Bell, CalendarDays, Filter, Heart } from 'lucide-react';

export default function StaffDashboard({ user, onLogout }) {
  const { t, language } = useLanguage();
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

  // Load notification counts
  const loadNotificationCounts = useCallback(async () => {
    try {
      const response = await api.get('/staff/notifications/summary');
      setNotificationCounts(response.data);
    } catch (error) {
      console.error('Error loading notification counts:', error);
    }
  }, []);

  const loadStats = async () => {
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
  };

  useEffect(() => {
    loadStats();
    loadNotificationCounts();
  }, [loadNotificationCounts]);

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
      default:
        return null;
    }
  };

  const menuItems = useMemo(() => [
    { id: 'databases', label: t('nav.browseDatabases'), icon: FileSpreadsheet },
    { id: 'leaderboard', label: t('nav.leaderboard'), icon: Trophy },
    { id: 'daily-summary', label: t('nav.dailySummary'), icon: CalendarDays },
    { id: 'funnel', label: t('nav.conversionFunnel'), icon: Filter },
    { id: 'retention', label: t('nav.customerRetention'), icon: Heart },
    { id: 'followups', label: t('nav.followUpReminders'), icon: Bell },
    { id: 'requests', label: t('nav.myRequests'), icon: Clock },
    { id: 'assigned', label: t('nav.myAssignedCustomers'), icon: User },
    { id: 'reserved', label: t('nav.reservedMembers'), icon: UserCheck },
    { id: 'omset', label: t('nav.omsetCRM'), icon: DollarSign },
    { id: 'bonanza', label: t('nav.dbBonanza'), icon: Gift, badge: notificationCounts.bonanza_new },
    { id: 'memberwd', label: t('nav.memberWDCRM'), icon: CreditCard, badge: notificationCounts.memberwd_new },
    { id: 'leave', label: t('nav.offDaySakit'), icon: CalendarOff },
    { id: 'izin', label: t('nav.izin'), icon: Timer }
  ], [t, language, notificationCounts]);

  return (
    <DashboardLayout
      user={user}
      onLogout={onLogout}
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      menuItems={menuItems}
    >
      {renderContent()}
    </DashboardLayout>
  );
}