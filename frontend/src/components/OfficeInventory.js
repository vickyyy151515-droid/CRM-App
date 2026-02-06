import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Plus, Layers } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import InventoryStatsCards from './inventory/InventoryStatsCards';
import InventoryFilters from './inventory/InventoryFilters';
import InventoryTable from './inventory/InventoryTable';
import InventoryItemModal from './inventory/InventoryItemModal';
import InventoryAssignModal from './inventory/InventoryAssignModal';
import InventoryReturnModal from './inventory/InventoryReturnModal';
import InventoryHistoryModal from './inventory/InventoryHistoryModal';
import InventoryBulkAddModal from './inventory/InventoryBulkAddModal';

const EMPTY_FORM = {
  name: '', description: '', category: 'laptop', serial_number: '',
  purchase_date: '', purchase_price: '', condition: 'good', notes: '',
  assign_to_staff_id: '', assignment_notes: ''
};

const EMPTY_BULK_ROW = { name: '', category: 'laptop', serial_number: '', condition: 'good', staff_id: '' };

export default function OfficeInventory() {
  const { t } = useLanguage();
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState({ total: 0, assigned: 0, available: 0 });
  const [loading, setLoading] = useState(true);
  const [staff, setStaff] = useState([]);

  // Filters
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterStaff, setFilterStaff] = useState('');

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBulkAddModal, setShowBulkAddModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [assignmentHistory, setAssignmentHistory] = useState([]);

  // Form state
  const [bulkItems, setBulkItems] = useState([{ ...EMPTY_BULK_ROW }]);
  const [formData, setFormData] = useState({ ...EMPTY_FORM });
  const [assignData, setAssignData] = useState({ staff_id: '', notes: '' });
  const [returnData, setReturnData] = useState({ condition: 'good', notes: '' });
  const [saving, setSaving] = useState(false);

  const loadInventory = useCallback(async () => {
    try {
      const params = {};
      if (search) params.search = search;
      if (filterCategory) params.category = filterCategory;
      if (filterStatus) params.status = filterStatus;
      if (filterStaff) params.assigned_to = filterStaff;

      const response = await api.get('/inventory', { params });
      setItems(response.data.items);
      setCategories(response.data.categories);
      setStats(response.data.stats);
    } catch (error) {
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  }, [search, filterCategory, filterStatus, filterStaff]);

  const loadStaff = async () => {
    try {
      const response = await api.get('/users');
      setStaff(response.data.filter(u => u.role === 'staff'));
    } catch (error) {
      console.error('Failed to load staff:', error);
    }
  };

  useEffect(() => {
    loadInventory();
    loadStaff();
  }, [loadInventory]);

  const resetForm = () => {
    setFormData({ ...EMPTY_FORM });
    setSelectedItem(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...formData, purchase_price: formData.purchase_price ? parseFloat(formData.purchase_price) : null };
      if (selectedItem) {
        await api.put(`/inventory/${selectedItem.id}`, payload);
        toast.success('Item updated successfully');
      } else {
        await api.post('/inventory', payload);
        toast.success('Item added successfully');
      }
      setShowAddModal(false);
      resetForm();
      loadInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save item');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (item) => {
    if (!window.confirm(`Are you sure you want to delete "${item.name}"?`)) return;
    try {
      await api.delete(`/inventory/${item.id}`);
      toast.success('Item deleted successfully');
      loadInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete item');
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!assignData.staff_id) { toast.error('Please select a staff member'); return; }
    setSaving(true);
    try {
      await api.post(`/inventory/${selectedItem.id}/assign`, assignData);
      toast.success('Item assigned successfully');
      setShowAssignModal(false);
      setAssignData({ staff_id: '', notes: '' });
      loadInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign item');
    } finally {
      setSaving(false);
    }
  };

  const handleReturn = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post(`/inventory/${selectedItem.id}/return`, returnData);
      toast.success('Item returned successfully');
      setShowReturnModal(false);
      setReturnData({ condition: 'good', notes: '' });
      loadInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to return item');
    } finally {
      setSaving(false);
    }
  };

  const handleBulkAdd = async (e) => {
    e.preventDefault();
    const validItems = bulkItems.filter(item => item.name.trim());
    if (validItems.length === 0) { toast.error('Please enter at least one item name'); return; }
    setSaving(true);
    try {
      const response = await api.post('/inventory/bulk', { items: validItems });
      toast.success(`Successfully created ${response.data.total_created} items`);
      setShowBulkAddModal(false);
      setBulkItems([{ ...EMPTY_BULK_ROW }]);
      loadInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to bulk add items');
    } finally {
      setSaving(false);
    }
  };

  const loadHistory = async (item) => {
    try {
      const response = await api.get(`/inventory/${item.id}`);
      setAssignmentHistory(response.data.assignment_history);
      setSelectedItem(item);
      setShowHistoryModal(true);
    } catch (error) {
      toast.error('Failed to load history');
    }
  };

  const openEditModal = (item) => {
    setSelectedItem(item);
    setFormData({
      name: item.name, description: item.description || '', category: item.category,
      serial_number: item.serial_number || '', purchase_date: item.purchase_date || '',
      purchase_price: item.purchase_price || '', condition: item.condition, notes: item.notes || '',
      assign_to_staff_id: '', assignment_notes: ''
    });
    setShowAddModal(true);
  };

  // Bulk add helpers
  const addBulkRow = () => setBulkItems([...bulkItems, { ...EMPTY_BULK_ROW }]);
  const removeBulkRow = (index) => { if (bulkItems.length > 1) setBulkItems(bulkItems.filter((_, i) => i !== index)); };
  const updateBulkItem = (index, field, value) => { const updated = [...bulkItems]; updated[index] = { ...updated[index], [field]: value }; setBulkItems(updated); };
  const duplicateBulkRow = (index) => setBulkItems([...bulkItems, { ...bulkItems[index], serial_number: '' }]);
  const applyStaffToAll = (staffId) => setBulkItems(bulkItems.map(item => ({ ...item, staff_id: staffId })));

  return (
    <div data-testid="office-inventory-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Office Inventory</h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Track office equipment assigned to staff</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowBulkAddModal(true)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-2 transition-colors" data-testid="btn-bulk-add">
            <Layers size={18} /> Bulk Add
          </button>
          <button onClick={() => { resetForm(); setShowAddModal(true); }} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2 transition-colors" data-testid="btn-add-item">
            <Plus size={18} /> Add Item
          </button>
        </div>
      </div>

      <InventoryStatsCards stats={stats} />

      <InventoryFilters
        search={search} setSearch={setSearch}
        filterCategory={filterCategory} setFilterCategory={setFilterCategory}
        filterStatus={filterStatus} setFilterStatus={setFilterStatus}
        filterStaff={filterStaff} setFilterStaff={setFilterStaff}
        staff={staff}
      />

      <InventoryTable
        items={items} loading={loading}
        onAssign={(item) => { setSelectedItem(item); setShowAssignModal(true); }}
        onReturn={(item) => { setSelectedItem(item); setShowReturnModal(true); }}
        onHistory={loadHistory} onEdit={openEditModal} onDelete={handleDelete}
      />

      <InventoryItemModal
        show={showAddModal} selectedItem={selectedItem}
        formData={formData} setFormData={setFormData}
        staff={staff} saving={saving}
        onSubmit={handleSubmit} onClose={() => { setShowAddModal(false); resetForm(); }}
      />

      <InventoryAssignModal
        show={showAssignModal} item={selectedItem}
        assignData={assignData} setAssignData={setAssignData}
        staff={staff} saving={saving}
        onSubmit={handleAssign} onClose={() => setShowAssignModal(false)}
      />

      <InventoryReturnModal
        show={showReturnModal} item={selectedItem}
        returnData={returnData} setReturnData={setReturnData}
        saving={saving}
        onSubmit={handleReturn} onClose={() => setShowReturnModal(false)}
      />

      <InventoryHistoryModal
        show={showHistoryModal} item={selectedItem}
        history={assignmentHistory}
        onClose={() => setShowHistoryModal(false)}
      />

      <InventoryBulkAddModal
        show={showBulkAddModal} bulkItems={bulkItems}
        staff={staff} saving={saving}
        onUpdateItem={updateBulkItem} onAddRow={addBulkRow}
        onRemoveRow={removeBulkRow} onDuplicateRow={duplicateBulkRow}
        onApplyStaffToAll={applyStaffToAll}
        onSubmit={handleBulkAdd} onClose={() => setShowBulkAddModal(false)}
      />
    </div>
  );
}
