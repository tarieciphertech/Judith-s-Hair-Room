from datetime import date, datetime, time, timedelta
from enum import Enum
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Judith's Hair Room API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Status(str, Enum):
    PENDING="PENDING"; CONFIRMED="CONFIRMED"; IN_PROGRESS="IN_PROGRESS"; COMPLETED="COMPLETED"; CANCELLED="CANCELLED"; NO_SHOW="NO_SHOW"

class Style(BaseModel):
    id: UUID
    name: str
    min_price: int
    max_price: int
    estimated_duration_minutes: int
    required_hair: str

STYLES = [
    Style(id=uuid4(), name="Wash", min_price=60, max_price=70, estimated_duration_minutes=60, required_hair="Customer's hair"),
    Style(id=uuid4(), name="Condro", min_price=140, max_price=200, estimated_duration_minutes=180, required_hair="Customer buys required braid/hair"),
    Style(id=uuid4(), name="Carrot", min_price=180, max_price=250, estimated_duration_minutes=210, required_hair="Customer buys required braid/hair"),
    Style(id=uuid4(), name="Singles", min_price=250, max_price=500, estimated_duration_minutes=240, required_hair="Customer buys required braid/hair"),
    Style(id=uuid4(), name="Udo", min_price=50, max_price=50, estimated_duration_minutes=60, required_hair="Customer's hair"),
    Style(id=uuid4(), name="Brazilian", min_price=100, max_price=100, estimated_duration_minutes=120, required_hair="Customer buys required braid/hair"),
    Style(id=uuid4(), name="French", min_price=15, max_price=25, estimated_duration_minutes=45, required_hair="Customer buys required braid/hair"),
]

class Appointment(BaseModel):
    id: UUID
    customer_name: str
    phone: str
    style_id: UUID
    style_name: str
    date: date
    start_time: time
    expected_end_time: time
    agreed_price: float
    deposit_amount: float
    balance: float
    status: Status = Status.CONFIRMED
    payment_status: str = "DEPOSIT_PAID"

APPOINTMENTS: list[Appointment] = []
BLOCKED: list[tuple[date,time,time]] = []

class Booking(BaseModel):
    customer_name: str = Field(min_length=2)
    phone: str = Field(min_length=5)
    style_id: UUID
    date: date
    start_time: time
    expected_end_time: time
    agreed_price: float = Field(gt=0)
    deposit_amount: float = Field(gt=0)

@app.get("/health")
def health(): return {"status":"ok","service":"judiths-hair-room"}

@app.get("/api/styles", response_model=list[Style])
def styles(): return STYLES

@app.get("/api/appointments", response_model=list[Appointment])
def appointments(): return APPOINTMENTS

@app.get("/api/availability")
def availability(date: date, start_time: time, end_time: time):
    if end_time <= start_time: raise HTTPException(400, "End time must be after start time")
    for a in APPOINTMENTS:
        if a.date == date and a.status != Status.CANCELLED and start_time < a.expected_end_time and end_time > a.start_time:
            return {"available":False,"reason":"appointment_conflict","suggestions":suggestions(date,start_time,end_time)}
    for d,s,e in BLOCKED:
        if d == date and start_time < e and end_time > s:
            return {"available":False,"reason":"blocked_time","suggestions":suggestions(date,start_time,end_time)}
    return {"available":True,"suggestions":[]}

def suggestions(day:date, requested_start:time, requested_end:time):
    duration = datetime.combine(day, requested_end) - datetime.combine(day, requested_start)
    out=[]; cursor=datetime.combine(day, max(requested_start,time(8,0)))
    close=datetime.combine(day,time(18,0))
    while cursor + duration <= close and len(out)<3:
        s=cursor.time(); e=(cursor+duration).time()
        if availability(day,s,e)["available"]: out.append({"start_time":s.isoformat(timespec="minutes"),"end_time":e.isoformat(timespec="minutes")})
        cursor += timedelta(minutes=30)
    return out

@app.post("/api/appointments", response_model=Appointment, status_code=201)
def create_booking(data: Booking):
    if data.expected_end_time <= data.start_time: raise HTTPException(400,"End time must be after start time")
    conflict=availability(data.date,data.start_time,data.expected_end_time)
    if not conflict["available"]: raise HTTPException(409, detail={"message":"That slot is no longer available.","reason":conflict["reason"],"suggestions":conflict["suggestions"]})
    style=next((s for s in STYLES if s.id==data.style_id),None)
    if not style: raise HTTPException(404,"Style not found")
    if data.deposit_amount < data.agreed_price*0.5: raise HTTPException(400,"Deposit must be at least 50% of agreed price")
    a=Appointment(id=uuid4(),customer_name=data.customer_name,phone=data.phone,style_id=data.style_id,style_name=style.name,date=data.date,start_time=data.start_time,expected_end_time=data.expected_end_time,agreed_price=data.agreed_price,deposit_amount=data.deposit_amount,balance=data.agreed_price-data.deposit_amount)
    APPOINTMENTS.append(a); return a

@app.post("/api/appointments/{appointment_id}/start", response_model=Appointment)
def start(appointment_id:UUID):
    a=next((x for x in APPOINTMENTS if x.id==appointment_id),None)
    if not a: raise HTTPException(404,"Appointment not found")
    if a.status not in (Status.CONFIRMED,Status.PENDING): raise HTTPException(409,"Appointment cannot be started")
    a.status=Status.IN_PROGRESS; return a

@app.post("/api/appointments/{appointment_id}/complete", response_model=Appointment)
def complete(appointment_id:UUID):
    a=next((x for x in APPOINTMENTS if x.id==appointment_id),None)
    if not a: raise HTTPException(404,"Appointment not found")
    a.status=Status.COMPLETED; a.expected_end_time=datetime.now().time().replace(second=0,microsecond=0); return a

@app.post("/api/appointments/{appointment_id}/cancel", response_model=Appointment)
def cancel(appointment_id:UUID):
    a=next((x for x in APPOINTMENTS if x.id==appointment_id),None)
    if not a: raise HTTPException(404,"Appointment not found")
    a.status=Status.CANCELLED; return a

@app.get("/api/dashboard")
def dashboard():
    today=date.today(); todays=[a for a in APPOINTMENTS if a.date==today and a.status!=Status.CANCELLED]
    return {"today":today,"occupied":any(a.status==Status.IN_PROGRESS for a in todays),"appointments":len(todays),"completed":sum(a.status==Status.COMPLETED for a in todays),"unpaid_deposits":sum(a.payment_status=="UNPAID" for a in todays),"revenue":sum(a.deposit_amount for a in todays if a.status==Status.COMPLETED)}
