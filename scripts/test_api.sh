#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-http://localhost:7615}

echo "Creating tenant..."
TENANT_RESP=$(curl -s -X POST "$BASE/v1/tenants" -H 'Content-Type: application/json' -d '{"name":"test-tenant"}')
echo "Tenant response: $TENANT_RESP"
API_KEY=$(echo "$TENANT_RESP" | python -c "import sys,json; r=json.load(sys.stdin); print(r.get('\"'\"'api_key'\"'\"','\"'\"''\"'\"'))")
TENANT_ID=$(echo "$TENANT_RESP" | python -c "import sys,json; r=json.load(sys.stdin); print(r.get('\"'\"'id'\"'\"','\"'\"''\"'\"'))")
AUTH_HEADER="Authorization: Bearer $API_KEY"

echo "Creating dataset..."
DS_RESP=$(curl -s -X POST "$BASE/v1/datasets" -H "$AUTH_HEADER" -H 'Content-Type: application/json' -d '{"name":"test-ds"}')
echo "Dataset response: $DS_RESP"
DATASET_ID=$(echo "$DS_RESP" | python -c "import sys,json; r=json.load(sys.stdin); print(r.get('\"'\"'id'\"'\"','\"'\"''\"'\"'))")

echo "Listing datasets..."
curl -s "$BASE/v1/datasets" -H "$AUTH_HEADER"

echo "Uploading document..."
UPLOAD_RESP=$(curl -s -X POST "$BASE/v1/documents" -H "$AUTH_HEADER" -F "dataset_id=$DATASET_ID" -F "files=@<(echo 'Hello world from script')")
echo "Upload response: $UPLOAD_RESP"
JOB_ID=$(echo "$UPLOAD_RESP" | python -c "import sys,json; r=json.load(sys.stdin); print((r.get('\"'\"'job_ids'\"'\"') or ['\"'\"''\"'\"'])[0])")

if [ -n "$JOB_ID" ]; then
  echo "Fetching job status..."
  curl -s "$BASE/v1/jobs/$JOB_ID" -H "$AUTH_HEADER"
fi

echo "Querying..."
curl -s -X POST "$BASE/v1/query" -H "$AUTH_HEADER" -H 'Content-Type: application/json' -d "{\"query\":\"Hello world\", \"dataset_ids\":[\"$DATASET_ID\"], \"k\":3}"

echo "Deleting dataset..."
curl -s -X DELETE "$BASE/v1/datasets/$DATASET_ID" -H "$AUTH_HEADER"

echo "Deleting tenant..."
curl -s -X DELETE "$BASE/v1/tenants/$TENANT_ID"

echo "Done."
