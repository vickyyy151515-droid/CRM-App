import { LogOut } from 'lucide-react';

export default function DashboardLayout({ user, onLogout, activeTab, setActiveTab, menuItems, children }) {
  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col" data-testid="sidebar">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-2xl font-bold text-slate-900">CRM Pro</h1>
          <p className="text-sm text-slate-600 mt-1">{user.role === 'admin' ? 'Admin Panel' : 'Staff Panel'}</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                data-testid={`nav-${item.id}`}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  activeTab === item.id
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="mb-3 px-2">
            <p className="text-sm font-medium text-slate-900">{user.name}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
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

      <main className="flex-1 overflow-auto">
        <div className="p-8 md:p-12">
          {children}
        </div>
      </main>
    </div>
  );
}