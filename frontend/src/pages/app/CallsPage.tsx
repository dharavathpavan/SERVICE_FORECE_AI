import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { PhoneForwarded, PhoneCall, Filter, ArrowRight, Clock, ShieldCheck } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const CallsPage: React.FC = () => {
  const [calls, setCalls] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [directionFilter, setDirectionFilter] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState('');

  const fetchCalls = async () => {
    setIsLoading(true);
    try {
      let query = '/calls?limit=50';
      if (directionFilter) query += `&direction=${directionFilter}`;
      if (outcomeFilter) query += `&outcome=${outcomeFilter}`;

      const res = await apiRequest<{ total: number; items: any[] }>(query);
      setCalls(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCalls();
  }, [directionFilter, outcomeFilter]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Call Records & Transcripts</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit full-duplex conversational audio, event timelines, tool traces, and AI dispositions.
          </p>
        </div>

        {/* Filter Selectors */}
        <div className="flex items-center space-x-2 text-xs">
          <select
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All Directions</option>
            <option value="inbound">Inbound</option>
            <option value="outbound">Outbound</option>
          </select>

          <select
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All Outcomes</option>
            <option value="ai_resolved">AI Resolved</option>
            <option value="human_transferred">Human Transferred</option>
            <option value="customer_ended">Customer Ended</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-navy-950">Persisted Call Sessions ({total})</h3>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading call history...</div>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <PhoneCall className="h-8 w-8 mx-auto mb-2 text-slate-300" />
            <p className="font-semibold text-slate-700">No calls matching criteria</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 text-xs">
            {calls.map((call) => (
              <Link
                key={call.id}
                to={`/app/calls/${call.id}`}
                className="p-4 px-6 flex items-center justify-between hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center space-x-4 min-w-0">
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
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-900">{call.phone_number}</span>
                      <Badge variant="outline" className="text-[10px] uppercase">
                        {call.direction}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">
                      {call.summary || 'Call recorded'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-6 text-slate-500 shrink-0">
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

                  <div className="text-right">
                    <p className="font-mono text-slate-900 font-semibold">{call.duration_seconds}s</p>
                    <p className="text-[10px] text-slate-400">{new Date(call.created_at).toLocaleTimeString()}</p>
                  </div>

                  <ArrowRight className="h-4 w-4 text-slate-300" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
