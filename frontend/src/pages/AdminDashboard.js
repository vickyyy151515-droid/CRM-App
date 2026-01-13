import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import UploadDatabase from '../components/UploadDatabase';
import DatabaseList from '../components/DatabaseList';
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
import { LayoutDashboard, Upload, FileSpreadsheet, Clock, Users, Package, List, BarChart, UserCheck, DollarSign, UserCog, Gift, CreditCard, PieChart, Download } from 'lucide-react';

export default function AdminDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState({
    totalDatabases: 0,
    pendingRequests: 0,
    pendingReservations: 0,
    totalDownloads: 0
  });

  const loadStats = useCallback(async () => {
    try {
      const [databases, requests, history, reservations] = await Promise.all([
        api.get('/databases'),
        api.get('/download-requests'),
        api.get('/download-history'),
        api.get('/reserved-members')
      ]);

      setStats({
        totalDatabases: databases.data.length,
        pendingRequests: requests.data.filter(r => r.status === 'pending').length,
        pendingReservations: reservations.data.filter(r => r.status === 'pending').length,
        totalDownloads: history.data.length
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

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Dashboard Overview</h2>
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
            <DatabaseList onUpdate={loadStats} />
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
      default:
        return null;
    }
  };

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, badge: 0 },
    { id: 'analytics', label: 'Advanced Analytics', icon: PieChart, badge: 0 },
    { id: 'export', label: 'Export Center', icon: Download, badge: 0 },
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
