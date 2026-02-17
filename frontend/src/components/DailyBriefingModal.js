import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription
} from './ui/dialog';
import { AlertTriangle, Clock, Users, ChevronRight } from 'lucide-react';

const RISK_CONFIG = {
  critical: { label: 'Critical', color: 'bg-red-500', text: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800' },
  high: { label: 'High Risk', color: 'bg-orange-500', text: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-200 dark:border-orange-800' },
  medium: { label: 'Medium Risk', color: 'bg-yellow-500', text: 'text-yellow-600', bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800' }
};

function RiskSection({ level, customers, totalCount }) {
  const config = RISK_CONFIG[level];
  if (!customers?.length) return null;

  return (
    <div className={`rounded-lg border p-3 ${config.bg} ${config.border}`} data-testid={`briefing-risk-${level}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${config.color}`} />
          <span className={`text-sm font-semibold ${config.text}`}>{config.label}</span>
        </div>
        <span className="text-xs text-slate-500">{customers.length} of {totalCount}</span>
      </div>
      <div className="space-y-1.5">
        {customers.map((c, i) => (
          <div key={i} className="flex items-center justify-between text-sm bg-white/60 dark:bg-slate-800/60 rounded px-2.5 py-1.5">
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-medium text-slate-800 dark:text-slate-200 truncate">{c.customer_name || c.customer_id}</span>
              <span className="text-xs text-slate-400 shrink-0">{c.product_name}</span>
            </div>
            <span className={`text-xs font-mono shrink-0 ml-2 ${config.text}`}>{c.days_since_deposit}d ago</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FollowupSection({ productName, data }) {
  if (!data?.items?.length) return null;

  return (
    <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-3" data-testid={`briefing-followup-${productName}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <ChevronRight size={14} className="text-blue-500" />
          <span className="text-sm font-semibold text-blue-600">{productName}</span>
        </div>
        <span className="text-xs text-slate-500">{data.items.length} of {data.total}</span>
      </div>
      <div className="space-y-1.5">
        {data.items.map((c, i) => (
          <div key={i} className="flex items-center justify-between text-sm bg-white/60 dark:bg-slate-800/60 rounded px-2.5 py-1.5">
            <span className="font-medium text-slate-800 dark:text-slate-200 truncate">{c.customer_display}</span>
            <span className="text-xs font-mono text-blue-600 shrink-0 ml-2">{c.days_since_response}d waiting</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DailyBriefingModal() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);

  const fetchBriefing = useCallback(async () => {
    try {
      const res = await api.get('/retention/daily-briefing');
      if (res.data?.show) {
        setData(res.data);
        setOpen(true);
      }
    } catch (err) {
      console.debug('Daily briefing fetch failed:', err.message);
    }
  }, []);

  useEffect(() => {
    fetchBriefing();
  }, [fetchBriefing]);

  const handleDismiss = async () => {
    setOpen(false);
    try {
      await api.post('/retention/daily-briefing/dismiss');
    } catch (err) {
      console.debug('Dismiss failed:', err.message);
    }
  };

  if (!data) return null;

  const { at_risk, followups_by_product } = data;
  const hasAtRisk = at_risk.critical?.length || at_risk.high?.length || at_risk.medium?.length;
  const hasFollowups = Object.keys(followups_by_product || {}).length > 0;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleDismiss(); }}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto" data-testid="daily-briefing-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <AlertTriangle size={20} className="text-amber-500" />
            Daily Briefing
          </DialogTitle>
          <DialogDescription className="text-sm">
            Your priority customers for today, {data.date}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* At-Risk Section */}
          {hasAtRisk ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Clock size={16} className="text-red-500" />
                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide">At-Risk Customers</h3>
              </div>
              <div className="space-y-3">
                <RiskSection level="critical" customers={at_risk.critical} totalCount={at_risk.total_critical} />
                <RiskSection level="high" customers={at_risk.high} totalCount={at_risk.total_high} />
                <RiskSection level="medium" customers={at_risk.medium} totalCount={at_risk.total_medium} />
              </div>
            </div>
          ) : (
            <div className="text-center py-3 text-sm text-slate-500 bg-green-50 dark:bg-green-900/20 rounded-lg" data-testid="no-atrisk-message">
              No at-risk customers today!
            </div>
          )}

          {/* Follow-up Section */}
          {hasFollowups && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Users size={16} className="text-blue-500" />
                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Follow-Up Reminders</h3>
              </div>
              <div className="space-y-3">
                {Object.entries(followups_by_product).map(([product, pdata]) => (
                  <FollowupSection key={product} productName={product} data={pdata} />
                ))}
              </div>
            </div>
          )}

          {!hasAtRisk && !hasFollowups && (
            <div className="text-center py-4 text-sm text-slate-500">
              All clear! No priority items for today.
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={handleDismiss}
            className="px-5 py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
            data-testid="briefing-dismiss-btn"
          >
            Got it
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
