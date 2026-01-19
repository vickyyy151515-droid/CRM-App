import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Filter, TrendingDown, TrendingUp, Users, MessageCircle, UserCheck, DollarSign, BarChart3, ChevronDown, ChevronUp, RefreshCcw, Package, Copy, Check } from 'lucide-react';

export default function ConversionFunnel({ isAdmin = false }) {
  const [funnelData, setFunnelData] = useState(null);
  const [productBreakdown, setProductBreakdown] = useState(null);
  const [staffBreakdown, setStaffBreakdown] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('overview');
  const [dateRange, setDateRange] = useState('30');
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [showDeposited, setShowDeposited] = useState(false);
  const [expandedProduct, setExpandedProduct] = useState(null);
  const [expandedStaff, setExpandedStaff] = useState(null);
  const [copiedUsername, setCopiedUsername] = useState(null);

  const loadFunnelData = useCallback(async () => {
    try {
      setLoading(true);
      
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - parseInt(dateRange) * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      let url = `/funnel?start_date=${startDate}&end_date=${endDate}`;
      if (selectedProduct) {
        url += `&product_id=${selectedProduct}`;
      }
      
      const response = await api.get(url);
      setFunnelData(response.data);
    } catch (error) {
      toast.error('Failed to load funnel data');
    } finally {
      setLoading(false);
    }
  }, [dateRange, selectedProduct]);

  const loadProductBreakdown = useCallback(async () => {
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - parseInt(dateRange) * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const response = await api.get(`/funnel/by-product?start_date=${startDate}&end_date=${endDate}`);
      setProductBreakdown(response.data);
    } catch (error) {
      console.error('Failed to load product breakdown');
    }
  }, [dateRange]);

  const loadStaffBreakdown = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - parseInt(dateRange) * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const response = await api.get(`/funnel/by-staff?start_date=${startDate}&end_date=${endDate}`);
      setStaffBreakdown(response.data);
    } catch (error) {
      console.error('Failed to load staff breakdown');
    }
  }, [dateRange, isAdmin]);

  const loadProducts = useCallback(async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data || []);
    } catch (error) {
      console.error('Failed to load products');
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  useEffect(() => {
    loadFunnelData();
    loadProductBreakdown();
    if (isAdmin) {
      loadStaffBreakdown();
    }
  }, [loadFunnelData, loadProductBreakdown, loadStaffBreakdown, isAdmin]);

  const formatNumber = (num) => {
    if (!num) return '0';
    return num.toLocaleString('id-ID');
  };

  const getConversionColor = (rate) => {
    if (rate >= 50) return 'text-emerald-600';
    if (rate >= 30) return 'text-amber-600';
    return 'text-red-500';
  };

  const getConversionBg = (rate) => {
    if (rate >= 50) return 'bg-emerald-50 border-emerald-200';
    if (rate >= 30) return 'bg-amber-50 border-amber-200';
    return 'bg-red-50 border-red-200';
  };

  const stageIcons = {
    'Assigned': Users,
    'WhatsApp Reached': MessageCircle,
    'Responded': UserCheck,
    'Deposited': DollarSign
  };

  const stageColors = {
    'Assigned': 'from-indigo-500 to-indigo-600',
    'WhatsApp Reached': 'from-green-500 to-emerald-600',
    'Responded': 'from-amber-500 to-orange-600',
    'Deposited': 'from-emerald-500 to-teal-600'
  };

  const copyUsername = async (username) => {
    try {
      await navigator.clipboard.writeText(username);
      setCopiedUsername(username);
      setTimeout(() => setCopiedUsername(null), 2000);
      toast.success(`Copied: ${username}`);
    } catch (err) {
      toast.error('Failed to copy');
    }
  };

  // Get deposited customers from the funnel data
  const getDepositedCustomers = () => {
    if (!funnelData || !funnelData.stages) return [];
    const depositedStage = funnelData.stages.find(s => s.name === 'Deposited');
    return depositedStage?.customers || [];
  };

  return (
    <div data-testid="conversion-funnel">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Conversion Funnel</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Track customer journey from assignment to deposit
          </p>
        </div>
        
        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="date-range-select"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
          
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="product-filter-select"
          >
            <option value="">All Products</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          
          <button
            onClick={() => {
              loadFunnelData();
              loadProductBreakdown();
              if (isAdmin) loadStaffBreakdown();
            }}
            className="p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            data-testid="refresh-btn"
          >
            <RefreshCcw size={20} />
          </button>
        </div>
      </div>

      {/* View Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveView('overview')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeView === 'overview'
              ? 'bg-indigo-100 text-indigo-700'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
          data-testid="overview-tab"
        >
          Overview
        </button>
        <button
          onClick={() => setActiveView('by-product')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeView === 'by-product'
              ? 'bg-indigo-100 text-indigo-700'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
          data-testid="by-product-tab"
        >
          By Product
        </button>
        {isAdmin && (
          <button
            onClick={() => setActiveView('by-staff')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeView === 'by-staff'
                ? 'bg-indigo-100 text-indigo-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            data-testid="by-staff-tab"
          >
            By Staff
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading funnel data...</div>
      ) : activeView === 'overview' && funnelData ? (
        <div>
          {/* Main Funnel Visualization */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
            <div className="flex items-center gap-2 mb-6">
              <BarChart3 className="text-indigo-600" size={24} />
              <h3 className="text-lg font-semibold text-slate-900">Sales Funnel</h3>
            </div>
            
            {/* Funnel Stages */}
            <div className="space-y-3">
              {funnelData.stages.map((stage, index) => {
                const Icon = stageIcons[stage.name] || Users;
                const widthPercent = Math.max(20, stage.rate);
                const prevStage = index > 0 ? funnelData.stages[index - 1] : null;
                const dropRate = prevStage ? prevStage.count - stage.count : 0;
                
                return (
                  <div key={stage.name} className="relative">
                    <div 
                      className={`relative bg-gradient-to-r ${stageColors[stage.name]} rounded-xl p-4 transition-all duration-500`}
                      style={{ width: `${widthPercent}%`, minWidth: '200px' }}
                    >
                      <div className="flex items-center justify-between text-white">
                        <div className="flex items-center gap-3">
                          <Icon size={24} />
                          <div>
                            <p className="font-semibold">{stage.name}</p>
                            <p className="text-sm opacity-90">{formatNumber(stage.count)} records</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold">{stage.rate}%</p>
                          {index > 0 && (
                            <p className="text-xs opacity-75">from prev stage</p>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Drop indicator */}
                    {index > 0 && dropRate > 0 && (
                      <div className="absolute -top-1 right-0 transform translate-x-full ml-4 flex items-center gap-1 text-xs text-red-500">
                        <TrendingDown size={14} />
                        <span>-{formatNumber(dropRate)}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            
            {/* Overall Conversion */}
            <div className={`mt-6 p-4 rounded-xl border ${getConversionBg(funnelData.overall_conversion)}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className={getConversionColor(funnelData.overall_conversion)} size={20} />
                  <span className="font-medium text-slate-700">Overall Conversion Rate</span>
                </div>
                <span className={`text-2xl font-bold ${getConversionColor(funnelData.overall_conversion)}`}>
                  {funnelData.overall_conversion}%
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                From {formatNumber(funnelData.stages[0]?.count || 0)} assigned to {formatNumber(funnelData.stages[3]?.count || 0)} deposited
              </p>
            </div>
          </div>

          {/* Stage Details Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {funnelData.stages.map((stage, index) => {
              const Icon = stageIcons[stage.name] || Users;
              const prevStage = index > 0 ? funnelData.stages[index - 1] : null;
              
              return (
                <div key={stage.name} className="bg-white border border-slate-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-r ${stageColors[stage.name]} flex items-center justify-center`}>
                      <Icon className="text-white" size={20} />
                    </div>
                    <span className="text-sm font-medium text-slate-700">{stage.name}</span>
                  </div>
                  <p className="text-2xl font-bold text-slate-900">{formatNumber(stage.count)}</p>
                  {prevStage && (
                    <p className="text-sm text-slate-500 mt-1">
                      {stage.rate}% from {prevStage.name.toLowerCase()}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : activeView === 'by-product' && productBreakdown ? (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <Package className="text-indigo-600" size={20} />
              <h3 className="font-semibold text-slate-900">Funnel by Product</h3>
            </div>
          </div>
          
          {(productBreakdown.products || []).length === 0 ? (
            <div className="p-8 text-center text-slate-500">No product data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Product</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Assigned</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">WA Reached</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Responded</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Deposited</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Overall Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {productBreakdown.products.map((product, index) => (
                    <tr key={product.product_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === 0 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {index + 1}
                          </div>
                          <span className="font-medium text-slate-900">{product.product_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-semibold text-indigo-600">{formatNumber(product.stages.assigned)}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div>
                          <span className="font-semibold text-green-600">{formatNumber(product.stages.wa_reached)}</span>
                          <span className="text-xs text-slate-500 block">{product.conversion_rates.assigned_to_wa}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div>
                          <span className="font-semibold text-amber-600">{formatNumber(product.stages.responded)}</span>
                          <span className="text-xs text-slate-500 block">{product.conversion_rates.wa_to_responded}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div>
                          <span className="font-semibold text-emerald-600">{formatNumber(product.stages.deposited)}</span>
                          <span className="text-xs text-slate-500 block">{product.conversion_rates.responded_to_deposited}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${getConversionBg(product.conversion_rates.overall)} ${getConversionColor(product.conversion_rates.overall)}`}>
                          {product.conversion_rates.overall}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : activeView === 'by-staff' && staffBreakdown ? (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <Users className="text-indigo-600" size={20} />
              <h3 className="font-semibold text-slate-900">Funnel by Staff</h3>
            </div>
          </div>
          
          {(staffBreakdown.staff || []).length === 0 ? (
            <div className="p-8 text-center text-slate-500">No staff data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Staff</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Assigned</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">WA Reached</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Responded</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Deposited</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Overall Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {staffBreakdown.staff.map((staff, index) => (
                    <tr key={staff.staff_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === 0 ? 'bg-yellow-100 text-yellow-700' :
                            index === 1 ? 'bg-slate-200 text-slate-700' :
                            index === 2 ? 'bg-orange-100 text-orange-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {index + 1}
                          </div>
                          <span className="font-medium text-slate-900">{staff.staff_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-semibold text-indigo-600">{formatNumber(staff.stages.assigned)}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div>
                          <span className="font-semibold text-green-600">{formatNumber(staff.stages.wa_reached)}</span>
                          <span className="text-xs text-slate-500 block">{staff.conversion_rates.assigned_to_wa}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div>
                          <span className="font-semibold text-amber-600">{formatNumber(staff.stages.responded)}</span>
                          <span className="text-xs text-slate-500 block">{staff.conversion_rates.wa_to_responded}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div>
                          <span className="font-semibold text-emerald-600">{formatNumber(staff.stages.deposited)}</span>
                          <span className="text-xs text-slate-500 block">{staff.conversion_rates.responded_to_deposited}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${getConversionBg(staff.conversion_rates.overall)} ${getConversionColor(staff.conversion_rates.overall)}`}>
                          {staff.conversion_rates.overall}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12 text-slate-600">No data available</div>
      )}
    </div>
  );
}
