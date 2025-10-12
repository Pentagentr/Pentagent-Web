// Kayıt sayfası - dark lacivert, buz efektli, transparan tasarım
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Lock, Mail, User, UserPlus, AlertCircle, CheckCircle } from 'lucide-react';
import '../styles/auth.css';

const RegisterPage = () => {
  const [formData, setFormData] = useState({
    displayName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup, currentUser } = useAuth();
  const navigate = useNavigate();

  // Eğer kullanıcı zaten giriş yapmışsa, ana sayfaya yönlendir
  useEffect(() => {
    if (currentUser) {
      navigate('/');
    }
  }, [currentUser, navigate]);


  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const validateForm = () => {
    const { displayName, email, password, confirmPassword } = formData;

    if (!displayName || !email || !password || !confirmPassword) {
      setError('Lütfen tüm alanları doldurun');
      return false;
    }

    if (displayName.length < 2) {
      setError('İsim en az 2 karakter olmalıdır');
      return false;
    }

    if (password.length < 6) {
      setError('Şifre en az 6 karakter olmalıdır');
      return false;
    }

    if (password !== confirmPassword) {
      setError('Şifreler eşleşmiyor');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      await signup(formData.email, formData.password, formData.displayName);
      navigate('/');
    } catch (error) {
      console.error('Signup error:', error);
      
      // Türkçe hata mesajları
      switch (error.code) {
        case 'auth/email-already-in-use':
          setError('Bu e-posta adresi zaten kullanımda');
          break;
        case 'auth/invalid-email':
          setError('Geçersiz e-posta adresi');
          break;
        case 'auth/operation-not-allowed':
          setError('Bu işlem şu anda kullanılamıyor');
          break;
        case 'auth/weak-password':
          setError('Şifre çok zayıf');
          break;
        default:
          setError('Kayıt olurken bir hata oluştu');
      }
    } finally {
      setLoading(false);
    }
  };

  // Şifre gücü göstergesi
  const getPasswordStrength = (password) => {
    if (!password) return { strength: 0, text: '', color: '' };
    
    let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z\d]/.test(password)) strength++;

    const levels = [
      { strength: 0, text: '', color: '' },
      { strength: 1, text: 'Zayıf', color: 'text-red-400' },
      { strength: 2, text: 'Orta', color: 'text-yellow-400' },
      { strength: 3, text: 'İyi', color: 'text-green-400' },
      { strength: 4, text: 'Güçlü', color: 'text-cyan-400' },
      { strength: 5, text: 'Çok Güçlü', color: 'text-cyan-300' }
    ];

    return levels[Math.min(strength, 5)];
  };

  const passwordStrength = getPasswordStrength(formData.password);

  return (
    <div className="min-h-screen auth-background flex items-center justify-center p-4">
      {/* Register container */}
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

        {/* Register form */}
        <div className="glass-panel rounded-xl p-5 shadow-2xl">
          <div className="text-center mb-4">
            <h2 className="text-lg font-semibold text-platinum">Create Account</h2>
            <p className="mt-1 text-platinum-tertiary text-xs">
              Join the security platform
            </p>
          </div>

          {/* Error mesajı */}
          {error && (
            <div className="auth-error rounded-lg p-2 mb-3 flex items-center gap-2 text-rose-400 text-xs">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            {/* Display Name input */}
            <div>
              <label htmlFor="displayName" className="block text-xs font-medium text-platinum-secondary mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User size={14} className="text-platinum-tertiary" />
                </div>
                <input
                  id="displayName"
                  name="displayName"
                  type="text"
                  value={formData.displayName}
                  onChange={handleChange}
                  placeholder="John Doe"
                  className="auth-input w-full pl-9 pr-3 py-2 rounded-lg text-xs"
                  disabled={loading}
                />
              </div>
            </div>

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
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
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
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••••••"
                  className="auth-input w-full pl-9 pr-3 py-2 rounded-lg text-xs"
                  disabled={loading}
                />
              </div>
              {formData.password && (
                <p className={`mt-1 text-[10px] ${passwordStrength.color}`}>
                  Strength: {passwordStrength.text}
                </p>
              )}
            </div>

            {/* Confirm Password input */}
            <div>
              <label htmlFor="confirmPassword" className="block text-xs font-medium text-platinum-secondary mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock size={14} className="text-platinum-tertiary" />
                </div>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••••••"
                  className="auth-input w-full pl-9 pr-3 py-2 rounded-lg text-xs"
                  disabled={loading}
                />
                {formData.confirmPassword && formData.password === formData.confirmPassword && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <CheckCircle size={14} className="text-success" />
                  </div>
                )}
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
                  <span>Creating account...</span>
                </>
              ) : (
                <>
                  <UserPlus size={14} />
                  <span>Create Account</span>
                </>
              )}
            </button>
          </form>

          {/* Giriş yap linki */}
          <div className="mt-4 text-center pt-4 border-t border-platinum-500/10">
            <p className="text-platinum-tertiary text-xs">
              Already have an account?{' '}
              <Link
                to="/login"
                className="auth-link font-medium"
              >
                Login
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

export default RegisterPage;

