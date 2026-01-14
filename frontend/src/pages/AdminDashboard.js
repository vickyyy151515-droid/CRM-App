import { useState, useEffect, useCallback } from 'react';
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
import { LayoutDashboard, Upload, FileSpreadsheet, Clock, Users, Package, List, BarChart, UserCheck, DollarSign, UserCog, Gift, CreditCard, PieChart, Download, FileText, Calculator, CalendarOff, Calendar, Timer } from 'lucide-react';

export default function AdminDashboard({ user, onLogout }) {
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
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Dashboard Overview</h2>
            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-total-databases">
                <div className="flex items-center justify-between mb-3">
                  <FileSpreadsheet className="text-indigo-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.totalDatabases}</span>
                </div>
                <p className="text-sm text-slate-600">Total Databases</p>
              </div>
              <div 
                className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm cursor-pointer hover:border-amber-300 transition-colors" 
                data-testid="stat-pending-requests"
                onClick={() => setActiveTab('requests')}
              >
                <div className="flex items-center justify-between mb-3">
                  <Clock className="text-amber-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.pendingRequests}</span>
                </div>
                <p className="text-sm text-slate-600">Pending DB Requests</p>
              </div>
              <div 
                className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm cursor-pointer hover:border-amber-300 transition-colors" 
                data-testid="stat-pending-reservations"
                onClick={() => setActiveTab('reserved')}
              >
                <div className="flex items-center justify-between mb-3">
                  <UserCheck className="text-amber-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.pendingReservations}</span>
                </div>
                <p className="text-sm text-slate-600">Pending Reservations</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-total-downloads">
                <div className="flex items-center justify-between mb-3">
                  <LayoutDashboard className="text-emerald-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.totalDownloads}</span>
                </div>
                <p className="text-sm text-slate-600">Total Downloads</p>
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
        return <CreateUser />;
      case 'manage-users':
        return <ManageUsers />;
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
      default:
        return null;
    }
  };

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, badge: 0 },
    { id: 'analytics', label: 'Advanced Analytics', icon: PieChart, badge: 0 },
    { id: 'export', label: 'Export Center', icon: Download, badge: 0 },
    { id: 'report', label: 'Report CRM', icon: FileText, badge: 0 },
    { id: 'bonus', label: 'CRM Bonus Calculation', icon: Calculator, badge: 0 },
    { id: 'leave', label: 'Leave Requests', icon: CalendarOff, badge: 0 },
    { id: 'leave-calendar', label: 'Leave Calendar', icon: Calendar, badge: 0 },
    { id: 'izin-monitor', label: 'Monitor Izin', icon: Timer, badge: 0 },
    { id: 'progress', label: 'Staff Progress & Quality', icon: BarChart, badge: 0 },
    { id: 'omset', label: 'OMSET CRM', icon: DollarSign, badge: 0 },
    { id: 'reserved', label: 'Reserved Member CRM', icon: UserCheck, badge: stats.pendingReservations },
    { id: 'bonanza', label: 'DB Bonanza', icon: Gift, badge: 0 },
    { id: 'memberwd', label: 'Member WD CRM', icon: CreditCard, badge: 0 },
    { id: 'upload', label: 'Upload Database', icon: Upload, badge: 0 },
    { id: 'databases', label: 'Manage Databases', icon: FileSpreadsheet, badge: 0 },
    { id: 'assignments', label: 'View All Assignments', icon: List, badge: 0 },
    { id: 'requests', label: 'Download Requests', icon: Clock, badge: stats.pendingRequests },
    { id: 'history', label: 'Download History', icon: LayoutDashboard, badge: 0 },
    { id: 'products', label: 'Manage Products', icon: Package, badge: 0 },
    { id: 'manage-users', label: 'Manage Users', icon: UserCog, badge: 0 },
    { id: 'users', label: 'Create User', icon: Users, badge: 0 }
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
