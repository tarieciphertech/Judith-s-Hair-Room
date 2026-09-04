from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .availability import BLOCKING_STATUSES, generate_slots, overlaps
from .config import settings
from .db import get_db, lock_calendar_day
from .models import Appointment, BlockedTime, Customer, Payment, SalonSettings, Style

app = FastAPI(title="Judith's Hair Room API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StyleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; name: str; min_price: Decimal; max_price: Decimal; estimated_duration_minutes: int; required_hair: str; description: str = ''

class BookingIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    notes: str = Field(default='', max_length=2000)
    style_id: UUID
    date: date
    start_time: time
    expected_end_time: time
    agreed_price: Decimal = Field(gt=0)
    deposit_amount: Decimal = Field(gt=0)

class AppointmentUpdate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    style_id: UUID
    date: date
    start_time: time
    expected_end_time: time
    agreed_price: Decimal = Field(gt=0)

class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0)
    method: str = Field(default='Orange Money', max_length=40)
    payment_type: str = Field(default='BALANCE', max_length=20)
    reference: str | None = Field(default=None, max_length=120)

class CustomerUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    preferred_styles: str = ''
    notes: str = ''

class BlockIn(BaseModel):
    date: date
    start_time: time
    end_time: time
    reason: str = Field(min_length=2, max_length=255)

class AppointmentOut(BaseModel):
    id: str; customer_id: str; customer_name: str; phone: str; style_id: str; style_name: str
    date: date; start_time: time; expected_end_time: time; actual_end_time: time | None = None
    agreed_price: Decimal; deposit_amount: Decimal; balance: Decimal; status: str; payment_status: str
    started_at: datetime | None = None; completed_at: datetime | None = None

class CustomerOut(BaseModel):
    id: str; name: str; phone: str; email: str | None; preferred_styles: str; notes: str
    created_at: datetime; last_visit: datetime | None; appointments: int

class BlockOut(BaseModel):
    id: str; date: date; start_time: time; end_time: time; reason: str


def get_settings_row(db: Session) -> SalonSettings:
    row = db.scalar(select(SalonSettings).limit(1))
    if not row:
        row = SalonSettings()
        db.add(row); db.commit(); db.refresh(row)
    return row


def appointment_out(a: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=a.id, customer_id=a.customer_id, customer_name=a.customer.name, phone=a.customer.phone,
        style_id=a.style_id, style_name=a.style.name, date=a.appointment_date, start_time=a.start_time,
        expected_end_time=a.expected_end_time, actual_end_time=a.actual_end_time, agreed_price=a.agreed_price,
        deposit_amount=a.deposit_amount, balance=a.balance, status=a.status, payment_status=a.payment_status,
        started_at=a.started_at, completed_at=a.completed_at,
    )


def blocking_conflict(db: Session, day: date, start: time, end: time, exclude_id: str | None = None) -> str | None:
    query = select(Appointment).where(
        Appointment.appointment_date == day,
        Appointment.status.in_(BLOCKING_STATUSES),
        Appointment.start_time < end,
        Appointment.expected_end_time > start,
    )
    if exclude_id:
        query = query.where(Appointment.id != exclude_id)
    if db.scalar(query.limit(1)):
        return 'appointment_conflict'
    if db.scalar(select(BlockedTime.id).where(
        BlockedTime.blocked_date == day,
        BlockedTime.start_time < end,
        BlockedTime.end_time > start,
    ).limit(1)):
        return 'blocked_time'
    return None


def valid_calendar_window(cfg: SalonSettings, day: date, start: time, end: time) -> str | None:
    if end <= start: return 'invalid_time_range'
    if start < cfg.opening_time or end > cfg.closing_time: return 'outside_hours'
    if str(day.weekday()) not in {x.strip() for x in cfg.working_days.split(',') if x.strip()}: return 'closed_day'
    now = datetime.now()
    requested = datetime.combine(day, start)
    if requested < now + timedelta(minutes=cfg.booking_min_notice_minutes): return 'minimum_notice'
    if day > date.today() + timedelta(days=cfg.max_advance_days): return 'too_far_ahead'
    return None


def suggestions(db: Session, cfg: SalonSettings, day: date, duration_minutes: int, limit: int = 4):
    results = []
    for offset in range(0, 8):
        candidate_day = day + timedelta(days=offset)
        if str(candidate_day.weekday()) not in cfg.working_days.split(','): continue
        for slot in generate_slots(candidate_day, duration_minutes, cfg.opening_time, cfg.closing_time):
            reason = blocking_conflict(db, candidate_day, slot.start, slot.end)
            if not reason:
                if candidate_day == date.today() and datetime.combine(candidate_day, slot.start) < datetime.now() + timedelta(minutes=cfg.booking_min_notice_minutes):
                    continue
                results.append({'date': candidate_day.isoformat(), 'start_time': slot.start.strftime('%H:%M'), 'end_time': slot.end.strftime('%H:%M')})
                if len(results) >= limit: return results
    return results


