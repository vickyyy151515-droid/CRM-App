import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import StaffDashboard from './pages/StaffDashboard';
import { Toaster } from 'sonner';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Heartbeat function to track user activity
  const sendHeartbeat = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        await api.post('/auth/heartbeat');
      } catch (error) {
        // Silently fail - don't disrupt user experience
        console.debug('Heartbeat failed:', error.message);
      }
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/auth/me')
        .then(res => {
          setUser(res.data);
          setLoading(false);
        })
        .catch(() => {
          localStorage.removeItem('token');
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  // Send heartbeat every 2 minutes when user is logged in
  useEffect(() => {
    if (user) {
      // Send initial heartbeat
      sendHeartbeat();
      
      // Set up interval for periodic heartbeats
      const heartbeatInterval = setInterval(sendHeartbeat, 2 * 60 * 1000); // 2 minutes
      
      // Also send heartbeat on user activity (mouse move, key press, click)
      let activityTimeout;
      const handleActivity = () => {
        if (activityTimeout) clearTimeout(activityTimeout);
        activityTimeout = setTimeout(sendHeartbeat, 1000); // Debounce to 1 second
      };
      
      window.addEventListener('mousemove', handleActivity);
      window.addEventListener('keypress', handleActivity);
      window.addEventListener('click', handleActivity);
      
      return () => {
        clearInterval(heartbeatInterval);
        if (activityTimeout) clearTimeout(activityTimeout);
        window.removeEventListener('mousemove', handleActivity);
        window.removeEventListener('keypress', handleActivity);
        window.removeEventListener('click', handleActivity);
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
                element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" />}
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
                  <Navigate to="/login" />
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