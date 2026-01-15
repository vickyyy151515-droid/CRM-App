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
  MessageSquare
} from 'lucide-react';

export default function ScheduledReports() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [sending, setSending] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState(null);
  
  // Form state
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [reportHour, setReportHour] = useState(1);
  const [reportMinute, setReportMinute] = useState(0);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await api.get('/scheduled-reports/config');
      setConfig(response.data);
      
      // Set form values
      if (response.data.telegram_bot_token) {
        setBotToken(response.data.telegram_bot_token);
      }
      setChatId(response.data.telegram_chat_id || '');
      setEnabled(response.data.enabled || false);
      setReportHour(response.data.report_hour || 1);
      setReportMinute(response.data.report_minute || 0);
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
    </div>
  );
}
