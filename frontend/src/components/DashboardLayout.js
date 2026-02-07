import { LogOut, Menu, X, ChevronLeft, ChevronRight, Settings, ChevronDown, ChevronUp, Folder, FolderOpen, Sun, Moon, Globe, Crown, Shield, User, UserCog } from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import NotificationBell from './NotificationBell';
import SidebarConfigurator from './SidebarConfigurator';
import GlobalSearch from './GlobalSearch';
import ProfileSettings from './ProfileSettings';
import { useTheme, ROLE_THEMES } from '../contexts/ThemeContext';
import { useLanguage } from '../contexts/LanguageContext';
import { api } from '../App';

export default function DashboardLayout({ user, onLogout, activeTab, setActiveTab, menuItems, children, onUserUpdate }) {
  const { darkMode, toggleTheme, setUserRole } = useTheme();
  const { language, toggleLanguage, t } = useLanguage();
  
  // Get the theme for current user's role
  const roleTheme = ROLE_THEMES[user.role] || ROLE_THEMES.staff;
  
  // Update role in theme context when user changes
  useEffect(() => {
    if (user?.role) {
      setUserRole(user.role);
    }
  }, [user?.role, setUserRole]);
  
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar-collapsed');
    return saved === 'true';
  });
  const [showConfigurator, setShowConfigurator] = useState(false);
  const [showProfileSettings, setShowProfileSettings] = useState(false);
  const [sidebarConfig, setSidebarConfig] = useState(null);
  const [openFolders, setOpenFolders] = useState({});

  // Get role icon
  const getRoleIcon = (role) => {
    switch(role) {
      case 'master_admin': return Crown;
      case 'admin': return Shield;
      default: return User;
    }
  };

  const RoleIcon = getRoleIcon(user.role);

  // Get role display name
  const getRoleDisplayName = (role) => {
    switch(role) {
      case 'master_admin': return 'Master Admin';
      case 'admin': return 'Admin Panel';
      default: return 'Staff Panel';
    }
  };

  const loadSidebarConfig = async () => {
    try {
      const response = await api.get('/user/preferences/sidebar-config');
      if (response.data.config) {
        setSidebarConfig(response.data.config);
        // Initialize open folders state
        const folders = {};
        response.data.config.items?.forEach(item => {
          if (item.type === 'folder') {
            folders[item.id] = item.isOpen !== false;
          }
        });
        setOpenFolders(folders);
      }
    } catch (error) {
      console.error('Failed to load sidebar config:', error);
    }
  };

  // Load sidebar configuration on mount
  useEffect(() => {
    loadSidebarConfig();
  }, []);

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

  const toggleFolder = (folderId) => {
    setOpenFolders(prev => ({
      ...prev,
      [folderId]: !prev[folderId]
    }));
  };

  const handleConfigChange = (newConfig) => {
    setSidebarConfig(newConfig);
    if (newConfig) {
      const folders = {};
      newConfig.items?.forEach(item => {
        if (item.type === 'folder') {
          folders[item.id] = item.isOpen !== false;
        }
      });
      setOpenFolders(folders);
    }
  };

  // Build the menu based on config or default
  const buildMenu = () => {
    if (!sidebarConfig || !sidebarConfig.items) {
      return menuItems.map(item => ({ ...item, type: 'item' }));
    }

    const menuMap = {};
    menuItems.forEach(item => {
      menuMap[item.id] = item;
    });

    // Get all item IDs currently in the saved config (including items inside folders)
    const configItemIds = new Set();
    sidebarConfig.items.forEach(configItem => {
      if (configItem.type === 'folder') {
        configItem.items.forEach(itemId => configItemIds.add(itemId));
      } else {
        configItemIds.add(configItem.id);
      }
    });

    // Find new menu items that are not in the saved config
    const newItems = menuItems.filter(item => !configItemIds.has(item.id));

    // Build the menu from saved config - ALWAYS use labels from menuItems (translated)
    const configuredMenu = sidebarConfig.items.map(configItem => {
      if (configItem.type === 'folder') {
        return {
          ...configItem,
          items: configItem.items.map(itemId => menuMap[itemId]).filter(Boolean)
        };
      }
      // Use menuMap item which has translated label, ignore stored label
      return menuMap[configItem.id] ? { ...menuMap[configItem.id], type: 'item' } : null;
    }).filter(Boolean);

    // Add new items at the beginning (after Overview if it exists)
    if (newItems.length > 0) {
      const newMenuItems = newItems.map(item => ({ ...item, type: 'item' }));
      // Insert after the first item (usually Overview)
      const firstItem = configuredMenu[0];
      if (firstItem && firstItem.id === 'overview') {
        return [firstItem, ...newMenuItems, ...configuredMenu.slice(1)];
      }
      return [...newMenuItems, ...configuredMenu];
    }

    return configuredMenu;
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const organizedMenu = useMemo(() => buildMenu(), [menuItems, sidebarConfig, openFolders]);

  const renderMenuItem = (item, isInFolder = false) => {
    const Icon = item.icon;
    const isActive = activeTab === item.id;

    // Role-based active state styling
    const getActiveClass = () => {
      if (user.role === 'master_admin') {
        return 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white shadow-lg shadow-amber-500/25';
      } else if (user.role === 'admin') {
        return 'bg-slate-900 dark:bg-indigo-600 text-white';
      }
      return 'bg-blue-600 text-white';
    };

    return (
      <button
        key={item.id}
        onClick={() => handleNavClick(item.id)}
        data-testid={`nav-${item.id}`}
        title={collapsed ? item.label : ''}
        className={`
          w-full flex items-center rounded-lg text-sm font-medium transition-all
          ${collapsed && !isInFolder ? 'lg:justify-center lg:px-2 px-4' : 'px-4'} 
          ${isInFolder ? 'py-2 pl-8' : 'py-2.5'}
          ${isActive
            ? getActiveClass()
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
          }
          group relative
        `}
      >
        <span className={`flex items-center ${collapsed && !isInFolder ? 'lg:gap-0' : 'gap-3'}`}>
          <Icon size={isInFolder ? 16 : 20} className="flex-shrink-0" />
          <span className={`truncate transition-all duration-200 ${collapsed && !isInFolder ? 'lg:hidden lg:w-0 lg:opacity-0' : 'opacity-100'}`}>
            {item.label}
          </span>
        </span>
        
        {/* Badge */}
        {item.badge > 0 && (
          <span 
            className={`
              min-w-[20px] h-5 px-1.5 rounded-full text-xs font-bold flex items-center justify-center
              ${collapsed && !isInFolder ? 'lg:absolute lg:top-0 lg:right-0 lg:-mt-1 lg:-mr-1' : 'ml-auto'}
              ${isActive
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
        {collapsed && !isInFolder && (
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
            <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
          </div>
        )}
      </button>
    );
  };

  const renderFolder = (folder) => {
    const isOpen = openFolders[folder.id];
    const hasActiveItem = folder.items?.some(item => item.id === activeTab);

    return (
      <div key={folder.id} className="mb-1">
        <button
          onClick={() => toggleFolder(folder.id)}
          className={`
            w-full flex items-center rounded-lg text-sm font-medium transition-all px-4 py-2.5
            ${hasActiveItem ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:bg-slate-100'}
            ${collapsed ? 'lg:justify-center lg:px-2' : ''}
            group relative
          `}
        >
          <span className={`flex items-center ${collapsed ? 'lg:gap-0' : 'gap-3'}`}>
            {isOpen ? <FolderOpen size={20} /> : <Folder size={20} />}
            <span className={`truncate ${collapsed ? 'lg:hidden' : ''}`}>{folder.name}</span>
          </span>
          <span className={`ml-auto ${collapsed ? 'lg:hidden' : ''}`}>
            {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </span>

          {/* Tooltip for collapsed state */}
          {collapsed && (
            <div className="
              hidden lg:group-hover:flex absolute left-full ml-2 px-3 py-2 
              bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
              pointer-events-none shadow-lg flex-col gap-1
            ">
              <span className="font-medium">{folder.name}</span>
              {folder.items?.map(item => (
                <span key={item.id} className={`text-xs ${item.id === activeTab ? 'text-blue-300' : 'text-slate-300'}`}>
                  • {item.label}
                </span>
              ))}
              <div className="absolute left-0 top-4 -translate-x-1 border-4 border-transparent border-r-slate-900" />
            </div>
          )}
        </button>
        
        {/* Folder contents - always show on mobile, respect isOpen on desktop */}
        <div className={`
          overflow-hidden transition-all duration-200
          ${isOpen ? 'max-h-96 opacity-100' : 'lg:max-h-0 lg:opacity-0 max-h-96 opacity-100'}
          ${collapsed ? 'lg:hidden' : ''}
        `}>
          {folder.items?.map(item => renderMenuItem(item, true))}
        </div>
      </div>
    );
  };

  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex overflow-hidden transition-colors">
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
          fixed lg:static inset-y-0 left-0 z-50 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col
          transform transition-all duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          ${collapsed ? 'lg:w-20' : 'w-64'}
        `}
        data-testid="sidebar"
      >
        {/* Header with role-based accent */}
        <div className={`p-4 border-b border-slate-200 dark:border-slate-800 flex items-center ${collapsed ? 'lg:justify-center' : 'justify-between'} ${roleTheme.headerAccent}`}>
          <div className={`${collapsed ? 'lg:hidden' : ''}`}>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">CRM Pro</h1>
            <div className="flex items-center gap-1.5 mt-1">
              <RoleIcon size={14} className={roleTheme.icon} />
              <p className={`text-sm font-medium ${roleTheme.text}`}>{getRoleDisplayName(user.role)}</p>
            </div>
          </div>
          {/* Collapsed logo with role color */}
          {collapsed && (
            <div className="hidden lg:flex items-center justify-center">
              <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${roleTheme.bgGradient} flex items-center justify-center`}>
                <span className="text-lg font-bold text-white">C</span>
              </div>
            </div>
          )}
          {/* Mobile close button */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {organizedMenu.map(item => 
            item.type === 'folder' ? renderFolder(item) : renderMenuItem(item)
          )}
        </nav>

        {/* Settings & User Section */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800">
          {/* Configure Sidebar Button */}
          <button
            onClick={() => setShowConfigurator(true)}
            data-testid="sidebar-settings-btn"
            title={collapsed ? t('nav.configureSidebar') : ''}
            className={`
              w-full flex items-center gap-2 py-2 mb-2 text-sm text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors
              ${collapsed ? 'lg:justify-center lg:px-2 px-4' : 'px-4'}
              group relative
            `}
          >
            <Settings size={18} />
            <span className={`${collapsed ? 'lg:hidden' : ''}`}>{t('nav.configureSidebar')}</span>
            
            {/* Tooltip */}
            {collapsed && (
              <div className="
                hidden lg:group-hover:flex absolute left-full ml-2 px-3 py-2 
                bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                pointer-events-none shadow-lg
              ">
                {t('nav.configureSidebar')}
                <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
              </div>
            )}
          </button>

          {/* User Info with role badge */}
          {!collapsed && (
            <div className="mb-3 px-2">
              <div className="flex items-center gap-2 mb-1">
                <div className={`w-8 h-8 rounded-full ${roleTheme.avatarBg} flex items-center justify-center text-white font-semibold text-sm`}>
                  {user.name?.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{user.name}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{user.email}</p>
                </div>
              </div>
            </div>
          )}
          
          {/* Collapsed user avatar with role color */}
          {collapsed && (
            <div className="hidden lg:flex justify-center mb-3 group relative">
              <div className={`w-10 h-10 rounded-full ${roleTheme.avatarBg} flex items-center justify-center text-white font-semibold shadow-lg`}>
                {user.name?.charAt(0).toUpperCase()}
              </div>
              <div className="
                hidden group-hover:flex absolute left-full ml-2 px-3 py-2 
                bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                pointer-events-none shadow-lg flex-col
              ">
                <span className="font-medium">{user.name}</span>
                <span className="text-slate-400 text-xs">{user.email}</span>
                <span className={`text-xs mt-1 ${roleTheme.text}`}>{getRoleDisplayName(user.role)}</span>
                <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
              </div>
            </div>
          )}

          {/* Account Settings Button */}
          <button
            onClick={() => setShowProfileSettings(true)}
            data-testid="account-settings-btn"
            title={collapsed ? 'Account Settings' : ''}
            className={`
              w-full flex items-center gap-2 py-2 mb-1 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors
              ${collapsed ? 'lg:justify-center lg:px-2 px-4' : 'px-4'}
              group relative
            `}
          >
            <UserCog size={18} />
            <span className={`${collapsed ? 'lg:hidden' : ''}`}>Account Settings</span>
            
            {collapsed && (
              <div className="
                hidden lg:group-hover:flex absolute left-full ml-2 px-3 py-2 
                bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                pointer-events-none shadow-lg
              ">
                Account Settings
                <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
              </div>
            )}
          </button>

          {/* Logout */}
          <button
            onClick={onLogout}
            data-testid="logout-button"
            title={collapsed ? t('auth.logout') : ''}
            className={`
              w-full flex items-center gap-2 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors
              ${collapsed ? 'lg:justify-center lg:px-2 px-4' : 'px-4'}
              group relative
            `}
          >
            <LogOut size={18} />
            <span className={`${collapsed ? 'lg:hidden' : ''}`}>{t('auth.logout')}</span>
            
            {collapsed && (
              <div className="
                hidden lg:group-hover:flex absolute left-full ml-2 px-3 py-2 
                bg-slate-900 text-white text-sm rounded-lg whitespace-nowrap z-50
                pointer-events-none shadow-lg
              ">
                {t('auth.logout')}
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
            w-6 h-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full
            items-center justify-center text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white
            hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm z-50
          "
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top bar for mobile with role accent */}
        <header className={`lg:hidden bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between ${roleTheme.headerAccent}`}>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
            data-testid="mobile-menu-btn"
          >
            <Menu size={24} />
          </button>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">CRM Pro</h1>
            <RoleIcon size={16} className={roleTheme.icon} />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleLanguage}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg flex items-center gap-1"
              data-testid="language-toggle-mobile"
              title={language === 'en' ? 'Switch to Indonesian' : 'Ganti ke Inggris'}
            >
              <Globe size={18} />
              <span className="text-xs font-medium uppercase">{language}</span>
            </button>
            <button
              onClick={toggleTheme}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
              data-testid="theme-toggle-mobile"
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <NotificationBell userRole={user?.role} />
          </div>
        </header>

        {/* Desktop top bar with role indicator */}
        <div className="hidden lg:flex items-center justify-between p-4 pb-0">
          <div className="flex items-center gap-4">
            <GlobalSearch onNavigate={(tab) => setActiveTab(tab)} isAdmin={user?.role === 'admin' || user?.role === 'master_admin'} />
            {/* Role badge on desktop */}
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${roleTheme.bgLight} ${roleTheme.border} border`}>
              <RoleIcon size={14} className={roleTheme.icon} />
              <span className={`text-xs font-medium ${roleTheme.text}`}>{getRoleDisplayName(user.role)}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleLanguage}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-1.5"
              data-testid="language-toggle"
              title={language === 'en' ? 'Switch to Indonesian' : 'Ganti ke Inggris'}
            >
              <Globe size={18} />
              <span className="text-xs font-medium uppercase">{language}</span>
            </button>
            <button
              onClick={toggleTheme}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              data-testid="theme-toggle"
              title={darkMode ? t('settings.lightMode') : t('settings.darkMode')}
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <NotificationBell userRole={user?.role} />
          </div>
        </div>

        <main className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-950">
          <div className="p-4 sm:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>

      {/* Sidebar Configurator Modal */}
      <SidebarConfigurator
        isOpen={showConfigurator}
        onClose={() => setShowConfigurator(false)}
        menuItems={menuItems}
        onConfigChange={handleConfigChange}
      />

      {/* Profile Settings Modal */}
      <ProfileSettings
        user={user}
        isOpen={showProfileSettings}
        onClose={() => setShowProfileSettings(false)}
        onProfileUpdate={onUserUpdate}
      />
    </div>
  );
}
