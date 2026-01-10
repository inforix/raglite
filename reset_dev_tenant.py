#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/wyp/develop/rag')

from infra.db import SessionLocal
from infra import models
from passlib.hash import pbkdf2_sha256
import uuid

db = SessionLocal()

# Delete all existing data
print("Deleting all tenants...")
db.query(models.ApiKey).delete()
db.query(models.Job).delete()
db.query(models.Chunk).delete()
db.query(models.Document).delete()
db.query(models.Dataset).delete()
db.query(models.Tenant).delete()
db.commit()
print("✓ All data deleted")

# Create dev-tenant
print("\nCreating dev-tenant...")
tenant = models.Tenant(
    id='dev-tenant',
    name='dev-tenant',
    description='Development tenant'
)

api_key_value = 'dev-secret-key'
api_key = models.ApiKey(
    id=str(uuid.uuid4()),
    tenant_id='dev-tenant',
    name='default-dev-key',
    key_hash=pbkdf2_sha256.hash(api_key_value),
    active=True
)

db.add(tenant)
db.add(api_key)
db.commit()

print("✓ Created tenant: dev-tenant")
print(f"✓ API Key: {api_key_value}")
print(f"\nTest with:")
print(f'  curl -H "Authorization: Bearer {api_key_value}" http://localhost:7615/v1/datasets')

db.close()
