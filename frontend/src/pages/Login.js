import { useState } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import { Eye, EyeOff, RefreshCw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function Login({ onLogin }) {
  const { t } = useLanguage();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [serviceError, setServiceError] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setServiceError(false);

    try {
      const response = await api.post('/auth/login', { email, password });
      toast.success(t('common.success') + '!');
      onLogin(response.data.user, response.data.token);
    } catch (error) {
      // Handle service unavailable (503) - server restarting
      if (error.response?.status === 503 || !error.response) {
        setServiceError(true);
        toast.error('Service temporarily unavailable. Please wait and try again.', { duration: 5000 });
      } else {
        toast.error(error.response?.data?.detail || t('auth.invalidCredentials'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      <div className="w-full lg:w-2/5 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 mb-3">
              CRM Pro
            </h1>
            <p className="text-base leading-relaxed text-slate-600">
              {t('auth.loginSubtitle')}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
                className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
                placeholder="admin@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                {t('auth.password')}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  data-testid="login-password-input"
                  className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
                  placeholder={t('auth.password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  data-testid="toggle-password-visibility"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Service Error Banner */}
            {serviceError && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
                <RefreshCw size={18} className="text-amber-600 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-800">Service temporarily unavailable</p>
                  <p className="text-xs text-amber-600">The server is restarting. Please wait a moment and try again.</p>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="w-full bg-slate-900 text-white hover:bg-slate-800 shadow-sm font-medium px-6 py-2.5 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('auth.loggingIn') : t('auth.loginButton')}
            </button>
          </form>

          <div className="mt-8 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <p className="text-sm text-slate-600 mb-2 font-medium">Demo Credentials:</p>
            <p className="text-xs text-slate-500">Admin: admin@crm.com / admin123</p>
            <p className="text-xs text-slate-500">Staff: staff@crm.com / staff123</p>
          </div>
        </div>
      </div>

      <div className="hidden lg:block lg:w-3/5 relative overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1758873271761-6cfe9b4f000c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTJ8MHwxfHNlYXJjaHwxfHxjb3Jwb3JhdGUlMjBvZmZpY2UlMjB0ZWFtJTIwd29ya2luZyUyMGRpdmVyc2V8ZW58MHx8fHwxNzY4MjE5MjEwfDA&ixlib=rb-4.1.0&q=85"
          alt="Corporate team collaboration"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-slate-900/20 flex items-end p-12">
          <div className="text-white">
            <h2 className="text-3xl font-semibold tracking-tight mb-3">
              {t('auth.loginTitle')}
            </h2>
            <p className="text-base leading-relaxed text-slate-200">
              {t('auth.loginSubtitle')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}