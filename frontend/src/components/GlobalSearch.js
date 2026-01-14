import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../App';
import { Search, X, User, Users, Package, Database, FileText, DollarSign, Loader2 } from 'lucide-react';

export default function GlobalSearch({ onNavigate, isAdmin = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  // Keyboard shortcut to open search (Ctrl/Cmd + K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
        setQuery('');
        setResults(null);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      setSelectedIndex(-1);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await api.get(`/search?q=${encodeURIComponent(query)}`);
        setResults(response.data);
        setSelectedIndex(-1);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Get flat list of all results for keyboard navigation
  const getAllResults = useCallback(() => {
    if (!results) return [];
    const all = [];
    if (results.customers?.length) {
      results.customers.forEach(c => all.push({ ...c, type: 'customer' }));
    }
    if (results.staff?.length) {
      results.staff.forEach(s => all.push({ ...s, type: 'staff' }));
    }
    if (results.products?.length) {
      results.products.forEach(p => all.push({ ...p, type: 'product' }));
    }
    if (results.databases?.length) {
      results.databases.forEach(d => all.push({ ...d, type: 'database' }));
    }
    if (results.omset_records?.length) {
      results.omset_records.forEach(o => all.push({ ...o, type: 'omset' }));
    }
    return all;
  }, [results]);

  // Keyboard navigation
  const handleKeyDown = (e) => {
    const allResults = getAllResults();
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, allResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault();
      handleResultClick(allResults[selectedIndex]);
    }
  };

  const handleResultClick = (result) => {
    setIsOpen(false);
    setQuery('');
    setResults(null);
    
    // Navigate based on result type
    if (result.type === 'customer') {
      onNavigate?.('assigned', { customerId: result.id });
    } else if (result.type === 'staff') {
      onNavigate?.('manage-users', { staffId: result.id });
    } else if (result.type === 'product') {
      onNavigate?.('products', { productId: result.id });
    } else if (result.type === 'database') {
      onNavigate?.('databases', { databaseId: result.id });
    } else if (result.type === 'omset') {
      onNavigate?.('omset', { recordId: result.id });
    }
  };

  const getCategoryIcon = (type) => {
    switch (type) {
      case 'customer': return User;
      case 'staff': return Users;
      case 'product': return Package;
      case 'database': return Database;
      case 'omset': return DollarSign;
      default: return FileText;
    }
  };

  const getCategoryLabel = (type) => {
    switch (type) {
      case 'customer': return 'Customers';
      case 'staff': return 'Staff';
      case 'product': return 'Products';
      case 'database': return 'Databases';
      case 'omset': return 'OMSET Records';
      default: return 'Results';
    }
  };

  const hasResults = results && (
    results.customers?.length ||
    results.staff?.length ||
    results.products?.length ||
    results.databases?.length ||
    results.omset_records?.length
  );

  let currentIndex = -1;

  return (
    <div ref={containerRef} className="relative">
      {/* Search Trigger Button */}
      <button
        onClick={() => {
          setIsOpen(true);
          setTimeout(() => inputRef.current?.focus(), 100);
        }}
        className="flex items-center gap-2 px-3 py-2 text-sm text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
        data-testid="global-search-btn"
      >
        <Search size={16} />
        <span className="hidden md:inline">Search...</span>
        <kbd className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono bg-slate-200 dark:bg-slate-700 rounded">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      {/* Search Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-2xl mx-4 bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 border-b border-slate-200 dark:border-slate-700">
              <Search className="text-slate-400" size={20} />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search customers, staff, products, databases..."
                className="flex-1 py-4 text-lg bg-transparent outline-none text-slate-900 dark:text-slate-100 placeholder-slate-400"
                data-testid="global-search-input"
              />
              {loading && <Loader2 className="text-slate-400 animate-spin" size={20} />}
              {query && !loading && (
                <button
                  onClick={() => {
                    setQuery('');
                    setResults(null);
                  }}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
                >
                  <X size={18} className="text-slate-400" />
                </button>
              )}
              <button
                onClick={() => {
                  setIsOpen(false);
                  setQuery('');
                  setResults(null);
                }}
                className="px-2 py-1 text-xs font-medium text-slate-500 bg-slate-100 dark:bg-slate-800 rounded"
              >
                ESC
              </button>
            </div>

            {/* Results */}
            <div className="max-h-96 overflow-y-auto">
              {!query.trim() ? (
                <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                  <Search size={32} className="mx-auto mb-3 opacity-50" />
                  <p className="text-sm">Start typing to search across the entire CRM</p>
                  <p className="text-xs mt-2 text-slate-400">
                    Search for customers, staff members, products, databases, or OMSET records
                  </p>
                </div>
              ) : loading ? (
                <div className="p-8 text-center text-slate-500">
                  <Loader2 className="mx-auto mb-2 animate-spin" size={24} />
                  <p className="text-sm">Searching...</p>
                </div>
              ) : !hasResults ? (
                <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                  <p className="text-sm">No results found for "{query}"</p>
                  <p className="text-xs mt-2 text-slate-400">Try a different search term</p>
                </div>
              ) : (
                <div className="py-2">
                  {/* Customers */}
                  {results.customers?.length > 0 && (
                    <div>
                      <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider bg-slate-50 dark:bg-slate-800/50">
                        Customers ({results.customers.length})
                      </div>
                      {results.customers.map((customer) => {
                        currentIndex++;
                        const idx = currentIndex;
                        return (
                          <button
                            key={customer.id}
                            onClick={() => handleResultClick({ ...customer, type: 'customer' })}
                            className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors ${
                              selectedIndex === idx ? 'bg-indigo-50 dark:bg-indigo-900/30' : ''
                            }`}
                          >
                            <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                              <User size={16} className="text-blue-600 dark:text-blue-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 dark:text-slate-100 truncate">{customer.name}</p>
                              <p className="text-xs text-slate-500 truncate">{customer.product_name} • {customer.status}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Staff */}
                  {results.staff?.length > 0 && isAdmin && (
                    <div>
                      <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider bg-slate-50 dark:bg-slate-800/50">
                        Staff ({results.staff.length})
                      </div>
                      {results.staff.map((staff) => {
                        currentIndex++;
                        const idx = currentIndex;
                        return (
                          <button
                            key={staff.id}
                            onClick={() => handleResultClick({ ...staff, type: 'staff' })}
                            className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors ${
                              selectedIndex === idx ? 'bg-indigo-50 dark:bg-indigo-900/30' : ''
                            }`}
                          >
                            <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center">
                              <Users size={16} className="text-purple-600 dark:text-purple-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 dark:text-slate-100 truncate">{staff.name}</p>
                              <p className="text-xs text-slate-500 truncate">{staff.email} • {staff.role}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Products */}
                  {results.products?.length > 0 && (
                    <div>
                      <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider bg-slate-50 dark:bg-slate-800/50">
                        Products ({results.products.length})
                      </div>
                      {results.products.map((product) => {
                        currentIndex++;
                        const idx = currentIndex;
                        return (
                          <button
                            key={product.id}
                            onClick={() => handleResultClick({ ...product, type: 'product' })}
                            className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors ${
                              selectedIndex === idx ? 'bg-indigo-50 dark:bg-indigo-900/30' : ''
                            }`}
                          >
                            <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
                              <Package size={16} className="text-green-600 dark:text-green-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 dark:text-slate-100 truncate">{product.name}</p>
                              <p className="text-xs text-slate-500 truncate">{product.category || 'Product'}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Databases */}
                  {results.databases?.length > 0 && (
                    <div>
                      <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider bg-slate-50 dark:bg-slate-800/50">
                        Databases ({results.databases.length})
                      </div>
                      {results.databases.map((db) => {
                        currentIndex++;
                        const idx = currentIndex;
                        return (
                          <button
                            key={db.id}
                            onClick={() => handleResultClick({ ...db, type: 'database' })}
                            className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors ${
                              selectedIndex === idx ? 'bg-indigo-50 dark:bg-indigo-900/30' : ''
                            }`}
                          >
                            <div className="w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
                              <Database size={16} className="text-amber-600 dark:text-amber-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 dark:text-slate-100 truncate">{db.name}</p>
                              <p className="text-xs text-slate-500 truncate">{db.product_name} • {db.total_records} records</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* OMSET Records */}
                  {results.omset_records?.length > 0 && (
                    <div>
                      <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider bg-slate-50 dark:bg-slate-800/50">
                        OMSET Records ({results.omset_records.length})
                      </div>
                      {results.omset_records.map((record) => {
                        currentIndex++;
                        const idx = currentIndex;
                        return (
                          <button
                            key={record.id}
                            onClick={() => handleResultClick({ ...record, type: 'omset' })}
                            className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors ${
                              selectedIndex === idx ? 'bg-indigo-50 dark:bg-indigo-900/30' : ''
                            }`}
                          >
                            <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
                              <DollarSign size={16} className="text-emerald-600 dark:text-emerald-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 dark:text-slate-100 truncate">{record.customer_name}</p>
                              <p className="text-xs text-slate-500 truncate">
                                Rp {record.depo_total?.toLocaleString('id-ID')} • {record.record_date}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            {hasResults && (
              <div className="px-4 py-2 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-500 flex items-center justify-between">
                <span>
                  <kbd className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-700 rounded mr-1">↑↓</kbd> to navigate
                  <kbd className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-700 rounded mx-1">Enter</kbd> to select
                </span>
                <span>{results.total || 0} results found</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
