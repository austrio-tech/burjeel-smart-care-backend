# Burjeel Smart Care – Database Setup Guide for Supabase

This guide will help you create the complete PostgreSQL database for the Burjeel Smart Care system using **Supabase**.  
No prior experience needed – just follow the steps one by one.

---

## 1. What you need

- A free [Supabase account](https://supabase.com/) (you can sign up with GitHub or email).
- A modern browser (Chrome, Firefox, Edge).
- (Optional) A GitHub account to link your project for later deployments.

---

## 2. Create a new Supabase project

1. Go to [app.supabase.com](https://app.supabase.com) and log in.
2. Click the **New project** button.
3. Fill in:
   - **Name**: `burjeel-smart-care-db` (or any name you like)
   - **Database password**: Choose a strong password and **save it** – you'll need it later.
   - **Region**: Pick the one closest to you (e.g., `ap-southeast-1` for Oman).
   - **Pricing Plan**: Choose `Free` (gives you 2 projects, 500 MB database, and automatic backups).
4. Click **Create new project**.

Wait 1–2 minutes until the project is ready. Then you'll see the dashboard.

---

## 3. Open the SQL Editor

- In the left sidebar, click the **SQL Editor** icon (looks like a terminal).
- Click **New query**.
- You'll now see a blank editor where you can paste and run SQL code.

---

## 4. Database schema overview

The system needs six tables:

| Table          | Description |
|----------------|-------------|
| `users`        | All system users (admin, pharmacist, IT, patients) |
| `patients`     | Extended patient profile |
| `reminders`    | Scheduled medication/appointment reminders |
| `attendance`   | Records whether a patient came to collect/attend |
| `sms_log`      | History of all SMS reminders sent |
| `chat_messages`| Live chat between patients and staff |

All foreign keys and appropriate indexes will be created automatically with the script below.

---

## 5. Complete SQL script (tables + indexes)

Copy **all** the code below, paste it into the Supabase SQL editor, and click **Run**.

```sql
-- ============================================================
-- 1. CREATE TABLES
-- ============================================================

-- 1. users
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL CHECK (role IN ('admin','pharmacist','it_staff','patient')),
    last_login    TIMESTAMPTZ,
    account_status VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (account_status IN ('active','inactive','suspended')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by    INTEGER REFERENCES users(user_id)
);

-- 2. patients
CREATE TABLE patients (
    patient_id         SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
    full_name          VARCHAR(100) NOT NULL,
    phone_number       VARCHAR(15)  NOT NULL,
    medical_record_ref VARCHAR(50),
    registered_date    DATE NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by         INTEGER REFERENCES users(user_id)
);

-- 3. reminders
CREATE TABLE reminders (
    reminder_id            SERIAL PRIMARY KEY,
    patient_id             INTEGER NOT NULL REFERENCES patients(patient_id),
    medication_name        VARCHAR(100) NOT NULL,
    scheduled_date         DATE NOT NULL,
    sent_status            VARCHAR(10) NOT NULL DEFAULT 'pending' CHECK (sent_status IN ('pending','sent','failed')),
    delivery_confirmation  VARCHAR(10) CHECK (delivery_confirmation IN ('delivered','failed','unknown')),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by             INTEGER REFERENCES users(user_id)
);

-- 4. attendance
CREATE TABLE attendance (
    attendance_id    SERIAL PRIMARY KEY,
    reminder_id      INTEGER REFERENCES reminders(reminder_id),
    patient_id       INTEGER NOT NULL REFERENCES patients(patient_id),
    appointment_date DATE NOT NULL,
    status           VARCHAR(10) NOT NULL CHECK (status IN ('came','not came')),
    marked_by        INTEGER NOT NULL REFERENCES users(user_id),
    timestamp        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by       INTEGER NOT NULL REFERENCES users(user_id)
);

-- 5. sms_log
CREATE TABLE sms_log (
    log_id          SERIAL PRIMARY KEY,
    reminder_id     INTEGER NOT NULL REFERENCES reminders(reminder_id),
    gateway_response TEXT,
    sent_timestamp  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      INTEGER REFERENCES users(user_id)
);

-- 6. chat_messages
CREATE TABLE chat_messages (
    message_id   SERIAL PRIMARY KEY,
    sender_id    INTEGER NOT NULL REFERENCES users(user_id),
    receiver_id  INTEGER REFERENCES users(user_id),
    message_text TEXT NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by   INTEGER NOT NULL REFERENCES users(user_id)
);

-- ============================================================
-- 2. CREATE INDEXES (essential for performance)
-- ============================================================

-- users
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_by ON users(created_by);

-- patients
CREATE INDEX idx_patients_full_name ON patients(full_name);
CREATE INDEX idx_patients_created_by ON patients(created_by);

-- reminders
CREATE INDEX idx_reminders_patient_id ON reminders(patient_id);
CREATE INDEX idx_reminders_scheduled_date ON reminders(scheduled_date);
CREATE INDEX idx_reminders_sent_status ON reminders(sent_status);
CREATE INDEX idx_reminders_created_by ON reminders(created_by);

-- attendance
CREATE INDEX idx_attendance_reminder_id ON attendance(reminder_id);
CREATE INDEX idx_attendance_patient_id ON attendance(patient_id);
CREATE INDEX idx_attendance_appointment_date ON attendance(appointment_date);
CREATE INDEX idx_attendance_status ON attendance(status);
CREATE INDEX idx_attendance_marked_by ON attendance(marked_by);

-- sms_log
CREATE INDEX idx_sms_log_reminder_id ON sms_log(reminder_id);
CREATE INDEX idx_sms_log_sent_timestamp ON sms_log(sent_timestamp);
CREATE INDEX idx_sms_log_created_by ON sms_log(created_by);

-- chat_messages
CREATE INDEX idx_chat_messages_sender_id ON chat_messages(sender_id);
CREATE INDEX idx_chat_messages_receiver_id ON chat_messages(receiver_id);
CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp);
```

When you run the script, you should see a success message. If you get an error, check that you selected the whole script and that the editor is empty before pasting.

---

## 6. Verify the tables

- In the left sidebar, click **Table Editor**.
- You should see all six tables listed: `users`, `patients`, `reminders`, `attendance`, `sms_log`, `chat_messages`.
- You can click on any table to see its columns and, later, any data you insert.

---
