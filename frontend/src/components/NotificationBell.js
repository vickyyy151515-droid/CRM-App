import { useState, useEffect, useRef } from 'react';
import { api } from '../App';
import { Bell, Check, CheckCheck, Trash2, X, AlertCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';

export default function NotificationBell({ userRole }) {
  const [notifications, setNotifications] = useState([]);
  const [followupAlerts, setFollowupAlerts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [followupCount, setFollowupCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);
  const prevUnreadCount = useRef(0);

  useEffect(() => {
    loadNotifications();
    if (userRole === 'staff') {
      loadFollowupAlerts();
    }
    // Poll for new notifications every 30 seconds
    const interval = setInterval(() => {
      loadNotifications();
      if (userRole === 'staff') {
        loadFollowupAlerts();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [userRole]);

  useEffect(() => {
    // Close dropdown when clicking outside
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    // Show toast for new notifications
    if (unreadCount > prevUnreadCount.current && prevUnreadCount.current > 0) {
      const newCount = unreadCount - prevUnreadCount.current;
      toast.info(`You have ${newCount} new notification${newCount > 1 ? 's' : ''}`);
    }
    prevUnreadCount.current = unreadCount;
  }, [unreadCount]);

  const loadNotifications = async () => {
    try {
      const response = await api.get('/notifications?limit=20');
      setNotifications(response.data.notifications);
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('Failed to load notifications');
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
    } catch (error) {
      toast.error('Failed to delete notification');
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
        return <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center"><Check size={16} className="text-emerald-600" /></div>;
      case 'request_rejected':
      case 'reserved_rejected':
        return <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center"><X size={16} className="text-red-600" /></div>;
      case 'records_assigned':
        return <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center"><CheckCheck size={16} className="text-blue-600" /></div>;
      case 'new_reserved_request':
        return <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center"><Bell size={16} className="text-amber-600" /></div>;
      case 'followup_critical':
        return <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center"><AlertCircle size={16} className="text-red-600" /></div>;
      case 'followup_high':
        return <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center"><Clock size={16} className="text-orange-600" /></div>;
      default:
        return <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center"><Bell size={16} className="text-slate-600" /></div>;
    }
  };

  const totalAlerts = unreadCount + followupCount;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
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
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-lg border border-slate-200 z-50 max-h-[70vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <h3 className="font-semibold text-slate-900">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Mark all as read
              </button>
            )}
          </div>

          {/* Follow-up Alerts Section (for staff only) */}
          {followupAlerts.length > 0 && (
            <div className="border-b border-slate-200 bg-gradient-to-r from-red-50 to-orange-50">
              <div className="px-4 py-2 border-b border-red-100">
                <span className="text-xs font-semibold text-red-700 uppercase tracking-wider">Follow-up Reminders</span>
              </div>
              {followupAlerts.map((alert, index) => (
                <div key={index} className="p-3 flex items-start gap-3">
                  {getNotificationIcon(alert.type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{alert.title}</p>
                    <p className="text-sm text-slate-600">{alert.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Notifications List */}
          <div className="overflow-y-auto flex-1">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <Bell className="mx-auto mb-2 text-slate-300" size={32} />
                <p>No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {notifications.map(notification => (
                  <div
                    key={notification.id}
                    className={`p-4 hover:bg-slate-50 transition-colors ${!notification.read ? 'bg-indigo-50/50' : ''}`}
                  >
                    <div className="flex gap-3">
                      {getNotificationIcon(notification.type)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-sm ${!notification.read ? 'font-semibold text-slate-900' : 'text-slate-700'}`}>
                            {notification.title}
                          </p>
                          <span className="text-xs text-slate-400 whitespace-nowrap">
                            {formatTime(notification.created_at)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">
                          {notification.message}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          {!notification.read && (
                            <button
                              onClick={() => markAsRead(notification.id)}
                              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                            >
                              Mark as read
                            </button>
                          )}
                          <button
                            onClick={() => deleteNotification(notification.id)}
                            className="text-xs text-slate-400 hover:text-red-600"
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
