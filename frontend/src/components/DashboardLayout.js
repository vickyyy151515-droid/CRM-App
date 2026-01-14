import { LogOut, Menu, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState, useEffect } from 'react';
import NotificationBell from './NotificationBell';

export default function DashboardLayout({ user, onLogout, activeTab, setActiveTab, menuItems, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    // Load collapsed state from localStorage
    const saved = localStorage.getItem('sidebar-collapsed');
    return saved === 'true';
  });

  // Save collapsed state to localStorage
  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', collapsed.toString());
  }, [collapsed]);

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    setSidebarOpen(false);
  };

  const toggleCollapse = () => {
    setCollapsed(!collapsed);
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
          fixed lg:static inset-y-0 left-0 z-50 bg-white border-r border-slate-200 flex flex-col
          transform transition-all duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          ${collapsed ? 'lg:w-20' : 'w-64'}
        `}
        data-testid="sidebar"
      >
        {/* Header */}
        <div className={`p-4 border-b border-slate-200 flex items-center ${collapsed ? 'lg:justify-center' : 'justify-between'}`}>
          <div className={`${collapsed ? 'lg:hidden' : ''}`}>
            <h1 className="text-2xl font-bold text-slate-900">CRM Pro</h1>
            <p className="text-sm text-slate-600 mt-1">{user.role === 'admin' ? 'Admin Panel' : 'Staff Panel'}</p>
          </div>
          {/* Collapsed logo */}
          {collapsed && (
            <div className="hidden lg:flex items-center justify-center">
              <span className="text-2xl font-bold text-slate-900">C</span>
            </div>
          )}
          {/* Mobile close button */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                data-testid={`nav-${item.id}`}
                title={collapsed ? item.label : ''}
                className={`
                  w-full flex items-center rounded-lg text-sm font-medium transition-all
                  ${collapsed ? 'lg:justify-center lg:px-2 px-4' : 'px-4'} py-2.5
                  ${activeTab === item.id
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }
                  group relative
                `}
              >
                <span className={`flex items-center ${collapsed ? 'lg:gap-0' : 'gap-3'}`}>
                  <Icon size={20} className="flex-shrink-0" />
                  <span className={`truncate transition-all duration-200 ${collapsed ? 'lg:hidden lg:w-0 lg:opacity-0' : 'opacity-100'}`}>
                    {item.label}
                  </span>
                </span>
                
                {/* Badge */}
                {item.badge > 0 && (
                  <span 
                    className={`
                      min-w-[20px] h-5 px-1.5 rounded-full text-xs font-bold flex items-center justify-center
                      ${collapsed ? 'lg:absolute lg:top-0 lg:right-0 lg:-mt-1 lg:-mr-1' : 'ml-auto'}
                      ${activeTab === item.id
                        ? 'bg-white text-slate-900'
                        : 'bg-red-500 text-white'
                      }
                    `}
                    data-testid={`badge-${item.id}`}
                  >
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}

                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div className="
                    hidden lg:group-hover:flex absolute left-full ml-2 px-3 py-2 
                    bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                    pointer-events-none shadow-lg
                  ">
                    {item.label}
                    {item.badge > 0 && (
                      <span className="ml-2 px-1.5 py-0.5 bg-red-500 rounded-full text-xs">
                        {item.badge}
                      </span>
                    )}
                    {/* Tooltip arrow */}
                    <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* User info & Logout */}
        <div className="p-3 border-t border-slate-200">
          {!collapsed && (
            <div className="mb-3 px-2">
              <p className="text-sm font-medium text-slate-900 truncate">{user.name}</p>
              <p className="text-xs text-slate-500 truncate">{user.email}</p>
            </div>
          )}
          
          {/* Collapsed user avatar */}
          {collapsed && (
            <div className="hidden lg:flex justify-center mb-3 group relative">
              <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-semibold">
                {user.name?.charAt(0).toUpperCase()}
              </div>
              {/* User tooltip */}
              <div className="
                hidden group-hover:flex absolute left-full ml-2 px-3 py-2 
                bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                pointer-events-none shadow-lg flex-col
              ">
                <span className="font-medium">{user.name}</span>
                <span className="text-slate-400 text-xs">{user.email}</span>
                <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
              </div>
            </div>
          )}

          <button
            onClick={onLogout}
            data-testid="logout-button"
            title={collapsed ? 'Sign Out' : ''}
            className={`
              w-full flex items-center gap-2 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors
              ${collapsed ? 'lg:justify-center lg:px-2 px-4' : 'px-4'}
              group relative
            `}
          >
            <LogOut size={18} />
            <span className={`${collapsed ? 'lg:hidden' : ''}`}>Sign Out</span>
            
            {/* Tooltip for collapsed */}
            {collapsed && (
              <div className="
                hidden lg:group-hover:flex absolute left-full ml-2 px-3 py-2 
                bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                pointer-events-none shadow-lg
              ">
                Sign Out
                <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
              </div>
            )}
          </button>
        </div>

        {/* Collapse toggle button (desktop only) */}
        <button
          onClick={toggleCollapse}
          data-testid="collapse-toggle"
          className="
            hidden lg:flex absolute -right-3 top-20 
            w-6 h-6 bg-white border border-slate-200 rounded-full
            items-center justify-center text-slate-500 hover:text-slate-900
            hover:bg-slate-50 transition-colors shadow-sm z-50
          "
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
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
