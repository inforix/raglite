# Quick Start: Admin Login

## Setup (First Time Only)

1. **Run Migration**:
   ```bash
   cd /Users/wyp/develop/rag
   alembic upgrade head
   ```

2. **Create Admin User**:
   ```bash
   python scripts/create_admin_user.py
   ```
   
   This creates:
   - Email: `admin@raglite.local`
   - Password: `admin123`

3. **Start Server**:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 7615
   ```

4. **Login**:
   - Open: http://localhost:7615/ui/login
   - Use the credentials above

## Custom Admin User

```bash
python scripts/create_admin_user.py your@email.com yourpassword "Your Name"
```

## Password Security

**IMPORTANT**: Change the default password for production!

To change the secret key for JWT tokens, edit [`app/auth.py`](app/auth.py:13):
```python
SECRET_KEY = "your-production-secret-key-here"
```

Or use environment variable:
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret")
```

## How It Works

1. User submits email/password to `/auth/login`
2. Backend validates credentials against database
3. If valid, returns JWT access token (24hr expiration)
4. Frontend stores token in localStorage
5. All API requests include `Authorization: Bearer <token>` header
6. Backend validates token on each request via `/auth/me`

See [LOGIN_IMPLEMENTATION.md](docs/LOGIN_IMPLEMENTATION.md) for full details.
