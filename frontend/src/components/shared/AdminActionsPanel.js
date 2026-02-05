import { RefreshCw, AlertTriangle, Settings, Wrench } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Admin Actions Panel Component
 * Provides common admin actions like Fix Product Mismatch, Fix Reserved Conflicts
 */
export default function AdminActionsPanel({
  api,
  moduleType = 'bonanza', // 'bonanza' or 'memberwd'
  onDataRefresh,
  onShowSettings,
  showSettingsBtn = true,
  className = ''
}) {
  const endpoints = {
    bonanza: {
      diagnoseMismatch: '/bonanza/admin/diagnose-product-mismatch',
      repairMismatch: '/bonanza/admin/repair-product-mismatch',
      diagnoseConflicts: '/bonanza/admin/diagnose-reserved-conflicts',
      fixConflicts: '/bonanza/admin/fix-reserved-conflicts'
    },
    memberwd: {
      diagnoseMismatch: '/memberwd/admin/diagnose-product-mismatch',
      repairMismatch: '/memberwd/admin/repair-product-mismatch',
      diagnoseConflicts: '/memberwd/admin/diagnose-reserved-conflicts',
      fixConflicts: '/memberwd/admin/fix-reserved-conflicts'
    }
  };

  const ep = endpoints[moduleType];
  const moduleName = moduleType === 'bonanza' ? 'DB Bonanza' : 'Member WD';

  const handleFixProductMismatch = async () => {
    try {
      // First diagnose
      const diagRes = await api.get(ep.diagnoseMismatch);
      const diag = diagRes.data;
      
      if (diag.total_mismatched === 0) {
        toast.info('No product mismatches found. All records are in the correct database.');
        return;
      }
      
      // Show what will be fixed
      let message = `Found ${diag.total_mismatched} records in wrong databases:\n\n`;
      diag.would_move.forEach(m => {
        message += `• ${m.count} records (${m.assigned_count} assigned) will move:\n  ${m.from_database} → ${m.to_database}\n`;
      });
      
      if (diag.cannot_fix?.length > 0) {
        message += `\n⚠️ Cannot fix ${diag.cannot_fix.length} records (no target database)`;
      }
      
      message += '\n\nProceed with repair?';
      
      if (!window.confirm(message)) return;
      
      // Run the repair
      const repairRes = await api.post(ep.repairMismatch);
      toast.success(repairRes.data.message);
      onDataRefresh?.();
      console.log(`${moduleName} Product Mismatch Repair Log:`, repairRes.data.repair_log);
    } catch (error) {
      console.error('Repair error:', error);
      toast.error('Failed to repair product mismatch');
    }
  };

  const handleFixReservedConflicts = async () => {
    try {
      // First diagnose
      const diagRes = await api.get(ep.diagnoseConflicts);
      const diag = diagRes.data;
      
      if (diag.total_conflicts === 0) {
        toast.success('✅ No reserved member conflicts found! All records are assigned correctly.');
        return;
      }
      
      // Show what will be fixed
      let message = `⚠️ CRITICAL: Found ${diag.total_conflicts} records assigned to WRONG staff!\n\n`;
      message += `These records are reserved members but assigned to different staff:\n\n`;
      
      // Group by from_staff -> to_staff
      const groups = {};
      diag.conflicts.slice(0, 20).forEach(c => {
        const key = `${c.assigned_to} → ${c.reserved_by}`;
        if (!groups[key]) groups[key] = 0;
        groups[key]++;
      });
      
      Object.entries(groups).forEach(([key, count]) => {
        message += `• ${count} records: ${key}\n`;
      });
      
      if (diag.total_conflicts > 20) {
        message += `\n... and ${diag.total_conflicts - 20} more\n`;
      }
      
      message += '\n\nFix these conflicts? (Records will be reassigned to correct staff)';
      
      if (!window.confirm(message)) return;
      
      // Run the fix
      const fixRes = await api.post(ep.fixConflicts);
      toast.success(fixRes.data.message);
      onDataRefresh?.();
      console.log(`${moduleName} Reserved Conflict Fix Log:`, fixRes.data);
    } catch (error) {
      console.error('Fix error:', error);
      toast.error('Failed to fix reserved conflicts');
    }
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <button
        onClick={handleFixProductMismatch}
        className="px-3 py-2 bg-purple-100 hover:bg-purple-200 dark:bg-purple-900/50 dark:hover:bg-purple-900 text-purple-700 dark:text-purple-300 rounded-lg flex items-center gap-2 transition-colors text-sm"
        title="Fix records that are in the wrong database based on product_id"
        data-testid={`${moduleType}-fix-mismatch-btn`}
      >
        <RefreshCw size={16} />
        Fix Product Mismatch
      </button>
      
      <button
        onClick={handleFixReservedConflicts}
        className="px-3 py-2 bg-red-100 hover:bg-red-200 dark:bg-red-900/50 dark:hover:bg-red-900 text-red-700 dark:text-red-300 rounded-lg flex items-center gap-2 transition-colors text-sm"
        title="CRITICAL: Fix records assigned to wrong staff (reserved member conflicts)"
        data-testid={`${moduleType}-fix-conflicts-btn`}
      >
        <AlertTriangle size={16} />
        Fix Reserved Conflicts
      </button>
      
      {showSettingsBtn && onShowSettings && (
        <button
          onClick={onShowSettings}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg flex items-center gap-2 transition-colors"
          data-testid={`${moduleType}-settings-btn`}
        >
          <Settings size={18} />
          Settings
        </button>
      )}
    </div>
  );
}
