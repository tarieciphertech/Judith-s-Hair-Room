import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

pytestmark = pytest.mark.integration


def setup_client():
    if not os.getenv('DATABASE_URL'):
        pytest.skip('DATABASE_URL is required for PostgreSQL integration tests')
    from app.main import app
    from app.db import SessionLocal
    from app.models import Style
    with SessionLocal() as db:
        style = db.scalar(select(Style).where(Style.name == 'Singles'))
        if not style:
            pytest.skip('Seeded Singles style is missing; run alembic upgrade head first')
        return TestClient(app), style.id


def payload(style_id, phone, day, start='10:00', end='14:00', price=300, deposit=150):
    return {
        'customer_name': 'Booking API Test', 'phone': phone, 'style_id': style_id,
        'date': day.isoformat(), 'start_time': start, 'expected_end_time': end,
        'agreed_price': price, 'deposit_amount': deposit,
    }


def cleanup(phones):
    from app.db import SessionLocal
    from app.models import Appointment, Customer
    with SessionLocal() as db:
        customers = db.scalars(select(Customer).where(Customer.phone.in_(phones))).all()
        for customer in customers:
            db.execute(delete(Appointment).where(Appointment.customer_id == customer.id))
            db.delete(customer)
        db.commit()


def test_valid_booking_creates_confirmed_appointment_and_deposit():
    client, style_id = setup_client(); phone = '+26771100001'; day = date.today() + timedelta(days=12)
    try:
        response = client.post('/api/appointments', json=payload(style_id, phone, day))
        assert response.status_code == 201
        body = response.json()
        assert body['status'] == 'CONFIRMED'
        assert body['payment_status'] == 'DEPOSIT_PAID'
        assert Decimal(str(body['deposit_amount'])) == Decimal('150.00')
        assert Decimal(str(body['balance'])) == Decimal('150.00')
    finally: cleanup([phone])


def test_invalid_price_is_rejected():
    client, style_id = setup_client(); phone = '+26771100002'; day = date.today() + timedelta(days=13)
    try:
        response = client.post('/api/appointments', json=payload(style_id, phone, day, price=501, deposit=251))
        assert response.status_code == 400
        assert 'price' in response.json()['detail'].lower()
    finally: cleanup([phone])


def test_insufficient_deposit_is_rejected():
    client, style_id = setup_client(); phone = '+26771100003'; day = date.today() + timedelta(days=14)
    try:
        response = client.post('/api/appointments', json=payload(style_id, phone, day, deposit=149))
        assert response.status_code == 400
        assert 'deposit' in response.json()['detail'].lower()
    finally: cleanup([phone])


def test_unavailable_appointment_returns_409_with_suggestions():
    client, style_id = setup_client(); first = '+26771100004'; second = '+26771100005'; day = date.today() + timedelta(days=15)
    try:
        assert client.post('/api/appointments', json=payload(style_id, first, day)).status_code == 201
        response = client.post('/api/appointments', json=payload(style_id, second, day))
        assert response.status_code == 409
        detail = response.json()['detail']
        assert detail['reason'] == 'appointment_conflict'
        assert isinstance(detail['suggestions'], list)
    finally: cleanup([first, second])


def test_blocked_time_rejects_booking():
    client, style_id = setup_client(); phone = '+26771100006'; day = date.today() + timedelta(days=16)
    try:
        block = client.post('/api/blocked-times', json={'date': day.isoformat(), 'start_time': '10:00', 'end_time': '14:00', 'reason': 'Personal time'})
        assert block.status_code == 201
        response = client.post('/api/appointments', json=payload(style_id, phone, day))
        assert response.status_code == 409
        assert response.json()['detail']['reason'] == 'blocked_time'
    finally:
        from app.db import SessionLocal
        from app.models import BlockedTime
        with SessionLocal() as db:
            db.execute(delete(BlockedTime).where(BlockedTime.blocked_date == day, BlockedTime.reason == 'Personal time'))
            db.commit()
        cleanup([phone])


def test_cancelled_appointment_does_not_block_slot():
    client, style_id = setup_client(); first = '+26771100007'; second = '+26771100008'; day = date.today() + timedelta(days=17)
    try:
        created = client.post('/api/appointments', json=payload(style_id, first, day))
        assert created.status_code == 201
        appointment_id = created.json()['id']
        assert client.post(f'/api/appointments/{appointment_id}/cancel').status_code == 200
        response = client.post('/api/appointments', json=payload(style_id, second, day))
        assert response.status_code == 201
    finally: cleanup([first, second])


def test_race_condition_allows_only_one_booking():
    client, style_id = setup_client(); phones = ['+26771100009', '+26771100010']; day = date.today() + timedelta(days=18)
    body = payload(style_id, '', day)
    def book(phone):
        request = dict(body); request['phone'] = phone
        return client.post('/api/appointments', json=request)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(book, phones))
        assert sorted(response.status_code for response in responses) == [201, 409]
    finally: cleanup(phones)
