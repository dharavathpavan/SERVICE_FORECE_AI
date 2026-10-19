import React, { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, Filter, FileText } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDetails, setSelectedDetails] = useState<any | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const res = await apiRequest<{ total: number; items: any[] }>('/audit-logs');
      setLogs(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Security & Compliance Audit Trail</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable, tenant-scoped audit logging for privileged changes, tool execution writes, and team actions.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="p-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-navy-950">Audit Records ({total})</h3>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading audit trail...</div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-400">No audit events recorded yet.</div>
        ) : (
          <div className="divide-y divide-slate-100 text-xs">
            {logs.map((log) => (
              <div
                key={log.id}
                className="p-4 px-6 flex items-center justify-between hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => setSelectedDetails(log)}
              >
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-slate-900">{log.action}</span>
                    <Badge variant="slate">{log.entity_type}</Badge>
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Entity ID: {log.entity_id || 'N/A'}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[11px] text-slate-400 font-mono">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-brand-600 block mt-0.5">Click for JSON payload →</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Details Modal */}
      <Modal
        isOpen={!!selectedDetails}
        onClose={() => setSelectedDetails(null)}
        title={`Audit Event: ${selectedDetails?.action}`}
      >
        <div className="space-y-3 text-xs">
          <div className="p-3 bg-slate-900 text-slate-100 rounded-xl font-mono text-[11px] overflow-x-auto max-h-72">
            <pre>{JSON.stringify(selectedDetails?.details || {}, null, 2)}</pre>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            Recorded at {selectedDetails && new Date(selectedDetails.created_at).toISOString()}
          </p>
        </div>
      </Modal>
    </div>
  );
};
