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
  const scannerRef = useRef(null);
  const html5QrCodeRef = useRef(null);

  // Generate or retrieve device token
  useEffect(() => {
    let token = localStorage.getItem('attendance_device_token');
    if (!token) {
      // Generate unique device token
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

  const startScanner = async () => {
    setScanning(true);
    setError(null);
    setResult(null);

    try {
      const html5QrCode = new Html5Qrcode("qr-reader");
      html5QrCodeRef.current = html5QrCode;

      await html5QrCode.start(
        { facingMode: "environment" },
        {
          fps: 10,
          qrbox: { width: 250, height: 250 }
        },
        async (decodedText) => {
          // QR code scanned successfully
          await html5QrCode.stop();
          setScanning(false);
          await handleScan(decodedText);
        },
        (errorMessage) => {
          // Ignore scan errors (normal during scanning)
        }
      );
    } catch (err) {
      setError('Failed to start camera. Please ensure camera permissions are granted.');
      setScanning(false);
    }
  };

  const stopScanner = async () => {
    if (html5QrCodeRef.current) {
      try {
        await html5QrCodeRef.current.stop();
      } catch (err) {
        // Ignore
      }
    }
    setScanning(false);
  };

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
        <div className="text-center mb-8 pt-8">
          <div className="w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Smartphone size={32} />
          </div>
          <h1 className="text-2xl font-bold">Attendance Scanner</h1>
          <p className="text-slate-400 mt-1">Scan the QR code on your computer</p>
        </div>

        {/* Device Registration Status */}
        {isLoggedIn && !deviceRegistered && (
          <div className="bg-amber-900/50 border border-amber-600 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-amber-500 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-amber-200">Device Not Registered</p>
                <p className="text-sm text-amber-300 mt-1">
                  This phone is not registered to your account. Register it to use for attendance.
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
          <div className="bg-emerald-900/50 border border-emerald-600 rounded-lg p-4 mb-6">
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
        {!result && (
          <div className="bg-slate-800 rounded-xl overflow-hidden mb-6">
            <div 
              id="qr-reader" 
              ref={scannerRef}
              className={`${scanning ? 'block' : 'hidden'}`}
              style={{ width: '100%' }}
            />
            
            {!scanning && (
              <div className="p-8 text-center">
                <Camera size={48} className="text-slate-500 mx-auto mb-4" />
                <p className="text-slate-400 mb-4">
                  {deviceRegistered 
                    ? 'Tap the button below to start scanning'
                    : 'Register your device first, then scan the QR code'}
                </p>
                <button
                  onClick={startScanner}
                  disabled={!deviceRegistered}
                  className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                >
                  Start Scanner
                </button>
              </div>
            )}

            {scanning && (
              <div className="p-4 text-center">
                <p className="text-slate-400 mb-2">Point camera at QR code</p>
                <button
                  onClick={stopScanner}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors"
                >
                  Stop Scanner
                </button>
              </div>
            )}
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

        {/* Login Prompt */}
        {!isLoggedIn && (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <p className="text-slate-400 mb-4">
              Please log in on this device to register it for attendance scanning.
            </p>
            <a
              href="/"
              className="inline-block px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium transition-colors"
            >
              Go to Login
            </a>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-slate-800 rounded-xl p-4 mt-6">
          <h3 className="font-semibold mb-3">Instructions</h3>
          <ol className="text-sm text-slate-400 space-y-2">
            <li>1. Log in on your computer at the office</li>
            <li>2. A QR code will appear on screen</li>
            <li>3. Open this scanner on your registered phone</li>
            <li>4. Scan the QR code to check in</li>
          </ol>
        </div>

        {/* Device Info */}
        <div className="mt-6 text-center text-xs text-slate-500">
          <p>Device ID: {deviceToken?.slice(-8)}</p>
        </div>
      </div>
    </div>
  );
}
