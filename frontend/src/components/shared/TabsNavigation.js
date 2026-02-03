import { Database, Archive } from 'lucide-react';

/**
 * Tabs Navigation Component
 * Used for switching between Databases and Invalid Database tabs
 */
export default function TabsNavigation({
  activeTab,
  onTabChange,
  archivedCount = 0,
  tabs = [
    { id: 'databases', label: 'Databases', icon: Database },
    { id: 'invalid', label: 'Database Invalid', icon: Archive, showBadge: true }
  ],
  testIdPrefix = 'tab'
}) {
  return (
    <div className="mb-6 border-b border-slate-200 dark:border-slate-700">
      <div className="flex gap-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-b-0 border-slate-200 dark:border-slate-700'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
              data-testid={`${testIdPrefix}-${tab.id}`}
            >
              <Icon size={16} />
              {tab.label}
              {tab.showBadge && archivedCount > 0 && (
                <span className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
                  {archivedCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
