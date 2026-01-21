/**
 * AttendanceScanner - Phone page to scan QR codes for attendance
 * Uses @zxing/library for reliable cross-platform QR scanning
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw, LogIn, StopCircle } from 'lucide-react';
import { BrowserMultiFormatReader, BarcodeFormat, DecodeHintType } from '@zxing/library';

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
  const [scanning, setScanning] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [scanStatus, setScanStatus] = useState('');
  
  // Refs
  const videoRef = useRef(null);
  const readerRef = useRef(null);
  const hasScannedRef = useRef(false);

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
        } catch (err) {
          localStorage.removeItem('scanner_token');
        }
      }
      setCheckingDevice(false);
    };
    checkAuth();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopScanner();
    };
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
    } catch (err) {
      setLoginError(err.message);
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
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Process detected QR code
  const processQRCode = useCallback(async (qrCode) => {
    if (hasScannedRef.current || processing) return;
    
    // Validate format
    if (!qrCode.startsWith('ATT-')) {
      toast.error('Invalid QR code format');
      return;
    }
    
    hasScannedRef.current = true;
    setProcessing(true);
    setScanStatus('Processing...');
    
    // Stop camera
    stopScanner();
    
    // Vibrate feedback
    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
    
    try {
      toast.loading('Recording attendance...', { id: 'scan-loading' });
      
      const response = await apiCall('POST', '/attendance/scan', {
        qr_code: qrCode,
        device_id: deviceId
      }, token);
      
      toast.dismiss('scan-loading');
      
      setResult({
        success: true,
        staffName: response.staff_name,
        checkInTime: response.check_in_time,
        isLate: response.is_late,
        lateMinutes: response.late_minutes,
        status: response.attendance_status
      });
      
      toast.success('Check-in successful!');
      
    } catch (err) {
      toast.dismiss('scan-loading');
      setError(err.message);
      setResult({ success: false, message: err.message });
      toast.error(err.message);
      hasScannedRef.current = false;
    } finally {
      setProcessing(false);
    }
  }, [deviceId, token, processing]);

  // Start scanner
  const startScanner = async () => {
    setError(null);
    setScanStatus('Starting camera...');
    hasScannedRef.current = false;
    
    try {
      // Configure hints for better QR detection
      const hints = new Map();
      hints.set(DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.QR_CODE]);
      hints.set(DecodeHintType.TRY_HARDER, true);
      
      const reader = new BrowserMultiFormatReader(hints);
      readerRef.current = reader;
      
      // Get available cameras
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      
      // Prefer back camera
      let selectedDeviceId = undefined;
      for (const device of videoDevices) {
        const label = device.label.toLowerCase();
        if (label.includes('back') || label.includes('rear') || label.includes('environment')) {
          selectedDeviceId = device.deviceId;
          break;
        }
      }
      // If no back camera found, use the last one (usually back on phones)
      if (!selectedDeviceId && videoDevices.length > 0) {
        selectedDeviceId = videoDevices[videoDevices.length - 1].deviceId;
      }
      
      setScanStatus('Camera starting...');
      setScanning(true);
      
      // Start continuous scanning
      await reader.decodeFromVideoDevice(
        selectedDeviceId,
        videoRef.current,
        (result, err) => {
          if (result) {
            const text = result.getText();
            console.log('QR Detected:', text);
            setScanStatus('QR Code found!');
            processQRCode(text);
          }
          if (err && err.name !== 'NotFoundException') {
            // Only log non-"not found" errors
            console.debug('Scan error:', err.message);
          }
        }
      );
      
      setScanStatus('Point camera at QR code');
      toast.success('Camera ready!');
      
    } catch (err) {
      console.error('Scanner error:', err);
      setScanning(false);
      
      let errorMsg = 'Could not start camera';
      if (err.name === 'NotAllowedError') {
        errorMsg = 'Camera permission denied. Please allow camera access.';
      } else if (err.name === 'NotFoundError') {
        errorMsg = 'No camera found on this device.';
      } else if (err.name === 'NotReadableError') {
        errorMsg = 'Camera is in use by another app.';
      }
      
      setError(errorMsg);
      toast.error(errorMsg);
    }
  };

  // Stop scanner
  const stopScanner = useCallback(() => {
    if (readerRef.current) {
      readerRef.current.reset();
      readerRef.current = null;
    }
    setScanning(false);
    setScanStatus('');
  }, []);

  // Reset for new scan
  const handleReset = () => {
    setResult(null);
    setError(null);
    hasScannedRef.current = false;
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
        <div className="text-center mb-4">
          <h1 className="text-2xl font-bold mb-1">📱 Attendance Scanner</h1>
          <p className="text-slate-400 text-sm">Scan QR code to check in</p>
        </div>

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

            {/* Video Preview */}
            <div className="bg-black rounded-xl overflow-hidden relative" style={{ aspectRatio: '4/3' }}>
              <video
                ref={videoRef}
                className="w-full h-full object-cover"
                playsInline
                muted
                autoPlay
              />
              
              {/* Scanning overlay */}
              {scanning && (
                <div className="absolute inset-0 pointer-events-none">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-48 h-48 border-2 border-green-400 rounded-lg relative">
                      <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-green-400" />
                      <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-green-400" />
                      <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-green-400" />
                      <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-green-400" />
                      <div className="absolute left-2 right-2 h-0.5 bg-red-500 top-1/2 animate-pulse" />
                    </div>
                  </div>
                </div>
              )}
              
              {/* Not scanning overlay */}
              {!scanning && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-800">
                  <div className="text-center">
                    <Camera size={48} className="text-slate-500 mx-auto mb-2" />
                    <p className="text-slate-400">Tap Start to scan</p>
                  </div>
                </div>
              )}
            </div>

            {/* Status */}
            {scanStatus && (
              <div className="bg-indigo-900/50 border border-indigo-500 rounded-lg p-3 text-center">
                <p className="text-indigo-200 text-sm flex items-center justify-center gap-2">
                  {scanning && <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />}
                  {scanStatus}
                </p>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-red-400 shrink-0" size={20} />
                  <p className="text-red-200 text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Action Button */}
            {!scanning ? (
              <button
                onClick={startScanner}
                disabled={processing}
                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 rounded-xl font-bold text-lg flex items-center justify-center gap-3"
              >
                <Camera size={24} />
                Start Camera
              </button>
            ) : (
              <button
                onClick={stopScanner}
                className="w-full py-4 bg-red-600 hover:bg-red-700 rounded-xl font-bold text-lg flex items-center justify-center gap-3"
              >
                <StopCircle size={24} />
                Stop Camera
              </button>
            )}

            {/* Manual Code Input - Backup Option */}
            <div className="bg-slate-800/50 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-2 text-center">
                Camera not working? Paste QR code text here:
              </p>
              <form onSubmit={(e) => {
                e.preventDefault();
                const input = e.target.elements.qrcode;
                if (input.value.trim()) {
                  processQRCode(input.value.trim());
                  input.value = '';
                }
              }} className="flex gap-2">
                <input
                  name="qrcode"
                  type="text"
                  placeholder="ATT-xxxxx..."
                  className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm font-mono"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium"
                >
                  Submit
                </button>
              </form>
            </div>

            {/* Instructions */}
            <div className="bg-slate-800 rounded-xl p-4 text-sm">
              <h3 className="font-semibold mb-2">Instructions:</h3>
              <ol className="text-slate-400 space-y-1">
                <li>1. Login to CRM on computer → QR appears</li>
                <li>2. Tap &quot;Start Camera&quot; above</li>
                <li>3. Point phone at QR code on screen</li>
                <li>4. Hold steady until detected</li>
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
          <p>Scanner v4.0 (ZXing)</p>
        </div>
      </div>
    </div>
  );
}
