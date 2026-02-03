import { Upload } from 'lucide-react';

/**
 * Database Upload Form Component
 * Form for uploading new databases with product selection
 */
export default function DatabaseUploadForm({
  uploadName,
  setUploadName,
  uploadProductId,
  setUploadProductId,
  selectedFile,
  setSelectedFile,
  uploading,
  onSubmit,
  products,
  testIdPrefix = 'upload'
}) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <Upload size={20} className="text-indigo-600" />
        Upload New Database
      </h3>
      <form onSubmit={onSubmit} className="flex flex-col md:flex-row gap-4">
        <input
          type="text"
          placeholder="Database name..."
          value={uploadName}
          onChange={(e) => setUploadName(e.target.value)}
          className="flex-1 h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid={`${testIdPrefix}-db-name`}
        />
        <select
          value={uploadProductId}
          onChange={(e) => setUploadProductId(e.target.value)}
          className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid={`${testIdPrefix}-product-select`}
        >
          <option value="">Select Product (Optional)</option>
          {products.map(product => (
            <option key={product.id} value={product.id}>{product.name}</option>
          ))}
        </select>
        <label className="h-10 px-4 bg-slate-100 dark:bg-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">
          <Upload size={16} />
          {selectedFile ? selectedFile.name : 'Choose File'}
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            className="hidden"
            data-testid={`${testIdPrefix}-file-input`}
          />
        </label>
        <button
          type="submit"
          disabled={uploading || !selectedFile || !uploadName}
          className="h-10 px-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors flex items-center gap-2"
          data-testid={`${testIdPrefix}-submit-btn`}
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  );
}
