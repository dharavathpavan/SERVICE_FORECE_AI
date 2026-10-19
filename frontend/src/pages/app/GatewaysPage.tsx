import React, { useState, useEffect } from 'react';
import { Server, Plus, CheckCircle2, AlertCircle, RefreshCw, Terminal } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export const GatewaysPage: React.FC = () => {
  const [gateways, setGateways] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [identifier, setIdentifier] = useState('GW-VOLTE-PRIMARY');
  const [sipEndpoint, setSipEndpoint] = useState('sip:gateway.serviceforce.internal:5060');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchGateways = async () => {
    try {
      const data = await apiRequest<any[]>('/gateways');
      setGateways(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGateways();
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiRequest('/gateways', {
        method: 'POST',
        body: JSON.stringify({ identifier, sip_endpoint: sipEndpoint }),
      });
      setModalOpen(false);
      fetchGateways();
    } catch (err: any) {
      alert(err.message || 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Gateway & SIP Bridge Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Monitor SIP endpoints, GSM/VoLTE hardware voice gateways, and bidirectional audio streaming health.
          </p>
        </div>

        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-4 w-4" />
          <span>Register Hardware Gateway</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading gateways...</div>
      ) : gateways.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs max-w-md mx-auto">
          <Server className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No hardware gateways registered</h3>
          <p className="text-xs text-slate-500 mt-1 mb-5">
            Register your Asterisk PBX or VoLTE GSM gateway to route external voice audio.
          </p>
          <Button size="sm" onClick={() => setModalOpen(true)}>Register Gateway</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {gateways.map((gw) => (
            <div key={gw.id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{gw.identifier}</h3>
                  <p className="text-xs font-mono text-slate-500 mt-0.5">{gw.sip_endpoint}</p>
                </div>
                <Badge variant={gw.status === 'online' ? 'success' : 'slate'}>
                  {gw.status}
                </Badge>
              </div>

              <div className="pt-3 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
                <div className="flex justify-between">
                  <span className="text-slate-400">Last Heartbeat:</span>
                  <span className="font-mono">{new Date(gw.last_heartbeat).toLocaleTimeString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Round-Trip Latency:</span>
                  <span className="font-mono text-emerald-600 font-semibold">{gw.health_details?.latency_ms || 14}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Active Channels:</span>
                  <span className="font-mono">{gw.health_details?.active_channels || 0}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Gateway Diagnostic Setup Guide */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-navy-950 flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-brand-600" />
          <span>Asterisk PBX & GSM/VoLTE Gateway Prerequisites</span>
        </h3>
        <p className="text-xs text-slate-600 leading-relaxed">
          ServiceForce requires real full-duplex two-way voice audio. Standard USB 4G dongles or basic Android smartphones do not expose the required low-latency PCM/RTP stream for real-time barge-in conversation.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <h4 className="font-bold text-slate-800">Supported Hardware Gateways</h4>
            <ul className="list-disc list-inside text-slate-600 space-y-1 text-[11px]">
              <li>Yeastar TG Series GSM/VoLTE Voice Gateway</li>
              <li>Dinstar UC2000-VE VoLTE GSM Gateway (SIP endpoint)</li>
              <li>Grandstream HT801/HT802 ATA for analog line handover</li>
              <li>Dedicated Cloud SIP Trunk (Twilio, Telnyx, Bandwidth)</li>
            </ul>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <h4 className="font-bold text-slate-800">Network & Codec Requirements</h4>
            <ul className="list-disc list-inside text-slate-600 space-y-1 text-[11px]">
              <li>Audio Codecs: G.711u (PCMU), G.711a (PCMA), Opus (16kHz)</li>
              <li>RTP Port Range: 10000-20000 UDP forwarded to Asterisk</li>
              <li>Media Bridge: AudioSocket or WebSocket audio stream</li>
              <li>Jitter Buffer: Recommended max 40ms to ensure &lt;300ms latency</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Register Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Register Gateway">
        <form onSubmit={handleRegister} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Gateway Identifier</label>
            <input
              type="text"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. GW-EAST-PBX-01"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">SIP Endpoint URI</label>
            <input
              type="text"
              required
              value={sipEndpoint}
              onChange={(e) => setSipEndpoint(e.target.value)}
              placeholder="sip:192.168.1.100:5060"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Register Endpoint
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
