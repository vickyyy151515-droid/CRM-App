import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Users, UserPlus, RefreshCcw, Heart, TrendingUp, DollarSign, Calendar, Award, ChevronDown, ChevronUp, Star, Package, BarChart3 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area } from 'recharts';

export default function CustomerRetention({ isAdmin = false }) {
  const [overview, setOverview] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [trend, setTrend] = useState(null);
  const [productBreakdown, setProductBreakdown] = useState(null);
  const [staffBreakdown, setStaffBreakdown] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('overview');
  const [dateRange, setDateRange] = useState('90');
  const [customerFilter, setCustomerFilter] = useState('all');
  const [customerSort, setCustomerSort] = useState('deposits');
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [showTopCustomers, setShowTopCustomers] = useState(true);

  const loadOverview = useCallback(async () => {
    try {
      setLoading(true);
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - parseInt(dateRange) * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      let url = `/retention/overview?start_date=${startDate}&end_date=${endDate}`;
      if (selectedProduct) url += `&product_id=${selectedProduct}`;
      
      const response = await api.get(url);
      setOverview(response.data);
    } catch (error) {
      toast.error('Failed to load retention data');
    } finally {
      setLoading(false);
    }
  }, [dateRange, selectedProduct]);

  const loadCustomers = useCallback(async () => {
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - parseInt(dateRange) * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      let url = `/retention/customers?start_date=${startDate}&end_date=${endDate}&filter_type=${customerFilter}&sort_by=${customerSort}&limit=100`;
      if (selectedProduct) url += `&product_id=${selectedProduct}`;
      
      const response = await api.get(url);
      setCustomers(response.data.customers || []);
    } catch (error) {
      console.error('Failed to load customers');
    }
  }, [dateRange, selectedProduct, customerFilter, customerSort]);

  const loadTrend = useCallback(async () => {
    try {
      let url = `/retention/trend?days=${Math.min(parseInt(dateRange), 90)}`;
      if (selectedProduct) url += `&product_id=${selectedProduct}`;
      
      const response = await api.get(url);
      setTrend(response.data);
    } catch (error) {
      console.error('Failed to load trend');
    }
  }, [dateRange, selectedProduct]);

  const loadProductBreakdown = useCallback(async () => {
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - parseInt(dateRange) * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const response = await api.get(`/retention/by-product?start_date=${startDate}&end_date=${endDate}`);
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
      
      const response = await api.get(`/retention/by-staff?start_date=${startDate}&end_date=${endDate}`);
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
    loadOverview();
    loadTrend();
    loadProductBreakdown();
    if (isAdmin) loadStaffBreakdown();
  }, [loadOverview, loadTrend, loadProductBreakdown, loadStaffBreakdown, isAdmin]);

  useEffect(() => {
    if (activeView === 'customers') {
      loadCustomers();
    }
  }, [activeView, loadCustomers]);

  const formatCurrency = (amount) => {
    if (!amount) return 'Rp 0';
    if (amount >= 1000000000) return `Rp ${(amount / 1000000000).toFixed(2)}B`;
    if (amount >= 1000000) return `Rp ${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `Rp ${(amount / 1000).toFixed(0)}K`;
    return `Rp ${amount.toLocaleString('id-ID')}`;
  };

  const formatNumber = (num) => num?.toLocaleString('id-ID') || '0';

  const getRetentionColor = (rate) => {
    if (rate >= 50) return 'text-emerald-600';
    if (rate >= 30) return 'text-amber-600';
    return 'text-red-500';
  };

  const getRetentionBg = (rate) => {
    if (rate >= 50) return 'bg-emerald-50 border-emerald-200';
    if (rate >= 30) return 'bg-amber-50 border-amber-200';
    return 'bg-red-50 border-red-200';
  };

  const getLoyaltyBadge = (score) => {
    if (score >= 80) return { label: 'VIP', color: 'bg-purple-100 text-purple-700 border-purple-300' };
    if (score >= 50) return { label: 'Loyal', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' };
    if (score >= 30) return { label: 'Regular', color: 'bg-blue-100 text-blue-700 border-blue-300' };
    return { label: 'New', color: 'bg-slate-100 text-slate-600 border-slate-300' };
  };

  return (
    <div data-testid="customer-retention">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Customer Retention</h2>
          <p className="text-sm text-slate-500 mt-1">
            Track repeat depositors and customer loyalty metrics
          </p>
        </div>
        
        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="date-range-select"
          >
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="180">Last 6 months</option>
            <option value="365">Last year</option>
          </select>
          
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="product-filter-select"
          >
            <option value="">All Products</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          
          <button
            onClick={() => {
              loadOverview();
              loadTrend();
              loadProductBreakdown();
              if (isAdmin) loadStaffBreakdown();
              if (activeView === 'customers') loadCustomers();
            }}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
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
            activeView === 'overview' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
          }`}
          data-testid="overview-tab"
        >
          Overview
        </button>
        <button
          onClick={() => setActiveView('customers')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeView === 'customers' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
          }`}
          data-testid="customers-tab"
        >
          Customer List
        </button>
        <button
          onClick={() => setActiveView('by-product')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeView === 'by-product' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
          }`}
          data-testid="by-product-tab"
        >
          By Product
        </button>
        {isAdmin && (
          <button
            onClick={() => setActiveView('by-staff')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeView === 'by-staff' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
            }`}
            data-testid="by-staff-tab"
          >
            By Staff
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-600">Loading retention data...</div>
      ) : activeView === 'overview' && overview ? (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Users className="text-blue-600" size={20} />
                <span className="text-sm font-medium text-blue-700">Total Customers</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{formatNumber(overview.total_customers)}</p>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <UserPlus className="text-green-600" size={20} />
                <span className="text-sm font-medium text-green-700">New (NDP)</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{formatNumber(overview.ndp_customers)}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-violet-50 border border-purple-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <RefreshCcw className="text-purple-600" size={20} />
                <span className="text-sm font-medium text-purple-700">Returning (RDP)</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{formatNumber(overview.rdp_customers)}</p>
            </div>
            <div className={`rounded-xl p-5 border ${getRetentionBg(overview.retention_rate)}`}>
              <div className="flex items-center gap-2 mb-2">
                <Heart className={getRetentionColor(overview.retention_rate)} size={20} />
                <span className={`text-sm font-medium ${getRetentionColor(overview.retention_rate)}`}>Retention Rate</span>
              </div>
              <p className={`text-2xl font-bold ${getRetentionColor(overview.retention_rate)}`}>{overview.retention_rate}%</p>
            </div>
          </div>

          {/* Secondary Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <p className="text-sm text-slate-500 mb-1">Total Deposits</p>
              <p className="text-xl font-bold text-slate-900">{formatNumber(overview.total_deposits)}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <p className="text-sm text-slate-500 mb-1">Total OMSET</p>
              <p className="text-xl font-bold text-emerald-600">{formatCurrency(overview.total_omset)}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <p className="text-sm text-slate-500 mb-1">Avg Deposits/Customer</p>
              <p className="text-xl font-bold text-slate-900">{overview.avg_deposits_per_customer}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <p className="text-sm text-slate-500 mb-1">Avg OMSET/Customer</p>
              <p className="text-xl font-bold text-emerald-600">{formatCurrency(overview.avg_omset_per_customer)}</p>
            </div>
          </div>

          {/* Trend Chart */}
          {trend && trend.trend && trend.trend.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <BarChart3 className="text-indigo-600" size={20} />
                  <h3 className="font-semibold text-slate-900">Daily NDP vs RDP Trend</h3>
                </div>
                <div className="text-sm text-slate-500">
                  Avg: {trend.summary.avg_daily_ndp} NDP, {trend.summary.avg_daily_rdp} RDP/day
                </div>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={trend.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(date) => new Date(date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    labelFormatter={(date) => new Date(date).toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long' })}
                    formatter={(value, name) => [value, name === 'ndp' ? 'New (NDP)' : name === 'rdp' ? 'Returning (RDP)' : name]}
                  />
                  <Legend />
                  <Area type="monotone" dataKey="ndp" name="New (NDP)" stackId="1" stroke="#22c55e" fill="#bbf7d0" />
                  <Area type="monotone" dataKey="rdp" name="Returning (RDP)" stackId="1" stroke="#8b5cf6" fill="#ddd6fe" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Top Loyal Customers */}
          {overview.top_loyal_customers && overview.top_loyal_customers.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div 
                className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between cursor-pointer"
                onClick={() => setShowTopCustomers(!showTopCustomers)}
              >
                <div className="flex items-center gap-2">
                  <Award className="text-amber-500" size={20} />
                  <h3 className="font-semibold text-slate-900">Top Loyal Customers</h3>
                </div>
                {showTopCustomers ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </div>
              {showTopCustomers && (
                <div className="divide-y divide-slate-100">
                  {overview.top_loyal_customers.map((customer, index) => {
                    const badge = getLoyaltyBadge(customer.loyalty_score || 0);
                    return (
                      <div key={`${customer.customer_id}-${index}`} className="p-4 flex items-center justify-between hover:bg-slate-50">
                        <div className="flex items-center gap-4">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                            index === 0 ? 'bg-yellow-100 text-yellow-700' :
                            index === 1 ? 'bg-slate-200 text-slate-700' :
                            index === 2 ? 'bg-orange-100 text-orange-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {index + 1}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-semibold text-slate-900">{customer.customer_name}</p>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${badge.color}`}>
                                {badge.label}
                              </span>
                            </div>
                            <p className="text-sm text-slate-500">{customer.product_name}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-6 text-right">
                          <div>
                            <p className="font-bold text-indigo-600">{customer.total_deposits}</p>
                            <p className="text-xs text-slate-500">deposits</p>
                          </div>
                          <div>
                            <p className="font-bold text-emerald-600">{formatCurrency(customer.total_omset)}</p>
                            <p className="text-xs text-slate-500">total</p>
                          </div>
                          <div>
                            <p className="font-bold text-slate-700">{formatCurrency(customer.avg_deposit)}</p>
                            <p className="text-xs text-slate-500">avg</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      ) : activeView === 'customers' ? (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="text-indigo-600" size={20} />
              <h3 className="font-semibold text-slate-900">Customer List</h3>
              <span className="text-sm text-slate-500">({customers.length} shown)</span>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={customerFilter}
                onChange={(e) => setCustomerFilter(e.target.value)}
                className="px-2 py-1 text-sm border border-slate-200 rounded-lg"
              >
                <option value="all">All Customers</option>
                <option value="ndp">New (NDP)</option>
                <option value="rdp">Returning (RDP)</option>
                <option value="loyal">Loyal (3+ deposits)</option>
              </select>
              <select
                value={customerSort}
                onChange={(e) => setCustomerSort(e.target.value)}
                className="px-2 py-1 text-sm border border-slate-200 rounded-lg"
              >
                <option value="deposits">Sort by Deposits</option>
                <option value="omset">Sort by OMSET</option>
                <option value="recent">Sort by Recent</option>
              </select>
            </div>
          </div>
          
          {customers.length === 0 ? (
            <div className="p-8 text-center text-slate-500">No customers found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Customer</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Product</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Deposits</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Total OMSET</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Avg Deposit</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Last Deposit</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {customers.map((customer, index) => {
                    const badge = getLoyaltyBadge(customer.loyalty_score || 0);
                    return (
                      <tr key={`${customer.customer_id}-${index}`} className="hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-900">{customer.customer_name}</p>
                          <p className="text-xs text-slate-500">{customer.staff_name}</p>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">{customer.product_name}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="font-semibold text-indigo-600">{customer.total_deposits}</span>
                          <span className="text-xs text-slate-500 block">{customer.unique_days} days</span>
                        </td>
                        <td className="px-4 py-3 text-center font-semibold text-emerald-600">
                          {formatCurrency(customer.total_omset)}
                        </td>
                        <td className="px-4 py-3 text-center text-slate-700">
                          {formatCurrency(customer.avg_deposit)}
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-slate-600">
                          {customer.last_deposit ? new Date(customer.last_deposit).toLocaleDateString('id-ID') : '-'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full border ${badge.color}`}>
                            {badge.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : activeView === 'by-product' && productBreakdown ? (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <Package className="text-indigo-600" size={20} />
              <h3 className="font-semibold text-slate-900">Retention by Product</h3>
            </div>
          </div>
          
          {(productBreakdown.products || []).length === 0 ? (
            <div className="p-8 text-center text-slate-500">No product data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Product</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Total</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">NDP</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">RDP</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Retention</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Deposits</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">OMSET</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Avg/Customer</th>
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
                      <td className="px-4 py-3 text-center font-semibold text-slate-900">{product.total_customers}</td>
                      <td className="px-4 py-3 text-center text-green-600">{product.ndp_customers}</td>
                      <td className="px-4 py-3 text-center text-purple-600">{product.rdp_customers}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${getRetentionBg(product.retention_rate)} ${getRetentionColor(product.retention_rate)}`}>
                          {product.retention_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-slate-700">{product.total_deposits}</td>
                      <td className="px-4 py-3 text-center font-semibold text-emerald-600">{formatCurrency(product.total_omset)}</td>
                      <td className="px-4 py-3 text-center text-slate-600">{product.avg_deposits_per_customer}</td>
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
              <h3 className="font-semibold text-slate-900">Retention by Staff</h3>
            </div>
          </div>
          
          {(staffBreakdown.staff || []).length === 0 ? (
            <div className="p-8 text-center text-slate-500">No staff data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Staff</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Customers</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">NDP</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">RDP</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Loyal (3+)</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Retention</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Loyalty</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">OMSET</th>
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
                      <td className="px-4 py-3 text-center font-semibold text-slate-900">{staff.total_customers}</td>
                      <td className="px-4 py-3 text-center text-green-600">{staff.ndp_customers}</td>
                      <td className="px-4 py-3 text-center text-purple-600">{staff.rdp_customers}</td>
                      <td className="px-4 py-3 text-center text-amber-600">{staff.loyal_customers}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${getRetentionBg(staff.retention_rate)} ${getRetentionColor(staff.retention_rate)}`}>
                          {staff.retention_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          staff.loyalty_rate >= 20 ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {staff.loyalty_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center font-semibold text-emerald-600">{formatCurrency(staff.total_omset)}</td>
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
