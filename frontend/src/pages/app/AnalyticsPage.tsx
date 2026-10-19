import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Calendar,
  Download,
  PhoneCall,
  CheckCircle2,
  Clock,
  Sparkles,
  PhoneForwarded,
  DollarSign
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid
} from 'recharts';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [days, setDays] = useState(30);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const res = await apiRequest(`/analytics/summary?days=${days}`);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const handleExportCsv = () => {
    if (!data?.daily_volume) return;
    const header = 'Date,Total Calls,AI Resolved,Human Transferred\n';
    const rows = data.daily_volume
      .map((d: any) => `${d.date},${d.total_calls},${d.ai_resolved},${d.transferred}`)
      .join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `serviceforce_analytics_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Analytics & Workforce Intelligence</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Measured telephony minutes, answer rates, resolution trends, and call disposition metrics.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value))}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
          >
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>

          <Button variant="outline" size="sm" onClick={handleExportCsv}>
            <Download className="h-3.5 w-3.5" />
            <span>Export CSV</span>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] text-slate-400 font-semibold uppercase">Total Volume</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{data?.total_calls ?? 0}</p>
          <p className="text-[11px] text-emerald-600 font-medium mt-0.5">{data?.answer_rate_pct ?? 0}% Answer Rate</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] text-slate-400 font-semibold uppercase">AI Resolution</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{data?.ai_resolution_rate_pct ?? 0}%</p>
          <p className="text-[11px] text-slate-500 mt-0.5">{data?.ai_resolved_calls ?? 0} resolved</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] text-slate-400 font-semibold uppercase">Human Escalation</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{data?.human_transfer_rate_pct ?? 0}%</p>
          <p className="text-[11px] text-slate-500 mt-0.5">{data?.human_transfers ?? 0} transferred</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] text-slate-400 font-semibold uppercase">Total Call Minutes</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{data?.total_minutes ?? 0}m</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Avg: {data?.avg_duration_seconds ?? 0}s/call</p>
        </div>
      </div>

      {/* Volume Chart */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div>
          <h3 className="text-sm font-bold text-navy-950">Daily Call Volume & AI Resolution Trends</h3>
          <p className="text-xs text-slate-500 mt-0.5">Comparing total received calls against AI resolved outcomes.</p>
        </div>

        <div className="h-72 w-full pt-4">
          {data?.daily_volume && data.daily_volume.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.daily_volume} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '11px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="total_calls" name="Total Calls" fill="#0272c5" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ai_resolved" name="AI Resolved" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="transferred" name="Human Escalated" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No historical data available.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
