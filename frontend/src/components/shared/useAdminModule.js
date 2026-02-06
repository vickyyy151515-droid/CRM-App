import { useState, useEffect, useCallback } from 'react';
import { api } from '../../App';
import { toast } from 'sonner';

/**
 * Custom hook for Admin module state management
 * Shared between AdminDBBonanza, AdminMemberWDCRM, and AdminOmsetCRM
 * 
 * @param {string} moduleType - 'bonanza', 'memberwd', or 'omset'
 * @param {Object} options - Additional options
 */
export function useAdminModule(moduleType, options = {}) {
  const { settingsKey = `${moduleType}_settings` } = options;
  
  // Core state
  const [databases, setDatabases] = useState([]);
  const [products, setProducts] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  
  // Upload form state
  const [uploadName, setUploadName] = useState('');
  const [uploadProductId, setUploadProductId] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  
  // Records state
  const [expandedDb, setExpandedDb] = useState(null);
  const [records, setRecords] = useState([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [selectedRecords, setSelectedRecords] = useState([]);
  
  // Assignment state
  const [selectedStaff, setSelectedStaff] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [randomQuantity, setRandomQuantity] = useState('');
  
  // Filter state
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterProduct, setFilterProduct] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Invalid records state
  const [invalidRecords, setInvalidRecords] = useState(null);
  const [showInvalidPanel, setShowInvalidPanel] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [expandedInvalidStaff, setExpandedInvalidStaff] = useState({});
  
  // Replacement modal state
  const [showReplaceModal, setShowReplaceModal] = useState(false);
  const [replaceStaffId, setReplaceStaffId] = useState(null);
  const [replaceStaffName, setReplaceStaffName] = useState('');
  const [replaceInvalidCount, setReplaceInvalidCount] = useState(0);
  const [replaceQuantity, setReplaceQuantity] = useState(0);
  
  // Tab state
  const [activeTab, setActiveTab] = useState('databases');
  const [archivedRecords, setArchivedRecords] = useState(null);
  const [loadingArchived, setLoadingArchived] = useState(false);
  
  // Settings state
  const [moduleSettings, setModuleSettings] = useState({
    auto_replace_invalid: false,
    max_replacements_per_batch: 10
  });
  const [showSettingsPanel, setShowSettingsPanel] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  
  // Reserved names
  const [reservedNames, setReservedNames] = useState([]);
  
  // API prefix
  const apiPrefix = moduleType === 'bonanza' ? '/bonanza' : 
                   moduleType === 'memberwd' ? '/memberwd' : '';

  // ==================== LOAD FUNCTIONS ====================
  
  const loadProducts = useCallback(async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  }, []);

  const loadStaff = useCallback(async () => {
    try {
      const response = await api.get('/users?role=staff');
      setStaff(response.data);
    } catch (error) {
      console.error('Failed to load staff:', error);
    }
  }, []);

  const loadReservedNames = useCallback(async () => {
    try {
      const response = await api.get('/reserved-members');
      setReservedNames(response.data.map(r => r.name ? r.name.toLowerCase().trim() : null).filter(Boolean));
    } catch (error) {
      console.error('Failed to load reserved names');
    }
  }, []);

  const loadDatabases = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterProduct) params.append('product_id', filterProduct);
      
      const endpoint = apiPrefix ? `${apiPrefix}/databases` : '/databases/with-stats';
      const response = await api.get(`${endpoint}?${params}`);
      setDatabases(response.data);
    } catch (error) {
      toast.error('Failed to load databases');
    } finally {
      setLoading(false);
    }
  }, [apiPrefix, filterProduct]);

  const loadInvalidRecords = useCallback(async () => {
    try {
      const endpoint = apiPrefix ? `${apiPrefix}/admin/invalid-records` : '/admin/invalid-records';
      const response = await api.get(endpoint);
      setInvalidRecords(response.data);
    } catch (error) {
      console.error('Failed to load invalid records');
    }
  }, [apiPrefix]);

  const loadArchivedRecords = useCallback(async () => {
    try {
      setLoadingArchived(true);
      const endpoint = apiPrefix ? `${apiPrefix}/admin/archived-records` : '/admin/archived-records';
      const response = await api.get(endpoint);
      setArchivedRecords(response.data);
    } catch (error) {
      console.error('Failed to load archived records');
    } finally {
      setLoadingArchived(false);
    }
  }, [apiPrefix]);

  const loadSettings = useCallback(async () => {
    try {
      const response = await api.get('/settings');
      const settings = response.data.find(s => s.key === settingsKey);
      if (settings) {
        setModuleSettings(settings.value);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }, [settingsKey]);

  const loadRecords = useCallback(async (databaseId) => {
    if (expandedDb === databaseId) {
      setExpandedDb(null);
      setRecords([]);
      return;
    }
    
    try {
      setLoadingRecords(true);
      setExpandedDb(databaseId);
      const endpoint = apiPrefix ? `${apiPrefix}/databases/${databaseId}/records` : `/databases/${databaseId}/records`;
      const response = await api.get(endpoint);
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load records');
    } finally {
      setLoadingRecords(false);
    }
  }, [apiPrefix, expandedDb]);

  // ==================== ACTION FUNCTIONS ====================

  const handleSaveSettings = useCallback(async () => {
    try {
      setSavingSettings(true);
      await api.post('/settings', {
        key: settingsKey,
        value: moduleSettings
      });
      toast.success('Settings saved successfully');
      setShowSettingsPanel(false);
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSavingSettings(false);
    }
  }, [settingsKey, moduleSettings]);

  const handleUpload = useCallback(async (e) => {
    e.preventDefault();
    if (!selectedFile || !uploadName || !uploadProductId) {
      toast.error('Please fill in all fields and select a file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', uploadName);
      formData.append('product_id', uploadProductId);

      const endpoint = apiPrefix ? `${apiPrefix}/databases` : '/databases';
      await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success('Database uploaded successfully');
      setUploadName('');
      setUploadProductId('');
      setSelectedFile(null);
      loadDatabases();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload database');
    } finally {
      setUploading(false);
    }
  }, [selectedFile, uploadName, uploadProductId, apiPrefix, loadDatabases]);

  const handleDeleteDatabase = useCallback(async (databaseId) => {
    if (!window.confirm('Are you sure you want to delete this database? All records will be lost.')) return;
    
    try {
      const endpoint = apiPrefix ? `${apiPrefix}/databases/${databaseId}` : `/databases/${databaseId}`;
      await api.delete(endpoint);
      toast.success('Database deleted');
      loadDatabases();
    } catch (error) {
      toast.error('Failed to delete database');
    }
  }, [apiPrefix, loadDatabases]);

  const handleDismissInvalidAlerts = useCallback(async () => {
    try {
      const endpoint = apiPrefix ? `${apiPrefix}/admin/dismiss-invalid-alerts` : '/admin/dismiss-invalid-alerts';
      await api.post(endpoint);
      toast.success('Invalid alerts dismissed');
      loadInvalidRecords();
    } catch (error) {
      toast.error('Failed to dismiss alerts');
    }
  }, [apiPrefix, loadInvalidRecords]);

  const openReplaceModal = useCallback((staffId, staffName, count) => {
    setReplaceStaffId(staffId);
    setReplaceStaffName(staffName);
    setReplaceInvalidCount(count);
    setReplaceQuantity(Math.min(count, moduleSettings.max_replacements_per_batch));
    setShowReplaceModal(true);
  }, [moduleSettings.max_replacements_per_batch]);

  const handleProcessInvalid = useCallback(async () => {
    if (!replaceStaffId) return;
    
    try {
      setProcessing(true);
      const endpoint = apiPrefix ? `${apiPrefix}/admin/replace-invalid` : '/admin/replace-invalid';
      await api.post(endpoint, {
        staff_id: replaceStaffId,
        quantity: replaceQuantity
      });
      toast.success(`Replaced ${replaceQuantity} invalid records`);
      setShowReplaceModal(false);
      loadInvalidRecords();
      loadDatabases();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to replace records');
    } finally {
      setProcessing(false);
    }
  }, [apiPrefix, replaceStaffId, replaceQuantity, loadInvalidRecords, loadDatabases]);

  const toggleExpandInvalidStaff = useCallback((staffId) => {
    setExpandedInvalidStaff(prev => ({
      ...prev,
      [staffId]: !prev[staffId]
    }));
  }, []);

  // ==================== EFFECTS ====================

  useEffect(() => {
    loadProducts();
    loadStaff();
    loadReservedNames();
    loadInvalidRecords();
    loadSettings();
  }, [loadProducts, loadStaff, loadReservedNames, loadInvalidRecords, loadSettings]);

  useEffect(() => {
    loadDatabases();
  }, [loadDatabases]);

  useEffect(() => {
    if (activeTab === 'invalid') {
      loadArchivedRecords();
    }
  }, [activeTab, loadArchivedRecords]);

  // ==================== RETURN ====================

  return {
    // Data state
    databases,
    products,
    staff,
    records,
    reservedNames,
    invalidRecords,
    archivedRecords,
    
    // Loading state
    loading,
    uploading,
    loadingRecords,
    loadingArchived,
    processing,
    assigning,
    savingSettings,
    
    // UI state
    expandedDb,
    activeTab,
    showInvalidPanel,
    showReplaceModal,
    showSettingsPanel,
    expandedInvalidStaff,
    
    // Form state
    uploadName,
    uploadProductId,
    selectedFile,
    selectedRecords,
    selectedStaff,
    filterStatus,
    filterProduct,
    searchTerm,
    randomQuantity,
    
    // Replace modal state
    replaceStaffId,
    replaceStaffName,
    replaceInvalidCount,
    replaceQuantity,
    
    // Settings
    moduleSettings,
    
    // Setters
    setDatabases,
    setRecords,
    setUploadName,
    setUploadProductId,
    setSelectedFile,
    setSelectedRecords,
    setSelectedStaff,
    setAssigning,
    setFilterStatus,
    setFilterProduct,
    setSearchTerm,
    setRandomQuantity,
    setActiveTab,
    setShowInvalidPanel,
    setShowReplaceModal,
    setShowSettingsPanel,
    setReplaceQuantity,
    setModuleSettings,
    setExpandedDb,
    
    // Actions
    loadDatabases,
    loadRecords,
    loadInvalidRecords,
    loadArchivedRecords,
    handleUpload,
    handleDeleteDatabase,
    handleSaveSettings,
    handleDismissInvalidAlerts,
    handleProcessInvalid,
    openReplaceModal,
    toggleExpandInvalidStaff,
    
    // API prefix for custom calls
    apiPrefix,
  };
}

export default useAdminModule;
