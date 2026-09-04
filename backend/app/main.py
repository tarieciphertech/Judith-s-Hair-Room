from datetime import date, datetime, time, timedelta
from uuid import UUID
import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, text, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Appointment, BlockedTime, Customer, Payment, Style

app=FastAPI(title="Judith's Hair Room API",version="0.6.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',')],allow_methods=['*'],allow_headers=['*'])

class StyleOut(BaseModel):
 id:str; name:str; min_price:float; max_price:float; estimated_duration_minutes:int; required_hair:str
 model_config={'from_attributes':True}
class Booking(BaseModel):
 customer_name:str=Field(min_length=2); phone:str=Field(min_length=5); style_id:UUID; date:date; start_time:time; expected_end_time:time; agreed_price:float=Field(gt=0); deposit_amount:float=Field(gt=0)
class AppointmentUpdate(BaseModel):
 customer_name:str=Field(min_length=2); phone:str=Field(min_length=5); style_id:UUID; date:date; start_time:time; expected_end_time:time; agreed_price:float=Field(gt=0)
class PaymentIn(BaseModel):
 amount:float=Field(gt=0); method:str='Orange Money'; payment_type:str='BALANCE'; reference:str|None=None
class CustomerUpdate(BaseModel):
 name:str=Field(min_length=2); phone:str=Field(min_length=5); email:str|None=None; preferred_styles:str=''; notes:str=''
class BlockIn(BaseModel):
 date:date; start_time:time; end_time:time; reason:str=Field(min_length=2,max_length=255)
class AppointmentOut(BaseModel):
 id:str; customer_id:str; customer_name:str; phone:str; style_id:str; style_name:str; date:date; start_time:time; expected_end_time:time; agreed_price:float; deposit_amount:float; balance:float; status:str; payment_status:str
class CustomerOut(BaseModel):
 id:str; name:str; phone:str; email:str|None; preferred_styles:str; notes:str; created_at:datetime; last_visit:datetime|None; appointments:int
class BlockOut(BaseModel):
 id:str; date:date; start_time:time; end_time:time; reason:str

SEEDS=[('Wash',60,70,60,"Customer's hair"),('Condro',140,200,180,'Customer buys required braid/hair'),('Carrot',180,250,210,'Customer buys required braid/hair'),('Singles',250,500,240,'Customer buys required braid/hair'),('Udo',50,50,60,"Customer's hair"),('Brazilian',100,100,120,'Customer buys required braid/hair'),('French',15,25,45,'Customer buys required braid/hair')]

@app.on_event('startup')
def startup():
 Base.metadata.create_all(bind=engine)
 if engine.dialect.name=='postgresql':
  with engine.begin() as conn:
   conn.execute(text('CREATE EXTENSION IF NOT EXISTS btree_gist'))
   conn.execute(text("""DO $$ BEGIN ALTER TABLE appointments ADD CONSTRAINT appointments_no_overlap EXCLUDE USING gist (tsrange(appointment_date + start_time, appointment_date + expected_end_time, '[)') WITH &&) WHERE (status NOT IN ('CANCELLED','NO_SHOW')); EXCEPTION WHEN duplicate_object THEN NULL; END $$;"""))
 with Session(engine) as db:
  if not db.scalar(select(Style).limit(1)):
   db.add_all([Style(name=n,min_price=lo,max_price=hi,estimated_duration_minutes=d,required_hair=h) for n,lo,hi,d,h in SEEDS]); db.commit()

def dto(db,a):
 c=db.get(Customer,a.customer_id); s=db.get(Style,a.style_id)
 return AppointmentOut(id=a.id,customer_id=c.id,customer_name=c.name,phone=c.phone,style_id=a.style_id,style_name=s.name,date=a.appointment_date,start_time=a.start_time,expected_end_time=a.expected_end_time,agreed_price=a.agreed_price,deposit_amount=a.deposit_amount,balance=a.balance,status=a.status,payment_status=a.payment_status)

def conflicts(db,day,start,end,exclude_id=None):
 q=select(Appointment.id).where(Appointment.appointment_date==day,Appointment.status.not_in(['CANCELLED','NO_SHOW']),Appointment.start_time<end,Appointment.expected_end_time>start)
 if exclude_id:q=q.where(Appointment.id!=str(exclude_id))
 if db.scalar(q.limit(1)):return 'appointment_conflict'
 if db.scalar(select(BlockedTime.id).where(BlockedTime.blocked_date==day,BlockedTime.start_time<end,BlockedTime.end_time>start).limit(1)):return 'blocked_time'
 return None

def suggestions(db,day,start,end):
 duration=datetime.combine(day,end)-datetime.combine(day,start); cursor=datetime.combine(day,time(8)); close=datetime.combine(day,time(18)); out=[]
 while cursor+duration<=close and len(out)<4:
  s=cursor.time();e=(cursor+duration).time()
  if not conflicts(db,day,s,e):out.append({'start_time':s.strftime('%H:%M'),'end_time':e.strftime('%H:%M')})
  cursor+=timedelta(minutes=30)
 return out

def update_payment_state(a):
 if a.deposit_amount<=0:a.payment_status='UNPAID'
 elif a.balance<=0:a.payment_status='FULLY_PAID'
 else:a.payment_status='DEPOSIT_PAID'

@app.get('/health')
def health():return {'status':'ok','service':'judiths-hair-room'}
@app.get('/api/styles',response_model=list[StyleOut])
def styles(db:Session=Depends(get_db)):return db.scalars(select(Style).where(Style.active==True).order_by(Style.name)).all()
@app.get('/api/appointments',response_model=list[AppointmentOut])
def appointments(db:Session=Depends(get_db)):return [dto(db,a) for a in db.scalars(select(Appointment).order_by(Appointment.appointment_date,Appointment.start_time)).all()]
@app.get('/api/availability')
def availability(date:date,start_time:time,end_time:time,db:Session=Depends(get_db)):
 if end_time<=start_time:raise HTTPException(400,'End time must be after start time')
 reason=conflicts(db,date,start_time,end_time);return {'available':not reason,'reason':reason,'suggestions':suggestions(db,date,start_time,end_time) if reason else []}
@app.post('/api/appointments',response_model=AppointmentOut,status_code=201)
def create(data:Booking,db:Session=Depends(get_db)):
 if data.expected_end_time<=data.start_time:raise HTTPException(400,'End time must be after start time')
 style=db.get(Style,str(data.style_id))
 if not style:raise HTTPException(404,'Style not found')
 if data.deposit_amount<data.agreed_price*.5:raise HTTPException(400,'Deposit must be at least 50% of agreed price')
 if conflicts(db,data.date,data.start_time,data.expected_end_time):raise HTTPException(409,detail={'message':'That slot is no longer available.','suggestions':suggestions(db,data.date,data.start_time,data.expected_end_time)})
 c=db.scalar(select(Customer).where(Customer.phone==data.phone))
 if not c:c=Customer(name=data.customer_name,phone=data.phone);db.add(c);db.flush()
 else:c.name=data.customer_name
 a=Appointment(customer_id=c.id,style_id=style.id,appointment_date=data.date,start_time=data.start_time,expected_end_time=data.expected_end_time,agreed_price=data.agreed_price,deposit_amount=data.deposit_amount,balance=data.agreed_price-data.deposit_amount,status='CONFIRMED',payment_status='DEPOSIT_PAID');db.add(a)
 db.flush();db.add(Payment(appointment_id=a.id,amount=data.deposit_amount,method='Orange Money',payment_type='DEPOSIT'))
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,detail={'message':'That slot was booked by someone else.','suggestions':suggestions(db,data.date,data.start_time,data.expected_end_time)})
 db.refresh(a);return dto(db,a)
