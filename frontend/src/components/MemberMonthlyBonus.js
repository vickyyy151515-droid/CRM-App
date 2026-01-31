import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Award, Users, TrendingUp, Calendar, ChevronDown, ChevronUp, Download, RefreshCw, DollarSign, Package } from 'lucide-react';

export default function MemberMonthlyBonus() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [expandedStaff, setExpandedStaff] = useState({});
  const [expandedProducts, setExpandedProducts] = useState({});

  useEffect(() => {
    loadData();
  }, [selectedMonth, selectedYear]);

  const loadData = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/member-monthly-bonus?month=${selectedMonth}&year=${selectedYear}`);
      setData(response.data);
      // Auto-expand all staff
      const expanded = {};
      response.data.data?.forEach(staff => {
        expanded[staff.staff_id] = true;
      });
      setExpandedStaff(expanded);
    } catch (error) {
      toast.error('Failed to load member bonus data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await api.get(`/member-monthly-bonus/export?month=${selectedMonth}&year=${selectedYear}`);
      const exportData = response.data.data;
      
      // Create CSV content
      const headers = ['Staff', 'Product', 'Customer ID', 'Customer Name', 'Total Omset', 'Transaction Count'];
      const rows = exportData.map(row => [
        row.staff_name,
        row.product_name,
        row.customer_id,
        row.customer_name,
        row.total_omset,
        row.transaction_count
      ]);
      
      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n');
      
      // Download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `member_bonus_${selectedYear}_${selectedMonth}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      
      toast.success('Data exported successfully');
    } catch (error) {
      toast.error('Failed to export data');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const toggleStaff = (staffId) => {
    setExpandedStaff(prev => ({
      ...prev,
      [staffId]: !prev[staffId]
    }));
  };

  const toggleProduct = (staffId, productId) => {
    const key = `${staffId}-${productId}`;
    setExpandedProducts(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const months = [
    { value: 1, label: 'Januari' },
    { value: 2, label: 'Februari' },
    { value: 3, label: 'Maret' },
    { value: 4, label: 'April' },
    { value: 5, label: 'Mei' },
    { value: 6, label: 'Juni' },
    { value: 7, label: 'Juli' },
    { value: 8, label: 'Agustus' },
    { value: 9, label: 'September' },
    { value: 10, label: 'Oktober' },
    { value: 11, label: 'November' },
    { value: 12, label: 'Desember' }
  ];

  const years = [];
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 3; y--) {
    years.push(y);
  }

  return (
    <div data-testid="member-monthly-bonus-page">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Member Monthly Bonus
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Customers with total omset {formatCurrency(10000000)}+ in a month
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
            data-testid="month-select"
          >
            {months.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
            data-testid="year-select"
          >
            {years.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          
          <button
            onClick={loadData}
            className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={18} className={`text-slate-600 dark:text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={handleExport}
            className="h-10 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2 text-sm font-medium transition-colors"
            data-testid="export-btn"
          >
            <Download size={18} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/30 dark:to-orange-900/30 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
                <Award className="text-amber-600 dark:text-amber-400" size={24} />
              </div>
              <div>
                <p className="text-sm text-amber-700 dark:text-amber-300 font-medium">Total Qualifying Members</p>
                <p className="text-2xl font-bold text-amber-900 dark:text-amber-100">
                  {data.summary.total_qualifying_customers}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
                <DollarSign className="text-emerald-600 dark:text-emerald-400" size={24} />
              </div>
              <div>
                <p className="text-sm text-emerald-700 dark:text-emerald-300 font-medium">Total Qualifying Omset</p>
                <p className="text-2xl font-bold text-emerald-900 dark:text-emerald-100">
                  {formatCurrency(data.summary.total_qualifying_omset)}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 border border-indigo-200 dark:border-indigo-800 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                <Users className="text-indigo-600 dark:text-indigo-400" size={24} />
              </div>
              <div>
                <p className="text-sm text-indigo-700 dark:text-indigo-300 font-medium">Staff with Bonus Members</p>
                <p className="text-2xl font-bold text-indigo-900 dark:text-indigo-100">
                  {data.summary.total_staff_with_bonus_members}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Staff and Product Data */}
      {loading ? (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <RefreshCw size={32} className="mx-auto text-slate-400 animate-spin mb-4" />
          <p className="text-slate-500 dark:text-slate-400">Loading data...</p>
        </div>
      ) : !data || data.data.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <Award size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <h3 className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-2">
            Tidak ada member yang memenuhi syarat
          </h3>
          <p className="text-sm text-slate-400 dark:text-slate-500">
            Tidak ada customer dengan total omset {formatCurrency(10000000)}+ di bulan {data?.month_name} {data?.year}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.data.map((staff) => (
            <div
              key={staff.staff_id}
              className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm"
              data-testid={`staff-section-${staff.staff_id}`}
            >
              {/* Staff Header */}
              <button
                onClick={() => toggleStaff(staff.staff_id)}
                className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                    {staff.staff_name?.charAt(0).toUpperCase() || '?'}
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold text-slate-900 dark:text-white text-lg">
                      {staff.staff_name}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                      <span className="flex items-center gap-1">
                        <Users size={14} />
                        {staff.total_customers} members
                      </span>
                      <span className="flex items-center gap-1">
                        <TrendingUp size={14} />
                        {formatCurrency(staff.total_omset)}
                      </span>
                    </div>
                  </div>
                </div>
                {expandedStaff[staff.staff_id] ? (
                  <ChevronUp className="text-slate-400" />
                ) : (
                  <ChevronDown className="text-slate-400" />
                )}
              </button>

              {/* Products */}
              {expandedStaff[staff.staff_id] && (
                <div className="border-t border-slate-200 dark:border-slate-700">
                  {staff.products.map((product) => {
                    const productKey = `${staff.staff_id}-${product.product_id}`;
                    const isProductExpanded = expandedProducts[productKey] !== false; // Default expanded
                    
                    return (
                      <div key={product.product_id} className="border-b border-slate-100 dark:border-slate-700 last:border-b-0">
                        {/* Product Header */}
                        <button
                          onClick={() => toggleProduct(staff.staff_id, product.product_id)}
                          className="w-full px-4 py-3 flex items-center justify-between bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <Package size={18} className="text-slate-400" />
                            <span className="font-medium text-slate-700 dark:text-slate-300">
                              {product.product_name}
                            </span>
                            <span className="px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 text-xs rounded-full">
                              {product.total_customers} members
                            </span>
                            <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                              {formatCurrency(product.total_omset)}
                            </span>
                          </div>
                          {isProductExpanded ? (
                            <ChevronUp size={18} className="text-slate-400" />
                          ) : (
                            <ChevronDown size={18} className="text-slate-400" />
                          )}
                        </button>

                        {/* Customer List */}
                        {isProductExpanded && (
                          <div className="divide-y divide-slate-100 dark:divide-slate-700">
                            {product.customers.map((customer, idx) => (
                              <div
                                key={`${customer.customer_id}-${idx}`}
                                className="px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/30"
                              >
                                <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
                                    <Award size={16} className="text-amber-600 dark:text-amber-400" />
                                  </div>
                                  <div>
                                    <p className="font-medium text-slate-900 dark:text-white">
                                      {customer.customer_name || customer.customer_id}
                                    </p>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">
                                      ID: {customer.customer_id} | {customer.transaction_count} transaksi
                                    </p>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <p className="font-bold text-emerald-600 dark:text-emerald-400">
                                    {formatCurrency(customer.total_omset)}
                                  </p>
                                  <p className="text-xs text-slate-400 dark:text-slate-500">
                                    {customer.first_transaction} - {customer.last_transaction}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
