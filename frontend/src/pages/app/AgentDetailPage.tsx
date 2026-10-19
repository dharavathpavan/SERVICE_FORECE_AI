import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Bot,
  Save,
  Play,
  ArrowLeft,
  Sparkles,
  BookOpen,
  Wrench,
  Clock,
  History,
  PhoneForwarded,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const AgentDetailPage: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const isNew = !agentId || agentId === 'new';
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'config' | 'tools' | 'knowledge' | 'playground' | 'versions'>('config');

  // Form State
  const [name, setName] = useState('Apex Customer Care Specialist');
  const [description, setDescription] = useState('Autonomous customer care agent answering inbound queries, looking up order statuses, and scheduling appointments.');
  const [purpose, setPurpose] = useState('Customer Support');
  const [language, setLanguage] = useState('en-US');
  const [voice, setVoice] = useState('Puck');
  const [greeting, setGreeting] = useState('Thank you for calling Apex Healthcare! My name is Jordan. How may I assist you today?');
  const [systemPrompt, setSystemPrompt] = useState(`You are Jordan, a professional, empathetic customer care voice agent for Apex Healthcare.
Your goals:
1. Greet the customer warmly and ask how you can help.
2. If they ask about an order status, request their order ID and look it up using get_order_status.
3. If they want to schedule a consultation, check available slots with get_appointment_availability and book it with create_appointment.
4. Reference clinical policies accurately from attached knowledge bases.
5. If the caller requests a supervisor or is dissatisfied, immediately transfer them with request_human_transfer.
Always maintain a calm, concise, professional spoken cadence.`);
  const [fallbackBehavior, setFallbackBehavior] = useState('Apologize politely and transfer to human escalation line.');
  const [direction, setDirection] = useState('both');
  const [maxDuration, setMaxDuration] = useState(600);
  const [transferNumber, setTransferNumber] = useState('+1-800-555-0199');
  const [isActive, setIsActive] = useState(true);

  // Tools & Knowledge State
  const [availableTools, setAvailableTools] = useState<any[]>([]);
  const [enabledTools, setEnabledTools] = useState<string[]>([
    'lookup_customer',
    'get_order_status',
    'get_appointment_availability',
    'create_appointment',
    'request_human_transfer',
    'end_call'
  ]);
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);
  const [versions, setVersions] = useState<any[]>([]);
  const [versionNumber, setVersionNumber] = useState(1);

  // Playground State
  const [testMessage, setTestMessage] = useState('Where is my recent order ORD-8921?');
  const [testResult, setTestResult] = useState<any | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    async function loadResources() {
      try {
        const [toolsRes, kbsRes] = await Promise.all([
          apiRequest<any[]>('/tools'),
          apiRequest<any[]>('/knowledge-bases'),
        ]);
        setAvailableTools(toolsRes);
        setKnowledgeBases(kbsRes);

        if (!isNew && agentId) {
          const agentRes = await apiRequest<any>(`/agents/${agentId}`);
          setName(agentRes.name);
          setDescription(agentRes.description || '');
          setPurpose(agentRes.purpose);
          setLanguage(agentRes.language);
          setVoice(agentRes.voice);
          setGreeting(agentRes.greeting);
          setSystemPrompt(agentRes.system_prompt);
          setFallbackBehavior(agentRes.fallback_behavior);
          setDirection(agentRes.direction);
          setMaxDuration(agentRes.max_duration_seconds);
          setTransferNumber(agentRes.human_transfer_number || '');
          setIsActive(agentRes.is_active);
          setVersionNumber(agentRes.active_version_number);
          setVersions(agentRes.versions || []);
          if (agentRes.enabled_tools) {
            setEnabledTools(agentRes.enabled_tools);
          }
        }
      } catch (err) {
        console.error('Failed to load agent info:', err);
      }
    }
    loadResources();
  }, [agentId, isNew]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = {
        name,
        description,
        purpose,
        language,
        voice,
        greeting,
        system_prompt: systemPrompt,
        fallback_behavior: fallbackBehavior,
        direction,
        max_duration_seconds: maxDuration,
        human_transfer_number: transferNumber,
        is_active: isActive,
      };

      if (isNew) {
        const res = await apiRequest<any>('/agents', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        navigate(`/app/agents/${res.id}`);
      } else {
        const res = await apiRequest<any>(`/agents/${agentId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        });
        setVersionNumber(res.active_version_number);
        alert('Agent saved successfully! Version bumped to v' + res.active_version_number);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to save agent');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunPlaygroundTest = async () => {
    if (isNew) {
      alert('Please save the agent before executing playground tests.');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await apiRequest(`/agents/${agentId}/test`, {
        method: 'POST',
        body: JSON.stringify({
          message: testMessage,
          knowledge_base_ids: selectedKbIds,
          enable_tools: true,
        }),
      });
      setTestResult(res);
    } catch (err: any) {
      alert(err.message || 'Test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const toggleTool = (toolName: string) => {
    if (enabledTools.includes(toolName)) {
      setEnabledTools(enabledTools.filter((t) => t !== toolName));
    } else {
      setEnabledTools([...enabledTools, toolName]);
    }
  };

  const toggleKb = (kbId: string) => {
    if (selectedKbIds.includes(kbId)) {
      setSelectedKbIds(selectedKbIds.filter((id) => id !== kbId));
    } else {
      setSelectedKbIds([...selectedKbIds, kbId]);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/app/agents')}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-navy-950">{name || 'New Voice Agent'}</h1>
              {!isNew && <Badge variant="brand">v{versionNumber}</Badge>}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {isNew ? 'Configure and publish a new autonomous AI agent' : 'Manage instructions, tools, and playground turns'}
            </p>
          </div>
        </div>

        <Button onClick={handleSave} isLoading={isSaving} size="sm">
          <Save className="h-4 w-4" />
          <span>{isNew ? 'Publish Agent' : 'Save Changes'}</span>
        </Button>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('config')}
          className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
            activeTab === 'config'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Bot className="h-4 w-4" />
          <span>Core Configuration</span>
        </button>

        <button
          onClick={() => setActiveTab('tools')}
          className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
            activeTab === 'tools'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Wrench className="h-4 w-4" />
          <span>Live Tools ({enabledTools.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('knowledge')}
          className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
            activeTab === 'knowledge'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <BookOpen className="h-4 w-4" />
          <span>Knowledge Bases ({selectedKbIds.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('playground')}
          className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
            activeTab === 'playground'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Play className="h-4 w-4" />
          <span>Interactive Playground</span>
        </button>

        {!isNew && (
          <button
            onClick={() => setActiveTab('versions')}
            className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'versions'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <History className="h-4 w-4" />
            <span>Version History ({versions.length})</span>
          </button>
        )}
      </div>

      {/* Tab: Core Config */}
      {activeTab === 'config' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Agent Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Business Purpose</label>
              <input
                type="text"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Gemini Speech Voice</label>
              <select
                value={voice}
                onChange={(e) => setVoice(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              >
                <option value="Puck">Puck (Natural, Upbeat & Clear)</option>
                <option value="Charon">Charon (Deep, Confident & Professional)</option>
                <option value="Aoede">Aoede (Warm, Friendly & Empathetic)</option>
                <option value="Fenrir">Fenrir (Authoritative & Concise)</option>
                <option value="Kore">Kore (Balanced & Soothing)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              >
                <option value="en-US">English (US)</option>
                <option value="en-GB">English (UK)</option>
                <option value="es-US">Spanish (US)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Telephony Direction</label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              >
                <option value="both">Both Inbound & Outbound</option>
                <option value="inbound">Inbound Calls Only</option>
                <option value="outbound">Outbound Campaigns Only</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Spoken Greeting Message</label>
            <input
              type="text"
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
            <p className="text-[11px] text-slate-400 mt-1">This sentence is synthesized immediately upon call connection.</p>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">System Instructions & Behavior Prompt</label>
            <textarea
              rows={6}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full px-3 py-2 font-mono text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Human Transfer Phone / Extension</label>
              <input
                type="text"
                value={transferNumber}
                onChange={(e) => setTransferNumber(e.target.value)}
                placeholder="+1-800-555-0199 or SIP/104"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Max Call Duration (seconds)</label>
              <input
                type="number"
                value={maxDuration}
                onChange={(e) => setMaxDuration(parseInt(e.target.value) || 600)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Tab: Tools */}
      {activeTab === 'tools' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4 text-xs">
          <div>
            <h3 className="text-sm font-bold text-navy-950">Approved Live Operation Tools</h3>
            <p className="text-slate-500 mt-0.5">
              Select which verified functions this AI agent is authorized to invoke during telephone calls.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {availableTools.map((tool) => {
              const isEnabled = enabledTools.includes(tool.name);
              return (
                <div
                  key={tool.name}
                  onClick={() => toggleTool(tool.name)}
                  className={`p-4 rounded-xl border cursor-pointer select-none transition-all flex items-start space-x-3 ${
                    isEnabled
                      ? 'border-brand-500 bg-brand-50/30'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isEnabled}
                    onChange={() => {}}
                    className="mt-0.5 rounded text-brand-600 focus:ring-brand-500"
                  />
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-900">{tool.name}</span>
                      <Badge variant={tool.category === 'write' ? 'warning' : 'slate'}>
                        {tool.category}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">{tool.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab: Knowledge */}
      {activeTab === 'knowledge' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4 text-xs">
          <div>
            <h3 className="text-sm font-bold text-navy-950">Attach pgvector Knowledge Bases</h3>
            <p className="text-slate-500 mt-0.5">
              The agent will query semantic vector embeddings across attached knowledge collections during phone conversations.
            </p>
          </div>

          {knowledgeBases.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <BookOpen className="h-8 w-8 mx-auto mb-2 text-slate-300" />
              <p>No knowledge bases created yet. Go to Knowledge Bases to upload company docs.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {knowledgeBases.map((kb) => {
                const isSelected = selectedKbIds.includes(kb.id);
                return (
                  <div
                    key={kb.id}
                    onClick={() => toggleKb(kb.id)}
                    className={`p-4 rounded-xl border cursor-pointer select-none transition-all flex items-start space-x-3 ${
                      isSelected
                        ? 'border-purple-500 bg-purple-50/30'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      className="mt-0.5 rounded text-purple-600 focus:ring-purple-500"
                    />
                    <div>
                      <h4 className="font-bold text-slate-900">{kb.name}</h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">{kb.description || 'Reference knowledge'}</p>
                      <span className="text-[10px] text-purple-700 font-medium mt-1 inline-block">
                        {kb.document_count || 0} indexed documents
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Interactive Playground */}
      {activeTab === 'playground' && (
        <div className="space-y-4">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4 text-xs">
            <div>
              <h3 className="text-sm font-bold text-navy-950">Test Agent Playground</h3>
              <p className="text-slate-500 mt-0.5">
                Simulate caller statements to test real-time tool resolution, RAG citations, and speech latency.
              </p>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="e.g. Can you check status of order ORD-8921?"
                className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-brand-500"
              />
              <Button onClick={handleRunPlaygroundTest} isLoading={isTesting}>
                <Play className="h-3.5 w-3.5" />
                <span>Simulate Turn</span>
              </Button>
            </div>

            {testResult && (
              <div className="mt-4 pt-4 border-t border-slate-100 space-y-4">
                <div className="p-4 bg-brand-50/50 border border-brand-200 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-brand-900 flex items-center space-x-1.5">
                      <Bot className="h-4 w-4 text-brand-600" />
                      <span>Agent Spoken Response</span>
                    </span>
                    <span className="font-mono text-[11px] text-brand-700 bg-white px-2 py-0.5 rounded border border-brand-200">
                      Latency: {testResult.latency_ms}ms
                    </span>
                  </div>
                  <p className="text-slate-800 text-sm leading-relaxed">{testResult.reply}</p>
                </div>

                {/* Tool calls trace */}
                {testResult.tool_calls && testResult.tool_calls.length > 0 && (
                  <div className="p-4 bg-slate-900 text-slate-200 rounded-xl font-mono text-[11px] space-y-2">
                    <span className="text-cyan-400 font-bold uppercase tracking-wider text-[10px]">
                      Tool Execution Trace:
                    </span>
                    <pre className="overflow-x-auto">{JSON.stringify(testResult.tool_calls, null, 2)}</pre>
                  </div>
                )}

                {/* RAG Sources */}
                {testResult.retrieved_sources && testResult.retrieved_sources.length > 0 && (
                  <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl space-y-2">
                    <span className="text-purple-900 font-bold uppercase tracking-wider text-[10px]">
                      Retrieved Knowledge Base Sources:
                    </span>
                    {testResult.retrieved_sources.map((src: any, i: number) => (
                      <div key={i} className="text-[11px] text-slate-700 border-t border-purple-100 pt-1">
                        <span className="font-semibold">{src.document_title}</span> (sim: {src.similarity}):{' '}
                        {src.content}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Versions */}
      {activeTab === 'versions' && !isNew && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4 text-xs">
          <h3 className="text-sm font-bold text-navy-950">Agent Version Snapshots</h3>
          <div className="divide-y divide-slate-100">
            {versions.map((ver) => (
              <div key={ver.id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900">Version {ver.version_number}</span>
                    {ver.version_number === versionNumber && <Badge variant="success">Active</Badge>}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">{ver.notes || 'Config snapshot'}</p>
                </div>
                <span className="text-[11px] text-slate-400">{new Date(ver.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
