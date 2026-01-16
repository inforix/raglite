#!/bin/bash

# RAGLite Setup Script - Auth Implementation

set -e

echo "🚀 RAGLite Authentication Setup"
echo "================================"
echo ""

cd "$(dirname "$0")/.."

# Load env vars if present
if [ -f ".env" ]; then
    set -a
    . ./.env
    set +a
fi

RAGLITE_POSTGRES_DSN=${RAGLITE_POSTGRES_DSN:-postgresql://raglite:raglite@localhost:5432/raglite}

# Step 1: Check database
echo "📊 Step 1: Checking database..."
echo "✅ Using database: ${RAGLITE_POSTGRES_DSN}"

# Step 2: Run migrations
echo ""
echo "📊 Step 2: Running migrations..."
uv run python scripts/run_migrations.py

# Step 3: Create admin user
echo ""
echo "👤 Step 3: Creating admin user..."
uv run python scripts/create_admin_standalone.py

# Step 4: Rebuild UI
echo ""
echo "🎨 Step 4: Rebuilding UI..."
cd ui
bun install --frozen-lockfile --save-text-lockfile
bun run build 2>&1 | grep -E "(built in|error|warning)" || true
cd ..

# Step 5: Check server
echo ""
echo "🔍 Step 5: Checking server status..."
if lsof -ti:7615 > /dev/null 2>&1; then
    echo "⚠️  Server already running on port 7615"
    echo "   Stop it with: lsof -ti:7615 | xargs kill -9"
else
    echo "✅ Port 7615 is available"
fi

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📖 Next Steps:"
echo "   1. Start the server:"
echo "      uv run uvicorn app.main:app --host 0.0.0.0 --port 7615"
echo ""
echo "   2. Open the admin UI:"
echo "      http://localhost:7615/ui/login"
echo ""
echo "   3. Login with:"
echo "      Email: admin@raglite.local"
echo "      Password: admin123"
echo ""
echo "🔐 Security: Change the default password in production!"
echo ""
