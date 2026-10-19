import React, { useState, useEffect } from 'react';
import { Network, Plus, ShieldCheck, Play, Code2, Webhook, CheckCircle2, AlertCircle } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export const IntegrationsPage: React.FC = () => {
  const [tools, setTools] = useState<any[]>([]);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Webhook Modal
  const [webhookModalOpen, setWebhookModalOpen] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('https://webhook.site/test-endpoint');
  const [isCreatingHook, setIsCreatingHook] = useState(false);

  // SSRF REST Test State
  const [testUrl, setTestUrl] = useState('https://api.github.com/zen');
  const [testMethod, setTestMethod] = useState('GET');
  const [isTestingHttp, setIsTestingHttp] = useState(false);
  const [httpTestResult, setHttpTestResult] = useState<any | null>(null);

  const fetchResources = async () => {
    try {
      const [toolsRes, hooksRes] = await Promise.all([
        apiRequest<any[]>('/tools'),
        apiRequest<any[]>('/webhooks'),
      ]);
      setTools(toolsRes);
      setWebhooks(hooksRes);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResources();
  }, []);

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreatingHook(true);
    try {
      await apiRequest('/webhooks', {
        method: 'POST',
        body: JSON.stringify({ url: webhookUrl }),
      });
      setWebhookModalOpen(false);
      fetchResources();
    } catch (err: any) {
      alert(err.message || 'Failed to create webhook');
    } finally {
      setIsCreatingHook(false);
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      const res = await apiRequest(`/webhooks/${id}/test`, { method: 'POST' });
      alert(`Webhook test dispatched with signature: ${res.status}`);
    } catch (err: any) {
      alert(err.message || 'Test failed');
    }
  };

  const handleTestHttpTool = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTestingHttp(true);
    setHttpTestResult(null);
    try {
      const res = await apiRequest('/tools/custom-http-test', {
        method: 'POST',
        body: JSON.stringify({ url: testUrl, method: testMethod }),
      });
      setHttpTestResult({ success: true, data: res });
    } catch (err: any) {
      setHttpTestResult({ success: false, error: err.message });
    } finally {
      setIsTestingHttp(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Integrations, Tools & Webhooks</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Typed operation registry, SSRF-guarded REST endpoints, and signed HMAC event dispatchers.
          </p>
        </div>

        <Button size="sm" onClick={() => setWebhookModalOpen(true)}>
          <Plus className="h-4 w-4" />
          <span>Add Webhook Endpoint</span>
        </Button>
      </div>

      {/* Grid: Webhooks & SSRF REST Tester */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Webhooks Section */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-navy-950 flex items-center space-x-2">
                <Webhook className="h-4 w-4 text-purple-600" />
                <span>HMAC-Signed Webhooks</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Outbound call notifications signed with SHA-256 secret key.
              </p>
            </div>
          </div>

          <div className="space-y-3 pt-2 text-xs">
            {webhooks.length === 0 ? (
              <div className="p-6 text-center text-slate-400 bg-slate-50 rounded-xl">
                No webhook endpoints registered. Click above to add an endpoint.
              </div>
            ) : (
              webhooks.map((hook) => (
                <div key={hook.id} className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                  <div className="truncate pr-4">
                    <p className="font-mono font-semibold text-slate-900 truncate">{hook.url}</p>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                      Secret: {hook.secret.slice(0, 12)}••••••••
                    </p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => handleTestWebhook(hook.id)}>
                    <Play className="h-3 w-3" />
                    <span>Test Ping</span>
                  </Button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Custom REST Tool SSRF Guard Tester */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-navy-950 flex items-center space-x-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>SSRF-Protected REST API Tool Runner</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Outbound requests verify DNS and CIDR blocklists to prevent internal network scanning.
            </p>
          </div>

          <form onSubmit={handleTestHttpTool} className="space-y-3 text-xs">
            <div className="flex gap-2">
              <select
                value={testMethod}
                onChange={(e) => setTestMethod(e.target.value)}
                className="px-2 py-1.5 border border-slate-300 rounded-lg text-xs"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
              <input
                type="text"
                required
                value={testUrl}
                onChange={(e) => setTestUrl(e.target.value)}
                placeholder="https://api.yourcompany.com/crm/orders"
                className="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-mono"
              />
              <Button type="submit" size="sm" isLoading={isTestingHttp}>
                Test URL
              </Button>
            </div>
            <p className="text-[10px] text-slate-400">
              Try testing <code className="bg-slate-100 px-1 py-0.5 rounded text-red-600">http://169.254.169.254</code> or <code className="bg-slate-100 px-1 py-0.5 rounded text-red-600">http://127.0.0.1</code> to verify SSRF blocking!
            </p>

            {httpTestResult && (
              <div
                className={`p-3 rounded-xl border font-mono text-[11px] ${
                  httpTestResult.success
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-red-50 border-red-200 text-red-800'
                }`}
              >
                {httpTestResult.success ? (
                  <div>
                    <span className="font-bold flex items-center space-x-1 mb-1">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                      <span>Valid Public HTTP Response (Status {httpTestResult.data.status_code})</span>
                    </span>
                    <pre className="overflow-x-auto max-h-32">{JSON.stringify(httpTestResult.data.data, null, 2)}</pre>
                  </div>
                ) : (
                  <div className="flex items-start space-x-1.5">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-600" />
                    <span>{httpTestResult.error}</span>
                  </div>
                )}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Available Tools Registry Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-navy-950">Pre-Built Live Operation Tools ({tools.length})</h3>
        </div>

        <div className="divide-y divide-slate-100 text-xs">
          {tools.map((t) => (
            <div key={t.name} className="p-4 px-6 flex items-start justify-between hover:bg-slate-50">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-bold text-slate-900">{t.name}</span>
                  <Badge variant={t.category === 'write' ? 'warning' : 'slate'}>{t.category}</Badge>
                </div>
                <p className="text-slate-500 text-[11px]">{t.description}</p>
              </div>

              <div className="text-right font-mono text-[10px] text-slate-400">
                {Object.keys(t.parameters?.properties || {}).length} parameters
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Webhook Modal */}
      <Modal isOpen={webhookModalOpen} onClose={() => setWebhookModalOpen(false)} title="Register Webhook Endpoint">
        <form onSubmit={handleCreateWebhook} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Destination Webhook URL</label>
            <input
              type="url"
              required
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://api.yourcrm.com/webhooks/calls"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setWebhookModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isCreatingHook}>
              Save Webhook
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
