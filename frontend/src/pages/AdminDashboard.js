import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import DashboardLayout from '../components/DashboardLayout';
import UploadDatabase from '../components/UploadDatabase';
import DatabaseList from '../components/DatabaseList';
import DownloadRequests from '../components/DownloadRequests';
import DownloadHistory from '../components/DownloadHistory';
import CreateUser from '../components/CreateUser';
import ProductManagement from '../components/ProductManagement';
import AllAssignments from '../components/AllAssignments';
import { LayoutDashboard, Upload, FileSpreadsheet, Clock, Users, Package, List } from 'lucide-react';

export default function AdminDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState({
    totalDatabases: 0,
    pendingRequests: 0,
    totalDownloads: 0
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
        pendingRequests: requests.data.filter(r => r.status === 'pending').length,
        totalDownloads: history.data.length
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Dashboard Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-total-databases">
                <div className="flex items-center justify-between mb-3">
                  <FileSpreadsheet className="text-indigo-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.totalDatabases}</span>
                </div>
                <p className="text-sm text-slate-600">Total Databases</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm" data-testid="stat-pending-requests">
                <div className="flex items-center justify-between mb-3">
                  <Clock className="text-amber-600" size={24} />
                  <span className="text-2xl font-bold text-slate-900">{stats.pendingRequests}</span>
                </div>
                <p className="text-sm text-slate-600">Pending Requests</p>
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
      case 'products':
        return <ProductManagement />;
      default:
        return null;
    }
  };

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Database', icon: Upload },
    { id: 'databases', label: 'Manage Databases', icon: FileSpreadsheet },
    { id: 'requests', label: 'Download Requests', icon: Clock },
    { id: 'history', label: 'Download History', icon: LayoutDashboard },
    { id: 'products', label: 'Manage Products', icon: Package },
    { id: 'users', label: 'Create User', icon: Users }
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