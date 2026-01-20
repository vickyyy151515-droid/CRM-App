import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Camera, CheckCircle, XCircle, Smartphone, AlertTriangle, RefreshCw } from 'lucide-react';

export default function AttendanceScanner() {
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [deviceToken, setDeviceToken] = useState(null);
  const [deviceRegistered, setDeviceRegistered] = useState(false);
  const [checkingDevice, setCheckingDevice] = useState(true);
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const scanIntervalRef = useRef(null);

  // Generate or retrieve device token
  useEffect(() => {
    let token = localStorage.getItem('attendance_device_token');
    if (!token) {
      token = `DEV-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('attendance_device_token', token);
    }
    setDeviceToken(token);
  }, []);

  // Check if user is logged in and device is registered
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          setIsLoggedIn(true);
          
          // Check device registration
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

  // Start camera
  const startCamera = useCallback(async () => {
    setCameraError(null);
    setError(null);
    
    try {
      const constraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setScanning(true);
        
        // Start scanning for QR codes
        startQRScanning();
      }
    } catch (err) {
      console.error('Camera error:', err);
      setCameraError(err.message || 'Failed to access camera');
      setScanning(false);
    }
  }, []);

  // Stop camera
  const stopCamera = useCallback(() => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
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

  // Scan for QR codes using canvas
  const startQRScanning = useCallback(() => {
    // Dynamically import jsQR
    import('jsqr').then(({ default: jsQR }) => {
      scanIntervalRef.current = setInterval(() => {
        if (!videoRef.current || !canvasRef.current) return;
        
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        
        if (video.readyState !== video.HAVE_ENOUGH_DATA) return;
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: 'dontInvert'
        });
        
        if (code && code.data) {
          // Found a QR code
          console.log('QR Code found:', code.data);
          stopCamera();
          handleScan(code.data);
        }
      }, 100); // Scan every 100ms
    }).catch(err => {
      console.error('Failed to load jsQR:', err);
      setCameraError('Failed to load QR scanner');
    });
  }, [stopCamera]);

  // Handle scanned QR code
  const handleScan = async (qrCode) => {
    if (!qrCode.startsWith('ATT-')) {
      setError('Invalid QR code. Please scan the attendance QR code.');
      return;
    }

    try {
      const response = await api.post('/attendance/scan', {
        qr_code: qrCode,
        device_token: deviceToken
      });

      setResult({
        success: true,
        message: response.data.message,
        status: response.data.attendance_status,
        time: response.data.check_in_time,
        staffName: response.data.staff_name
      });
      
      toast.success(response.data.message);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to process QR code';
      setError(errorMsg);
      setResult({
        success: false,
        message: errorMsg
      });
      toast.error(errorMsg);
    }
  };

  const registerDevice = async () => {
    if (!isLoggedIn) {
      toast.error('Please log in first to register this device');
      return;
    }

    try {
      const response = await api.post('/attendance/register-device', {
        device_token: deviceToken,
        device_name: navigator.userAgent.includes('iPhone') ? 'iPhone' : 
                     navigator.userAgent.includes('Android') ? 'Android Phone' : 'Mobile Device'
      });
      
      setDeviceRegistered(true);
      toast.success(response.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to register device');
    }
  };

  const resetAndScanAgain = () => {
    setResult(null);
    setError(null);
    setCameraError(null);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

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
        <div className="text-center mb-6 pt-4">
          <div className="w-14 h-14 bg-indigo-600 rounded-full flex items-center justify-center mx-auto mb-3">
            <Smartphone size={28} />
          </div>
          <h1 className="text-xl font-bold">Attendance Scanner</h1>
          <p className="text-slate-400 text-sm mt-1">Scan the QR code on your computer</p>
        </div>

        {/* Login Prompt */}
        {!isLoggedIn && (
          <div className="bg-slate-800 rounded-xl p-6 text-center mb-6">
            <p className="text-slate-400 mb-4">
              Please log in to register your device and scan attendance.
            </p>
            <a
              href="/"
              className="inline-block px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium transition-colors"
            >
              Go to Login
            </a>
          </div>
        )}

        {/* Device Registration Status */}
        {isLoggedIn && !deviceRegistered && (
          <div className="bg-amber-900/50 border border-amber-600 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-amber-500 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-amber-200">Device Not Registered</p>
                <p className="text-sm text-amber-300 mt-1">
                  Register this phone to use for attendance.
                </p>
                <button
                  onClick={registerDevice}
                  className="mt-3 px-4 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-sm font-medium transition-colors"
                >
                  Register This Device
                </button>
              </div>
            </div>
          </div>
        )}

        {isLoggedIn && deviceRegistered && (
          <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-3 mb-6">
            <div className="flex items-center gap-3">
              <CheckCircle className="text-emerald-500" size={20} />
              <div>
                <p className="font-medium text-emerald-200">Device Registered</p>
                <p className="text-sm text-emerald-300">Logged in as {user?.name}</p>
              </div>
            </div>
          </div>
        )}

        {/* Scanner Area */}
        {isLoggedIn && deviceRegistered && !result && (
          <div className="bg-slate-800 rounded-xl overflow-hidden mb-6">
            {/* Video Preview */}
            <div className="relative aspect-square bg-black">
              <video 
                ref={videoRef}
                className={`w-full h-full object-cover ${scanning ? 'block' : 'hidden'}`}
                playsInline
                muted
              />
              <canvas ref={canvasRef} className="hidden" />
              
              {/* Scan overlay */}
              {scanning && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-64 h-64 border-2 border-indigo-500 rounded-lg relative">
                    <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-indigo-500 rounded-tl-lg"></div>
                    <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-indigo-500 rounded-tr-lg"></div>
                    <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-indigo-500 rounded-bl-lg"></div>
                    <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-indigo-500 rounded-br-lg"></div>
                  </div>
                </div>
              )}
              
              {!scanning && (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Camera size={48} className="text-slate-500 mb-4" />
                  <p className="text-slate-400 text-center px-4 mb-4">
                    Tap to start camera and scan QR code
                  </p>
                </div>
              )}
            </div>
            
            {/* Camera Error */}
            {cameraError && (
              <div className="p-4 bg-red-900/50 text-red-300 text-sm">
                <p className="font-medium">Camera Error:</p>
                <p>{cameraError}</p>
                <p className="mt-2 text-xs">Make sure you've granted camera permission.</p>
              </div>
            )}
            
            {/* Control Button */}
            <div className="p-4 text-center">
              {!scanning ? (
                <button
                  onClick={startCamera}
                  className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium transition-colors w-full"
                >
                  <Camera className="inline mr-2" size={20} />
                  Start Camera
                </button>
              ) : (
                <button
                  onClick={stopCamera}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors w-full"
                >
                  Stop Camera
                </button>
              )}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && !result && (
          <div className="bg-red-900/50 border border-red-600 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <XCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-red-200">Error</p>
                <p className="text-sm text-red-300 mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={resetAndScanAgain}
              className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className={`rounded-xl p-6 mb-6 ${
            result.success 
              ? 'bg-emerald-900/50 border border-emerald-600' 
              : 'bg-red-900/50 border border-red-600'
          }`}>
            <div className="text-center">
              {result.success ? (
                <>
                  <CheckCircle size={64} className="text-emerald-500 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-emerald-200 mb-2">Check-in Successful!</h2>
                  <p className="text-emerald-300">{result.staffName}</p>
                  <div className="mt-4 p-3 bg-emerald-800/50 rounded-lg">
                    <p className="text-sm text-emerald-400">Time: {result.time}</p>
                    <p className={`text-lg font-bold mt-1 ${
                      result.status === 'on_time' ? 'text-emerald-300' : 'text-amber-400'
                    }`}>
                      {result.status === 'on_time' ? '✓ ON TIME' : '⚠ LATE'}
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <XCircle size={64} className="text-red-500 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-red-200 mb-2">Check-in Failed</h2>
                  <p className="text-red-300">{result.message}</p>
                </>
              )}
              
              <button
                onClick={resetAndScanAgain}
                className="mt-6 px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition-colors"
              >
                Scan Another QR
              </button>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-slate-800 rounded-xl p-4">
          <h3 className="font-semibold mb-3">Instructions</h3>
          <ol className="text-sm text-slate-400 space-y-2">
            <li>1. Log in on your computer at the office</li>
            <li>2. A QR code will appear on screen</li>
            <li>3. Tap "Start Camera" above</li>
            <li>4. Point your camera at the QR code</li>
            <li>5. Wait for confirmation</li>
          </ol>
        </div>

        {/* Device Info */}
        <div className="mt-4 text-center text-xs text-slate-500">
          <p>Device ID: {deviceToken?.slice(-8)}</p>
        </div>
      </div>
    </div>
  );
}
