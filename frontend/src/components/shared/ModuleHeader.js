import { Check, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Module Header Component
 * Title with health check and repair actions
 * Used by both AdminDBBonanza and AdminMemberWDCRM
 */
export default function ModuleHeader({
  title,
  api,
  moduleType, // 'bonanza' or 'memberwd'
  onDataRefresh,
  children // Additional buttons like AdminActionsPanel
}) {
  const handleHealthCheck = async () => {
    try {
      const response = await api.get(`/${moduleType}/admin/data-health`);
      if (response.data.is_healthy) {
        toast.success(`Data healthy! ${response.data.databases?.length || 0} databases checked.`);
      } else {
        const issues = [];
        const dbs = response.data.databases || [];
        for (const db of dbs) {
          if (db.has_issues) {
            const dbIssues = db.issues || {};
            if (dbIssues.missing_db_name > 0) issues.push(`${db.database_name}: ${dbIssues.missing_db_name} records missing database name`);
            if (dbIssues.orphaned_assignments > 0) issues.push(`${db.database_name}: ${dbIssues.orphaned_assignments} orphaned assignments`);
            if (dbIssues.invalid_status > 0) issues.push(`${db.database_name}: ${dbIssues.invalid_status} records with invalid status`);
            if (dbIssues.other_invalid_status > 0) issues.push(`${db.database_name}: ${dbIssues.other_invalid_status} records with unknown status`);
          }
        }
        const batches = response.data.batches || [];
        for (const batch of batches) {
          if (batch.has_mismatch) issues.push(`Batch ${batch.staff_name}: count mismatch (stored=${batch.stored_count}, actual=${batch.actual_count})`);
        }
        const issueText = issues.length > 0 ? issues.join('. ') : `${response.data.total_issues} issue(s) detected`;
        toast.error(`Found ${response.data.total_issues} issues: ${issueText}. Click "Repair Data" to fix.`, { duration: 10000 });
      }
    } catch (error) {
      toast.error('Failed to check data health');
    }
  };

  const handleRepairData = async () => {
    if (!window.confirm('Run data repair? This will fix orphaned records and missing data.')) return;
    try {
      const response = await api.post(`/${moduleType}/admin/repair-data`);
      toast.success(response.data.message);
      if (onDataRefresh) onDataRefresh();
      console.log('Repair Log:', response.data.repair_log);
    } catch (error) {
      toast.error('Failed to repair data');
    }
  };

  return (
    <div className="flex items-center justify-between mb-6">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
        {title}
      </h2>
      <div className="flex items-center gap-2">
        <button
          onClick={handleHealthCheck}
          className="px-3 py-2 bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-900/50 dark:hover:bg-emerald-900 text-emerald-700 dark:text-emerald-300 rounded-lg flex items-center gap-2 transition-colors text-sm"
          title="Check data consistency"
        >
          <Check size={16} />
          Health Check
        </button>
        <button
          onClick={handleRepairData}
          className="px-3 py-2 bg-amber-100 hover:bg-amber-200 dark:bg-amber-900/50 dark:hover:bg-amber-900 text-amber-700 dark:text-amber-300 rounded-lg flex items-center gap-2 transition-colors text-sm"
          title="Repair data inconsistencies"
        >
          <RefreshCw size={16} />
          Repair Data
        </button>
        {children}
      </div>
    </div>
  );
}
