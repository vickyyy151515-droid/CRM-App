import { Settings } from 'lucide-react';

/**
 * Settings Panel Component
 * Used by both AdminDBBonanza and AdminMemberWDCRM
 */
export default function SettingsPanel({
  title,
  settings,
  onSettingsChange,
  onSave,
  onClose,
  saving,
  testIdPrefix = 'settings'
}) {
  return (
    <div className="mb-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6" data-testid={`${testIdPrefix}-panel`}>
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">{title}</h3>
      
      <div className="space-y-4">
        {/* Auto Replace Toggle */}
        <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
          <div>
            <h4 className="font-medium text-slate-900 dark:text-white">Auto-Replace Invalid Records</h4>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              When staff marks a record as invalid, automatically assign a new replacement from the same database
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.auto_replace_invalid}
              onChange={(e) => onSettingsChange({...settings, auto_replace_invalid: e.target.checked})}
              className="sr-only peer"
              data-testid={`${testIdPrefix}-auto-replace-toggle`}
            />
            <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-slate-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-500 peer-checked:bg-indigo-600"></div>
          </label>
        </div>

        {/* Max Replacements */}
        <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-slate-900 dark:text-white">Max Replacements Per Batch</h4>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Maximum number of invalid records that can be replaced per batch/database
              </p>
            </div>
            <input
              type="number"
              min="1"
              max="100"
              value={settings.max_replacements_per_batch}
              onChange={(e) => onSettingsChange({...settings, max_replacements_per_batch: parseInt(e.target.value) || 10})}
              className="w-20 h-10 px-3 text-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              data-testid={`${testIdPrefix}-max-replacements`}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            data-testid={`${testIdPrefix}-save-btn`}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Settings Button Component
 */
export function SettingsButton({ onClick, testId = 'settings-btn' }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg flex items-center gap-2 transition-colors"
      data-testid={testId}
    >
      <Settings size={18} />
      Settings
    </button>
  );
}
