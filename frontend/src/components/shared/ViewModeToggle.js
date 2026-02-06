import { Download } from 'lucide-react';

/**
 * View Mode Toggle with Export Buttons
 * Used by AdminOmsetCRM and similar pages for switching between summary/detail views
 */
export default function ViewModeToggle({
  viewMode,
  setViewMode,
  onExportSummary,
  onExportDetails,
  showExports = true,
  summaryLabel = 'Summary View',
  detailsLabel = 'Detail View',
  extraTabs = [],
  testIdPrefix = 'view-mode'
}) {
  return (
    <div className="flex justify-between items-center mb-6" data-testid={`${testIdPrefix}-container`}>
      {/* View Mode Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => setViewMode('summary')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'summary' 
              ? 'bg-indigo-600 text-white' 
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
          data-testid={`${testIdPrefix}-summary-btn`}
        >
          {summaryLabel}
        </button>
        <button
          onClick={() => setViewMode('details')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'details' 
              ? 'bg-indigo-600 text-white' 
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
          data-testid={`${testIdPrefix}-details-btn`}
        >
          {detailsLabel}
        </button>
        {extraTabs.map(tab => (
          <button
            key={tab.value}
            onClick={() => setViewMode(tab.value)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              viewMode === tab.value
                ? (tab.activeClass || 'bg-indigo-600 text-white')
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
            data-testid={`${testIdPrefix}-${tab.value}-btn`}
          >
            {tab.label}
            {tab.badge > 0 && (
              <span className={`px-1.5 py-0.5 text-xs rounded-full ${viewMode === tab.value ? 'bg-white/20 text-white' : 'bg-red-100 text-red-600'}`}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Export Buttons */}
      {showExports && (
        <div className="flex gap-2">
          {onExportSummary && (
            <button
              onClick={onExportSummary}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-2 transition-colors text-sm"
              data-testid={`${testIdPrefix}-export-summary`}
            >
              <Download size={16} />
              Export Summary
            </button>
          )}
          {onExportDetails && (
            <button
              onClick={onExportDetails}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-colors text-sm"
              data-testid={`${testIdPrefix}-export-details`}
            >
              <Download size={16} />
              Export Details
            </button>
          )}
        </div>
      )}
    </div>
  );
}
