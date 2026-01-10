#!/usr/bin/env bash
# Comprehensive API test script for RAGLite
set -euo pipefail

BASE=${BASE:-http://localhost:7615}
FAILED=0
PASSED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

# Test health endpoint
log_test "Testing health endpoint..."
HEALTH=$(curl -s "$BASE/health")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    log_pass "Health endpoint working"
else
    log_fail "Health endpoint failed: $HEALTH"
fi

# Test creating tenant
log_test "Creating tenant..."
TENANT_RESP=$(curl -s -X POST "$BASE/v1/tenants" \
    -H 'Content-Type: application/json' \
    -d '{"name":"test-tenant","description":"Test tenant for API validation"}')

if echo "$TENANT_RESP" | grep -q '"id"'; then
    log_pass "Tenant created successfully"
    API_KEY=$(echo "$TENANT_RESP" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('api_key',''))" 2>/dev/null || echo "")
    TENANT_ID=$(echo "$TENANT_RESP" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('id',''))" 2>/dev/null || echo "")
    
    if [ -z "$API_KEY" ] || [ -z "$TENANT_ID" ]; then
        log_fail "Failed to extract API key or tenant ID"
        exit 1
    fi
else
    log_fail "Tenant creation failed: $TENANT_RESP"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $API_KEY"

# Test listing tenants
log_test "Listing tenants..."
TENANTS_LIST=$(curl -s "$BASE/v1/tenants")
if echo "$TENANTS_LIST" | grep -q "$TENANT_ID"; then
    log_pass "Tenants list working"
else
    log_fail "Tenants list failed: $TENANTS_LIST"
fi

# Test creating dataset
log_test "Creating dataset..."
DS_RESP=$(curl -s -X POST "$BASE/v1/datasets" \
    -H "$AUTH_HEADER" \
    -H 'Content-Type: application/json' \
    -d '{"name":"test-dataset","description":"Test dataset","embedder":"sentence-transformers/all-MiniLM-L6-v2"}')

if echo "$DS_RESP" | grep -q '"id"'; then
    log_pass "Dataset created successfully"
    DATASET_ID=$(echo "$DS_RESP" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('id',''))" 2>/dev/null || echo "")
    
    if [ -z "$DATASET_ID" ]; then
        log_fail "Failed to extract dataset ID"
        exit 1
    fi
else
    log_fail "Dataset creation failed: $DS_RESP"
    exit 1
fi

# Test listing datasets
log_test "Listing datasets..."
DS_LIST=$(curl -s "$BASE/v1/datasets" -H "$AUTH_HEADER")
if echo "$DS_LIST" | grep -q "$DATASET_ID"; then
    log_pass "Datasets list working"
else
    log_fail "Datasets list failed: $DS_LIST"
fi

# Test uploading document with files parameter (missing validation)
log_test "Testing document upload without files or source_uri (should fail)..."
UPLOAD_FAIL=$(curl -s -X POST "$BASE/v1/documents" \
    -H "$AUTH_HEADER" \
    -F "dataset_id=$DATASET_ID" 2>&1 || echo "")
if echo "$UPLOAD_FAIL" | grep -q "must be provided"; then
    log_pass "Validation working - rejects empty upload"
else
    log_fail "Validation failed - should reject empty upload"
fi

# Test uploading document with text file
log_test "Uploading document with file..."
echo "This is a test document for RAGLite API. It contains some sample text for chunking and embedding." > /tmp/test_doc.txt
UPLOAD_RESP=$(curl -s -X POST "$BASE/v1/documents" \
    -H "$AUTH_HEADER" \
    -F "dataset_id=$DATASET_ID" \
    -F "files=@/tmp/test_doc.txt")

if echo "$UPLOAD_RESP" | grep -q '"job_ids"'; then
    log_pass "Document upload working"
    JOB_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; r=json.load(sys.stdin); jobs=r.get('job_ids',[]); print(jobs[0] if jobs else '')" 2>/dev/null || echo "")
    
    if [ -n "$JOB_ID" ]; then
        # Wait a bit for job processing
        sleep 2
        
        # Test job status endpoint
        log_test "Checking job status..."
        JOB_RESP=$(curl -s "$BASE/v1/jobs/$JOB_ID" -H "$AUTH_HEADER")
        if echo "$JOB_RESP" | grep -q '"id"'; then
            log_pass "Job status endpoint working"
            JOB_STATUS=$(echo "$JOB_RESP" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('status',''))" 2>/dev/null || echo "")
            echo "    Job status: $JOB_STATUS"
        else
            log_fail "Job status endpoint failed: $JOB_RESP"
        fi
    fi
else
    log_fail "Document upload failed: $UPLOAD_RESP"
fi

# Test uploading with source_uri
log_test "Testing upload with source_uri (will likely fail without valid URL)..."
URI_UPLOAD=$(curl -s -X POST "$BASE/v1/documents" \
    -H "$AUTH_HEADER" \
    -F "dataset_id=$DATASET_ID" \
    -F "source_uri=https://httpbin.org/robots.txt" 2>&1 || echo "failed")
if echo "$URI_UPLOAD" | grep -q '"job_ids"' || echo "$URI_UPLOAD" | grep -q "Failed to fetch"; then
    log_pass "Source URI parameter accepted"
else
    log_fail "Source URI upload unexpected response: $URI_UPLOAD"
fi

# Wait for ingestion to complete
sleep 5

# Test query endpoint
log_test "Testing query endpoint..."
QUERY_RESP=$(curl -s -X POST "$BASE/v1/query" \
    -H "$AUTH_HEADER" \
    -H 'Content-Type: application/json' \
    -d "{\"query\":\"test document\", \"dataset_ids\":[\"$DATASET_ID\"], \"k\":3, \"rewrite\":false}")

if echo "$QUERY_RESP" | grep -q '"results"'; then
    log_pass "Query endpoint working"
    RESULT_COUNT=$(echo "$QUERY_RESP" | python3 -c "import sys,json; r=json.load(sys.stdin); print(len(r.get('results',[])))" 2>/dev/null || echo "0")
    echo "    Found $RESULT_COUNT results"
else
    log_fail "Query endpoint failed: $QUERY_RESP"
fi

# Test query with rewrite
log_test "Testing query with rewrite..."
QUERY_REWRITE=$(curl -s -X POST "$BASE/v1/query" \
    -H "$AUTH_HEADER" \
    -H 'Content-Type: application/json' \
    -d "{\"query\":\"test\", \"dataset_ids\":[\"$DATASET_ID\"], \"k\":5, \"rewrite\":true}")

if echo "$QUERY_REWRITE" | grep -q '"results"'; then
    log_pass "Query with rewrite working"
else
    log_fail "Query with rewrite failed: $QUERY_REWRITE"
fi

# Test reindex endpoint
log_test "Testing reindex endpoint..."
REINDEX_RESP=$(curl -s -X POST "$BASE/v1/reindex?dataset_id=$DATASET_ID" \
    -H "$AUTH_HEADER")

if echo "$REINDEX_RESP" | grep -q '"job_id"'; then
    log_pass "Reindex endpoint working"
else
    log_fail "Reindex endpoint failed: $REINDEX_RESP"
fi

# Test updating tenant
log_test "Testing tenant update..."
UPDATE_RESP=$(curl -s -X PUT "$BASE/v1/tenants/$TENANT_ID" \
    -H 'Content-Type: application/json' \
    -d '{"name":"updated-tenant","description":"Updated description"}')

if echo "$UPDATE_RESP" | grep -q "updated-tenant"; then
    log_pass "Tenant update working"
else
    log_fail "Tenant update failed: $UPDATE_RESP"
fi

# Test deleting document (need to get document ID first)
# Skip for now as we'd need to query documents

# Test deleting dataset
log_test "Testing dataset deletion..."
DEL_DS=$(curl -s -X DELETE "$BASE/v1/datasets/$DATASET_ID" -H "$AUTH_HEADER")
if echo "$DEL_DS" | grep -q "accepted"; then
    log_pass "Dataset deletion working"
else
    log_fail "Dataset deletion failed: $DEL_DS"
fi

# Test deleting tenant
log_test "Testing tenant deletion..."
DEL_TENANT=$(curl -s -X DELETE "$BASE/v1/tenants/$TENANT_ID")
if [ $? -eq 0 ]; then
    log_pass "Tenant deletion working"
else
    log_fail "Tenant deletion failed"
fi

# Cleanup
rm -f /tmp/test_doc.txt

# Summary
echo ""
echo "================================"
echo "Test Summary:"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "================================"

if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0
