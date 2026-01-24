import { Loader2 } from 'lucide-react';
import { Button } from './Button';

interface LoadingModalProps {
  isOpen: boolean;
  message?: string;
  progress?: number; // 0-100
  isIndeterminate?: boolean;
  onCancel?: () => void;
}

export default function LoadingModal({ isOpen, message = 'Cargando...', progress, isIndeterminate = true, onCancel }: LoadingModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-50 z-50 flex items-center justify-center backdrop-blur-sm transition-all">
      <div className="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 flex flex-col items-center animate-in fade-in zoom-in duration-200">
        
        {/* Icon & Spinner */}
        <div className="relative mb-6">
            <div className="absolute inset-0 bg-blue-100 rounded-full animate-ping opacity-25"></div>
            <div className="relative bg-blue-50 p-4 rounded-full">
                <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
            </div>
        </div>

        {/* Text */}
        <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
            Procesando Solicitud
        </h3>
        <p className="text-gray-500 text-center text-sm mb-6">
            {message}
        </p>

        {/* Progress Bar Container */}
        <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden shadow-inner">
            {isIndeterminate ? (
                 // Indeterminate Animation (Moving stripe)
                <div className="h-full w-full bg-blue-100 relative overflow-hidden">
                    <div className="absolute top-0 left-0 bottom-0 right-0 bg-gradient-to-r from-transparent via-blue-400 to-transparent w-1/2 animate-[shimmer_1.5s_infinite] translate-x-[-100%]" style={{ content: '""' }}></div>
                </div>
            ) : (
                // Determinate Progress
                <div 
                    className="bg-blue-600 h-full rounded-full transition-all duration-300 ease-out flex items-center justify-end"
                    style={{ width: `${Math.max(5, progress || 0)}%` }}
                >
                </div>
            )}
        </div>
        
        {/* Percentage or Status Text */}
        <div className="mt-3 flex justify-between w-full text-xs text-gray-400">
            <span>{isIndeterminate ? 'Por favor espere...' : 'Subiendo archivos...'}</span>
            {!isIndeterminate && progress !== undefined && (
                 <span className="font-medium text-gray-600">{Math.round(progress)}%</span>
            )}
        </div>

        {/* Cancel Button */}
        {onCancel && (
            <div className="mt-6 w-full flex justify-center">
                <button
                    onClick={onCancel}
                    className="text-red-600 hover:text-red-700 text-sm font-medium hover:underline focus:outline-none"
                >
                    Cancelar Operación
                </button>
            </div>
        )}

      </div>
      
      {/* CSS for custom shimmer animation if not in Tailwind config */}
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-150%); }
          100% { transform: translateX(250%); }
        }
      `}</style>
    </div>
  );
}