import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { QrCode, RefreshCw, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import QRCode from 'react-qr-code';

export default function AttendanceQRScreen({ onComplete, userName }) {
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeLeft, setTimeLeft] = useState(60);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [alreadyCheckedIn, setAlreadyCheckedIn] = useState(false);
  const [checkInTime, setCheckInTime] = useState(null);

  const generateQR = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.post('/attendance/generate-qr');
      
      if (response.data.already_checked_in) {
        setAlreadyCheckedIn(true);
        setCheckInTime(response.data.check_in_time);
        setTimeout(() => onComplete(), 2000);
        return;
      }
      
      setQrData(response.data);
      setTimeLeft(response.data.expires_in_seconds || 60);
    } catch (error) {
      toast.error('Failed to generate QR code');
    } finally {
      setLoading(false);
    }
  }, [onComplete]);

  // Check attendance status periodically
  const checkStatus = useCallback(async () => {
    if (checkingStatus) return;
    setCheckingStatus(true);
    
    try {
      const response = await api.get('/attendance/check-today');
      if (response.data.checked_in) {
        setAlreadyCheckedIn(true);
        setCheckInTime(response.data.check_in_time);
        toast.success('Attendance recorded! Redirecting...');
        setTimeout(() => onComplete(), 1500);
      }
    } catch (error) {
      // Silently fail
    } finally {
      setCheckingStatus(false);
    }
  }, [checkingStatus, onComplete]);

  useEffect(() => {
    generateQR();
  }, [generateQR]);

  // Countdown timer
  useEffect(() => {
    if (!qrData || alreadyCheckedIn) return;
    
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          // QR expired, generate new one
          generateQR();
          return 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [qrData, alreadyCheckedIn, generateQR]);

  // Check status every 3 seconds
  useEffect(() => {
    if (alreadyCheckedIn) return;
    
    const statusCheck = setInterval(checkStatus, 3000);
    return () => clearInterval(statusCheck);
  }, [alreadyCheckedIn, checkStatus]);

  if (alreadyCheckedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center">
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle size={48} className="text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Already Checked In!</h2>
          <p className="text-slate-600 mb-4">
            You checked in at {checkInTime ? new Date(checkInTime).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) : 'earlier today'}
          </p>
          <p className="text-sm text-slate-500">Redirecting to app...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <QrCode size={32} className="text-indigo-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Attendance Check-in</h2>
          <p className="text-slate-600 mt-1">Hello, {userName}!</p>
        </div>

        {/* QR Code */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="animate-spin text-indigo-600" size={40} />
            </div>
          ) : qrData ? (
            <div className="flex flex-col items-center">
              <div className="bg-white p-4 rounded-lg shadow-inner">
                <QRCode 
                  value={qrData.qr_code} 
                  size={200}
                  level="H"
                />
              </div>
              
              {/* Timer */}
              <div className="mt-4 flex items-center gap-2">
                <Clock size={18} className={timeLeft <= 10 ? 'text-red-500' : 'text-slate-500'} />
                <span className={`font-mono text-lg font-bold ${timeLeft <= 10 ? 'text-red-500' : 'text-slate-700'}`}>
                  {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
                </span>
              </div>
              
              {timeLeft <= 10 && (
                <p className="text-red-500 text-sm mt-2">QR code expiring soon!</p>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <AlertTriangle size={40} className="text-amber-500 mx-auto mb-2" />
              <p className="text-slate-600">Failed to generate QR code</p>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-blue-900 mb-2">How to check in:</h3>
          <ol className="text-sm text-blue-800 space-y-1">
            <li>1. Open the scanner on your <strong>registered phone</strong></li>
            <li>2. Scan this QR code before it expires</li>
            <li>3. Wait for confirmation</li>
          </ol>
        </div>

        {/* Refresh Button */}
        <button
          onClick={generateQR}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          Generate New QR Code
        </button>

        {/* Scanner Link */}
        <div className="mt-4 text-center">
          <p className="text-sm text-slate-500">
            Need to register your device?{' '}
            <a 
              href="/attendance-scanner" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-indigo-600 hover:underline font-medium"
            >
              Open Scanner
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
