import React from 'react';
import { Terminal, Shield, PhoneCall, Code2, Server } from 'lucide-react';

export const DocsPage: React.FC = () => {
  return (
    <div className="py-16 max-w-7xl mx-auto px-6">
      <div className="max-w-3xl mb-12">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-navy-950 tracking-tight">
          ServiceForce.ai Architecture & Integration Docs
        </h1>
        <p className="mt-4 text-slate-600 text-sm leading-relaxed">
          Comprehensive developer reference for connecting telephony gateways, authoring RAG knowledge bases, and executing typed API tools with SSRF protection.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-10">
          {/* Section: Telephony & SIP */}
          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center space-x-2.5 text-brand-600 mb-3 font-semibold text-base">
              <PhoneCall className="h-5 w-5" />
              <h2>Asterisk PBX & VoLTE Gateway Setup</h2>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              ServiceForce connects via an external media bridge over WebSocket / RTP. To route calls through Asterisk:
            </p>
            <div className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto">
              <pre>{`; /etc/asterisk/pjsip.conf
[serviceforce-trunk]
type=endpoint
context=from-serviceforce
disallow=all
allow=ulaw,alaw,opus
transport=transport-udp
aors=serviceforce-trunk

; /etc/asterisk/extensions.conf
[from-serviceforce]
exten => _+X.,1,NoOp(ServiceForce AI Agent Call)
same => n,Answer()
same => n,AudioSocket(serviceforce-media-bridge-uuid,localhost:9099)
same => n,Hangup()`}</pre>
            </div>
          </section>

          {/* Section: Live Data Tool Protocol */}
          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center space-x-2.5 text-purple-600 mb-3 font-semibold text-base">
              <Code2 className="h-5 w-5" />
              <h2>Live Tool Schema & SSRF Guard</h2>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Tools execute server-side with strict JSON schema validation. Outbound HTTP calls evaluate IP addresses to prevent Server-Side Request Forgery:
            </p>
            <div className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto">
              <pre>{`// Example: Order Lookup Tool Spec
{
  "name": "get_order_status",
  "description": "Look up recent order details by customer ID or order code.",
  "parameters": {
    "type": "object",
    "properties": {
      "order_id": { "type": "string" },
      "customer_phone": { "type": "string" }
    },
    "required": ["order_id"]
  }
}`}</pre>
            </div>
          </section>
        </div>

        {/* Sidebar Quick Links */}
        <div className="space-y-6">
          <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center space-x-2">
              <Server className="h-4 w-4 text-brand-600" />
              <span>API Endpoints</span>
            </h3>
            <ul className="space-y-2 text-xs font-mono text-slate-600">
              <li className="p-1.5 bg-white rounded border border-slate-200">POST /api/v1/auth/login</li>
              <li className="p-1.5 bg-white rounded border border-slate-200">GET /api/v1/agents</li>
              <li className="p-1.5 bg-white rounded border border-slate-200">POST /api/v1/knowledge-bases</li>
              <li className="p-1.5 bg-white rounded border border-slate-200">POST /api/v1/calls/simulate</li>
              <li className="p-1.5 bg-white rounded border border-slate-200">GET /api/v1/health/ready</li>
            </ul>
          </div>

          <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center space-x-2">
              <Shield className="h-4 w-4 text-emerald-600" />
              <span>Multi-Tenant Guarantee</span>
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every request executes within a verified TenantContext. Cross-organization access attempts return HTTP 403 Forbidden with audit logging.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
