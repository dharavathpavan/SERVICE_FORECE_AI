import React from 'react';
import { Link } from 'react-router-dom';
import {
  PhoneCall,
  Bot,
  Database,
  ShieldCheck,
  Zap,
  ArrowRight,
  Headphones,
  CheckCircle2,
  Workflow,
  Sparkles,
  Layers,
  Radio,
  Clock,
  Lock
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-24 bg-gradient-to-b from-brand-50/50 via-white to-slate-50 border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center space-x-2 bg-brand-100 text-brand-800 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider mb-6">
              <Sparkles className="h-3.5 w-3.5 text-brand-600" />
              <span>Autonomous AI Telephony Workforce</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy-950 tracking-tight leading-tight">
              Your business number.{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-cyan-600">
                Your AI workforce.
              </span>
            </h1>

            <p className="mt-6 text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
              Connect autonomous AI voice agents directly to your authorized business telephony, real-time databases, and internal knowledge bases. Handle customer calls with sub-second latency and seamless human transfer.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/signup"
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold px-6 py-3.5 rounded-xl shadow-md hover:shadow-lg transition-all"
              >
                <span>Deploy Your First Agent</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/login"
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold px-6 py-3.5 rounded-xl border border-slate-300 shadow-xs transition-all"
              >
                <span>Live Interactive Demo</span>
              </Link>
            </div>

            {/* Trust points */}
            <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 font-medium">
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Multi-Tenant RBAC Security</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Zero Fake Calls - Real SIP/Gateway</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>pgvector RAG Document Search</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Safe SSRF-Guarded Live Tools</span>
              </div>
            </div>
          </div>

          {/* Architecture Visual Preview */}
          <div className="mt-14 max-w-4xl mx-auto bg-white rounded-2xl border border-slate-200/80 shadow-xl overflow-hidden">
            <div className="bg-navy-950 px-4 py-3 flex items-center justify-between border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-amber-500" />
                <div className="h-3 w-3 rounded-full bg-emerald-500" />
                <span className="text-xs font-mono text-slate-400 ml-2">ServiceForce.ai Architecture Pipeline</span>
              </div>
              <div className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                Latency: ~280ms
              </div>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-900/95 text-slate-200 text-xs">
              <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60">
                <div className="flex items-center space-x-2 text-cyan-400 mb-2 font-semibold">
                  <PhoneCall className="h-4 w-4" />
                  <span>Telephony Layer</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Asterisk PBX, SIP Trunk or VoLTE Gateway with bidirectional streaming media bridge.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60">
                <div className="flex items-center space-x-2 text-brand-400 mb-2 font-semibold">
                  <Bot className="h-4 w-4" />
                  <span>Gemini Voice Engine</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Streaming speech recognition, interruption handling & function calling loop.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60">
                <div className="flex items-center space-x-2 text-purple-400 mb-2 font-semibold">
                  <Database className="h-4 w-4" />
                  <span>pgvector RAG</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Company manuals, FAQs, policies indexed with vector similarity and citation audit.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60">
                <div className="flex items-center space-x-2 text-emerald-400 mb-2 font-semibold">
                  <Workflow className="h-4 w-4" />
                  <span>Live Tool Router</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Real-time CRM order lookup, appointment booking, and human escalation.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Enterprise Pillars */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold text-navy-950 tracking-tight">
              Enterprise Voice Infrastructure
            </h2>
            <p className="mt-3 text-slate-600 text-sm">
              Engineered for actual production calls, strict regulatory compliance, and multi-tenant security.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:shadow-md transition-shadow">
              <div className="h-10 w-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center mb-4">
                <Radio className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Bring Your Own Carrier / SIM</h3>
              <p className="text-slate-600 text-xs leading-relaxed">
                Connect your existing business numbers through SIP trunks or compatible GSM/VoLTE gateways. Complete server-side credential isolation.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:shadow-md transition-shadow">
              <div className="h-10 w-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center mb-4">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Accurate Live Data Retrieval</h3>
              <p className="text-slate-600 text-xs leading-relaxed">
                Clear separation between reference knowledge (RAG) and transactional business truth (orders, inventory, appointments). Zero fabricated information.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:shadow-md transition-shadow">
              <div className="h-10 w-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-4">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">SSRF & Security Isolation</h3>
              <p className="text-slate-600 text-xs leading-relaxed">
                CIDR blocklist protecting private RFC1918 and cloud metadata endpoints. Strict tenant-level isolation on every database query and tool call.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
