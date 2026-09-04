import { useEffect, useState } from 'react'
import { CalendarDays, CheckCircle2, Clock3, LayoutDashboard, Plus, Scissors, UserRound, XCircle } from 'lucide-react'
import { api } from './api'

type Appointment = {id:string; customer_name:string; style_name:string; date:string; start_time:string; expected_end_time:string; agreed_price:number; deposit_amount:number; balance:number; status:string; payment_status:string}

type Style = {id:string; name:string; min_price:number; max_price:number; estimated_duration_minutes:number; required_hair:string}

const money = (n:number) => `P${n.toLocaleString()}`

export default function App() {
  const [tab, setTab] = useState<'today'|'book'>('today')
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [styles, setStyles] = useState<Style[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({customer_name:'',phone:'',style_id:'',date:new Date().toISOString().slice(0,10),start_time:'10:00',agreed_price:''})

  async function load() {
    try { const [a,s] = await Promise.all([api.appointments(), api.styles()]); setAppointments(a); setStyles(s) } catch(e:any) { setMessage(e.message) }
  }
  useEffect(()=>{load()},[])

  const today = new Date().toISOString().slice(0,10)
  const todays = appointments.filter(a=>a.date===today && a.status!=='CANCELLED').sort((a,b)=>a.start_time.localeCompare(b.start_time))
  const active = todays.find(a=>a.status==='IN_PROGRESS')
  const next = todays.find(a=>['PENDING','CONFIRMED'].includes(a.status) && a.start_time >= new Date().toTimeString().slice(0,5))
  const occupied = !!active

  async function action(fn:()=>Promise<any>) { setBusy(true); setMessage(''); try {await fn(); await load()} catch(e:any){setMessage(e.message)} finally{setBusy(false)} }
  async function create(e:React.FormEvent) {
    e.preventDefault(); const style=styles.find(s=>s.id===form.style_id); if(!style)return
    const start = new Date(`${form.date}T${form.start_time}:00`); const end = new Date(start.getTime()+style.estimated_duration_minutes*60000)
    await action(()=>api.createAppointment({customer_name:form.customer_name,phone:form.phone,style_id:form.style_id,date:form.date,start_time:form.start_time,expected_end_time:end.toTimeString().slice(0,5),agreed_price:Number(form.agreed_price),deposit_amount:Number(form.agreed_price)*.5}))
    setTab('today'); setForm({...form,customer_name:'',phone:'',style_id:'',agreed_price:''})
  }

  return <div className="app-shell">
    <header className="topbar"><div><p className="eyebrow">DIGITAL SECRETARY</p><h1>Judith's Hair Room</h1></div><div className={occupied?'status occupied':'status available'}><span/> {occupied?'OCCUPIED':'AVAILABLE'}</div></header>
    <main>
      {tab==='today' ? <>
        <section className="hero-card"><div><p className="eyebrow">RIGHT NOW</p><h2>{active?`Working with ${active.customer_name}`:next?`Next: ${next.customer_name}`:'No client right now'}</h2><p className="muted">{active?`${active.style_name} · started ${active.start_time}`:next?`${next.start_time} · ${next.style_name}`:'Your next booking will appear here.'}</p></div>{active?<button className="done" disabled={busy} onClick={()=>action(()=>api.complete(active.id))}><CheckCircle2/> DONE</button>:next?<button className="primary" disabled={busy} onClick={()=>action(()=>api.start(next.id))}><Clock3/> START</button>:null}</section>
        {message&&<div className="alert">{message}</div>}
        <div className="section-head"><div><p className="eyebrow">TODAY</p><h2>Appointments</h2></div><button className="icon-btn" onClick={()=>setTab('book')}><Plus/></button></div>
        <section className="timeline">{todays.length===0?<div className="empty"><CalendarDays/><p>No appointments today.</p><button className="primary" onClick={()=>setTab('book')}>Add appointment</button></div>:todays.map(a=><article className={`appointment ${a.status.toLowerCase()}`} key={a.id}><div className="time">{a.start_time}<small>{a.expected_end_time}</small></div><div className="appt-main"><strong>{a.customer_name}</strong><span>{a.style_name}</span><small>{money(a.agreed_price)} · {a.payment_status.replace('_',' ')}</small></div><div className="appt-state">{a.status==='COMPLETED'?<CheckCircle2/>:a.status==='CANCELLED'?<XCircle/>:<Clock3/>}</div></article>)}</section>
      </> : <>
        <div className="section-head"><div><p className="eyebrow">NEW BOOKING</p><h2>Book a client</h2></div><button className="ghost" onClick={()=>setTab('today')}>Back</button></div>
        <form className="card form" onSubmit={create}><label>Customer name<input required value={form.customer_name} onChange={e=>setForm({...form,customer_name:e.target.value})}/></label><label>Phone / WhatsApp<input required value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label><label>Style<select required value={form.style_id} onChange={e=>setForm({...form,style_id:e.target.value})}><option value="">Choose a style</option>{styles.map(s=><option key={s.id} value={s.id}>{s.name} — {money(s.min_price)}–{money(s.max_price)} · {s.required_hair}</option>)}</select></label><label>Date<input required type="date" min={today} value={form.date} onChange={e=>setForm({...form,date:e.target.value})}/></label><label>Start time<input required type="time" value={form.start_time} onChange={e=>setForm({...form,start_time:e.target.value})}/></label><label>Agreed price (P)<input required min="1" type="number" value={form.agreed_price} onChange={e=>setForm({...form,agreed_price:e.target.value})}/></label><div className="deposit">50% Orange Money deposit: <strong>{money(Number(form.agreed_price||0)*.5)}</strong></div><button className="primary wide" disabled={busy}><CheckCircle2/> Check availability & book</button></form>
      </>}
    </main>
    <nav className="bottom-nav"><button className={tab==='today'?'active':''} onClick={()=>setTab('today')}><LayoutDashboard/>Today</button><button className={tab==='book'?'active':''} onClick={()=>setTab('book')}><UserRound/>Book</button></nav>
  </div>
}
