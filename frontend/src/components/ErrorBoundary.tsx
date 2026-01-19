import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from './ui/Button';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-md w-full space-y-8 text-center">
            <div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                Algo salió mal
              </h2>
              <p className="mt-2 text-sm text-gray-600">
                Ha ocurrido un error inesperado en la aplicación.
              </p>
              {this.state.error && (
                <div className="mt-4 p-4 bg-red-50 rounded-md text-left overflow-auto max-h-48">
                    <p className="text-xs text-red-800 font-mono">
                        {this.state.error.toString()}
                    </p>
                </div>
              )}
            </div>
            <div className="mt-5">
                <Button onClick={() => window.location.reload()}>
                    Recargar Página
                </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
