import React, { useState, useEffect } from 'react';
import { UserCheck, Plus, Mail, Shield, Trash2 } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { useAuth } from '@/context/AuthContext';

export const TeamPage: React.FC = () => {
  const { role: myRole } = useAuth();
  const [members, setMembers] = useState<any[]>([]);
  const [invitations, setInvitations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Invite Modal
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('operator');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchTeam = async () => {
    try {
      const [membersRes, invRes] = await Promise.all([
        apiRequest<any[]>('/organizations/members'),
        apiRequest<any[]>('/organizations/invitations').catch(() => []),
      ]);
      setMembers(membersRes);
      setInvitations(invRes);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTeam();
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiRequest('/organizations/invite', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      setInviteEmail('');
      setInviteModalOpen(false);
      fetchTeam();
    } catch (err: any) {
      alert(err.message || 'Invitation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Team & Role-Based Access Control (RBAC)</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage organization team members and enforce roles: Owner, Admin, Manager, and Operator.
          </p>
        </div>

        {(myRole === 'owner' || myRole === 'admin') && (
          <Button size="sm" onClick={() => setInviteModalOpen(true)}>
            <Plus className="h-4 w-4" />
            <span>Invite Team Member</span>
          </Button>
        )}
      </div>

      {/* Role Definitions Guide */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 bg-white border border-slate-200 rounded-xl">
          <Badge variant="brand" className="uppercase font-bold">Owner</Badge>
          <p className="text-slate-600 mt-1.5 text-[11px]">Full organization, billing, and member role authority.</p>
        </div>
        <div className="p-3 bg-white border border-slate-200 rounded-xl">
          <Badge variant="slate" className="uppercase font-bold">Admin</Badge>
          <p className="text-slate-600 mt-1.5 text-[11px]">Manage agents, knowledge bases, gateways, and invites.</p>
        </div>
        <div className="p-3 bg-white border border-slate-200 rounded-xl">
          <Badge variant="outline" className="uppercase font-bold">Manager</Badge>
          <p className="text-slate-600 mt-1.5 text-[11px]">Monitor campaigns, call logs, and analytics.</p>
        </div>
        <div className="p-3 bg-white border border-slate-200 rounded-xl">
          <Badge variant="outline" className="uppercase font-bold">Operator</Badge>
          <p className="text-slate-600 mt-1.5 text-[11px]">View assigned calls and perform human-handoff tasks.</p>
        </div>
      </div>

      {/* Active Members Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-navy-950">Active Team Members ({members.length})</h3>
        </div>

        <div className="divide-y divide-slate-100 text-xs">
          {members.map((m) => (
            <div key={m.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-50">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-700">
                  {(m.user?.full_name?.[0] || 'U').toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-slate-900">{m.user?.full_name || 'Member'}</p>
                  <p className="text-[11px] text-slate-400">{m.user?.email}</p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <Badge variant={m.role === 'owner' ? 'brand' : 'slate'} className="uppercase">
                  {m.role}
                </Badge>
                <span className="text-[11px] text-slate-400 font-mono">
                  Joined {new Date(m.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pending Invitations Table */}
      {invitations.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-navy-950">Pending Invitations ({invitations.length})</h3>
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {invitations.map((inv) => (
              <div key={inv.id} className="p-4 px-6 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-900">{inv.email}</p>
                  <p className="text-[11px] text-slate-400">Invited as {inv.role}</p>
                </div>
                <Badge variant="warning">{inv.status}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invite Modal */}
      <Modal isOpen={inviteModalOpen} onClose={() => setInviteModalOpen(false)} title="Invite Team Member">
        <form onSubmit={handleInvite} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Email Address</label>
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="colleague@yourcompany.com"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Assigned Role</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            >
              <option value="operator">Operator (View assigned calls & handoffs)</option>
              <option value="manager">Manager (View analytics, campaigns, calls)</option>
              <option value="admin">Admin (Manage agents, knowledge, gateways)</option>
            </select>
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setInviteModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
