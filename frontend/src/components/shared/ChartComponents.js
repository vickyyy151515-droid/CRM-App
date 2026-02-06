import { ResponsiveContainer, LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

/**
 * Chart Card Component
 * Wrapper for Recharts with consistent styling
 * Used by AdvancedAnalytics, CustomerRetention, DailySummary
 */
export function ChartCard({
  title,
  subtitle,
  children,
  loading = false,
  className = '',
  headerAction,
  testId
}) {
  return (
    <div 
      className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
          {subtitle && (
            <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
        {headerAction}
      </div>
      
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        children
      )}
    </div>
  );
}

/**
 * Trend Line Chart
 * Simple line chart for trend visualization
 */
export function TrendLineChart({
  data,
  dataKey,
  xAxisKey = 'date',
  color = CHART_COLORS[0],
  height = 300,
  showGrid = true,
  showLegend = false,
  formatTooltip,
  formatXAxis,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
        <XAxis 
          dataKey={xAxisKey} 
          stroke="#94a3b8" 
          fontSize={12}
          tickFormatter={formatXAxis}
        />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1e293b', 
            border: 'none', 
            borderRadius: '8px',
            color: '#fff'
          }}
          formatter={formatTooltip}
        />
        {showLegend && <Legend />}
        <Line 
          type="monotone" 
          dataKey={dataKey} 
          stroke={color} 
          strokeWidth={2}
          dot={{ fill: color, strokeWidth: 2 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/**
 * Multi-Line Chart
 * For comparing multiple data series
 */
export function MultiLineChart({
  data,
  lines = [], // [{ dataKey: 'value', name: 'Label', color: '#6366f1' }]
  xAxisKey = 'date',
  height = 300,
  showGrid = true,
  showLegend = true,
  formatTooltip,
  formatXAxis,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
        <XAxis 
          dataKey={xAxisKey} 
          stroke="#94a3b8" 
          fontSize={12}
          tickFormatter={formatXAxis}
        />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1e293b', 
            border: 'none', 
            borderRadius: '8px',
            color: '#fff'
          }}
          formatter={formatTooltip}
        />
        {showLegend && <Legend />}
        {lines.map((line, idx) => (
          <Line 
            key={line.dataKey}
            type="monotone" 
            dataKey={line.dataKey}
            name={line.name || line.dataKey}
            stroke={line.color || CHART_COLORS[idx % CHART_COLORS.length]} 
            strokeWidth={2}
            dot={{ fill: line.color || CHART_COLORS[idx % CHART_COLORS.length], strokeWidth: 2 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/**
 * Simple Bar Chart
 */
export function SimpleBarChart({
  data,
  dataKey,
  xAxisKey = 'name',
  color = CHART_COLORS[0],
  height = 300,
  showGrid = true,
  formatTooltip,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
        <XAxis dataKey={xAxisKey} stroke="#94a3b8" fontSize={12} />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1e293b', 
            border: 'none', 
            borderRadius: '8px',
            color: '#fff'
          }}
          formatter={formatTooltip}
        />
        <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Area Chart for filled visualization
 */
export function SimpleAreaChart({
  data,
  dataKey,
  xAxisKey = 'date',
  color = CHART_COLORS[0],
  height = 300,
  showGrid = true,
  formatTooltip,
  formatXAxis,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
        <XAxis 
          dataKey={xAxisKey} 
          stroke="#94a3b8" 
          fontSize={12}
          tickFormatter={formatXAxis}
        />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1e293b', 
            border: 'none', 
            borderRadius: '8px',
            color: '#fff'
          }}
          formatter={formatTooltip}
        />
        <Area 
          type="monotone" 
          dataKey={dataKey} 
          stroke={color} 
          fill={`${color}20`}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export { CHART_COLORS };
export default ChartCard;
