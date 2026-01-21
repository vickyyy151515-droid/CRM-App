/**
 * AttendanceCodeEntry - Shows on computer after staff login
 * Staff enters 6-digit code from their Google Authenticator app
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { KeyRound, CheckCircle, Clock, AlertTriangle, LogOut, RefreshCw, Smartphone, Shield } from 'lucide-react';

export default function AttendanceCodeEntry({ onComplete, userName, onLogout }) {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [totpStatus, setTotpStatus] = useState(null);
  const [showSetup, setShowSetup] = useState(false);
  const [setupData, setSetupData] = useState(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [alreadyCheckedIn, setAlreadyCheckedIn] = useState(false);
  const [checkInTime, setCheckInTime] = useState(null);
  const [timeLeft, setTimeLeft] = useState(60);

  // Check TOTP status and attendance status
  const checkStatus = useCallback(async () => {
    setChecking(true);
    try {
      // Check if already checked in
      const attendanceRes = await api.get('/attendance/check-today');
      if (attendanceRes.data.checked_in) {
        setAlreadyCheckedIn(true);
        setCheckInTime(attendanceRes.data.check_in_time);
        toast.success('Already checked in! Redirecting...');
        setTimeout(() => onComplete(), 1500);
        return;
      }

      // Check TOTP setup status
      const totpRes = await api.get('/attendance/totp/status');
      setTotpStatus(totpRes.data);
      
      if (!totpRes.data.is_setup) {
        setShowSetup(true);
        await fetchSetupData();
      }
    } catch (error) {
      console.error('Status check error:', error);
    } finally {
      setChecking(false);
    }
  }, [onComplete]);

  // Fetch setup QR code
  const fetchSetupData = async () => {
    try {
      const response = await api.post('/attendance/totp/setup');
      setSetupData(response.data);
    } catch (error) {
      toast.error('Failed to generate setup code');
    }
  };

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Countdown timer for code expiry hint
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const seconds = now.getSeconds();
      setTimeLeft(60 - (seconds % 60));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Verify setup code
  const handleVerifySetup = async (e) => {
    e.preventDefault();
    if (verifyCode.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    try {
      await api.post('/attendance/totp/verify-setup', { code: verifyCode });
      toast.success('Authenticator verified! You can now check in.');
      setShowSetup(false);
      setTotpStatus({ is_setup: true });
      setVerifyCode('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  // Submit attendance code
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (code.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/attendance/checkin', { code });
      toast.success(`Checked in at ${response.data.check_in_time}!`);
      setTimeout(() => onComplete(), 1500);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in failed');
      setCode('');
    } finally {
      setLoading(false);
    }
  };

  // Handle code input (only numbers, max 6 digits)
  const handleCodeChange = (e, setter) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setter(value);
  };

  // Already checked in
  if (alreadyCheckedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center">
          <CheckCircle size={64} className="text-emerald-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Already Checked In!</h2>
          <p className="text-slate-600 mb-4">You checked in at {checkInTime}</p>
          <p className="text-sm text-slate-500">Redirecting to app...</p>
        </div>
      </div>
    );
  }

  // Loading
  if (checking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center p-4">
        <div className="text-center text-white">
          <RefreshCw className="animate-spin mx-auto mb-4" size={40} />
          <p>Checking status...</p>
        </div>
      </div>
    );
  }

  // Setup screen
  if (showSetup && setupData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Setup Authenticator</h2>
              <p className="text-slate-600 text-sm">One-time setup for {userName}</p>
            </div>
            {onLogout && (
              <button onClick={onLogout} className="text-red-500 hover:text-red-700">
                <LogOut size={20} />
              </button>
            )}
          </div>

          {/* Step 1: Scan QR */}
          <div className="bg-slate-50 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
              <h3 className="font-semibold text-slate-900">Scan with Google Authenticator</h3>
            </div>
            <div className="flex justify-center mb-3">
              <img src={setupData.qr_code} alt="Setup QR Code" className="w-48 h-48" />
            </div>
            <p className="text-xs text-slate-500 text-center">
              Open Google Authenticator → Tap + → Scan QR code
            </p>
          </div>

          {/* Manual entry option */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
            <p className="text-xs text-amber-800">
              <strong>Can&apos;t scan?</strong> Enter this code manually in your app:
            </p>
            <code className="block mt-1 text-xs bg-white p-2 rounded border font-mono break-all">
              {setupData.secret}
            </code>
          </div>

          {/* Step 2: Verify */}
          <div className="bg-slate-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
              <h3 className="font-semibold text-slate-900">Enter code to verify</h3>
            </div>
            <form onSubmit={handleVerifySetup}>
              <input
                type="text"
                inputMode="numeric"
                value={verifyCode}
                onChange={(e) => handleCodeChange(e, setVerifyCode)}
                placeholder="000000"
                className="w-full text-center text-3xl font-mono tracking-widest py-3 border-2 border-slate-300 rounded-lg focus:border-indigo-500 focus:outline-none"
                maxLength={6}
                autoFocus
              />
              <button
                type="submit"
                disabled={loading || verifyCode.length !== 6}
                className="w-full mt-3 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white rounded-lg font-medium flex items-center justify-center gap-2"
              >
                {loading ? <RefreshCw className="animate-spin" size={18} /> : <Shield size={18} />}
                Verify & Complete Setup
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Main check-in screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Attendance Check-in</h2>
            <p className="text-slate-600">Hello, {userName}!</p>
          </div>
          {onLogout && (
            <button onClick={onLogout} className="text-red-500 hover:text-red-700">
              <LogOut size={20} />
            </button>
          )}
        </div>

        {/* Code Entry */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Smartphone className="text-indigo-600" size={24} />
            <p className="text-slate-700">Enter code from Google Authenticator</p>
          </div>

          <form onSubmit={handleSubmit}>
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => handleCodeChange(e, setCode)}
              placeholder="000000"
              className="w-full text-center text-4xl font-mono tracking-[0.5em] py-4 border-2 border-slate-300 rounded-xl focus:border-indigo-500 focus:outline-none"
              maxLength={6}
              autoFocus
              autoComplete="one-time-code"
            />

            {/* Timer hint */}
            <div className="flex items-center justify-center gap-2 mt-3 text-sm">
              <Clock size={16} className={timeLeft <= 10 ? 'text-red-500' : 'text-slate-400'} />
              <span className={timeLeft <= 10 ? 'text-red-500' : 'text-slate-500'}>
                Code changes in {timeLeft}s
              </span>
            </div>

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full mt-4 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white rounded-xl font-bold text-lg flex items-center justify-center gap-2"
            >
              {loading ? (
                <RefreshCw className="animate-spin" size={20} />
              ) : (
                <KeyRound size={20} />
              )}
              Check In
            </button>
          </form>
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-blue-600 shrink-0 mt-0.5" size={20} />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">How to check in:</p>
              <ol className="space-y-1 text-blue-700">
                <li>1. Open Google Authenticator on your phone</li>
                <li>2. Find &quot;CRM Attendance&quot; entry</li>
                <li>3. Type the 6-digit code above</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Reset option */}
        <button
          onClick={() => { setShowSetup(true); fetchSetupData(); }}
          className="w-full mt-4 text-sm text-slate-500 hover:text-indigo-600"
        >
          Need to set up authenticator again?
        </button>

        {/* Skip (for testing) */}
        <button
          onClick={onComplete}
          className="w-full mt-2 text-xs text-slate-400 hover:text-slate-600"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
