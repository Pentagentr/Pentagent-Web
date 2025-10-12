// Giriş sayfası - dark lacivert, buz efektli, transparan tasarım
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Lock, Mail, LogIn, AlertCircle } from 'lucide-react';
import '../styles/auth.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, currentUser } = useAuth();
  const navigate = useNavigate();

  // Eğer kullanıcı zaten giriş yapmışsa, ana sayfaya yönlendir
  useEffect(() => {
    if (currentUser) {
      navigate('/');
    }
  }, [currentUser, navigate]);


  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validasyon
    if (!email || !password) {
      setError('Lütfen tüm alanları doldurun');
      return;
    }

    try {
      setLoading(true);
      await login(email, password);
      navigate('/');
    } catch (error) {
      console.error('Login error:', error);
      
      // Türkçe hata mesajları
      switch (error.code) {
        case 'auth/invalid-email':
          setError('Geçersiz e-posta adresi');
          break;
        case 'auth/user-disabled':
          setError('Bu hesap devre dışı bırakılmış');
          break;
        case 'auth/user-not-found':
          setError('Kullanıcı bulunamadı');
          break;
        case 'auth/wrong-password':
          setError('Hatalı şifre');
          break;
        case 'auth/invalid-credential':
          setError('E-posta veya şifre hatalı');
          break;
        default:
          setError('Giriş yapılırken bir hata oluştu');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen auth-background flex items-center justify-center p-4">
      {/* Login container */}
      <div className="relative z-10 w-full max-w-sm">
        {/* Logo ve başlık - Animated */}
        <div className="text-center mb-6 logo-container">
          <div className="inline-block logo-glow">
            <div className="text-2xl font-bold tracking-tight bg-gradient-to-r from-platinum-400 via-platinum-500 to-purple-400 bg-clip-text text-transparent">
              PENTAGENT
            </div>
          </div>
          <p className="mt-2 text-platinum-tertiary text-[11px] font-light tracking-wider uppercase">
            AI-Powered Penetration Testing
          </p>
          <div className="mt-1.5 w-16 h-[1px] mx-auto bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-50"></div>
        </div>

        {/* Login form */}
        <div className="glass-panel rounded-xl p-5 shadow-2xl">
          <div className="text-center mb-4">
            <h2 className="text-lg font-semibold text-platinum">Secure Login</h2>
            <p className="mt-1 text-platinum-tertiary text-xs">
              Access your security dashboard
            </p>
          </div>

          {/* Error mesajı */}
          {error && (
            <div className="auth-error rounded-lg p-2 mb-3 flex items-center gap-2 text-rose-400 text-xs">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {/* Email input */}
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-platinum-secondary mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail size={14} className="text-platinum-tertiary" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="auth-input w-full pl-9 pr-3 py-2 rounded-lg text-xs"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Password input */}
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-platinum-secondary mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock size={14} className="text-platinum-tertiary" />
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="auth-input w-full pl-9 pr-3 py-2 rounded-lg text-xs"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="auth-button w-full py-2.5 rounded-lg text-white text-xs font-semibold flex items-center justify-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
            >
              {loading ? (
                <>
                  <div className="auth-loader"></div>
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <LogIn size={14} />
                  <span>Login</span>
                </>
              )}
            </button>
          </form>

          {/* Kayıt ol linki */}
          <div className="mt-4 text-center pt-4 border-t border-platinum-500/10">
            <p className="text-platinum-tertiary text-xs">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="auth-link font-medium"
              >
                Create Account
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-4 text-center">
          <p className="text-platinum-tertiary/40 text-[10px]">
            © 2025 Pentagent
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;

