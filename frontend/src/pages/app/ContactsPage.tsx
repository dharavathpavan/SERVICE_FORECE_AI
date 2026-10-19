import React, { useState, useEffect } from 'react';
import { Users, Plus, Upload, ShieldAlert, CheckCircle2, Search, Trash2 } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export const ContactsPage: React.FC = () => {
  const [contacts, setContacts] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Modals
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);

  // Form State
  const [phone, setPhone] = useState('+1-555-0199');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [tags, setTags] = useState('VIP, Patients');
  const [consentSource, setConsentSource] = useState('web_patient_form');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Import State
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<any | null>(null);

  const fetchContacts = async () => {
    try {
      const q = search ? `?search=${encodeURIComponent(search)}` : '';
      const res = await apiRequest<{ total: number; items: any[] }>(`/contacts${q}`);
      setContacts(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchContacts();
  }, [search]);

  const handleCreateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiRequest('/contacts', {
        method: 'POST',
        body: JSON.stringify({
          phone_number: phone,
          first_name: firstName,
          last_name: lastName,
          email: email || undefined,
          tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
          consent_source: consentSource,
        }),
      });
      setAddModalOpen(false);
      fetchContacts();
    } catch (err: any) {
      alert(err.message || 'Failed to add contact');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSuppress = async (phoneNumber: string) => {
    if (!confirm(`Add ${phoneNumber} to Do-Not-Call (DNC) suppression registry? No outbound calls will ever reach this contact.`)) return;
    try {
      await apiRequest('/contacts/suppress', {
        method: 'POST',
        body: JSON.stringify({ phone_number: phoneNumber }),
      });
      fetchContacts();
    } catch (err: any) {
      alert(err.message || 'Suppression failed');
    }
  };

  const handleCsvImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('serviceforce_token');
      const orgId = localStorage.getItem('serviceforce_org_id');

      const response = await fetch('/api/v1/contacts/import-csv', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          ...(orgId ? { 'X-Organization-Id': orgId } : {}),
        },
        body: formData,
      });

      const data = await response.json();
      setImportResult(data);
      fetchContacts();
    } catch (err: any) {
      alert(err.message || 'Import failed');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Contacts & Lawful Consent</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit caller consent records, import customer phone registries, and maintain Do-Not-Call suppression lists.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={() => setImportModalOpen(true)}>
            <Upload className="h-3.5 w-3.5" />
            <span>Import CSV</span>
          </Button>

          <Button size="sm" onClick={() => setAddModalOpen(true)}>
            <Plus className="h-4 w-4" />
            <span>Add Contact</span>
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center space-x-2">
        <Search className="h-4 w-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by phone, name, or email..."
          className="w-full text-xs outline-none bg-transparent"
        />
      </div>

      {/* Contacts Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-navy-950">Customer Contact Registry ({total})</h3>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading contacts...</div>
        ) : contacts.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Users className="h-8 w-8 mx-auto mb-2 text-slate-300" />
            <p className="font-semibold text-slate-700">No contacts found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 text-xs">
            {contacts.map((contact) => (
              <div key={contact.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center space-x-4 min-w-0">
                  <div className="h-9 w-9 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-700 text-xs">
                    {(contact.first_name?.[0] || 'C').toUpperCase()}
                  </div>
                  <div className="truncate">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-900">
                        {contact.first_name} {contact.last_name}
                      </span>
                      <span className="font-mono text-slate-500">{contact.phone_number}</span>
                      {contact.is_suppressed && (
                        <Badge variant="danger">Do Not Call (Suppressed)</Badge>
                      )}
                    </div>
                    <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-0.5">
                      <span>Consent: {contact.consent_source}</span>
                      <span>•</span>
                      <span>{new Date(contact.consent_timestamp).toLocaleDateString()}</span>
                      {contact.tags && contact.tags.length > 0 && (
                        <span>• Tags: {contact.tags.join(', ')}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {!contact.is_suppressed && (
                    <button
                      onClick={() => handleSuppress(contact.phone_number)}
                      title="Add to Do-Not-Call (DNC) Suppression"
                      className="px-2.5 py-1 text-[11px] rounded font-semibold text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
                    >
                      DNC Opt-Out
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Contact Modal */}
      <Modal isOpen={addModalOpen} onClose={() => setAddModalOpen(false)} title="Add Customer Contact">
        <form onSubmit={handleCreateContact} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Phone Number (E.164)</label>
            <input
              type="text"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1-555-0199"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Jane"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Cooper"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jane.cooper@example.com"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Lawful Consent Source</label>
            <input
              type="text"
              value={consentSource}
              onChange={(e) => setConsentSource(e.target.value)}
              placeholder="web_form, direct_inbound, opt_in_portal"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setAddModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Save Contact
            </Button>
          </div>
        </form>
      </Modal>

      {/* CSV Import Modal */}
      <Modal isOpen={importModalOpen} onClose={() => setImportModalOpen(false)} title="Bulk Import Contacts CSV">
        <div className="space-y-4 text-xs">
          <p className="text-slate-600">
            Upload a CSV containing customer contacts. Phone numbers are validated and cross-referenced with your Do-Not-Call suppression list automatically.
          </p>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl font-mono text-[11px] text-slate-600">
            Expected header row:<br />
            <code>phone,first_name,last_name,email,tags</code>
          </div>

          {importResult && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 space-y-1">
              <p className="font-bold flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Import Succeeded!</span>
              </p>
              <p>Created: {importResult.created_count} contacts</p>
              <p>Duplicates Skipped: {importResult.duplicate_count}</p>
            </div>
          )}

          <div className="pt-2">
            <input type="file" accept=".csv" onChange={handleCsvImport} disabled={isImporting} />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="ghost" onClick={() => setImportModalOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
