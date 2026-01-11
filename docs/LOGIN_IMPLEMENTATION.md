# RAGLite Login Implementation Guide

## Overview
Proper JWT-based authentication has been implemented for the RAGLite admin UI, replacing the mock authentication system.

## Changes Made

### 1. Backend Changes

#### Database Model (`infra/models.py`)
Added `User` model with the following fields:
- `id`: Primary key (UUID)
- `email`: Unique email address (indexed)
- `password_hash`: Bcrypt hashed password
- `name`: Optional user name
- `is_active`: User activation status
- `is_superuser`: Admin privileges flag
- `created_at`: Timestamp
- `updated_at`: Auto-updated timestamp

#### Authentication Module (`app/auth.py`)
Created new authentication utilities:
- `verify_password()`: Verify password against bcrypt hash
- `get_password_hash()`: Hash password using bcrypt
- `create_access_token()`: Generate JWT tokens
- `decode_access_token()`: Validate and decode JWT tokens
- `get_current_user()`: Dependency to extract authenticated user from Bearer token
- `authenticate_user()`: Validate email/password credentials

#### API Routes (`app/api/routes.py`)
Updated authentication endpoints:
- **POST /auth/login**: 
  - Validates email and password
  - Returns JWT access token and user info
  - Returns 401 for invalid credentials
  
- **GET /auth/me**:
  - Requires Bearer token in Authorization header
  - Returns current user information
  - Returns 401 if token is invalid

#### Schemas (`app/schemas_auth.py`)
Updated authentication schemas:
- `UserOut`: Added `is_active` and `is_superuser` fields
- `LoginResponse`: Added `access_token` and `token_type` fields

#### Dependencies (`pyproject.toml`)
Added `python-jose[cryptography]` for JWT token handling

### 2. Frontend Changes

#### Auth Store (`ui/src/stores/authStore.ts`)
- Added token storage with persistence (localStorage)
- Changed `setUser` to `setAuth` to handle both user and token
- Tokens persist across browser refreshes

#### API Client (`ui/src/lib/api.ts`)
- Removed cookie-based authentication
- Added Bearer token authentication in request interceptor
- Automatically adds `Authorization: Bearer <token>` header to all requests
- Clears auth state and redirects to login on 401 responses

#### Login Page (`ui/src/components/auth/LoginPage.tsx`)
- Updated to handle `access_token` from login response
- Stores both user and token via `setAuth`
- Shows appropriate error messages from backend

#### Protected Route (`ui/src/components/layout/ProtectedRoute.tsx`)
- Only validates token if present
- Sends token in Bearer header for /auth/me check
- Handles token expiration properly

### 3. Database Migration

#### Migration File (`alembic/versions/b2c3d4e5f6a7_add_user_table.py`)
Creates the `users` table with all required fields and indexes.

### 4. Admin User Creation

#### Script (`scripts/create_admin_user.py`)
Utility script to create admin users:
```bash
# Create default admin (admin@raglite.local / admin123)
python scripts/create_admin_user.py

# Create custom admin
python scripts/create_admin_user.py user@example.com mypassword "My Name"
```

## Setup Instructions

### 1. Install Dependencies
```bash
cd /Users/wyp/develop/rag
uv sync
```

### 2. Run Database Migration
```bash
alembic upgrade head
```

### 3. Create Admin User
```bash
python scripts/create_admin_user.py
```

Default credentials:
- **Email**: `admin@raglite.local`
- **Password**: `admin123`

### 4. Rebuild UI
```bash
cd ui
npm run build
```

### 5. Start the Server
```bash
cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 7615
```

## Security Considerations

### Current Implementation
- JWT tokens with 24-hour expiration
- Bcrypt password hashing
- Bearer token authentication
- Token stored in localStorage (persists across refreshes)

### Production Recommendations

1. **Change Secret Key**: Update `SECRET_KEY` in `app/auth.py`:
   ```python
   SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
   ```

2. **Environment Variables**: Add to `.env`:
   ```env
   JWT_SECRET_KEY=<generate-strong-random-key>
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```

3. **HTTPS Only**: Always use HTTPS in production

4. **Token Refresh**: Consider implementing refresh tokens for longer sessions

5. **Rate Limiting**: Add rate limiting to `/auth/login` to prevent brute force

6. **Password Policy**: Enforce strong password requirements

7. **Account Lockout**: Implement account lockout after failed attempts

## API Usage

### Login
```bash
curl -X POST http://localhost:7615/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@raglite.local", "password": "admin123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "email": "admin@raglite.local",
    "name": "Admin User",
    "is_active": true,
    "is_superuser": true
  }
}
```

### Get Current User
```bash
curl http://localhost:7615/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Access Protected Endpoints
```bash
curl http://localhost:7615/tenants \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-Id: dev-tenant"
```

## Testing the Login

1. Navigate to http://localhost:7615/ui/login
2. Enter credentials:
   - Email: `admin@raglite.local`
   - Password: `admin123`
3. Click "Sign In"
4. You should be redirected to the dashboard with full access

## Troubleshooting

### "Could not validate credentials"
- Token has expired (24 hours)
- Secret key mismatch
- Token was tampered with
- Solution: Login again to get a new token

### "User not found"
- User was deleted from database
- Solution: Recreate admin user with script

### "Incorrect email or password"
- Invalid credentials
- Solution: Check email/password or reset password

### Migration Errors
```bash
# Check current migration version
alembic current

# Show migration history
alembic history

# Upgrade to specific version
alembic upgrade b2c3d4e5f6a7
```

## Next Steps

Consider implementing:
1. Password reset functionality
2. Email verification
3. Multi-factor authentication (MFA)
4. User management UI (create/edit/delete users)
5. Role-based access control (RBAC)
6. Audit logging
7. Session management
8. Token refresh mechanism
