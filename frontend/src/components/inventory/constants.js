import { Laptop, Monitor, Smartphone, Armchair, Box } from 'lucide-react';

export const CATEGORIES = [
  { id: 'laptop', name: 'Laptop', icon: Laptop },
  { id: 'monitor', name: 'Monitor', icon: Monitor },
  { id: 'phone', name: 'Phone', icon: Smartphone },
  { id: 'furniture', name: 'Furniture', icon: Armchair },
  { id: 'other', name: 'Other', icon: Box }
];

export const CONDITIONS = [
  { id: 'good', name: 'Good', color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400' },
  { id: 'fair', name: 'Fair', color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400' },
  { id: 'poor', name: 'Poor', color: 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400' }
];

export const getCategoryIcon = (categoryId) => {
  const category = CATEGORIES.find(c => c.id === categoryId);
  return category ? category.icon : Box;
};

export const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('id-ID', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
};

export const formatPrice = (price) => {
  if (!price) return '-';
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(price);
};
