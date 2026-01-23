import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import Cleaner from './pages/tools/Cleaner';
import Analysis from './pages/tools/Analysis';
import Breakdown from './pages/tools/Breakdown';
import WansoftDownloader from './pages/tools/WansoftDownloader';
import AdminUsers from './pages/settings/AdminUsers';
import { useAuthStore } from './store/authStore';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SessionTimeout } from './components/SessionTimeout';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <SessionTimeout />
        <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        <Route path="/" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          <Route index element={<Home />} />
          <Route path="tools/cleaner" element={<Cleaner toolType="sales" />} />
          <Route path="tools/analysis" element={<Cleaner toolType="analysis" />} />
          <Route path="tools/data-analysis" element={<Analysis />} />
          <Route path="tools/breakdown" element={<Breakdown />} />
          <Route path="tools/wansoft" element={<WansoftDownloader />} />
          <Route path="tools/production" element={<Cleaner toolType="production" />} />
          <Route path="settings/users" element={<AdminUsers />} />
        </Route>
      </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
