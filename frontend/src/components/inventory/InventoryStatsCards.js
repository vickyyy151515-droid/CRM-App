import { Package, Users, CheckCircle } from 'lucide-react';

export default function InventoryStatsCards({ stats }) {
  const cards = [
    { label: 'Total Items', value: stats.total, icon: Package, color: 'indigo' },
    { label: 'Assigned', value: stats.assigned, icon: Users, color: 'amber' },
    { label: 'Available', value: stats.available, icon: CheckCircle, color: 'emerald' }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {cards.map(({ label, value, icon: Icon, color }) => (
        <div key={label} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg bg-${color}-100 dark:bg-${color}-900/50 flex items-center justify-center`}>
              <Icon className={`text-${color}-600 dark:text-${color}-400`} size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
