import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ChatPage from './pages/ChatPage';
import RagSearch from './pages/RagSearch';
import ErrorBoundary from './components/common/ErrorBoundary';
// import Reports from './pages/Reports';
// import Dashboard from './pages/Dashboard';
// import LandingPage from './pages/LandingPage';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthProvider>
          <Routes>
            {/* Public routes - Authentication */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Protected routes - Ana uygulama */}
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <ChatPage />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/rag-search" 
              element={
                <ProtectedRoute>
                  <RagSearch />
                </ProtectedRoute>
              } 
            />
            
            {/* Reports sayfası (gelecekte) */}
            {/* <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} /> */}
            
            {/* Dashboard sayfası (gelecekte) */}
            {/* <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} /> */}
            
            {/* Landing page (gelecekte) */}
            {/* <Route path="/landing" element={<LandingPage />} /> */}
            
            {/* 404 - Login sayfasına yönlendir */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </AuthProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
