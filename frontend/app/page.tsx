'use client'
import { useEffect, useState, useRef } from 'react'
import {
  Activity, ShieldCheck, Radio, ClipboardList, Play,
  MapPin, CloudDownload, MessagesSquare, Download,
  CheckCircle2, XCircle, Bot, Send, Sparkles, Cpu, Globe
} from 'lucide-react'

const API = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')

type Point = {
  sector_id: string; district: string; pri: number; severity: string;
  source: string; evidence?: string; components: Record<string, number>
}
type Event = { id: number; agent: string; message: string; created_at: string }
type Order = {
  id: number; sector_id: string; title: string; priority: string;
  status: string; protocol_refs: string;
  decided_by?: string | null; decided_at?: string | null
}
type Summary = {
  locations?: number; critical?: number; high?: number; moderate?: number;
  low?: number; source_counts?: Record<string, number>;
  latest_observation?: string | null; data_mode?: string;
  synthetic_locations?: number; pending_approval?: number
}
type ChatMessage = { role: 'user' | 'ai'; text: string; model?: string }
type AIStatus = { gemini_api_key_configured: boolean; active_path: string; gemini_model: string }

const color = (n: number) => n >= 75 ? 'critical' : n >= 55 ? 'high' : n >= 30 ? 'moderate' : 'low'

const offlinePoints: Point[] = [
  { sector_id: 'MUC-NEU-05', district: 'Neuhausen-Nymphenburg', pri: 79.7, severity: 'critical', source: 'synthetic_scenario', evidence: 'Synthetic training scenario: recurring standing water, blocked gully, and waste accumulation near public access.', components: { temperature: 18.9, standing_water: 30, organic_waste: 13.8, sewer_level: 7, ph_deviation: 1.2, clog_probability: 8.8 } },
  { sector_id: 'MUC-SCH-02', district: 'Schwabing-Freimann', pri: 68.0, severity: 'high', source: 'synthetic_scenario', evidence: 'Synthetic training scenario: drain obstruction and prolonged pooled water near a pedestrian route.', components: { temperature: 18.5, standing_water: 24.2, organic_waste: 12.2, sewer_level: 4.7, ph_deviation: .5, clog_probability: 7.9 } },
  { sector_id: 'MUC-ALT-01', district: 'Altstadt-Lehel', pri: 36.7, severity: 'moderate', source: 'synthetic_scenario', evidence: 'Synthetic training scenario: pooled water beside a public waste point after rainfall.', components: { temperature: 16.8, standing_water: 7.5, organic_waste: 8.4, sewer_level: 0, ph_deviation: .2, clog_probability: 3.8 } },
  { sector_id: 'MUC-GIE-03', district: 'Obergiesing-Fasangarten', pri: 36.2, severity: 'moderate', source: 'synthetic_scenario', evidence: 'Synthetic training scenario: repeated organic-waste overflow around a collection point.', components: { temperature: 15.9, standing_water: 2.5, organic_waste: 15.2, sewer_level: 0, ph_deviation: 0, clog_probability: 2.2 } },
  { sector_id: 'MUC-BOG-04', district: 'Bogenhausen', pri: 14.5, severity: 'low', source: 'synthetic_scenario', evidence: 'Synthetic training scenario: routine water-edge observation with no elevated operational signal.', components: { temperature: 14.5, standing_water: 1.7, organic_waste: 2.8, sewer_level: 0, ph_deviation: .8, clog_probability: 1 } },
]

function offlineSummary(points: Point[]): Summary {
  const counts: Record<string, number> = {}
  points.forEach(p => { counts[p.source] = (counts[p.source] || 0) + 1 })
  return { locations: points.length, critical: points.filter(p => p.pri >= 75).length, high: points.filter(p => p.pri >= 55 && p.pri < 75).length, moderate: points.filter(p => p.pri >= 30 && p.pri < 55).length, low: points.filter(p => p.pri < 30).length, source_counts: counts, latest_observation: new Date().toISOString(), data_mode: 'synthetic_training_snapshot', synthetic_locations: points.length, pending_approval: 0 }
}

