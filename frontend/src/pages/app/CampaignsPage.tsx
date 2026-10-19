import React, { useState, useEffect } from 'react';
import { Megaphone, Plus, Play, Pause, AlertTriangle, CheckCircle2, Clock, ShieldCheck, Users } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export const CampaignsPage: React.FC = () => {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [dryRunModalOpen, setDryRunModalOpen] = useState(false);
  const [selectedCamp, setSelectedCamp] = useState<any | null>(null);
  const [dryRunData, setDryRunData] = useState<any | null>(null);

  // Create Form State
  const [name, setName] = useState('Patient Appointment Reminder Blast');
  const [agentId, setAgentId] = useState('');
  const [startHour, setStartHour] = useState('09:00');
  const [endHour, setEndHour] = useState('20:00');
  const [concurrency, setConcurrency] = useState(2);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchCampaigns = async () => {
    try {
      const [campRes, agentsRes, contactsRes] = await Promise.all([
        apiRequest<any[]>('/campaigns'),
        apiRequest<any[]>('/agents'),
        apiRequest<{ items: any[] }>('/contacts?limit=100'),
      ]);
      setCampaigns(campRes);
      setAgents(agentsRes);
      setContacts(contactsRes.items || []);
      if (agentsRes.length > 0 && !agentId) {
        setAgentId(agentsRes[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      // Pick first 5 contacts by default for the campaign audience
      const contactIds = contacts.slice(0, 5).map((c) => c.id);
      await apiRequest('/campaigns', {
        method: 'POST',
        body: JSON.stringify({
          name,
          agent_id: agentId,
          allowed_start_hour: startHour,
          allowed_end_hour: endHour,
          concurrency_limit: concurrency,
          max_attempts: maxAttempts,
          contact_ids: contactIds,
        }),
      });
      setCreateModalOpen(false);
      fetchCampaigns();
    } catch (err: any) {
      alert(err.message || 'Failed to create campaign');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenDryRun = async (camp: any) => {
    setSelectedCamp(camp);
    setDryRunModalOpen(true);
    try {
      const res = await apiRequest(`/campaigns/${camp.id}/dry-run`, { method: 'POST' });
      setDryRunData(res);
    } catch (err: any) {
      alert(err.message || 'Dry run failed');
    }
  };

  const handleStartCampaign = async (campId: string) => {
    try {
      await apiRequest(`/campaigns/${campId}/start`, { method: 'POST' });
      setDryRunModalOpen(false);
      fetchCampaigns();
    } catch (err: any) {
      alert(err.message || 'Activation failed');
    }
  };

  const handlePauseCampaign = async (campId: string) => {
    try {
      await apiRequest(`/campaigns/${campId}/pause`, { method: 'POST' });
      fetchCampaigns();
    } catch (err: any) {
      alert(err.message || 'Pause failed');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Outbound Calling Campaigns</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Safe, policy-constrained autonomous outbound calling with calling hours enforcement and concurrency caps.
          </p>
        </div>

        <Button size="sm" onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          <span>New Outbound Campaign</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading campaigns...</div>
      ) : campaigns.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs max-w-md mx-auto">
          <Megaphone className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No outbound campaigns created</h3>
          <p className="text-xs text-slate-500 mt-1 mb-5">
            Create an outbound campaign to automate appointment confirmations and customer follow-ups.
          </p>
          <Button size="sm" onClick={() => setCreateModalOpen(true)}>Create First Campaign</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {campaigns.map((camp) => (
            <div
              key={camp.id}
              className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">{camp.name}</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Calling Window: {camp.allowed_start_hour} - {camp.allowed_end_hour} ({camp.timezone})
                    </p>
                  </div>
                  <Badge
                    variant={
                      camp.status === 'running'
                        ? 'success'
                        : camp.status === 'paused'
                        ? 'warning'
                        : 'slate'
                    }
                  >
                    {camp.status}
                  </Badge>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs text-slate-600">
                  <div>
                    <span className="text-slate-400">Total Audience:</span>
                    <p className="font-bold text-slate-900">{camp.total_contacts} contacts</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Concurrency:</span>
                    <p className="font-bold text-slate-900">{camp.concurrency_limit} concurrent</p>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                {camp.status === 'running' ? (
                  <Button variant="outline" size="sm" onClick={() => handlePauseCampaign(camp.id)}>
                    <Pause className="h-3.5 w-3.5 text-amber-600" />
                    <span>Pause Dialing</span>
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => handleOpenDryRun(camp)}>
                    <Play className="h-3.5 w-3.5 text-brand-600" />
                    <span>Dry-Run Preview</span>
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal isOpen={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Create Outbound Campaign">
        <form onSubmit={handleCreateCampaign} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Campaign Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Assign Voice Agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.purpose})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Start Hour (Local)</label>
              <input
                type="text"
                value={startHour}
                onChange={(e) => setStartHour(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">End Hour (Local)</label>
              <input
                type="text"
                value={endHour}
                onChange={(e) => setEndHour(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Concurrency Cap</label>
              <input
                type="number"
                min={1}
                max={10}
                value={concurrency}
                onChange={(e) => setConcurrency(parseInt(e.target.value) || 2)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Max Attempts</label>
              <input
                type="number"
                min={1}
                max={5}
                value={maxAttempts}
                onChange={(e) => setMaxAttempts(parseInt(e.target.value) || 3)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create Draft Campaign
            </Button>
          </div>
        </form>
      </Modal>

      {/* Dry Run Preview Modal */}
      <Modal isOpen={dryRunModalOpen} onClose={() => setDryRunModalOpen(false)} title="Pre-Activation Safety Preview">
        <div className="space-y-4 text-xs">
          <p className="text-slate-600">
            Federal and state telecom regulations require verifying calling window hours, suppression registries, and caller permissions prior to dialing.
          </p>

          {dryRunData && (
            <div className="space-y-3">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-500">Audience:</span>
                  <span className="font-bold text-slate-800">{dryRunData.total_contacts} verified contacts</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Allowed Calling Window:</span>
                  <span className="font-mono text-slate-800">{dryRunData.calling_window}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Calling Window Status:</span>
                  <span className={dryRunData.is_within_calling_window ? 'text-emerald-600 font-bold' : 'text-amber-600 font-bold'}>
                    {dryRunData.is_within_calling_window ? 'Compliant & Open' : 'Outside Window (Held)'}
                  </span>
                </div>
              </div>

              {dryRunData.validation_warnings && dryRunData.validation_warnings.length > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 space-y-1">
                  {dryRunData.validation_warnings.map((w: string, i: number) => (
                    <p key={i} className="flex items-center space-x-1.5">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                      <span>{w}</span>
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" onClick={() => setDryRunModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => handleStartCampaign(selectedCamp?.id)}
            >
              <span>Confirm & Start Dialing</span>
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
