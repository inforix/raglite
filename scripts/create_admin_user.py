"""Create default admin user for RAGLite"""
import sys
from sqlalchemy.orm import Session
from infra.db import engine
from infra.models import User
from app.auth import get_password_hash


def create_admin_user(email: str = "admin@raglite.local", password: str = "admin123", name: str = "Admin User"):
    """Create a default admin user."""
    with Session(engine) as db:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User {email} already exists.")
            return
        
        # Create admin user
        admin_user = User(
            email=email,
            password_hash=get_password_hash(password),
            name=name,
            is_active=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   ID: {admin_user.id}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
        name = sys.argv[3] if len(sys.argv) > 3 else "Admin User"
        create_admin_user(email, password, name)
    else:
        create_admin_user()