export default function Dashboard() {
  const [points, setPoints] = useState<Point[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [summary, setSummary] = useState<Summary>({})
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [offline, setOffline] = useState(false)
  const [notice, setNotice] = useState('Connecting to UrbanGuard API...')
  const [selected, setSelected] = useState<Point | null>(null)
  const [actor, setActor] = useState('')
  // ── Gemini AI Chat state ────────────────────────────────────────────────
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'ai', text: '👋 I\'m your **Gemini AI Advisor**. Ask me anything about the current risk snapshot — e.g. "Which district is most critical?" or "What should we prioritise today?"', model: 'intro' }
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatBusy, setChatBusy] = useState(false)
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null)
  // ── AI Narrative for selected location ──────────────────────────────────
  const [aiNarrative, setAiNarrative] = useState<{ text: string; model: string } | null>(null)
  const [narrativeBusy, setNarrativeBusy] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const request = async (path: string, options?: RequestInit) => {
    let lastError: unknown
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const response = await fetch(`${API}/api/v1/${path}`, options)
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
        return await response.json()
      } catch (error) { lastError = error; await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1))) }
    }
    throw lastError
  }

  const load = async () => {
    setLoading(true)
    try {
      const [p, e, o, s] = await Promise.all(['risks/heatmap', 'activity', 'work-orders', 'dashboard/summary'].map(x => request(x)))
      setPoints(p); setEvents(e); setOrders(o); setSummary(s)
      setOffline(false); setNotice('Connected to UrbanGuard API.')
      // fetch AI status in background
      request('ai/status').then(setAiStatus).catch(() => {})
    } catch {
      setPoints(current => current.length ? current : offlinePoints)
      setSummary(current => current.locations ? current : offlineSummary(offlinePoints))
      setOffline(true)
      setNotice('Backend unavailable after 3 retries. Showing synthetic offline demo data.')
    } finally { setLoading(false) }
  }

  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i) }, [])
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages])

  const run = async (path: string, label: string, options?: RequestInit) => {
    setBusy(true)
    try {
      if (offline) { setNotice(`Offline demo: ${label}. No live municipal action was sent.`); return }
      const d = await request(path, options)
      setNotice(d.limitation ? `${label}: ${d.limitation}` : `${label}.`)
    } catch {
      setOffline(true)
      setPoints(current => current.length ? current : offlinePoints)
      setNotice(`${label} could not reach the backend. Offline demo mode is active.`)
    } finally { await load(); setBusy(false) }
  }

  const simulate = () => run('simulation/tick', 'Clearly labelled demo telemetry ingested', { method: 'POST' })
  const refreshWeather = () => run('data/refresh-weather', 'Real public weather refreshed', { method: 'POST' })
  const refreshReports = () => run('data/refresh-munich-reports', 'Official city reports refreshed', { method: 'POST' })
  const loadScenario = () => run('data/load-realistic-scenario', 'Realistic training scenario loaded', { method: 'POST' })

  const dispatch = async (s: string) => {
    setBusy(true)
    try {
      if (offline) {
        const point = points.find(item => item.sector_id === s)
        if (point && point.pri >= 30) {
          setOrders(current => [{ id: Date.now(), sector_id: s, title: `Inspect and mitigate vector breeding risk - ${point.district}`, priority: point.pri >= 75 ? 'P1 - same day' : 'P2 - within 24 hours', status: 'pending_approval', protocol_refs: 'BAV-WS-01, BAV-OHS-02' }, ...current])
          setNotice(`Offline demo dispatch drafted for ${s}; human approval required.`)
        } else setNotice('Offline demo: risk remains below the dispatch threshold.')
        return
      }
      const d = await request('agents/trigger-dispatch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sector_id: s }) })
      setNotice(d.action === 'monitor' ? 'Risk is below the dispatch threshold.' : `Dispatch drafted for ${s}; waiting for human approval.`)
    } catch {
      setOffline(true)
      setNotice('Dispatch could not reach the backend. Offline demo mode is active.')
    } finally { await load(); setBusy(false) }
  }

  const decide = async (id: number, decision: 'approve' | 'reject') => {
    if (!actor.trim()) { setNotice('Enter the reviewing officer name/id before approving or rejecting.'); return }
    setBusy(true)
    const status = decision === 'approve' ? 'approved' : 'rejected'
    try {
      if (offline) {
        setOrders(current => current.map(o => o.id === id ? { ...o, status, decided_by: actor } : o))
        setNotice(`Offline demo: work order #${id} ${status}. No live action was sent.`)
        return
      }
      await request(`work-orders/${id}/decision`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, actor }) })
      setNotice(`Work order #${id} ${status} by ${actor}.`)
    } catch {
      setOffline(true)
      setNotice('Decision could not reach the backend. Offline demo mode is active.')
    } finally { await load(); setBusy(false) }
  }

  // ── Gemini AI Chat ───────────────────────────────────────────────────────
  const sendChat = async () => {
    const q = chatInput.trim()
    if (!q || chatBusy) return
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', text: q }])
    setChatBusy(true)
    try {
      if (offline) {
        setChatMessages(prev => [...prev, {
          role: 'ai',
          text: `⚠️ Backend offline. In live mode, Gemini 2.0 Flash would analyse: "${q}" across ${points.length} risk locations.`,
          model: 'offline'
        }])
        return
      }
      const res = await fetch(`${API}/api/v1/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      })
      if (!res.ok) throw new Error(res.statusText)
      const data = await res.json()
      setChatMessages(prev => [...prev, { role: 'ai', text: data.answer, model: data.powered_by }])
    } catch {
      setChatMessages(prev => [...prev, {
        role: 'ai',
        text: 'Gemini AI temporarily unavailable. Configure GEMINI_API_KEY in your .env to enable conversational analysis.',
        model: 'error'
      }])
    } finally { setChatBusy(false) }
  }

  // ── Gemini AI Narrative for a selected location ──────────────────────────
  const fetchAINarrative = async (sector_id: string) => {
    setAiNarrative(null)
    setNarrativeBusy(true)
    try {
      if (offline) {
        setAiNarrative({ text: 'Connect the backend and configure GEMINI_API_KEY to see an AI-generated risk narrative.', model: 'offline' })
        return
      }
      const res = await fetch(`${API}/api/v1/ai/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sector_id })
      })
      const data = await res.json()
      setAiNarrative({ text: data.narrative?.narrative || 'Analysis unavailable.', model: data.narrative?.powered_by || 'unknown' })
    } catch {
      setAiNarrative({ text: 'AI narrative unavailable — backend not reachable.', model: 'error' })
    } finally { setNarrativeBusy(false) }
  }

  const handleSelectPoint = (p: Point) => {
    setSelected(p)
    fetchAINarrative(p.sector_id)
  }

  const dataMode = (summary.data_mode || 'unknown').replaceAll('_', ' ')
  const sourceLabels = Object.entries(summary.source_counts || {}).map(([name, count]) => `${name.replaceAll('_', ' ')} (${count})`).join(' · ')

  return (
    <main>
      <nav>
        <div className="brand"><ShieldCheck /><span>URBANGUARD</span><small>AI / MUNICIPAL OPS</small></div>
        <div className="nav-center">
          {aiStatus && (
            <div className="ai-badge">
              <Sparkles size={12} />
              <span>{aiStatus.gemini_api_key_configured ? `Gemini ${aiStatus.gemini_model}` : 'Gemini (no key)'}</span>
              <span className={`ai-dot ${aiStatus.gemini_api_key_configured ? 'ai-dot-live' : 'ai-dot-off'}`} />
            </div>
          )}
        </div>
        <div className="sovereign"><span className="dot" /> EU SOVEREIGN · LOCAL-FIRST · GOOGLE AI</div>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">MUNICH / BAVARIA REFERENCE LOCATIONS</p>
          <h1>Sanitation intelligence<br /><em>at city scale.</em></h1>
          <p className="sub">Powered by <strong>Gemini 2.0 Flash</strong> · Vertex AI · Cloud Run · Gemma fallback. All dispatches require human approval.</p>
        </div>
        <div className="actions">
          <button onClick={refreshWeather} disabled={busy}><CloudDownload size={17} />{busy ? 'PROCESSING' : 'REFRESH REAL WEATHER'}</button>
          <button onClick={refreshReports} disabled={busy}><MessagesSquare size={17} />{busy ? 'PROCESSING' : 'REFRESH CITY REPORTS'}</button>
          <button onClick={loadScenario} disabled={busy}><MapPin size={17} />{busy ? 'PROCESSING' : 'LOAD REALISTIC SCENARIO'}</button>
          <button className="secondary" onClick={simulate} disabled={busy}><Play size={17} />RUN DEMO DATA</button>
        </div>
      </section>

      <p className="notice"><Radio size={15} />{loading ? 'CONNECTING... ' : ''}{notice}</p>
      {offline && <p className="notice offline-notice"><Radio size={15} />OFFLINE DEMO MODE · synthetic data only · reconnecting automatically</p>}

      <section className="metrics">
        <div className="metric"><strong>{summary.locations ?? points.length}</strong><span>reference locations</span></div>
        <div className="metric"><strong>{(summary.critical ?? 0) + (summary.high ?? 0)}</strong><span>priority inspections</span></div>
        <div className="metric"><strong>{summary.moderate ?? 0}</strong><span>watch list</span></div>
        <div className="metric"><strong>{summary.pending_approval ?? orders.filter(o => o.status === 'pending_approval').length}</strong><span>awaiting approval</span></div>
      </section>

      <p className="provenance">DATA LINEAGE · {dataMode} · {sourceLabels || 'no streams'} · synthetic locations: {summary.synthetic_locations ?? 0} · risk scores are triage signals, not diagnoses.</p>

      {/* ── Google AI Services Banner ─────────────────────────────────────── */}
      <div className="google-ai-banner">
        <div className="google-service"><Sparkles size={14} /><span>Gemini 2.0 Flash</span><small>Risk narratives · Advisories</small></div>
        <div className="google-service"><Cpu size={14} /><span>Vertex AI</span><small>Production endpoint</small></div>
        <div className="google-service"><Globe size={14} /><span>Cloud Run</span><small>Serverless deploy</small></div>
        <div className="google-service"><Bot size={14} /><span>Gemma Fallback</span><small>Offline templates</small></div>
        <div className="google-service"><Sparkles size={14} /><span>Cloud Logging</span><small>Audit trail</small></div>
        <div className="google-service"><Cpu size={14} /><span>Secret Manager</span><small>API key security</small></div>
      </div>

      <div className="grid">
        <section className="panel map">
          <header>
            <span><MapPin /> CITY RISK MAP</span>
            <b>{points.length} ACTIVE LOCATIONS</b>
          </header>
          <div className="mapspace">
            <div className="river" />
            {points.length
              ? points.map((p, i) => (
                <button key={p.sector_id}
                  title={`${p.district}: PRI ${p.pri}. ${p.evidence || ''}`}
                  onClick={() => handleSelectPoint(p)}
                  className={`pin ${color(p.pri)} ${selected?.sector_id === p.sector_id ? 'pin-active' : ''}`}
                  style={{ left: `${13 + i * 18}%`, top: `${36 + (i % 2) * 26}%` }}>
                  <strong>{p.pri}</strong>
                  <span>{p.district.split('-')[0]}</span>
                </button>
              ))
              : <div className="empty">Refresh real weather or run clearly labelled demo data.</div>
            }
          </div>

          {selected && (
            <div className="evidence">
              <strong>{selected.district} · PRI {selected.pri}/100</strong>
              <span>{selected.source} · transparent score contributors</span>
              <div>{Object.entries(selected.components).map(([name, value]) => <i key={name}>{name.replaceAll('_', ' ')} <b>{value}</b></i>)}</div>
              {selected.evidence && <small>{selected.evidence}</small>}

              {/* ── Gemini AI Narrative Block ───────────────────────────── */}
              <div className="ai-narrative-block">
                <div className="ai-narrative-header">
                  <Sparkles size={12} />
                  <span>GEMINI AI RISK ANALYSIS</span>
                  {aiNarrative && <small className="ai-model-tag">{aiNarrative.model}</small>}
                </div>
                {narrativeBusy
                  ? <div className="ai-narrative-loading"><span className="pulse-dot" /><span className="pulse-dot" /><span className="pulse-dot" /></div>
                  : aiNarrative
                    ? <p className="ai-narrative-text">{aiNarrative.text}</p>
                    : <p className="ai-narrative-text ai-narrative-dim">Gemini analysis will appear here when a location is selected.</p>
                }
              </div>

              <div className="evidence-actions">
                <button onClick={() => dispatch(selected.sector_id)} disabled={busy}>{busy ? 'PROCESSING' : 'DRAFT REVIEWED DISPATCH'}</button>
                <a href={`${API}/api/v1/risks/export.csv`} target="_blank" rel="noreferrer" className="ghost"><Download size={14} />EXPORT CSV</a>
              </div>
            </div>
          )}

          <footer>
            <i className="low" />LOW <i className="moderate" />MODERATE <i className="high" />HIGH <i className="critical" />CRITICAL · select a location to inspect, then draft a reviewed dispatch
          </footer>
        </section>

        <section className="panel activity">
          <header><span><Activity /> AGENT ACTIVITY FEED</span><b>LIVE AUDIT</b></header>
          <div className="feed">
            {events.length
              ? events.map(e => (
                <article key={e.id}>
                  <div className={`agent ${e.agent.toLowerCase().includes('gemini') ? 'agent-gemini' : ''}`}>
                    {e.agent.toLowerCase().includes('gemini') && <Sparkles size={9} />}{e.agent}
                  </div>
                  <p>{e.message}</p>
                  <time>{new Date(e.created_at).toLocaleTimeString()}</time>
                </article>
              ))
              : <div className="empty">No agent activity yet.</div>
            }
          </div>
        </section>
      </div>

      {/* ── Gemini AI Chat Panel ─────────────────────────────────────────── */}
      <section className="panel ai-chat-panel">
        <header>
          <span><Bot /> GEMINI AI ADVISOR</span>
          <b className="gemini-badge"><Sparkles size={10} /> POWERED BY GEMINI 2.0 FLASH + VERTEX AI</b>
        </header>
        <div className="chat-feed" id="chat-feed">
          {chatMessages.map((msg, i) => (
            <div key={i} className={`chat-msg ${msg.role}`}>
              {msg.role === 'ai' && <div className="chat-avatar"><Bot size={13} /></div>}
              <div className="chat-bubble">
                <p dangerouslySetInnerHTML={{ __html: msg.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                {msg.model && msg.model !== 'intro' && msg.model !== 'offline' && msg.model !== 'error' && (
                  <small className="chat-model">{msg.model}</small>
                )}
              </div>
            </div>
          ))}
          {chatBusy && (
            <div className="chat-msg ai">
              <div className="chat-avatar"><Bot size={13} /></div>
              <div className="chat-bubble">
                <div className="ai-narrative-loading"><span className="pulse-dot" /><span className="pulse-dot" /><span className="pulse-dot" /></div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <div className="chat-input-row">
          <input
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChat()}
            placeholder="Ask Gemini: which district is critical? what should we prioritise?"
            disabled={chatBusy}
            id="gemini-chat-input"
          />
          <button onClick={sendChat} disabled={chatBusy || !chatInput.trim()} className="chat-send" id="gemini-send-btn">
            <Send size={15} />
          </button>
        </div>
      </section>

      <section className="panel orders">
        <header><span><ClipboardList /> WORK ORDER & ALERT MANAGER</span><b>HUMAN APPROVAL REQUIRED</b></header>
        <div className="review-bar">
          <label>Reviewing officer</label>
          <input value={actor} onChange={e => setActor(e.target.value)} placeholder="name or staff id" disabled={busy} />
        </div>
        {orders.length
          ? <div className="orderlist">{orders.map(o => (
            <article key={o.id}>
              <div>
                <strong>{o.title}</strong>
                <p>{o.sector_id} · {o.priority}{o.decided_by ? ` · ${o.status} by ${o.decided_by}` : ''}</p>
              </div>
              <code>{o.protocol_refs}</code>
              <span className={`status ${o.status}`}>{o.status.replaceAll('_', ' ')}</span>
              {o.status === 'pending_approval'
                ? <div className="order-actions">
                  <button className="approve" onClick={() => decide(o.id, 'approve')} disabled={busy}><CheckCircle2 size={14} />APPROVE</button>
                  <button className="reject" onClick={() => decide(o.id, 'reject')} disabled={busy}><XCircle size={14} />REJECT</button>
                </div>
                : <div className="order-actions"><span className="decision">locked · human decision recorded</span></div>
              }
            </article>
          ))}</div>
          : <div className="empty">Dispatch a high-risk location to draft an auditable work order.</div>
        }
      </section>
    </main>
  )
}
