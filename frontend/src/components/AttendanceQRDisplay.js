/**
 * AttendanceQRDisplay - Shows QR code on computer for staff to scan
 * Displayed after staff logs in (before they can access the app)
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { QrCode, RefreshCw, CheckCircle, Clock, AlertTriangle, LogOut, ExternalLink } from 'lucide-react';
import QRCode from 'react-qr-code';

export default function AttendanceQRDisplay({ onComplete, userName, onLogout }) {
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeLeft, setTimeLeft] = useState(60);
  const [alreadyCheckedIn, setAlreadyCheckedIn] = useState(false);
  const [checkInTime, setCheckInTime] = useState(null);

  // Generate new QR code
  const generateQR = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.post('/attendance/generate-qr');
      
      if (response.data.already_checked_in) {
        setAlreadyCheckedIn(true);
        setCheckInTime(response.data.check_in_time);
        toast.success('Already checked in! Redirecting...');
        setTimeout(() => onComplete(), 1500);
        return;
      }
      
      setQrData(response.data);
      setTimeLeft(response.data.expires_in_seconds || 60);
    } catch (error) {
      toast.error('Failed to generate QR code');
      console.error('QR generation error:', error);
    } finally {
      setLoading(false);
    }
  }, [onComplete]);

  // Check if staff has checked in (poll every 3 seconds)
  const checkStatus = useCallback(async () => {
    try {
      const response = await api.get('/attendance/check-today');
      if (response.data.checked_in) {
        setAlreadyCheckedIn(true);
        setCheckInTime(response.data.check_in_time);
        toast.success('Attendance recorded! Redirecting...');
        setTimeout(() => onComplete(), 1500);
      }
    } catch (error) {
      // Silently fail - will retry
    }
  }, [onComplete]);

  // Initial load
  useEffect(() => {
    generateQR();
  }, [generateQR]);

  // Countdown timer - refresh QR every minute
  useEffect(() => {
    if (!qrData || alreadyCheckedIn) return;
    
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          generateQR(); // Get new QR when expired
          return 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [qrData, alreadyCheckedIn, generateQR]);

  // Poll for check-in status
  useEffect(() => {
    if (alreadyCheckedIn) return;
    
    const statusCheck = setInterval(checkStatus, 3000);
    return () => clearInterval(statusCheck);
  }, [alreadyCheckedIn, checkStatus]);

  // Already checked in view
  if (alreadyCheckedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center">
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle size={48} className="text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Already Checked In!</h2>
          <p className="text-slate-600 mb-4">
            You checked in at {checkInTime || 'earlier today'}
          </p>
          <p className="text-sm text-slate-500">Redirecting to app...</p>
        </div>
      </div>
    );
  }

  const scannerUrl = `${window.location.origin}/attendance-scanner`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-lg w-full">
        {/* Header with logout */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Attendance Check-in</h2>
            <p className="text-slate-600">Hello, {userName}!</p>
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              className="flex items-center gap-1 text-sm text-red-500 hover:text-red-700 transition-colors"
              data-testid="logout-btn"
            >
              <LogOut size={16} />
              Logout
            </button>
          )}
        </div>

        {/* QR Code Display */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="animate-spin text-indigo-600" size={40} />
            </div>
          ) : qrData ? (
            <div className="flex flex-col items-center">
              <div className="bg-white p-4 rounded-lg shadow-inner border-4 border-indigo-100">
                <QRCode 
                  value={qrData.qr_code} 
                  size={220}
                  level="H"
                />
              </div>
              
              {/* Timer */}
              <div className="mt-4 flex items-center gap-2">
                <Clock size={20} className={timeLeft <= 10 ? 'text-red-500' : 'text-slate-500'} />
                <span className={`font-mono text-2xl font-bold ${timeLeft <= 10 ? 'text-red-500' : 'text-slate-700'}`}>
                  {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
                </span>
              </div>
              
              {timeLeft <= 10 && (
                <p className="text-red-500 text-sm mt-2 animate-pulse">QR code expiring soon!</p>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <AlertTriangle size={40} className="text-amber-500 mx-auto mb-2" />
              <p className="text-slate-600">Failed to generate QR code</p>
              <button
                onClick={generateQR}
                className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <QrCode className="text-blue-600 shrink-0 mt-1" size={24} />
            <div>
              <h3 className="font-semibold text-blue-900 mb-2">How to check in:</h3>
              <ol className="text-sm text-blue-800 space-y-1">
                <li>1. Open the scanner on your <strong>registered phone</strong></li>
                <li>2. Take a photo of this QR code</li>
                <li>3. Wait for confirmation</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Scanner Link */}
        <div className="bg-slate-100 rounded-lg p-4 mb-4">
          <p className="text-sm text-slate-600 mb-2">Scanner link for your phone:</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs bg-white px-3 py-2 rounded border truncate">
              {scannerUrl}
            </code>
            <a
              href={scannerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
              title="Open Scanner"
            >
              <ExternalLink size={16} />
            </a>
          </div>
        </div>

        {/* Refresh Button */}
        <button
          onClick={generateQR}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
          data-testid="refresh-qr-btn"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          Generate New QR Code
        </button>

        {/* Skip option (for testing/emergency) */}
        <button
          onClick={onComplete}
          className="w-full mt-3 text-sm text-slate-500 hover:text-slate-700"
          data-testid="skip-attendance-btn"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