@app.patch('/api/appointments/{id}',response_model=AppointmentOut)
def edit(id:UUID,data:AppointmentUpdate,db:Session=Depends(get_db)):
 a=db.get(Appointment,str(id))
 if not a:raise HTTPException(404,'Appointment not found')
 if a.status in ('COMPLETED','CANCELLED','NO_SHOW'):raise HTTPException(409,'This appointment can no longer be edited')
 if data.expected_end_time<=data.start_time:raise HTTPException(400,'End time must be after start time')
 if conflicts(db,data.date,data.start_time,data.expected_end_time,id):raise HTTPException(409,detail={'message':'That new time is unavailable.','suggestions':suggestions(db,data.date,data.start_time,data.expected_end_time)})
 c=db.get(Customer,a.customer_id);c.name=data.customer_name;c.phone=data.phone
 a.style_id=str(data.style_id);a.appointment_date=data.date;a.start_time=data.start_time;a.expected_end_time=data.expected_end_time;a.agreed_price=data.agreed_price;a.balance=max(0,data.agreed_price-a.deposit_amount);update_payment_state(a)
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,'That time is already occupied')
 db.refresh(a);return dto(db,a)
def mutate(id:UUID,new_status:str,db:Session):
 a=db.get(Appointment,str(id))
 if not a:raise HTTPException(404,'Appointment not found')
 if new_status=='IN_PROGRESS' and a.status not in ('CONFIRMED','PENDING'):raise HTTPException(409,'Appointment cannot be started')
 if new_status=='NO_SHOW' and a.status not in ('CONFIRMED','PENDING'):raise HTTPException(409,'Only confirmed appointments can be marked no-show')
 a.status=new_status
 if new_status=='COMPLETED':
  a.actual_end_time=datetime.now().time().replace(second=0,microsecond=0);a.expected_end_time=a.actual_end_time;db.get(Customer,a.customer_id).last_visit=datetime.utcnow()
 db.commit();db.refresh(a);return dto(db,a)
