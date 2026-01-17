import { useState, useEffect, useRef } from 'react';
import { api } from '../App';
import { Bell, Check, CheckCheck, Trash2, X, AlertCircle, Clock, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/LanguageContext';

// WebSocket connection status enum
const WS_STATUS = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  RECONNECTING: 'reconnecting'
};

export default function NotificationBell({ userRole }) {
  const { t } = useLanguage();
  const [notifications, setNotifications] = useState([]);
  const [followupAlerts, setFollowupAlerts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [followupCount, setFollowupCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [wsStatus, setWsStatus] = useState(WS_STATUS.DISCONNECTED);
  const dropdownRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 2000;

  // Get WebSocket URL from backend URL
  const getWsUrl = () => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    // Convert http(s) to ws(s)
    let wsUrl = backendUrl.replace('https://', 'wss://').replace('http://', 'ws://');
    return `${wsUrl}/ws/notifications?token=${token}`;
  };

  // Load initial notifications - increased limit to get more history
  const loadNotifications = async () => {
    try {
      setLoading(true);
      const response = await api.get('/notifications?limit=100');
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error('Failed to load notifications:', error);
      // Don't clear notifications on error - keep existing ones
    } finally {
      setLoading(false);
    }
  };

  const loadFollowupAlerts = async () => {
    try {
      const response = await api.get('/followups/notifications');
      setFollowupAlerts(response.data.notifications || []);
      setFollowupCount(response.data.count || 0);
    } catch (error) {
      console.error('Failed to load followup alerts');
    }
  };

  // WebSocket connection management
  useEffect(() => {
    let ws = null;
    let heartbeatInterval = null;
    let reconnectTimeout = null;

    const connect = () => {
      const wsUrl = getWsUrl();
      if (!wsUrl) {
        console.log('No token available for WebSocket connection');
        return;
      }

      setWsStatus(WS_STATUS.CONNECTING);
      console.log('Connecting to WebSocket...');

      try {
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected');
          setWsStatus(WS_STATUS.CONNECTED);
          reconnectAttemptsRef.current = 0;
          
          // Start heartbeat
          heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping' }));
            }
          }, 30000);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'notification') {
              // New notification received
              const notification = data.data;
              setNotifications(prev => [notification, ...prev]);
              setUnreadCount(prev => prev + 1);
              
              // Show toast for new notification
              toast.info(notification.title, {
                description: notification.message,
                duration: 5000
              });
            } else if (data.type === 'connection') {
              console.log('WebSocket connection confirmed:', data);
            }
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setWsStatus(WS_STATUS.DISCONNECTED);
        };

        ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          setWsStatus(WS_STATUS.DISCONNECTED);
          
          // Clear heartbeat interval
          if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
          }

          // Attempt reconnection if not intentionally closed
          if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
            setWsStatus(WS_STATUS.RECONNECTING);
            const delay = baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
            
            reconnectTimeout = setTimeout(() => {
              reconnectAttemptsRef.current++;
              connect();
            }, delay);
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        setWsStatus(WS_STATUS.DISCONNECTED);
      }
    };

    // Initial data load
    loadNotifications();
    if (userRole === 'staff') {
      loadFollowupAlerts();
    }

    // Connect WebSocket
    const token = localStorage.getItem('token');
    if (token) {
      connect();
    }

    // Fallback polling when WebSocket is not connected
    const pollInterval = setInterval(() => {
      loadNotifications();
      if (userRole === 'staff') {
        loadFollowupAlerts();
      }
    }, 60000);

    // Cleanup
    return () => {
      clearInterval(pollInterval);
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        ws.close(1000, 'Component unmount');
      }
    };
  }, [userRole]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const markAsRead = async (notificationId) => {
    try {
      await api.patch(`/notifications/${notificationId}/read`);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      toast.error('Failed to mark as read');
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.patch('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark all as read');
    }
  };

  const deleteNotification = async (notificationId) => {
    try {
      await api.delete(`/notifications/${notificationId}`);
      const notification = notifications.find(n => n.id === notificationId);
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
      if (notification && !notification.read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
      toast.success('Notification deleted');
    } catch (error) {
      toast.error('Failed to delete notification');
    }
  };

  const deleteAllNotifications = async () => {
    if (!window.confirm('Are you sure you want to delete all notifications?')) {
      return;
    }
    try {
      // Delete all notifications one by one (or we could add a bulk delete endpoint)
      const deletePromises = notifications.map(n => 
        api.delete(`/notifications/${n.id}`).catch(() => null)
      );
      await Promise.all(deletePromises);
      setNotifications([]);
      setUnreadCount(0);
      toast.success('All notifications deleted');
    } catch (error) {
      toast.error('Failed to delete all notifications');
      // Reload to get accurate state
      loadNotifications();
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
    return date.toLocaleDateString();
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'request_approved':
      case 'reserved_approved':
        return <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center"><Check size={16} className="text-emerald-600 dark:text-emerald-400" /></div>;
      case 'request_rejected':
      case 'reserved_rejected':
        return <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center"><X size={16} className="text-red-600 dark:text-red-400" /></div>;
      case 'records_assigned':
        return <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center"><CheckCheck size={16} className="text-blue-600 dark:text-blue-400" /></div>;
      case 'new_reserved_request':
        return <div className="w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center"><Bell size={16} className="text-amber-600 dark:text-amber-400" /></div>;
      case 'followup_critical':
        return <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center"><AlertCircle size={16} className="text-red-600 dark:text-red-400" /></div>;
      case 'followup_high':
        return <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/50 flex items-center justify-center"><Clock size={16} className="text-orange-600 dark:text-orange-400" /></div>;
      default:
        return <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center"><Bell size={16} className="text-slate-600 dark:text-slate-400" /></div>;
    }
  };

  const getWsStatusIndicator = () => {
    switch (wsStatus) {
      case WS_STATUS.CONNECTED:
        return <Wifi size={12} className="text-emerald-500" title="Real-time connected" />;
      case WS_STATUS.CONNECTING:
      case WS_STATUS.RECONNECTING:
        return <Wifi size={12} className="text-amber-500 animate-pulse" title="Connecting..." />;
      default:
        return <WifiOff size={12} className="text-slate-400" title="Offline - using polling" />;
    }
  };

  const totalAlerts = unreadCount + followupCount;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
        data-testid="notification-bell"
      >
        <Bell size={20} />
        {totalAlerts > 0 && (
          <span className={`absolute -top-1 -right-1 w-5 h-5 text-white text-xs font-bold rounded-full flex items-center justify-center ${followupCount > 0 ? 'bg-red-500' : 'bg-indigo-500'}`}>
            {totalAlerts > 9 ? '9+' : totalAlerts}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 z-50 max-h-[70vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-slate-900 dark:text-white">Notifications</h3>
              {getWsStatusIndicator()}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-medium"
              >
                Mark all as read
              </button>
            )}
          </div>

          {/* Follow-up Alerts Section (for staff only) */}
          {followupAlerts.length > 0 && (
            <div className="border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30">
              <div className="px-4 py-2 border-b border-red-100 dark:border-red-800">
                <span className="text-xs font-semibold text-red-700 dark:text-red-400 uppercase tracking-wider">Follow-up Reminders</span>
              </div>
              {followupAlerts.map((alert, index) => (
                <div key={index} className="p-3 flex items-start gap-3">
                  {getNotificationIcon(alert.type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">{alert.title}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{alert.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Notifications List */}
          <div className="overflow-y-auto flex-1">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                <Bell className="mx-auto mb-2 text-slate-300 dark:text-slate-600" size={32} />
                <p>No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {notifications.map(notification => (
                  <div
                    key={notification.id}
                    className={`p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${!notification.read ? 'bg-indigo-50/50 dark:bg-indigo-900/20' : ''}`}
                  >
                    <div className="flex gap-3">
                      {getNotificationIcon(notification.type)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-sm ${!notification.read ? 'font-semibold text-slate-900 dark:text-white' : 'text-slate-700 dark:text-slate-300'}`}>
                            {notification.title}
                          </p>
                          <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">
                            {formatTime(notification.created_at)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                          {notification.message}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          {!notification.read && (
                            <button
                              onClick={() => markAsRead(notification.id)}
                              className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-medium"
                            >
                              Mark as read
                            </button>
                          )}
                          <button
                            onClick={() => deleteNotification(notification.id)}
                            className="text-xs text-slate-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
