import { Package, TrendingUp, PieChart, Database, BarChart3, Users } from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart
} from 'recharts';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

const formatNumber = (num) => {
  if (!num) return '0';
  if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
};

/**
 * Empty State Component for Widgets
 */
function EmptyWidgetState({ icon: Icon, message, subMessage }) {
  return (
    <div className="h-64 sm:h-80 flex items-center justify-center text-slate-500 dark:text-slate-400">
      <div className="text-center">
        {Icon && <Icon size={48} className="mx-auto mb-2 opacity-30" />}
        <p>{message}</p>
        {subMessage && <p className="text-sm mt-1">{subMessage}</p>}
      </div>
    </div>
  );
}

/**
 * OMSET Trends Widget
 */
export function OmsetTrendsWidget({ data }) {
  const hasData = data?.omset_chart?.length > 0;
  
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <TrendingUp size={20} className="text-purple-600" />
        OMSET Trends
      </h3>
      {hasData ? (
        <div className="h-64 sm:h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.omset_chart}>
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
      ) : (
        <EmptyWidgetState 
          icon={TrendingUp}
          message="No OMSET trends data available"
          subMessage="OMSET trends will appear after daily records are added"
        />
      )}
    </div>
  );
}

/**
 * Product OMSET Widget
 */
export function ProductOmsetWidget({ data }) {
  const hasData = data?.product_omset?.some(p => p.total_omset > 0);
  const chartData = hasData ? data.product_omset.filter(p => p.total_omset > 0).slice(0, 6) : [];
  
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <Package size={20} className="text-purple-600" />
        OMSET by Product
      </h3>
      {hasData ? (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="product_name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value) => formatNumber(value)} />
              <Bar dataKey="total_omset" name="Total OMSET" fill="#8b5cf6">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyWidgetState 
          icon={Package}
          message="No OMSET data available for this period"
          subMessage='Add OMSET records from the "OMSET CRM" page'
        />
      )}
    </div>
  );
}

/**
 * NDP vs RDP Widget
 */
export function NdpRdpWidget({ data }) {
  const ndpCount = data?.summary?.ndp_count || 0;
  const rdpCount = data?.summary?.rdp_count || 0;
  const hasData = ndpCount + rdpCount > 0;
  
  const pieData = [
    { name: 'NDP (New)', value: ndpCount },
    { name: 'RDP (Return)', value: rdpCount }
  ];
  
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <PieChart size={20} className="text-purple-600" />
        NDP vs RDP Analysis
      </h3>
      {hasData ? (
        <>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPie>
                <Pie
                  data={pieData}
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
              <p className="text-lg font-bold text-indigo-600">{formatNumber(data?.summary?.ndp_omset)}</p>
            </div>
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">RDP OMSET</p>
              <p className="text-lg font-bold text-emerald-600">{formatNumber(data?.summary?.rdp_omset)}</p>
            </div>
          </div>
        </>
      ) : (
        <EmptyWidgetState 
          icon={PieChart}
          message="No NDP/RDP data available"
          subMessage="NDP (New Deposit) and RDP (Return Deposit) data will appear after OMSET records are added"
        />
      )}
    </div>
  );
}

/**
 * Database Utilization Widget
 */
export function DatabaseUtilizationWidget({ data }) {
  if (!data?.database_utilization?.length) return null;
  
  return (
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
            {data.database_utilization.slice(0, 10).map((db, idx) => (
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
}

/**
 * Daily Activity Trends Widget
 */
export function DailyTrendsWidget({ data }) {
  if (!data?.daily_trends?.length) return null;
  
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
        <TrendingUp size={20} className="text-indigo-600" />
        Daily Activity Trends
      </h3>
      <div className="h-64 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.daily_trends}>
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
}

/**
 * WhatsApp Distribution Widget
 */
export function WhatsappDistributionWidget({ data }) {
  const pieData = [
    { name: 'Ada', value: data?.summary?.whatsapp_ada || 0 },
    { name: 'Tidak', value: data?.summary?.whatsapp_tidak || 0 },
    { name: 'Ceklis1', value: data?.summary?.whatsapp_ceklis1 || 0 }
  ];
  
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
              data={pieData}
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
}

/**
 * Response Rate by Staff Widget
 */
export function ResponseRateWidget({ data }) {
  if (!data?.staff_metrics?.length) return null;
  
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
        <BarChart3 size={20} className="text-indigo-600" />
        Response Rate by Staff
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.staff_metrics.slice(0, 8)} layout="vertical">
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
}

export { COLORS, formatNumber, EmptyWidgetState };
