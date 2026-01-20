import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import StaffDashboard from './pages/StaffDashboard';
import BatchRecordsView from './components/BatchRecordsView';
import { Toaster, toast } from 'sonner';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  timeout: 30000, // 30 second timeout
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for global error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't show toast for canceled requests or auth errors (handled elsewhere)
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }
    
    // Service unavailable (503) - server is restarting or database issue
    if (error.response?.status === 503) {
      console.warn('Service temporarily unavailable, will retry...');
      toast.error('Service temporarily unavailable. Please wait a moment and try again.', {
        duration: 5000,
        id: 'service-unavailable' // Prevent duplicate toasts
      });
    }
    
    // Network error (no response from server)
    if (!error.response) {
      console.error('Network error:', error.message);
      // Don't show toast here - let individual components handle retry logic
    }
    
    return Promise.reject(error);
  }
);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastActivityTime, setLastActivityTime] = useState(Date.now());
  
  // Auto-logout after 1 hour (60 minutes) of inactivity
  const AUTO_LOGOUT_MS = 60 * 60 * 1000; // 1 hour in milliseconds
  const WARNING_BEFORE_LOGOUT_MS = 5 * 60 * 1000; // Show warning 5 minutes before logout
  
  // Heartbeat function to track user activity
  const sendHeartbeat = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        await api.post('/auth/heartbeat');
        setLastActivityTime(Date.now());
      } catch (error) {
        // Silently fail - don't disrupt user experience
        console.debug('Heartbeat failed:', error.message);
      }
    }
  }, []);
  
  // Force logout function
  const forceLogout = useCallback(async (reason = 'Session expired') => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.debug('Logout API call failed:', error.message);
    }
    localStorage.removeItem('token');
    setUser(null);
    toast.error(`${reason}. Please login again.`);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/auth/me')
        .then(res => {
          setUser(res.data);
          setLoading(false);
          setLastActivityTime(Date.now());
        })
        .catch(() => {
          localStorage.removeItem('token');
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);
  
  // Auto-logout check - runs every minute (only for staff users)
  useEffect(() => {
    // Only apply auto-logout to staff users
    if (!user || user.role !== 'staff') return;
    
    const checkInactivity = () => {
      const timeSinceActivity = Date.now() - lastActivityTime;
      
      // Check if session should be expired
      if (timeSinceActivity >= AUTO_LOGOUT_MS) {
        forceLogout('Session expired due to 1 hour of inactivity');
        return;
      }
      
      // Show warning 5 minutes before auto-logout
      const timeRemaining = AUTO_LOGOUT_MS - timeSinceActivity;
      if (timeRemaining <= WARNING_BEFORE_LOGOUT_MS && timeRemaining > WARNING_BEFORE_LOGOUT_MS - 60000) {
        const minutesRemaining = Math.ceil(timeRemaining / 60000);
        toast.warning(`Your session will expire in ${minutesRemaining} minutes due to inactivity. Move your mouse or click to stay logged in.`, {
          duration: 10000,
          id: 'session-warning' // Prevent duplicate toasts
        });
      }
    };
    
    // Check immediately and then every minute
    checkInactivity();
    const inactivityInterval = setInterval(checkInactivity, 60 * 1000);
    
    return () => clearInterval(inactivityInterval);
  }, [user, lastActivityTime, forceLogout, AUTO_LOGOUT_MS, WARNING_BEFORE_LOGOUT_MS]);

  // Send heartbeat every 2 minutes when user is logged in
  // Also send on meaningful user interactions (click, keypress) but NOT mousemove
  useEffect(() => {
    if (user) {
      // Send initial heartbeat
      sendHeartbeat();
      
      // Set up interval for periodic heartbeats (every 2 minutes)
      const heartbeatInterval = setInterval(sendHeartbeat, 2 * 60 * 1000); // 2 minutes
      
      // Track user activity on meaningful interactions only (not mousemove - too frequent)
      let activityTimeout;
      const handleActivity = () => {
        setLastActivityTime(Date.now()); // Update local activity time immediately
        // Debounce heartbeat to avoid flooding server
        if (activityTimeout) clearTimeout(activityTimeout);
        activityTimeout = setTimeout(sendHeartbeat, 2000); // 2 second debounce
      };
      
      // Only track clicks, keypresses, and scroll - NOT mousemove
      window.addEventListener('click', handleActivity);
      window.addEventListener('keypress', handleActivity);
      window.addEventListener('scroll', handleActivity);
      window.addEventListener('touchstart', handleActivity);
      
      // Handle browser/tab close - log out the user
      const handleBeforeUnload = () => {
        // Use sendBeacon for reliable delivery even when page is closing
        const token = localStorage.getItem('token');
        if (token) {
          const apiUrl = process.env.REACT_APP_BACKEND_URL || '';
          navigator.sendBeacon(
            `${apiUrl}/api/auth/logout-beacon`,
            JSON.stringify({ token })
          );
        }
      };
      
      window.addEventListener('beforeunload', handleBeforeUnload);
      
      return () => {
        clearInterval(heartbeatInterval);
        if (activityTimeout) clearTimeout(activityTimeout);
        window.removeEventListener('click', handleActivity);
        window.removeEventListener('keypress', handleActivity);
        window.removeEventListener('scroll', handleActivity);
        window.removeEventListener('touchstart', handleActivity);
        window.removeEventListener('beforeunload', handleBeforeUnload);
      };
    }
  }, [user, sendHeartbeat]);

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token);
    setUser(userData);
  };

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.debug('Logout API call failed:', error.message);
    }
    localStorage.removeItem('token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-slate-600">Loading...</div>
      </div>
    );
  }

  return (
    <ThemeProvider>
      <LanguageProvider>
        <div className="App min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors">
          <Toaster position="top-right" richColors />
          <BrowserRouter>
            <Routes>
              <Route
                path="/login"
                element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" replace />}
              />
              <Route
                path="/batch/:batchId"
                element={user ? <BatchRecordsView /> : <Navigate to="/login" replace />}
              />
              <Route
                path="/"
                element={
                  user ? (
                    (user.role === 'admin' || user.role === 'master_admin') ? (
                      <AdminDashboard user={user} onLogout={handleLogout} />
                    ) : (
                      <StaffDashboard user={user} onLogout={handleLogout} />
                    )
                  ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </BrowserRouter>
      </div>
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;