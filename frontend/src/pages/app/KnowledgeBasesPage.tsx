import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Plus, FileText, Trash2, ArrowRight } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';

export const KnowledgeBasesPage: React.FC = () => {
  const [kbs, setKbs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchKbs = async () => {
    try {
      const data = await apiRequest<any[]>('/knowledge-bases');
      setKbs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKbs();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiRequest('/knowledge-bases', {
        method: 'POST',
        body: JSON.stringify({ name, description }),
      });
      setName('');
      setDescription('');
      setCreateModalOpen(false);
      fetchKbs();
    } catch (err: any) {
      alert(err.message || 'Creation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string, kbName: string) => {
    if (!confirm(`Delete knowledge base "${kbName}" and all indexed vector chunks?`)) return;
    try {
      await apiRequest(`/knowledge-bases/${id}`, { method: 'DELETE' });
      fetchKbs();
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-950">pgvector Knowledge Bases</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Reference documents, product manuals, FAQs, and policies for semantic vector RAG retrieval.
          </p>
        </div>

        <Button size="sm" onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          <span>New Knowledge Base</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading knowledge bases...</div>
      ) : kbs.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs max-w-md mx-auto">
          <BookOpen className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No knowledge bases yet</h3>
          <p className="text-xs text-slate-500 mt-1 mb-5">
            Create a knowledge base to upload PDF, DOCX, and text policy manuals for your voice agents.
          </p>
          <Button size="sm" onClick={() => setCreateModalOpen(true)}>Create Knowledge Base</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {kbs.map((kb) => (
            <div
              key={kb.id}
              className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2.5">
                    <div className="h-9 w-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
                      <BookOpen className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 leading-tight">{kb.name}</h3>
                      <p className="text-[11px] text-purple-700 font-semibold mt-0.5">
                        {kb.document_count || 0} documents indexed
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(kb.id, kb.name)}
                    className="p-1 text-slate-300 hover:text-red-500 rounded transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                <p className="text-xs text-slate-600 mt-3 line-clamp-2">
                  {kb.description || 'Collection of verified business documents for semantic RAG.'}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-mono">
                  {new Date(kb.created_at).toLocaleDateString()}
                </span>
                <Link to={`/app/knowledge/${kb.id}`}>
                  <Button variant="outline" size="sm">
                    <FileText className="h-3.5 w-3.5" />
                    <span>Manage Documents</span>
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Knowledge Base"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Knowledge Base Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Clinical Policies & FAQs"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Description</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Hospital protocols, equipment warranties, and returns documentation."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create Collection
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
