// frontend/src/pages/LoginPage.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { 
  Shield, 
  Lock, 
  Mail, 
  ArrowRight, 
  AlertCircle, 
  Building2,
  Eye,
  EyeOff,
  Sun,
  Moon,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();

  const [email, setEmail] = useState('admin@acme.com');
  const [password, setPassword] = useState('Password123!');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemo = (demoEmail) => {
    setEmail(demoEmail);
    setPassword('Password123!');
  };

  return (
    <div className="min-h-screen app-mesh-bg flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden transition-colors duration-200">
      {/* Theme Toggle in top-right corner */}
      <div className="absolute top-6 right-6 z-20">
        <button
          onClick={toggleTheme}
          className="p-2.5 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400 transition shadow-sm"
          title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-600" />}
        </button>
      </div>

      {/* Decorative ambient gradient blooms */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-gradient-to-tr from-cyan-400/20 via-blue-500/10 to-indigo-500/20 blur-3xl pointer-events-none rounded-full dark:opacity-30" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10 space-y-3">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 text-white shadow-lg shadow-cyan-500/25 mx-auto">
          <Shield className="w-8 h-8" />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            ObserveVault
          </h1>
          <p className="text-xs font-semibold text-cyan-600 dark:text-cyan-400 uppercase tracking-widest mt-0.5 font-mono">
            Observe · Analyze · Optimize
          </p>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
          Privacy-First Intelligent Observability Platform with Tier-1 Edge Sanitization
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="glass-card py-8 px-6 sm:px-10 rounded-2xl shadow-soft-lg space-y-6">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-500/30 flex items-center gap-2 text-rose-800 dark:text-rose-300 text-xs animate-shake">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                Work Email Address
              </label>
              <div className="mt-1 relative rounded-xl shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@acme.com"
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                Password
              </label>
              <div className="mt-1 relative rounded-xl shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-10 pr-10 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 transition-all duration-200 shadow-md shadow-blue-500/25 disabled:opacity-50 active:scale-[0.99]"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Platform</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Switcher Cards */}
          <div className="pt-4 border-t border-slate-100 dark:border-white/5 space-y-3">
            <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider text-center">
              Multi-Tenant Demo Credentials
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => handleQuickDemo('admin@acme.com')}
                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-cyan-500 hover:bg-cyan-50/50 dark:hover:bg-slate-800/60 text-left transition space-y-0.5 group shadow-2xs"
              >
                <div className="flex items-center gap-1.5 text-cyan-700 dark:text-cyan-400 font-bold text-xs">
                  <Building2 className="w-3.5 h-3.5" />
                  <span>Acme FinTech</span>
                </div>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">admin@acme.com</p>
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemo('admin@biohealth.com')}
                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-purple-500 hover:bg-purple-50/50 dark:hover:bg-slate-800/60 text-left transition space-y-0.5 group shadow-2xs"
              >
                <div className="flex items-center gap-1.5 text-purple-700 dark:text-purple-400 font-bold text-xs">
                  <Building2 className="w-3.5 h-3.5" />
                  <span>BioHealth Global</span>
                </div>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">admin@biohealth.com</p>
              </button>
            </div>
            <p className="text-[10px] text-center text-slate-400 dark:text-slate-500">
              Demo Password: <code className="text-cyan-600 dark:text-cyan-400 font-bold">Password123!</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