@app.post('/api/appointments/{id}/start',response_model=AppointmentOut)
def start(id:UUID,db:Session=Depends(get_db)):return mutate(id,'IN_PROGRESS',db)
@app.post('/api/appointments/{id}/complete',response_model=AppointmentOut)
def complete(id:UUID,db:Session=Depends(get_db)):return mutate(id,'COMPLETED',db)
@app.post('/api/appointments/{id}/cancel',response_model=AppointmentOut)
def cancel(id:UUID,db:Session=Depends(get_db)):return mutate(id,'CANCELLED',db)
@app.post('/api/appointments/{id}/no-show',response_model=AppointmentOut)
def no_show(id:UUID,db:Session=Depends(get_db)):return mutate(id,'NO_SHOW',db)
@app.post('/api/appointments/{id}/payments',response_model=AppointmentOut)
def payment(id:UUID,data:PaymentIn,db:Session=Depends(get_db)):
 a=db.get(Appointment,str(id))
 if not a:raise HTTPException(404,'Appointment not found')
 if data.amount>a.balance:raise HTTPException(400,'Payment is greater than the outstanding balance')
 db.add(Payment(appointment_id=a.id,amount=data.amount,method=data.method,payment_type=data.payment_type,reference=data.reference))
 a.deposit_amount += data.amount;a.balance=max(0,a.agreed_price-a.deposit_amount);update_payment_state(a);db.commit();db.refresh(a);return dto(db,a)
@app.get('/api/appointments/{id}/payments')
def payment_history(id:UUID,db:Session=Depends(get_db)):
 return db.scalars(select(Payment).where(Payment.appointment_id==str(id)).order_by(Payment.paid_at.desc())).all()
