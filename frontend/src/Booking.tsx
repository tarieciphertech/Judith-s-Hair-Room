import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { CalendarDays, Check, ChevronLeft, ChevronRight, Clock3, CreditCard, Scissors, ShieldCheck, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ApiError, api } from './api'
import './booking.css'

type Style = { id: string; name: string; min_price: number; max_price: number; estimated_duration_minutes: number; required_hair: string; description?: string }
type Suggestion = { date: string; start_time: string; end_time: string }
type Availability = { available: boolean; reason: string | null; requested_slot: { date: string; start_time: string; end_time: string }; suggestions: Suggestion[] }
type BookingResult = { id: string; customer_name: string; phone: string; style_name: string; date: string; start_time: string; expected_end_time: string; agreed_price: number; deposit_amount: number; balance: number; status: string; payment_status: string }

type Form = { style_id: string; agreed_price: string; date: string; start_time: string; customer_name: string; phone: string; email: string; notes: string; deposit_reference: string; hair_confirmed: boolean }

const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
const money = (n: number) => `P${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const endFor = (date: string, start: string, minutes: number) => {
  const value = new Date(`${date}T${start}:00`)
  value.setMinutes(value.getMinutes() + minutes)
  if (value.getDate() !== new Date(`${date}T12:00:00`).getDate()) return ''
  return `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`
}
const dateLabel = (v: string) => new Date(`${v}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

function StepTitle({ step, title, text }: { step: number; title: string; text: string }) {
  return <div className="booking-step-title"><span className="booking-step-number">{step}</span><div><p className="eyebrow">STEP {step} OF 8</p><h2>{title}</h2><p>{text}</p></div></div>
}

