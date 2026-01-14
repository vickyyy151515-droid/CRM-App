import { useState, useEffect } from 'react';
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
import { LayoutDashboard, FileSpreadsheet, Clock, User, UserCheck, DollarSign, Gift, CreditCard, CalendarOff, Timer, Trophy, Bell, CalendarDays, Filter, Heart } from 'lucide-react';

export default function StaffDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('databases');
  const [stats, setStats] = useState({
    totalDatabases: 0,
    myRequests: 0,
    myDownloads: 0
  });

  useEffect(() => {
    loadStats();
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

  const renderContent = () => {
    switch (activeTab) {
      case 'databases':
        return (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-available-databases">
                <div className="flex items-center justify-between mb-3">
                  <FileSpreadsheet className="text-indigo-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.totalDatabases}</span>
                </div>
                <p className="text-sm text-slate-600">Available Databases</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-my-requests">
                <div className="flex items-center justify-between mb-3">
                  <Clock className="text-amber-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.myRequests}</span>
                </div>
                <p className="text-sm text-slate-600">My Requests</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-my-downloads">
                <div className="flex items-center justify-between mb-3">
                  <LayoutDashboard className="text-emerald-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.myDownloads}</span>
                </div>
                <p className="text-sm text-slate-600">My Downloads</p>
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

  const menuItems = [
    { id: 'databases', label: 'Browse Databases', icon: FileSpreadsheet },
    { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { id: 'daily-summary', label: 'Daily Summary', icon: CalendarDays },
    { id: 'funnel', label: 'Conversion Funnel', icon: Filter },
    { id: 'retention', label: 'Customer Retention', icon: Heart },
    { id: 'followups', label: 'Follow-up Reminders', icon: Bell },
    { id: 'requests', label: 'My Requests', icon: Clock },
    { id: 'assigned', label: 'My Assigned Customers', icon: User },
    { id: 'reserved', label: 'Reserved Member CRM', icon: UserCheck },
    { id: 'omset', label: 'OMSET CRM', icon: DollarSign },
    { id: 'bonanza', label: 'DB Bonanza', icon: Gift },
    { id: 'memberwd', label: 'Member WD CRM', icon: CreditCard },
    { id: 'leave', label: 'Off Day / Sakit', icon: CalendarOff },
    { id: 'izin', label: 'Izin', icon: Timer }
  ];

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