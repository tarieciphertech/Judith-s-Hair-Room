import { useEffect, useState } from 'react'
import { ArrowRight, CalendarDays, Check, Clock3, MessageCircle, Scissors, ShieldCheck, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from './api'

type Style = { id: string; name: string; min_price: number; max_price: number; estimated_duration_minutes: number; required_hair: string; description?: string }

const money = (n: number) => `P${Number(n || 0).toLocaleString()}`

export default function Landing() {
  const navigate = useNavigate()
  const [styles, setStyles] = useState<Style[]>([])

  useEffect(() => { api.styles().then(setStyles).catch(() => setStyles([])) }, [])

  return <div className="landing-shell">
    <header className="landing-nav">
      <button className="landing-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
        <span className="landing-brand-mark"><Scissors /></span>
        <span><strong>Judith's Hair Room</strong><small>Beautiful hair. Personal service.</small></span>
      </button>
      <nav><a href="#services">Services</a><a href="#about">About</a><button onClick={() => navigate('/booking')}>Book now <ArrowRight /></button></nav>
    </header>

    <main>
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <p className="eyebrow"><Sparkles /> JUDITH'S HAIR ROOM</p>
          <h1>Your hair deserves <em>your moment.</em></h1>
          <p className="landing-lead">A warm, personal hair experience with Judith — from choosing your style to securing a time that genuinely works.</p>
          <div className="landing-actions"><button className="landing-primary" onClick={() => navigate('/booking')}>Book an appointment <ArrowRight /></button><a className="landing-text-link" href="#services">Explore services</a></div>
          <div className="landing-trust"><span><Check /> Real availability</span><span><ShieldCheck /> Secure booking</span><span><Clock3 /> Personal service</span></div>
        </div>
        <div className="landing-hero-art" aria-hidden="true">
          <div className="hero-orb hero-orb-one" /><div className="hero-orb hero-orb-two" />
          <div className="salon-card"><Scissors /><span>JUDITH'S</span><strong>Hair Room</strong><small>Appointments by booking</small></div>
        </div>
      </section>

      <section className="landing-intro" id="about">
        <div><p className="eyebrow">A LITTLE ABOUT THE ROOM</p><h2>One chair. One stylist. <em>All attention on you.</em></h2></div>
        <p>Judith's Hair Room is built around personal service. No rushed hand-offs, no guessing when to arrive — just a clear appointment, a style prepared for you, and Judith ready for your time.</p>
      </section>

      <section className="landing-services" id="services">
        <div className="landing-section-head"><div><p className="eyebrow">THE MENU</p><h2>Choose your style.</h2></div><button onClick={() => navigate('/booking')}>See availability <ArrowRight /></button></div>
        {styles.length > 0 ? <div className="landing-service-grid">{styles.slice(0, 6).map(s => <article className="landing-service-card" key={s.id}><span className="service-number">0{styles.indexOf(s) + 1}</span><div><h3>{s.name}</h3><p>{s.description || `A personalised ${s.name} appointment prepared around your hair needs.`}</p><div><strong>{money(s.min_price)} – {money(s.max_price)}</strong><span><Clock3 /> {s.estimated_duration_minutes} min</span></div></div></article>)}</div> : <div className="landing-service-empty">Services are loading — you can still <button onClick={() => navigate('/booking')}>start your booking</button>.</div>}
      </section>

      <section className="landing-booking-cta">
        <div><p className="eyebrow">READY WHEN YOU ARE</p><h2>Let's find your <em>perfect time.</em></h2><p>Choose your style, see Judith's actual availability, and secure your appointment with a 50% deposit.</p></div>
        <button className="landing-primary" onClick={() => navigate('/booking')}><CalendarDays /> Book your appointment <ArrowRight /></button>
      </section>

      <section className="landing-contact">
        <div><span className="landing-brand-mark"><Scissors /></span><div><h2>Judith's Hair Room</h2><p>Beautiful hair. Personal service.</p></div></div>
        <div className="landing-contact-links"><a href="https://wa.me/26700000000"><MessageCircle /> WhatsApp Judith</a><button onClick={() => navigate('/booking')}>Book online <ArrowRight /></button></div>
      </section>
    </main>
    <footer><span>© {new Date().getFullYear()} Judith's Hair Room</span><button onClick={() => navigate('/admin')}>Owner login</button></footer>
  </div>
}
