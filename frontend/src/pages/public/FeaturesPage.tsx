import React from 'react';
import { Bot, PhoneCall, Database, ShieldCheck, Headphones, Zap, Radio, CheckCircle2 } from 'lucide-react';

export const FeaturesPage: React.FC = () => {
  return (
    <div className="py-16 max-w-7xl mx-auto px-6">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-navy-950 tracking-tight">
          Enterprise Features Built for Voice Reliability
        </h1>
        <p className="mt-4 text-slate-600 text-base">
          ServiceForce.ai combines carrier-grade telephony interfaces, low-latency streaming speech engines, and auditable tool execution.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <div className="h-10 w-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center mb-4">
            <Bot className="h-5 w-5" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Streaming Conversational Engine</h3>
          <p className="text-slate-600 text-sm leading-relaxed mb-4">
            Under-300ms time-to-first-token speech synthesis, natural human speech barge-in and interruption detection, background noise suppression, and prompt versioning.
          </p>
          <ul className="space-y-2 text-xs text-slate-600">
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-brand-500" />
              <span>Full duplex audio streaming over WebSocket & RTP</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-brand-500" />
              <span>Interruption detection with instant audio abort</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-brand-500" />
              <span>Configurable Gemini voice personalities (Puck, Charon, Aoede, Fenrir)</span>
            </li>
          </ul>
        </div>

        <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <div className="h-10 w-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center mb-4">
            <Database className="h-5 w-5" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">pgvector Document RAG</h3>
          <p className="text-slate-600 text-sm leading-relaxed mb-4">
            Upload company product catalogs, knowledge articles, FAQs, and policy documents (PDF, DOCX, TXT, Markdown). Automatic recursive chunking and semantic search.
          </p>
          <ul className="space-y-2 text-xs text-slate-600">
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-purple-500" />
              <span>Tenant-isolated vector indexing</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-purple-500" />
              <span>Document chunking with configurable overlap</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-purple-500" />
              <span>Citation audit trail in call transcript</span>
            </li>
          </ul>
        </div>

        <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <div className="h-10 w-10 rounded-xl bg-cyan-100 text-cyan-600 flex items-center justify-center mb-4">
            <Radio className="h-5 w-5" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">BYO Telephony & GSM Gateway</h3>
          <p className="text-slate-600 text-sm leading-relaxed mb-4">
            Bring your existing business phone number via Asterisk PBX, SIP trunking, or certified VoLTE hardware gateways.
          </p>
          <ul className="space-y-2 text-xs text-slate-600">
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-cyan-500" />
              <span>Server-side credential encryption</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-cyan-500" />
              <span>SIP registration health heartbeat monitoring</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-cyan-500" />
              <span>Built-in local mock telephony adapter for instant zero-hardware testing</span>
            </li>
          </ul>
        </div>

        <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <div className="h-10 w-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-4">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Safe Live Data Tool Router</h3>
          <p className="text-slate-600 text-sm leading-relaxed mb-4">
            Securely route tool invocations to real business databases and external REST APIs with strict parameter validation and SSRF defenses.
          </p>
          <ul className="space-y-2 text-xs text-slate-600">
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>SSRF IP blocklist (private RFC1918 & cloud metadata)</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Pre-built tools for order lookup, appointments, and inventory</span>
            </li>
            <li className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Audit logging on all database write actions</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
