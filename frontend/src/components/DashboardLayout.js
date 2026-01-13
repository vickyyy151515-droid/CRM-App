import { LogOut, Menu, X } from 'lucide-react';
import { useState } from 'react';
import NotificationBell from './NotificationBell';

export default function DashboardLayout({ user, onLogout, activeTab, setActiveTab, menuItems, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    setSidebarOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`
          fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
        data-testid="sidebar"
      >
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">CRM Pro</h1>
            <p className="text-sm text-slate-600 mt-1">{user.role === 'admin' ? 'Admin Panel' : 'Staff Panel'}</p>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                data-testid={`nav-${item.id}`}
                className={`w-full flex items-center justify-between px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  activeTab === item.id
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <span className="flex items-center gap-3">
                  <Icon size={18} />
                  <span className="truncate">{item.label}</span>
                </span>
                {item.badge > 0 && (
                  <span 
                    className={`min-w-[20px] h-5 px-1.5 rounded-full text-xs font-bold flex items-center justify-center ${
                      activeTab === item.id
                        ? 'bg-white text-slate-900'
                        : 'bg-red-500 text-white'
                    }`}
                    data-testid={`badge-${item.id}`}
                  >
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="mb-3 px-2">
            <p className="text-sm font-medium text-slate-900 truncate">{user.name}</p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
          <button
            onClick={onLogout}
            data-testid="logout-button"
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar for mobile */}
        <header className="lg:hidden bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
            data-testid="mobile-menu-btn"
          >
            <Menu size={24} />
          </button>
          <h1 className="text-lg font-bold text-slate-900">CRM Pro</h1>
          <NotificationBell />
        </header>

        {/* Desktop notification bell */}
        <div className="hidden lg:flex justify-end p-4 pb-0">
          <NotificationBell />
        </div>

        <main className="flex-1 overflow-auto">
          <div className="p-4 sm:p-6 md:p-8 lg:p-12">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