@app.get('/api/customers',response_model=list[CustomerOut])
def customers(q:str='',db:Session=Depends(get_db)):
 stmt=select(Customer).order_by(Customer.name)
 if q:stmt=stmt.where(or_(Customer.name.ilike(f'%{q}%'),Customer.phone.ilike(f'%{q}%')))
 out=[]
 for c in db.scalars(stmt).all():
  count=len(db.scalars(select(Appointment.id).where(Appointment.customer_id==c.id)).all())
  out.append(CustomerOut(id=c.id,name=c.name,phone=c.phone,email=c.email,preferred_styles=c.preferred_styles,notes=c.notes,created_at=c.created_at,last_visit=c.last_visit,appointments=count))
 return out
@app.get('/api/customers/{id}')
def customer(id:UUID,db:Session=Depends(get_db)):
 c=db.get(Customer,str(id))
 if not c:raise HTTPException(404,'Customer not found')
 history=[dto(db,a) for a in db.scalars(select(Appointment).where(Appointment.customer_id==c.id).order_by(Appointment.appointment_date.desc(),Appointment.start_time.desc())).all()]
 return {'customer':CustomerOut(id=c.id,name=c.name,phone=c.phone,email=c.email,preferred_styles=c.preferred_styles,notes=c.notes,created_at=c.created_at,last_visit=c.last_visit,appointments=len(history)),'history':history}
@app.patch('/api/customers/{id}',response_model=CustomerOut)
def edit_customer(id:UUID,data:CustomerUpdate,db:Session=Depends(get_db)):
 c=db.get(Customer,str(id))
 if not c:raise HTTPException(404,'Customer not found')
 c.name=data.name;c.phone=data.phone;c.email=data.email;c.preferred_styles=data.preferred_styles;c.notes=data.notes;db.commit();db.refresh(c)
 count=len(db.scalars(select(Appointment.id).where(Appointment.customer_id==c.id)).all())
 return CustomerOut(id=c.id,name=c.name,phone=c.phone,email=c.email,preferred_styles=c.preferred_styles,notes=c.notes,created_at=c.created_at,last_visit=c.last_visit,appointments=count)
@app.get('/api/blocked-times',response_model=list[BlockOut])
def blocks(db:Session=Depends(get_db)):
 return [BlockOut(id=b.id,date=b.blocked_date,start_time=b.start_time,end_time=b.end_time,reason=b.reason) for b in db.scalars(select(BlockedTime).order_by(BlockedTime.blocked_date,BlockedTime.start_time)).all()]
@app.post('/api/blocked-times',response_model=BlockOut,status_code=201)
def create_block(data:BlockIn,db:Session=Depends(get_db)):
 if data.end_time<=data.start_time:raise HTTPException(400,'End time must be after start time')
 if conflicts(db,data.date,data.start_time,data.end_time):raise HTTPException(409,'This period is already unavailable')
 b=BlockedTime(blocked_date=data.date,start_time=data.start_time,end_time=data.end_time,reason=data.reason);db.add(b);db.commit();db.refresh(b);return BlockOut(id=b.id,date=b.blocked_date,start_time=b.start_time,end_time=b.end_time,reason=b.reason)
@app.delete('/api/blocked-times/{id}')
def delete_block(id:UUID,db:Session=Depends(get_db)):
 b=db.get(BlockedTime,str(id))
 if not b:raise HTTPException(404,'Blocked time not found')
 db.delete(b);db.commit();return {'ok':True}
@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db)):
 d=date.today();rows=db.scalars(select(Appointment).where(Appointment.appointment_date==d)).all();active=[a for a in rows if a.status!='CANCELLED'];completed=[a for a in active if a.status=='COMPLETED']
 return {'today':d,'occupied':any(a.status=='IN_PROGRESS' for a in active),'appointments':len(active),'completed':len(completed),'unpaid_deposits':sum(1 for a in active if a.balance>0),'revenue':sum(a.deposit_amount for a in completed),'outstanding':sum(a.balance for a in active),'no_shows':sum(a.status=='NO_SHOW' for a in rows)}
