// frontend/src/App.jsx
import React, { useState, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import AICopilotDrawer from './components/ai/AICopilotDrawer';

import LoginPage from './pages/LoginPage';
import OverviewPage from './pages/OverviewPage';
import InfrastructurePage from './pages/InfrastructurePage';
import ApplicationObservabilityPage from './pages/ApplicationObservabilityPage';
import MLInsightsPage from './pages/MLInsightsPage';
import NetworkPage from './pages/NetworkPage';
import SecurityPage from './pages/SecurityPage';
import AlertsIncidentsPage from './pages/AlertsIncidentsPage';
import RootCauseAnalysisPage from './pages/RootCauseAnalysisPage';
import PredictiveAnalyticsPage from './pages/PredictiveAnalyticsPage';
import IntegrationsPage from './pages/IntegrationsPage';
import CollectorManagementPage from './pages/CollectorManagementPage';
import PrivacyEgressPage from './pages/PrivacyEgressPage';
import RecommendationsPage from './pages/RecommendationsPage';
import SettingsPage from './pages/SettingsPage';

export const LayoutContext = createContext(null);

function ProtectedLayout() {
  const { isAuthenticated, loading } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState('Last 15m');

  if (loading) {
    return (
      <div className="min-h-screen app-mesh-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 dark:text-slate-400 font-mono tracking-wide">
            Authenticating ObserVault Session...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const triggerGlobalRefresh = () => {
    setRefreshKey((k) => k + 1);
  };

  return (
    <LayoutContext.Provider value={{
      mobileSidebarOpen,
      setMobileSidebarOpen,
      copilotOpen,
      setCopilotOpen,
      searchQuery,
      setSearchQuery,
      timeRange,
      setTimeRange
    }}>
      <div className="min-h-screen app-mesh-bg text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-cyan-500/20 selection:text-cyan-600 dark:selection:text-cyan-300">
        <Navbar 
          onRefresh={triggerGlobalRefresh} 
          onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)} 
        />
        <div className="flex-1 flex overflow-hidden relative">
          <Sidebar 
            mobileOpen={mobileSidebarOpen} 
            onCloseMobile={() => setMobileSidebarOpen(false)} 
          />
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full transition-all duration-200">
            <Outlet key={refreshKey} context={{ triggerGlobalRefresh, searchQuery, timeRange }} />
          </main>
        </div>
        <AICopilotDrawer 
          isOpen={copilotOpen} 
          onClose={() => setCopilotOpen(false)} 
        />
      </div>
    </LayoutContext.Provider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedLayout />}>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/infrastructure" element={<InfrastructurePage />} />
              <Route path="/applications" element={<ApplicationObservabilityPage />} />
              <Route path="/ml-insights" element={<MLInsightsPage />} />
              <Route path="/network" element={<NetworkPage />} />
              <Route path="/security" element={<SecurityPage />} />
              <Route path="/alerts" element={<AlertsIncidentsPage />} />
              <Route path="/rca" element={<RootCauseAnalysisPage />} />
              <Route path="/predictive" element={<PredictiveAnalyticsPage />} />
              <Route path="/integrations" element={<IntegrationsPage />} />
              <Route path="/collectors" element={<CollectorManagementPage />} />
              <Route path="/privacy-egress" element={<PrivacyEgressPage />} />
              <Route path="/recommendations" element={<RecommendationsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
