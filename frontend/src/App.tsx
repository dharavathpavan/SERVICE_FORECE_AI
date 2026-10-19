import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/context/AuthContext';
import { PublicLayout } from '@/components/layout/PublicLayout';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

// Public Pages
import { LandingPage } from '@/pages/public/LandingPage';
import { FeaturesPage } from '@/pages/public/FeaturesPage';
import { PricingPage } from '@/pages/public/PricingPage';
import { DocsPage } from '@/pages/public/DocsPage';
import { LoginPage } from '@/pages/public/LoginPage';
import { SignupPage } from '@/pages/public/SignupPage';

// Authenticated Pages
import { DashboardPage } from '@/pages/app/DashboardPage';
import { AgentsListPage } from '@/pages/app/AgentsListPage';
import { AgentDetailPage } from '@/pages/app/AgentDetailPage';
import { KnowledgeBasesPage } from '@/pages/app/KnowledgeBasesPage';
import { KnowledgeDetailPage } from '@/pages/app/KnowledgeDetailPage';
import { PhoneConnectionsPage } from '@/pages/app/PhoneConnectionsPage';
import { GatewaysPage } from '@/pages/app/GatewaysPage';
import { CallsPage } from '@/pages/app/CallsPage';
import { CallDetailPage } from '@/pages/app/CallDetailPage';
import { ContactsPage } from '@/pages/app/ContactsPage';
import { CampaignsPage } from '@/pages/app/CampaignsPage';
import { IntegrationsPage } from '@/pages/app/IntegrationsPage';
import { AnalyticsPage } from '@/pages/app/AnalyticsPage';
import { TeamPage } from '@/pages/app/TeamPage';
import { BillingPage } from '@/pages/app/BillingPage';
import { SettingsPage } from '@/pages/app/SettingsPage';
import { AuditLogsPage } from '@/pages/app/AuditLogsPage';

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route element={<PublicLayout />}>
              <Route path="/" element={<LandingPage />} />
              <Route path="/features" element={<FeaturesPage />} />
              <Route path="/use-cases" element={<FeaturesPage />} />
              <Route path="/pricing" element={<PricingPage />} />
              <Route path="/docs" element={<DocsPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route path="/privacy" element={<DocsPage />} />
              <Route path="/terms" element={<DocsPage />} />
            </Route>

            {/* Authenticated SaaS Routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/app" element={<AppLayout />}>
                <Route index element={<Navigate to="/app/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="agents" element={<AgentsListPage />} />
                <Route path="agents/new" element={<AgentDetailPage />} />
                <Route path="agents/:agentId" element={<AgentDetailPage />} />
                <Route path="knowledge" element={<KnowledgeBasesPage />} />
                <Route path="knowledge/:knowledgeBaseId" element={<KnowledgeDetailPage />} />
                <Route path="phone-numbers" element={<PhoneConnectionsPage />} />
                <Route path="gateways" element={<GatewaysPage />} />
                <Route path="calls" element={<CallsPage />} />
                <Route path="calls/:callId" element={<CallDetailPage />} />
                <Route path="contacts" element={<ContactsPage />} />
                <Route path="campaigns" element={<CampaignsPage />} />
                <Route path="integrations" element={<IntegrationsPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="team" element={<TeamPage />} />
                <Route path="billing" element={<BillingPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="audit-logs" element={<AuditLogsPage />} />
              </Route>
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
