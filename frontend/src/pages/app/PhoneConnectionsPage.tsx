import React, { useState, useEffect } from 'react';
import { PhoneCall, Plus, CheckCircle2, AlertTriangle, Trash2, Radio } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export const PhoneConnectionsPage: React.FC = () => {
  const [connections, setConnections] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // Form State
  const [friendlyName, setFriendlyName] = useState('Main Inbound Support');
  const [phoneNumber, setPhoneNumber] = useState('+1-800-555-0199');
  const [connectionType, setConnectionType] = useState('mock');
  const [assignedAgentId, setAssignedAgentId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchConnections = async () => {
    try {
      const [connRes, agentsRes] = await Promise.all([
        apiRequest<any[]>('/phone-connections'),
        apiRequest<any[]>('/agents'),
      ]);
      setConnections(connRes);
      setAgents(agentsRes);
      if (agentsRes.length > 0 && !assignedAgentId) {
        setAssignedAgentId(agentsRes[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConnections();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiRequest('/phone-connections', {
        method: 'POST',
        body: JSON.stringify({
          friendly_name: friendlyName,
          phone_number: phoneNumber,
          connection_type: connectionType,
          assigned_agent_id: assignedAgentId || null,
          inbound_enabled: true,
          outbound_enabled: true,
        }),
      });
      setCreateModalOpen(false);
      fetchConnections();
    } catch (err: any) {
      alert(err.message || 'Creation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Remove phone connection "${name}"?`)) return;
    try {
      await apiRequest(`/phone-connections/${id}`, { method: 'DELETE' });
      fetchConnections();
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Phone Connections & Numbers</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage verified business telephone numbers, BYO SIM gateways, and SIP trunk lines.
          </p>
        </div>

        <Button size="sm" onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          <span>Connect Phone Number</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading phone connections...</div>
      ) : connections.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs max-w-md mx-auto">
          <PhoneCall className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No phone numbers attached</h3>
          <p className="text-xs text-slate-500 mt-1 mb-5">
            Attach your business number using our local simulation adapter or enterprise SIP gateway.
          </p>
          <Button size="sm" onClick={() => setCreateModalOpen(true)}>Connect First Number</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {connections.map((conn) => {
            const assignedAgent = agents.find((a) => a.id === conn.assigned_agent_id);
            return (
              <div
                key={conn.id}
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">{conn.friendly_name}</h3>
                      <p className="text-base font-mono font-bold text-brand-600 mt-0.5">
                        {conn.phone_number}
                      </p>
                    </div>
                    <Badge variant={conn.health_status === 'healthy' ? 'success' : 'warning'}>
                      {conn.health_status}
                    </Badge>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 space-y-2 text-xs">
                    <div className="flex justify-between text-slate-500">
                      <span>Provider Type:</span>
                      <span className="font-semibold text-slate-800 uppercase">{conn.connection_type}</span>
                    </div>

                    <div className="flex justify-between text-slate-500">
                      <span>Assigned Agent:</span>
                      <span className="font-semibold text-slate-800">
                        {assignedAgent?.name || 'Unassigned'}
                      </span>
                    </div>

                    <div className="flex justify-between text-slate-500">
                      <span>Verified Ownership:</span>
                      <span className="text-emerald-600 font-semibold flex items-center space-x-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Verified</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                    <span>Inbound: {conn.inbound_enabled ? 'ON' : 'OFF'}</span>
                    <span>•</span>
                    <span>Outbound: {conn.outbound_enabled ? 'ON' : 'OFF'}</span>
                  </div>

                  <button
                    onClick={() => handleDelete(conn.id, conn.friendly_name)}
                    className="p-1.5 text-slate-300 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Connect Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Connect Phone Number"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Friendly Label</label>
            <input
              type="text"
              required
              value={friendlyName}
              onChange={(e) => setFriendlyName(e.target.value)}
              placeholder="e.g. Inbound Patient Hotline"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Phone Number (E.164 format)</label>
            <input
              type="text"
              required
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+1-800-555-0199"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Connection Type</label>
            <select
              value={connectionType}
              onChange={(e) => setConnectionType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            >
              <option value="mock">Local Development Mock Adapter (Zero hardware required)</option>
              <option value="gsm_gateway">Certified GSM / VoLTE Gateway (BYO SIM)</option>
              <option value="sip_trunk">Direct SIP Trunk (Asterisk PBX / Cloud SIP)</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Assign Default AI Agent</label>
            <select
              value={assignedAgentId}
              onChange={(e) => setAssignedAgentId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.purpose})
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Connect Number
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
