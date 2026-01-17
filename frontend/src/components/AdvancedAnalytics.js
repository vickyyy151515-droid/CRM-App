import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  BarChart3, TrendingUp, Users, Package, Database, PieChart, 
  Eye, EyeOff, RefreshCw, Filter, GripVertical, Save
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

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

const DEFAULT_WIDGET_ORDER = [
  'staffComparison',
  'dailyTrends', 
  'whatsappDistribution',
  'responseRate',
  'omsetTrends',
  'productOmset',
  'ndpRdp',
  'databaseUtilization'
];

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
    staffComparison: true,
    dailyTrends: true,
    whatsappDistribution: true,
    responseRate: true,
    omsetTrends: true,
    productOmset: true,
    ndpRdp: true,
    databaseUtilization: true
  });
  
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
        setWidgetOrder(response.data.widget_order);
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

      const [staffRes, businessRes] = await Promise.all([
        api.get(`/analytics/staff-performance?${params}`),
        api.get(`/analytics/business?${params}`)
      ]);
      
      setStaffData(staffRes.data);
      setBusinessData(businessRes.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

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
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <TrendingUp size={20} className="text-indigo-600" />
              Daily Activity Trends
            </h3>
            <div className="h-64 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={staffData.daily_chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="assigned" name="Assigned" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
                  <Area type="monotone" dataKey="wa_checked" name="WA Checked" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                  <Area type="monotone" dataKey="responded" name="Responded" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        );

      case 'whatsappDistribution':
        return (
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <PieChart size={20} className="text-indigo-600" />
              WhatsApp Status Distribution
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={[
                      { name: 'Ada', value: staffData?.summary?.whatsapp_ada || 0 },
                      { name: 'Tidak', value: staffData?.summary?.whatsapp_tidak || 0 },
                      { name: 'Ceklis1', value: staffData?.summary?.whatsapp_ceklis1 || 0 }
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  >
                    <Cell fill="#22c55e" />
                    <Cell fill="#ef4444" />
                    <Cell fill="#f59e0b" />
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
            </div>
          </div>
        );

      case 'responseRate':
        return staffData?.staff_metrics?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <BarChart3 size={20} className="text-indigo-600" />
              Response Rate by Staff
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={staffData.staff_metrics.slice(0, 8)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="staff_name" tick={{ fontSize: 12 }} width={80} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Bar dataKey="respond_rate" name="Response Rate %" fill="#6366f1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        );

      case 'omsetTrends':
        return businessData?.omset_chart?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <TrendingUp size={20} className="text-purple-600" />
              OMSET Trends
            </h3>
            <div className="h-64 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={businessData.omset_chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => formatNumber(value)} />
                  <Legend />
                  <Line type="monotone" dataKey="total" name="Total OMSET" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="count" name="Records" stroke="#06b6d4" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        );

      case 'productOmset':
        const hasProductOmsetData = businessData?.product_omset?.some(p => p.total_omset > 0);
        return (
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Package size={20} className="text-purple-600" />
              OMSET by Product
            </h3>
            {hasProductOmsetData ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={businessData.product_omset.filter(p => p.total_omset > 0).slice(0, 6)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="product_name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(value) => formatNumber(value)} />
                    <Bar dataKey="total_omset" name="Total OMSET" fill="#8b5cf6">
                      {businessData.product_omset.filter(p => p.total_omset > 0).slice(0, 6).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500 dark:text-slate-400">
                <div className="text-center">
                  <Package size={48} className="mx-auto mb-2 opacity-30" />
                  <p>No OMSET data available for this period</p>
                  <p className="text-sm mt-1">Add OMSET records from the "OMSET CRM" page</p>
                </div>
              </div>
            )}
          </div>
        );

      case 'ndpRdp':
        const hasNdpRdpData = (businessData?.summary?.ndp_count || 0) + (businessData?.summary?.rdp_count || 0) > 0;
        return (
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <PieChart size={20} className="text-purple-600" />
              NDP vs RDP Analysis
            </h3>
            {hasNdpRdpData ? (
              <>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPie>
                      <Pie
                        data={[
                          { name: 'NDP (New)', value: businessData?.summary?.ndp_count || 0 },
                          { name: 'RDP (Return)', value: businessData?.summary?.rdp_count || 0 }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        <Cell fill="#6366f1" />
                        <Cell fill="#22c55e" />
                      </Pie>
                      <Tooltip />
                    </RechartsPie>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-4 text-center">
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">NDP OMSET</p>
                    <p className="text-lg font-bold text-indigo-600">{formatNumber(businessData?.summary?.ndp_omset)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">RDP OMSET</p>
                    <p className="text-lg font-bold text-emerald-600">{formatNumber(businessData?.summary?.rdp_omset)}</p>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500 dark:text-slate-400">
                <div className="text-center">
                  <PieChart size={48} className="mx-auto mb-2 opacity-30" />
                  <p>No NDP/RDP data available</p>
                  <p className="text-sm mt-1">NDP (New Deposit) and RDP (Return Deposit) data will appear after OMSET records are added</p>
                </div>
              </div>
            )}
          </div>
        );

      case 'databaseUtilization':
        return businessData?.database_utilization?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Database size={20} className="text-indigo-600" />
              Database Utilization
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Database</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Product</th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700">Total</th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700">Assigned</th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700">Available</th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700">Utilization</th>
                  </tr>
                </thead>
                <tbody>
                  {businessData.database_utilization.slice(0, 10).map((db, idx) => (
                    <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4 text-sm text-slate-900">{db.database_name}</td>
                      <td className="py-3 px-4 text-sm text-slate-600">{db.product_name}</td>
                      <td className="py-3 px-4 text-sm text-slate-900 text-right">{db.total_records}</td>
                      <td className="py-3 px-4 text-sm text-blue-600 text-right">{db.assigned}</td>
                      <td className="py-3 px-4 text-sm text-emerald-600 text-right">{db.available}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-indigo-600 rounded-full"
                              style={{ width: `${db.utilization_rate}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium text-slate-700">{db.utilization_rate}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
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
            💡 Tip: Drag widgets by the grip handle to reorder them. Click "Save Layout" to persist changes.
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
