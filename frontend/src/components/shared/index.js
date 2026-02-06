// Shared components for AdminDBBonanza and AdminMemberWDCRM
export { default as SettingsPanel, SettingsButton } from './SettingsPanel';
export { default as InvalidRecordsPanel } from './InvalidRecordsPanel';
export { default as InvalidRecordsAlertBanner } from './InvalidRecordsAlertBanner';
export { default as ReplaceModal } from './ReplaceModal';
export { default as DatabaseUploadForm } from './DatabaseUploadForm';
export { default as TabsNavigation } from './TabsNavigation';
export { default as ModuleTabs } from './ModuleTabs';
export { default as ModuleHeader } from './ModuleHeader';
export { default as ProductFilter } from './ProductFilter';
export { default as RecordsTable } from './RecordsTable';
export { default as DatabaseCard } from './DatabaseCard';
export { default as DatabaseListSection } from './DatabaseListSection';
export { default as ArchivedRecordsTable } from './ArchivedRecordsTable';
export { default as AssignmentPanel } from './AssignmentPanel';
export { default as AdminActionsPanel } from './AdminActionsPanel';
export { default as ProactiveMonitoringAlert } from './ProactiveMonitoringAlert';
export { useAdminModule } from './useAdminModule';

// Shared components for analytics and reporting
export { default as DateRangeSelector } from './DateRangeSelector';
export { default as SummaryStatsCards, StatsCard } from './SummaryStatsCards';
export { default as AnalyticsFilterBar } from './AnalyticsFilterBar';
export { ChartCard, TrendLineChart, MultiLineChart, SimpleBarChart, SimpleAreaChart, CHART_COLORS } from './ChartComponents';

// Shared components for staff-facing pages
export { default as InvalidatedByReservationSection } from './InvalidatedByReservationSection';

// Utility functions
export const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Hidden columns for records tables
export const HIDDEN_COLUMNS = ['rekening', 'rek', 'bank', 'no_rekening', 'norek', 'account'];

export const filterVisibleColumns = (columns) => 
  columns.filter(col => 
    !HIDDEN_COLUMNS.some(hidden => col.toLowerCase().includes(hidden.toLowerCase()))
  );
