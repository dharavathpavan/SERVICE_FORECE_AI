import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  PhoneCall,
  Bot,
  Users,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  PhoneForwarded,
  DollarSign,
  AlertCircle,
  Play,
  Activity,
  Layers,
  Server
} from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

interface AnalyticsData {
  calls_today: number;
  total_calls: number;
  answered_calls: number;
  failed_calls: number;
  ai_resolved_calls: number;
  human_transfers: number;
  total_minutes: number;
  avg_duration_seconds: number;
  estimated_usage_cost_usd: number;
  active_agents: number;
  running_campaigns: number;
  answer_rate_pct: number;
  ai_resolution_rate_pct: number;
  human_transfer_rate_pct: number;
}

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [recentCalls, setRecentCalls] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [simModalOpen, setSimModalOpen] = useState(false);
  const [simScenario, setSimScenario] = useState('order_tracking');
  const [isSimulating, setIsSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any | null>(null);

  const fetchDashboardData = async () => {
    try {
      const [analyticsRes, callsRes] = await Promise.all([
        apiRequest<AnalyticsData>('/analytics/summary'),
        apiRequest<{ items: any[] }>('/calls?limit=5'),
      ]);
      setData(analyticsRes);
      setRecentCalls(callsRes.items || []);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleSimulateCall = async () => {
    setIsSimulating(true);
    setSimResult(null);
    try {
      const res = await apiRequest('/calls/simulate', {
        method: 'POST',
        body: JSON.stringify({
          scenario: simScenario,
          caller_phone: '+1-555-0199',
          direction: 'inbound',
        }),
      });
      setSimResult(res);
      await fetchDashboardData();
    } catch (err: any) {
      alert(err.message || 'Simulation failed');
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Workforce Operations Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time telephony metrics, autonomous agent resolution rates, and system diagnostics.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSimModalOpen(true)}
            className="border-brand-300 text-brand-700 bg-brand-50/50 hover:bg-brand-100"
          >
            <Play className="h-3.5 w-3.5 fill-brand-600 text-brand-600" />
            <span>Simulate Voice Call</span>
          </Button>

          <Link to="/app/agents/new">
            <Button size="sm">
              <Bot className="h-3.5 w-3.5" />
              <span>Deploy New Agent</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Calls Today */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Calls Today</span>
            <div className="p-2 bg-brand-50 text-brand-600 rounded-lg">
              <PhoneCall className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-navy-950">{data?.calls_today ?? 0}</span>
            <span className="text-[11px] text-slate-500">{data?.total_calls ?? 0} total</span>
          </div>
        </div>

        {/* AI Resolution Rate */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Resolution Rate</span>
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-navy-950">{data?.ai_resolution_rate_pct ?? 0}%</span>
            <span className="text-[11px] text-emerald-600 font-medium">
              {data?.ai_resolved_calls ?? 0} calls resolved
            </span>
          </div>
        </div>

        {/* Human Transfers */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Human Escalations</span>
            <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
              <PhoneForwarded className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-navy-950">{data?.human_transfers ?? 0}</span>
            <span className="text-[11px] text-slate-500">{data?.human_transfer_rate_pct ?? 0}% transfer rate</span>
          </div>
        </div>

        {/* Total Minutes & Cost */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Voice Minutes Used</span>
            <div className="p-2 bg-cyan-50 text-cyan-600 rounded-lg">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-navy-950">{data?.total_minutes ?? 0}m</span>
            <span className="text-[11px] text-slate-500">Est. ${data?.estimated_usage_cost_usd?.toFixed(2) ?? '0.00'}</span>
          </div>
        </div>
      </div>

      {/* Onboarding Checklist (if low call count) */}
      {(data?.total_calls ?? 0) === 0 && (
        <div className="bg-gradient-to-r from-brand-900 to-navy-900 text-white p-6 rounded-2xl shadow-sm border border-slate-800">
          <div className="max-w-2xl">
            <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-brand-500/20 text-brand-300 text-xs font-semibold uppercase mb-3">
              <Sparkles className="h-3 w-3" />
              <span>Getting Started Checklist</span>
            </div>
            <h3 className="text-lg font-bold">Configure Your AI Workforce in 4 Easy Steps</h3>
            <p className="text-xs text-slate-300 mt-1 mb-5">
              Follow these recommended steps to attach your business telephony and begin taking calls autonomously.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Link
                to="/app/agents/new"
                className="flex items-center space-x-3 p-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 transition-colors"
              >
                <div className="h-7 w-7 rounded-lg bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-xs">
                  1
                </div>
                <div>
                  <h4 className="text-xs font-semibold">Create AI Voice Agent</h4>
                  <p className="text-[11px] text-slate-400">Configure prompt, voice & personality</p>
                </div>
              </Link>

              <Link
                to="/app/knowledge"
                className="flex items-center space-x-3 p-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 transition-colors"
              >
                <div className="h-7 w-7 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-xs">
                  2
                </div>
                <div>
                  <h4 className="text-xs font-semibold">Upload Knowledge Base</h4>
                  <p className="text-[11px] text-slate-400">Add PDF/DOCX policy manuals & FAQs</p>
                </div>
              </Link>

              <Link
                to="/app/phone-numbers"
                className="flex items-center space-x-3 p-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 transition-colors"
              >
                <div className="h-7 w-7 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs">
                  3
                </div>
                <div>
                  <h4 className="text-xs font-semibold">Connect Phone Number</h4>
                  <p className="text-[11px] text-slate-400">Attach SIP Trunk or GSM Gateway</p>
                </div>
              </Link>

              <button
                onClick={() => setSimModalOpen(true)}
                className="flex items-center space-x-3 p-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors"
              >
                <div className="h-7 w-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                  4
                </div>
                <div>
                  <h4 className="text-xs font-semibold">Run Test Call Simulation</h4>
                  <p className="text-[11px] text-slate-400">Verify end-to-end voice loop</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Recent Calls & System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Calls Table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-navy-950">Recent Voice Calls</h3>
            <Link to="/app/calls" className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center space-x-1">
              <span>View All</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-slate-100 text-xs">
            {recentCalls.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <PhoneCall className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                <p className="font-medium">No calls logged yet.</p>
                <p className="text-[11px] text-slate-400 mt-1">Simulate a call above to test live data resolution.</p>
              </div>
            ) : (
              recentCalls.map((call) => (
                <Link
                  key={call.id}
                  to={`/app/calls/${call.id}`}
                  className="px-6 py-3.5 flex items-center justify-between hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <div
                      className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                        call.outcome === 'ai_resolved'
                          ? 'bg-emerald-500'
                          : call.outcome === 'human_transferred'
                          ? 'bg-purple-500'
                          : 'bg-slate-400'
                      }`}
                    />
                    <div className="truncate">
                      <p className="font-semibold text-slate-900 truncate">{call.phone_number}</p>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5">{call.summary || 'Call logged'}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 shrink-0 text-slate-500">
                    <Badge
                      variant={
                        call.outcome === 'ai_resolved'
                          ? 'success'
                          : call.outcome === 'human_transferred'
                          ? 'brand'
                          : 'slate'
                      }
                    >
                      {call.outcome?.replace('_', ' ')}
                    </Badge>
                    <span className="font-mono text-[11px]">{call.duration_seconds}s</span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Telephony and Integration Diagnostics */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-navy-950">Integration Health</h3>
            <Badge variant="success">All Systems Healthy</Badge>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Server className="h-4 w-4 text-brand-600" />
                <div>
                  <p className="font-semibold text-slate-900">Database & pgvector</p>
                  <p className="text-[11px] text-slate-500">PostgreSQL Vector Indexing</p>
                </div>
              </div>
              <span className="text-emerald-600 font-semibold text-[11px]">Online</span>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <PhoneCall className="h-4 w-4 text-cyan-600" />
                <div>
                  <p className="font-semibold text-slate-900">Telephony Media Bridge</p>
                  <p className="text-[11px] text-slate-500">SIP / RTP WebSocket Streamer</p>
                </div>
              </div>
              <span className="text-emerald-600 font-semibold text-[11px]">Ready</span>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Bot className="h-4 w-4 text-purple-600" />
                <div>
                  <p className="font-semibold text-slate-900">AI Speech Engine</p>
                  <p className="text-[11px] text-slate-500">Gemini Conversational Provider</p>
                </div>
              </div>
              <span className="text-emerald-600 font-semibold text-[11px]">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Voice Call Simulation Modal */}
      <Modal
        isOpen={simModalOpen}
        onClose={() => setSimModalOpen(false)}
        title="Simulate Autonomous Voice Call"
      >
        <div className="space-y-4 text-xs">
          <p className="text-slate-600">
            Run an end-to-end simulated telephone call to test how your configured agent, tools, and RAG knowledge respond in real-time.
          </p>

          <div>
            <label className="block font-semibold text-slate-700 mb-1.5">Select Call Scenario</label>
            <select
              value={simScenario}
              onChange={(e) => setSimScenario(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-brand-500"
            >
              <option value="order_tracking">Live Order Tracking (Customer asks where package is)</option>
              <option value="appointment_booking">Live Appointment Booking (Customer schedules consultation)</option>
              <option value="human_escalation">Human Escalation & Warm Transfer (Caller requests supervisor)</option>
              <option value="faq_inquiry">RAG Knowledge Inquiry (Policy & warranty question)</option>
            </select>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <p className="font-semibold text-slate-700">Simulated Telephony Specs:</p>
            <ul className="list-disc list-inside text-slate-500 space-y-0.5 text-[11px]">
              <li>Caller: +1-555-0199 (Jane Cooper)</li>
              <li>Signaling: SIP INVITE / 200 OK / ACK</li>
              <li>Speech synthesis: Full-duplex audio stream with barge-in detection</li>
              <li>Outcome disposition: Automatic AI classification</li>
            </ul>
          </div>

          {simResult && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 space-y-1">
              <p className="font-bold flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Call Simulation Completed!</span>
              </p>
              <p className="text-[11px]">Disposition: {simResult.outcome} ({simResult.duration_seconds} seconds)</p>
              <p className="text-[11px] font-medium text-slate-700">{simResult.summary}</p>
              <Link
                to={`/app/calls/${simResult.call_id}`}
                className="inline-block text-xs font-semibold text-brand-600 hover:underline mt-1"
                onClick={() => setSimModalOpen(false)}
              >
                Inspect Detailed Call Transcript & Events →
              </Link>
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" onClick={() => setSimModalOpen(false)}>
              Close
            </Button>
            <Button onClick={handleSimulateCall} isLoading={isSimulating}>
              <Play className="h-3.5 w-3.5" />
              <span>Execute Call Scenario</span>
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
