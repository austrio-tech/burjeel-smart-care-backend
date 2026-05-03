# Burjeel Smart Care Backend

FastAPI backend for Burjeel Smart Care patient management system.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and configure your settings.

4. Set up your Supabase database using the SQL script in `Supabase.md`.

5. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Visit `http://localhost:8000/docs` for Swagger UI or `http://localhost:8000/redoc` for ReDoc.
