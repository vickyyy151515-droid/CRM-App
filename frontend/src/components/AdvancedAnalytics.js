import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  BarChart3, TrendingUp, Users, Package, Database, PieChart, 
  Eye, EyeOff, RefreshCw, Filter, GripVertical, Save, GitCompare, X, Plus,
  ChevronRight, Clock, CheckCircle2, XCircle, ArrowUpRight, Loader2, Info
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  OmsetTrendsWidget,
  ProductOmsetWidget,
  NdpRdpWidget,
  DatabaseUtilizationWidget,
  DailyTrendsWidget,
  WhatsappDistributionWidget,
  ResponseRateWidget,
  formatNumber
} from './shared/AnalyticsWidgets';
import { ChartInfoTooltip } from './shared/ChartInfoTooltip';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
const COMPARISON_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
const STAFF_CHART_COLORS = [
  '#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#a855f7',
  '#0ea5e9', '#e11d48', '#84cc16', '#7c3aed', '#d946ef'
];

const DEFAULT_WIDGET_ORDER = [
  'staffNdpRdpDaily',
  'conversionFunnel',
  'revenueHeatmap',
  'depositLifecycle',
  'responseTime',
  'followupEffectiveness',
  'productPerformance',
  'customerValue',
  'depositTrends',
  'staffCompare',
  'staffComparison',
  'dailyTrends', 
  'whatsappDistribution',
  'responseRate',
  'omsetTrends',
  'productOmset',
  'ndpRdp',
  'databaseUtilization'
];

const CHART_DESCRIPTIONS = {
  staffNdpRdpDaily: {
    title: 'Staff NDP / RDP Daily',
    desc: 'Tracks each staff member\'s daily New Deposit (NDP) and Re-Deposit (RDP) performance over time. Helps identify consistent performers vs those who need support, and spot daily trends or anomalies.',
  },
  conversionFunnel: {
    title: 'Staff Conversion Funnel',
    desc: 'Visualizes the drop-off at each stage: Assigned → WA Checked → Responded → Deposited. Reveals bottlenecks in your sales process and which staff converts most efficiently from lead to deposit.',
  },
  revenueHeatmap: {
    title: 'Revenue Heatmap',
    desc: 'Shows deposit activity intensity across days and staff. Quickly spot peak revenue days, identify which days staff are most/least productive, and optimize scheduling and follow-up timing.',
  },
  depositLifecycle: {
    title: 'Deposit Lifecycle',
    desc: 'Measures the average time from a customer\'s first response to their first deposit. Shorter lifecycle = more efficient sales process. Helps benchmark staff speed and identify slow conversions.',
  },
  responseTime: {
    title: 'Response Time by Staff',
    desc: 'Shows how fast each staff member checks WhatsApp and responds to assigned customers. Faster response times strongly correlate with higher conversion rates. Speed grades help identify who needs improvement.',
  },
  followupEffectiveness: {
    title: 'Follow-up Effectiveness',
    desc: 'Compares the number of follow-ups sent vs successful deposits per staff. The effectiveness percentage shows who is best at converting responded customers into actual depositors.',
  },
  productPerformance: {
    title: 'Product Performance',
    desc: 'Breaks down NDP/RDP counts and deposit amounts by product. Identifies your top-revenue products, shows which products attract more new vs returning customers, and helps prioritize product focus.',
  },
  customerValue: {
    title: 'New vs Returning Customer Value',
    desc: 'Compares total deposit amounts from new customers (NDP) vs returning customers (RDP) per staff. Understanding this split helps optimize acquisition vs retention strategies and staff allocation.',
  },
  depositTrends: {
    title: 'Deposit Trends Over Time',
    desc: 'Shows deposit volume and count trends with daily, weekly, or monthly views. Spot seasonal patterns, growth trends, and peak periods to plan resources and campaigns effectively.',
  },
  staffCompare: {
    title: 'Staff Comparison (Side-by-Side)',
    desc: 'Select 2-6 staff members for a direct performance comparison across key metrics like OMSET, NDP, RDP, and trends. Great for performance reviews and identifying best practices from top performers.',
  },
  staffComparison: {
    title: 'Staff Performance Comparison',
    desc: 'Bar chart comparing total assignments, WA checks, and responses across all staff. Quickly see workload distribution and identify who is handling the most leads effectively.',
  },
  dailyTrends: {
    title: 'Daily Activity Trends',
    desc: 'Shows daily patterns in customer assignments, WA checks, and responses. Helps understand operational rhythms and identify the most productive days of the week or month.',
  },
  whatsappDistribution: {
    title: 'WhatsApp Status Distribution',
    desc: 'Pie chart showing the breakdown of WhatsApp statuses (Active, Inactive, etc.) across all assigned customers. Helps assess data quality and the reach of your WhatsApp follow-up efforts.',
  },
  responseRate: {
    title: 'Response Rate by Staff',
    desc: 'Shows the percentage of assigned customers who responded to each staff member. Higher response rates indicate better communication skills and follow-up persistence.',
  },
  omsetTrends: {
    title: 'OMSET Trends',
    desc: 'Tracks total revenue (OMSET) over time. Identifies growth patterns, seasonal dips, and helps forecast future revenue based on historical performance.',
  },
  productOmset: {
    title: 'OMSET by Product',
    desc: 'Shows revenue contribution by product. Identifies your highest-earning products and helps make data-driven decisions about which products to promote or invest in.',
  },
  ndpRdp: {
    title: 'NDP vs RDP Analysis',
    desc: 'Overall breakdown of New Deposits vs Re-Deposits. A healthy ratio indicates balanced customer acquisition and retention. Helps set strategic targets for growth vs loyalty programs.',
  },
  databaseUtilization: {
    title: 'Database Utilization',
    desc: 'Shows how effectively uploaded customer databases are being used — from total records to assigned, checked, and converted. Low utilization suggests untapped potential in your customer data.',
  },
};

function ChartInfoTooltip({ chartKey }) {
  const [show, setShow] = useState(false);
  const info = CHART_DESCRIPTIONS[chartKey];
  if (!info) return null;

  return (
    <span
      className="relative inline-flex ml-1.5 cursor-help"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      data-testid={`chart-info-${chartKey}`}
    >
      <Info size={14} className="text-slate-500 hover:text-slate-300 transition-colors" />
      {show && (
        <span
          className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-72 sm:w-80 rounded-xl px-4 py-3 text-xs leading-relaxed shadow-2xl border z-[100] pointer-events-none"
          style={{
            background: 'rgba(15, 23, 42, 0.97)',
            borderColor: 'rgba(255,255,255,0.1)',
            backdropFilter: 'blur(12px)',
            color: '#cbd5e1',
          }}
          data-testid={`chart-tooltip-${chartKey}`}
        >
          <span className="block font-semibold text-white text-[13px] mb-1">{info.title}</span>
          {info.desc}
          <span className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 border-t border-l" style={{ background: 'rgba(15, 23, 42, 0.97)', borderColor: 'rgba(255,255,255,0.1)' }} />
        </span>
      )}
    </span>
  );
}

