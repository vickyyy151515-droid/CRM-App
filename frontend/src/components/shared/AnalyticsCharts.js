import { 
  ResponsiveContainer, 
  LineChart, Line, 
  BarChart, Bar, 
  AreaChart, Area,
  PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend 
} from 'recharts';

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

const tooltipStyle = {
  backgroundColor: '#1e293b',
  border: 'none',
  borderRadius: '8px',
  color: '#fff'
};

/**
 * Area Chart with Multiple Series
 * Used for trends visualization (e.g., daily activity trends)
 */
export function MultiAreaChart({
  data,
  areas = [], // [{ dataKey: 'value', name: 'Label', color: '#6366f1' }]
  xAxisKey = 'date',
  height = 300,
  showGrid = true,
  showLegend = true,
  formatTooltip,
  formatXAxis,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
        <XAxis 
          dataKey={xAxisKey} 
          tick={{ fontSize: 12 }} 
          tickFormatter={formatXAxis}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip 
          contentStyle={tooltipStyle}
          formatter={formatTooltip}
        />
        {showLegend && <Legend />}
        {areas.map((area, idx) => (
          <Area 
            key={area.dataKey}
            type="monotone" 
            dataKey={area.dataKey}
            name={area.name || area.dataKey}
            stroke={area.color || CHART_COLORS[idx % CHART_COLORS.length]}
            fill={area.color || CHART_COLORS[idx % CHART_COLORS.length]}
            fillOpacity={0.3}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

/**
 * Donut/Pie Chart
 * Used for distribution visualization (e.g., WhatsApp status)
 */
export function DonutChart({
  data, // [{ name: 'Label', value: 100, color: '#6366f1' }]
  height = 256,
  innerRadius = 60,
  outerRadius = 100,
  showLabel = true,
  labelFormat,
}) {
  const defaultLabelFormat = ({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPie>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          paddingAngle={5}
          dataKey="value"
          label={showLabel ? (labelFormat || defaultLabelFormat) : false}
        >
          {data.map((entry, idx) => (
            <Cell key={`cell-${idx}`} fill={entry.color || CHART_COLORS[idx % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
      </RechartsPie>
    </ResponsiveContainer>
  );
}

/**
 * Horizontal Bar Chart
 * Used for ranking/comparison (e.g., Response Rate by Staff)
 */
export function HorizontalBarChart({
  data,
  dataKey,
  categoryKey = 'name',
  color = CHART_COLORS[0],
  height = 256,
  showGrid = true,
  formatTooltip,
  maxValue,
  yAxisWidth = 80,
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical">
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
        <XAxis type="number" domain={maxValue ? [0, maxValue] : undefined} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey={categoryKey} tick={{ fontSize: 12 }} width={yAxisWidth} />
        <Tooltip 
          contentStyle={tooltipStyle}
          formatter={formatTooltip}
        />
        <Bar dataKey={dataKey} fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Dual Line Chart
 * Used for comparing two metrics over time
 */
export function DualLineChart({
  data,
  line1 = { dataKey: 'value1', name: 'Value 1', color: CHART_COLORS[0] },
  line2 = { dataKey: 'value2', name: 'Value 2', color: CHART_COLORS[1] },
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
          tick={{ fontSize: 12 }}
          tickFormatter={formatXAxis}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip 
          contentStyle={tooltipStyle}
          formatter={formatTooltip}
        />
        {showLegend && <Legend />}
        <Line 
          type="monotone" 
          dataKey={line1.dataKey}
          name={line1.name}
          stroke={line1.color}
          strokeWidth={2}
          dot={false}
        />
        <Line 
          type="monotone" 
          dataKey={line2.dataKey}
          name={line2.name}
          stroke={line2.color}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/**
 * Progress Bar Component
 * Used in tables for utilization visualization
 */
export function ProgressBar({
  value,
  max = 100,
  color = 'bg-indigo-600',
  bgColor = 'bg-slate-200',
  showLabel = true,
  width = 'w-24',
  height = 'h-2',
}) {
  const percentage = Math.min((value / max) * 100, 100);
  
  return (
    <div className="flex items-center gap-2">
      <div className={`${width} ${height} ${bgColor} rounded-full overflow-hidden`}>
        <div 
          className={`h-full ${color} rounded-full transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {percentage.toFixed(0)}%
        </span>
      )}
    </div>
  );
}

export { CHART_COLORS, tooltipStyle };