def update_payment_state(a: Appointment):
    if a.deposit_amount <= 0: a.payment_status = 'UNPAID'
    elif a.balance <= 0: a.payment_status = 'FULLY_PAID'
    else: a.payment_status = 'DEPOSIT_PAID'

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'judiths-hair-room', 'database': 'postgresql'}

@app.get('/api/styles', response_model=list[StyleOut])
def styles(db: Session = Depends(get_db)):
    return db.scalars(select(Style).where(Style.active.is_(True)).order_by(Style.name)).all()

@app.get('/api/availability')
def availability(date: date, start_time: time, end_time: time, db: Session = Depends(get_db)):
    cfg = get_settings_row(db)
    window_error = valid_calendar_window(cfg, date, start_time, end_time)
    reason = window_error or blocking_conflict(db, date, start_time, end_time)
    duration = int((datetime.combine(date, end_time) - datetime.combine(date, start_time)).total_seconds() // 60)
    return {
        'available': reason is None,
        'reason': reason,
        'requested_slot': {'date': date.isoformat(), 'start_time': start_time.strftime('%H:%M'), 'end_time': end_time.strftime('%H:%M')},
        'suggestions': [] if reason is None else suggestions(db, cfg, date, duration),
    }

@app.post('/api/appointments', response_model=AppointmentOut, status_code=201)
def create_appointment(data: BookingIn, db: Session = Depends(get_db)):
    cfg = get_settings_row(db)
    style = db.get(Style, str(data.style_id))
    if not style or not style.active: raise HTTPException(404, 'Style not found')
    if data.agreed_price < style.min_price or data.agreed_price > style.max_price:
        raise HTTPException(400, 'Agreed price must be within the selected style price range')
    required_deposit = (data.agreed_price * Decimal(str(cfg.deposit_percentage)) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if data.deposit_amount < required_deposit:
        raise HTTPException(400, f'Deposit must be at least {required_deposit} ({cfg.deposit_percentage}%)')
    window_error = valid_calendar_window(cfg, data.date, data.start_time, data.expected_end_time)
    if window_error: raise HTTPException(400, window_error)

    lock_calendar_day(db, data.date)
    conflict = blocking_conflict(db, data.date, data.start_time, data.expected_end_time)
    if conflict:
        duration = int((datetime.combine(data.date, data.expected_end_time) - datetime.combine(data.date, data.start_time)).total_seconds() // 60)
        raise HTTPException(409, detail={'message': 'That slot is no longer available.', 'reason': conflict, 'suggestions': suggestions(db, cfg, data.date, duration)})

    customer = db.scalar(select(Customer).where(Customer.phone == data.phone))
    if not customer:
        customer = Customer(name=data.customer_name.strip(), phone=data.phone.strip(), email=data.email, notes=data.notes)
        db.add(customer); db.flush()
    else:
        customer.name = data.customer_name.strip(); customer.email = data.email or customer.email
        if data.notes: customer.notes = data.notes
    appointment = Appointment(
        customer_id=customer.id, style_id=style.id, appointment_date=data.date, start_time=data.start_time,
        expected_end_time=data.expected_end_time, agreed_price=data.agreed_price, deposit_amount=data.deposit_amount,
        balance=max(Decimal('0.00'), data.agreed_price - data.deposit_amount), status='CONFIRMED', payment_status='DEPOSIT_PAID',
    )
    db.add(appointment); db.flush()
    db.add(Payment(appointment_id=appointment.id, amount=data.deposit_amount, method='Orange Money', payment_type='DEPOSIT'))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail={'message': 'That slot was booked by someone else.', 'suggestions': suggestions(db, cfg, data.date, int((datetime.combine(data.date, data.expected_end_time)-datetime.combine(data.date, data.start_time)).total_seconds()//60))})
    appointment = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == appointment.id))
    return appointment_out(appointment)

@app.get('/api/appointments', response_model=list[AppointmentOut])
def appointments(
    date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).order_by(Appointment.appointment_date, Appointment.start_time)
    if date: stmt = stmt.where(Appointment.appointment_date == date)
    return [appointment_out(a) for a in db.scalars(stmt).unique().all()]

@app.patch('/api/appointments/{id}', response_model=AppointmentOut)
def edit_appointment(id: UUID, data: AppointmentUpdate, db: Session = Depends(get_db)):
    a = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == str(id)))
    if not a: raise HTTPException(404, 'Appointment not found')
    if a.status in ('COMPLETED', 'CANCELLED', 'NO_SHOW'): raise HTTPException(409, 'This appointment can no longer be edited')
    cfg = get_settings_row(db); style = db.get(Style, str(data.style_id))
    if not style or not style.active: raise HTTPException(404, 'Style not found')
    if data.agreed_price < style.min_price or data.agreed_price > style.max_price: raise HTTPException(400, 'Agreed price is outside the style range')
    window_error = valid_calendar_window(cfg, data.date, data.start_time, data.expected_end_time)
    if window_error: raise HTTPException(400, window_error)
    lock_calendar_day(db, data.date)
    if blocking_conflict(db, data.date, data.start_time, data.expected_end_time, a.id):
        duration = int((datetime.combine(data.date, data.expected_end_time)-datetime.combine(data.date, data.start_time)).total_seconds()//60)
        raise HTTPException(409, detail={'message': 'That new time is unavailable.', 'suggestions': suggestions(db, cfg, data.date, duration)})
    a.customer.name = data.customer_name; a.customer.phone = data.phone
    a.style_id = style.id; a.appointment_date = data.date; a.start_time = data.start_time; a.expected_end_time = data.expected_end_time; a.agreed_price = data.agreed_price
    a.balance = max(Decimal('0.00'), data.agreed_price - a.deposit_amount); update_payment_state(a)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, 'That time is already occupied')
    db.refresh(a); return appointment_out(a)

@app.post('/api/appointments/{id}/start', response_model=AppointmentOut)
def start(id: UUID, db: Session = Depends(get_db)):
    a = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == str(id)))
    if not a: raise HTTPException(404, 'Appointment not found')
    if a.status not in ('PENDING', 'CONFIRMED'): raise HTTPException(409, 'Appointment cannot be started')
    a.status = 'IN_PROGRESS'; a.started_at = datetime.utcnow(); db.commit(); db.refresh(a); return appointment_out(a)

