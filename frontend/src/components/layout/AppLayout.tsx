import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  BookOpen,
  PhoneCall,
  Server,
  PhoneForwarded,
  Users,
  Megaphone,
  Network,
  BarChart3,
  UserCheck,
  CreditCard,
  Settings,
  ShieldAlert,
  LogOut,
  Building2,
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export const AppLayout: React.FC = () => {
  const { user, organization, role, logout, isDemoMode, setDemoMode } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/app/dashboard', icon: LayoutDashboard },
    { name: 'AI Agents', path: '/app/agents', icon: Bot },
    { name: 'Knowledge Bases', path: '/app/knowledge', icon: BookOpen },
    { name: 'Phone Numbers', path: '/app/phone-numbers', icon: PhoneCall },
    { name: 'Gateways', path: '/app/gateways', icon: Server },
    { name: 'Call History', path: '/app/calls', icon: PhoneForwarded },
    { name: 'Contacts & Consent', path: '/app/contacts', icon: Users },
    { name: 'Campaigns', path: '/app/campaigns', icon: Megaphone },
    { name: 'Integrations & Tools', path: '/app/integrations', icon: Network },
    { name: 'Analytics', path: '/app/analytics', icon: BarChart3 },
    { name: 'Team & RBAC', path: '/app/team', icon: UserCheck },
    { name: 'Billing & Usage', path: '/app/billing', icon: CreditCard },
    { name: 'Audit Logs', path: '/app/audit-logs', icon: ShieldAlert },
    { name: 'Settings', path: '/app/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-navy-950 text-slate-300 flex flex-col border-r border-slate-800 shrink-0">
        {/* Brand */}
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 to-cyan-400 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-brand-500/20">
              S
            </div>
            <div>
              <span className="font-bold text-white text-base tracking-tight flex items-center gap-1.5">
                ServiceForce<span className="text-brand-400">.ai</span>
              </span>
              <p className="text-[10px] text-slate-400 font-medium leading-none mt-0.5">
                AI Service Workforce
              </p>
            </div>
          </div>
        </div>

        {/* Organization Info */}
        <div className="px-4 py-3 border-b border-slate-800/60 bg-slate-900/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 min-w-0">
              <Building2 className="h-4 w-4 text-brand-400 shrink-0" />
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate">
                  {organization?.name || 'Workspace'}
                </p>
                <p className="text-[10px] text-slate-400 truncate uppercase tracking-wider">
                  Plan: {organization?.billing_plan || 'Starter'}
                </p>
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded font-mono font-medium bg-brand-500/10 text-brand-300 border border-brand-500/20 uppercase">
              {role || 'admin'}
            </span>
          </div>
        </div>

        {/* Navigation links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto text-sm">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2 rounded-lg font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom User Area */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-900/30">
          <div className="flex items-center justify-between">
            <div className="truncate pr-2">
              <p className="text-xs font-medium text-white truncate">
                {user?.full_name || 'Operator'}
              </p>
              <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 shadow-xs">
          <div className="flex items-center space-x-4">
            <h1 className="text-sm font-semibold text-slate-700 tracking-tight">
              Enterprise Telephony & Autonomous Service Agents
            </h1>
          </div>

          <div className="flex items-center space-x-3">
            {/* Demo / Live Mode Indicator */}
            <div
              className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium border cursor-pointer select-none transition-all ${
                isDemoMode
                  ? 'bg-amber-50 text-amber-700 border-amber-300'
                  : 'bg-emerald-50 text-emerald-700 border-emerald-300'
              }`}
              onClick={() => setDemoMode(!isDemoMode)}
              title="Click to toggle Demo simulation / Live Provider mode"
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  isDemoMode ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'
                }`}
              />
              <span>{isDemoMode ? 'Demo Simulator Mode' : 'Live Production Telephony'}</span>
            </div>

            <div className="h-4 w-px bg-slate-200" />

            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <span className="font-medium text-slate-700">{user?.full_name}</span>
              <span className="text-slate-400">({role})</span>
            </div>
          </div>
        </header>

        {/* Scrollable Page Outlet */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-50/60">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
