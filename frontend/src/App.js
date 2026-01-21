import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import StaffDashboard from './pages/StaffDashboard';
import BatchRecordsView from './components/BatchRecordsView';
import AttendanceScanner from './pages/AttendanceScanner';
import AttendanceQRScreen from './components/AttendanceQRScreen';
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

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token);
    setUser(userData);
    // Reset attendance check for new login
    setAttendanceChecked(false);
  };

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.debug('Logout API call failed:', error.message);
    }
    localStorage.removeItem('token');
    setUser(null);
    setAttendanceChecked(false);
  };

  // State for attendance check (staff only)
  const [attendanceChecked, setAttendanceChecked] = useState(false);
  const [checkingAttendance, setCheckingAttendance] = useState(false);

  // Check attendance status for staff on login
  useEffect(() => {
    const checkAttendance = async () => {
      // Only check for staff users
      if (!user || user.role !== 'staff' || attendanceChecked) return;
      
      setCheckingAttendance(true);
      try {
        const response = await api.get('/attendance/check-today');
        if (response.data.checked_in) {
          setAttendanceChecked(true);
        }
      } catch (error) {
        // If endpoint fails, allow access anyway
        setAttendanceChecked(true);
      } finally {
        setCheckingAttendance(false);
      }
    };
    
    checkAttendance();
  }, [user, attendanceChecked]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-slate-600">Loading...</div>
      </div>
    );
  }

  // Show attendance QR screen for staff who haven't checked in
  const shouldShowAttendanceQR = user && user.role === 'staff' && !attendanceChecked && !checkingAttendance;

  return (
    <ThemeProvider>
      <LanguageProvider>
        <div className="App min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors">
          <Toaster position="top-right" richColors />
          <BrowserRouter>
            <Routes>
              {/* Public attendance scanner route */}
              <Route path="/attendance-scanner" element={<AttendanceScanner />} />
              
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
                    ) : shouldShowAttendanceQR ? (
                      <AttendanceQRScreen 
                        onComplete={() => setAttendanceChecked(true)} 
                        userName={user.name}
                        onLogout={handleLogout}
                      />
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