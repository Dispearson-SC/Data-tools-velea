import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  // Use '/api' relative path to leverage Nginx proxy in production
  // Fallback to localhost for local dev if not proxied
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token expired or invalid
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

export default api;
