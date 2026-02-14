import { useState } from 'react';
import { Info } from 'lucide-react';

const CHART_DESCRIPTIONS = {
  staffNdpRdpDaily: {
    title: 'Staff NDP / RDP Daily',
    desc: "Tracks each staff member's daily New Deposit (NDP) and Re-Deposit (RDP) performance over time. Helps identify consistent performers vs those who need support, and spot daily trends or anomalies.",
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
    desc: "Measures the average time from a customer's first response to their first deposit. Shorter lifecycle = more efficient sales process. Helps benchmark staff speed and identify slow conversions.",
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

export function ChartInfoTooltip({ chartKey }) {
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
