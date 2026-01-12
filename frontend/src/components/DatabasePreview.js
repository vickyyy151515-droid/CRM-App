import { X } from 'lucide-react';

export default function DatabasePreview({ database, onClose }) {
  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="database-preview-modal">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h3 className="text-2xl font-semibold text-slate-900">{database.filename}</h3>
            {database.description && (
              <p className="text-sm text-slate-600 mt-1">{database.description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            data-testid="close-preview-button"
            className="text-slate-400 hover:text-slate-600 p-2"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 overflow-auto max-h-[calc(80vh-120px)]">
          {database.preview_data?.error ? (
            <div className="text-center py-8 text-rose-600">
              <p>Error loading preview: {database.preview_data.error}</p>
            </div>
          ) : database.preview_data?.columns && database.preview_data?.rows ? (
            <div>
              <p className="text-sm text-slate-600 mb-4">
                Showing first 5 rows of {database.preview_data.total_rows || 'many'} rows
              </p>
              <div className="overflow-x-auto">
                <table className="min-w-full border border-slate-200 rounded-lg" data-testid="preview-table">
                  <thead className="bg-slate-50">
                    <tr>
                      {database.preview_data.columns.map((col, idx) => (
                        <th
                          key={idx}
                          className="px-4 py-3 text-left text-xs font-semibold text-slate-700 border-b border-slate-200"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {database.preview_data.rows.map((row, rowIdx) => (
                      <tr key={rowIdx} className="border-b border-slate-100 hover:bg-slate-50">
                        {row.map((cell, cellIdx) => (
                          <td key={cellIdx} className="px-4 py-3 text-sm text-slate-900">
                            {cell !== null && cell !== undefined ? String(cell) : '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-600">
              <p>No preview available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}