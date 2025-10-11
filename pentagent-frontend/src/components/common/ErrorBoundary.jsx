import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div className="min-h-screen bg-obsidian-950 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-obsidian-900 border border-rose-500/30 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-rose-500/20 rounded-lg flex items-center justify-center">
                <span className="text-rose-500 text-xl">⚠️</span>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-text-primary">Uygulama Hatası</h2>
                <p className="text-sm text-text-secondary">Bir hata oluştu</p>
              </div>
            </div>
            
            <div className="space-y-3">
              <p className="text-sm text-text-secondary">
                Uygulamada beklenmeyen bir hata oluştu. Lütfen sayfayı yenileyin.
              </p>
              
              {this.state.error && (
                <details className="text-xs text-text-tertiary">
                  <summary className="cursor-pointer text-text-secondary hover:text-text-primary">
                    Hata Detayları
                  </summary>
                  <pre className="mt-2 p-2 bg-obsidian-850 rounded border overflow-auto">
                    {this.state.error.toString()}
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
              
              <div className="flex gap-2">
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-platinum-500 text-obsidian-950 rounded-lg hover:bg-platinum-400 transition-colors"
                >
                  Sayfayı Yenile
                </button>
                <button
                  onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
                  className="px-4 py-2 bg-obsidian-700 text-text-primary rounded-lg hover:bg-obsidian-600 transition-colors"
                >
                  Tekrar Dene
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
