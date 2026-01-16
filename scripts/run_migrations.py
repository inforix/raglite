#!/usr/bin/env python3
"""Run database migrations - standalone script"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

DEFAULT_DSN = "postgresql://raglite:raglite@localhost:5432/raglite"


def run_migrations(db_path=None):
    """Run all pending migrations directly."""
    if not db_path:
        db_path = os.getenv("RAGLITE_POSTGRES_DSN", DEFAULT_DSN)

    engine = create_engine(db_path)
    
    with Session(engine) as db:
        # Create alembic_version table if it doesn't exist
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """))
        
        # Check current version
        result = db.execute(text("SELECT version_num FROM alembic_version"))
        current = result.fetchone()
        current_version = current[0] if current else None
        
        print(f"Current migration version: {current_version or 'None'}")
        
        # Check if users table exists
        if not inspect(engine).has_table("users"):
            print("Creating users table...")
            
            # Create users table
            db.execute(text("""
                CREATE TABLE users (
                    id VARCHAR NOT NULL,
                    email VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    name VARCHAR,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (id)
                )
            """))
            
            # Create index
            db.execute(text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
            
            # Update alembic version
            if current_version:
                db.execute(text(
                    "UPDATE alembic_version SET version_num = 'b2c3d4e5f6a7'"
                ))
            else:
                db.execute(text(
                    "INSERT INTO alembic_version (version_num) VALUES ('b2c3d4e5f6a7')"
                ))
            
            db.commit()
            print("✅ Users table created successfully!")
            print("✅ Migration b2c3d4e5f6a7 applied")
        else:
            print("✅ Users table already exists")
        
        return True


if __name__ == "__main__":
    try:
        run_migrations()
        print("\n✅ All migrations completed!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
