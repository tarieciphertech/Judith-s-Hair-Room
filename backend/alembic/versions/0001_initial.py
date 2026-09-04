"""Initial production schema for Judith's Hair Room."""
from alembic import op

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    op.execute('''
    CREATE TABLE salon_settings (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), salon_name varchar(160) NOT NULL,
      phone varchar(40) NOT NULL DEFAULT '', whatsapp varchar(40) NOT NULL DEFAULT '', address varchar(255) NOT NULL DEFAULT '',
      opening_time time NOT NULL DEFAULT '08:00', closing_time time NOT NULL DEFAULT '18:00', working_days varchar(32) NOT NULL DEFAULT '0,1,2,3,4,5,6',
      booking_min_notice_minutes integer NOT NULL DEFAULT 60, max_advance_days integer NOT NULL DEFAULT 60,
      deposit_percentage numeric(5,2) NOT NULL DEFAULT 50, currency varchar(8) NOT NULL DEFAULT 'BWP',
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE styles (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name varchar(80) NOT NULL UNIQUE, min_price numeric(10,2) NOT NULL,
      max_price numeric(10,2) NOT NULL, estimated_duration_minutes integer NOT NULL, required_hair varchar(160) NOT NULL DEFAULT '',
      description text NOT NULL DEFAULT '', active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
      CHECK (min_price > 0 AND max_price >= min_price), CHECK (estimated_duration_minutes > 0)
    );
    CREATE TABLE customers (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name varchar(160) NOT NULL, phone varchar(40) NOT NULL UNIQUE,
      email varchar(255), preferred_styles text NOT NULL DEFAULT '', notes text NOT NULL DEFAULT '', last_visit timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE appointments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
      style_id uuid NOT NULL REFERENCES styles(id) ON DELETE RESTRICT, appointment_date date NOT NULL, start_time time NOT NULL,
      expected_end_time time NOT NULL, actual_end_time time, agreed_price numeric(10,2) NOT NULL, deposit_amount numeric(10,2) NOT NULL DEFAULT 0,
      balance numeric(10,2) NOT NULL, status varchar(20) NOT NULL DEFAULT 'CONFIRMED', payment_status varchar(20) NOT NULL DEFAULT 'UNPAID',
      started_at timestamptz, completed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
      CHECK (start_time < expected_end_time), CHECK (agreed_price > 0), CHECK (deposit_amount >= 0), CHECK (balance >= 0),
      CHECK (status IN ('PENDING','CONFIRMED','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW')),
      CHECK (payment_status IN ('UNPAID','DEPOSIT_PAID','FULLY_PAID','REFUNDED')),
      EXCLUDE USING gist (tsrange(appointment_date + start_time, appointment_date + expected_end_time, '[)') WITH &&)
        WHERE (status IN ('PENDING','CONFIRMED','IN_PROGRESS'))
    );
    CREATE TABLE payments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), appointment_id uuid NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
      amount numeric(10,2) NOT NULL, method varchar(40) NOT NULL DEFAULT 'Orange Money', payment_type varchar(20) NOT NULL DEFAULT 'DEPOSIT',
      reference varchar(120), status varchar(20) NOT NULL DEFAULT 'RECORDED', paid_at timestamptz NOT NULL DEFAULT now(), created_at timestamptz NOT NULL DEFAULT now(), CHECK (amount > 0)
    );
    CREATE TABLE blocked_times (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), blocked_date date NOT NULL, start_time time NOT NULL, end_time time NOT NULL,
      reason varchar(255) NOT NULL DEFAULT 'Unavailable', created_at timestamptz NOT NULL DEFAULT now(), CHECK (start_time < end_time),
      EXCLUDE USING gist (tsrange(blocked_date + start_time, blocked_date + end_time, '[)') WITH &&)
    );
    CREATE TABLE inventory_items (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), product varchar(160) NOT NULL, category varchar(80) NOT NULL DEFAULT 'Other',
      quantity numeric(10,2) NOT NULL DEFAULT 0, minimum_quantity numeric(10,2) NOT NULL DEFAULT 0, cost_price numeric(10,2) NOT NULL DEFAULT 0,
      selling_price numeric(10,2) NOT NULL DEFAULT 0, supplier varchar(160) NOT NULL DEFAULT '', notes text NOT NULL DEFAULT '',
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE expenses (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), description varchar(255) NOT NULL, amount numeric(10,2) NOT NULL,
      category varchar(80) NOT NULL DEFAULT 'Other', expense_date date NOT NULL, notes text NOT NULL DEFAULT '',
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), CHECK (amount > 0)
    );
    CREATE TABLE notifications (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), customer_id uuid REFERENCES customers(id) ON DELETE SET NULL,
      appointment_id uuid REFERENCES appointments(id) ON DELETE SET NULL, channel varchar(20) NOT NULL DEFAULT 'IN_APP',
      notification_type varchar(40) NOT NULL, recipient varchar(255) NOT NULL, message text NOT NULL, status varchar(20) NOT NULL DEFAULT 'PENDING',
      scheduled_for timestamptz, sent_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
    );
    ''')
    op.execute("CREATE INDEX ix_appointments_date_start ON appointments(appointment_date, start_time)")
    op.execute("CREATE INDEX ix_appointments_customer ON appointments(customer_id)")
    op.execute("CREATE INDEX ix_appointments_payment_status ON appointments(payment_status)")
    op.execute("CREATE INDEX ix_payments_appointment ON payments(appointment_id)")
    op.execute("CREATE INDEX ix_blocked_times_date ON blocked_times(blocked_date, start_time)")
    op.execute("CREATE INDEX ix_notifications_status ON notifications(status)")
    op.execute("INSERT INTO salon_settings (salon_name) VALUES ('Judith''s Hair Room')")
    for name, lo, hi, duration, hair in [
        ('Wash',60,70,60,"Customer's hair"), ('Condro',140,200,180,'Customer buys required braid/hair'),
        ('Carrot',180,250,210,'Customer buys required braid/hair'), ('Singles',250,500,240,'Customer buys required braid/hair'),
        ('Udo',50,50,60,"Customer's hair"), ('Brazilian',100,100,120,'Customer buys required braid/hair'),
        ('French',15,25,45,'Customer buys required braid/hair')]:
        safe_name = name.replace("'", "''"); safe_hair = hair.replace("'", "''")
        op.execute(f"INSERT INTO styles (name,min_price,max_price,estimated_duration_minutes,required_hair) VALUES ('{safe_name}',{lo},{hi},{duration},'{safe_hair}')")


def downgrade():
    for table in ['notifications','expenses','inventory_items','blocked_times','payments','appointments','customers','styles','salon_settings']:
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
