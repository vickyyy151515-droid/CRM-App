import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw } from 'lucide-react';
import { Html5Qrcode } from 'html5-qrcode';

export default function AttendanceScanner() {
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [deviceToken, setDeviceToken] = useState(null);
  const [deviceRegistered, setDeviceRegistered] = useState(false);
  const [checkingDevice, setCheckingDevice] = useState(true);
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [scannerStatus, setScannerStatus] = useState('idle');
  const scannerRef = useRef(null);
  const hasScannedRef = useRef(false);

  // Generate or retrieve device token
  useEffect(() => {
    let token = localStorage.getItem('attendance_device_token');
    if (!token) {
      token = `DEV-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('attendance_device_token', token);
    }
    setDeviceToken(token);
  }, []);

  // Check auth status
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          setIsLoggedIn(true);
          
          const deviceResponse = await api.get('/attendance/device-status');
          setDeviceRegistered(deviceResponse.data.has_device);
        } catch (error) {
          setIsLoggedIn(false);
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

  const stopScanner = useCallback(async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
      } catch (e) {
        // Ignore
      }
      scannerRef.current = null;
    }
    setScanning(false);
    setScannerStatus('idle');
  }, []);

  const handleQRDetected = useCallback(async (decodedText) => {
    // Prevent multiple scans
    if (hasScannedRef.current) return;
    hasScannedRef.current = true;
    
    console.log('QR Code detected:', decodedText);
    setScannerStatus('processing');
    
    // Stop scanner
    await stopScanner();
    
    // Validate QR format
    if (!decodedText.startsWith('ATT-')) {
      setError('Invalid QR code. Please scan the attendance QR from your computer.');
      setScannerStatus('idle');
      hasScannedRef.current = false;
      return;
    }

    try {
      toast.loading('Recording attendance...');
      
      const response = await api.post('/attendance/scan', {
        qr_code: decodedText,
        device_token: deviceToken
      });

      toast.dismiss();
      
      setResult({
        success: true,
        message: response.data.message,
        status: response.data.attendance_status,
        time: response.data.check_in_time,
        staffName: response.data.staff_name
      });
      
      toast.success('Check-in successful!');
      
    } catch (error) {
      toast.dismiss();
      const errorMsg = error.response?.data?.detail || 'Failed to check in';
      setError(errorMsg);
      setResult({ success: false, message: errorMsg });
      toast.error(errorMsg);
    }
    
    setScannerStatus('idle');
  }, [deviceToken, stopScanner]);

  const startScanner = async () => {
    setError(null);
    setScannerStatus('starting');
    hasScannedRef.current = false;
    
    // Wait for element to be ready
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const element = document.getElementById('qr-reader-box');
    if (!element) {
      setError('Scanner element not found. Please refresh the page.');
      setScannerStatus('idle');
      return;
    }

    try {
      const html5QrCode = new Html5Qrcode("qr-reader-box");
      scannerRef.current = html5QrCode;

      const config = { 
        fps: 10, 
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0,
        disableFlip: false
      };

      // Get available cameras
      let cameraId = null;
      try {
        const cameras = await Html5Qrcode.getCameras();
        console.log('Available cameras:', cameras);
        
        if (cameras && cameras.length > 0) {
          // Prefer back camera
          const backCamera = cameras.find(c => 
            c.label.toLowerCase().includes('back') || 
            c.label.toLowerCase().includes('rear') ||
            c.label.toLowerCase().includes('environment')
          );
          cameraId = backCamera ? backCamera.id : cameras[cameras.length - 1].id;
        }
      } catch (e) {
        console.log('Could not enumerate cameras:', e);
      }

      // Start with camera
      if (cameraId) {
        await html5QrCode.start(
          cameraId,
          config,
          handleQRDetected,
          () => {} // Ignore scan errors
        );
      } else {
        // Fallback to facingMode
        await html5QrCode.start(
          { facingMode: "environment" },
          config,
          handleQRDetected,
          () => {}
        );
      }

      setScanning(true);
      setScannerStatus('scanning');
      toast.success('Camera ready! Point at QR code.');
      
    } catch (err) {
      console.error('Scanner error:', err);
      let errorMsg = 'Could not start camera.';
      
      if (err.message?.includes('NotAllowedError') || err.message?.includes('Permission')) {
        errorMsg = 'Camera permission denied. Please allow camera access and try again.';
      } else if (err.message?.includes('NotFoundError')) {
        errorMsg = 'No camera found on this device.';
      } else if (err.message?.includes('NotReadableError')) {
        errorMsg = 'Camera is in use by another app. Please close other apps using the camera.';
      }
      
      setError(errorMsg);
      setScannerStatus('idle');
    }
  };

  const registerDevice = async () => {
    if (!isLoggedIn) {
      toast.error('Please log in first');
      return;
    }

    try {
      const deviceName = /iPhone|iPad|iPod/.test(navigator.userAgent) ? 'iPhone' : 
                         /Android/.test(navigator.userAgent) ? 'Android' : 'Mobile';
      
      await api.post('/attendance/register-device', {
        device_token: deviceToken,
        device_name: deviceName
      });
      
      setDeviceRegistered(true);
      toast.success('Device registered successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    }
  };

  const resetScanner = () => {
    setResult(null);
    setError(null);
    setScannerStatus('idle');
    hasScannedRef.current = false;
  };

  if (checkingDevice) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <RefreshCw className="animate-spin text-white" size={40} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="text-center mb-4 pt-2">
          <div className="w-12 h-12 bg-indigo-600 rounded-full flex items-center justify-center mx-auto mb-2">
            <Smartphone size={24} />
          </div>
          <h1 className="text-lg font-bold">Attendance Scanner</h1>
        </div>

        {/* Not Logged In */}
        {!isLoggedIn && (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <p className="text-slate-400 mb-4">Please log in first</p>
            <a href="/" className="inline-block px-6 py-3 bg-indigo-600 rounded-lg font-medium">
              Go to Login
            </a>
          </div>
        )}

        {/* Device Not Registered */}
        {isLoggedIn && !deviceRegistered && (
          <div className="bg-amber-900/50 border border-amber-500 rounded-xl p-4 mb-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-amber-400 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-amber-200">Device Not Registered</p>
                <p className="text-sm text-amber-300 mt-1">Register this phone first.</p>
                <button
                  onClick={registerDevice}
                  className="mt-3 px-4 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-sm font-medium"
                >
                  Register This Device
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Device Registered */}
        {isLoggedIn && deviceRegistered && !result && (
          <>
            <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-3 mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-emerald-400" size={18} />
                <span className="text-emerald-200 text-sm">Device registered • {user?.name}</span>
              </div>
            </div>

            {/* Scanner Container - ALWAYS VISIBLE when device registered */}
            <div className="bg-slate-800 rounded-xl overflow-hidden mb-4">
              {/* This div must always exist for html5-qrcode */}
              <div 
                id="qr-reader-box" 
                style={{ 
                  width: '100%', 
                  minHeight: '280px',
                  background: '#000'
                }}
              />
              
              {/* Overlay when not scanning */}
              {!scanning && scannerStatus !== 'starting' && (
                <div 
                  className="flex flex-col items-center justify-center p-8"
                  style={{ marginTop: '-280px', minHeight: '280px', background: 'rgba(30,41,59,0.95)' }}
                >
                  <Camera size={40} className="text-slate-500 mb-3" />
                  <p className="text-slate-400 text-sm text-center">
                    Tap button below to start camera
                  </p>
                </div>
              )}
              
              {/* Starting indicator */}
              {scannerStatus === 'starting' && (
                <div 
                  className="flex flex-col items-center justify-center p-8"
                  style={{ marginTop: '-280px', minHeight: '280px', background: 'rgba(30,41,59,0.95)' }}
                >
                  <RefreshCw size={40} className="text-indigo-400 mb-3 animate-spin" />
                  <p className="text-indigo-300 text-sm">Starting camera...</p>
                </div>
              )}
            </div>

            {/* Scanning indicator */}
            {scanning && (
              <div className="bg-indigo-900/50 border border-indigo-500 rounded-lg p-3 mb-4">
                <div className="flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  <span className="text-indigo-200 text-sm">
                    {scannerStatus === 'processing' ? 'Processing...' : 'Point camera at QR code'}
                  </span>
                </div>
              </div>
            )}

            {/* Control Button */}
            {!scanning ? (
              <button
                onClick={startScanner}
                disabled={scannerStatus === 'starting'}
                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 rounded-xl font-medium flex items-center justify-center gap-2"
              >
                {scannerStatus === 'starting' ? (
                  <><RefreshCw className="animate-spin" size={20} /> Starting...</>
                ) : (
                  <><Camera size={20} /> Start Camera</>
                )}
              </button>
            ) : (
              <button
                onClick={stopScanner}
                className="w-full py-4 bg-red-600 hover:bg-red-700 rounded-xl font-medium"
              >
                Stop Camera
              </button>
            )}
          </>
        )}

        {/* Error */}
        {error && !result && (
          <div className="bg-red-900/50 border border-red-500 rounded-xl p-4 mt-4">
            <div className="flex items-start gap-3">
              <XCircle className="text-red-400 mt-0.5" size={20} />
              <div className="flex-1">
                <p className="text-red-200 text-sm">{error}</p>
                <button
                  onClick={resetScanner}
                  className="mt-2 px-4 py-2 bg-red-600 rounded-lg text-sm"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className={`rounded-xl p-6 mt-4 ${
            result.success ? 'bg-emerald-900/50 border border-emerald-500' : 'bg-red-900/50 border border-red-500'
          }`}>
            <div className="text-center">
              {result.success ? (
                <>
                  <CheckCircle size={56} className="text-emerald-400 mx-auto mb-3" />
                  <h2 className="text-xl font-bold text-emerald-200">Check-in Successful!</h2>
                  <p className="text-emerald-300 mt-1">{result.staffName}</p>
                  <div className="mt-3 p-3 bg-emerald-800/50 rounded-lg">
                    <p className="text-emerald-300">Time: {result.time}</p>
                    <p className={`text-lg font-bold mt-1 ${
                      result.status === 'on_time' ? 'text-emerald-300' : 'text-amber-400'
                    }`}>
                      {result.status === 'on_time' ? '✓ ON TIME' : '⚠ LATE'}
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <XCircle size={56} className="text-red-400 mx-auto mb-3" />
                  <h2 className="text-xl font-bold text-red-200">Failed</h2>
                  <p className="text-red-300 mt-1">{result.message}</p>
                </>
              )}
              <button
                onClick={resetScanner}
                className="mt-4 w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg"
              >
                Scan Again
              </button>
            </div>
          </div>
        )}

        {/* Instructions */}
        {isLoggedIn && deviceRegistered && !result && (
          <div className="bg-slate-800 rounded-xl p-4 mt-4">
            <p className="font-medium text-sm mb-2">Instructions:</p>
            <ol className="text-xs text-slate-400 space-y-1">
              <li>1. Log in on office computer → QR shows</li>
              <li>2. Tap "Start Camera" above</li>
              <li>3. Point phone at QR code</li>
              <li>4. Wait for success message</li>
            </ol>
          </div>
        )}

        <p className="text-center text-xs text-slate-600 mt-4">
          Device: {deviceToken?.slice(-8)}
        </p>
      </div>
    </div>
  );
}