function StaffNdpRdpDailyWidget({ data }) {
  if (!data?.chart_data?.length || !data?.staff?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)' }} data-testid="staff-ndp-rdp-daily-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <BarChart3 size={20} className="text-cyan-400" />
          Staff NDP / RDP Daily
        </h3>
        <div className="text-center py-12 text-slate-500">
          <BarChart3 size={48} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">No data available for this period</p>
        </div>
      </div>
    );
  }

  const { chart_data, staff: staffList } = data;

  const NDP_PALETTE = ['#22d3ee', '#a78bfa', '#f472b6', '#34d399', '#fbbf24', '#fb923c', '#e879f9', '#2dd4bf', '#60a5fa', '#f87171'];
  const RDP_PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#0ea5e9', '#d946ef'];

  // Build per-staff daily data for separate NDP and RDP charts
  const ndpChartData = chart_data.map(row => {
    const entry = { date: row.date };
    staffList.forEach(s => { entry[s.name] = row[`ndp_${s.id}`] || 0; });
    return entry;
  });

  const rdpChartData = chart_data.map(row => {
    const entry = { date: row.date };
    staffList.forEach(s => { entry[s.name] = row[`rdp_${s.id}`] || 0; });
    return entry;
  });

  // Calculate averages
  const days = chart_data.length || 1;
  const staffNdpAvg = {};
  const staffRdpAvg = {};
  staffList.forEach(s => {
    let ndpTotal = 0, rdpTotal = 0;
    chart_data.forEach(row => {
      ndpTotal += row[`ndp_${s.id}`] || 0;
      rdpTotal += row[`rdp_${s.id}`] || 0;
    });
    staffNdpAvg[s.name] = (ndpTotal / days).toFixed(1);
    staffRdpAvg[s.name] = (rdpTotal / days).toFixed(1);
  });

  const totalNdpAvg = Object.values(staffNdpAvg).reduce((s, v) => s + parseFloat(v), 0).toFixed(1);
  const totalRdpAvg = Object.values(staffRdpAvg).reduce((s, v) => s + parseFloat(v), 0).toFixed(1);

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  };

  const ChartTooltip = ({ active, payload, label, type }) => {
    if (!active || !payload?.length) return null;
    const items = payload.filter(p => p.value > 0).sort((a, b) => b.value - a.value);
    const total = items.reduce((s, p) => s + p.value, 0);
    return (
      <div className="rounded-xl px-4 py-3 shadow-2xl border text-sm backdrop-blur-xl" style={{ background: 'rgba(15,23,42,0.92)', borderColor: 'rgba(255,255,255,0.08)' }}>
        <p className="font-semibold text-slate-300 mb-2 text-xs">{formatDate(label)}</p>
        {items.map(item => (
          <div key={item.dataKey} className="flex items-center gap-2 py-0.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color, boxShadow: `0 0 6px ${item.color}` }} />
            <span className="text-slate-300 text-xs">{item.dataKey}</span>
            <span className="ml-auto font-bold text-white text-xs">{item.value}</span>
          </div>
        ))}
        <div className="border-t border-slate-700 mt-1.5 pt-1.5 flex justify-between text-xs">
          <span className="text-slate-400">Total {type}</span>
          <span className="font-bold text-white">{total}</span>
        </div>
      </div>
    );
  };

  const renderChart = (chartData, palette, type, avgData, totalAvg) => (
    <div className="rounded-xl p-4 sm:p-5 border" style={{ background: 'linear-gradient(180deg, rgba(30,41,59,0.5) 0%, rgba(15,23,42,0.8) 100%)', borderColor: 'rgba(255,255,255,0.06)' }}>
      {/* Chart Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: type === 'NDP' ? 'linear-gradient(135deg, #06b6d4, #22d3ee)' : 'linear-gradient(135deg, #7c3aed, #a78bfa)' }}>
            <TrendingUp size={16} className="text-white" />
          </div>
          <div>
            <h4 className="font-bold text-white text-sm tracking-wide">Daily {type} by Staff</h4>
            <p className="text-[11px] text-slate-500">{type === 'NDP' ? 'New Deposit' : 'Re-Deposit'} trend per staff</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-400">Avg Total</p>
          <p className="text-lg font-black text-white" style={{ textShadow: type === 'NDP' ? '0 0 20px rgba(34,211,238,0.3)' : '0 0 20px rgba(167,139,250,0.3)' }}>
            {totalAvg}<span className="text-xs font-normal text-slate-500 ml-1">{type}/day</span>
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="h-56 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <defs>
              {staffList.map((s, i) => (
                <linearGradient key={s.id} id={`grad_${type}_${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={palette[i % palette.length]} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={palette[i % palette.length]} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 10, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 10, fill: '#475569' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<ChartTooltip type={type} />} cursor={{ stroke: 'rgba(255,255,255,0.06)', strokeWidth: 1 }} />
            {staffList.map((s, i) => (
              <Area
                key={s.id}
                type="monotone"
                dataKey={s.name}
                stroke={palette[i % palette.length]}
                strokeWidth={2}
                fill={`url(#grad_${type}_${i})`}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: palette[i % palette.length], fill: '#0f172a' }}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-3 pt-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
        {staffList.map((s, i) => (
          <div key={s.id} className="flex items-center gap-1.5 text-[11px]" data-testid={`legend-${type.toLowerCase()}-${s.id}`}>
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: palette[i % palette.length], boxShadow: `0 0 8px ${palette[i % palette.length]}40` }} />
            <span className="text-slate-400">{s.name}</span>
            <span className="font-semibold text-slate-300">{avgData[s.name]}/d</span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1a1f3a 50%, #1e293b 100%)' }} data-testid="staff-ndp-rdp-daily-widget">
      {/* Main Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            <BarChart3 size={18} className="text-white" />
          </span>
          Staff NDP / RDP Daily
          <ChartInfoTooltip chartKey="staffNdpRdpDaily" />
        </h3>
        <div className="flex items-center gap-3 text-xs">
          <div className="px-3 py-1.5 rounded-lg border" style={{ borderColor: 'rgba(34,211,238,0.3)', background: 'rgba(34,211,238,0.08)' }}>
            <span className="text-cyan-400 font-bold">{totalNdpAvg}</span>
            <span className="text-slate-500 ml-1">NDP/day</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg border" style={{ borderColor: 'rgba(167,139,250,0.3)', background: 'rgba(167,139,250,0.08)' }}>
            <span className="text-purple-400 font-bold">{totalRdpAvg}</span>
            <span className="text-slate-500 ml-1">RDP/day</span>
          </div>
        </div>
      </div>

      {/* Two charts side by side */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4" data-testid="ndp-rdp-charts-grid">
        {renderChart(ndpChartData, NDP_PALETTE, 'NDP', staffNdpAvg, totalNdpAvg)}
        {renderChart(rdpChartData, RDP_PALETTE, 'RDP', staffRdpAvg, totalRdpAvg)}
      </div>
    </div>
  );
}


