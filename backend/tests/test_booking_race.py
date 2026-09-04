import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _client_and_style():
    if not os.getenv('DATABASE_URL'):
        pytest.skip('DATABASE_URL is required for PostgreSQL integration tests')
    from app.main import app
    from app.db import SessionLocal
    from app.models import Style
    from sqlalchemy import select
    with SessionLocal() as db:
        style = db.scalar(select(Style).where(Style.name == 'Singles'))
        if not style:
            pytest.skip('Seeded Singles style is missing; run alembic upgrade head first')
        return TestClient(app), style.id


def test_two_simultaneous_requests_only_one_can_book_same_slot():
    client, style_id = _client_and_style()
    booking_day = date.today() + timedelta(days=10)
    payload = {
        'customer_name': 'Race Test', 'phone': '', 'style_id': style_id,
        'date': booking_day.isoformat(), 'start_time': '10:00', 'expected_end_time': '14:00',
        'agreed_price': 300, 'deposit_amount': 150,
    }
    def book(phone):
        body = dict(payload); body['phone'] = phone
        return client.post('/api/appointments', json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(book, ['+26770000001', '+26770000002']))
    assert sorted(response.status_code for response in responses) == [201, 409]
