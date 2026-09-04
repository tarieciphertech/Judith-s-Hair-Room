from datetime import date, datetime, time, timedelta
from uuid import UUID
import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Appointment, BlockedTime, Customer, Style

app=FastAPI(title="Judith's Hair Room API",version="0.2.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',')],allow_methods=['*'],allow_headers=['*'])

class StyleOut(BaseModel):
 id:str; name:str; min_price:float; max_price:float; estimated_duration_minutes:int; required_hair:str
 model_config={'from_attributes':True}
class Booking(BaseModel):
 customer_name:str=Field(min_length=2); phone:str=Field(min_length=5); style_id:UUID; date:date; start_time:time; expected_end_time:time; agreed_price:float=Field(gt=0); deposit_amount:float=Field(gt=0)
class AppointmentOut(BaseModel):
 id:str; customer_name:str; phone:str; style_id:str; style_name:str; date:date; start_time:time; expected_end_time:time; agreed_price:float; deposit_amount:float; balance:float; status:str; payment_status:str

SEEDS=[('Wash',60,70,60,"Customer's hair"),('Condro',140,200,180,'Customer buys required braid/hair'),('Carrot',180,250,210,'Customer buys required braid/hair'),('Singles',250,500,240,'Customer buys required braid/hair'),('Udo',50,50,60,"Customer's hair"),('Brazilian',100,100,120,'Customer buys required braid/hair'),('French',15,25,45,'Customer buys required braid/hair')]
@app.on_event('startup')
def startup():
 Base.metadata.create_all(bind=engine)
 with Session(engine) as db:
  if not db.scalar(select(Style).limit(1)):
   db.add_all([Style(name=n,min_price=lo,max_price=hi,estimated_duration_minutes=d,required_hair=h) for n,lo,hi,d,h in SEEDS]); db.commit()

def dto(db,a):
 c=db.get(Customer,a.customer_id); s=db.get(Style,a.style_id)
 return AppointmentOut(id=a.id,customer_name=c.name,phone=c.phone,style_id=a.style_id,style_name=s.name,date=a.appointment_date,start_time=a.start_time,expected_end_time=a.expected_end_time,agreed_price=a.agreed_price,deposit_amount=a.deposit_amount,balance=a.balance,status=a.status,payment_status=a.payment_status)

def conflicts(db,day,start,end):
 ap=db.scalar(select(Appointment.id).where(Appointment.appointment_date==day,Appointment.status.not_in(['CANCELLED','NO_SHOW']),Appointment.start_time<end,Appointment.expected_end_time>start).limit(1))
 if ap:return 'appointment_conflict'
 block=db.scalar(select(BlockedTime.id).where(BlockedTime.blocked_date==day,BlockedTime.start_time<end,BlockedTime.end_time>start).limit(1))
 return 'blocked_time' if block else None

def suggestions(db,day,start,end):
 duration=datetime.combine(day,end)-datetime.combine(day,start); cursor=datetime.combine(day,time(8)); close=datetime.combine(day,time(18)); out=[]
 while cursor+duration<=close and len(out)<3:
  s=cursor.time(); e=(cursor+duration).time()
  if not conflicts(db,day,s,e): out.append({'start_time':s.strftime('%H:%M'),'end_time':e.strftime('%H:%M')})
  cursor+=timedelta(minutes=30)
 return out

@app.get('/health')
def health():return {'status':'ok','service':'judiths-hair-room'}
@app.get('/api/styles',response_model=list[StyleOut])
def styles(db:Session=Depends(get_db)):return db.scalars(select(Style).where(Style.active==True).order_by(Style.name)).all()
@app.get('/api/appointments',response_model=list[AppointmentOut])
def appointments(db:Session=Depends(get_db)):return [dto(db,a) for a in db.scalars(select(Appointment).order_by(Appointment.appointment_date,Appointment.start_time)).all()]
@app.get('/api/availability')
def availability(date:date,start_time:time,end_time:time,db:Session=Depends(get_db)):
 if end_time<=start_time:raise HTTPException(400,'End time must be after start time')
 reason=conflicts(db,date,start_time,end_time)
 return {'available':not reason,'reason':reason,'suggestions':suggestions(db,date,start_time,end_time) if reason else []}
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
 a=Appointment(customer_id=c.id,style_id=style.id,appointment_date=data.date,start_time=data.start_time,expected_end_time=data.expected_end_time,agreed_price=data.agreed_price,deposit_amount=data.deposit_amount,balance=data.agreed_price-data.deposit_amount,status='CONFIRMED',payment_status='DEPOSIT_PAID')
 db.add(a);db.commit();db.refresh(a);return dto(db,a)
def mutate(id:UUID,new_status:str,db:Session):
 a=db.get(Appointment,str(id));
 if not a:raise HTTPException(404,'Appointment not found')
 if new_status=='IN_PROGRESS' and a.status not in ('CONFIRMED','PENDING'):raise HTTPException(409,'Appointment cannot be started')
 a.status=new_status
 if new_status=='COMPLETED':a.actual_end_time=datetime.now().time().replace(second=0,microsecond=0);a.expected_end_time=a.actual_end_time
 db.commit();db.refresh(a);return dto(db,a)
@app.post('/api/appointments/{id}/start',response_model=AppointmentOut)
def start(id:UUID,db:Session=Depends(get_db)):return mutate(id,'IN_PROGRESS',db)
@app.post('/api/appointments/{id}/complete',response_model=AppointmentOut)
def complete(id:UUID,db:Session=Depends(get_db)):return mutate(id,'COMPLETED',db)
@app.post('/api/appointments/{id}/cancel',response_model=AppointmentOut)
def cancel(id:UUID,db:Session=Depends(get_db)):return mutate(id,'CANCELLED',db)
@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db)):
 d=date.today(); rows=db.scalars(select(Appointment).where(Appointment.appointment_date==d)).all()
 return {'today':d,'occupied':any(a.status=='IN_PROGRESS' for a in rows),'appointments':len([a for a in rows if a.status!='CANCELLED']),'completed':sum(a.status=='COMPLETED' for a in rows),'unpaid_deposits':sum(a.payment_status=='UNPAID' for a in rows),'revenue':sum(a.deposit_amount for a in rows if a.status=='COMPLETED')}
