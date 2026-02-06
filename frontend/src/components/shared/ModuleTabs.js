import { Database, Archive } from 'lucide-react';

/**
 * Module Tabs Component
 * Tab navigation for Databases and Invalid Database tabs
 * Used by both AdminDBBonanza and AdminMemberWDCRM
 */
export default function ModuleTabs({
  activeTab,
  setActiveTab,
  archivedCount = 0,
  showMigrationTab = false,
  testIdPrefix = 'module'
}) {
  return (
    <div className="mb-6 border-b border-slate-200 dark:border-slate-700">
      <div className="flex gap-1">
        <button
          onClick={() => setActiveTab('databases')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            activeTab === 'databases'
              ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-b-0 border-slate-200 dark:border-slate-700'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
          data-testid={`${testIdPrefix}-tab-databases`}
        >
          <Database size={16} className="inline mr-2" />
          Databases
        </button>
        
        <button
          onClick={() => setActiveTab('invalid')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'invalid'
              ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-b-0 border-slate-200 dark:border-slate-700'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
          data-testid={`${testIdPrefix}-tab-invalid`}
        >
          <Archive size={16} />
          Database Invalid
          {archivedCount > 0 && (
            <span className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
              {archivedCount}
            </span>
          )}
        </button>
        
        {showMigrationTab && (
          <button
            onClick={() => setActiveTab('migration')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === 'migration'
                ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 border border-b-0 border-slate-200 dark:border-slate-700'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
            data-testid={`${testIdPrefix}-tab-migration`}
          >
            Migration Status
          </button>
        )}
      </div>
    </div>
  );
}