// ==================== CHART 1: CONVERSION FUNNEL ====================
function ConversionFunnelWidget({ data }) {
  if (!data?.funnel_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(145deg, #0c0f1a 0%, #151b2e 100%)' }} data-testid="conversion-funnel-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><TrendingUp size={20} className="text-amber-400" /> Staff Conversion Funnel</h3>
        <div className="text-center py-12 text-slate-500"><TrendingUp size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }

  const { funnel_data } = data;
  const stages = [
    { key: 'assigned', label: 'Assigned', color: '#64748b', glow: '#64748b' },
    { key: 'wa_checked', label: 'WA Checked', color: '#3b82f6', glow: '#3b82f6' },
    { key: 'responded', label: 'Responded', color: '#f59e0b', glow: '#f59e0b' },
    { key: 'deposited', label: 'Deposited', color: '#22c55e', glow: '#22c55e' },
  ];

  const maxAssigned = Math.max(...funnel_data.map(d => d.assigned), 1);

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(145deg, #0c0f1a 0%, #151b2e 50%, #0f172a 100%)' }} data-testid="conversion-funnel-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
            <TrendingUp size={18} className="text-white" />
          </span>
          Staff Conversion Funnel
          <ChartInfoTooltip chartKey="conversionFunnel" />
        </h3>
        <div className="flex gap-2">
          {stages.map(s => (
            <div key={s.key} className="flex items-center gap-1 text-[10px]">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-slate-500 hidden sm:inline">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {funnel_data.map((staff, si) => {
          const widthScale = staff.assigned / maxAssigned;
          return (
            <div key={staff.staff_id} className="rounded-xl p-3 sm:p-4 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.05)' }} data-testid={`funnel-staff-${staff.staff_id}`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white" style={{ background: `linear-gradient(135deg, ${STAFF_CHART_COLORS[si % STAFF_CHART_COLORS.length]}, ${STAFF_CHART_COLORS[(si + 3) % STAFF_CHART_COLORS.length]})` }}>
                    {staff.staff_name.charAt(0)}
                  </div>
                  <span className="text-sm font-semibold text-white">{staff.staff_name}</span>
                </div>
                <span className="text-xs text-slate-500">{staff.assigned} records</span>
              </div>
              {/* Funnel bars */}
              <div className="space-y-1.5">
                {stages.map((stage, i) => {
                  const value = staff[stage.key];
                  const prevValue = i === 0 ? staff.assigned : staff[stages[i - 1].key];
                  const pct = prevValue > 0 ? ((value / prevValue) * 100).toFixed(0) : 0;
                  const totalPct = staff.assigned > 0 ? ((value / staff.assigned) * 100).toFixed(0) : 0;
                  const barWidth = staff.assigned > 0 ? Math.max(2, (value / maxAssigned) * 100) : 0;
                  return (
                    <div key={stage.key} className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-500 w-16 sm:w-20 text-right shrink-0">{stage.label}</span>
                      <div className="flex-1 h-6 rounded-md overflow-hidden relative" style={{ background: 'rgba(255,255,255,0.03)' }}>
                        <div
                          className="h-full rounded-md transition-all duration-700 flex items-center"
                          style={{ width: `${barWidth}%`, background: `linear-gradient(90deg, ${stage.color}dd, ${stage.color}88)`, boxShadow: `0 0 12px ${stage.glow}30` }}
                        >
                          <span className="text-[10px] font-bold text-white ml-2 whitespace-nowrap drop-shadow">{value}</span>
                        </div>
                      </div>
                      <span className="text-[10px] font-semibold w-10 text-right shrink-0" style={{ color: stage.color }}>{totalPct}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==================== CHART 2: REVENUE HEATMAP ====================
function RevenueHeatmapWidget({ data }) {
  const [metric, setMetric] = useState('count');

  if (!data?.grid?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg bg-slate-900" data-testid="revenue-heatmap-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><Database size={20} className="text-emerald-400" /> Revenue Heatmap</h3>
        <div className="text-center py-12 text-slate-500"><Database size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }

  const { grid, max_count, max_amount, day_names } = data;
  const maxVal = metric === 'count' ? max_count : max_amount;

  const getHeatColor = (value) => {
    if (!value || !maxVal) return 'rgba(255,255,255,0.02)';
    const intensity = value / maxVal;
    if (metric === 'count') {
      const r = Math.round(6 + intensity * 93);
      const g = Math.round(182 + intensity * (-40));
      const b = Math.round(212 + intensity * (-120));
      return `rgba(${r},${g},${b},${0.15 + intensity * 0.85})`;
    } else {
      const r = Math.round(34 + intensity * (220 - 34));
      const g = Math.round(197 + intensity * (38 - 197));
      const b = Math.round(94 + intensity * (38 - 94));
      return `rgba(${r},${g},${b},${0.15 + intensity * 0.85})`;
    }
  };

  const formatAmount = (val) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
    return val.toString();
  };

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl bg-slate-900 border border-slate-800" data-testid="revenue-heatmap-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-emerald-500 to-teal-600">
            <Database size={18} className="text-white" />
          </span>
          Revenue Heatmap
          <ChartInfoTooltip chartKey="revenueHeatmap" />
        </h3>
        <div className="flex items-center bg-slate-800 rounded-lg p-0.5" data-testid="heatmap-metric-toggle">
          {[{ key: 'count', label: 'Deposits' }, { key: 'amount', label: 'Amount' }].map(opt => (
            <button
              key={opt.key}
              onClick={() => setMetric(opt.key)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${metric === opt.key ? 'bg-slate-700 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
              data-testid={`heatmap-${opt.key}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Heatmap grid */}
      <div className="overflow-x-auto">
        <div className="min-w-[480px]">
          {/* Day headers */}
          <div className="flex items-center mb-2">
            <div className="w-28 sm:w-36 shrink-0" />
            {day_names.map(d => (
              <div key={d} className="flex-1 text-center text-[11px] font-semibold text-slate-400">{d}</div>
            ))}
          </div>

          {/* Staff rows */}
          {grid.map((row, ri) => (
            <div key={row.staff_id} className="flex items-center mb-1.5" data-testid={`heatmap-row-${row.staff_id}`}>
              <div className="w-28 sm:w-36 shrink-0 flex items-center gap-2 pr-2">
                <div className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold text-white" style={{ background: STAFF_CHART_COLORS[ri % STAFF_CHART_COLORS.length] }}>
                  {row.staff_name.charAt(0)}
                </div>
                <span className="text-xs text-slate-300 truncate">{row.staff_name}</span>
              </div>
              {row.days.map((cell, ci) => {
                const val = metric === 'count' ? cell.count : cell.amount;
                return (
                  <div key={ci} className="flex-1 px-0.5">
                    <div
                      className="h-12 sm:h-14 rounded-lg flex flex-col items-center justify-center cursor-default transition-all hover:scale-105 hover:z-10 relative group border"
                      style={{ background: getHeatColor(val), borderColor: val > 0 ? 'rgba(255,255,255,0.06)' : 'transparent' }}
                      title={`${row.staff_name} - ${cell.day}: ${cell.count} deposits, ${formatAmount(cell.amount)}`}
                    >
                      {val > 0 && (
                        <>
                          <span className="text-sm font-bold text-white drop-shadow">{metric === 'count' ? val : formatAmount(val)}</span>
                          <span className="text-[9px] text-white/50">{metric === 'count' ? 'dep' : `${cell.count}x`}</span>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Color scale */}
      <div className="flex items-center justify-end gap-2 mt-3 pt-3 border-t border-slate-800">
        <span className="text-[10px] text-slate-500">Low</span>
        <div className="flex gap-0.5">
          {[0.1, 0.3, 0.5, 0.7, 0.9].map(i => (
            <div key={i} className="w-5 h-3 rounded-sm" style={{ background: getHeatColor(maxVal * i) }} />
          ))}
        </div>
        <span className="text-[10px] text-slate-500">High</span>
      </div>
    </div>
  );
}

// ==================== CHART 3: DEPOSIT LIFECYCLE ====================
function DepositLifecycleWidget({ data }) {
  if (!data?.lifecycle_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(160deg, #1a0a2e 0%, #16132d 50%, #0f172a 100%)' }} data-testid="deposit-lifecycle-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><Users size={20} className="text-fuchsia-400" /> Deposit Lifecycle</h3>
        <div className="text-center py-12 text-slate-500"><Users size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }

  const { lifecycle_data } = data;
  const maxAvgDays = Math.max(...lifecycle_data.filter(d => d.avg_days !== null).map(d => d.avg_days), 1);

  const getSpeedColor = (avgDays) => {
    if (avgDays === null) return { text: '#64748b', bar: '#334155', label: 'No Data' };
    if (avgDays <= 2) return { text: '#22c55e', bar: 'linear-gradient(90deg, #22c55e, #4ade80)', label: 'Fast' };
    if (avgDays <= 5) return { text: '#3b82f6', bar: 'linear-gradient(90deg, #3b82f6, #60a5fa)', label: 'Good' };
    if (avgDays <= 10) return { text: '#f59e0b', bar: 'linear-gradient(90deg, #f59e0b, #fbbf24)', label: 'Average' };
    return { text: '#ef4444', bar: 'linear-gradient(90deg, #ef4444, #f87171)', label: 'Slow' };
  };

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(160deg, #1a0a2e 0%, #16132d 50%, #0f172a 100%)' }} data-testid="deposit-lifecycle-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #d946ef, #a855f7)' }}>
            <Users size={18} className="text-white" />
          </span>
          Deposit Lifecycle
          <ChartInfoTooltip chartKey="depositLifecycle" />
        </h3>
        <p className="text-[11px] text-slate-500">Response to Deposit time</p>
      </div>

      <div className="space-y-3">
        {lifecycle_data.map((staff, si) => {
          const speed = getSpeedColor(staff.avg_days);
          const barWidth = staff.avg_days !== null ? Math.max(8, (staff.avg_days / maxAvgDays) * 100) : 0;

          return (
            <div key={staff.staff_id} className="rounded-xl p-3 sm:p-4 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.05)' }} data-testid={`lifecycle-staff-${staff.staff_id}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white" style={{ background: STAFF_CHART_COLORS[si % STAFF_CHART_COLORS.length] }}>
                    {staff.staff_name.charAt(0)}
                  </div>
                  <span className="text-sm font-semibold text-white">{staff.staff_name}</span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider" style={{ color: speed.text, background: `${speed.text}18` }}>
                    {speed.label}
                  </span>
                </div>
              </div>

              {/* Timeline bar */}
              <div className="flex items-center gap-3 mb-2">
                <div className="flex-1 h-7 rounded-lg overflow-hidden" style={{ background: 'rgba(255,255,255,0.03)' }}>
                  {staff.avg_days !== null ? (
                    <div className="h-full rounded-lg flex items-center transition-all duration-700" style={{ width: `${barWidth}%`, background: speed.bar, boxShadow: `0 0 16px ${speed.text}30` }}>
                      <span className="text-xs font-black text-white ml-2 drop-shadow whitespace-nowrap">
                        {staff.avg_days} days avg
                      </span>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center">
                      <span className="text-xs text-slate-600">No conversions yet</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Stats row */}
              <div className="flex items-center gap-4 text-[11px]">
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">Responded:</span>
                  <span className="font-semibold text-slate-300">{staff.total_responded}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">Converted:</span>
                  <span className="font-semibold" style={{ color: '#22c55e' }}>{staff.converted_count}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">Pending:</span>
                  <span className="font-semibold text-amber-400">{staff.pending_count}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">Rate:</span>
                  <span className="font-bold" style={{ color: staff.conversion_rate >= 50 ? '#22c55e' : staff.conversion_rate >= 25 ? '#f59e0b' : '#ef4444' }}>
                    {staff.conversion_rate}%
                  </span>
                </div>
                {staff.min_days !== null && (
                  <div className="flex items-center gap-1 ml-auto">
                    <span className="text-slate-600">Min {staff.min_days}d</span>
                    <span className="text-slate-700">|</span>
                    <span className="text-slate-600">Max {staff.max_days}d</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ==================== CHART 4: RESPONSE TIME BY STAFF ====================
function ResponseTimeByStaffWidget({ data, onDrillDown }) {
  if (!data?.response_time_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(145deg, #0a1628 0%, #162033 100%)' }} data-testid="response-time-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><BarChart3 size={20} className="text-sky-400" /> Response Time by Staff</h3>
        <div className="text-center py-12 text-slate-500"><BarChart3 size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }
  const { response_time_data } = data;
  const maxHours = Math.max(...response_time_data.filter(d => d.avg_wa_hours !== null).map(d => d.avg_wa_hours), 1);

  const getSpeedGrade = (hours) => {
    if (hours === null) return { color: '#475569', bg: 'rgba(71,85,105,0.15)', label: 'N/A' };
    if (hours <= 1) return { color: '#22c55e', bg: 'rgba(34,197,94,0.12)', label: 'Excellent' };
    if (hours <= 4) return { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', label: 'Good' };
    if (hours <= 12) return { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: 'Average' };
    return { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', label: 'Slow' };
  };

  const formatHours = (h) => {
    if (h === null) return '-';
    if (h < 1) return `${Math.round(h * 60)}m`;
    if (h >= 24) return `${(h / 24).toFixed(1)}d`;
    return `${h.toFixed(1)}h`;
  };

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(145deg, #0a1628 0%, #101d35 50%, #162033 100%)' }} data-testid="response-time-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #0ea5e9, #38bdf8)' }}>
            <BarChart3 size={18} className="text-white" />
          </span>
          Response Time by Staff
          <ChartInfoTooltip chartKey="responseTime" />
        </h3>
        <div className="flex gap-1.5 text-[9px]">
          {[{ c: '#22c55e', l: '<1h' }, { c: '#3b82f6', l: '1-4h' }, { c: '#f59e0b', l: '4-12h' }, { c: '#ef4444', l: '>12h' }].map(g => (
            <span key={g.l} className="px-1.5 py-0.5 rounded-md border" style={{ color: g.c, borderColor: `${g.c}30`, background: `${g.c}08` }}>{g.l}</span>
          ))}
        </div>
      </div>
      <div className="space-y-2.5">
        {response_time_data.map((staff, si) => {
          const grade = getSpeedGrade(staff.avg_wa_hours);
          const barWidth = staff.avg_wa_hours !== null ? Math.max(6, (staff.avg_wa_hours / maxHours) * 100) : 0;
          return (
            <div key={staff.staff_id} className="rounded-xl p-3 border cursor-pointer hover:border-sky-500/30 transition-colors" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.05)' }} data-testid={`response-time-staff-${staff.staff_id}`} onClick={() => onDrillDown?.('response_time', { staff_id: staff.staff_id, staff_name: staff.staff_name })}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white" style={{ background: STAFF_CHART_COLORS[si % STAFF_CHART_COLORS.length] }}>
                    {staff.staff_name.charAt(0)}
                  </div>
                  <span className="text-sm font-semibold text-white">{staff.staff_name}</span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider" style={{ color: grade.color, background: grade.bg }}>{grade.label}</span>
                </div>
                <div className="text-right">
                  <span className="text-lg font-black" style={{ color: grade.color }}>{formatHours(staff.avg_wa_hours)}</span>
                  <span className="text-[10px] text-slate-500 ml-1">avg WA</span>
                </div>
              </div>
              {/* Dual bars: WA time and Response time */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 w-14 text-right shrink-0">WA Check</span>
                  <div className="flex-1 h-5 rounded-md overflow-hidden" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <div className="h-full rounded-md flex items-center transition-all duration-700" style={{ width: `${barWidth}%`, background: `linear-gradient(90deg, ${grade.color}cc, ${grade.color}66)`, boxShadow: `0 0 10px ${grade.color}25` }}>
                      <span className="text-[9px] font-bold text-white ml-1.5 drop-shadow whitespace-nowrap">{formatHours(staff.avg_wa_hours)}</span>
                    </div>
                  </div>
                </div>
                {staff.avg_respond_hours !== null && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-500 w-14 text-right shrink-0">Response</span>
                    <div className="flex-1 h-5 rounded-md overflow-hidden" style={{ background: 'rgba(255,255,255,0.03)' }}>
                      <div className="h-full rounded-md flex items-center transition-all duration-700" style={{ width: `${Math.max(6, (staff.avg_respond_hours / maxHours) * 100)}%`, background: 'linear-gradient(90deg, #a78bfacc, #a78bfa66)', boxShadow: '0 0 10px rgba(167,139,250,0.25)' }}>
                        <span className="text-[9px] font-bold text-white ml-1.5 drop-shadow whitespace-nowrap">{formatHours(staff.avg_respond_hours)}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-4 mt-1.5 text-[10px]">
                <span className="text-slate-500">Assigned: <span className="text-slate-300 font-semibold">{staff.total_assigned}</span></span>
                <span className="text-slate-500">WA'd: <span className="text-slate-300 font-semibold">{staff.wa_checked_count}</span></span>
                <span className="text-slate-500">Responded: <span className="text-slate-300 font-semibold">{staff.responded_count}</span></span>
                {staff.fastest_wa !== null && <span className="text-slate-600 ml-auto">Best {formatHours(staff.fastest_wa)}</span>}
                <ChevronRight size={12} className="text-slate-600 ml-auto shrink-0" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==================== CHART 5: FOLLOW-UP EFFECTIVENESS ====================
function FollowupEffectivenessWidget({ data, onDrillDown }) {
  if (!data?.effectiveness_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(150deg, #0f1a0f 0%, #0d1f17 100%)' }} data-testid="followup-effectiveness-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><TrendingUp size={20} className="text-emerald-400" /> Follow-up Effectiveness</h3>
        <div className="text-center py-12 text-slate-500"><TrendingUp size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }
  const { effectiveness_data } = data;

  const chartData = effectiveness_data.map(s => ({
    name: s.staff_name,
    wa_checked: s.wa_checked,
    responded: s.responded,
    deposited: s.deposited,
    effectiveness: s.effectiveness
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const d = effectiveness_data.find(s => s.staff_name === label);
    return (
      <div className="rounded-xl px-4 py-3 shadow-2xl border text-sm backdrop-blur-xl" style={{ background: 'rgba(15,23,42,0.95)', borderColor: 'rgba(255,255,255,0.08)' }}>
        <p className="font-bold text-white mb-2">{label}</p>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between gap-4"><span className="text-slate-400">WA Checked</span><span className="text-sky-400 font-semibold">{d?.wa_checked}</span></div>
          <div className="flex justify-between gap-4"><span className="text-slate-400">Responded</span><span className="text-amber-400 font-semibold">{d?.responded}</span></div>
          <div className="flex justify-between gap-4"><span className="text-slate-400">Deposited</span><span className="text-emerald-400 font-semibold">{d?.deposited}</span></div>
          <div className="border-t border-slate-700 pt-1 flex justify-between gap-4"><span className="text-slate-300 font-medium">Effectiveness</span><span className="text-white font-bold">{d?.effectiveness}%</span></div>
        </div>
      </div>
    );
  };

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(150deg, #0f1a0f 0%, #0d1f17 50%, #0f172a 100%)' }} data-testid="followup-effectiveness-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
            <TrendingUp size={18} className="text-white" />
          </span>
          Follow-up Effectiveness
          <ChartInfoTooltip chartKey="followupEffectiveness" />
        </h3>
        <div className="flex gap-2 text-[10px]">
          {[{ c: '#38bdf8', l: 'WA Checked' }, { c: '#fbbf24', l: 'Responded' }, { c: '#4ade80', l: 'Deposited' }].map(g => (
            <div key={g.l} className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: g.c }} /><span className="text-slate-500 hidden sm:inline">{g.l}</span></div>
          ))}
        </div>
      </div>
      <div className="h-64 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 40 }}>
            <defs>
              <linearGradient id="grad_wa" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#38bdf8" stopOpacity={0.9} /><stop offset="100%" stopColor="#0284c7" stopOpacity={0.7} /></linearGradient>
              <linearGradient id="grad_resp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#fbbf24" stopOpacity={0.9} /><stop offset="100%" stopColor="#d97706" stopOpacity={0.7} /></linearGradient>
              <linearGradient id="grad_dep" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4ade80" stopOpacity={0.9} /><stop offset="100%" stopColor="#16a34a" stopOpacity={0.7} /></linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} angle={-25} textAnchor="end" axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="wa_checked" name="WA Checked" fill="url(#grad_wa)" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(d) => { const s = effectiveness_data.find(x => x.staff_name === d.name); if (s) onDrillDown?.('followup', { staff_id: s.staff_id, staff_name: s.staff_name }); }} />
            <Bar dataKey="responded" name="Responded" fill="url(#grad_resp)" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(d) => { const s = effectiveness_data.find(x => x.staff_name === d.name); if (s) onDrillDown?.('followup', { staff_id: s.staff_id, staff_name: s.staff_name }); }} />
            <Bar dataKey="deposited" name="Deposited" fill="url(#grad_dep)" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(d) => { const s = effectiveness_data.find(x => x.staff_name === d.name); if (s) onDrillDown?.('followup', { staff_id: s.staff_id, staff_name: s.staff_name }); }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {/* Effectiveness ranking */}
      <div className="mt-4 pt-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <p className="text-[11px] text-slate-500 mb-2">Conversion Rate (Responded → Deposited)</p>
        <div className="flex flex-wrap gap-2">
          {effectiveness_data.slice(0, 8).map((s, i) => (
            <div key={s.staff_id} className="flex items-center gap-1.5 px-2 py-1 rounded-lg border cursor-pointer hover:border-emerald-500/30 transition-colors" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }} onClick={() => onDrillDown?.('followup', { staff_id: s.staff_id, staff_name: s.staff_name })}>
              <span className="text-[10px] text-slate-400">{s.staff_name}</span>
              <span className="text-[11px] font-bold" style={{ color: s.effectiveness >= 50 ? '#22c55e' : s.effectiveness >= 25 ? '#f59e0b' : '#ef4444' }}>{s.effectiveness}%</span>
              <ChevronRight size={10} className="text-slate-600" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ==================== CHART 6: PRODUCT PERFORMANCE ====================
function ProductPerformanceWidget({ data, onDrillDown }) {
  if (!data?.product_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(135deg, #1a0f2e 0%, #1e1338 100%)' }} data-testid="product-performance-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><Package size={20} className="text-violet-400" /> Product Performance</h3>
        <div className="text-center py-12 text-slate-500"><Package size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }
  const { product_data } = data;
  const DONUT_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6'];
  const totalAmount = product_data.reduce((s, p) => s + p.total_amount, 0);

  const pieData = product_data.map((p, i) => ({
    name: p.product_name,
    value: p.total_count,
    amount: p.total_amount,
    fill: DONUT_COLORS[i % DONUT_COLORS.length]
  }));

  const formatAmt = (val) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
    return val.toString();
  };

  const CustomLabel = ({ cx, cy }) => (
    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle">
      <tspan x={cx} y={cy - 8} fill="#fff" fontSize="18" fontWeight="800">{product_data.length}</tspan>
      <tspan x={cx} y={cy + 12} fill="#64748b" fontSize="10">Products</tspan>
    </text>
  );

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(135deg, #1a0f2e 0%, #1e1338 50%, #0f172a 100%)' }} data-testid="product-performance-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' }}>
            <Package size={18} className="text-white" />
          </span>
          Product Performance
          <ChartInfoTooltip chartKey="productPerformance" />
        </h3>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donut chart */}
        <div className="h-64 sm:h-72">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsPie>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={95} paddingAngle={3} dataKey="value" stroke="none" label={CustomLabel} labelLine={false} cursor="pointer" onClick={(_, idx) => { const p = product_data[idx]; if (p) onDrillDown?.('product_staff', { product_id: p.product_id, product_name: p.product_name }); }}>
                {pieData.map((entry, i) => <Cell key={`cell-${i}`} fill={entry.fill} />)}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-xl text-sm" style={{ background: 'rgba(15,23,42,0.95)', borderColor: 'rgba(255,255,255,0.08)' }}>
                      <p className="font-bold text-white mb-1">{d.name}</p>
                      <p className="text-slate-400 text-xs">Deposits: <span className="text-white font-semibold">{d.value}</span></p>
                      <p className="text-slate-400 text-xs">Amount: <span className="text-white font-semibold">{formatAmt(d.amount)}</span></p>
                    </div>
                  );
                }}
              />
            </RechartsPie>
          </ResponsiveContainer>
        </div>
        {/* Product breakdown */}
        <div className="space-y-2">
          {product_data.map((p, i) => {
            const pct = totalAmount > 0 ? (p.total_amount / totalAmount * 100).toFixed(1) : 0;
            return (
              <div key={p.product_id} className="rounded-lg p-3 border cursor-pointer hover:border-violet-500/30 transition-colors" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.05)' }} data-testid={`product-perf-${p.product_id}`} onClick={() => onDrillDown?.('product_staff', { product_id: p.product_id, product_name: p.product_name })}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }} />
                    <span className="text-sm font-semibold text-white">{p.product_name}</span>
                  </div>
                  <span className="text-sm font-bold text-white">{formatAmt(p.total_amount)}</span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: DONUT_COLORS[i % DONUT_COLORS.length] }} />
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[10px]">
                  <span className="text-cyan-400">NDP: {p.ndp_count}</span>
                  <span className="text-purple-400">RDP: {p.rdp_count}</span>
                  <span className="text-slate-500 ml-auto">{pct}% of total</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ==================== CHART 7: CUSTOMER VALUE COMPARISON (LTV) ====================
function CustomerValueWidget({ data, onDrillDown }) {
  if (!data?.staff_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(145deg, #1a0a0a 0%, #2d1313 100%)' }} data-testid="customer-value-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><Users size={20} className="text-rose-400" /> New vs Returning Customer Value</h3>
        <div className="text-center py-12 text-slate-500"><Users size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }
  const { staff_data, summary } = data;
  const formatAmt = (val) => {
    if (!val) return '0';
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
    return val.toLocaleString();
  };

  const chartData = staff_data.map(s => ({
    name: s.staff_name,
    ndp: s.ndp_amount,
    rdp: s.rdp_amount,
  }));

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(145deg, #1a0a0a 0%, #1f1020 50%, #0f172a 100%)' }} data-testid="customer-value-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #e11d48, #f43f5e)' }}>
            <Users size={18} className="text-white" />
          </span>
          New vs Returning Value
          <ChartInfoTooltip chartKey="customerValue" />
        </h3>
        {summary && (
          <div className="flex gap-3 text-xs">
            <div className="px-3 py-1.5 rounded-lg border" style={{ borderColor: 'rgba(34,211,238,0.3)', background: 'rgba(34,211,238,0.08)' }}>
              <span className="text-cyan-400 font-bold">{formatAmt(summary.total_ndp_amount)}</span>
              <span className="text-slate-500 ml-1">NDP</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg border" style={{ borderColor: 'rgba(167,139,250,0.3)', background: 'rgba(167,139,250,0.08)' }}>
              <span className="text-purple-400 font-bold">{formatAmt(summary.total_rdp_amount)}</span>
              <span className="text-slate-500 ml-1">RDP</span>
            </div>
          </div>
        )}
      </div>
      {/* Stacked bar chart */}
      <div className="h-64 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 40 }}>
            <defs>
              <linearGradient id="grad_ndp_val" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#22d3ee" stopOpacity={0.9} /><stop offset="100%" stopColor="#0891b2" stopOpacity={0.7} /></linearGradient>
              <linearGradient id="grad_rdp_val" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a78bfa" stopOpacity={0.9} /><stop offset="100%" stopColor="#7c3aed" stopOpacity={0.7} /></linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} angle={-25} textAnchor="end" axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => formatAmt(v)} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const s = staff_data.find(x => x.staff_name === label);
                return (
                  <div className="rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-xl text-sm" style={{ background: 'rgba(15,23,42,0.95)', borderColor: 'rgba(255,255,255,0.08)' }}>
                    <p className="font-bold text-white mb-2">{label}</p>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between gap-4"><span className="text-cyan-400">NDP Value</span><span className="text-white font-semibold">{formatAmt(s?.ndp_amount)}</span></div>
                      <div className="flex justify-between gap-4"><span className="text-purple-400">RDP Value</span><span className="text-white font-semibold">{formatAmt(s?.rdp_amount)}</span></div>
                      <div className="border-t border-slate-700 pt-1 flex justify-between gap-4"><span className="text-slate-300">Avg NDP</span><span className="text-white font-semibold">{formatAmt(s?.avg_ndp)}</span></div>
                      <div className="flex justify-between gap-4"><span className="text-slate-300">Avg RDP</span><span className="text-white font-semibold">{formatAmt(s?.avg_rdp)}</span></div>
                    </div>
                  </div>
                );
              }}
            />
            <Bar dataKey="ndp" name="New Customer (NDP)" stackId="a" fill="url(#grad_ndp_val)" radius={[0, 0, 0, 0]} cursor="pointer" onClick={(d) => { const s = staff_data.find(x => x.staff_name === d.name); if (s) onDrillDown?.('staff_customers', { staff_id: s.staff_id, staff_name: s.staff_name }); }} />
            <Bar dataKey="rdp" name="Returning (RDP)" stackId="a" fill="url(#grad_rdp_val)" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(d) => { const s = staff_data.find(x => x.staff_name === d.name); if (s) onDrillDown?.('staff_customers', { staff_id: s.staff_id, staff_name: s.staff_name }); }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {/* Share indicator */}
      {summary && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-500">NDP Share</span>
            <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
              <div className="h-full rounded-full" style={{ width: `${summary.ndp_share}%`, background: 'linear-gradient(90deg, #22d3ee, #0891b2)' }} />
            </div>
            <span className="text-[11px] font-bold text-cyan-400">{summary.ndp_share}%</span>
            <span className="text-[11px] text-slate-500 ml-2">RDP</span>
            <span className="text-[11px] font-bold text-purple-400">{(100 - summary.ndp_share).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== CHART 8: DEPOSIT TRENDS OVER TIME ====================
function DepositTrendsWidget({ data, onGranularityChange, granularity, onDrillDown }) {
  if (!data?.chart_data?.length) {
    return (
      <div className="rounded-2xl p-6 shadow-lg" style={{ background: 'linear-gradient(160deg, #0f172a 0%, #1a1a2e 100%)' }} data-testid="deposit-trends-widget">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2"><TrendingUp size={20} className="text-indigo-400" /> Deposit Trends</h3>
        <div className="text-center py-12 text-slate-500"><TrendingUp size={48} className="mx-auto mb-3 opacity-30" /><p>No data available</p></div>
      </div>
    );
  }
  const { chart_data, summary } = data;
  const formatAmt = (val) => {
    if (!val) return '0';
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
    return val.toLocaleString();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    if (granularity === 'monthly') {
      const [y, m] = dateStr.split('-');
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${months[parseInt(m) - 1]} ${y.slice(2)}`;
    }
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  };

  return (
    <div className="rounded-2xl p-4 sm:p-5 shadow-xl" style={{ background: 'linear-gradient(160deg, #0f172a 0%, #1a1a2e 50%, #0f172a 100%)' }} data-testid="deposit-trends-widget">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #6366f1, #818cf8)' }}>
            <TrendingUp size={18} className="text-white" />
          </span>
          Deposit Trends
          <ChartInfoTooltip chartKey="depositTrends" />
        </h3>
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg p-0.5" style={{ background: 'rgba(255,255,255,0.06)' }} data-testid="granularity-toggle">
            {['daily', 'weekly', 'monthly'].map(g => (
              <button
                key={g}
                onClick={() => onGranularityChange?.(g)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${granularity === g ? 'text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
                style={granularity === g ? { background: 'rgba(99,102,241,0.5)' } : {}}
                data-testid={`granularity-${g}`}
              >{g.charAt(0).toUpperCase() + g.slice(1)}</button>
            ))}
          </div>
        </div>
      </div>
      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Total Volume', value: formatAmt(summary.total_amount), color: '#6366f1' },
            { label: 'Total Deposits', value: summary.total_deposits.toLocaleString(), color: '#22c55e' },
            { label: 'Avg/Period', value: formatAmt(summary.avg_per_period), color: '#f59e0b' },
            { label: 'Peak', value: formatAmt(summary.peak_amount), color: '#ef4444' },
          ].map(s => (
            <div key={s.label} className="rounded-lg p-3 border" style={{ borderColor: `${s.color}20`, background: `${s.color}08` }}>
              <p className="text-[10px] text-slate-500">{s.label}</p>
              <p className="text-lg font-bold" style={{ color: s.color }}>{s.value}</p>
            </div>
          ))}
        </div>
      )}
      {/* Main chart */}
      <div className="h-64 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chart_data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <defs>
              <linearGradient id="grad_trend_amt" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="grad_trend_count" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="amount" tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => formatAmt(v)} />
            <YAxis yAxisId="count" orientation="right" tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const d = chart_data.find(x => x.date === label);
                return (
                  <div className="rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-xl text-sm" style={{ background: 'rgba(15,23,42,0.95)', borderColor: 'rgba(255,255,255,0.08)' }}>
                    <p className="font-semibold text-slate-300 mb-2 text-xs">{formatDate(label)}</p>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between gap-4"><span className="text-indigo-400">Amount</span><span className="text-white font-semibold">{formatAmt(d?.amount)}</span></div>
                      <div className="flex justify-between gap-4"><span className="text-emerald-400">Deposits</span><span className="text-white font-semibold">{d?.count}</span></div>
                      <div className="flex justify-between gap-4"><span className="text-slate-400">Unique Customers</span><span className="text-white font-semibold">{d?.unique_customers}</span></div>
                      <div className="flex justify-between gap-4"><span className="text-slate-400">Avg Deposit</span><span className="text-white font-semibold">{formatAmt(d?.avg_deposit)}</span></div>
                    </div>
                  </div>
                );
              }}
            />
            <Area yAxisId="amount" type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={2} fill="url(#grad_trend_amt)" dot={false} activeDot={{ r: 5, stroke: '#6366f1', fill: '#0f172a', strokeWidth: 2, cursor: 'pointer', onClick: (e, p) => { const d = chart_data[p.index]; if (d) onDrillDown?.('date_deposits', { date: d.date, granularity }); } }} />
            <Line yAxisId="count" type="monotone" dataKey="count" stroke="#22c55e" strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: '#22c55e', fill: '#0f172a', strokeWidth: 2, cursor: 'pointer', onClick: (e, p) => { const d = chart_data[p.index]; if (d) onDrillDown?.('date_deposits', { date: d.date, granularity }); } }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center gap-4 mt-2 text-[11px]">
        <div className="flex items-center gap-1.5"><span className="w-3 h-1 rounded-full" style={{ background: '#6366f1' }} /><span className="text-slate-400">Deposit Amount</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3 h-1 rounded-full" style={{ background: '#22c55e' }} /><span className="text-slate-400">Deposit Count</span></div>
      </div>
    </div>
  );
}


// ==================== DRILL-DOWN PANEL ====================
function DrillDownPanel({ isOpen, onClose, title, subtitle, loading, data, type }) {
  if (!isOpen) return null;

  const formatAmt = (val) => {
    if (!val) return '0';
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
    return val.toLocaleString();
  };

  const formatHours = (h) => {
    if (h === null || h === undefined) return '-';
    if (h < 1) return `${Math.round(h * 60)}m`;
    if (h >= 24) return `${(h / 24).toFixed(1)}d`;
    return `${h.toFixed(1)}h`;
  };

  const formatDate = (d) => {
    if (!d) return '-';
    try {
      const dt = new Date(d.includes('T') ? d : d + 'T00:00:00');
      return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' });
    } catch { return d; }
  };

  const renderContent = () => {
    if (loading) return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={28} className="animate-spin text-indigo-400" />
        <span className="ml-3 text-slate-400">Loading details...</span>
      </div>
    );
    if (!data) return <div className="text-center py-16 text-slate-500">No data available</div>;

    switch (type) {
      case 'response_time':
        return (
          <div className="space-y-2" data-testid="drilldown-response-time">
            <div className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
              <div className="col-span-2">Customer</div>
              <div className="col-span-2">Product</div>
              <div className="col-span-2">Assigned</div>
              <div className="col-span-1">WA</div>
              <div className="col-span-2 text-right">WA Time</div>
              <div className="col-span-1">Resp</div>
              <div className="col-span-2 text-right">Resp Time</div>
            </div>
            {data.records?.map((r, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 px-3 py-2.5 rounded-lg text-xs items-center hover:bg-white/[0.03] transition-colors" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <div className="col-span-2 text-slate-300 truncate font-medium">{r.customer_id}</div>
                <div className="col-span-2 text-slate-500 truncate">{r.product}</div>
                <div className="col-span-2 text-slate-500">{formatDate(r.assigned_at)}</div>
                <div className="col-span-1">
                  {r.wa_status === 'ada' ? <CheckCircle2 size={14} className="text-emerald-400" /> : r.wa_status === 'tidak' ? <XCircle size={14} className="text-red-400" /> : <span className="text-slate-600">-</span>}
                </div>
                <div className="col-span-2 text-right font-semibold" style={{ color: r.wa_hours === null ? '#475569' : r.wa_hours <= 1 ? '#22c55e' : r.wa_hours <= 4 ? '#3b82f6' : r.wa_hours <= 12 ? '#f59e0b' : '#ef4444' }}>
                  {formatHours(r.wa_hours)}
                </div>
                <div className="col-span-1">
                  {r.respond_status === 'ya' ? <CheckCircle2 size={14} className="text-emerald-400" /> : r.respond_status === 'tidak' ? <XCircle size={14} className="text-red-400" /> : <span className="text-slate-600">-</span>}
                </div>
                <div className="col-span-2 text-right font-semibold text-purple-400">{formatHours(r.respond_hours)}</div>
              </div>
            ))}
          </div>
        );

      case 'followup':
        return (
          <div data-testid="drilldown-followup">
            <div className="flex gap-3 mb-4">
              <div className="flex-1 rounded-lg p-3 border" style={{ borderColor: 'rgba(34,197,94,0.2)', background: 'rgba(34,197,94,0.06)' }}>
                <p className="text-[10px] text-slate-500">Converted</p>
                <p className="text-xl font-bold text-emerald-400">{data.converted}</p>
              </div>
              <div className="flex-1 rounded-lg p-3 border" style={{ borderColor: 'rgba(245,158,11,0.2)', background: 'rgba(245,158,11,0.06)' }}>
                <p className="text-[10px] text-slate-500">Pending</p>
                <p className="text-xl font-bold text-amber-400">{data.pending}</p>
              </div>
              <div className="flex-1 rounded-lg p-3 border" style={{ borderColor: 'rgba(99,102,241,0.2)', background: 'rgba(99,102,241,0.06)' }}>
                <p className="text-[10px] text-slate-500">Total</p>
                <p className="text-xl font-bold text-indigo-400">{data.total}</p>
              </div>
            </div>
            <div className="space-y-1.5">
              {data.records?.map((r, i) => (
                <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0" style={{ background: r.deposited ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)' }}>
                    {r.deposited ? <CheckCircle2 size={13} className="text-emerald-400" /> : <Clock size={13} className="text-amber-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-300 truncate">{r.customer_id}</p>
                    <p className="text-[10px] text-slate-500">{r.product} {r.respond_at ? `• Responded ${formatDate(r.respond_at)}` : ''}</p>
                  </div>
                  {r.deposited ? (
                    <div className="text-right shrink-0">
                      <p className="text-xs font-bold text-emerald-400">{formatAmt(r.deposit_total)}</p>
                      <p className="text-[10px] text-slate-500">{r.deposit_count}x • Last {formatDate(r.last_deposit)}</p>
                    </div>
                  ) : (
                    <span className="text-[10px] text-amber-400 font-medium shrink-0">Pending</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      case 'product_staff':
        return (
          <div data-testid="drilldown-product-staff">
            <p className="text-xs text-slate-500 mb-3">{data.total_staff} staff with deposits for this product</p>
            <div className="space-y-2">
              {data.staff_breakdown?.map((s, i) => (
                <div key={s.staff_id} className="rounded-xl p-3 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.05)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white" style={{ background: STAFF_CHART_COLORS[i % STAFF_CHART_COLORS.length] }}>
                        {s.staff_name.charAt(0)}
                      </div>
                      <span className="text-sm font-semibold text-white">{s.staff_name}</span>
                    </div>
                    <span className="text-sm font-bold text-white">{formatAmt(s.total_amount)}</span>
                  </div>
                  <div className="flex gap-4 text-[11px]">
                    <span className="text-cyan-400">NDP: {s.ndp_count} ({formatAmt(s.ndp_amount)})</span>
                    <span className="text-purple-400">RDP: {s.rdp_count} ({formatAmt(s.rdp_amount)})</span>
                    <span className="text-slate-500 ml-auto">{s.total_count} total deposits</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'staff_customers':
        return (
          <div data-testid="drilldown-staff-customers">
            <div className="space-y-1.5">
              {data.customers?.map((c, i) => (
                <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <div className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold shrink-0" style={{ background: c.type === 'NDP' ? 'rgba(34,211,238,0.15)' : 'rgba(167,139,250,0.15)', color: c.type === 'NDP' ? '#22d3ee' : '#a78bfa' }}>
                    {c.type === 'NDP' ? 'N' : 'R'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-300 truncate">{c.customer_name || c.customer_id}</p>
                    <p className="text-[10px] text-slate-500">{c.product} • {c.deposit_count}x deposits</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-bold text-white">{formatAmt(c.total_amount)}</p>
                    <p className="text-[10px] text-slate-500">{formatDate(c.first_deposit)} - {formatDate(c.last_deposit)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'date_deposits':
        return (
          <div data-testid="drilldown-date-deposits">
            <div className="flex gap-3 mb-4">
              <div className="flex-1 rounded-lg p-3 border" style={{ borderColor: 'rgba(99,102,241,0.2)', background: 'rgba(99,102,241,0.06)' }}>
                <p className="text-[10px] text-slate-500">Total Amount</p>
                <p className="text-xl font-bold text-indigo-400">{formatAmt(data.total_amount)}</p>
              </div>
              <div className="flex-1 rounded-lg p-3 border" style={{ borderColor: 'rgba(34,197,94,0.2)', background: 'rgba(34,197,94,0.06)' }}>
                <p className="text-[10px] text-slate-500">Deposits</p>
                <p className="text-xl font-bold text-emerald-400">{data.total_count}</p>
              </div>
            </div>
            <div className="space-y-1.5">
              {data.deposits?.map((d, i) => (
                <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-300 truncate">{d.customer_name || d.customer_id}</p>
                    <p className="text-[10px] text-slate-500">{d.staff_name} • {d.product}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-white">{formatAmt(d.amount)}</p>
                    {d.note && <p className="text-[10px] text-slate-500 truncate max-w-[120px]">{d.note}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return <div className="text-center py-12 text-slate-500">Unknown drill-down type</div>;
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" onClick={onClose} data-testid="drilldown-backdrop" />
      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-full sm:w-[540px] lg:w-[620px] z-50 shadow-2xl flex flex-col" style={{ background: 'linear-gradient(180deg, #0f172a 0%, #131b2e 100%)' }} data-testid="drilldown-panel">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <div>
            <h3 className="text-base font-bold text-white">{title}</h3>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10 transition-colors" data-testid="drilldown-close">
            <X size={18} className="text-slate-400" />
          </button>
        </div>
        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 custom-scrollbar">
          {renderContent()}
        </div>
      </div>
    </>
  );
}


function SortableWidget({ id, children, isVisible }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    display: isVisible ? 'block' : 'none'
  };

  return (
    <div ref={setNodeRef} style={style} className="relative group">
      <div
        {...attributes}
        {...listeners}
        className="absolute top-4 right-4 z-10 p-2 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 transition-opacity"
        title="Drag to reorder"
      >
        <GripVertical size={16} className="text-slate-500" />
      </div>
      {children}
    </div>
  );
}

export default function AdvancedAnalytics() {
  const [staffData, setStaffData] = useState(null);
  const [businessData, setBusinessData] = useState(null);
  const [staffNdpRdpData, setStaffNdpRdpData] = useState(null);
  const [funnelData, setFunnelData] = useState(null);
  const [heatmapData, setHeatmapData] = useState(null);
  const [lifecycleData, setLifecycleData] = useState(null);
  const [responseTimeData, setResponseTimeData] = useState(null);
  const [followupEffData, setFollowupEffData] = useState(null);
  const [productPerfData, setProductPerfData] = useState(null);
  const [customerValueData, setCustomerValueData] = useState(null);
  const [depositTrendsData, setDepositTrendsData] = useState(null);
  const [depositGranularity, setDepositGranularity] = useState('daily');
  const [products, setProducts] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingLayout, setSavingLayout] = useState(false);
  const [layoutChanged, setLayoutChanged] = useState(false);
  
  const [period, setPeriod] = useState('month');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('');
  
  const [widgetOrder, setWidgetOrder] = useState(DEFAULT_WIDGET_ORDER);
  const [visibleWidgets, setVisibleWidgets] = useState({
    staffNdpRdpDaily: true,
    conversionFunnel: true,
    revenueHeatmap: true,
    depositLifecycle: true,
    responseTime: true,
    followupEffectiveness: true,
    productPerformance: true,
    customerValue: true,
    depositTrends: true,
    staffCompare: true,
    staffComparison: true,
    dailyTrends: true,
    whatsappDistribution: true,
    responseRate: true,
    omsetTrends: true,
    productOmset: true,
    ndpRdp: true,
    databaseUtilization: true
  });
  
  // Compare Staff feature state
  const [compareMode, setCompareMode] = useState(false);
  const [compareStaff, setCompareStaff] = useState([]);
  const [compareData, setCompareData] = useState(null);
  const [loadingCompare, setLoadingCompare] = useState(false);
  
  const [showWidgetSettings, setShowWidgetSettings] = useState(false);
  const [activeId, setActiveId] = useState(null);
  
  // Drill-down state
  const [drillDown, setDrillDown] = useState({ isOpen: false, type: null, title: '', subtitle: '', data: null, loading: false });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    loadFilters();
    loadSavedLayout();
  }, []);

  useEffect(() => {
    loadAnalytics();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, selectedProduct, selectedStaff]);

  const loadFilters = async () => {
    try {
      const [productsRes, staffRes] = await Promise.all([
        api.get('/products'),
        api.get('/staff-users')
      ]);
      setProducts(productsRes.data);
      setStaff(staffRes.data);
    } catch (error) {
      console.error('Failed to load filters');
    }
  };

  const loadSavedLayout = async () => {
    try {
      const response = await api.get('/user/preferences/widget-layout');
      if (response.data.widget_order?.length > 0) {
        // Merge saved layout with default to include any new widgets
        const savedOrder = response.data.widget_order;
        const newWidgets = DEFAULT_WIDGET_ORDER.filter(w => !savedOrder.includes(w));
        // Add new widgets at the beginning
        setWidgetOrder([...newWidgets, ...savedOrder]);
      }
    } catch (error) {
      console.error('Failed to load saved layout');
    }
  };

  const saveLayout = async () => {
    setSavingLayout(true);
    try {
      await api.put('/user/preferences/widget-layout', { widget_order: widgetOrder });
      toast.success('Layout saved successfully');
      setLayoutChanged(false);
    } catch (error) {
      toast.error('Failed to save layout');
    } finally {
      setSavingLayout(false);
    }
  };

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ period });
      if (selectedProduct) params.append('product_id', selectedProduct);
      if (selectedStaff) params.append('staff_id', selectedStaff);

      const [staffRes, businessRes, ndpRdpRes, funnelRes, heatmapRes, lifecycleRes, respTimeRes, followupEffRes, productPerfRes, custValueRes, depositTrendsRes] = await Promise.all([
        api.get(`/analytics/staff-performance?${params}`),
        api.get(`/analytics/business?${params}`),
        api.get(`/analytics/staff-ndp-rdp-daily?${params}`),
        api.get(`/analytics/staff-conversion-funnel?${params}`),
        api.get(`/analytics/revenue-heatmap?${params}`),
        api.get(`/analytics/deposit-lifecycle?${params}`),
        api.get(`/analytics/response-time-by-staff?${params}`),
        api.get(`/analytics/followup-effectiveness?${params}`),
        api.get(`/analytics/product-performance?${params}`),
        api.get(`/analytics/customer-value-comparison?${params}`),
        api.get(`/analytics/deposit-trends?${params}&granularity=${depositGranularity}`)
      ]);
      
      setStaffData(staffRes.data);
      setBusinessData(businessRes.data);
      setStaffNdpRdpData(ndpRdpRes.data);
      setFunnelData(funnelRes.data);
      setHeatmapData(heatmapRes.data);
      setLifecycleData(lifecycleRes.data);
      setResponseTimeData(respTimeRes.data);
      setFollowupEffData(followupEffRes.data);
      setProductPerfData(productPerfRes.data);
      setCustomerValueData(custValueRes.data);
      setDepositTrendsData(depositTrendsRes.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  // Load comparison data for selected staff members
  const loadCompareData = async () => {
    if (compareStaff.length < 2) {
      setCompareData(null);
      return;
    }

    setLoadingCompare(true);
    try {
      const params = new URLSearchParams({ period });
      if (selectedProduct) params.append('product_id', selectedProduct);

      // Fetch data for each staff member in parallel
      const requests = compareStaff.map(staffId => 
        api.get(`/analytics/business?${params}&staff_id=${staffId}`)
      );
      
      const responses = await Promise.all(requests);
      
      // Build comparison dataset
      const comparisonResults = responses.map((res, idx) => {
        const staffMember = staff.find(s => s.id === compareStaff[idx]);
        return {
          staff_id: compareStaff[idx],
          staff_name: staffMember?.name || 'Unknown',
          color: COMPARISON_COLORS[idx % COMPARISON_COLORS.length],
          data: res.data
        };
      });

      // Build chart data for trends comparison
      const allDates = new Set();
      comparisonResults.forEach(result => {
        result.data.omset_chart?.forEach(d => allDates.add(d.date));
      });
      
      const sortedDates = Array.from(allDates).sort();
      const trendChartData = sortedDates.map(date => {
        const point = { date };
        comparisonResults.forEach(result => {
          const dayData = result.data.omset_chart?.find(d => d.date === date);
          point[`omset_${result.staff_id}`] = dayData?.total || 0;
          point[`count_${result.staff_id}`] = dayData?.count || 0;
        });
        return point;
      });

      setCompareData({
        staff: comparisonResults,
        trendChart: trendChartData
      });
    } catch (error) {
      console.error('Failed to load comparison data:', error);
      toast.error('Failed to load comparison data');
    } finally {
      setLoadingCompare(false);
    }
  };

  // Add staff to comparison
  const addToCompare = (staffId) => {
    if (compareStaff.length >= 6) {
      toast.warning('Maximum 6 staff members can be compared');
      return;
    }
    if (!compareStaff.includes(staffId)) {
      setCompareStaff([...compareStaff, staffId]);
    }
  };

  // Remove staff from comparison
  const removeFromCompare = (staffId) => {
    setCompareStaff(compareStaff.filter(id => id !== staffId));
  };

  // Toggle compare mode
  const toggleCompareMode = () => {
    if (compareMode) {
      setCompareStaff([]);
      setCompareData(null);
    }
    setCompareMode(!compareMode);
  };

  // Load comparison data when staff selection changes
  useEffect(() => {
    if (compareMode && compareStaff.length >= 2) {
      loadCompareData();
    } else {
      setCompareData(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compareStaff, compareMode, period, selectedProduct]);

  // Reload deposit trends when granularity changes
  const handleGranularityChange = async (newGranularity) => {
    setDepositGranularity(newGranularity);
    try {
      const params = new URLSearchParams({ period, granularity: newGranularity });
      if (selectedProduct) params.append('product_id', selectedProduct);
      const res = await api.get(`/analytics/deposit-trends?${params}`);
      setDepositTrendsData(res.data);
    } catch (error) {
      console.error('Failed to load deposit trends');
    }
  };

  // Drill-down handler
  const handleDrillDown = useCallback(async (type, params) => {
    const titles = {
      response_time: { title: `Response Time Details`, subtitle: params.staff_name },
      followup: { title: `Follow-up Details`, subtitle: params.staff_name },
      product_staff: { title: `Staff Breakdown`, subtitle: params.product_name },
      staff_customers: { title: `Top Customers`, subtitle: params.staff_name },
      date_deposits: { title: `Deposit Details`, subtitle: params.date },
    };
    const t = titles[type] || { title: 'Details', subtitle: '' };
    setDrillDown({ isOpen: true, type, title: t.title, subtitle: t.subtitle, data: null, loading: true });

    try {
      const qp = new URLSearchParams({ period });
      if (selectedProduct) qp.append('product_id', selectedProduct);

      let url;
      switch (type) {
        case 'response_time':
          qp.append('staff_id', params.staff_id);
          url = `/analytics/drill-down/response-time?${qp}`;
          break;
        case 'followup':
          qp.append('staff_id', params.staff_id);
          url = `/analytics/drill-down/followup-detail?${qp}`;
          break;
        case 'product_staff':
          url = `/analytics/drill-down/product-staff?${new URLSearchParams({ period, product_id: params.product_id })}`;
          break;
        case 'staff_customers':
          qp.append('staff_id', params.staff_id);
          url = `/analytics/drill-down/staff-customers?${qp}`;
          break;
        case 'date_deposits':
          qp.append('date', params.date);
          qp.append('granularity', params.granularity || 'daily');
          url = `/analytics/drill-down/date-deposits?${qp}`;
          break;
        default:
          setDrillDown(prev => ({ ...prev, loading: false }));
          return;
      }
      const res = await api.get(url);
      setDrillDown(prev => ({ ...prev, data: res.data, loading: false }));
    } catch (error) {
      toast.error('Failed to load details');
      setDrillDown(prev => ({ ...prev, loading: false }));
    }
  }, [period, selectedProduct]);

  const closeDrillDown = () => setDrillDown({ isOpen: false, type: null, title: '', subtitle: '', data: null, loading: false });

  const toggleWidget = (key) => {
    setVisibleWidgets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num?.toLocaleString() || '0';
  };

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);
    
    if (over && active.id !== over.id) {
      setWidgetOrder((items) => {
        const oldIndex = items.indexOf(active.id);
        const newIndex = items.indexOf(over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
      setLayoutChanged(true);
    }
  };

  const widgetConfig = {
    staffNdpRdpDaily: { label: 'Staff NDP/RDP Daily', icon: BarChart3 },
    conversionFunnel: { label: 'Staff Conversion Funnel', icon: TrendingUp },
    revenueHeatmap: { label: 'Revenue Heatmap', icon: Database },
    depositLifecycle: { label: 'Deposit Lifecycle', icon: Users },
    responseTime: { label: 'Response Time by Staff', icon: BarChart3 },
    followupEffectiveness: { label: 'Follow-up Effectiveness', icon: TrendingUp },
    productPerformance: { label: 'Product Performance', icon: Package },
    customerValue: { label: 'New vs Returning Value', icon: Users },
    depositTrends: { label: 'Deposit Trends Over Time', icon: TrendingUp },
    staffCompare: { label: 'Staff Comparison (Side-by-Side)', icon: GitCompare },
    staffComparison: { label: 'Staff Performance Comparison', icon: Users },
    dailyTrends: { label: 'Daily Activity Trends', icon: TrendingUp },
    whatsappDistribution: { label: 'WhatsApp Status Distribution', icon: PieChart },
    responseRate: { label: 'Response Rate by Staff', icon: BarChart3 },
    omsetTrends: { label: 'OMSET Trends', icon: TrendingUp },
    productOmset: { label: 'OMSET by Product', icon: Package },
    ndpRdp: { label: 'NDP vs RDP Analysis', icon: PieChart },
    databaseUtilization: { label: 'Database Utilization', icon: Database }
  };

  const renderWidget = (widgetId) => {
    switch (widgetId) {
      case 'staffNdpRdpDaily':
        return <StaffNdpRdpDailyWidget data={staffNdpRdpData} />;

      case 'conversionFunnel':
        return <ConversionFunnelWidget data={funnelData} />;

      case 'revenueHeatmap':
        return <RevenueHeatmapWidget data={heatmapData} />;

      case 'depositLifecycle':
        return <DepositLifecycleWidget data={lifecycleData} />;

      case 'responseTime':
        return <ResponseTimeByStaffWidget data={responseTimeData} onDrillDown={handleDrillDown} />;

      case 'followupEffectiveness':
        return <FollowupEffectivenessWidget data={followupEffData} onDrillDown={handleDrillDown} />;

      case 'productPerformance':
        return <ProductPerformanceWidget data={productPerfData} onDrillDown={handleDrillDown} />;

      case 'customerValue':
        return <CustomerValueWidget data={customerValueData} onDrillDown={handleDrillDown} />;

      case 'depositTrends':
        return <DepositTrendsWidget data={depositTrendsData} onGranularityChange={handleGranularityChange} granularity={depositGranularity} onDrillDown={handleDrillDown} />;

      case 'staffCompare':
        return (
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm" data-testid="staff-compare-widget">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <GitCompare size={20} className="text-purple-600" />
                Staff Comparison (Side-by-Side)
                <ChartInfoTooltip chartKey="staffCompare" />
              </h3>
              <button
                onClick={toggleCompareMode}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  compareMode 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                }`}
                data-testid="toggle-compare-mode"
              >
                {compareMode ? 'Exit Compare Mode' : 'Enable Compare Mode'}
              </button>
            </div>

            {!compareMode ? (
              <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                <GitCompare size={48} className="mx-auto mb-3 opacity-30" />
                <p className="font-medium">Enable Compare Mode to compare staff performance</p>
                <p className="text-sm mt-1">Select 2-6 staff members to see side-by-side charts</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Staff Selection */}
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Select staff to compare:</span>
                  <select
                    onChange={(e) => e.target.value && addToCompare(e.target.value)}
                    value=""
                    className="h-9 px-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    disabled={compareStaff.length >= 6}
                    data-testid="compare-staff-select"
                  >
                    <option value="">+ Add staff...</option>
                    {staff.filter(s => !compareStaff.includes(s.id)).map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>

                {/* Selected Staff Chips */}
                {compareStaff.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {compareStaff.map((staffId, idx) => {
                      const staffMember = staff.find(s => s.id === staffId);
                      return (
                        <span 
                          key={staffId}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium text-white"
                          style={{ backgroundColor: COMPARISON_COLORS[idx % COMPARISON_COLORS.length] }}
                          data-testid={`compare-chip-${staffId}`}
                        >
                          {staffMember?.name}
                          <button 
                            onClick={() => removeFromCompare(staffId)}
                            className="hover:bg-white/20 rounded-full p-0.5"
                          >
                            <X size={14} />
                          </button>
                        </span>
                      );
                    })}
                    {compareStaff.length < 2 && (
                      <span className="text-sm text-amber-600 dark:text-amber-400 flex items-center gap-1">
                        <Plus size={14} /> Select at least 2 staff to compare
                      </span>
                    )}
                  </div>
                )}

                {/* Comparison Charts */}
                {loadingCompare ? (
                  <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                    <RefreshCw size={24} className="mx-auto mb-2 animate-spin" />
                    <p>Loading comparison data...</p>
                  </div>
                ) : compareData && compareStaff.length >= 2 ? (
                  <div className="space-y-6">
                    {/* Summary Comparison Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                      {compareData.staff.map((s, idx) => (
                        <div 
                          key={s.staff_id}
                          className="p-3 rounded-lg border-2"
                          style={{ borderColor: s.color, backgroundColor: `${s.color}10` }}
                        >
                          <p className="text-xs font-medium truncate" style={{ color: s.color }}>{s.staff_name}</p>
                          <p className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                            {formatNumber(s.data.summary?.total_omset)}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            NDP: {s.data.summary?.ndp_count || 0} • RDP: {s.data.summary?.rdp_count || 0}
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* OMSET Comparison Bar Chart */}
                    <div>
                      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Total OMSET Comparison</h4>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={compareData.staff.map(s => ({
                            name: s.staff_name,
                            total_omset: s.data.summary?.total_omset || 0,
                            ndp_omset: s.data.summary?.ndp_omset || 0,
                            rdp_omset: s.data.summary?.rdp_omset || 0,
                            color: s.color
                          }))}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatNumber(v)} />
                            <Tooltip formatter={(value) => formatNumber(value)} />
                            <Legend />
                            <Bar dataKey="total_omset" name="Total OMSET" fill="#8b5cf6">
                              {compareData.staff.map((s, idx) => (
                                <Cell key={`cell-${idx}`} fill={s.color} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* NDP vs RDP Comparison */}
                    <div>
                      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">NDP vs RDP Comparison</h4>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={compareData.staff.map(s => ({
                            name: s.staff_name,
                            ndp: s.data.summary?.ndp_count || 0,
                            rdp: s.data.summary?.rdp_count || 0
                          }))}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="ndp" name="NDP (New)" fill="#6366f1" />
                            <Bar dataKey="rdp" name="RDP (Return)" fill="#22c55e" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Trends Line Chart */}
                    {compareData.trendChart.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">OMSET Trends Over Time</h4>
                        <div className="h-64 sm:h-80">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={compareData.trendChart}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatNumber(v)} />
                              <Tooltip formatter={(value) => formatNumber(value)} />
                              <Legend />
                              {compareData.staff.map((s, idx) => (
                                <Line 
                                  key={s.staff_id}
                                  type="monotone" 
                                  dataKey={`omset_${s.staff_id}`} 
                                  name={s.staff_name}
                                  stroke={s.color} 
                                  strokeWidth={2} 
                                  dot={false} 
                                />
                              ))}
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )}
                  </div>
                ) : compareStaff.length >= 2 ? (
                  <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                    <p>No comparison data available</p>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        );

      case 'staffComparison':
        return staffData?.staff_metrics?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Users size={20} className="text-indigo-600" />
              Staff Performance Comparison
              <ChartInfoTooltip chartKey="staffComparison" />
            </h3>
            <div className="h-64 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={staffData.staff_metrics.slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="staff_name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total_assigned" name="Total Assigned" fill="#6366f1" />
                  <Bar dataKey="whatsapp_checked" name="WA Checked" fill="#22c55e" />
                  <Bar dataKey="respond_ya" name="Responded" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        );

      case 'dailyTrends':
        return staffData?.daily_chart?.length > 0 && (
          <DailyTrendsWidget data={{ daily_trends: staffData.daily_chart }} />
        );

      case 'whatsappDistribution':
        return (
          <WhatsappDistributionWidget data={staffData} />
        );

      case 'responseRate':
        return staffData?.staff_metrics?.length > 0 && (
          <ResponseRateWidget data={staffData} />
        );

      case 'omsetTrends':
        return (
          <OmsetTrendsWidget data={businessData} />
        );

      case 'productOmset':
        return (
          <ProductOmsetWidget data={businessData} />
        );

      case 'ndpRdp':
        return (
          <NdpRdpWidget data={businessData} />
        );

      case 'databaseUtilization':
        return (
          <DatabaseUtilizationWidget data={businessData} />
        );

      default:
        return null;
    }
  };

  return (
    <>
    <div data-testid="advanced-analytics">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
        <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">Advanced Analytics</h2>
        
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="period-filter"
          >
            <option value="today">Today</option>
            <option value="yesterday">Yesterday</option>
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
            <option value="quarter">Last 90 Days</option>
            <option value="year">Last Year</option>
          </select>

          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="product-filter"
          >
            <option value="">All Products</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          <select
            value={selectedStaff}
            onChange={(e) => setSelectedStaff(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="staff-filter"
          >
            <option value="">All Staff</option>
            {staff.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          <button
            onClick={() => setShowWidgetSettings(!showWidgetSettings)}
            className="h-10 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            data-testid="widget-settings-btn"
          >
            <Filter size={16} />
            <span className="hidden sm:inline">Widgets</span>
          </button>

          {layoutChanged && (
            <button
              onClick={saveLayout}
              disabled={savingLayout}
              className="h-10 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
              data-testid="save-layout-btn"
            >
              <Save size={16} />
              {savingLayout ? 'Saving...' : 'Save Layout'}
            </button>
          )}

          <button
            onClick={loadAnalytics}
            disabled={loading}
            className="h-10 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
            data-testid="refresh-btn"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Widget Visibility Settings */}
      {showWidgetSettings && (
        <div className="mb-6 p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Show/Hide Widgets</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(widgetConfig).map(([key, { label, icon: Icon }]) => (
              <button
                key={key}
                onClick={() => toggleWidget(key)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  visibleWidgets[key]
                    ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {visibleWidgets[key] ? <Eye size={14} /> : <EyeOff size={14} />}
                <span className="truncate">{label}</span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Tip: Drag widgets by the grip handle to reorder them. Click Save Layout to persist changes.
          </p>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading analytics...</div>
      ) : (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Total Records</p>
              <p className="text-2xl sm:text-3xl font-bold text-slate-900">{formatNumber(staffData?.summary?.total_records)}</p>
              <p className="text-xs text-slate-500 mt-1">In period: {formatNumber(staffData?.summary?.records_in_period)}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">WhatsApp Rate</p>
              <p className="text-2xl sm:text-3xl font-bold text-emerald-600">{staffData?.summary?.whatsapp_rate}%</p>
              <p className="text-xs text-slate-500 mt-1">Ada: {formatNumber(staffData?.summary?.whatsapp_ada)}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Response Rate</p>
              <p className="text-2xl sm:text-3xl font-bold text-blue-600">{staffData?.summary?.respond_rate}%</p>
              <p className="text-xs text-slate-500 mt-1">Ya: {formatNumber(staffData?.summary?.respond_ya)}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Total OMSET</p>
              <p className="text-2xl sm:text-3xl font-bold text-purple-600">{formatNumber(businessData?.summary?.total_omset)}</p>
              <p className="text-xs text-slate-500 mt-1">{formatNumber(businessData?.summary?.total_records)} records</p>
            </div>
          </div>

          {/* Draggable Widgets */}
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={widgetOrder} strategy={verticalListSortingStrategy}>
              <div className="space-y-6">
                {widgetOrder.map((widgetId) => (
                  <SortableWidget key={widgetId} id={widgetId} isVisible={visibleWidgets[widgetId]}>
                    {renderWidget(widgetId)}
                  </SortableWidget>
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      )}
    </div>

      {/* Drill-down Panel */}
      <DrillDownPanel
        isOpen={drillDown.isOpen}
        onClose={closeDrillDown}
        title={drillDown.title}
        subtitle={drillDown.subtitle}
        loading={drillDown.loading}
        data={drillDown.data}
        type={drillDown.type}
      />
    </>
  );
}
