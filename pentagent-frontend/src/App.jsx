import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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
        <Routes>
          {/* Ana chat sayfası */}
          <Route path="/" element={<ChatPage />} />
          
          {/* RAG arama sayfası */}
          <Route path="/rag-search" element={<RagSearch />} />
          
          {/* Reports sayfası (gelecekte) */}
          {/* <Route path="/reports" element={<Reports />} /> */}
          
          {/* Dashboard sayfası (gelecekte) */}
          {/* <Route path="/dashboard" element={<Dashboard />} /> */}
          
          {/* Landing page (gelecekte) */}
          {/* <Route path="/landing" element={<LandingPage />} /> */}
          
          {/* 404 - Ana sayfaya yönlendir */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
