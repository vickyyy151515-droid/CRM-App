import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { 
  Send, 
  Clock, 
  Settings, 
  CheckCircle, 
  XCircle, 
  RefreshCw,
  Eye,
  Zap,
  MessageSquare,
  AlertTriangle,
  Users,
  UserX,
  Trash2,
  Plus
} from 'lucide-react';

export default function ScheduledReports() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [sending, setSending] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState(null);
  
  // Daily Report Form state
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [reportHour, setReportHour] = useState(1);
  const [reportMinute, setReportMinute] = useState(0);
  
  // At-Risk Alert Form state
  const [atriskEnabled, setAtriskEnabled] = useState(false);
  const [atriskGroupChatId, setAtriskGroupChatId] = useState('');
  const [atriskHour, setAtriskHour] = useState(11);
  const [atriskMinute, setAtriskMinute] = useState(0);
  const [atriskInactiveDays, setAtriskInactiveDays] = useState(14);
  const [atriskSaving, setAtriskSaving] = useState(false);
  const [atriskTesting, setAtriskTesting] = useState(false);
  const [atriskSending, setAtriskSending] = useState(false);
  const [atriskPreview, setAtriskPreview] = useState(null);

  // Staff Offline Alert Form state
  const [staffOfflineEnabled, setStaffOfflineEnabled] = useState(false);
  const [staffOfflineHour, setStaffOfflineHour] = useState(11);
  const [staffOfflineMinute, setStaffOfflineMinute] = useState(0);
  const [staffOfflineSaving, setStaffOfflineSaving] = useState(false);
  const [staffOfflineSending, setStaffOfflineSending] = useState(false);

  // Reserved Member Grace Period state
  const [reservedConfig, setReservedConfig] = useState(null);
  const [reservedConfigLoading, setReservedConfigLoading] = useState(false);
  const [reservedSaving, setReservedSaving] = useState(false);
  const [reservedPreview, setReservedPreview] = useState(null);
  const [reservedPreviewing, setReservedPreviewing] = useState(false);
  const [globalGraceDays, setGlobalGraceDays] = useState(30);
  const [warningDays, setWarningDays] = useState(7);
  const [productOverrides, setProductOverrides] = useState([]);
  const [availableProducts, setAvailableProducts] = useState([]);

  useEffect(() => {
    loadConfig();
    loadReservedMemberConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await api.get('/scheduled-reports/config');
      setConfig(response.data);
      
      // Set daily report form values
      if (response.data.telegram_bot_token) {
        setBotToken(response.data.telegram_bot_token);
      }
      setChatId(response.data.telegram_chat_id || '');
      setEnabled(response.data.enabled || false);
      setReportHour(response.data.report_hour || 1);
      setReportMinute(response.data.report_minute || 0);
      
      // Set at-risk form values
      setAtriskEnabled(response.data.atrisk_enabled || false);
      setAtriskGroupChatId(response.data.atrisk_group_chat_id || '');
      setAtriskHour(response.data.atrisk_hour || 11);
      setAtriskMinute(response.data.atrisk_minute || 0);
      setAtriskInactiveDays(response.data.atrisk_inactive_days || 14);

      // Set staff offline alert form values
      setStaffOfflineEnabled(response.data.staff_offline_enabled || false);
      setStaffOfflineHour(response.data.staff_offline_hour || 11);
      setStaffOfflineMinute(response.data.staff_offline_minute || 0);
    } catch (error) {
      toast.error('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    
    if (!botToken || !chatId) {
      toast.error('Please fill in Bot Token and Chat ID');
      return;
    }

    setSaving(true);
    try {
      await api.post('/scheduled-reports/config', {
        bot_token: botToken,
        chat_id: chatId,
        enabled: enabled,
        report_hour: reportHour,
        report_minute: reportMinute
      });
      toast.success('Configuration saved successfully');
      loadConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      await api.post('/scheduled-reports/test');
      toast.success('Test message sent! Check your Telegram.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send test message');
    } finally {
      setTesting(false);
    }
  };

  const handleSendNow = async () => {
    setSending(true);
    try {
      await api.post('/scheduled-reports/send-now');
      toast.success('Daily report sent! Check your Telegram.');
      loadConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send report');
    } finally {
      setSending(false);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      const response = await api.get('/scheduled-reports/preview');
      setPreview(response.data.report);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate preview');
    } finally {
      setPreviewing(false);
    }
  };

  // At-Risk Alert handlers
  const handleAtriskSave = async (e) => {
    e.preventDefault();
    
    if (!botToken || !atriskGroupChatId) {
      toast.error('Please fill in Bot Token and Group Chat ID');
      return;
    }

    setAtriskSaving(true);
    try {
      await api.post('/scheduled-reports/atrisk-config', {
        bot_token: botToken,
        group_chat_id: atriskGroupChatId,
        enabled: atriskEnabled,
        alert_hour: atriskHour,
        alert_minute: atriskMinute,
        inactive_days_threshold: atriskInactiveDays
      });
      toast.success('At-risk alert configuration saved successfully');
      loadConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save at-risk configuration');
    } finally {
      setAtriskSaving(false);
    }
  };

  const handleAtriskTest = async () => {
    setAtriskTesting(true);
    try {
      await api.post('/scheduled-reports/atrisk-test');
      toast.success('Test message sent to group! Check your Telegram group.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send test message');
    } finally {
      setAtriskTesting(false);
    }
  };

  const handleAtriskSendNow = async () => {
    setAtriskSending(true);
    try {
      await api.post('/scheduled-reports/atrisk-send-now');
      toast.success('At-risk alert sent to group! Check your Telegram group.');
      loadConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send at-risk alert');
    } finally {
      setAtriskSending(false);
    }
  };

  const handleAtriskPreview = async () => {
    try {
      const response = await api.get('/scheduled-reports/atrisk-preview');
      setAtriskPreview(response.data.alert);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate at-risk preview');
    }
  };

  // Staff Offline Alert handlers
  const handleStaffOfflineSave = async (e) => {
    e.preventDefault();
    
    if (!botToken || !chatId) {
      toast.error('Please configure Telegram Bot Token and Chat ID first (in Daily Report section)');
      return;
    }

    setStaffOfflineSaving(true);
    try {
      await api.post('/scheduled-reports/staff-offline-config', {
        enabled: staffOfflineEnabled,
        alert_hour: staffOfflineHour,
        alert_minute: staffOfflineMinute
      });
      toast.success('Staff offline alert configuration saved successfully');
      loadConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save staff offline configuration');
    } finally {
      setStaffOfflineSaving(false);
    }
  };

  const handleStaffOfflineSendNow = async () => {
    setStaffOfflineSending(true);
    try {
      await api.post('/scheduled-reports/staff-offline-send-now');
      toast.success('Staff offline alert sent! Check your Telegram.');
      loadConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send staff offline alert');
    } finally {
      setStaffOfflineSending(false);
    }
  };

  // Reserved Member Grace Period functions
  const loadReservedMemberConfig = async () => {
    setReservedConfigLoading(true);
    try {
      const response = await api.get('/reserved-members/cleanup-config');
      setReservedConfig(response.data);
      setGlobalGraceDays(response.data.global_grace_days || 30);
      setWarningDays(response.data.warning_days || 7);
      setProductOverrides(response.data.product_overrides || []);
      setAvailableProducts(response.data.available_products || []);
    } catch (error) {
      console.error('Error loading reserved member config:', error);
    } finally {
      setReservedConfigLoading(false);
    }
  };

  const handleReservedConfigSave = async (e) => {
    e.preventDefault();
    setReservedSaving(true);
    try {
      await api.put('/reserved-members/cleanup-config', {
        global_grace_days: globalGraceDays,
        warning_days: warningDays,
        product_overrides: productOverrides
      });
      toast.success('Grace period configuration saved!');
      loadReservedMemberConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setReservedSaving(false);
    }
  };

  const handleReservedPreview = async () => {
    setReservedPreviewing(true);
    try {
      const response = await api.get('/scheduled-reports/reserved-member-cleanup-preview');
      setReservedPreview(response.data);
    } catch (error) {
      toast.error('Failed to load preview');
    } finally {
      setReservedPreviewing(false);
    }
  };

  const addProductOverride = () => {
    // Find first product not already in overrides
    const usedProductIds = productOverrides.map(p => p.product_id);
    const availableProduct = availableProducts.find(p => !usedProductIds.includes(p.id));
    if (availableProduct) {
      setProductOverrides([...productOverrides, {
        product_id: availableProduct.id,
        product_name: availableProduct.name,
        grace_days: globalGraceDays
      }]);
    }
  };

  const removeProductOverride = (index) => {
    setProductOverrides(productOverrides.filter((_, i) => i !== index));
  };

  const updateProductOverride = (index, field, value) => {
    const updated = [...productOverrides];
    if (field === 'product_id') {
      const product = availableProducts.find(p => p.id === value);
      updated[index] = {
        ...updated[index],
        product_id: value,
        product_name: product?.name || 'Unknown'
      };
    } else {
      updated[index] = { ...updated[index], [field]: value };
    }
    setProductOverrides(updated);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="scheduled-reports-loading">
        <RefreshCw className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="scheduled-reports-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Scheduled Reports</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Configure automatic daily reports sent to Telegram
          </p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          config?.enabled 
            ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400' 
            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
        }`}>
          {config?.enabled ? '🟢 Active' : '⚫ Inactive'}
        </div>
      </div>

      {/* Status Card */}
      {config?.enabled && (
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center gap-3 mb-4">
            <Clock size={24} />
            <span className="text-lg font-semibold">Next Report Schedule</span>
          </div>
          <p className="text-2xl font-bold mb-2">
            Daily at {String(reportHour).padStart(2, '0')}:{String(reportMinute).padStart(2, '0')} WIB
          </p>
          <p className="text-indigo-100 text-sm">
            Reports previous day's NDP, RDP, Total Form, and Nominal for each staff by product
          </p>
          {config?.last_sent && (
            <p className="text-indigo-200 text-xs mt-4">
              Last sent: {new Date(config.last_sent).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })} WIB
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration Form */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Settings size={20} className="text-indigo-600" />
            Telegram Configuration
          </h2>
          
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Bot Token
              </label>
              <input
                type="password"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                placeholder="Enter your Telegram Bot Token"
                className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                data-testid="input-bot-token"
              />
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Get this from @BotFather on Telegram
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Chat ID
              </label>
              <input
                type="text"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                placeholder="Enter your Telegram Chat ID"
                className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                data-testid="input-chat-id"
              />
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Message @userinfobot on Telegram to get your Chat ID
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Report Hour (WIB)
                </label>
                <select
                  value={reportHour}
                  onChange={(e) => setReportHour(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="select-report-hour"
                >
                  {[...Array(24)].map((_, i) => (
                    <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Minute
                </label>
                <select
                  value={reportMinute}
                  onChange={(e) => setReportMinute(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="select-report-minute"
                >
                  {[0, 15, 30, 45].map((m) => (
                    <option key={m} value={m}>:{String(m).padStart(2, '0')}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="flex items-center gap-3 py-2">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                  className="sr-only peer"
                  data-testid="toggle-enabled"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-indigo-600"></div>
                <span className="ms-3 text-sm font-medium text-slate-700 dark:text-slate-300">
                  Enable scheduled reports
                </span>
              </label>
            </div>
            
            <button
              type="submit"
              disabled={saving}
              className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              data-testid="btn-save-config"
            >
              {saving ? <RefreshCw className="animate-spin" size={18} /> : <CheckCircle size={18} />}
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </form>
        </div>

        {/* Actions Panel */}
        <div className="space-y-4">
          {/* Quick Actions */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Zap size={20} className="text-amber-500" />
              Quick Actions
            </h2>
            
            <div className="space-y-3">
              <button
                onClick={handleTest}
                disabled={testing || !config?.telegram_bot_token}
                className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors flex items-center gap-3"
                data-testid="btn-test-telegram"
              >
                {testing ? <RefreshCw className="animate-spin" size={18} /> : <MessageSquare size={18} />}
                <div className="text-left">
                  <div className="font-medium">Test Telegram Connection</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">Send a test message to verify setup</div>
                </div>
              </button>
              
              <button
                onClick={handleSendNow}
                disabled={sending || !config?.telegram_bot_token}
                className="w-full px-4 py-3 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/50 disabled:opacity-50 transition-colors flex items-center gap-3"
                data-testid="btn-send-now"
              >
                {sending ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
                <div className="text-left">
                  <div className="font-medium">Send Report Now</div>
                  <div className="text-xs text-emerald-600 dark:text-emerald-500">Manually send yesterday's report</div>
                </div>
              </button>
              
              <button
                onClick={handlePreview}
                disabled={previewing}
                className="w-full px-4 py-3 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/50 disabled:opacity-50 transition-colors flex items-center gap-3"
                data-testid="btn-preview"
              >
                {previewing ? <RefreshCw className="animate-spin" size={18} /> : <Eye size={18} />}
                <div className="text-left">
                  <div className="font-medium">Preview Report</div>
                  <div className="text-xs text-indigo-600 dark:text-indigo-500">See what the report looks like</div>
                </div>
              </button>
            </div>
          </div>

          {/* Help Section */}
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
            <h3 className="font-medium text-amber-800 dark:text-amber-400 mb-2">How to get your Chat ID:</h3>
            <ol className="text-sm text-amber-700 dark:text-amber-500 space-y-1 list-decimal list-inside">
              <li>Open Telegram and search for @userinfobot</li>
              <li>Start a chat and send /start</li>
              <li>The bot will reply with your Chat ID</li>
              <li>Copy and paste the ID here</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {preview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setPreview(null)}>
          <div 
            className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 dark:text-white">Report Preview</h3>
              <button
                onClick={() => setPreview(null)}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                <XCircle size={20} />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <div className="bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-sm whitespace-pre-wrap">
                {preview.replace(/<[^>]*>/g, '')}
              </div>
            </div>
            <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => setPreview(null)}
                className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              >
                Close
              </button>
              <button
                onClick={() => { setPreview(null); handleSendNow(); }}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-2"
              >
                <Send size={16} />
                Send This Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* At-Risk Preview Modal */}
      {atriskPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setAtriskPreview(null)}>
          <div 
            className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <AlertTriangle size={20} className="text-amber-500" />
                At-Risk Alert Preview
              </h3>
              <button
                onClick={() => setAtriskPreview(null)}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                <XCircle size={20} />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <div className="bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-sm whitespace-pre-wrap">
                {atriskPreview.replace(/<[^>]*>/g, '')}
              </div>
            </div>
            <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => setAtriskPreview(null)}
                className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              >
                Close
              </button>
              <button
                onClick={() => { setAtriskPreview(null); handleAtriskSendNow(); }}
                className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 flex items-center gap-2"
              >
                <Send size={16} />
                Send This Alert
              </button>
            </div>
          </div>
        </div>
      )}

      {/* At-Risk Customer Alerts Section */}
      <div className="mt-8 border-t border-slate-200 dark:border-slate-700 pt-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <AlertTriangle size={24} className="text-amber-500" />
              At-Risk Customer Alerts
            </h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
              Send alerts for customers who haven't deposited recently to a Telegram group
            </p>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            config?.atrisk_enabled 
              ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400' 
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
          }`}>
            {config?.atrisk_enabled ? '🟡 Active' : '⚫ Inactive'}
          </div>
        </div>

        {/* At-Risk Status Card */}
        {config?.atrisk_enabled && (
          <div className="bg-gradient-to-r from-amber-500 to-orange-600 rounded-xl p-6 text-white shadow-lg mb-6">
            <div className="flex items-center gap-3 mb-4">
              <Users size={24} />
              <span className="text-lg font-semibold">At-Risk Alert Schedule</span>
            </div>
            <p className="text-2xl font-bold mb-2">
              Daily at {String(atriskHour).padStart(2, '0')}:{String(atriskMinute).padStart(2, '0')} WIB
            </p>
            <p className="text-amber-100 text-sm">
              Alerts for customers inactive for {atriskInactiveDays}+ days • Sent to group chat
            </p>
            {config?.atrisk_last_sent && (
              <p className="text-amber-200 text-xs mt-4">
                Last sent: {new Date(config.atrisk_last_sent).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })} WIB
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* At-Risk Configuration Form */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Settings size={20} className="text-amber-600" />
              Alert Configuration
            </h3>
            
            <form onSubmit={handleAtriskSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Group Chat ID
                </label>
                <input
                  type="text"
                  value={atriskGroupChatId}
                  onChange={(e) => setAtriskGroupChatId(e.target.value)}
                  placeholder="e.g., -4779729623"
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="input-atrisk-group-id"
                />
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Group chat IDs start with a minus sign (-)
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Alert Hour (WIB)
                  </label>
                  <select
                    value={atriskHour}
                    onChange={(e) => setAtriskHour(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    data-testid="select-atrisk-hour"
                  >
                    {[...Array(24)].map((_, i) => (
                      <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Minute
                  </label>
                  <select
                    value={atriskMinute}
                    onChange={(e) => setAtriskMinute(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    data-testid="select-atrisk-minute"
                  >
                    {[0, 15, 30, 45].map((m) => (
                      <option key={m} value={m}>:{String(m).padStart(2, '0')}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Inactive Days Threshold
                </label>
                <select
                  value={atriskInactiveDays}
                  onChange={(e) => setAtriskInactiveDays(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="select-atrisk-days"
                >
                  <option value={7}>7+ days</option>
                  <option value={14}>14+ days</option>
                  <option value={21}>21+ days</option>
                  <option value={30}>30+ days</option>
                </select>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Alert for customers who haven't deposited in this many days
                </p>
              </div>
              
              <div className="flex items-center gap-3 py-2">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={atriskEnabled}
                    onChange={(e) => setAtriskEnabled(e.target.checked)}
                    className="sr-only peer"
                    data-testid="toggle-atrisk-enabled"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 dark:peer-focus:ring-amber-800 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-amber-600"></div>
                  <span className="ms-3 text-sm font-medium text-slate-700 dark:text-slate-300">
                    Enable at-risk alerts
                  </span>
                </label>
              </div>
              
              <button
                type="submit"
                disabled={atriskSaving}
                className="w-full px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                data-testid="btn-save-atrisk-config"
              >
                {atriskSaving ? <RefreshCw className="animate-spin" size={18} /> : <CheckCircle size={18} />}
                {atriskSaving ? 'Saving...' : 'Save Alert Configuration'}
              </button>
            </form>
          </div>

          {/* At-Risk Quick Actions */}
          <div className="space-y-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <Zap size={20} className="text-amber-500" />
                Alert Actions
              </h3>
              
              <div className="space-y-3">
                <button
                  onClick={handleAtriskTest}
                  disabled={atriskTesting || !config?.atrisk_group_chat_id}
                  className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors flex items-center gap-3"
                  data-testid="btn-test-atrisk"
                >
                  {atriskTesting ? <RefreshCw className="animate-spin" size={18} /> : <MessageSquare size={18} />}
                  <div className="text-left">
                    <div className="font-medium">Test Group Connection</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">Send a test message to the group</div>
                  </div>
                </button>
                
                <button
                  onClick={handleAtriskSendNow}
                  disabled={atriskSending || !config?.atrisk_group_chat_id}
                  className="w-full px-4 py-3 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/50 disabled:opacity-50 transition-colors flex items-center gap-3"
                  data-testid="btn-send-atrisk-now"
                >
                  {atriskSending ? <RefreshCw className="animate-spin" size={18} /> : <AlertTriangle size={18} />}
                  <div className="text-left">
                    <div className="font-medium">Send Alert Now</div>
                    <div className="text-xs text-amber-600 dark:text-amber-500">Manually send at-risk customer alert</div>
                  </div>
                </button>
                
                <button
                  onClick={handleAtriskPreview}
                  className="w-full px-4 py-3 bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 rounded-lg hover:bg-orange-100 dark:hover:bg-orange-900/50 disabled:opacity-50 transition-colors flex items-center gap-3"
                  data-testid="btn-preview-atrisk"
                >
                  <Eye size={18} />
                  <div className="text-left">
                    <div className="font-medium">Preview Alert</div>
                    <div className="text-xs text-orange-600 dark:text-orange-500">See what the alert looks like</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Help Section */}
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
              <h4 className="font-medium text-amber-800 dark:text-amber-400 mb-2">How to get Group Chat ID:</h4>
              <ol className="text-sm text-amber-700 dark:text-amber-500 space-y-1 list-decimal list-inside">
                <li>Add your bot to the Telegram group</li>
                <li>Send a message in the group</li>
                <li>Add @RawDataBot to the group temporarily</li>
                <li>It will show the group ID (starts with -)</li>
              </ol>
            </div>
          </div>
        </div>
      </div>

      {/* Staff Offline Alerts Section */}
      <div className="mt-8 border-t border-slate-200 dark:border-slate-700 pt-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Users size={24} className="text-red-500" />
              Staff Offline Alerts
            </h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
              Get notified when staff members haven't logged in by a specific time
            </p>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            config?.staff_offline_enabled 
              ? 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-400' 
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
          }`}>
            {config?.staff_offline_enabled ? '🔴 Active' : '⚫ Inactive'}
          </div>
        </div>

        {/* Staff Offline Status Card */}
        {config?.staff_offline_enabled && (
          <div className="bg-gradient-to-r from-red-500 to-rose-600 rounded-xl p-6 text-white shadow-lg mb-6">
            <div className="flex items-center gap-3 mb-4">
              <Clock size={24} />
              <span className="text-lg font-semibold">Staff Offline Check Schedule</span>
            </div>
            <p className="text-2xl font-bold mb-2">
              Daily at {String(staffOfflineHour).padStart(2, '0')}:{String(staffOfflineMinute).padStart(2, '0')} WIB
            </p>
            <p className="text-red-100 text-sm">
              Alerts when staff members are not online • Sent to admin's personal chat
            </p>
            {config?.staff_offline_last_sent && (
              <p className="text-red-200 text-xs mt-4">
                Last sent: {new Date(config.staff_offline_last_sent).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })} WIB
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Staff Offline Configuration Form */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Settings size={20} className="text-red-600" />
              Alert Configuration
            </h3>
            
            <form onSubmit={handleStaffOfflineSave} className="space-y-4">
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  <strong>Note:</strong> This alert uses the same Bot Token and Chat ID configured in the Daily Report section above. 
                  Make sure to configure those first.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Alert Hour (WIB)
                  </label>
                  <select
                    value={staffOfflineHour}
                    onChange={(e) => setStaffOfflineHour(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    data-testid="select-staff-offline-hour"
                  >
                    {[...Array(24)].map((_, i) => (
                      <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Minute
                  </label>
                  <select
                    value={staffOfflineMinute}
                    onChange={(e) => setStaffOfflineMinute(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    data-testid="select-staff-offline-minute"
                  >
                    {[0, 15, 30, 45].map((m) => (
                      <option key={m} value={m}>:{String(m).padStart(2, '0')}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="flex items-center gap-3 py-2">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={staffOfflineEnabled}
                    onChange={(e) => setStaffOfflineEnabled(e.target.checked)}
                    className="sr-only peer"
                    data-testid="toggle-staff-offline-enabled"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-red-300 dark:peer-focus:ring-red-800 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-red-600"></div>
                  <span className="ms-3 text-sm font-medium text-slate-700 dark:text-slate-300">
                    Enable staff offline alerts
                  </span>
                </label>
              </div>
              
              <button
                type="submit"
                disabled={staffOfflineSaving}
                className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                data-testid="btn-save-staff-offline-config"
              >
                {staffOfflineSaving ? <RefreshCw className="animate-spin" size={18} /> : <CheckCircle size={18} />}
                {staffOfflineSaving ? 'Saving...' : 'Save Alert Configuration'}
              </button>
            </form>
          </div>

          {/* Staff Offline Quick Actions */}
          <div className="space-y-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <Zap size={20} className="text-red-500" />
                Alert Actions
              </h3>
              
              <div className="space-y-3">
                <button
                  onClick={handleStaffOfflineSendNow}
                  disabled={staffOfflineSending || !config?.telegram_bot_token || !config?.telegram_chat_id}
                  className="w-full px-4 py-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 disabled:opacity-50 transition-colors flex items-center gap-3"
                  data-testid="btn-send-staff-offline-now"
                >
                  {staffOfflineSending ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
                  <div className="text-left">
                    <div className="font-medium">Check Staff Status Now</div>
                    <div className="text-xs text-red-600 dark:text-red-500">Send current staff online/offline status</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Info Section */}
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
              <h4 className="font-medium text-red-800 dark:text-red-400 mb-2">How it works:</h4>
              <ul className="text-sm text-red-700 dark:text-red-500 space-y-1 list-disc list-inside">
                <li>At the scheduled time, checks which staff are online</li>
                <li>Staff are considered &quot;online&quot; if active within 30 minutes</li>
                <li>Alert lists all offline staff with last login time</li>
                <li>Helps ensure team is working on time</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Reserved Member Grace Period Section */}
      <div className="bg-gradient-to-r from-teal-500 to-emerald-600 rounded-xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-3 mb-2">
          <UserX size={24} />
          <span className="text-lg font-semibold">Reserved Member Auto-Cleanup</span>
        </div>
        <p className="text-teal-100 text-sm">
          Automatically removes reserved members if no OMSET is recorded within the grace period. 
          Daily cleanup runs at 00:01 AM WIB.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Grace Period Configuration */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Settings size={20} className="text-teal-600" />
            Grace Period Settings
          </h3>
          
          <form onSubmit={handleReservedConfigSave} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Global Grace Period (Days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={globalGraceDays}
                  onChange={(e) => setGlobalGraceDays(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="input-global-grace-days"
                />
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Default days before auto-delete
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Warning Period (Days)
                </label>
                <input
                  type="number"
                  min="1"
                  max={globalGraceDays - 1}
                  value={warningDays}
                  onChange={(e) => setWarningDays(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  data-testid="input-warning-days"
                />
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Start warning notifications X days before expiry
                </p>
              </div>
            </div>

            {/* Product Overrides */}
            <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Product-Specific Grace Periods (Optional)
                </label>
                <button
                  type="button"
                  onClick={addProductOverride}
                  disabled={productOverrides.length >= availableProducts.length}
                  className="text-teal-600 hover:text-teal-700 text-sm flex items-center gap-1 disabled:opacity-50"
                  data-testid="btn-add-product-override"
                >
                  <Plus size={16} /> Add Product
                </button>
              </div>
              
              {productOverrides.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400 italic">
                  No product-specific overrides. All products use the global grace period.
                </p>
              ) : (
                <div className="space-y-2">
                  {productOverrides.map((override, index) => (
                    <div key={index} className="flex items-center gap-2 bg-slate-50 dark:bg-slate-700/50 p-3 rounded-lg">
                      <select
                        value={override.product_id}
                        onChange={(e) => updateProductOverride(index, 'product_id', e.target.value)}
                        className="flex-1 px-3 py-1.5 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                        data-testid={`select-override-product-${index}`}
                      >
                        {availableProducts.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="1"
                        max="365"
                        value={override.grace_days}
                        onChange={(e) => updateProductOverride(index, 'grace_days', Number(e.target.value))}
                        className="w-20 px-3 py-1.5 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                        data-testid={`input-override-days-${index}`}
                      />
                      <span className="text-sm text-slate-500 dark:text-slate-400">days</span>
                      <button
                        type="button"
                        onClick={() => removeProductOverride(index)}
                        className="text-red-500 hover:text-red-700 p-1"
                        data-testid={`btn-remove-override-${index}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <button
              type="submit"
              disabled={reservedSaving}
              className="w-full px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              data-testid="btn-save-reserved-config"
            >
              {reservedSaving ? <RefreshCw className="animate-spin" size={18} /> : <CheckCircle size={18} />}
              {reservedSaving ? 'Saving...' : 'Save Grace Period Configuration'}
            </button>
          </form>
        </div>

        {/* Preview Section */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Eye size={20} className="text-teal-500" />
              Cleanup Preview
            </h3>
            
            <button
              onClick={handleReservedPreview}
              disabled={reservedPreviewing}
              className="w-full px-4 py-3 bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400 rounded-lg hover:bg-teal-100 dark:hover:bg-teal-900/50 disabled:opacity-50 transition-colors flex items-center gap-3 mb-4"
              data-testid="btn-preview-reserved-cleanup"
            >
              {reservedPreviewing ? <RefreshCw className="animate-spin" size={18} /> : <Eye size={18} />}
              <div className="text-left">
                <div className="font-medium">Preview Cleanup</div>
                <div className="text-xs text-teal-600 dark:text-teal-500">See which members will be warned/deleted</div>
              </div>
            </button>

            {reservedPreview && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                    <div className="text-slate-500 dark:text-slate-400">Total Approved</div>
                    <div className="text-xl font-bold text-slate-900 dark:text-white">{reservedPreview.total_approved_members}</div>
                  </div>
                  <div className="bg-emerald-50 dark:bg-emerald-900/30 rounded-lg p-3">
                    <div className="text-emerald-600 dark:text-emerald-400">Active (Has OMSET)</div>
                    <div className="text-xl font-bold text-emerald-700 dark:text-emerald-300">{reservedPreview.active_members_with_omset}</div>
                  </div>
                  <div className="bg-amber-50 dark:bg-amber-900/30 rounded-lg p-3">
                    <div className="text-amber-600 dark:text-amber-400">Expiring Soon</div>
                    <div className="text-xl font-bold text-amber-700 dark:text-amber-300">{reservedPreview.expiring_soon_count}</div>
                  </div>
                  <div className="bg-red-50 dark:bg-red-900/30 rounded-lg p-3">
                    <div className="text-red-600 dark:text-red-400">Will Be Deleted</div>
                    <div className="text-xl font-bold text-red-700 dark:text-red-300">{reservedPreview.will_be_deleted_count}</div>
                  </div>
                </div>

                {reservedPreview.expiring_soon?.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-amber-600 dark:text-amber-400 mb-2">Expiring Soon:</h4>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {reservedPreview.expiring_soon.map((m, i) => (
                        <div key={i} className="text-xs bg-amber-50 dark:bg-amber-900/20 p-2 rounded flex justify-between">
                          <span className="text-slate-700 dark:text-slate-300">{m.customer_name} ({m.staff_name})</span>
                          <span className="text-amber-600 dark:text-amber-400">{m.days_remaining}d left</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {reservedPreview.will_be_deleted?.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">Will Be Deleted:</h4>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {reservedPreview.will_be_deleted.map((m, i) => (
                        <div key={i} className="text-xs bg-red-50 dark:bg-red-900/20 p-2 rounded flex justify-between">
                          <span className="text-slate-700 dark:text-slate-300">{m.customer_name} ({m.staff_name})</span>
                          <span className="text-red-600 dark:text-red-400">{m.grace_days}d grace period</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Info Section */}
          <div className="bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-xl p-4">
            <h4 className="font-medium text-teal-800 dark:text-teal-400 mb-2">How it works:</h4>
            <ul className="text-sm text-teal-700 dark:text-teal-500 space-y-1 list-disc list-inside">
              <li>Reserved members without OMSET are tracked</li>
              <li>Warning notifications start {warningDays} days before expiry</li>
              <li>After {globalGraceDays} days with no OMSET, auto-deleted</li>
              <li>Product-specific periods override the global setting</li>
              <li>Cleanup runs automatically at 00:01 AM WIB daily</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
