import { useState } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Upload, File, X } from 'lucide-react';

export default function UploadDatabase({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [productId, setProductId] = useState('');
  const [products, setProducts] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  useState(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
      if (response.data.length > 0) {
        setProductId(response.data[0].id);
      }
    } catch (error) {
      toast.error('Failed to load products');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.xlsx')) {
        setFile(droppedFile);
      } else {
        toast.error('Only CSV and Excel files are allowed');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      toast.error('Please select a file');
      return;
    }
    if (!productId) {
      toast.error('Please select a product');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('product_id', productId);
    if (description) {
      formData.append('description', description);
    }

    try {
      await api.post('/databases', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Database uploaded successfully!');
      setFile(null);
      setDescription('');
      onUploadSuccess?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-6">Upload Database</h2>

      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="product" className="block text-sm font-medium text-slate-700 mb-2">
              Select Product *
            </label>
            <select
              id="product"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              required
              data-testid="select-product-upload"
              className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
            >
              <option value="">Choose a product...</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </div>

          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            data-testid="file-upload-dropzone"
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
              dragActive
                ? 'border-indigo-600 bg-indigo-50'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            {!file ? (
              <>
                <Upload className="mx-auto text-slate-400 mb-4" size={48} />
                <p className="text-base text-slate-700 mb-2">Drag & drop your database file here</p>
                <p className="text-sm text-slate-500 mb-4">or</p>
                <label className="inline-block">
                  <input
                    type="file"
                    accept=".csv,.xlsx"
                    onChange={handleFileChange}
                    className="hidden"
                    data-testid="file-upload-input"
                  />
                  <span className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2.5 rounded-md transition-all cursor-pointer inline-block">
                    Browse Files
                  </span>
                </label>
                <p className="text-xs text-slate-500 mt-4">Supported formats: CSV, Excel (.xlsx)</p>
              </>
            ) : (
              <div className="flex items-center justify-center gap-4">
                <File className="text-indigo-600" size={32} />
                <div className="text-left flex-1">
                  <p className="text-sm font-medium text-slate-900" data-testid="selected-filename">{file.name}</p>
                  <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  data-testid="remove-file-button"
                  className="text-slate-400 hover:text-slate-600 p-2"
                >
                  <X size={20} />
                </button>
              </div>
            )}
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-2">
              Description (Optional)
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              data-testid="database-description-input"
              className="flex w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              placeholder="Add a description for this database..."
            />
          </div>

          <button
            type="submit"
            disabled={uploading || !file}
            data-testid="upload-database-button"
            className="w-full bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2.5 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : 'Upload Database'}
          </button>
        </form>
      </div>
    </div>
  );
}