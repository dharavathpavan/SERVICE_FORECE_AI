import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  PhoneCall,
  ArrowLeft,
  Clock,
  DollarSign,
  Bot,
  User,
  ShieldCheck,
  Zap,
  PhoneForwarded,
  Sparkles,
  Volume2
} from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const CallDetailPage: React.FC = () => {
  const { callId } = useParams<{ callId: string }>();
  const navigate = useNavigate();
  const [call, setCall] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadCall() {
      try {
        const data = await apiRequest<any>(`/calls/${callId}`);
        setCall(data);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    if (callId) loadCall();
  }, [callId]);

  if (isLoading) {
    return <div className="p-12 text-center text-xs text-slate-400">Loading call details...</div>;
  }

  if (!call) {
    return <div className="p-12 text-center text-xs text-red-500">Call record not found.</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/app/calls')}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-navy-950">{call.phone_number}</h1>
              <Badge variant={call.outcome === 'ai_resolved' ? 'success' : 'brand'}>
                {call.outcome?.replace('_', ' ')}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Call ID: <span className="font-mono">{call.id}</span> • {new Date(call.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <span className="text-slate-400 text-[10px] uppercase font-semibold">Duration</span>
          <p className="text-lg font-bold text-slate-900 mt-1">{call.duration_seconds} seconds</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <span className="text-slate-400 text-[10px] uppercase font-semibold">Direction</span>
          <p className="text-lg font-bold text-slate-900 mt-1 capitalize">{call.direction}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <span className="text-slate-400 text-[10px] uppercase font-semibold">Estimated Cost</span>
          <p className="text-lg font-bold text-slate-900 mt-1">${call.estimated_cost?.toFixed(4) || '0.0000'}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <span className="text-slate-400 text-[10px] uppercase font-semibold">Status</span>
          <p className="text-lg font-bold text-slate-900 mt-1 capitalize">{call.status}</p>
        </div>
      </div>

      {/* AI Summary Banner */}
      <div className="p-4 bg-brand-50/50 border border-brand-200 rounded-xl space-y-1">
        <div className="flex items-center space-x-1.5 text-brand-900 text-xs font-bold">
          <Sparkles className="h-4 w-4 text-brand-600" />
          <span>AI Generated Call Summary & Disposition</span>
        </div>
        <p className="text-xs text-slate-700 leading-relaxed">{call.summary || 'Summary generated upon completion.'}</p>
      </div>

      {/* Audio Recording Banner */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
            <Volume2 className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">Lawful Call Recording Reference</h4>
            <p className="text-[11px] text-slate-400">Encrypted dual-channel audio archive with caller notice acknowledgment</p>
          </div>
        </div>
        <Badge variant="outline">Recorded & Compliant</Badge>
      </div>

      {/* Transcripts & Events Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transcript Conversation */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4">
          <h3 className="text-sm font-bold text-navy-950">Spoken Multi-Turn Transcript</h3>
          <div className="space-y-4 pt-2">
            {call.transcripts && call.transcripts.length > 0 ? (
              call.transcripts.map((t: any) => {
                const isAgent = t.speaker === 'agent';
                const isSystem = t.speaker === 'system';
                return (
                  <div
                    key={t.id}
                    className={`flex items-start space-x-3 ${
                      isAgent ? 'pl-0 pr-8' : isSystem ? 'px-6 py-2 bg-slate-50 rounded-lg text-slate-500' : 'pl-8 pr-0 flex-row-reverse space-x-reverse'
                    }`}
                  >
                    {!isSystem && (
                      <div
                        className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-white text-xs ${
                          isAgent ? 'bg-brand-600' : 'bg-slate-700'
                        }`}
                      >
                        {isAgent ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
                      </div>
                    )}
                    <div
                      className={`p-3 rounded-2xl text-xs leading-relaxed ${
                        isAgent
                          ? 'bg-slate-100 text-slate-900 rounded-tl-xs'
                          : isSystem
                          ? 'text-center text-[11px] italic w-full'
                          : 'bg-brand-600 text-white rounded-tr-xs'
                      }`}
                    >
                      <p>{t.text}</p>
                      {!isSystem && (
                        <span
                          className={`text-[9px] block mt-1 font-mono ${
                            isAgent ? 'text-slate-400' : 'text-brand-200'
                          }`}
                        >
                          {(t.start_timestamp_ms / 1000).toFixed(1)}s - {(t.end_timestamp_ms / 1000).toFixed(1)}s
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400">No transcript entries recorded.</p>
            )}
          </div>
        </div>

        {/* Chronological Event Timeline */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4">
          <h3 className="text-sm font-bold text-navy-950">Telephony Event Timeline</h3>
          <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 text-xs">
            {call.events && call.events.length > 0 ? (
              call.events.map((e: any, i: number) => (
                <div key={e.id || i} className="relative">
                  <div className="absolute -left-6 top-1 h-2.5 w-2.5 rounded-full bg-brand-600 ring-4 ring-white" />
                  <p className="font-bold font-mono text-slate-800 uppercase text-[10px]">{e.event_type}</p>
                  {e.payload && Object.keys(e.payload).length > 0 && (
                    <div className="mt-1 p-2 rounded bg-slate-50 text-[10px] font-mono text-slate-600 overflow-x-auto">
                      {JSON.stringify(e.payload)}
                    </div>
                  )}
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {new Date(e.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400">No events captured.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