@app.post('/api/appointments/{id}/complete', response_model=AppointmentOut)
def complete(id: UUID, db: Session = Depends(get_db)):
    a = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == str(id)))
    if not a: raise HTTPException(404, 'Appointment not found')
    if a.status != 'IN_PROGRESS': raise HTTPException(409, 'Only an in-progress appointment can be completed')
    now = datetime.utcnow(); a.status = 'COMPLETED'; a.actual_end_time = now.time().replace(second=0, microsecond=0); a.completed_at = now; a.customer.last_visit = now
    db.commit(); db.refresh(a); return appointment_out(a)

@app.post('/api/appointments/{id}/cancel', response_model=AppointmentOut)
def cancel(id: UUID, db: Session = Depends(get_db)):
    a = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == str(id)))
    if not a: raise HTTPException(404, 'Appointment not found')
    if a.status in ('COMPLETED', 'CANCELLED', 'NO_SHOW'): raise HTTPException(409, 'Appointment cannot be cancelled')
    a.status = 'CANCELLED'; db.commit(); db.refresh(a); return appointment_out(a)

@app.post('/api/appointments/{id}/no-show', response_model=AppointmentOut)
def no_show(id: UUID, db: Session = Depends(get_db)):
    a = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == str(id)))
    if not a: raise HTTPException(404, 'Appointment not found')
    if a.status not in ('PENDING', 'CONFIRMED'): raise HTTPException(409, 'Only confirmed appointments can be marked no-show')
    a.status = 'NO_SHOW'; db.commit(); db.refresh(a); return appointment_out(a)

@app.post('/api/appointments/{id}/payments', response_model=AppointmentOut)
def record_payment(id: UUID, data: PaymentIn, db: Session = Depends(get_db)):
    a = db.scalar(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.id == str(id)))
    if not a: raise HTTPException(404, 'Appointment not found')
    if data.amount > a.balance: raise HTTPException(400, 'Payment is greater than the outstanding balance')
    db.add(Payment(appointment_id=a.id, amount=data.amount, method=data.method, payment_type=data.payment_type, reference=data.reference))
    a.deposit_amount += data.amount; a.balance = max(Decimal('0.00'), a.agreed_price - a.deposit_amount); update_payment_state(a)
    db.commit(); db.refresh(a); return appointment_out(a)

@app.get('/api/appointments/{id}/payments')
def payment_history(id: UUID, db: Session = Depends(get_db)):
    return db.scalars(select(Payment).where(Payment.appointment_id == str(id)).order_by(Payment.paid_at.desc())).all()

