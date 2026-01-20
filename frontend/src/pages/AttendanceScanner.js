import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw, Keyboard, Bug } from 'lucide-react';
import { Html5Qrcode, Html5QrcodeScanner } from 'html5-qrcode';

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
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualCode, setManualCode] = useState('');
  const [debugInfo, setDebugInfo] = useState('');
  const [debugLogs, setDebugLogs] = useState([]);
  const [showDebug, setShowDebug] = useState(false);
  const [scanCount, setScanCount] = useState(0);
  const scannerRef = useRef(null);
  const hasScannedRef = useRef(false);
  const mountedRef = useRef(true);

  // Add debug log helper
  const addDebugLog = useCallback((message) => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[Scanner ${timestamp}]`, message);
    setDebugLogs(prev => [...prev.slice(-20), `${timestamp}: ${message}`]);
  }, []);

  // Generate or retrieve device token
  useEffect(() => {
    let token = localStorage.getItem('attendance_device_token');
    if (!token) {
      token = `DEV-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('attendance_device_token', token);
    }
    setDeviceToken(token);
    addDebugLog(`Device token: ${token.slice(-8)}`);
  }, [addDebugLog]);

  // Check auth status
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          setIsLoggedIn(true);
          addDebugLog(`Logged in as: ${response.data.name}`);
          
          const deviceResponse = await api.get('/attendance/device-status');
          setDeviceRegistered(deviceResponse.data.has_device);
          addDebugLog(`Device registered: ${deviceResponse.data.has_device}`);
        } catch (error) {
          setIsLoggedIn(false);
          addDebugLog(`Auth check failed: ${error.message}`);
        }
      }
      setCheckingDevice(false);
    };
    checkAuth();
  }, [addDebugLog]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (scannerRef.current) {
        try {
          scannerRef.current.stop().catch(() => {});
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    };
  }, []);

  const stopScanner = useCallback(async () => {
    addDebugLog('Stopping scanner...');
    if (scannerRef.current) {
      try {
        const state = scannerRef.current.getState();
        addDebugLog(`Scanner state before stop: ${state}`);
        if (state === 2) { // SCANNING state
          await scannerRef.current.stop();
          addDebugLog('Scanner stopped successfully');
        }
      } catch (e) {
        addDebugLog(`Stop error (ignoring): ${e.message}`);
      }
      scannerRef.current = null;
    }
    if (mountedRef.current) {
      setScanning(false);
      setScannerStatus('idle');
    }
  }, [addDebugLog]);

  const handleQRDetected = useCallback(async (decodedText, decodedResult) => {
    // Prevent multiple scans
    if (hasScannedRef.current) {
      addDebugLog('Ignoring duplicate scan');
      return;
    }
    
    addDebugLog(`*** QR DETECTED: ${decodedText.substring(0, 30)}...`);
    addDebugLog(`Format: ${decodedResult?.result?.format?.formatName || 'unknown'}`);
    
    // IMPORTANT: Show immediate feedback
    toast.success(`QR Detected! Processing...`, { duration: 2000 });
    
    hasScannedRef.current = true;
    setScannerStatus('processing');
    
    // Stop scanner first
    await stopScanner();
    
    // Validate QR format
    if (!decodedText.startsWith('ATT-')) {
      addDebugLog('Invalid QR format - not ATT- prefix');
      setError('Invalid QR code. Please scan the attendance QR from your computer.');
      setScannerStatus('idle');
      hasScannedRef.current = false;
      return;
    }

    try {
      addDebugLog('Sending attendance scan API request...');
      toast.loading('Recording attendance...', { id: 'attendance-loading' });
      
      const response = await api.post('/attendance/scan', {
        qr_code: decodedText,
        device_token: deviceToken
      });

      toast.dismiss('attendance-loading');
      addDebugLog(`API response: ${JSON.stringify(response.data)}`);
      
      setResult({
        success: true,
        message: response.data.message,
        status: response.data.attendance_status,
        time: response.data.check_in_time,
        staffName: response.data.staff_name
      });
      
      toast.success('Check-in successful!');
      
    } catch (error) {
      toast.dismiss('attendance-loading');
      const errorMsg = error.response?.data?.detail || 'Failed to check in';
      addDebugLog(`API error: ${errorMsg}`);
      setError(errorMsg);
      setResult({ success: false, message: errorMsg });
      toast.error(errorMsg);
    }
    
    setScannerStatus('idle');
  }, [deviceToken, stopScanner, addDebugLog]);

  const startScanner = async () => {
    setError(null);
    setScannerStatus('starting');
    hasScannedRef.current = false;
    setScanCount(0);
    addDebugLog('Starting scanner...');
    
    // Cleanup any existing scanner
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
      } catch (e) {
        // Ignore cleanup errors
      }
      scannerRef.current = null;
    }
    
    // Wait for DOM to be ready
    await new Promise(resolve => setTimeout(resolve, 200));
    
    const element = document.getElementById('qr-reader-box');
    if (!element) {
      addDebugLog('ERROR: Scanner element not found');
      setError('Scanner element not found. Please refresh the page.');
      setScannerStatus('idle');
      return;
    }
    
    addDebugLog(`Element found, dimensions: ${element.offsetWidth}x${element.offsetHeight}`);

    try {
      const html5QrCode = new Html5Qrcode("qr-reader-box", { 
        verbose: false
      });
      scannerRef.current = html5QrCode;
      addDebugLog('Html5Qrcode instance created');

      // Simpler config for better mobile compatibility
      const config = { 
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0,
        disableFlip: false
      };

      // Get available cameras
      let cameraConfig;
      try {
        addDebugLog('Enumerating cameras...');
        const cameras = await Html5Qrcode.getCameras();
        addDebugLog(`Found ${cameras.length} cameras: ${cameras.map(c => c.label || c.id).join(', ')}`);
        
        if (cameras && cameras.length > 0) {
          // Prefer back camera
          const backCamera = cameras.find(c => {
            const label = (c.label || '').toLowerCase();
            return label.includes('back') || label.includes('rear') || label.includes('environment');
          });
          
          if (backCamera) {
            cameraConfig = backCamera.id;
            addDebugLog(`Using back camera: ${backCamera.label || backCamera.id}`);
          } else {
            // Use last camera (usually back camera on phones)
            cameraConfig = cameras[cameras.length - 1].id;
            addDebugLog(`Using camera: ${cameras[cameras.length - 1].label || cameraConfig}`);
          }
        } else {
          // No cameras enumerated, use facingMode
          cameraConfig = { facingMode: "environment" };
          addDebugLog('No cameras enumerated, using facingMode: environment');
        }
      } catch (e) {
        addDebugLog(`Camera enumeration failed: ${e.message}, using facingMode`);
        cameraConfig = { facingMode: "environment" };
      }

      // Success callback wrapper with extra logging
      const onScanSuccess = (decodedText, decodedResult) => {
        setScanCount(prev => prev + 1);
        addDebugLog(`SCAN SUCCESS: ${decodedText.substring(0, 20)}...`);
        // Show immediate visual feedback
        toast.success('QR Code Found!', { duration: 1000 });
        handleQRDetected(decodedText, decodedResult);
      };
      
      // Error callback - shows scanning activity
      let errorCount = 0;
      let lastStatusTime = Date.now();
      const onScanError = (errorMessage) => {
        errorCount++;
        // Log first few errors for debugging
        if (errorCount <= 3) {
          addDebugLog(`Scan attempt ${errorCount}: ${errorMessage.substring(0, 50)}`);
        }
        // Every 100 attempts (roughly every 10 seconds at 10fps), show activity
        if (errorCount % 100 === 0) {
          const elapsed = Math.round((Date.now() - lastStatusTime) / 1000);
          addDebugLog(`Still scanning... ${errorCount} frames processed in ${elapsed}s`);
        }
      };

      addDebugLog(`Starting with config: ${JSON.stringify(config)}`);
      addDebugLog(`Camera config: ${typeof cameraConfig === 'string' ? cameraConfig : JSON.stringify(cameraConfig)}`);
      
      await html5QrCode.start(
        cameraConfig,
        config,
        onScanSuccess,
        onScanError
      );

      addDebugLog('Camera started successfully!');
      setScanning(true);
      setScannerStatus('scanning');
      setDebugInfo('Camera active - point at QR code');
      toast.success('Camera ready! Point at QR code.');
      
    } catch (err) {
      addDebugLog(`Scanner error: ${err.name} - ${err.message}`);
      console.error('Scanner error:', err);
      
      let errorMsg = 'Could not start camera.';
      
      if (err.name === 'NotAllowedError' || err.message?.includes('Permission')) {
        errorMsg = 'Camera permission denied. Please allow camera access in your browser settings and try again.';
      } else if (err.name === 'NotFoundError') {
        errorMsg = 'No camera found on this device.';
      } else if (err.name === 'NotReadableError' || err.name === 'AbortError') {
        errorMsg = 'Camera is in use by another app. Please close other apps using the camera.';
      } else if (err.name === 'OverconstrainedError') {
        errorMsg = 'Camera does not support required settings. Try a different browser.';
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
      
      addDebugLog(`Registering device: ${deviceName}`);
      
      await api.post('/attendance/register-device', {
        device_token: deviceToken,
        device_name: deviceName
      });
      
      setDeviceRegistered(true);
      addDebugLog('Device registered successfully');
      toast.success('Device registered successfully!');
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Registration failed';
      addDebugLog(`Registration failed: ${errMsg}`);
      toast.error(errMsg);
    }
  };

  const resetScanner = () => {
    addDebugLog('Resetting scanner state');
    setResult(null);
    setError(null);
    setScannerStatus('idle');
    hasScannedRef.current = false;
  };

  const handleManualSubmit = () => {
    if (manualCode.trim()) {
      addDebugLog(`Manual code submitted: ${manualCode.trim()}`);
      handleQRDetected(manualCode.trim(), { result: { format: { formatName: 'MANUAL' } } });
    }
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
          
          {/* Debug toggle button */}
          <button
            onClick={() => setShowDebug(!showDebug)}
            className="mt-2 text-xs text-slate-500 flex items-center justify-center gap-1 mx-auto"
          >
            <Bug size={12} />
            {showDebug ? 'Hide Debug' : 'Show Debug'}
          </button>
        </div>

        {/* Debug Panel */}
        {showDebug && (
          <div className="bg-slate-800 rounded-lg p-3 mb-4 max-h-40 overflow-y-auto">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-mono text-slate-400">Debug Logs ({debugLogs.length})</span>
              <button 
                onClick={() => setDebugLogs([])}
                className="text-xs text-red-400"
              >
                Clear
              </button>
            </div>
            <div className="text-xs font-mono text-green-400 space-y-0.5">
              {debugLogs.slice(-15).map((log, i) => (
                <div key={i} className="break-all">{log}</div>
              ))}
              {debugLogs.length === 0 && <div className="text-slate-500">No logs yet</div>}
            </div>
          </div>
        )}

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
                  data-testid="register-device-btn"
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

            {/* Scanner Container */}
            <div className="bg-slate-800 rounded-xl overflow-hidden mb-4 relative" style={{ minHeight: '300px' }}>
              {/* Scanner element - ALWAYS visible with fixed dimensions */}
              <div 
                id="qr-reader-box" 
                style={{ 
                  width: '100%', 
                  minHeight: '300px',
                  background: '#000'
                }}
              />
              
              {/* Overlay when not scanning - covers the scanner element */}
              {!scanning && scannerStatus !== 'starting' && (
                <div 
                  className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800"
                  style={{ zIndex: 10 }}
                >
                  <Camera size={48} className="text-slate-500 mb-3" />
                  <p className="text-slate-400 text-sm text-center">
                    Tap button below to start camera
                  </p>
                </div>
              )}
              
              {/* Starting indicator overlay */}
              {scannerStatus === 'starting' && (
                <div 
                  className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800"
                  style={{ zIndex: 10 }}
                >
                  <RefreshCw size={48} className="text-indigo-400 mb-3 animate-spin" />
                  <p className="text-indigo-300 text-sm">Starting camera...</p>
                  <p className="text-slate-500 text-xs mt-2">Please allow camera access if prompted</p>
                </div>
              )}
            </div>

            {/* Scanning indicator with scan count */}
            {scanning && (
              <div className="bg-indigo-900/50 border border-indigo-500 rounded-lg p-3 mb-4">
                <div className="flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  <span className="text-indigo-200 text-sm">
                    {scannerStatus === 'processing' ? 'Processing QR code...' : 'Camera active - point at QR code'}
                  </span>
                </div>
                {scanCount > 0 && (
                  <p className="text-center text-xs text-slate-400 mt-1">
                    Detected: {scanCount} QR code(s)
                  </p>
                )}
              </div>
            )}

            {/* Control Button */}
            {!scanning ? (
              <button
                onClick={startScanner}
                disabled={scannerStatus === 'starting'}
                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 rounded-xl font-medium flex items-center justify-center gap-2"
                data-testid="start-camera-btn"
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
                data-testid="stop-camera-btn"
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
                  data-testid="try-again-btn"
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
                data-testid="scan-again-btn"
              >
                Scan Again
              </button>
            </div>
          </div>
        )}

        {/* Manual Input Option - For when camera scanning doesn't work */}
        {isLoggedIn && deviceRegistered && !result && (
          <div className="mt-4">
            <button
              onClick={() => setShowManualInput(!showManualInput)}
              className="w-full py-2 text-slate-400 text-sm flex items-center justify-center gap-2"
              data-testid="manual-input-toggle"
            >
              <Keyboard size={16} />
              {showManualInput ? 'Hide manual input' : 'Camera not working? Enter code manually'}
            </button>
            
            {showManualInput && (
              <div className="mt-2 bg-slate-800 rounded-xl p-4">
                <p className="text-xs text-slate-400 mb-2">
                  Ask admin to read the QR code text (starts with ATT-)
                </p>
                <input
                  type="text"
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  placeholder="ATT-..."
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm mb-2"
                  data-testid="manual-code-input"
                />
                <button
                  onClick={handleManualSubmit}
                  disabled={!manualCode.trim()}
                  className="w-full py-2 bg-indigo-600 disabled:bg-slate-600 rounded-lg text-sm font-medium"
                  data-testid="submit-manual-code-btn"
                >
                  Submit Code
                </button>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        {isLoggedIn && deviceRegistered && !result && !showManualInput && (
          <div className="bg-slate-800 rounded-xl p-4 mt-4">
            <p className="font-medium text-sm mb-2">Instructions:</p>
            <ol className="text-xs text-slate-400 space-y-1">
              <li>1. Log in on office computer → QR shows</li>
              <li>2. Tap &quot;Start Camera&quot; above</li>
              <li>3. Point phone at QR code</li>
              <li>4. Wait for success message</li>
            </ol>
          </div>
        )}

        {/* Debug Info */}
        {debugInfo && (
          <p className="text-center text-xs text-slate-500 mt-2" data-testid="debug-info">
            {debugInfo}
          </p>
        )}

        <p className="text-center text-xs text-slate-600 mt-2">
          Device: {deviceToken?.slice(-8)}
        </p>
      </div>
    </div>
  );
}
