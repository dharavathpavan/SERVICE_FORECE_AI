import React, { useState } from 'react';
import { Settings, Shield, Server, Bot, Key, CheckCircle2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const SettingsPage: React.FC = () => {
  const { organization, user, role, isDemoMode, setDemoMode } = useAuth();
  const [orgName, setOrgName] = useState(organization?.name || 'My Organization');
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto text-xs">
      <div>
        <h1 className="text-xl font-bold text-navy-950">Workspace Settings</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Organization identity, multi-tenant isolation parameters, and telephony connectivity.
        </p>
      </div>

      {isSaved && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-emerald-800">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>Settings saved successfully.</span>
        </div>
      )}

      {/* Tenant Identity */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-navy-950 flex items-center space-x-2">
          <Shield className="h-4 w-4 text-brand-600" />
          <span>Tenant Organization Profile</span>
        </h3>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Organization Name</label>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Tenant ID</span>
              <p className="font-mono text-slate-700 font-semibold mt-1">{organization?.id || 'N/A'}</p>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Organization Slug</span>
              <p className="font-mono text-slate-700 font-semibold mt-1">{organization?.slug || 'default'}</p>
            </div>
          </div>

          <div className="pt-2">
            <Button type="submit" size="sm">Save Profile</Button>
          </div>
        </form>
      </div>

      {/* Telephony Server Configuration */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-navy-950 flex items-center space-x-2">
          <Server className="h-4 w-4 text-cyan-600" />
          <span>Asterisk PBX & Media Bridge Host</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">SIP Signaling Host</label>
            <input
              type="text"
              readOnly
              value="localhost:5060 (UDP/TLS)"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 font-mono text-slate-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">AudioSocket Media Bridge</label>
            <input
              type="text"
              readOnly
              value="ws://localhost:9099/audio"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 font-mono text-slate-600"
            />
          </div>
        </div>
      </div>

      {/* Simulation / Live Mode Toggle */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <h3 className="text-sm font-bold text-navy-950">Operating Environment</h3>
        <p className="text-slate-500">
          Toggle between zero-hardware simulation mode and live carrier SIP dialing.
        </p>

        <div className="flex items-center space-x-3 pt-1">
          <Button
            variant={isDemoMode ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setDemoMode(true)}
          >
            Demo / Simulator Mode
          </Button>

          <Button
            variant={!isDemoMode ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setDemoMode(false)}
          >
            Live Production Telephony
          </Button>
        </div>
      </div>
    </div>
  );
};