@app.get('/api/customers', response_model=list[CustomerOut])
def customers(q: str = '', db: Session = Depends(get_db)):
    stmt = select(Customer).order_by(Customer.name)
    if q: stmt = stmt.where(or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%')))
    result = []
    for c in db.scalars(stmt).all():
        result.append(CustomerOut(id=c.id, name=c.name, phone=c.phone, email=c.email, preferred_styles=c.preferred_styles, notes=c.notes, created_at=c.created_at, last_visit=c.last_visit, appointments=len(c.appointments)))
    return result

@app.get('/api/customers/{id}')
def customer(id: UUID, db: Session = Depends(get_db)):
    c = db.get(Customer, str(id))
    if not c: raise HTTPException(404, 'Customer not found')
    history = db.scalars(select(Appointment).options(joinedload(Appointment.customer), joinedload(Appointment.style)).where(Appointment.customer_id == c.id).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())).unique().all()
    return {'customer': CustomerOut(id=c.id, name=c.name, phone=c.phone, email=c.email, preferred_styles=c.preferred_styles, notes=c.notes, created_at=c.created_at, last_visit=c.last_visit, appointments=len(history)), 'history': [appointment_out(a) for a in history]}

@app.patch('/api/customers/{id}', response_model=CustomerOut)
def edit_customer(id: UUID, data: CustomerUpdate, db: Session = Depends(get_db)):
    c = db.get(Customer, str(id))
    if not c: raise HTTPException(404, 'Customer not found')
    c.name=data.name; c.phone=data.phone; c.email=data.email; c.preferred_styles=data.preferred_styles; c.notes=data.notes
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, 'A customer with that phone number already exists')
    db.refresh(c)
    return CustomerOut(id=c.id, name=c.name, phone=c.phone, email=c.email, preferred_styles=c.preferred_styles, notes=c.notes, created_at=c.created_at, last_visit=c.last_visit, appointments=len(c.appointments))

@app.get('/api/blocked-times', response_model=list[BlockOut])
def blocks(db: Session = Depends(get_db)):
    return [BlockOut(id=b.id, date=b.blocked_date, start_time=b.start_time, end_time=b.end_time, reason=b.reason) for b in db.scalars(select(BlockedTime).order_by(BlockedTime.blocked_date, BlockedTime.start_time)).all()]

@app.post('/api/blocked-times', response_model=BlockOut, status_code=201)
def create_block(data: BlockIn, db: Session = Depends(get_db)):
    cfg = get_settings_row(db)
    if data.end_time <= data.start_time: raise HTTPException(400, 'End time must be after start time')
    if data.start_time < cfg.opening_time or data.end_time > cfg.closing_time: raise HTTPException(400, 'Blocked time must be within salon hours')
    lock_calendar_day(db, data.date)
    if blocking_conflict(db, data.date, data.start_time, data.end_time): raise HTTPException(409, 'This period is already unavailable')
    b=BlockedTime(blocked_date=data.date,start_time=data.start_time,end_time=data.end_time,reason=data.reason); db.add(b)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, 'This period is already blocked')
    db.refresh(b); return BlockOut(id=b.id,date=b.blocked_date,start_time=b.start_time,end_time=b.end_time,reason=b.reason)

@app.delete('/api/blocked-times/{id}')
def delete_block(id: UUID, db: Session = Depends(get_db)):
    b=db.get(BlockedTime,str(id))
    if not b: raise HTTPException(404,'Blocked time not found')
    db.delete(b); db.commit(); return {'ok': True}

@app.get('/api/dashboard')
def dashboard(db: Session = Depends(get_db)):
    today = date.today(); rows = db.scalars(select(Appointment).where(Appointment.appointment_date == today)).all()
    blocking = [a for a in rows if a.status in BLOCKING_STATUSES]
    completed = [a for a in rows if a.status == 'COMPLETED']
    return {
        'today': today, 'occupied': any(a.status == 'IN_PROGRESS' for a in rows),
        'current': next((a.id for a in rows if a.status == 'IN_PROGRESS'), None),
        'appointments': len([a for a in rows if a.status != 'CANCELLED']), 'completed': len(completed),
        'unpaid_deposits': sum(1 for a in blocking if a.payment_status == 'UNPAID'),
        'revenue': sum(a.deposit_amount for a in completed), 'outstanding': sum(a.balance for a in rows if a.status != 'CANCELLED'),
        'no_shows': sum(a.status == 'NO_SHOW' for a in rows), 'cancellations': sum(a.status == 'CANCELLED' for a in rows),
    }
