import { useState, useEffect, useRef } from 'react';
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
  const [scannerStatus, setScannerStatus] = useState('idle'); // idle, starting, scanning, processing
  const scannerRef = useRef(null);

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

  // Cleanup scanner on unmount
  useEffect(() => {
    return () => {
      if (scannerRef.current) {
        scannerRef.current.stop().catch(() => {});
      }
    };
  }, []);

  const startScanner = async () => {
    setError(null);
    setScannerStatus('starting');
    
    try {
      const html5QrCode = new Html5Qrcode("qr-reader-element");
      scannerRef.current = html5QrCode;

      const qrCodeSuccessCallback = async (decodedText) => {
        console.log('QR Code detected:', decodedText);
        setScannerStatus('processing');
        
        // Stop scanner immediately after detection
        try {
          await html5QrCode.stop();
          scannerRef.current = null;
        } catch (e) {
          console.log('Scanner already stopped');
        }
        
        setScanning(false);
        await handleScan(decodedText);
      };

      const config = { 
        fps: 10, 
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0
      };

      // Try back camera first, fall back to any camera
      try {
        await html5QrCode.start(
          { facingMode: "environment" },
          config,
          qrCodeSuccessCallback,
          (errorMessage) => {
            // Ignore scanning errors - these happen constantly while scanning
          }
        );
      } catch (err) {
        console.log('Back camera failed, trying any camera:', err);
        // Try any available camera
        const devices = await Html5Qrcode.getCameras();
        if (devices && devices.length > 0) {
          await html5QrCode.start(
            devices[0].id,
            config,
            qrCodeSuccessCallback,
            (errorMessage) => {}
          );
        } else {
          throw new Error('No cameras found');
        }
      }

      setScanning(true);
      setScannerStatus('scanning');
      toast.success('Camera started! Point at QR code.');
      
    } catch (err) {
      console.error('Scanner error:', err);
      setError(`Camera error: ${err.message}. Please ensure camera permission is granted and try again.`);
      setScannerStatus('idle');
      setScanning(false);
    }
  };

  const stopScanner = async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
        scannerRef.current = null;
      } catch (e) {
        console.log('Error stopping scanner:', e);
      }
    }
    setScanning(false);
    setScannerStatus('idle');
  };

  const handleScan = async (qrCode) => {
    console.log('Processing QR code:', qrCode);
    
    if (!qrCode.startsWith('ATT-')) {
      setError('Invalid QR code format. Please scan the attendance QR code from your computer.');
      setScannerStatus('idle');
      return;
    }

    try {
      toast.loading('Verifying attendance...');
      
      const response = await api.post('/attendance/scan', {
        qr_code: qrCode,
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
      setScannerStatus('idle');
      
    } catch (error) {
      toast.dismiss();
      const errorMsg = error.response?.data?.detail || 'Failed to process QR code';
      setError(errorMsg);
      setResult({
        success: false,
        message: errorMsg
      });
      toast.error(errorMsg);
      setScannerStatus('idle');
    }
  };

  const registerDevice = async () => {
    if (!isLoggedIn) {
      toast.error('Please log in first to register this device');
      return;
    }

    try {
      const deviceName = /iPhone|iPad|iPod/.test(navigator.userAgent) ? 'iPhone' : 
                         /Android/.test(navigator.userAgent) ? 'Android Phone' : 'Mobile Device';
      
      const response = await api.post('/attendance/register-device', {
        device_token: deviceToken,
        device_name: deviceName
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
    setScannerStatus('idle');
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
        <div className="text-center mb-6 pt-4">
          <div className="w-14 h-14 bg-indigo-600 rounded-full flex items-center justify-center mx-auto mb-3">
            <Smartphone size={28} />
          </div>
          <h1 className="text-xl font-bold">Attendance Scanner</h1>
          <p className="text-slate-400 text-sm mt-1">Scan QR code from office computer</p>
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

        {/* Device Registration */}
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

        {/* Device Registered */}
        {isLoggedIn && deviceRegistered && (
          <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-3 mb-6">
            <div className="flex items-center gap-3">
              <CheckCircle className="text-emerald-500" size={20} />
              <div>
                <p className="font-medium text-emerald-200">Device Registered ✓</p>
                <p className="text-sm text-emerald-300">Logged in as {user?.name}</p>
              </div>
            </div>
          </div>
        )}

        {/* Scanner Area */}
        {isLoggedIn && deviceRegistered && !result && (
          <div className="mb-6">
            {/* QR Reader Container - Always render but control visibility */}
            <div 
              id="qr-reader-element" 
              className="bg-black rounded-xl overflow-hidden"
              style={{ 
                width: '100%',
                minHeight: '300px',
                display: scanning ? 'block' : 'none'
              }}
            />
            
            {/* Placeholder when not scanning */}
            {!scanning && (
              <div className="bg-slate-800 rounded-xl p-8 text-center">
                <Camera size={48} className="text-slate-500 mx-auto mb-4" />
                <p className="text-slate-400 mb-2">
                  {scannerStatus === 'starting' ? 'Starting camera...' : 'Ready to scan'}
                </p>
                <p className="text-slate-500 text-sm mb-4">
                  Tap the button below to open camera
                </p>
              </div>
            )}

            {/* Scanner Status */}
            {scanning && (
              <div className="mt-2 p-3 bg-indigo-900/50 rounded-lg text-center">
                <div className="flex items-center justify-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-indigo-300 text-sm">
                    {scannerStatus === 'processing' ? 'Processing QR code...' : 'Scanning... Point camera at QR code'}
                  </span>
                </div>
              </div>
            )}

            {/* Control Button */}
            <div className="mt-4">
              {!scanning ? (
                <button
                  onClick={startScanner}
                  disabled={scannerStatus === 'starting'}
                  className="w-full px-6 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
                >
                  {scannerStatus === 'starting' ? (
                    <>
                      <RefreshCw className="animate-spin" size={20} />
                      Starting Camera...
                    </>
                  ) : (
                    <>
                      <Camera size={20} />
                      Start Camera
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={stopScanner}
                  className="w-full px-6 py-4 bg-red-600 hover:bg-red-700 rounded-xl font-medium transition-colors"
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
              <div className="flex-1">
                <p className="font-medium text-red-200">Error</p>
                <p className="text-sm text-red-300 mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={resetAndScanAgain}
              className="mt-3 w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Success/Failure Result */}
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
                className="mt-6 w-full px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition-colors"
              >
                Scan Another QR
              </button>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-slate-800 rounded-xl p-4">
          <h3 className="font-semibold mb-3">How to check in:</h3>
          <ol className="text-sm text-slate-400 space-y-2">
            <li className="flex gap-2">
              <span className="text-indigo-400 font-bold">1.</span>
              Log in on office computer - QR code appears
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-400 font-bold">2.</span>
              Tap "Start Camera" button above
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-400 font-bold">3.</span>
              Point phone camera at the QR code
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-400 font-bold">4.</span>
              Wait for "Check-in Successful" message
            </li>
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
