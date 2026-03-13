// ── API base paths (proxied via Vite dev server → real ports) ─
export const API = {
  L1: '/api/l1',
  L3: '/api/l3',
  L5: '/api/l5',
  L6: '/api/l6',
  L7: '/api/l7',
  L8: '/api/l8',
};

export const TEST_USERS = {
  physician: {
    oid: 'oid-dr-patel-4521', name: 'Dr. Rajesh Patel',
    email: 'dr.patel@apollohospitals.com',
    roles: ['Attending_Physician'], groups: ['clinical-cardiology'],
    include_mfa: true, label: 'Dr. Rajesh Patel — Attending Physician',
    domain: 'Clinical', clearance: 4,
  },
  nurse: {
    oid: 'oid-nurse-kumar-2847', name: 'Anita Kumar',
    email: 'anita.kumar@apollohospitals.com',
    roles: ['Registered_Nurse'], groups: ['clinical-cardiology'],
    include_mfa: true, label: 'Anita Kumar — Registered Nurse',
    domain: 'Clinical', clearance: 2,
  },
  billing: {
    oid: 'oid-bill-maria-5521', name: 'Maria Fernandes',
    email: 'maria.fernandes@apollohospitals.com',
    roles: ['Billing_Clerk'], groups: ['billing-ops'],
    include_mfa: true, label: 'Maria Fernandes — Billing Clerk',
    domain: 'Business', clearance: 2,
  },
  admin: {
    oid: 'oid-it-admin-7801', name: 'Vikram Joshi',
    email: 'vikram.joshi@apollohospitals.com',
    roles: ['IT_Administrator'], groups: ['infrastructure'],
    include_mfa: true, label: 'Vikram Joshi — IT Administrator',
    domain: 'IT', clearance: 2,
  },
  hr: {
    oid: 'oid-hr-priya-7701', name: 'Priya Mehta',
    email: 'priya.mehta@apollohospitals.com',
    roles: ['HR_Manager'], groups: ['hr-department'],
    include_mfa: true, label: 'Priya Mehta — HR Manager',
    domain: 'HR', clearance: 3,
  },
  revenue: {
    oid: 'oid-rev-james-6601', name: 'James Thomas',
    email: 'james.thomas@apollohospitals.com',
    roles: ['Revenue_Cycle_Manager'], groups: ['billing-ops'],
    include_mfa: true, label: 'James Thomas — Revenue Cycle Manager',
    domain: 'Business', clearance: 2,
  },
  researcher: {
    oid: 'oid-researcher-das', name: 'Dr. Anirban Das',
    email: 'anirban.das@apollohospitals.com',
    roles: ['Clinical_Researcher'], groups: ['quality-assurance'],
    include_mfa: true, label: 'Dr. Anirban Das — Clinical Researcher',
    domain: 'Analytics', clearance: 2,
  },
};

export const LAYERS = [
  { id: 'l1', label: 'Identity & Context' },
  { id: 'l2', label: 'Knowledge Graph' },
  { id: 'l3', label: 'Retrieval' },
  { id: 'l4', label: 'Policy Resolution' },
  { id: 'l5', label: 'SQL Generation' },
  { id: 'l6', label: 'Validation' },
  { id: 'l7', label: 'Execution' },
  { id: 'l8', label: 'Audit' },
];

export const HEALTH_ENDPOINTS = [
  { name: 'L1 Identity',   url: `${API.L1}/health`,                       id: 'l1' },
  { name: 'L3 Retrieval',  url: `${API.L3}/api/v1/retrieval/health`,      id: 'l3' },
  { name: 'L5 Generation', url: `${API.L5}/health`,                       id: 'l5' },
  { name: 'L6 Validation', url: `${API.L6}/health`,                       id: 'l6' },
  { name: 'L7 Execution',  url: `${API.L7}/api/v1/execute/health`,        id: 'l7' },
  { name: 'L8 Audit',      url: `${API.L8}/health`,                       id: 'l8' },
];

export async function apiFetch(url, opts = {}) {
  try {
    const { headers: extraHeaders, ...rest } = opts;
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(extraHeaders || {}) },
      ...rest,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { error: e.message } };
  }
}

export function uid() { return 'req-' + Math.random().toString(36).slice(2, 10); }
