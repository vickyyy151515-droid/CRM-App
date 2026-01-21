/**
 * AttendanceScanner - Phone page to scan QR codes for attendance
 * SIMPLIFIED APPROACH: Since Android cameras auto-detect QR codes,
 * staff can simply copy the QR text and paste it here.
 */
import { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw, LogIn, ClipboardPaste, ScanLine } from 'lucide-react';
import jsQR from 'jsqr';

// Standalone API
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
  const [qrCodeInput, setQrCodeInput] = useState('');
  
  // Refs
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);

  // Generate unique device ID
  useEffect(() => {
    let id = localStorage.getItem('attendance_device_id');
    if (!id) {
      id = 'DEV-' + Math.random().toString(36).substring(2, 15) + '-' + Date.now().toString(36);
      localStorage.setItem('attendance_device_id', id);
    }
    setDeviceId(id);
  }, []);

  // Check auth status
  useEffect(() => {
    const checkAuth = async () => {
      const savedToken = localStorage.getItem('scanner_token');
      if (savedToken) {
        try {
          const userData = await apiCall('GET', '/auth/me', null, savedToken);
          setUser(userData);
          setToken(savedToken);
          setIsLoggedIn(true);
          
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

  // Submit QR code (from paste or image scan)
  const submitQRCode = async (qrCode) => {
    if (!qrCode || !qrCode.trim()) {
      toast.error('Please enter a QR code');
      return;
    }
    
    const code = qrCode.trim();
    
    if (!code.startsWith('ATT-')) {
      setError('Invalid QR code. Must start with ATT-');
      toast.error('Invalid QR code format');
      return;
    }
    
    setProcessing(true);
    setError(null);
    
    try {
      toast.loading('Recording attendance...', { id: 'scan-loading' });
      
      const response = await apiCall('POST', '/attendance/scan', {
        qr_code: code,
        device_id: deviceId
      }, token);
      
      toast.dismiss('scan-loading');
      
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
      setQrCodeInput('');
      
    } catch (error) {
      toast.dismiss('scan-loading');
      setError(error.message);
      toast.error(error.message);
    } finally {
      setProcessing(false);
    }
  };

  // Handle paste button
  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.startsWith('ATT-')) {
        setQrCodeInput(text);
        toast.success('QR code pasted!');
        // Auto-submit after paste
        submitQRCode(text);
      } else if (text) {
        setQrCodeInput(text);
        toast.info('Text pasted. Tap Submit if this is the QR code.');
      } else {
        toast.error('Clipboard is empty');
      }
    } catch (error) {
      toast.error('Could not access clipboard. Please paste manually.');
    }
  };

  // Handle form submit
  const handleSubmit = (e) => {
    e.preventDefault();
    submitQRCode(qrCodeInput);
  };

  // Process captured image (fallback for phones that return images)
  const processImage = async (file) => {
    setProcessing(true);
    setError(null);
    
    try {
      const img = new Image();
      const imageUrl = URL.createObjectURL(file);
      
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = imageUrl;
      });
      
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
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
      
      const imageData = ctx.getImageData(0, 0, width, height);
      let qrCode = jsQR(imageData.data, width, height, { inversionAttempts: 'attemptBoth' });
      
      URL.revokeObjectURL(imageUrl);
      
      if (qrCode && qrCode.data) {
        submitQRCode(qrCode.data);
      } else {
        setError('No QR code found in image. Please try the paste method instead.');
        toast.error('No QR code detected');
        setProcessing(false);
      }
    } catch (error) {
      setError('Failed to process image');
      toast.error('Image processing failed');
      setProcessing(false);
    }
  };

  // Handle file input
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processImage(file);
    }
    e.target.value = '';
  };

  // Reset
  const handleReset = () => {
    setResult(null);
    setError(null);
    setQrCodeInput('');
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

        {/* Hidden elements */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />
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
              You can only register <span className="text-amber-400 font-bold">ONE phone</span>.
            </p>
            <button
              onClick={registerDevice}
              className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium"
            >
              Register This Phone
            </button>
          </div>
        )}

        {/* Main Scanner Interface */}
        {isLoggedIn && deviceRegistered && !result && (
          <div className="space-y-4">
            {/* User Info */}
            <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-emerald-400" size={18} />
                <span className="text-emerald-200">{user?.name} • Device Registered</span>
              </div>
            </div>

            {/* PASTE QR CODE - Primary Method */}
            <div className="bg-slate-800 rounded-xl p-6">
              <div className="text-center mb-4">
                <ScanLine size={48} className="text-indigo-400 mx-auto mb-2" />
                <h2 className="text-lg font-semibold">Enter QR Code</h2>
                <p className="text-slate-400 text-sm mt-1">
                  Scan QR on computer, then paste the code here
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="relative">
                  <input
                    type="text"
                    value={qrCodeInput}
                    onChange={(e) => setQrCodeInput(e.target.value)}
                    placeholder="ATT-xxxxx-xxxxx..."
                    className="w-full px-4 py-4 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 font-mono text-sm"
                  />
                </div>
                
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handlePaste}
                    className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium flex items-center justify-center gap-2"
                  >
                    <ClipboardPaste size={18} />
                    Paste
                  </button>
                  <button
                    type="submit"
                    disabled={processing || !qrCodeInput.trim()}
                    className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 rounded-lg font-medium flex items-center justify-center gap-2"
                  >
                    {processing ? (
                      <RefreshCw className="animate-spin" size={18} />
                    ) : (
                      <CheckCircle size={18} />
                    )}
                    Submit
                  </button>
                </div>
              </form>
            </div>

            {/* Alternative: Camera Capture */}
            <div className="bg-slate-800/50 rounded-xl p-4">
              <p className="text-sm text-slate-400 text-center mb-3">
                Or try taking a photo (works on some phones)
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={processing}
                className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm flex items-center justify-center gap-2"
              >
                <Camera size={18} />
                Open Camera
              </button>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={20} />
                  <div>
                    <p className="text-red-200 font-medium">Error</p>
                    <p className="text-red-300 text-sm mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Instructions */}
            <div className="bg-blue-900/30 border border-blue-700 rounded-xl p-4">
              <h3 className="font-semibold text-blue-200 mb-2">📋 How to check in:</h3>
              <ol className="text-sm text-blue-100 space-y-2">
                <li><span className="text-blue-400 font-bold">1.</span> Open CRM on computer → QR code appears</li>
                <li><span className="text-blue-400 font-bold">2.</span> Use your phone camera to scan the QR</li>
                <li><span className="text-blue-400 font-bold">3.</span> Your phone will show the QR text (starts with ATT-)</li>
                <li><span className="text-blue-400 font-bold">4.</span> Tap <span className="bg-blue-800 px-1 rounded">&quot;Copy text&quot;</span> on that screen</li>
                <li><span className="text-blue-400 font-bold">5.</span> Come back here → Tap <span className="bg-emerald-800 px-1 rounded">Paste</span></li>
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
          <p>Scanner v3.1</p>
        </div>
      </div>
    </div>
  );
}
