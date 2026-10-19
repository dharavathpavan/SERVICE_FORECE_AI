import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bot, Plus, Copy, Trash2, Play, CheckCircle2, Sliders, ArrowRight } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const AgentsListPage: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAgents = async () => {
    try {
      const data = await apiRequest<any[]>('/agents');
      setAgents(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleDuplicate = async (id: string) => {
    try {
      await apiRequest(`/agents/${id}/duplicate`, { method: 'POST' });
      fetchAgents();
    } catch (err: any) {
      alert(err.message || 'Duplication failed');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete agent "${name}"?`)) return;
    try {
      await apiRequest(`/agents/${id}`, { method: 'DELETE' });
      fetchAgents();
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">AI Voice Agents</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure conversational personalities, prompt instructions, knowledge bases, and approved live tools.
          </p>
        </div>

        <Link to="/app/agents/new">
          <Button size="sm">
            <Plus className="h-4 w-4" />
            <span>Create AI Agent</span>
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading agents...</div>
      ) : agents.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs max-w-md mx-auto">
          <Bot className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No AI agents configured</h3>
          <p className="text-xs text-slate-500 mt-1 mb-5">
            Create your first conversational agent with pre-built customer support templates.
          </p>
          <Link to="/app/agents/new">
            <Button size="sm">Create First Agent</Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2.5">
                    <div className="h-9 w-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center font-bold">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 leading-tight">{agent.name}</h3>
                      <p className="text-[11px] text-slate-500">{agent.purpose}</p>
                    </div>
                  </div>
                  <Badge variant={agent.is_active ? 'success' : 'slate'}>
                    {agent.is_active ? 'Active' : 'Draft'}
                  </Badge>
                </div>

                <p className="text-xs text-slate-600 mt-3 line-clamp-2">
                  {agent.description || agent.greeting}
                </p>

                <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px] text-slate-500">
                  <div>
                    <span className="font-semibold text-slate-700">Voice:</span> {agent.voice}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700">Version:</span> v{agent.active_version_number}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700">Direction:</span> {agent.direction}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700">Max Call:</span> {agent.max_duration_seconds}s
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleDuplicate(agent.id)}
                    title="Duplicate Agent"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(agent.id, agent.name)}
                    title="Delete Agent"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                <Link to={`/app/agents/${agent.id}`}>
                  <Button variant="outline" size="sm">
                    <Sliders className="h-3.5 w-3.5" />
                    <span>Studio & Test</span>
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
