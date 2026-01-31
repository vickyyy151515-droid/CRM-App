import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { CreditCard, Calendar, Package, CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp, Users, RefreshCw, Edit2, Check, X } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function StaffMemberWDCRM() {
  const { t } = useLanguage();
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedBatches, setExpandedBatches] = useState({});
  const [selectedRecords, setSelectedRecords] = useState([]);
  const [showInvalidModal, setShowInvalidModal] = useState(false);
  const [invalidReason, setInvalidReason] = useState('');
  const [processing, setProcessing] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState(null);
  // Rename state
  const [editingBatchId, setEditingBatchId] = useState(null);
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    loadBatches();
  }, []);

  const loadBatches = async () => {
    setLoading(true);
    try {
      const response = await api.get('/memberwd/staff/batches');
      setBatches(response.data);
      // Auto-expand first batch if exists
      if (response.data.length > 0) {
        setExpandedBatches({ [response.data[0].id]: true });
      }
    } catch (error) {
      toast.error('Gagal memuat data batch');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Start editing batch name
  const startEditingBatch = (batch, e) => {
    e.stopPropagation();
    setEditingBatchId(batch.id);
    setEditingName(batch.custom_name || batch.database_name);
  };

  // Save batch name
  const saveBatchName = async (batchId, e) => {
    e.stopPropagation();
    if (!editingName.trim()) {
      toast.error('Nama batch tidak boleh kosong');
      return;
    }
    
    try {
      await api.patch(`/memberwd/staff/batches/${batchId}/rename`, {
        custom_name: editingName.trim()
      });
      toast.success('Nama batch berhasil diubah');
      // Update local state
      setBatches(prev => prev.map(b => 
        b.id === batchId ? { ...b, custom_name: editingName.trim() } : b
      ));
      setEditingBatchId(null);
      setEditingName('');
    } catch (error) {
      toast.error('Gagal mengubah nama batch');
    }
  };

  // Cancel editing
  const cancelEditing = (e) => {
    e.stopPropagation();
    setEditingBatchId(null);
    setEditingName('');
  };

  const toggleBatch = (batchId) => {
    setExpandedBatches(prev => ({
      ...prev,
      [batchId]: !prev[batchId]
    }));
  };

  // Toggle record selection within a batch
  const toggleRecordSelection = (recordId, batchId) => {
    setActiveBatchId(batchId);
    setSelectedRecords(prev => 
      prev.includes(recordId) 
        ? prev.filter(id => id !== recordId)
        : [...prev, recordId]
    );
  };

  // Select all unvalidated records in a batch
  const selectAllInBatch = (batch) => {
    const unvalidatedRecords = batch.records.filter(r => !r.validation_status);
    const recordIds = unvalidatedRecords.map(r => r.id);
    const allSelected = recordIds.every(id => selectedRecords.includes(id));
    
    setActiveBatchId(batch.id);
    if (allSelected) {
      setSelectedRecords(prev => prev.filter(id => !recordIds.includes(id)));
    } else {
      setSelectedRecords(prev => [...new Set([...prev, ...recordIds])]);
    }
  };

  // Mark selected as valid
  const markAsValid = async () => {
    if (selectedRecords.length === 0) return;
    
    setProcessing(true);
    try {
      await api.post('/memberwd/staff/validate', {
        record_ids: selectedRecords,
        is_valid: true
      });
      toast.success(`${selectedRecords.length} record ditandai valid`);
      setSelectedRecords([]);
      loadBatches();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal menandai record');
    } finally {
      setProcessing(false);
    }
  };

  // Mark selected as invalid
  const markAsInvalid = async () => {
    if (selectedRecords.length === 0 || !invalidReason.trim()) return;
    
    setProcessing(true);
    try {
      await api.post('/memberwd/staff/validate', {
        record_ids: selectedRecords,
        is_valid: false,
        reason: invalidReason
      });
      toast.success(`${selectedRecords.length} record ditandai tidak valid`);
      setSelectedRecords([]);
      setShowInvalidModal(false);
      setInvalidReason('');
      loadBatches();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Gagal menandai record');
    } finally {
      setProcessing(false);
    }
  };

  const getStatusBadge = (record) => {
    if (record.validation_status === 'valid') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-xs rounded-full">
          <CheckCircle size={12} />
          Valid
        </span>
      );
    } else if (record.validation_status === 'invalid') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 text-xs rounded-full">
          <XCircle size={12} />
          Invalid
        </span>
      );
    }
    return (
      <span className="text-xs text-slate-400 dark:text-slate-500">Belum divalidasi</span>
    );
  };

  // Calculate total stats
  const totalRecords = batches.reduce((sum, b) => sum + b.active_count, 0);
  const totalValidated = batches.reduce((sum, b) => sum + b.validated_count, 0);
  const totalInvalid = batches.reduce((sum, b) => sum + b.invalid_count, 0);
  const totalUnvalidated = batches.reduce((sum, b) => sum + b.unvalidated_count, 0);

  return (
    <div data-testid="staff-memberwd-crm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Member WD CRM
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {totalRecords} total records dalam {batches.length} batch
          </p>
        </div>
        <button
          onClick={loadBatches}
          className="h-10 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2"
        >
          <RefreshCw size={18} className={`text-slate-600 dark:text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">Total Batches</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{batches.length}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">Total Records</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalRecords}</p>
        </div>
        <div className="bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4">
          <p className="text-sm text-emerald-600 dark:text-emerald-400">Validated</p>
          <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{totalValidated}</p>
        </div>
        <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
          <p className="text-sm text-amber-600 dark:text-amber-400">Belum Validasi</p>
          <p className="text-2xl font-bold text-amber-700 dark:text-amber-300">{totalUnvalidated}</p>
        </div>
      </div>

      {/* Validation Actions */}
      {selectedRecords.length > 0 && (
        <div className="mb-4 p-4 bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-800 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-indigo-700 dark:text-indigo-300 font-medium">
              {selectedRecords.length} record dipilih
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedRecords([])}
              className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
            >
              Batal
            </button>
            <button
              onClick={markAsValid}
              disabled={processing}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg flex items-center gap-2 disabled:opacity-50"
              data-testid="mark-valid-btn"
            >
              <CheckCircle size={16} />
              Tandai Valid
            </button>
            <button
              onClick={() => setShowInvalidModal(true)}
              disabled={processing}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg flex items-center gap-2 disabled:opacity-50"
              data-testid="mark-invalid-btn"
            >
              <XCircle size={16} />
              Tandai Tidak Valid
            </button>
          </div>
        </div>
      )}

      {/* Validation Guide */}
      <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-xl">
        <div className="flex items-start gap-3">
          <AlertTriangle className="text-amber-600 dark:text-amber-400 mt-0.5" size={20} />
          <div>
            <h4 className="font-semibold text-amber-800 dark:text-amber-300">Validasi Database</h4>
            <p className="text-sm text-amber-700 dark:text-amber-400">
              Pilih record dan tandai sebagai <strong>Valid</strong> jika data benar, atau <strong>Tidak Valid</strong> jika ada masalah. 
              Admin akan diberitahu untuk record yang tidak valid dan akan memberikan pengganti.
            </p>
          </div>
        </div>
      </div>

      {/* Invalid Reason Modal */}
      {showInvalidModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowInvalidModal(false)}>
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
              Alasan Tidak Valid
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
              Jelaskan mengapa {selectedRecords.length} record ini tidak valid:
            </p>
            <textarea
              value={invalidReason}
              onChange={(e) => setInvalidReason(e.target.value)}
              placeholder="Contoh: Nomor tidak aktif, Data tidak lengkap, dll..."
              className="w-full h-24 px-4 py-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white resize-none"
              data-testid="invalid-reason-input"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => {
                  setShowInvalidModal(false);
                  setInvalidReason('');
                }}
                className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg"
              >
                Batal
              </button>
              <button
                onClick={markAsInvalid}
                disabled={!invalidReason.trim() || processing}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50"
                data-testid="confirm-invalid-btn"
              >
                {processing ? 'Memproses...' : 'Konfirmasi'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Cards */}
      {loading ? (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <RefreshCw size={32} className="mx-auto text-slate-400 animate-spin mb-4" />
          <p className="text-slate-500 dark:text-slate-400">Memuat data...</p>
        </div>
      ) : batches.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <CreditCard size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <h3 className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-2">
            Belum ada data Member WD
          </h3>
          <p className="text-sm text-slate-400 dark:text-slate-500">
            Admin akan menugaskan data Member WD kepada Anda
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {batches.map((batch) => (
            <div
              key={batch.id}
              className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm"
              data-testid={`batch-card-${batch.id}`}
            >
              {/* Batch Header */}
              <div
                onClick={() => editingBatchId !== batch.id && toggleBatch(batch.id)}
                className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white">
                    <CreditCard size={24} />
                  </div>
                  <div className="text-left">
                    {editingBatchId === batch.id ? (
                      <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          className="px-2 py-1 text-base font-semibold rounded border border-indigo-300 dark:border-indigo-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveBatchName(batch.id, e);
                            if (e.key === 'Escape') cancelEditing(e);
                          }}
                        />
                        <button
                          onClick={(e) => saveBatchName(batch.id, e)}
                          className="p-1 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 rounded text-emerald-600 dark:text-emerald-400"
                          title="Simpan"
                        >
                          <Check size={18} />
                        </button>
                        <button
                          onClick={cancelEditing}
                          className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-600 dark:text-red-400"
                          title="Batal"
                        >
                          <X size={18} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-900 dark:text-white">
                          {batch.custom_name || batch.database_name}
                        </h3>
                        <button
                          onClick={(e) => startEditingBatch(batch, e)}
                          className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                          title="Ubah nama batch"
                        >
                          <Edit2 size={14} />
                        </button>
                      </div>
                    )}
                    <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
                      <span className="flex items-center gap-1">
                        <Package size={14} />
                        {batch.product_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {formatDate(batch.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-600 dark:text-slate-400">{batch.active_count} records</span>
                      {batch.validated_count > 0 && (
                        <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-xs rounded-full">
                          {batch.validated_count} valid
                        </span>
                      )}
                      {batch.unvalidated_count > 0 && (
                        <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs rounded-full">
                          {batch.unvalidated_count} pending
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      Ditugaskan oleh {batch.created_by}
                    </p>
                  </div>
                  {expandedBatches[batch.id] ? (
                    <ChevronUp className="text-slate-400" />
                  ) : (
                    <ChevronDown className="text-slate-400" />
                  )}
                </div>
              </div>

              {/* Batch Content */}
              {expandedBatches[batch.id] && (
                <div className="border-t border-slate-200 dark:border-slate-700">
                  {/* Select All Button */}
                  {batch.unvalidated_count > 0 && (
                    <div className="p-3 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
                      <button
                        onClick={() => selectAllInBatch(batch)}
                        className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-medium"
                      >
                        Pilih Semua Belum Validasi ({batch.unvalidated_count})
                      </button>
                    </div>
                  )}

                  {/* Records Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-slate-50 dark:bg-slate-900/50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase w-12">#</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Status</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Username</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Nama</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">WhatsApp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                        {batch.records.map((record, idx) => {
                          const rowData = record.row_data || {};
                          
                          // More flexible field detection - check multiple possible column names
                          const username = rowData.USERNAME || rowData.Username || rowData.username || rowData.USER || rowData.user || rowData.ID || rowData.id || '-';
                          const name = rowData.NAMA_REKENING || rowData.nama_rekening || rowData['Nama Rekening'] || rowData['Nama Lengkap'] || rowData.nama_lengkap || rowData.NAMA || rowData.Nama || rowData.Name || rowData.name || rowData.NAME || '-';
                          const whatsapp = rowData.WHATSAPP || rowData.WhatsApp || rowData.whatsapp || rowData.PHONE || rowData.Phone || rowData.phone || rowData.HP || rowData.hp || rowData.NO_HP || rowData.no_hp || '-';
                          const isSelected = selectedRecords.includes(record.id);
                          const isUnvalidated = !record.validation_status;

                          return (
                            <tr
                              key={record.id}
                              className={`hover:bg-slate-50 dark:hover:bg-slate-700/30 ${isSelected ? 'bg-indigo-50 dark:bg-indigo-900/20' : ''}`}
                            >
                              <td className="px-4 py-3">
                                {isUnvalidated ? (
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleRecordSelection(record.id, batch.id)}
                                    className="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-indigo-600 focus:ring-indigo-500"
                                  />
                                ) : (
                                  <span className="text-sm text-slate-400">{idx + 1}</span>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                {getStatusBadge(record)}
                              </td>
                              <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">
                                {username}
                              </td>
                              <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                                {name}
                              </td>
                              <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                                {whatsapp}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
