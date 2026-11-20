// frontend/src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('observault_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      const token = localStorage.getItem('observault_token');
      if (token) {
        try {
          const userData = await api.getCurrentUser();
          const userProfile = {
            id: userData.id || userData.email,
            email: userData.email,
            fullName: userData.full_name || userData.fullName,
            tenantId: userData.tenant_id || userData.tenantId,
            tenantName: userData.tenant_name || userData.tenantName,
            role: userData.role,
          };
          localStorage.setItem('observault_user', JSON.stringify(userProfile));
          setUser(userProfile);
        } catch (err) {
          console.warn('Session expired or invalid, logging out');
          logout();
        }
      }
      setLoading(false);
    }
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    localStorage.setItem('observault_token', data.access_token);
    const userProfile = {
      id: data.email,
      email: data.email,
      fullName: data.full_name,
      tenantId: data.tenant_id,
      tenantName: data.tenant_name,
      role: data.role,
    };
    localStorage.setItem('observault_user', JSON.stringify(userProfile));
    setUser(userProfile);
    return userProfile;
  };

  const logout = () => {
    localStorage.removeItem('observault_token');
    localStorage.removeItem('observault_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
