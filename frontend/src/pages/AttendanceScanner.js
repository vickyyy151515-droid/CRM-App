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
  const [lastScanTime, setLastScanTime] = useState(null);
  
  // Manual input
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualCode, setManualCode] = useState('');
  
  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const animationRef = useRef(null);
  const mountedRef = useRef(true);

  // Generate device token on mount
  useEffect(() => {
    mountedRef.current = true;
    let token = localStorage.getItem('device_token');
    if (!token) {
      token = 'DEV-' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
      localStorage.setItem('device_token', token);
    }
    setDeviceToken(token);
    
    return () => {
      mountedRef.current = false;
      stopScanner();
    };
  }, []);

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
          
          // Check device status
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
      
      // Check device status
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
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setScanning(false);
  }, []);

  // Process QR code detection
  const processQRCode = useCallback(async (code) => {
    if (!code.startsWith('ATT-')) {
      toast.error('Invalid QR code format');
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
      
    } catch (error) {
      toast.dismiss('attendance-loading');
      const errorMsg = error.response?.data?.detail || 'Failed to check in';
      setError(errorMsg);
      setResult({ success: false, message: errorMsg });
      toast.error(errorMsg);
    }
  }, [deviceToken, stopScanner]);

  // Start camera with jsQR scanning
  const startScanner = async () => {
    setError(null);
    setFrameCount(0);
    
    try {
      // Request camera with back camera preference
      const constraints = {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };
      
      toast.loading('Starting camera...', { id: 'camera-start' });
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      
      toast.dismiss('camera-start');
      toast.success('Camera ready! Point at QR code');
      setScanning(true);
      
      // Start scanning loop
      scanLoop();
      
    } catch (err) {
      toast.dismiss('camera-start');
      console.error('Camera error:', err);
      
      let errorMsg = 'Could not start camera.';
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

  // Continuous scanning loop using jsQR
  const scanLoop = useCallback(() => {
    if (!mountedRef.current || !videoRef.current || !canvasRef.current) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      // Set canvas size to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // Draw video frame to canvas
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Get image data for jsQR
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      
      // Try to detect QR code
      const code = jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: 'dontInvert',
      });
      
      setFrameCount(prev => prev + 1);
      
      if (code && code.data) {
        console.log('QR Code detected:', code.data);
        setLastScanTime(new Date().toISOString());
        
        // Draw detection box
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(code.location.topLeftCorner.x, code.location.topLeftCorner.y);
        ctx.lineTo(code.location.topRightCorner.x, code.location.topRightCorner.y);
        ctx.lineTo(code.location.bottomRightCorner.x, code.location.bottomRightCorner.y);
        ctx.lineTo(code.location.bottomLeftCorner.x, code.location.bottomLeftCorner.y);
        ctx.closePath();
        ctx.stroke();
        
        // Process the QR code
        processQRCode(code.data);
        return; // Stop loop after detection
      }
    }
    
    // Continue scanning
    animationRef.current = requestAnimationFrame(scanLoop);
  }, [processQRCode]);

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
        <div className="text-center mb-6">
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
              <p className="text-slate-400 text-sm mt-1">Please log in to use the scanner</p>
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
                {loginLoading ? (
                  <><RefreshCw className="animate-spin" size={18} /> Logging in...</>
                ) : (
                  <><LogIn size={18} /> Login</>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Not Registered */}
        {isLoggedIn && !deviceRegistered && (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <Smartphone className="w-12 h-12 text-amber-400 mx-auto mb-3" />
            <h2 className="text-lg font-semibold mb-2">Register This Device</h2>
            <p className="text-slate-400 text-sm mb-4">
              Register this device for attendance scanning
            </p>
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
            <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-3 mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-emerald-400" size={18} />
                <span className="text-emerald-200 text-sm">Device registered • {user?.name}</span>
              </div>
            </div>

            {/* Camera View */}
            <div className="bg-black rounded-xl overflow-hidden mb-4 relative" style={{ aspectRatio: '4/3' }}>
              <video
                ref={videoRef}
                playsInline
                muted
                className="w-full h-full object-cover"
                style={{ display: scanning ? 'block' : 'none' }}
              />
              
              {/* Scanning overlay */}
              {scanning && (
                <div className="absolute inset-0 pointer-events-none">
                  {/* Scan frame */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-56 h-56 border-2 border-green-400 rounded-lg relative">
                      <div className="absolute -top-1 -left-1 w-8 h-8 border-t-4 border-l-4 border-green-400 rounded-tl" />
                      <div className="absolute -top-1 -right-1 w-8 h-8 border-t-4 border-r-4 border-green-400 rounded-tr" />
                      <div className="absolute -bottom-1 -left-1 w-8 h-8 border-b-4 border-l-4 border-green-400 rounded-bl" />
                      <div className="absolute -bottom-1 -right-1 w-8 h-8 border-b-4 border-r-4 border-green-400 rounded-br" />
                      {/* Scan line animation */}
                      <div className="absolute left-2 right-2 h-0.5 bg-green-400 animate-pulse" style={{ top: '50%' }} />
                    </div>
                  </div>
                </div>
              )}
              
              {/* Camera off state */}
              {!scanning && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800">
                  <Camera size={48} className="text-slate-500 mb-3" />
                  <p className="text-slate-400 text-sm">Tap button below to start</p>
                </div>
              )}
            </div>

            {/* Frame Counter */}
            {scanning && (
              <div className="bg-indigo-900/50 border border-indigo-500 rounded-lg p-3 mb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    <span className="text-indigo-200 text-sm">Scanning...</span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    Frames: {frameCount}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-2 text-center">
                  Position QR code inside the green frame
                </p>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 mb-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="text-red-400" size={18} />
                  <span className="text-red-200 text-sm">{error}</span>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-3">
              {!scanning ? (
                <button
                  onClick={startScanner}
                  className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium flex items-center justify-center gap-2"
                  data-testid="start-camera-btn"
                >
                  <Camera size={20} /> Start Camera
                </button>
              ) : (
                <button
                  onClick={stopScanner}
                  className="w-full py-4 bg-red-600 hover:bg-red-700 rounded-lg font-medium flex items-center justify-center gap-2"
                  data-testid="stop-camera-btn"
                >
                  <XCircle size={20} /> Stop Camera
                </button>
              )}

              {/* Manual Input Toggle */}
              <button
                onClick={() => setShowManualInput(!showManualInput)}
                className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm flex items-center justify-center gap-2"
                data-testid="manual-input-toggle"
              >
                <Keyboard size={18} /> {showManualInput ? 'Hide' : 'Enter Code Manually'}
              </button>

              {/* Manual Input Form */}
              {showManualInput && (
                <form onSubmit={handleManualSubmit} className="bg-slate-800 rounded-lg p-4">
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

            {/* Instructions */}
            <div className="bg-slate-800 rounded-xl p-4 mt-4">
              <p className="font-medium text-sm mb-2">Instructions:</p>
              <ol className="text-xs text-slate-400 space-y-1">
                <li>1. Open computer → QR code displays</li>
                <li>2. Tap &quot;Start Camera&quot; on this phone</li>
                <li>3. Point camera at QR code on screen</li>
                <li>4. Hold steady inside green frame</li>
              </ol>
              <div className="mt-3 pt-3 border-t border-slate-700">
                <p className="font-medium text-xs text-amber-400 mb-1">Camera not detecting?</p>
                <ul className="text-xs text-slate-500 space-y-1">
                  <li>• Hold phone 15-30 cm from screen</li>
                  <li>• Make sure QR fully fits in frame</li>
                  <li>• Avoid glare on the screen</li>
                  <li>• Use &quot;Enter Code Manually&quot; as backup</li>
                </ul>
              </div>
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

        {/* Footer */}
        <div className="text-center mt-6 text-xs text-slate-500">
          <p>Device: {deviceToken?.substring(0, 12)}...</p>
        </div>
      </div>
    </div>
  );
}
