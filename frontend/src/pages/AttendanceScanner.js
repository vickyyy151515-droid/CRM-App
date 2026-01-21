import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw, Keyboard, LogIn } from 'lucide-react';
import jsQR from 'jsqr';

export default function AttendanceScanner() {
  // Auth state
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');
  
  // Device state
  const [deviceToken, setDeviceToken] = useState(null);
  const [deviceRegistered, setDeviceRegistered] = useState(false);
  const [checkingDevice, setCheckingDevice] = useState(true);
  
  // Scanner state
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [frameCount, setFrameCount] = useState(0);
  const [cameraReady, setCameraReady] = useState(false);
  const [debugLog, setDebugLog] = useState([]);
  
  // Manual input
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualCode, setManualCode] = useState('');
  
  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const scanIntervalRef = useRef(null);
  const mountedRef = useRef(true);

  // Add debug log
  const addLog = useCallback((msg) => {
    console.log('[Scanner]', msg);
    setDebugLog(prev => [...prev.slice(-20), `${new Date().toLocaleTimeString()}: ${msg}`]);
  }, []);

  // Generate device token on mount
  useEffect(() => {
    mountedRef.current = true;
    let token = localStorage.getItem('device_token');
    if (!token) {
      token = 'DEV-' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
      localStorage.setItem('device_token', token);
    }
    setDeviceToken(token);
    
    // Detect device
    const ua = navigator.userAgent;
    const isAndroid = /Android/i.test(ua);
    const isIOS = /iPhone|iPad|iPod/i.test(ua);
    addLog(`Device: ${isAndroid ? 'Android' : isIOS ? 'iOS' : 'Other'}`);
    addLog(`UserAgent: ${ua.substring(0, 50)}...`);
    
    return () => {
      mountedRef.current = false;
      stopScanner();
    };
  }, [addLog]);

  // Check auth status
  useEffect(() => {
    const checkAuth = async () => {
      const scannerToken = localStorage.getItem('scanner_token');
      const mainToken = localStorage.getItem('token');
      const tokenToUse = scannerToken || mainToken;
      
      if (tokenToUse) {
        try {
          const response = await api.get('/auth/me', {
            headers: { Authorization: `Bearer ${tokenToUse}` }
          });
          setUser(response.data);
          setIsLoggedIn(true);
          localStorage.setItem('scanner_token', tokenToUse);
          
          const deviceResponse = await api.get('/attendance/device-status', {
            headers: { Authorization: `Bearer ${tokenToUse}` }
          });
          setDeviceRegistered(deviceResponse.data.has_device);
        } catch (error) {
          localStorage.removeItem('scanner_token');
          setIsLoggedIn(false);
        }
      }
      setCheckingDevice(false);
    };
    checkAuth();
  }, []);

  // Handle login
  const handleScannerLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    
    try {
      const response = await api.post('/auth/login', {
        email: loginEmail,
        password: loginPassword
      });
      
      const { token, user: userData } = response.data;
      localStorage.setItem('scanner_token', token);
      setUser(userData);
      setIsLoggedIn(true);
      
      const deviceResponse = await api.get('/attendance/device-status', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDeviceRegistered(deviceResponse.data.has_device);
      
      toast.success('Login successful!');
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Login failed';
      setLoginError(errMsg);
    } finally {
      setLoginLoading(false);
    }
  };

  // Register device
  const registerDevice = async () => {
    if (!isLoggedIn) {
      toast.error('Please log in first');
      return;
    }

    try {
      const deviceName = /iPhone|iPad|iPod/.test(navigator.userAgent) ? 'iPhone' : 
                         /Android/.test(navigator.userAgent) ? 'Android' : 'Mobile';
      
      const scannerToken = localStorage.getItem('scanner_token');
      await api.post('/attendance/register-device', {
        device_token: deviceToken,
        device_name: deviceName
      }, {
        headers: scannerToken ? { Authorization: `Bearer ${scannerToken}` } : {}
      });
      
      setDeviceRegistered(true);
      toast.success('Device registered successfully!');
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Registration failed';
      toast.error(errMsg);
    }
  };

  // Stop scanner
  const stopScanner = useCallback(() => {
    addLog('Stopping scanner...');
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop();
        addLog(`Stopped track: ${track.kind}`);
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setScanning(false);
    setCameraReady(false);
  }, [addLog]);

  // Process QR code detection
  const processQRCode = useCallback(async (code) => {
    addLog(`QR Code detected: ${code.substring(0, 30)}...`);
    
    if (!code.startsWith('ATT-')) {
      toast.error('Invalid QR code format. Must start with ATT-');
      addLog('Invalid QR format');
      return;
    }

    stopScanner();
    
    try {
      toast.loading('Recording attendance...', { id: 'attendance-loading' });
      
      const scannerToken = localStorage.getItem('scanner_token');
      const response = await api.post('/attendance/scan', {
        qr_code: code,
        device_token: deviceToken
      }, {
        headers: scannerToken ? { Authorization: `Bearer ${scannerToken}` } : {}
      });

      toast.dismiss('attendance-loading');
      
      setResult({
        success: true,
        message: response.data.message,
        status: response.data.attendance_status,
        time: response.data.check_in_time,
        staffName: response.data.staff_name
      });
      
      toast.success('Check-in successful!');
      addLog('Check-in successful!');
      
    } catch (error) {
      toast.dismiss('attendance-loading');
      const errorMsg = error.response?.data?.detail || 'Failed to check in';
      setError(errorMsg);
      setResult({ success: false, message: errorMsg });
      toast.error(errorMsg);
      addLog(`Check-in failed: ${errorMsg}`);
    }
  }, [deviceToken, stopScanner, addLog]);

  // Scan a single frame
  const scanFrame = useCallback(() => {
    if (!mountedRef.current || !videoRef.current || !canvasRef.current) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // Check video state
    if (video.readyState < video.HAVE_CURRENT_DATA) {
      return;
    }

    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    
    // Use actual video dimensions
    const width = video.videoWidth;
    const height = video.videoHeight;
    
    if (width === 0 || height === 0) {
      return;
    }

    canvas.width = width;
    canvas.height = height;
    
    try {
      ctx.drawImage(video, 0, 0, width, height);
      const imageData = ctx.getImageData(0, 0, width, height);
      
      // Try with different inversion settings for better detection
      // 'attemptBoth' tries normal and inverted, which helps with screens
      let code = jsQR(imageData.data, width, height, {
        inversionAttempts: 'attemptBoth',
      });
      
      setFrameCount(prev => {
        const newCount = prev + 1;
        if (newCount % 50 === 0) {
          addLog(`Frames: ${newCount}, res: ${width}x${height}`);
        }
        return newCount;
      });
      
      if (code && code.data) {
        addLog(`FOUND QR: ${code.data}`);
        // Vibrate on success if supported
        if (navigator.vibrate) {
          navigator.vibrate(200);
        }
        processQRCode(code.data);
      }
    } catch (err) {
      // Silently handle draw errors
    }
  }, [processQRCode, addLog]);

  // Start camera
  const startScanner = async () => {
    setError(null);
    setFrameCount(0);
    setCameraReady(false);
    setDebugLog([]);
    
    addLog('Starting scanner...');
    
    // Check if getUserMedia is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError('Camera not supported on this browser');
      addLog('getUserMedia not supported');
      return;
    }

    try {
      addLog('Requesting camera permission...');
      toast.loading('Starting camera...', { id: 'camera-start' });
      
      // Try different constraints for Android compatibility
      let stream = null;
      const constraintsList = [
        // Try 1: Ideal environment facing
        { 
          video: { 
            facingMode: { ideal: 'environment' },
            width: { ideal: 1280 },
            height: { ideal: 720 }
          } 
        },
        // Try 2: Exact environment facing
        { 
          video: { 
            facingMode: { exact: 'environment' }
          } 
        },
        // Try 3: Just video true (fallback)
        { 
          video: true 
        }
      ];
      
      for (let i = 0; i < constraintsList.length; i++) {
        try {
          addLog(`Trying constraint ${i + 1}...`);
          stream = await navigator.mediaDevices.getUserMedia(constraintsList[i]);
          addLog(`Constraint ${i + 1} succeeded`);
          break;
        } catch (e) {
          addLog(`Constraint ${i + 1} failed: ${e.name}`);
          if (i === constraintsList.length - 1) {
            throw e;
          }
        }
      }
      
      if (!stream) {
        throw new Error('Could not get camera stream');
      }
      
      streamRef.current = stream;
      
      // Log stream info
      const tracks = stream.getVideoTracks();
      addLog(`Got ${tracks.length} video track(s)`);
      if (tracks[0]) {
        const settings = tracks[0].getSettings();
        addLog(`Camera: ${settings.width}x${settings.height}, facing: ${settings.facingMode || 'unknown'}`);
      }
      
      const video = videoRef.current;
      if (!video) {
        throw new Error('Video element not found');
      }
      
      // Set video attributes for Android compatibility
      video.setAttribute('autoplay', '');
      video.setAttribute('playsinline', '');
      video.setAttribute('muted', '');
      video.muted = true;
      video.playsInline = true;
      
      // Set source
      video.srcObject = stream;
      
      // Wait for video to be ready
      addLog('Waiting for video to load...');
      
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Video load timeout'));
        }, 10000);
        
        video.onloadedmetadata = () => {
          addLog(`Video metadata loaded: ${video.videoWidth}x${video.videoHeight}`);
          clearTimeout(timeout);
          resolve();
        };
        
        video.onerror = (e) => {
          addLog(`Video error: ${e}`);
          clearTimeout(timeout);
          reject(new Error('Video error'));
        };
      });
      
      // Play video
      addLog('Playing video...');
      await video.play();
      addLog(`Video playing: ${video.videoWidth}x${video.videoHeight}`);
      
      toast.dismiss('camera-start');
      toast.success('Camera ready! Point at QR code');
      
      setScanning(true);
      setCameraReady(true);
      
      // Start scanning interval (more reliable than requestAnimationFrame on some Android)
      addLog('Starting scan interval...');
      scanIntervalRef.current = setInterval(scanFrame, 100); // 10 fps
      
    } catch (err) {
      toast.dismiss('camera-start');
      addLog(`Camera error: ${err.name} - ${err.message}`);
      console.error('Camera error:', err);
      
      let errorMsg = 'Could not start camera.';
      if (err.name === 'NotAllowedError') {
        errorMsg = 'Camera permission denied. Please allow camera access in browser settings.';
      } else if (err.name === 'NotFoundError') {
        errorMsg = 'No camera found on this device.';
      } else if (err.name === 'NotReadableError') {
        errorMsg = 'Camera is in use by another app. Close other apps using camera.';
      } else if (err.name === 'OverconstrainedError') {
        errorMsg = 'Camera does not support required settings.';
      } else if (err.message === 'Video load timeout') {
        errorMsg = 'Camera took too long to start. Please try again.';
      }
      
      setError(errorMsg);
      toast.error(errorMsg);
      stopScanner();
    }
  };

  // Handle manual code submission
  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!manualCode.trim()) return;
    
    await processQRCode(manualCode.trim());
    setManualCode('');
    setShowManualInput(false);
  };

  // Reset for new scan
  const handleReset = () => {
    setResult(null);
    setError(null);
    setFrameCount(0);
    setDebugLog([]);
  };

  // Loading state
  if (checkingDevice) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="text-center">
          <RefreshCw className="animate-spin text-indigo-400 mx-auto mb-3" size={32} />
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
          <h1 className="text-xl font-bold mb-1">Attendance Scanner</h1>
          <p className="text-slate-400 text-sm">Scan QR code to check in</p>
        </div>

        {/* Hidden canvas for jsQR processing */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* Login Form */}
        {!isLoggedIn && (
          <div className="bg-slate-800 rounded-xl p-6">
            <div className="text-center mb-4">
              <LogIn className="w-10 h-10 text-indigo-400 mx-auto mb-2" />
              <h2 className="text-lg font-semibold">Login Required</h2>
            </div>
            
            <form onSubmit={handleScannerLogin} className="space-y-3">
              <input
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="Email"
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400"
                required
                data-testid="scanner-login-email"
              />
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Password"
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400"
                required
                data-testid="scanner-login-password"
              />
              
              {loginError && (
                <div className="text-red-400 text-sm text-center">{loginError}</div>
              )}
              
              <button
                type="submit"
                disabled={loginLoading}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 rounded-lg font-medium flex items-center justify-center gap-2"
                data-testid="scanner-login-btn"
              >
                {loginLoading ? <><RefreshCw className="animate-spin" size={18} /> Logging in...</> : <><LogIn size={18} /> Login</>}
              </button>
            </form>
          </div>
        )}

        {/* Not Registered */}
        {isLoggedIn && !deviceRegistered && (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <Smartphone className="w-12 h-12 text-amber-400 mx-auto mb-3" />
            <h2 className="text-lg font-semibold mb-2">Register This Device</h2>
            <p className="text-slate-400 text-sm mb-4">Register this device for attendance</p>
            <button
              onClick={registerDevice}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium"
              data-testid="register-device-btn"
            >
              Register Device
            </button>
          </div>
        )}

        {/* Scanner Interface */}
        {isLoggedIn && deviceRegistered && !result && (
          <>
            {/* Status Badge */}
            <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-2 mb-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-emerald-400" size={16} />
                <span className="text-emerald-200 text-sm">{user?.name}</span>
              </div>
            </div>

            {/* Camera View */}
            <div className="bg-black rounded-xl overflow-hidden mb-3 relative" style={{ aspectRatio: '4/3' }}>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
              
              {/* Scanning overlay */}
              {scanning && cameraReady && (
                <div className="absolute inset-0 pointer-events-none">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-48 h-48 border-2 border-green-400 rounded-lg relative">
                      <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-green-400" />
                      <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-green-400" />
                      <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-green-400" />
                      <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-green-400" />
                      <div className="absolute left-1 right-1 h-0.5 bg-red-500 opacity-75 animate-bounce" style={{ top: '50%' }} />
                    </div>
                  </div>
                </div>
              )}
              
              {/* Camera off state */}
              {!scanning && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800">
                  <Camera size={40} className="text-slate-500 mb-2" />
                  <p className="text-slate-400 text-sm">Tap Start Camera</p>
                </div>
              )}
            </div>

            {/* Status Bar */}
            {scanning && (
              <div className="bg-slate-800 rounded-lg p-3 mb-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${cameraReady ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`} />
                    <span className="text-sm">{cameraReady ? 'Scanning...' : 'Starting...'}</span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">Frames: {frameCount}</span>
                </div>
                <p className="text-xs text-slate-500 text-center">Hold QR code steady inside the frame</p>
              </div>
            )}

            {/* Debug Log - Always visible when scanning */}
            {scanning && debugLog.length > 0 && (
              <div className="bg-slate-800 rounded-lg p-2 mb-3 max-h-32 overflow-y-auto">
                <div className="text-xs font-mono text-green-400 space-y-0.5">
                  {debugLog.slice(-8).map((log, i) => (
                    <div key={i} className="truncate">{log}</div>
                  ))}
                </div>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 mb-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={16} />
                  <span className="text-red-200 text-sm">{error}</span>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-2">
              {!scanning ? (
                <button
                  onClick={startScanner}
                  className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium flex items-center justify-center gap-2 text-lg"
                  data-testid="start-camera-btn"
                >
                  <Camera size={22} /> Start Camera
                </button>
              ) : (
                <button
                  onClick={stopScanner}
                  className="w-full py-3 bg-red-600 hover:bg-red-700 rounded-lg font-medium flex items-center justify-center gap-2"
                  data-testid="stop-camera-btn"
                >
                  <XCircle size={18} /> Stop Camera
                </button>
              )}

              <button
                onClick={() => setShowManualInput(!showManualInput)}
                className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm flex items-center justify-center gap-2"
                data-testid="manual-input-toggle"
              >
                <Keyboard size={16} /> {showManualInput ? 'Hide Manual Input' : 'Enter Code Manually'}
              </button>

              {showManualInput && (
                <form onSubmit={handleManualSubmit} className="bg-slate-800 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-2">Enter the QR code text (starts with ATT-)</p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={manualCode}
                      onChange={(e) => setManualCode(e.target.value)}
                      placeholder="ATT-..."
                      className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm"
                      data-testid="manual-code-input"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium"
                      data-testid="manual-submit-btn"
                    >
                      Submit
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Compact Instructions */}
            <div className="bg-slate-800 rounded-lg p-3 mt-3 text-xs text-slate-400">
              <p className="font-medium text-white mb-1">Instructions:</p>
              <p>1. Open CRM on computer → QR shows</p>
              <p>2. Start Camera → Point at QR</p>
              <p>3. Hold steady until detected</p>
              <p className="mt-2 text-amber-400">Not working? Use "Enter Code Manually"</p>
            </div>
          </>
        )}

        {/* Result Screen */}
        {result && (
          <div className={`rounded-xl p-6 text-center ${result.success ? 'bg-emerald-900/50 border border-emerald-600' : 'bg-red-900/50 border border-red-600'}`}>
            {result.success ? (
              <>
                <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
                <h2 className="text-xl font-bold mb-2">Check-in Successful!</h2>
                <p className="text-emerald-200 mb-1">{result.staffName}</p>
                <p className="text-slate-400 text-sm mb-4">{result.status} at {result.time}</p>
              </>
            ) : (
              <>
                <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
                <h2 className="text-xl font-bold mb-2">Check-in Failed</h2>
                <p className="text-red-200 text-sm mb-4">{result.message}</p>
              </>
            )}
            
            <button
              onClick={handleReset}
              className="px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium"
              data-testid="scan-again-btn"
            >
              Scan Again
            </button>
          </div>
        )}

        {/* Footer with version */}
        <div className="text-center mt-4 text-xs text-slate-600">
          <p>Device: {deviceToken?.substring(0, 12)}...</p>
          <p className="text-slate-500 mt-1">Scanner v2.1 (jsQR)</p>
        </div>
      </div>
    </div>
  );
}
