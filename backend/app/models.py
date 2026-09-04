from datetime import date, datetime, time
from uuid import uuid4
from sqlalchemy import Date, DateTime, Float, Integer, String, Time, Boolean, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Style(Base):
    __tablename__='styles'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda:str(uuid4()))
    name: Mapped[str] = mapped_column(String(80), unique=True)
    min_price: Mapped[float] = mapped_column(Float)
    max_price: Mapped[float] = mapped_column(Float)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer)
    required_hair: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Customer(Base):
    __tablename__='customers'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda:str(uuid4()))
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40), index=True)
    email: Mapped[str|None] = mapped_column(String(255), nullable=True)
    preferred_styles: Mapped[str] = mapped_column(String(500), default='')
    notes: Mapped[str] = mapped_column(String(2000), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_visit: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

class Appointment(Base):
    __tablename__='appointments'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda:str(uuid4()))
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    style_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    appointment_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    expected_end_time: Mapped[time] = mapped_column(Time)
    actual_end_time: Mapped[time|None] = mapped_column(Time, nullable=True)
    agreed_price: Mapped[float] = mapped_column(Float)
    deposit_amount: Mapped[float] = mapped_column(Float)
    balance: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default='CONFIRMED', index=True)
    payment_status: Mapped[str] = mapped_column(String(20), default='DEPOSIT_PAID')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(CheckConstraint('agreed_price > 0'),Index('ix_appointments_slot','appointment_date','start_time','expected_end_time'))

class Payment(Base):
    __tablename__='payments'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda:str(uuid4()))
    appointment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(40), default='Orange Money')
    payment_type: Mapped[str] = mapped_column(String(20), default='DEPOSIT')
    reference: Mapped[str|None] = mapped_column(String(120), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class BlockedTime(Base):
    __tablename__='blocked_times'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda:str(uuid4()))
    blocked_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    reason: Mapped[str] = mapped_column(String(255), default='Unavailable')
