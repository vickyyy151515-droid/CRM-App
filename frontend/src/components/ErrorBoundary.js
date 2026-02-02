import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="text-red-600 dark:text-red-400" size={24} />
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-300">
              Something went wrong
            </h3>
          </div>
          <p className="text-red-700 dark:text-red-400 mb-4">
            {this.props.fallbackMessage || 'There was an error loading this content. This might be caused by invalid data in the database.'}
          </p>
          <button
            onClick={this.handleReset}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <RefreshCw size={16} />
            Try Again
          </button>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-4 text-xs text-red-600 dark:text-red-400">
              <summary className="cursor-pointer">Error Details</summary>
              <pre className="mt-2 p-2 bg-red-100 dark:bg-red-900/50 rounded overflow-auto">
                {this.state.error.toString()}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
