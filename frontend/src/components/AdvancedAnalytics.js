import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  BarChart3, TrendingUp, Users, Package, Database, PieChart, 
  Eye, EyeOff, RefreshCw, Filter, GripVertical, Save, GitCompare, X, Plus
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

      const [staffRes, businessRes, ndpRdpRes] = await Promise.all([
        api.get(`/analytics/staff-performance?${params}`),
        api.get(`/analytics/business?${params}`),
        api.get(`/analytics/staff-ndp-rdp-daily?${params}`)
      ]);
      
      setStaffData(staffRes.data);
      setBusinessData(businessRes.data);
      setStaffNdpRdpData(ndpRdpRes.data);
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

      case 'staffCompare':
        return (
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm" data-testid="staff-compare-widget">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <GitCompare size={20} className="text-purple-600" />
                Staff Comparison (Side-by-Side)
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
  );
}
