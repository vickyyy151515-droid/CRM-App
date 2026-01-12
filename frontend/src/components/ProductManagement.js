import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Package, Trash2, Plus } from 'lucide-react';

export default function ProductManagement() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newProductName, setNewProductName] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newProductName.trim()) {
      toast.error('Please enter a product name');
      return;
    }

    setCreating(true);
    try {
      await api.post('/products', { name: newProductName.trim() });
      toast.success('Product created successfully!');
      setNewProductName('');
      loadProducts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create product');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;

    try {
      await api.delete(`/products/${id}`);
      toast.success('Product deleted successfully');
      loadProducts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete product');
    }
  };

  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Manage Products</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Plus className="text-indigo-600" size={20} />
            Add New Product
          </h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label htmlFor="productName" className="block text-sm font-medium text-slate-700 mb-2">
                Product Name
              </label>
              <input
                id="productName"
                type="text"
                value={newProductName}
                onChange={(e) => setNewProductName(e.target.value)}
                placeholder="Enter product name (e.g., LIGA2000)"
                data-testid="new-product-name-input"
                className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              />
            </div>
            <button
              type="submit"
              disabled={creating || !newProductName.trim()}
              data-testid="create-product-button"
              className="w-full bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2.5 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Plus size={18} />
              {creating ? 'Creating...' : 'Create Product'}
            </button>
          </form>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Package className="text-indigo-600" size={20} />
            Existing Products ({products.length})
          </h3>

          {loading ? (
            <div className="text-center py-8 text-slate-600">Loading products...</div>
          ) : products.length === 0 ? (
            <div className="text-center py-8 text-slate-600">No products yet</div>
          ) : (
            <div className="space-y-3" data-testid="products-list">
              {products.map((product) => (
                <div
                  key={product.id}
                  className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                  data-testid={`product-item-${product.id}`}
                >
                  <div className="flex items-center gap-3">
                    <Package className="text-indigo-600" size={18} />
                    <span className="font-medium text-slate-900">{product.name}</span>
                  </div>
                  <button
                    onClick={() => handleDelete(product.id, product.name)}
                    data-testid={`delete-product-${product.id}`}
                    className="text-rose-600 hover:bg-rose-50 p-2 rounded-md transition-colors"
                    title="Delete product"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          <strong>Note:</strong> You cannot delete a product if it has associated databases. 
          Delete all databases for that product first.
        </p>
      </div>
    </div>
  );
}
