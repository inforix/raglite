#!/usr/bin/env python3
"""Reset tenants and create dev-tenant"""

from infra.db import SessionLocal
from infra import models
from passlib.hash import pbkdf2_sha256
import uuid

def main():
    db = SessionLocal()
    try:
        # Delete all existing tenants and related data
        print("Deleting all existing tenants...")
        tenants = db.query(models.Tenant).all()
        for tenant in tenants:
            print(f"  Deleting tenant: {tenant.name} (ID: {tenant.id})")
            # Delete related data
            db.query(models.ApiKey).filter(models.ApiKey.tenant_id == tenant.id).delete()
            db.query(models.Job).filter(models.Job.tenant_id == tenant.id).delete()
            db.query(models.Chunk).filter(models.Chunk.tenant_id == tenant.id).delete()
            db.query(models.Document).filter(models.Document.tenant_id == tenant.id).delete()
            db.query(models.Dataset).filter(models.Dataset.tenant_id == tenant.id).delete()
            db.delete(tenant)
        db.commit()
        print("All tenants deleted.")
        
        # Create dev-tenant
        print("\nCreating dev-tenant...")
        tenant_id = "dev-tenant"
        tenant = models.Tenant(
            id=tenant_id,
            name="dev-tenant",
            description="Development tenant"
        )
        
        # Create API key
        api_key_value = "dev-secret-key"
        key_hash = pbkdf2_sha256.hash(api_key_value)
        api_key = models.ApiKey(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="default-dev-key",
            key_hash=key_hash,
            active=True,
        )
        
        db.add(tenant)
        db.add(api_key)
        db.commit()
        
        print(f"✓ Tenant created: {tenant.name}")
        print(f"✓ Tenant ID: {tenant.id}")
        print(f"✓ API Key: {api_key_value}")
        print("\nYou can now use:")
        print(f'  curl -H "Authorization: Bearer {api_key_value}" http://localhost:7615/v1/datasets')
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
