import React, { useState, useEffect } from 'react';
import { Shield, Plus, FileJson, FileText, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

interface Policy {
  policy_id: string;
  name: string;
  effect: string;
  priority: number;
  nl_description: string;
  structured_rule: Record<string, any>;
  version: number;
}

function App() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    effect: 'DENY',
    priority: 100,
    regulation: '',
    effective_until: '',
    nl_description: '',
    structured_rule: '{\n  "property": "value"\n}'
  });

  const fetchPolicies = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/policies');
      if (response.ok) {
        const data = await response.json();
        setPolicies(data);
      }
    } catch (error) {
      console.error("Failed to fetch policies", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      // Validate JSON
      const parsedRule = JSON.parse(formData.structured_rule);

      const payload = {
        name: formData.name,
        effect: formData.effect,
        priority: Number(formData.priority),
        regulation: formData.regulation || null,
        effective_until: formData.effective_until || null,
        nl_description: formData.nl_description,
        structured_rule: parsedRule
      };

      const res = await fetch('/api/v1/policies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        setSuccessMsg(`Policy successfully stored in Graph (Version ${data.version})`);
        setShowForm(false);
        setFormData({
          name: '', effect: 'DENY', priority: 100, regulation: '', effective_until: '',
          nl_description: '',
          structured_rule: '{\n  "property": "value"\n}'
        });
        fetchPolicies(); // refresh list
      } else {
        setErrorMsg(data.detail || 'Failed to save policy');
      }
    } catch (err: any) {
      setErrorMsg(`Invalid JSON for Structured Rule: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (policy: any) => {
    setFormData({
      name: policy.name,
      effect: policy.effect,
      priority: policy.priority,
      regulation: policy.regulation || '',
      effective_until: policy.effective_until || '',
      nl_description: policy.nl_description,
      structured_rule: JSON.stringify(policy.structured_rule, null, 2)
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 font-sans p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex items-center justify-between mb-8 pb-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-indigo-400" />
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Policy Administration Console</h1>
              <p className="text-slate-400 text-sm mt-1">Manage Apollo Graph Security Policies</p>
            </div>
          </div>
          <button
            onClick={() => { setShowForm(!showForm); setErrorMsg(''); setSuccessMsg(''); }}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg transition-colors font-medium shadow-lg shadow-indigo-600/20"
          >
            {showForm ? 'Cancel' : <><Plus className="w-4 h-4" /> New Policy</>}
          </button>
        </header>

        {successMsg && (
          <div className="mb-6 p-4 bg-emerald-900/40 border border-emerald-800 rounded-lg flex items-center gap-3 text-emerald-300">
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
            <p>{successMsg}</p>
          </div>
        )}

        {errorMsg && (
          <div className="mb-6 p-4 bg-red-900/40 border border-red-800 rounded-lg flex items-center gap-3 text-red-300">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p>{errorMsg}</p>
          </div>
        )}

        {showForm && (
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 mb-8 shadow-2xl">
            <h2 className="text-xl font-semibold text-white mb-6">Create or Update Policy</h2>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-slate-400 mb-1">Policy Name (ID)</label>
                  <input
                    type="text" required
                    value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. HIPAA_Mask_Clinical"
                    className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-slate-400 mb-1">Effect</label>
                  <select
                    value={formData.effect} onChange={e => setFormData({ ...formData, effect: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="ALLOW">ALLOW</option>
                    <option value="DENY">DENY</option>
                    <option value="MASK">MASK (Redact)</option>
                    <option value="FILTER">FILTER</option>
                  </select>
                </div>
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-slate-400 mb-1">Regulation</label>
                  <input
                    type="text"
                    value={formData.regulation} onChange={e => setFormData({ ...formData, regulation: e.target.value })}
                    placeholder="e.g. HIPAA, GDPR"
                    className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-slate-400 mb-1">Effective Until</label>
                  <input
                    type="date"
                    value={formData.effective_until} onChange={e => setFormData({ ...formData, effective_until: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-slate-400 mb-1">Priority (1-999)</label>
                  <input
                    type="number" required
                    value={formData.priority} onChange={e => setFormData({ ...formData, priority: Number(e.target.value) })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-400 mb-2">
                  <FileText className="w-4 h-4" /> Natural Language Description
                </label>
                <textarea
                  required rows={2}
                  value={formData.nl_description} onChange={e => setFormData({ ...formData, nl_description: e.target.value })}
                  placeholder="Describe the policy intent clearly for auditors..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-400 mb-2">
                  <FileJson className="w-4 h-4" /> Structured Rule (JSON)
                </label>
                <textarea
                  required rows={4}
                  value={formData.structured_rule} onChange={e => setFormData({ ...formData, structured_rule: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 font-mono text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit" disabled={submitting}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {submitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Save Version to Graph'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Policies List */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">Active Policies in Graph</h2>
            <button onClick={fetchPolicies} className="text-slate-400 hover:text-white p-2 transition-colors">
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {loading && policies.length === 0 ? (
            <div className="py-12 text-center text-slate-500">Loading graph policies...</div>
          ) : policies.length === 0 ? (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
              <Shield className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-slate-300">No active policies</h3>
              <p className="text-slate-500 mt-1">Create a policy above to insert it into the Knowledge Graph.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {policies.map((p: any) => (
                <div key={p.policy_id} className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-slate-600 transition-colors flex flex-col sm:flex-row gap-5 shadow-sm">

                  <div className="flex-grow">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-lg text-white">{p.name}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${p.effect === 'DENY' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                          p.effect === 'ALLOW' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                            'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}>
                          {p.effect}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-300 text-xs border border-slate-600">
                          v{p.version}
                        </span>
                        {p.regulation && (
                          <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-xs border border-indigo-500/30">
                            {p.regulation}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleEdit(p)}
                        className="text-sm text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        Edit Rule
                      </button>
                    </div>

                    <p className="text-slate-400 text-sm mb-4 leading-relaxed">{p.nl_description}</p>

                    <div className="bg-slate-900 rounded p-3 text-xs font-mono text-slate-300 overflow-x-auto border border-slate-700/50">
                      {JSON.stringify(p.structured_rule)}
                    </div>
                  </div>

                  <div className="sm:w-32 flex-shrink-0 flex flex-col justify-between border-t sm:border-t-0 sm:border-l border-slate-700 pt-4 sm:pt-0 sm:pl-5 text-sm">
                    <div>
                      <span className="block text-slate-500 text-xs mb-1 uppercase tracking-wider font-semibold">Priority</span>
                      <span className="font-mono text-white text-lg">{p.priority}</span>
                    </div>
                    {p.effective_until && (
                      <div className="mt-4">
                        <span className="block text-slate-500 text-xs mb-1 uppercase tracking-wider font-semibold">Expiry</span>
                        <span className="text-red-400 text-xs">{p.effective_until}</span>
                      </div>
                    )}
                    <div className="mt-auto pt-4">
                      <span className="block text-slate-500 text-xs mb-1">Graph ID</span>
                      <span className="font-mono text-slate-500 text-[10px] break-all">{p.policy_id.split('-')[0]}...</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export default App;
