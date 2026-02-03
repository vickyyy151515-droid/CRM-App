import { Users, Shuffle } from 'lucide-react';

/**
 * Assignment Panel Component
 * Panel for assigning selected records to staff
 */
export default function AssignmentPanel({
  selectedRecords,
  selectedStaff,
  setSelectedStaff,
  randomQuantity,
  setRandomQuantity,
  staff,
  onAssign,
  onRandomAssign,
  assigning,
  availableCount,
  testIdPrefix = 'assign'
}) {
  if (selectedRecords.length === 0 && !randomQuantity) {
    return null;
  }

  return (
    <div className="mt-4 p-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl">
      <div className="flex flex-wrap items-center gap-4">
        {/* Manual Assignment */}
        {selectedRecords.length > 0 && (
          <>
            <div className="flex items-center gap-2">
              <Users size={18} className="text-indigo-600" />
              <span className="text-sm font-medium text-indigo-800 dark:text-indigo-200">
                {selectedRecords.length} records selected
              </span>
            </div>
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              className="h-9 px-3 rounded-lg border border-indigo-200 dark:border-indigo-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
              data-testid={`${testIdPrefix}-staff-select`}
            >
              <option value="">Select Staff</option>
              {staff.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <button
              onClick={onAssign}
              disabled={!selectedStaff || assigning}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg disabled:opacity-50 transition-colors"
              data-testid={`${testIdPrefix}-btn`}
            >
              {assigning ? 'Assigning...' : 'Assign Selected'}
            </button>
          </>
        )}

        {/* Divider */}
        {selectedRecords.length > 0 && (
          <div className="h-8 w-px bg-indigo-200 dark:bg-indigo-700" />
        )}

        {/* Random Assignment */}
        <div className="flex items-center gap-2">
          <Shuffle size={18} className="text-indigo-600" />
          <input
            type="number"
            min="1"
            max={availableCount}
            placeholder="Quantity"
            value={randomQuantity}
            onChange={(e) => setRandomQuantity(e.target.value)}
            className="w-24 h-9 px-3 rounded-lg border border-indigo-200 dark:border-indigo-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
            data-testid={`${testIdPrefix}-random-qty`}
          />
          <select
            value={selectedStaff}
            onChange={(e) => setSelectedStaff(e.target.value)}
            className="h-9 px-3 rounded-lg border border-indigo-200 dark:border-indigo-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
            data-testid={`${testIdPrefix}-random-staff`}
          >
            <option value="">Select Staff</option>
            {staff.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <button
            onClick={onRandomAssign}
            disabled={!selectedStaff || !randomQuantity || assigning}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2"
            data-testid={`${testIdPrefix}-random-btn`}
          >
            <Shuffle size={14} />
            Random Assign
          </button>
        </div>
      </div>
    </div>
  );
}
