#!/usr/bin/env python3
"""Create admin user - standalone script"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_DSN = "postgresql://raglite:raglite@localhost:5432/raglite"


def create_admin_user(
    db_path=None,
    email="admin@raglite.local",
    password="admin123",
    name="Admin User"
):
    """Create an admin user directly in the database."""
    if not db_path:
        db_path = os.getenv("RAGLITE_POSTGRES_DSN", DEFAULT_DSN)

    engine = create_engine(db_path)
    
    with Session(engine) as db:
        # Check if users table exists
        if not inspect(engine).has_table("users"):
            print("❌ Users table does not exist. Run migrations first:")
            print("   uv run python -m alembic upgrade head")
            return False
        
        # Check if user already exists
        result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
        if result.fetchone():
            print(f"❌ User {email} already exists.")
            return False
        
        # Create admin user
        user_id = str(uuid.uuid4())
        password_hash = pwd_context.hash(password)
        now = datetime.utcnow()
        
        db.execute(text("""
            INSERT INTO users (id, email, password_hash, name, is_active, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :password_hash, :name, :is_active, :is_superuser, :created_at, :updated_at)
        """), {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "is_active": True,
            "is_superuser": True,
            "created_at": now,
            "updated_at": now
        })
        
        db.commit()
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   ID: {user_id}")
        print(f"\n🔐 Login at: http://localhost:7615/ui/login")
        return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
        name = sys.argv[3] if len(sys.argv) > 3 else "Admin User"
        create_admin_user(email=email, password=password, name=name)
    else:
        create_admin_user()
