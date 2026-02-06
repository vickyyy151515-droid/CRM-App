import { Package, UserPlus, RefreshCw, TrendingUp } from 'lucide-react';

/**
 * Format currency with thousand separators
 */
const formatCurrency = (num) => {
  if (!num && num !== 0) return '0';
  return Math.round(num).toLocaleString('id-ID');
};

/**
 * Gradient color classes for product cards
 */
const GRADIENT_COLORS = [
  'from-indigo-500 to-indigo-600',
  'from-blue-500 to-blue-600',
  'from-purple-500 to-purple-600',
  'from-cyan-500 to-cyan-600',
  'from-teal-500 to-teal-600'
];

/**
 * Product Stats Card
 */
function ProductCard({ product, colorIndex }) {
  const colorClass = GRADIENT_COLORS[colorIndex % GRADIENT_COLORS.length];
  
  return (
    <div className={`bg-gradient-to-br ${colorClass} rounded-xl p-4 text-white shadow-lg`}>
      <div className="flex items-center justify-between mb-2">
        <Package className="opacity-80" size={20} />
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{product.count} rec</span>
      </div>
      <p className="text-white/80 text-xs font-medium mb-1">{product.product_name}</p>
      <p className="text-xl font-bold">Rp {formatCurrency(product.total_depo)}</p>
    </div>
  );
}

/**
 * NDP Card (New Deposits)
 */
function NDPCard({ count }) {
  return (
    <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 text-white shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <UserPlus className="opacity-80" size={20} />
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{count} NDP</span>
      </div>
      <p className="text-white/80 text-xs font-medium mb-1">Total NDP (New Depo)</p>
      <p className="text-xl font-bold">{count}</p>
    </div>
  );
}

/**
 * RDP Card (Repeat Deposits)
 */
function RDPCard({ count }) {
  return (
    <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-4 text-white shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <RefreshCw className="opacity-80" size={20} />
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{count} RDP</span>
      </div>
      <p className="text-white/80 text-xs font-medium mb-1">Total RDP (Redepo)</p>
      <p className="text-xl font-bold">{count}</p>
    </div>
  );
}

/**
 * Grand Total Card
 */
function GrandTotalCard({ totalRecords, totalDepo }) {
  return (
    <div className="bg-gradient-to-br from-slate-700 to-slate-800 rounded-xl p-4 text-white shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <TrendingUp className="opacity-80" size={20} />
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{totalRecords} total</span>
      </div>
      <p className="text-white/80 text-xs font-medium mb-1">GRAND TOTAL</p>
      <p className="text-xl font-bold">Rp {formatCurrency(totalDepo)}</p>
    </div>
  );
}

/**
 * OMSET Stats Grid Component
 * Displays product cards, NDP/RDP counts, and grand total
 * Used by AdminOmsetCRM
 */
export default function OmsetStatsGrid({ 
  summary,
  testIdPrefix = 'omset-stats'
}) {
  if (!summary) return null;

  const { by_product = [], total = {} } = summary;

  if (by_product.length === 0) {
    return (
      <div 
        className="bg-white border border-slate-200 rounded-xl p-6 text-center text-slate-500 mb-6"
        data-testid={`${testIdPrefix}-empty`}
      >
        No OMSET data for selected filters
      </div>
    );
  }

  return (
    <div 
      className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6"
      data-testid={`${testIdPrefix}-grid`}
    >
      {/* Product Cards */}
      {by_product.map((product, idx) => (
        <ProductCard 
          key={product.product_id} 
          product={product} 
          colorIndex={idx}
        />
      ))}
      
      {/* NDP Card */}
      <NDPCard count={total.total_ndp || 0} />
      
      {/* RDP Card */}
      <RDPCard count={total.total_rdp || 0} />
      
      {/* Grand Total Card */}
      <GrandTotalCard 
        totalRecords={total.total_records || 0} 
        totalDepo={total.total_depo || 0} 
      />
    </div>
  );
}

// Export individual components for flexibility
export { ProductCard, NDPCard, RDPCard, GrandTotalCard, formatCurrency, GRADIENT_COLORS };
