import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { Button } from './ui/Button';
import { Clock, AlertTriangle } from 'lucide-react';

// Configuration
// Warning appears after INACTIVITY_LIMIT_MS
// Token lasts 2 hours, let's warn after 1 hour 59 mins of inactivity? 
// Or just simple inactivity check (e.g., 15 mins).
// User asked for: "si no despues de un rato de inactividad"
// Let's set inactivity limit to 15 minutes for security/UX balance, even if token lasts longer.
const INACTIVITY_LIMIT_MS = 15 * 60 * 1000; // 15 minutes
const WARNING_DURATION_S = 60; // 60 seconds countdown

export const SessionTimeout = () => {
  const { token, logout } = useAuthStore();
  const [showWarning, setShowWarning] = useState(false);
  const [timeLeft, setTimeLeft] = useState(60);
  
  // Timers references
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const countdownTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleTimeout = useCallback(() => {
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    logout();
    window.location.href = '/login'; // Force redirect
  }, [logout]);

  const startCountdown = useCallback(() => {
    countdownTimerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          handleTimeout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [handleTimeout]);

  const resetTimers = useCallback(() => {
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    
    setShowWarning(false);
    setTimeLeft(WARNING_DURATION_S);
    
    if (token) {
        idleTimerRef.current = setTimeout(() => {
            setShowWarning(true);
            startCountdown();
        }, INACTIVITY_LIMIT_MS);
    }
  }, [token, startCountdown]);

  const handleContinue = () => {
    resetTimers();
    // Optional: Ping API to refresh token if we had sliding expiration
  };

  useEffect(() => {
    if (!token) return;

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    const handleActivity = () => {
        // Only reset if warning is NOT shown. 
        // If warning is shown, user MUST click "Continue" button explicitly.
        if (!showWarning) {
            resetTimers();
        }
    };

    // Initial start
    resetTimers();

    // Add listeners
    events.forEach(event => window.addEventListener(event, handleActivity));

    return () => {
      events.forEach(event => window.removeEventListener(event, handleActivity));
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    };
  }, [token, showWarning, resetTimers]);

  if (!showWarning) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 bg-opacity-75 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4 border-l-4 border-yellow-500">
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-8 w-8 text-yellow-500" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-medium text-gray-900">
              Inactividad Detectada
            </h3>
            <div className="mt-2">
              <p className="text-sm text-gray-500">
                Tu sesión ha estado inactiva por un tiempo. Por seguridad, se cerrará automáticamente en:
              </p>
              <div className="mt-4 flex items-center justify-center">
                 <div className="text-3xl font-bold text-gray-700 font-mono flex items-center">
                    <Clock className="w-6 h-6 mr-2 text-gray-400" />
                    {timeLeft}s
                 </div>
              </div>
            </div>
            <div className="mt-6 flex space-x-3">
              <Button 
                variant="primary" 
                onClick={handleContinue}
                className="w-full justify-center"
              >
                Continuar Sesión
              </Button>
              <Button 
                variant="outline" 
                onClick={handleTimeout}
                className="w-full justify-center"
              >
                Cerrar Sesión
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
