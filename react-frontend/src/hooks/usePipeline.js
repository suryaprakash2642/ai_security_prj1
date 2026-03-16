/**
 * Custom hook encapsulating all pipeline orchestration logic.
 * Manages auth state, layer states, and the full L1→L8 pipeline execution.
 */
import { useState } from 'react'
import { API, TEST_USERS, apiFetch, uid } from '../config.js'
import { INITIAL_PIPELINE_STATE } from '../constants.js'
import { buildFilteredSchema } from '../utils/schemaBuilder.js'

export function usePipeline(toast) {
  const [auth, setAuth] = useState(null)
  const [jwtRef] = useState({ current: null })
  const [l3CtxRef] = useState({ current: null })
  const [svcTokenRef] = useState({ current: null })
  const [ctxTokenRef] = useState({ current: null })
  const [btgState, setBtgState] = useState(null) // { active, expiresAt, previousClearance, elevatedClearance }
  const [layerStates, setLayerStates] = useState({})
  const [pipelineState, setPipelineState] = useState(INITIAL_PIPELINE_STATE)

  // ── Layer state helpers ──────────────────────────────────
  function setLayer(id, st, ms) {
    setLayerStates(prev => ({
      ...prev, [id]: st,
      ...(ms != null ? { [id + '_ms']: ms } : {}),
    }))
  }
  function resetLayers() { setLayerStates({}) }

  function upPipe(id, status) {
    setPipelineState(p => ({ ...p, pipeSteps: { ...p.pipeSteps, [id]: status } }))
  }
  function upStatus(msg) {
    setPipelineState(p => ({ ...p, pipeStatus: msg }))
  }
  function addDetail(layerId, title, data, status = 'success') {
    setPipelineState(p => ({
      ...p, layerDetails: [...p.layerDetails, { layerId, title, data, status }],
    }))
  }

  // ── Login ────────────────────────────────────────────────
  async function handleLogin(userKey) {
    const user = TEST_USERS[userKey]
    setLayer('l1', 'active')
    console.log('[L1 Login] Starting authentication for', user.name)
    try {
      const qp = new URLSearchParams({
        oid: user.oid, name: user.name, email: user.email, include_mfa: user.include_mfa,
      })
      const tokenRes = await apiFetch(`${API.L1}/mock/token?${qp}`, {
        method: 'POST',
        body: JSON.stringify({ roles: user.roles, groups: user.groups }),
      })
      if (!tokenRes.ok) { setLayer('l1', 'error'); toast('L1 mock token failed — is L1 running?', 'error'); return }

      jwtRef.current = tokenRes.data.token

      const ctxRes = await apiFetch(`${API.L1}/identity/resolve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${jwtRef.current}` },
      })
      if (!ctxRes.ok) { setLayer('l1', 'error'); toast('L1 identity resolve failed', 'error'); return }

      const ctxId = ctxRes.data.context_token_id
      ctxTokenRef.current = ctxId
      const verifyRes = await apiFetch(`${API.L1}/identity/verify/${ctxId}`)
      const full = verifyRes.ok ? verifyRes.data : {}

      const sc = {
        user_id:         full.identity?.oid || ctxRes.data.user_id,
        effective_roles: full.authorization?.effective_roles || ctxRes.data.effective_roles || [],
        clearance_level: full.authorization?.clearance_level ?? ctxRes.data.max_clearance_level,
        department:      full.org_context?.department || 'General',
        session_id:      full.request_metadata?.session_id || '',
      }

      l3CtxRef.current = {
        user_id:           sc.user_id,
        effective_roles:   sc.effective_roles,
        department:        sc.department,
        clearance_level:   sc.clearance_level,
        session_id:        full.request_metadata?.session_id || ctxId,
        context_expiry:    full.expires_at || new Date(Date.now() + 900000).toISOString(),
        facility_id:       (full.org_context?.facility_ids || [])[0] || '',
        mfa_verified:      full.identity?.mfa_verified ?? true,
        context_signature: ctxRes.data.context_signature,
        // Clinical context for row-filter parameter injection ({{user.provider_id}})
        provider_id:       full.org_context?.employee_id || '',
        unit_id:           (full.org_context?.unit_ids || [])[0] || '',
      }

      if (!l3CtxRef.current.context_signature) {
        setLayer('l1', 'error')
        toast('L1 missing context_signature — restart L1 server', 'error')
        return
      }

      const stRes = await apiFetch(`${API.L3}/mock/service-token`)
      svcTokenRef.current = stRes.ok ? stRes.data.token : null

      setLayer('l1', 'success', Date.now())
      setAuth(sc)
      console.log('[L1 Login] Authenticated:', sc.user_id, 'roles:', sc.effective_roles)
      toast(`Authenticated as ${user.name}`, 'success')
    } catch (e) {
      setLayer('l1', 'error')
      toast('Login error: ' + e.message, 'error')
    }
  }

  function handleLogout() {
    setAuth(null)
    jwtRef.current = null
    l3CtxRef.current = null
    svcTokenRef.current = null
    ctxTokenRef.current = null
    setBtgState(null)
    resetLayers()
    setPipelineState(INITIAL_PIPELINE_STATE)
    toast('Logged out')
  }

  // ── Break-the-Glass ─────────────────────────────────────
  async function activateBTG(reason, patientId) {
    if (!auth || !ctxTokenRef.current || !jwtRef.current) {
      toast('Must be logged in to activate BTG', 'error')
      return false
    }
    const body = { ctx_token: ctxTokenRef.current, reason }
    if (patientId) body.patient_id = patientId

    const res = await apiFetch(`${API.L1}/identity/emergency`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${jwtRef.current}` },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      toast(`BTG failed: ${res.data?.detail || JSON.stringify(res.data)}`, 'error')
      return false
    }

    const d = res.data
    setBtgState({
      active: true,
      expiresAt: new Date(Date.now() + d.expires_in * 1000),
      previousClearance: d.previous_clearance,
      elevatedClearance: d.elevated_clearance,
    })
    setAuth(prev => ({ ...prev, clearance_level: d.elevated_clearance }))

    // Re-fetch the full context from L1 to get the exact expires_at that was signed.
    // L3 verifies HMAC over (user_id|roles|dept|session|expiry|clearance),
    // so we must use the exact timestamp L1 used, not a client-side approximation.
    const verifyRes = await apiFetch(`${API.L1}/identity/verify/${ctxTokenRef.current}`)
    if (verifyRes.ok && l3CtxRef.current) {
      const full = verifyRes.data
      l3CtxRef.current = {
        ...l3CtxRef.current,
        context_signature: d.context_signature,
        clearance_level: full.authorization?.clearance_level ?? d.elevated_clearance,
        context_expiry: full.expires_at || l3CtxRef.current.context_expiry,
        break_glass: true,
        btg_patient_id: full.emergency?.patient_id || patientId || '',
      }
    }

    toast(d.message || 'Break-the-Glass activated', 'success')
    console.log('[BTG] Activated:', d)
    return true
  }

  // ── Pipeline ─────────────────────────────────────────────
  async function runPipeline(question) {
    if (!question.trim()) { toast('Enter a question first', 'error'); return }
    if (!auth) { toast('Please login first', 'error'); return }

    const reqId = uid()
    console.log(`\n${'='.repeat(60)}\n[Pipeline] START request=${reqId}\n  question="${question}"\n${'='.repeat(60)}`)

    setPipelineState({
      ...INITIAL_PIPELINE_STATE, running: true, shown: true,
    })
    resetLayers()

    const finish = (ok, msg) => {
      setPipelineState(p => ({ ...p, running: false, pipeStatus: msg || '' }))
      if (!ok) toast(msg, 'error')
      console.log(`[Pipeline] ${ok ? 'SUCCESS' : 'FAILED'}: ${msg}`)
    }

    // L1 already done
    upPipe('l1', 'done')

    // ── L3: Retrieval + Policy ─────────────────────────────
    upPipe('l2', 'running'); upPipe('l3', 'running'); upPipe('l4', 'running')
    setLayer('l2', 'active'); setLayer('l3', 'active'); setLayer('l4', 'active')
    upStatus('L3: Retrieving schema and resolving policies...')
    const t3 = Date.now()

    const l3Res = await apiFetch(`${API.L3}/api/v1/retrieval/resolve`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${svcTokenRef.current}` },
      body: JSON.stringify({
        question, security_context: l3CtxRef.current,
        request_id: reqId, max_tables: 10, include_ddl: true,
      }),
    })
    const ms3 = Date.now() - t3

    if (!l3Res.ok) {
      upPipe('l3', 'error'); setLayer('l3', 'error')
      upPipe('l2', 'error'); setLayer('l2', 'error')
      upPipe('l4', 'error'); setLayer('l4', 'error')
      ;['l5', 'l6', 'l7', 'l8'].forEach(l => upPipe(l, 'pending'))
      addDetail('l3', 'Retrieval FAILED', l3Res.data, 'error')
      finish(false, 'L3 Retrieval failed: ' + (l3Res.data?.detail || JSON.stringify(l3Res.data)))
      return
    }

    const l3Result = l3Res.data?.data || l3Res.data || {}
    const allTables = l3Result.filtered_schema || []

    console.log(`[L3 Retrieval] ${allTables.length} tables returned (${ms3}ms):`,
      allTables.map(t => `${t.table_id} (score=${t.relevance_score})`))

    upPipe('l3', 'done'); upPipe('l2', 'done'); upPipe('l4', 'done')
    setLayer('l3', 'success', ms3); setLayer('l2', 'success'); setLayer('l4', 'success')
    addDetail('l3', `Retrieval OK — ${allTables.length} tables`, l3Result)

    // ── Database metadata from L3 (passed to L5 for LLM context) ────────
    // The LLM in L5 decides which database to target based on the tables
    // and their metadata — we do NOT pre-select a dialect here.
    const filteredTables = allTables
    const dbMetadata = l3Result.database_metadata || {}

    console.log('[Database Metadata] From L3:', dbMetadata)

    // ── L5: SQL Generation ──────────────────────────────────
    upPipe('l5', 'running'); setLayer('l5', 'active')
    upStatus('L5: Generating SQL with LLM...')
    const t5 = Date.now()

    const permEnv = l3Result.permission_envelope || l3Res.data?.permission_envelope
    if (!permEnv?.signature) {
      upPipe('l5', 'error'); setLayer('l5', 'error')
      addDetail('l5', 'Missing signed permission envelope', { l3_keys: Object.keys(l3Result) }, 'error')
      finish(false, 'SECURITY BLOCK: Missing signed envelope from L3/L4')
      return
    }
    if (!filteredTables.length) {
      upPipe('l5', 'error'); setLayer('l5', 'error')
      addDetail('l5', 'No tables available', {}, 'error')
      finish(false, 'No tables available for the question.')
      return
    }

    const filteredSchema = buildFilteredSchema(filteredTables, l3Result)

    // Pass database_metadata to L5 so the LLM knows each database's dialect.
    // Dialect is NOT pre-selected from L3 — the LLM already has per-table
    // dialect info in the DDL headers. L5 infers the target DB from the
    // tables the LLM actually references in the generated SQL.
    const l5Body = {
      user_question: question, filtered_schema: filteredSchema, security_context: l3CtxRef.current,
      permission_envelope: permEnv, request_id: reqId,
      database_metadata: dbMetadata,
    }

    console.log('[L5 Request] Sending to LLM:', {
      databaseMetadata: dbMetadata,
      tableCount: filteredSchema.tables.length,
      tables: filteredSchema.tables.map(t => `${t.table_id} (${t.columns.length} cols)`),
    })

    const l5Res = await apiFetch(`${API.L5}/api/v1/generate/sql`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${svcTokenRef.current}` },
      body: JSON.stringify(l5Body),
    })
    const ms5 = Date.now() - t5

    if (!l5Res.ok) {
      upPipe('l5', 'error'); setLayer('l5', 'error')
      ;['l6', 'l7', 'l8'].forEach(l => upPipe(l, 'pending'))
      addDetail('l5', 'SQL Generation FAILED', l5Res.data, 'error')
      finish(false, 'L5 Generation failed: ' + (l5Res.data?.detail || JSON.stringify(l5Res.data)))
      return
    }

    const l5Result = l5Res.data?.data || l5Res.data || {}
    const generatedSql = l5Result.sql || l5Result.generated_sql || ''
    const l5Status = l5Result.status || ''

    // L5 infers the target database and dialect from the tables the LLM used.
    const detectedDialect = l5Result.dialect || l3Result.detected_dialect || ''
    const detectedDb = l5Result.target_database || l3Result.target_database || ''
    if (!detectedDialect) {
      console.warn('[L5 Result] WARNING: No dialect detected from L5 or L3 — check database_metadata')
    }
    console.log(`[L5 Result] status=${l5Status}, SQL generated (${ms5}ms), dialect=${detectedDialect}, db=${detectedDb}:`, generatedSql)

    // Handle L5 non-success statuses (CANNOT_ANSWER, GENERATION_FAILED, etc.)
    if (!generatedSql) {
      const reason = l5Result.cannot_answer_reason || l5Status || 'No SQL generated'
      upPipe('l5', 'error'); setLayer('l5', 'error', ms5)
      ;['l6', 'l7', 'l8'].forEach(l => upPipe(l, 'skipped'))
      setPipelineState(p => ({ ...p, detectedDialect, detectedDb }))
      addDetail('l5', `L5: ${reason}`, l5Result, 'error')
      finish(false, `L5: ${reason}`)
      return
    }

    upPipe('l5', 'done'); setLayer('l5', 'success', ms5)
    setPipelineState(p => ({
      ...p, sql: generatedSql, sqlDialect: detectedDialect,
      detectedDialect, detectedDb,
    }))
    addDetail('l5', `SQL Generated (${ms5}ms)`, l5Result)

    // ── L6: Validation ──────────────────────────────────────
    upPipe('l6', 'running'); setLayer('l6', 'active')
    upStatus('L6: Validating SQL...')
    const t6 = Date.now()

    const l6Res = await apiFetch(`${API.L6}/api/v1/validate/sql`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${svcTokenRef.current}` },
      body: JSON.stringify({
        raw_sql: generatedSql, security_context: l3CtxRef.current,
        permission_envelope: permEnv, request_id: reqId, dialect: detectedDialect,
      }),
    })
    const ms6 = Date.now() - t6

    if (!l6Res.ok) {
      upPipe('l6', 'error'); setLayer('l6', 'error')
      ;['l7', 'l8'].forEach(l => upPipe(l, 'pending'))
      addDetail('l6', 'Validation FAILED', l6Res.data, 'error')
      finish(false, 'L6 Validation failed')
      return
    }
    const l6Result = l6Res.data?.data || l6Res.data || {}
    const decision = l6Result.decision || l6Result.validation_result
    console.log(`[L6 Validation] Decision: ${decision} (${ms6}ms)`)

    upPipe('l6', decision === 'BLOCKED' ? 'error' : 'done')
    setLayer('l6', decision === 'BLOCKED' ? 'error' : 'success', ms6)
    setPipelineState(p => ({ ...p, valDetail: l6Result, valDecision: decision }))
    addDetail('l6', `Validation: ${decision}`, l6Result, decision === 'BLOCKED' ? 'error' : 'success')

    if (decision === 'BLOCKED') {
      ;['l7', 'l8'].forEach(l => upPipe(l, 'skipped'))
      finish(false, `BLOCKED by L6: ${l6Result.reason || 'Policy violation'}`)
      return
    }

    // ── Resolve target_database from SQL table references ───
    // The LLM picks which table(s) to query. Match those table names
    // back to the filtered schema to find the correct database for L7.
    const resolvedDb = (() => {
      const sqlLower = generatedSql.toLowerCase()
      for (const t of filteredTables) {
        const shortName = (t.table_name || t.table_id.split('.').pop()).toLowerCase()
        if (sqlLower.includes(shortName)) {
          const db = t.table_id.split('.')[0].toLowerCase()
          if (db && db !== detectedDb) {
            console.log(`[Target DB] Corrected: ${detectedDb} → ${db} (SQL references ${shortName} from ${t.table_id})`)
          }
          return db || detectedDb
        }
      }
      return detectedDb
    })()

    // ── L7: Execution ───────────────────────────────────────
    upPipe('l7', 'running'); setLayer('l7', 'active')
    upStatus('L7: Executing SQL...')
    const t7 = Date.now()

    const l7Res = await apiFetch(`${API.L7}/api/v1/execute/sql`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${svcTokenRef.current}` },
      body: JSON.stringify({
        validated_sql: generatedSql, target_database: resolvedDb, dialect: detectedDialect,
        security_context: l3CtxRef.current, permission_envelope: permEnv,
        request_id: reqId, original_question: question,
      }),
    })
    const ms7 = Date.now() - t7

    if (!l7Res.ok) {
      upPipe('l7', 'error'); setLayer('l7', 'error')
      upPipe('l8', 'pending')
      addDetail('l7', 'Execution FAILED', l7Res.data, 'error')
      finish(false, 'L7 Execution failed: ' + (l7Res.data?.detail || JSON.stringify(l7Res.data)))
      return
    }

    const l7Result = l7Res.data?.data || l7Res.data || {}
    const rawRows = l7Result.rows || l7Result.results || []
    const rawCols = l7Result.columns || (rawRows.length > 0 ? Object.keys(rawRows[0]) : [])
    const cols = rawCols.map(c => typeof c === 'object' ? (c.name || c.column_name || JSON.stringify(c)) : c)

    // L7 returns rows as arrays — convert to objects keyed by column name
    const rows = rawRows.map(r =>
      Array.isArray(r) ? Object.fromEntries(cols.map((c, i) => [c, r[i]])) : r
    )
    console.log(`[L7 Execution] ${rows.length} rows, ${cols.length} columns (${ms7}ms)`, cols, rows[0])

    upPipe('l7', 'done'); setLayer('l7', 'success', ms7)
    setPipelineState(p => ({
      ...p, results: rows, resultCols: cols,
      execMetrics: {
        rows_returned: l7Result.rows_returned ?? rows.length,
        execution_time_ms: l7Result.execution_time_ms ?? ms7,
        columns_masked: l7Result.columns_masked,
        truncated: l7Result.truncated,
      },
    }))
    addDetail('l7', `Executed — ${rows.length} rows (${ms7}ms)`, { rows_returned: rows.length, ...l7Result })

    // ── L8: Audit ───────────────────────────────────────────
    upPipe('l8', 'running'); setLayer('l8', 'active')
    upStatus('L8: Sending to audit...')

    const l8Res = await apiFetch(`${API.L8}/api/v1/audit/ingest`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${svcTokenRef.current}` },
      body: JSON.stringify({
        event_id: `evt-${reqId}-${Date.now()}`,
        event_type: 'QUERY_EXECUTED',
        source_layer: 'L7',
        timestamp: new Date().toISOString(),
        request_id: reqId, user_id: auth.user_id,
        question, sql: generatedSql,
        target_db: detectedDb, rows_returned: rows.length,
        security_context: l3CtxRef.current,
      }),
    })
    upPipe('l8', l8Res.ok ? 'done' : 'error')
    setLayer('l8', l8Res.ok ? 'success' : 'error', Date.now())
    addDetail('l8', l8Res.ok ? 'Audit logged' : 'Audit failed', l8Res.data, l8Res.ok ? 'success' : 'error')

    finish(true, `Done — ${rows.length} rows returned`)
    toast(`Query complete — ${rows.length} rows`, 'success')
  }

  return { auth, layerStates, pipelineState, btgState, handleLogin, handleLogout, runPipeline, activateBTG }
}
