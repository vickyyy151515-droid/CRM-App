/**
 * AttendanceScanner - Phone page to scan QR codes for attendance
 * Uses NATIVE CAMERA CAPTURE for maximum compatibility on all devices
 * Works on: iPhone, ALL Android phones, ALL browsers including Telegram's browser
 */
import { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw, LogIn } from 'lucide-react';
import jsQR from 'jsqr';

// Standalone API - doesn't use the main app's api instance
const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

async function apiCall(method, endpoint, data = null, token = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  
  const options = { method, headers };
  if (data) options.body = JSON.stringify(data);
  
  const response = await fetch(`${API_URL}${endpoint}`, options);
  const result = await response.json();
  
  if (!response.ok) {
    throw new Error(result.detail || 'Request failed');
  }
  return result;
}

export default function AttendanceScanner() {
  // Auth state
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [token, setToken] = useState(null);
  
  // Device state
  const [deviceId, setDeviceId] = useState(null);
  const [deviceRegistered, setDeviceRegistered] = useState(false);
  const [checkingDevice, setCheckingDevice] = useState(true);
  
  // Scanner state
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  // Refs
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);

  // Generate unique device ID on mount
  useEffect(() => {
    let id = localStorage.getItem('attendance_device_id');
    if (!id) {
      id = 'DEV-' + Math.random().toString(36).substring(2, 15) + '-' + Date.now().toString(36);
      localStorage.setItem('attendance_device_id', id);
    }
    setDeviceId(id);
  }, []);

  // Check auth status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const savedToken = localStorage.getItem('scanner_token');
      if (savedToken) {
        try {
          const userData = await apiCall('GET', '/auth/me', null, savedToken);
          setUser(userData);
          setToken(savedToken);
          setIsLoggedIn(true);
          
          // Check device status
          const deviceStatus = await apiCall('GET', '/attendance/device-status', null, savedToken);
          setDeviceRegistered(deviceStatus.has_device);
        } catch (error) {
          localStorage.removeItem('scanner_token');
        }
      }
      setCheckingDevice(false);
    };
    checkAuth();
  }, []);

  // Handle login
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    
    try {
      const response = await apiCall('POST', '/auth/login', {
        email: loginEmail,
        password: loginPassword
      });
      
      localStorage.setItem('scanner_token', response.token);
      setToken(response.token);
      setUser(response.user);
      setIsLoggedIn(true);
      
      // Check device status
      const deviceStatus = await apiCall('GET', '/attendance/device-status', null, response.token);
      setDeviceRegistered(deviceStatus.has_device);
      
      toast.success('Login successful!');
    } catch (error) {
      setLoginError(error.message);
    } finally {
      setLoginLoading(false);
    }
  };

  // Register device
  const registerDevice = async () => {
    try {
      const deviceName = /iPhone|iPad|iPod/i.test(navigator.userAgent) ? 'iPhone' : 
                         /Android/i.test(navigator.userAgent) ? 'Android' : 'Mobile';
      
      await apiCall('POST', '/attendance/register-device', {
        device_id: deviceId,
        device_name: deviceName
      }, token);
      
      setDeviceRegistered(true);
      toast.success('Device registered successfully!');
    } catch (error) {
      toast.error(error.message);
    }
  };

  // Process captured image for QR code
  const processImage = async (file) => {
    setProcessing(true);
    setError(null);
    
    try {
      // Create image from file
      const img = new Image();
      const imageUrl = URL.createObjectURL(file);
      
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = imageUrl;
      });
      
      // Draw to canvas
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      // Use reasonable size for processing
      const maxSize = 1024;
      let width = img.width;
      let height = img.height;
      
      if (width > maxSize || height > maxSize) {
        if (width > height) {
          height = (height / width) * maxSize;
          width = maxSize;
        } else {
          width = (width / height) * maxSize;
          height = maxSize;
        }
      }
      
      canvas.width = width;
      canvas.height = height;
      ctx.drawImage(img, 0, 0, width, height);
      
      // Get image data for QR detection
      const imageData = ctx.getImageData(0, 0, width, height);
      
      // Try to detect QR code with multiple attempts
      let qrCode = jsQR(imageData.data, width, height, { inversionAttempts: 'attemptBoth' });
      
      URL.revokeObjectURL(imageUrl);
      
      if (!qrCode || !qrCode.data) {
        throw new Error('No QR code found in image. Please try again with a clearer photo.');
      }
      
      const qrData = qrCode.data;
      
      // Validate QR format
      if (!qrData.startsWith('ATT-')) {
        throw new Error('Invalid QR code. Please scan the attendance QR from your computer.');
      }
      
      // Send to backend
      toast.loading('Recording attendance...', { id: 'scan-loading' });
      
      const response = await apiCall('POST', '/attendance/scan', {
        qr_code: qrData,
        device_id: deviceId
      }, token);
      
      toast.dismiss('scan-loading');
      
      // Vibrate on success
      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
      
      setResult({
        success: true,
        staffName: response.staff_name,
        checkInTime: response.check_in_time,
        isLate: response.is_late,
        lateMinutes: response.late_minutes,
        status: response.attendance_status
      });
      
      toast.success('Check-in successful!');
      
    } catch (error) {
      toast.dismiss('scan-loading');
      setError(error.message);
      toast.error(error.message);
    } finally {
      setProcessing(false);
    }
  };

  // Handle file input change
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processImage(file);
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  };

  // Trigger camera
  const openCamera = () => {
    fileInputRef.current?.click();
  };

  // Reset for new scan
  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  // Loading state
  if (checkingDevice) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="text-center text-white">
          <RefreshCw className="animate-spin mx-auto mb-3" size={32} />
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold mb-1">📱 Attendance Scanner</h1>
          <p className="text-slate-400 text-sm">Scan QR code to check in</p>
        </div>

        {/* Hidden canvas for image processing */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* Hidden file input for camera capture */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        {/* Login Form */}
        {!isLoggedIn && (
          <div className="bg-slate-800 rounded-xl p-6">
            <div className="text-center mb-4">
              <LogIn className="w-12 h-12 text-indigo-400 mx-auto mb-2" />
              <h2 className="text-lg font-semibold">Login Required</h2>
              <p className="text-slate-400 text-sm">Enter your CRM credentials</p>
            </div>
            
            <form onSubmit={handleLogin} className="space-y-4">
              <input
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="Email"
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400"
                required
                autoComplete="email"
              />
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Password"
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400"
                required
                autoComplete="current-password"
              />
              
              {loginError && (
                <div className="text-red-400 text-sm text-center bg-red-900/30 p-2 rounded">
                  {loginError}
                </div>
              )}
              
              <button
                type="submit"
                disabled={loginLoading}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 rounded-lg font-medium flex items-center justify-center gap-2"
              >
                {loginLoading ? (
                  <><RefreshCw className="animate-spin" size={18} /> Logging in...</>
                ) : (
                  <><LogIn size={18} /> Login</>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Device Registration */}
        {isLoggedIn && !deviceRegistered && !result && (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <Smartphone className="w-16 h-16 text-amber-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Register This Device</h2>
            <p className="text-slate-400 text-sm mb-6">
              This phone needs to be registered for attendance scanning.
              <br />
              <span className="text-amber-400">You can only register ONE device.</span>
            </p>
            <button
              onClick={registerDevice}
              className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium"
            >
              Register This Phone
            </button>
          </div>
        )}

        {/* Scanner Interface */}
        {isLoggedIn && deviceRegistered && !result && (
          <div className="space-y-4">
            {/* User Info */}
            <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-emerald-400" size={18} />
                <span className="text-emerald-200">{user?.name} • Device Registered</span>
              </div>
            </div>

            {/* Camera Button */}
            <div className="bg-slate-800 rounded-xl p-8 text-center">
              <Camera size={64} className="text-indigo-400 mx-auto mb-4" />
              <p className="text-slate-300 mb-6">
                Take a photo of the QR code on your computer screen
              </p>
              
              <button
                onClick={openCamera}
                disabled={processing}
                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 rounded-xl font-bold text-lg flex items-center justify-center gap-3"
              >
                {processing ? (
                  <><RefreshCw className="animate-spin" size={24} /> Processing...</>
                ) : (
                  <><Camera size={24} /> Open Camera</>
                )}
              </button>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={20} />
                  <div>
                    <p className="text-red-200 font-medium">Scan Failed</p>
                    <p className="text-red-300 text-sm mt-1">{error}</p>
                  </div>
                </div>
                <button
                  onClick={() => setError(null)}
                  className="mt-3 w-full py-2 bg-red-800 hover:bg-red-700 rounded-lg text-sm"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Instructions */}
            <div className="bg-slate-800 rounded-xl p-4">
              <h3 className="font-semibold mb-2">Instructions:</h3>
              <ol className="text-sm text-slate-400 space-y-1">
                <li>1. Log in to CRM on your computer</li>
                <li>2. A QR code will appear on screen</li>
                <li>3. Tap &quot;Open Camera&quot; above</li>
                <li>4. Take a clear photo of the QR</li>
                <li>5. Your attendance will be recorded!</li>
              </ol>
            </div>
          </div>
        )}

        {/* Result Screen */}
        {result && (
          <div className={`rounded-xl p-6 text-center ${
            result.success ? 'bg-emerald-900/50 border-2 border-emerald-500' : 'bg-red-900/50 border-2 border-red-500'
          }`}>
            {result.success ? (
              <>
                <CheckCircle className="w-20 h-20 text-emerald-400 mx-auto mb-4" />
                <h2 className="text-2xl font-bold mb-2">Check-in Successful!</h2>
                <p className="text-emerald-200 text-lg mb-1">{result.staffName}</p>
                <p className="text-slate-300 mb-4">
                  Checked in at <span className="font-mono font-bold">{result.checkInTime}</span>
                </p>
                <div className={`inline-block px-4 py-2 rounded-full text-sm font-medium ${
                  result.isLate ? 'bg-amber-600' : 'bg-emerald-600'
                }`}>
                  {result.isLate ? `Late by ${result.lateMinutes} minutes` : '✓ On Time'}
                </div>
              </>
            ) : (
              <>
                <XCircle className="w-20 h-20 text-red-400 mx-auto mb-4" />
                <h2 className="text-2xl font-bold mb-2">Check-in Failed</h2>
                <p className="text-red-200">{result.message}</p>
              </>
            )}
            
            <button
              onClick={handleReset}
              className="mt-6 px-8 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium"
            >
              Done
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-6 text-xs text-slate-600">
          <p>Device ID: {deviceId?.substring(0, 12)}...</p>
          <p className="mt-1">Scanner v3.0</p>
        </div>
      </div>
    </div>
  );
}
