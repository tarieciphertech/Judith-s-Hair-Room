import { CalendarDays, CheckCircle2, Clock3, MessageCircle, Phone, Scissors } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import './booking.css'

type BookingResult = { id: string; customer_name: string; phone: string; style_name: string; date: string; start_time: string; expected_end_time: string; agreed_price: number; deposit_amount: number; balance: number; status: string; payment_status: string }
const money = (n: number) => `P${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const dateLabel = (v: string) => new Date(`${v}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

export default function Confirmation() {
  const location = useLocation()
  let booking = location.state as BookingResult | null
  if (!booking) {
    try { booking = JSON.parse(sessionStorage.getItem('judith_booking_confirmation') || 'null') } catch { booking = null }
  }

  if (!booking) return <div className="booking-shell"><main className="booking-main"><div className="booking-card confirmation-empty"><Scissors /><h1>Booking confirmation</h1><p>We couldn't find a recent booking on this device. Please start a new booking.</p><Link className="booking-primary" to="/booking">Start a booking</Link></div></main></div>

  return <div className="booking-shell">
    <header className="booking-header"><Link className="booking-brand" to="/"><span><Scissors /></span><div><strong>Judith's Hair Room</strong><small>Booking confirmed</small></div></Link></header>
    <main className="booking-main confirmation-main">
      <div className="confirmation-mark"><CheckCircle2 /></div>
      <div className="booking-intro confirmation-intro"><p className="eyebrow">APPOINTMENT CONFIRMED</p><h1>You're booked, {booking.customer_name.split(' ')[0]}.</h1><p>Judith's Hair Room has your appointment. Keep this page for your booking details.</p></div>
      <section className="booking-card confirmation-card">
        <div className="confirmation-style"><span className="confirmation-icon"><Scissors /></span><div><span>Service</span><strong>{booking.style_name}</strong></div></div>
        <div className="confirmation-grid"><div><CalendarDays /><span>Date</span><strong>{dateLabel(booking.date)}</strong></div><div><Clock3 /><span>Time</span><strong>{booking.start_time} – {booking.expected_end_time}</strong></div><div><span>Total</span><strong>{money(booking.agreed_price)}</strong></div><div><span>Deposit paid</span><strong>{money(booking.deposit_amount)}</strong></div></div>
        <div className="confirmation-reference"><span>Booking reference</span><strong>{booking.id.slice(0, 8).toUpperCase()}</strong></div>
        <div className="confirmation-note"><strong>What's next?</strong><p>Keep your required hair ready and contact Judith if you need to reschedule. Your remaining balance is {money(booking.balance)}.</p></div>
      </section>
      <div className="confirmation-actions"><a className="booking-secondary" href={`tel:${booking.phone}`}><Phone /> Call Judith</a><a className="booking-secondary" href={`https://wa.me/${booking.phone.replace(/\D/g, '')}`} target="_blank" rel="noreferrer"><MessageCircle /> WhatsApp</a><Link className="booking-primary" to="/booking">Book another</Link></div>
    </main>
  </div>
}
