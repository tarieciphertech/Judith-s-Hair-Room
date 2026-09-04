import { useEffect, useMemo, useState } from 'react'
import { CalendarDays, CheckCircle2, Clock3, LayoutDashboard, Plus, Scissors, UserRound, XCircle, WalletCards, UsersRound } from 'lucide-react'
import { api } from './api'

type Appointment = { id:string; customer_name:string; phone:string; style_name:string; date:string; start_time:string; expected_end_time:string; agreed_price:number; deposit_amount:number; balance:number; status:string; payment_status:string }
type Style = { id:string; name:string; min_price:number; max_price:number; estimated_duration_minutes:number; required_hair:string }
type Dashboard = { today:string; occupied:boolean; appointments:number; completed:number; unpaid_deposits:number; revenue:number }

const money = (n:number) => `P${n.toLocaleString()}`
const localDate = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }
const prettyDate = (value:string) => new Date(`${value}T12:00:00`).toLocaleDateString(undefined,{weekday:'short',day:'numeric',month:'short'})

export default function App() {
  const [tab, setTab] = useState<'today'|'book'>('today')
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [styles, setStyles] = useState<Style[]>([])
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [now, setNow] = useState(new Date())
  const [form, setForm] = useState({customer_name:'',phone:'',style_id:'',date:localDate(),start_time:'10:00',agreed_price:''})

  async function load() {
    try {
      const [a,s,d] = await Promise.all([api.appointments(), api.styles(), api.dashboard()])
      setAppointments(a); setStyles(s); setDashboard(d)
    } catch(e:any) { setMessage(e.message || 'Could not load the dashboard.') }
  }
  useEffect(()=>{ load(); const timer=setInterval(()=>setNow(new Date()),30000); return ()=>clearInterval(timer) },[])

  const today = localDate()
  const todays = useMemo(()=>appointments.filter(a=>a.date===today && a.status!=='CANCELLED').sort((a,b)=>a.start_time.localeCompare(b.start_time)),[appointments,today])
  const active = todays.find(a=>a.status==='IN_PROGRESS')
  const currentTime = now.toTimeString().slice(0,5)
  const next = todays.find(a=>['PENDING','CONFIRMED'].includes(a.status) && a.start_time >= currentTime)
  const upcoming = appointments.filter(a=>a.date>today && ['PENDING','CONFIRMED'].includes(a.status)).sort((a,b)=>`${a.date}${a.start_time}`.localeCompare(`${b.date}${b.start_time}`)).slice(0,3)
  const occupied = !!active

  async function action(fn:()=>Promise<any>) { setBusy(true); setMessage(''); try { await fn(); await load() } catch(e:any) { setMessage(typeof e.message==='string'?e.message:'Action failed.') } finally { setBusy(false) } }

  async function create(e:React.FormEvent) {
    e.preventDefault(); const style=styles.find(s=>s.id===form.style_id); if(!style)return
    const start = new Date(`${form.date}T${form.start_time}:00`)
    const end = new Date(start.getTime()+style.estimated_duration_minutes*60000)
    await action(()=>api.createAppointment({customer_name:form.customer_name.trim(),phone:form.phone.trim(),style_id:form.style_id,date:form.date,start_time:form.start_time,expected_end_time:end.toTimeString().slice(0,5),agreed_price:Number(form.agreed_price),deposit_amount:Number(form.agreed_price)*.5}))
    setTab('today'); setForm({...form,customer_name:'',phone:'',style_id:'',agreed_price:''})
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Scissors/></div><div><p className="eyebrow">DIGITAL SECRETARY</p><h1>Judith's Hair Room</h1><p className="date-line">{now.toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'long'})}</p></div></div>
      <div className={occupied?'status occupied':'status available'}><span/> {occupied?'OCCUPIED':'AVAILABLE'}</div>
    </header>

    <main>
      {tab==='today' ? <>
        <section className="hero-card">
          <div className="hero-copy"><p className="eyebrow">{active?'CURRENT CLIENT':'RIGHT NOW'}</p><h2>{active?`Working with ${active.customer_name}`:next?`Next: ${next.customer_name}`:'You're free'}</h2><p className="muted">{active?`${active.style_name} · started at ${active.start_time}`:next?`${next.start_time} · ${next.style_name}`:'No appointment is being worked on right now.'}</p></div>
          {active?<button className="done" disabled={busy} onClick={()=>action(()=>api.complete(active.id))}><CheckCircle2/> DONE</button>:next?<button className="primary" disabled={busy} onClick={()=>action(()=>api.start(next.id))}><Clock3/> START</button>:<button className="primary" onClick={()=>setTab('book')}><Plus/> BOOK CLIENT</button>}
        </section>

        {message&&<div className="alert">{message}</div>}

        <section className="stats-grid">
          <div className="stat-card"><CalendarDays/><div><span>Today</span><strong>{dashboard?.appointments ?? todays.length}</strong></div></div>
          <div className="stat-card"><CheckCircle2/><div><span>Completed</span><strong>{dashboard?.completed ?? 0}</strong></div></div>
          <div className="stat-card"><WalletCards/><div><span>Revenue</span><strong>{money(dashboard?.revenue ?? 0)}</strong></div></div>
          <div className="stat-card"><UsersRound/><div><span>Unpaid</span><strong>{dashboard?.unpaid_deposits ?? 0}</strong></div></div>
        </section>

        <div className="section-head"><div><p className="eyebrow">TODAY · {todays.length} BOOKING{todays.length===1?'':'S'}</p><h2>Appointments</h2></div><button className="icon-btn" onClick={()=>setTab('book')} aria-label="Add appointment"><Plus/></button></div>
        <section className="timeline">{todays.length===0?<div className="empty"><CalendarDays/><strong>Your day is clear</strong><p>No appointments scheduled for today.</p><button className="primary" onClick={()=>setTab('book')}>Add appointment</button></div>:todays.map(a=><article className={`appointment ${a.status.toLowerCase()} ${a.id===active?.id?'is-active':''}`} key={a.id}><div className="time">{a.start_time}<small>{a.expected_end_time}</small></div><div className="appt-main"><strong>{a.customer_name}</strong><span>{a.style_name}</span><small>{money(a.agreed_price)} · {a.payment_status.replaceAll('_',' ')}</small></div><div className="appt-state">{a.status==='COMPLETED'?<CheckCircle2/>:a.status==='CANCELLED'?<XCircle/>:<Clock3/>}</div></article>)}</section>

        <section className="upcoming-block"><div className="section-head"><div><p className="eyebrow">COMING UP</p><h2>Upcoming</h2></div></div>{upcoming.length===0?<p className="muted">No future bookings yet.</p>:upcoming.map(a=><div className="upcoming-row" key={a.id}><div><strong>{a.customer_name}</strong><span>{a.style_name}</span></div><div><strong>{prettyDate(a.date)}</strong><span>{a.start_time} · {money(a.agreed_price)}</span></div></div>)}</section>
      </> : <>
        <div className="section-head"><div><p className="eyebrow">NEW BOOKING</p><h2>Book a client</h2><p className="muted">Reserve the chair and collect the 50% deposit.</p></div><button className="ghost" onClick={()=>setTab('today')}>Back</button></div>
        <form className="card form" onSubmit={create}>
          <label>Customer name<input required minLength={2} value={form.customer_name} onChange={e=>setForm({...form,customer_name:e.target.value})} placeholder="e.g. Rudo Moyo"/></label>
          <label>Phone / WhatsApp<input required minLength={5} value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})} placeholder="07..."/></label>
          <label>Style<select required value={form.style_id} onChange={e=>setForm({...form,style_id:e.target.value})}><option value="">Choose a style</option>{styles.map(s=><option key={s.id} value={s.id}>{s.name} — {money(s.min_price)}–{money(s.max_price)} · {s.required_hair}</option>)}</select></label>
          <div className="form-row"><label>Date<input required type="date" min={today} value={form.date} onChange={e=>setForm({...form,date:e.target.value})}/></label><label>Start time<input required type="time" value={form.start_time} onChange={e=>setForm({...form,start_time:e.target.value})}/></label></div>
          <label>Agreed price (P)<input required min="1" type="number" value={form.agreed_price} onChange={e=>setForm({...form,agreed_price:e.target.value})} placeholder="Enter final agreed price"/></label>
          {form.style_id&&<div className="style-note"><strong>{styles.find(s=>s.id===form.style_id)?.name}</strong><span>{styles.find(s=>s.id===form.style_id)?.estimated_duration_minutes} min estimated · {styles.find(s=>s.id===form.style_id)?.required_hair}</span></div>}
          <div className="deposit"><span>50% Orange Money deposit</span><strong>{money(Number(form.agreed_price||0)*.5)}</strong></div>
          <button className="primary wide" disabled={busy}>{busy?'Booking…':<><CheckCircle2/> Check availability & book</>}</button>
        </form>
      </>}
    </main>
    <nav className="bottom-nav"><button className={tab==='today'?'active':''} onClick={()=>setTab('today')}><LayoutDashboard/>Today</button><button className={tab==='book'?'active':''} onClick={()=>setTab('book')}><UserRound/>Book</button></nav>
  </div>
}