function ChoiceButton({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button type="button" className={`booking-choice ${selected ? 'selected' : ''}`} onClick={onClick}>{children}{selected && <Check />}</button>
}

export default function Booking() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [styles, setStyles] = useState<Style[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [availability, setAvailability] = useState<Availability | null>(null)
  const [conflictSuggestions, setConflictSuggestions] = useState<Suggestion[]>([])
  const [form, setForm] = useState<Form>({ style_id: '', agreed_price: '', date: today(), start_time: '10:00', customer_name: '', phone: '', email: '', notes: '', deposit_reference: '', hair_confirmed: false })

  useEffect(() => { api.styles().then(setStyles).catch(e => setError(e?.message || 'We could not load the styles.')).finally(() => setLoading(false)) }, [])

  const style = useMemo(() => styles.find(s => s.id === form.style_id), [styles, form.style_id])
  const endTime = style ? endFor(form.date, form.start_time, style.estimated_duration_minutes) : ''
  const price = Number(form.agreed_price || 0)
  const deposit = Math.round(price * 0.5 * 100) / 100
  const progress = Math.round((step / 8) * 100)

  const update = <K extends keyof Form>(key: K, value: Form[K]) => setForm(current => ({ ...current, [key]: value }))
  const next = () => { setError(''); setStep(s => Math.min(8, s + 1)) }
  const back = () => { setError(''); setAvailability(null); setConflictSuggestions([]); setStep(s => Math.max(1, s - 1)) }

  async function checkAvailability() {
    if (!style || !endTime) { setError('This appointment duration cannot fit on the selected date and time.'); return }
    setBusy(true); setError(''); setConflictSuggestions([])
    try {
      const result = await api.availability(form.date, form.start_time, endTime) as Availability
      setAvailability(result)
      if (result.available) setStep(7)
      else { setConflictSuggestions(result.suggestions || []); setError('That time is not available. Choose one of the suggested slots.') }
    } catch (e: any) { setError(e?.message || 'Could not check availability.') } finally { setBusy(false) }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!style || !endTime) return
    setBusy(true); setError(''); setConflictSuggestions([])
    try {
      const result = await api.createAppointment({
        customer_name: form.customer_name.trim(), phone: form.phone.trim(), email: form.email.trim() || null,
        notes: form.notes.trim(), style_id: form.style_id, date: form.date, start_time: form.start_time,
        expected_end_time: endTime, agreed_price: price, deposit_amount: deposit,
      }) as BookingResult
      sessionStorage.setItem('judith_booking_confirmation', JSON.stringify(result))
      navigate('/booking/confirmation', { state: result })
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 409) {
        const suggestions = e.detail?.suggestions || []
        setConflictSuggestions(suggestions)
        setError(e.message || 'That time was just booked. Please choose another slot.')
        setStep(6)
      } else setError(e?.message || 'We could not confirm the booking. Please try again.')
    } finally { setBusy(false) }
  }

  function chooseSuggestion(s: Suggestion) { update('date', s.date); update('start_time', s.start_time); setAvailability(null); setConflictSuggestions([]); setError(''); setStep(5) }

  if (loading) return <div className="booking-shell"><div className="booking-card booking-loading">Loading Judith's styles…</div></div>

  return <div className="booking-shell">
    <header className="booking-header"><button className="booking-brand" onClick={() => navigate('/')}><span><Scissors /></span><div><strong>Judith's Hair Room</strong><small>Online booking</small></div></button><div className="booking-trust"><ShieldCheck /> Secure booking</div></header>
    <main className="booking-main">
      <div className="booking-intro"><p className="eyebrow">BOOK YOUR APPOINTMENT</p><h1>Your hair, your time.</h1><p>Choose your style, find a real available slot, then secure it with a 50% Orange Money deposit.</p></div>
      <div className="booking-progress"><div><span>Booking progress</span><strong>{progress}%</strong></div><div className="progress-track"><span style={{ width: `${progress}%` }} /></div></div>
      {error && <div className="booking-alert">{error}</div>}

      <form className="booking-card" onSubmit={submit}>
        {step === 1 && <div><StepTitle step={1} title="Choose your style" text="Select the service you want Judith to prepare for." /><div className="style-grid">{styles.map(s => <ChoiceButton key={s.id} selected={form.style_id === s.id} onClick={() => { update('style_id', s.id); update('agreed_price', String(s.min_price)); setError('') }}><span><strong>{s.name}</strong><small>{money(s.min_price)} – {money(s.max_price)}</small><small>{s.estimated_duration_minutes} minutes</small></span></ChoiceButton>)}</div>{style?.description && <div className="booking-note">{style.description}</div>}</div>}

        {step === 2 && style && <div><StepTitle step={2} title="Agree your price" text={`The selected ${style.name} is priced between ${money(style.min_price)} and ${money(style.max_price)}.`} /><label className="booking-field"><span>Agreed price</span><div className="price-input"><b>P</b><input type="number" min={style.min_price} max={style.max_price} step="0.01" value={form.agreed_price} onChange={e => update('agreed_price', e.target.value)} required /></div></label><div className="booking-summary-line"><span>50% deposit</span><strong>{money(deposit)}</strong></div><div className="booking-summary-line"><span>Remaining balance</span><strong>{money(Math.max(0, price - deposit))}</strong></div></div>}

        {step === 3 && style && <div><StepTitle step={3} title="Prepare your hair" text="This is the hair/material Judith needs ready before your appointment." /><div className="hair-card"><div className="hair-icon"><Scissors /></div><div><span>Required hair</span><strong>{style.required_hair || 'Please confirm the required hair with Judith before booking.'}</strong></div></div><label className="check-row"><input type="checkbox" checked={form.hair_confirmed} onChange={e => update('hair_confirmed', e.target.checked)} /><span>I understand the required hair and will have it ready.</span></label></div>}

        {step === 4 && <div><StepTitle step={4} title="Pick a date" text="Choose a date within Judith's booking window." /><label className="booking-field"><span>Appointment date</span><input type="date" min={today()} value={form.date} onChange={e => { update('date', e.target.value); setAvailability(null) }} required /></label><div className="booking-date-preview"><CalendarDays /><span>{dateLabel(form.date)}</span></div></div>}

        {step === 5 && style && <div><StepTitle step={5} title="Choose a time" text={`Your ${style.name} takes about ${style.estimated_duration_minutes} minutes.`} /><label className="booking-field"><span>Start time</span><input type="time" value={form.start_time} onChange={e => { update('start_time', e.target.value); setAvailability(null) }} required /></label>{endTime ? <div className="duration-card"><Clock3 /><div><span>Estimated finish</span><strong>{form.start_time} – {endTime}</strong><small>This is an estimate used to request availability.</small></div></div> : <div className="booking-alert">This service would run past midnight. Please choose an earlier start time.</div>}</div>}

        {step === 6 && style && <div><StepTitle step={6} title="Check availability" text="The server now checks Judith's real calendar, working hours and blocked time." />{availability?.available && <div className="availability-success"><Check /><div><strong>That slot is available</strong><span>{dateLabel(form.date)} · {form.start_time} – {endTime}</span></div></div>}{availability && !availability.available && <div className="availability-fail"><Clock3 /><div><strong>That slot is occupied</strong><span>{availability.reason?.replaceAll('_', ' ')}</span></div></div>}{conflictSuggestions.length > 0 && <div className="suggestions"><strong>Try one of these instead</strong>{conflictSuggestions.map(s => <button type="button" key={`${s.date}-${s.start_time}`} onClick={() => chooseSuggestion(s)}>{dateLabel(s.date)} · {s.start_time} – {s.end_time}<ChevronRight /></button>)}</div>}<button type="button" className="booking-secondary" disabled={busy} onClick={() => void checkAvailability()}>{busy ? 'Checking Judith’s calendar…' : 'Check this time again'}</button></div>}

        {step === 7 && <div><StepTitle step={7} title="Your details" text="Tell Judith who the appointment is for and anything she should know." /><div className="booking-fields-grid"><label className="booking-field"><span>Full name</span><input required minLength={2} value={form.customer_name} onChange={e => update('customer_name', e.target.value)} autoComplete="name" /></label><label className="booking-field"><span>Phone / WhatsApp</span><input required minLength={5} value={form.phone} onChange={e => update('phone', e.target.value)} autoComplete="tel" /></label><label className="booking-field"><span>Email <em>optional</em></span><input type="email" value={form.email} onChange={e => update('email', e.target.value)} autoComplete="email" /></label><label className="booking-field"><span>Notes / preferences <em>optional</em></span><textarea rows={4} value={form.notes} onChange={e => update('notes', e.target.value)} placeholder="Anything Judith should know?" /></label></div></div>}

        {step === 8 && <div><StepTitle step={8} title="Secure your booking" text="A 50% Orange Money deposit secures your appointment." /><div className="payment-instructions"><CreditCard /><div><strong>Orange Money deposit</strong><p>Send <b>{money(deposit)}</b> to Judith using the salon's Orange Money details provided by Judith.</p><span>Enter your payment reference below after sending.</span></div></div><label className="booking-field"><span>Orange Money reference</span><input value={form.deposit_reference} onChange={e => update('deposit_reference', e.target.value)} placeholder="Payment reference" required /></label><div className="booking-confirm-summary"><div><span>Style</span><strong>{style?.name}</strong></div><div><span>Date & time</span><strong>{dateLabel(form.date)} · {form.start_time}</strong></div><div><span>Total</span><strong>{money(price)}</strong></div><div><span>Deposit</span><strong>{money(deposit)}</strong></div></div><button className="booking-primary wide" disabled={busy}>{busy ? 'Confirming your appointment…' : 'Confirm booking'}</button></div>}

        <div className="booking-actions">{step > 1 && <button type="button" className="booking-secondary" onClick={back}><ChevronLeft /> Back</button>}{step === 1 && <button type="button" className="booking-primary" disabled={!form.style_id} onClick={next}>Continue <ChevronRight /></button>}{step === 2 && <button type="button" className="booking-primary" disabled={!price || !style || price < style.min_price || price > style.max_price} onClick={next}>Continue <ChevronRight /></button>}{step === 3 && <button type="button" className="booking-primary" disabled={!form.hair_confirmed} onClick={next}>Continue <ChevronRight /></button>}{step === 4 && <button type="button" className="booking-primary" disabled={!form.date} onClick={next}>Continue <ChevronRight /></button>}{step === 5 && <button type="button" className="booking-primary" disabled={!endTime} onClick={() => { setStep(6); void checkAvailability() }}>Check availability <ChevronRight /></button>}{step === 6 && availability?.available && <button type="button" className="booking-primary" onClick={next}>Continue <ChevronRight /></button>}{step === 7 && <button type="button" className="booking-primary" disabled={!form.customer_name.trim() || !form.phone.trim()} onClick={next}>Continue to deposit <ChevronRight /></button>}</div>
      </form>
      <p className="booking-footnote"><UserRound /> Your details are used only to manage your appointment and customer record.</p>
    </main>
  </div>
}
