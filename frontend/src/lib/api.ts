import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  // Priority: 1. Env Var, 2. Hardcoded Production Backend, 3. Localhost
  baseURL: import.meta.env.VITE_API_URL || 'https://api.farone.cloud',
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
