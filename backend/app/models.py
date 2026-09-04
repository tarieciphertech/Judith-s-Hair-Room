from datetime import date, datetime, time
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class SalonSettings(Base, TimestampMixin):
    __tablename__ = 'salon_settings'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    salon_name: Mapped[str] = mapped_column(String(160), default="Judith's Hair Room")
    phone: Mapped[str] = mapped_column(String(40), default='')
    whatsapp: Mapped[str] = mapped_column(String(40), default='')
    address: Mapped[str] = mapped_column(String(255), default='')
    opening_time: Mapped[time] = mapped_column(Time, default=time(8, 0))
    closing_time: Mapped[time] = mapped_column(Time, default=time(18, 0))
    working_days: Mapped[str] = mapped_column(String(32), default='0,1,2,3,4,5')
    booking_min_notice_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_advance_days: Mapped[int] = mapped_column(Integer, default=60)
    deposit_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('50.00'))
    currency: Mapped[str] = mapped_column(String(8), default='BWP')

class Style(Base, TimestampMixin):
    __tablename__ = 'styles'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    min_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    required_hair: Mapped[str] = mapped_column(String(160), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (CheckConstraint('min_price > 0 AND max_price >= min_price'), CheckConstraint('estimated_duration_minutes > 0'))

class Customer(Base, TimestampMixin):
    __tablename__ = 'customers'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_styles: Mapped[str] = mapped_column(Text, default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    last_visit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    appointments: Mapped[list['Appointment']] = relationship(back_populates='customer')

class Appointment(Base):
    __tablename__ = 'appointments'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey('customers.id', ondelete='RESTRICT'), index=True)
    style_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey('styles.id', ondelete='RESTRICT'), index=True)
    appointment_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    expected_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    actual_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    agreed_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='CONFIRMED', index=True, nullable=False)
    payment_status: Mapped[str] = mapped_column(String(20), default='UNPAID', index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    customer: Mapped[Customer] = relationship(back_populates='appointments')
    style: Mapped[Style] = relationship()
    payments: Mapped[list['Payment']] = relationship(back_populates='appointment', cascade='all, delete-orphan')
    __table_args__ = (
        CheckConstraint('agreed_price > 0'),
        CheckConstraint('balance >= 0'),
        CheckConstraint('deposit_amount >= 0'),
        CheckConstraint("status IN ('PENDING','CONFIRMED','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW')"),
        CheckConstraint("payment_status IN ('UNPAID','DEPOSIT_PAID','FULLY_PAID','REFUNDED')"),
        Index('ix_appointments_calendar', 'appointment_date', 'start_time', 'expected_end_time', 'status'),
    )

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    appointment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey('appointments.id', ondelete='CASCADE'), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), default='Orange Money', nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), default='DEPOSIT', nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='RECORDED', nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    appointment: Mapped[Appointment] = relationship(back_populates='payments')

class BlockedTime(Base):
    __tablename__ = 'blocked_times'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    blocked_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default='Unavailable')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (CheckConstraint('start_time < end_time'), Index('ix_blocked_times_calendar', 'blocked_date', 'start_time', 'end_time'))

class InventoryItem(Base, TimestampMixin):
    __tablename__ = 'inventory_items'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    product: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default='Other')
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    minimum_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    supplier: Mapped[str] = mapped_column(String(160), default='')
    notes: Mapped[str] = mapped_column(Text, default='')

class Expense(Base, TimestampMixin):
    __tablename__ = 'expenses'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default='Other')
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default='')

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey('customers.id', ondelete='SET NULL'), nullable=True, index=True)
    appointment_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey('appointments.id', ondelete='SET NULL'), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(20), default='IN_APP')
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='PENDING', index=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
