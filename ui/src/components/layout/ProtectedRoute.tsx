import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, setUser } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await api.get(API_ENDPOINTS.ME);
        setUser(response.data);
      } catch (error) {
        setUser(null);
      }
    };

    if (isLoading) {
      checkAuth();
    }
  }, [isLoading, setUser]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/ui/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
