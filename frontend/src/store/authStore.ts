import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  user: string | null;
  setToken: (token: string, user: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      isAuthenticated: false,
      isAdmin: false,
      user: null,
      setToken: (token, user) => {
        // Simple heuristic: check if user is admin based on username (secure check is on backend)
        // Ideally we should decode JWT here or get role from login response
        const isAdmin = user === 'gerardoj.suastegui' || user === 'admin';
        set({ token, isAuthenticated: true, user, isAdmin });
      },
      logout: () => set({ token: null, isAuthenticated: false, user: null, isAdmin: false }),
    }),
    {
      name: 'auth-storage',
    }
  )
);
