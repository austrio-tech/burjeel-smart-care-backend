# Burjeel Smart Care – Backend (FastAPI)

High‑performance REST API and WebSocket backend for the **Burjeel Smart Care** intelligent patient management system. Built with **FastAPI**, backed by a **Supabase PostgreSQL** database, and deployed on **Render**.

---

## 📋 Overview

This backend handles:
- **Authentication & Authorisation** (JWT, role‑based access)
- **Patient Management** – register, update, list, search
- **Reminder Scheduling & Automated SMS Delivery** (via Twilio / gateway)
- **Attendance Tracking** – mark “Came” / “Not came”
- **Live Chat** – WebSocket endpoint for real‑time messaging
- **Reports & Analytics** – aggregated data for dashboards

---

## 🧠 Development Methodology

Aligned with the overall project’s **DSDM (Agile)** approach:
- **Iterative increments** – features delivered in timeboxed cycles
- **Continuous stakeholder feedback** (hospital staff)
- **MoSCoW prioritisation** – must‑have vs. could‑have features
- **Active prototype refinement** – schema and API evolve with each iteration

---

## 🛠 Tech Stack

| Component         | Technology                    |
|-------------------|-------------------------------|
| Framework         | FastAPI (Python 3.11+)        |
| ASGI Server       | Uvicorn                       |
| Database          | Supabase (PostgreSQL)         |
| ORM               | SQLAlchemy 2.0 (async)       |
| Schema Validation | Pydantic v2                   |
| Authentication    | JWT (PyJWT, python‑jose)      |
| Real‑time Chat    | WebSockets (native FastAPI)   |
| SMS Integration   | Twilio / custom gateway (HTTP API) |
| Background Tasks  | FastAPI BackgroundTasks or ARQ (for delayed reminders) |
| Testing           | Pytest, HTTPX                 |
| Deployment        | Render (web service)          |

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/                # Route handlers
│   │   ├── v1/             # API version 1
│   │   │   ├── auth.py     # Login, Register, Token Refresh
│   │   │   ├── patients.py # Patient CRUD
│   │   │   ├── reminders.py # Reminder CRUD & manual trigger
│   │   │   ├── attendance.py # Attendance marking & logs
│   │   │   ├── reports.py  # Aggregated statistics
│   │   │   └── chat.py     # WebSocket endpoint
│   │   └── deps.py         # Dependency injection (DB session, current user)
│   ├── core/               # Config, security, settings
│   │   ├── config.py       # Environment variables
│   │   ├── security.py     # Password hashing, JWT creation
│   │   └── database.py     # Async engine & session
│   ├── models/             # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── patient.py
│   │   ├── reminder.py
│   │   ├── attendance.py
│   │   ├── chat_message.py
│   │   └── sms_log.py
│   ├── schemas/            # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── patient.py
│   │   └── ...
│   ├── services/           # Business logic
│   │   ├── auth_service.py
│   │   ├── reminder_service.py
│   │   ├── sms_service.py
│   │   └── report_service.py
│   ├── utils/              # Helpers (pagination, serialisers)
│   └── main.py             # FastAPI app creation, routers, middleware
├── tests/                  # Pytest tests
├── requirements.txt
├── Dockerfile              # For containerised deployment (optional)
├── render.yaml             # Render deployment config
└── README.md
```

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.11 or higher
- pip / virtualenv
- A Supabase project with a PostgreSQL database

### Installation
```bash
git clone <backend-repo-url> burjeel-smartcare-backend
cd burjeel-smartcare-backend
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the project root:
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SMS Gateway (Twilio)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890

# App
APP_NAME=Burjeel Smart Care
DEBUG=True
```

### Database Setup (Migrations)
We use Alembic for schema migrations.
```bash
alembic upgrade head
```
*Alternatively, the first run can create tables automatically using SQLAlchemy’s `create_all` if migrations are not configured yet.*

### Run the Server
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

---

## 🔧 How the Backend Works

### 1. Authentication & Role‑Based Access
- Users login via `POST /api/v1/auth/login` with username/password.
- On success, a **JWT access token** is returned.
- All protected endpoints require the `Authorization: Bearer <token>` header.
- A dependency (`get_current_user`) decodes the token and returns the user object.
- Routes check the user’s role (`admin`, `pharmacist`, `it_staff`, `patient`) to restrict access.

### 2. Patient Management (Admin, Pharmacist)
- CRUD endpoints under `/api/v1/patients`.
- Search supported with query parameters (`?name=...`).
- Phone numbers are encrypted at the application level before storage (using AES) or rely on PostgreSQL column encryption.

### 3. Reminder Scheduling & SMS Automation
- **Create a reminder** via `POST /api/v1/reminders` (admin/pharmacist).
- A background scheduler (simple with FastAPI’s `BackgroundTasks` or a job queue like ARQ) checks for reminders due in 2 days and sends SMS via Twilio.
- The SMS delivery status is logged in `sms_logs`.
- A manual `POST /api/v1/reminders/{id}/send` endpoint allows immediate sending.

### 4. Attendance Tracking
- `POST /api/v1/attendance` marks a patient’s attendance (`came` / `not_came`).
- The endpoint records the staff member who entered the data and the timestamp.
- Historical attendance can be retrieved per patient or aggregated.

### 5. Live Chat (WebSocket)
- Endpoint: `ws://<host>/ws/chat/{user_id}?token=<jwt_token>`.
- Authentication is done on connection via the token query parameter.
- Messages are stored in the `chat_messages` table.
- Unauthorised connections are rejected.
- Staff can see all conversations; patients can only see their own.

### 6. Reports & Analytics
- `GET /api/v1/reports/attendance?from=...&to=...` returns counts of “came” vs. “not came”.
- `GET /api/v1/reports/reminders` – total sent, success rate.
- Uses SQL `GROUP BY` and aggregations for fast queries.

### 7. Security Measures
- All endpoints use HTTPS (forced by Render).
- Passwords are hashed with **bcrypt**.
- Inputs are validated by Pydantic; SQL injection prevented by ORM.
- CORS is configured only for the Vercel frontend domain.
- Sensitive settings are never exposed – they come from environment variables.

---

## 📦 Deployment to Render

1. **Create a new Web Service** on Render.
2. Link the GitHub repository.
3. Use the following settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env` in the Render dashboard.
5. The app will be deployed at `https://burjeel-smartcare-api.onrender.com`.

*Note: For background task scheduling (reminder checks), consider using Render Cron Jobs or an external scheduler (like a cheap Redis + ARQ worker).*

---

## 🔗 API Documentation

Once running, visit `/docs` for interactive Swagger UI or `/redoc` for ReDoc.

Key endpoint groups:
- **Auth** – login, register
- **Patients** – CRUD, search
- **Reminders** – schedule, list, send now
- **Attendance** – mark, history
- **Reports** – aggregated statistics
- **Chat** – WebSocket connection

---

## 🧪 Testing

Run tests with:
```bash
pytest
```
Tests are organised under `tests/`, using the FastAPI `TestClient` and a test database (isolated with `pytest-postgres` or a separate Supabase project).

---

## 📄 License

This project is proprietary – developed for academic purposes at Middle East College.

---

**Developed by:** Seham Albulushi (20S20055)  
**Supervisor:** Puttaswamy M. R.
```
