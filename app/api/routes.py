import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
import requests

from app import services
from app.config import get_settings
from app.dedup import find_duplicate_document
from app.deps import TenantContext, get_tenant
from app.schemas import (
    DatasetCreate,
    DatasetUpdate,
    DatasetOut,
    DocumentUploadResponse,
    JobOut,
    QueryRequest,
    QueryResponse,
    DocumentOut,
    DocumentUpdate,
    DocumentListResponse,
    QueryHistoryResponse,
    QueryDailyStatsResponse,
    SettingsOut,
    SettingsUpdate,
    ModelConfigCreate,
    ModelConfigOut,
    ModelConfigUpdate,
)
from app.schemas_tenant import TenantCreate, TenantOut, TenantApiKeyOut
from app.schemas_auth import LoginRequest, LoginResponse, UserOut, UserProfileOut, UserProfileUpdate
from app.auth import get_current_user as get_current_user_dep, get_current_superuser as get_current_superuser_dep
from core import answerer, embedder, rewriter, reranker, vectorstore, opensearch_bm25
from core import storage
from infra import models
from infra.models import User, ModelType
from infra.db import get_db
from app.settings_service import (
    get_app_settings_db,
    update_app_settings_db,
    get_model_configs,
    create_model_config,
    update_model_config,
    delete_model_config,
    get_allowed_model_names,
)
from app.user_profile_service import get_or_create_user_profile, update_user_profile

router = APIRouter()
settings = get_settings()
vs = vectorstore.get_vector_store()
bm25_client = opensearch_bm25.get_bm25_client()


@router.get("/settings", tags=["settings"], response_model=SettingsOut)
async def get_settings_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)) -> SettingsOut:
    app_settings = get_app_settings_db(db)
    embedders = get_model_configs(db, ModelType.embedder)
    chat_models = get_model_configs(db, ModelType.chat)
    rerank_models = get_model_configs(db, ModelType.rerank)
    return SettingsOut(
        default_embedder=app_settings.default_embedder,
        default_chat_model=app_settings.default_chat_model,
        default_rerank_model=app_settings.default_rerank_model,
        embedders=[ModelConfigOut.model_validate(m, from_attributes=True) for m in embedders],
        chat_models=[ModelConfigOut.model_validate(m, from_attributes=True) for m in chat_models],
        rerank_models=[ModelConfigOut.model_validate(m, from_attributes=True) for m in rerank_models],
    )


@router.put("/settings", tags=["settings"], response_model=SettingsOut)
async def update_settings_endpoint(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> SettingsOut:
    allowed_embedders = get_allowed_model_names(db, ModelType.embedder)
    allowed_chat_models = get_allowed_model_names(db, ModelType.chat)
    allowed_rerank_models = get_allowed_model_names(db, ModelType.rerank)

    if payload.default_embedder and payload.default_embedder not in allowed_embedders:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedder not allowed")
    if payload.default_chat_model and payload.default_chat_model not in allowed_chat_models:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat model not allowed")
    update_rerank = False
    target_rerank = None
    if payload.default_rerank_model is not None:
        update_rerank = True
        if payload.default_rerank_model != "":
            if payload.default_rerank_model not in allowed_rerank_models:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rerank model not allowed")
            target_rerank = payload.default_rerank_model
        else:
            needs_default = (
                db.query(models.Dataset)
                .filter(
                    models.Dataset.rerank_enabled.is_(True),
                    models.Dataset.rerank_model.is_(None),
                    models.Dataset.deleted_at.is_(None),
                )
                .first()
            )
            if needs_default:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot clear default rerank model while datasets rely on it.",
                )
    updated = update_app_settings_db(
        db,
        payload.default_embedder,
        payload.default_chat_model,
        default_rerank_model=target_rerank,
        update_rerank=update_rerank,
    )
    return SettingsOut(
        default_embedder=updated.default_embedder,
        default_chat_model=updated.default_chat_model,
        default_rerank_model=updated.default_rerank_model,
        embedders=[ModelConfigOut.model_validate(m, from_attributes=True) for m in get_model_configs(db, ModelType.embedder)],
        chat_models=[ModelConfigOut.model_validate(m, from_attributes=True) for m in get_model_configs(db, ModelType.chat)],
        rerank_models=[ModelConfigOut.model_validate(m, from_attributes=True) for m in get_model_configs(db, ModelType.rerank)],
    )


@router.post("/settings/embedders", tags=["settings"], response_model=ModelConfigOut, status_code=status.HTTP_201_CREATED)
async def create_embedder_model(
    payload: ModelConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> ModelConfigOut:
    mc = create_model_config(db, ModelType.embedder, payload)
    return ModelConfigOut.model_validate(mc, from_attributes=True)


@router.put("/settings/embedders/{model_id}", tags=["settings"], response_model=ModelConfigOut)
async def update_embedder_model(
    model_id: str,
    payload: ModelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> ModelConfigOut:
    mc = update_model_config(db, model_id, ModelType.embedder, payload)
    return ModelConfigOut.model_validate(mc, from_attributes=True)


@router.delete("/settings/embedders/{model_id}", tags=["settings"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_embedder_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
):
    delete_model_config(db, model_id, ModelType.embedder)
    return {}


@router.post("/settings/chat-models", tags=["settings"], response_model=ModelConfigOut, status_code=status.HTTP_201_CREATED)
async def create_chat_model(
    payload: ModelConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> ModelConfigOut:
    mc = create_model_config(db, ModelType.chat, payload)
    return ModelConfigOut.model_validate(mc, from_attributes=True)


@router.put("/settings/chat-models/{model_id}", tags=["settings"], response_model=ModelConfigOut)
async def update_chat_model(
    model_id: str,
    payload: ModelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> ModelConfigOut:
    mc = update_model_config(db, model_id, ModelType.chat, payload)
    return ModelConfigOut.model_validate(mc, from_attributes=True)


@router.delete("/settings/chat-models/{model_id}", tags=["settings"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
):
    delete_model_config(db, model_id, ModelType.chat)
    return {}


@router.post("/settings/rerank-models", tags=["settings"], response_model=ModelConfigOut, status_code=status.HTTP_201_CREATED)
async def create_rerank_model(
    payload: ModelConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> ModelConfigOut:
    mc = create_model_config(db, ModelType.rerank, payload)
    return ModelConfigOut.model_validate(mc, from_attributes=True)


@router.put("/settings/rerank-models/{model_id}", tags=["settings"], response_model=ModelConfigOut)
async def update_rerank_model(
    model_id: str,
    payload: ModelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
) -> ModelConfigOut:
    mc = update_model_config(db, model_id, ModelType.rerank, payload)
    return ModelConfigOut.model_validate(mc, from_attributes=True)


@router.delete("/settings/rerank-models/{model_id}", tags=["settings"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_rerank_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_dep),
):
    delete_model_config(db, model_id, ModelType.rerank)
    return {}


@router.post("/tenants", status_code=status.HTTP_201_CREATED, tags=["tenants"], response_model=TenantOut)
async def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    return services.create_tenant_with_key(db, payload)


@router.get("/tenants", tags=["tenants"], response_model=List[TenantOut])
async def list_tenants(db: Session = Depends(get_db)):
    return services.list_tenants(db)


@router.get("/tenants/{tenant_id}", tags=["tenants"], response_model=TenantOut)
async def get_tenant_by_id(tenant_id: str, db: Session = Depends(get_db)):
    return services.get_tenant(db, tenant_id)


@router.put("/tenants/{tenant_id}", tags=["tenants"], response_model=TenantOut)
async def update_tenant(tenant_id: str, payload: TenantCreate, db: Session = Depends(get_db)):
    return services.update_tenant(db, tenant_id, payload)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tenants"])
async def delete_tenant(tenant_id: str, db: Session = Depends(get_db)):
    services.delete_tenant(db, tenant_id)
    return {}


@router.post("/tenants/{tenant_id}/regenerate-key", tags=["tenants"], response_model=TenantApiKeyOut)
async def regenerate_tenant_key(tenant_id: str, db: Session = Depends(get_db)):
    return services.regenerate_tenant_api_key(db, tenant_id)


@router.post("/datasets", status_code=status.HTTP_201_CREATED, tags=["datasets"], response_model=DatasetOut)
async def create_dataset(
    payload: DatasetCreate, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)
) -> DatasetOut:
    return services.create_dataset(db, tenant.tenant_id, payload)


@router.get("/datasets", tags=["datasets"], response_model=List[DatasetOut])
async def list_datasets(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> List[DatasetOut]:
    return services.list_datasets(db, tenant.tenant_id)


@router.get("/datasets/{dataset_id}", tags=["datasets"], response_model=DatasetOut)
async def get_dataset(dataset_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> DatasetOut:
    return services.get_dataset(db, tenant.tenant_id, dataset_id)


@router.put("/datasets/{dataset_id}", tags=["datasets"], response_model=DatasetOut)
async def update_dataset(
    dataset_id: str,
    payload: DatasetUpdate,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db)
) -> DatasetOut:
    return services.update_dataset(db, tenant.tenant_id, dataset_id, payload)


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED, tags=["documents"], response_model=DocumentUploadResponse)
async def upload_documents(
    dataset_id: str,
    files: Optional[List[UploadFile]] = File(default=None),
    source_uri: Optional[str] = None,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    dataset = services.ensure_dataset(db, tenant.tenant_id, dataset_id)
    uploads = []
    incoming_files = list(files) if files else []
    
    # Validate that at least one source is provided
    if not incoming_files and not source_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either files or source_uri must be provided",
        )
    
    if incoming_files and len(incoming_files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files; max {settings.max_files_per_upload}",
        )
    if source_uri:
        from core.security import is_safe_url
        if not is_safe_url(source_uri):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or unsafe source_uri")
        try:
            resp = requests.get(source_uri, timeout=settings.parse_timeout_seconds)
            resp.raise_for_status()
            filename = source_uri.split("/")[-1] or "remote"
            doc_id = str(uuid.uuid4())
            path = storage.save_bytes(
                settings.object_store_root, tenant.tenant_id, dataset_id, doc_id, filename, resp.content
            )
            mime = resp.headers.get("content-type", "application/octet-stream")
            size = len(resp.content)
            content_hash = storage.compute_hash(resp.content)
            uploads.append((doc_id, filename, mime, size, path, content_hash, None))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to fetch source_uri: {e}")

    for f in incoming_files:
        if f.content_type not in settings.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type: {f.content_type}",
            )
        doc_id = str(uuid.uuid4())
        path, size, content_hash = storage.save_upload_file(
            settings.object_store_root, tenant.tenant_id, dataset_id, doc_id, f
        )
        if size > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large; max {settings.max_file_size_mb} MB",
            )
        dup = find_duplicate_document(db, tenant.tenant_id, dataset_id, content_hash)
        if dup:
            continue  # skip duplicates
        uploads.append((doc_id, f.filename or "upload", f.content_type, size, path, content_hash, None))
    if not uploads:
        return DocumentUploadResponse(job_ids=[])
    docs = services.record_documents(db, tenant.tenant_id, dataset_id, uploads)
    job_resp = services.create_document_jobs(db, tenant.tenant_id, dataset_id, docs, dataset.embedder)
    return job_resp


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED, tags=["documents"], response_model=DocumentUploadResponse)
async def upload_documents_form(
    dataset_id: str = Form(...),
    file: Optional[UploadFile] = File(default=None),
    files: Optional[List[UploadFile]] = File(default=None),
    source_uri: Optional[str] = Form(default=None),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Convenience alias for uploads from form-data (UI uses 'file'); forwards to /v1/documents handler.
    """
    incoming_files: List[UploadFile] = []
    if file:
        incoming_files.append(file)
    if files:
        incoming_files.extend(files)
    return await upload_documents(
        dataset_id=dataset_id,
        files=incoming_files or None,
        source_uri=source_uri,
        tenant=tenant,
        db=db,
    )


@router.get("/documents", tags=["documents"], response_model=DocumentListResponse)
async def list_documents(
    dataset_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """List documents with pagination. Optionally filter by dataset_id."""
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be between 1 and 100")
    return services.list_documents(db, tenant.tenant_id, dataset_id, page, page_size)


@router.get("/documents/{document_id}", tags=["documents"], response_model=DocumentOut)
async def get_document(
    document_id: str,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Get a single document by ID."""
    return services.get_document(db, tenant.tenant_id, document_id)


@router.put("/documents/{document_id}", tags=["documents"], response_model=DocumentOut)
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Update document metadata (filename, source_uri)."""
    return services.update_document(db, tenant.tenant_id, document_id, payload)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_202_ACCEPTED, tags=["datasets"])
async def delete_dataset(dataset_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    services.soft_delete_dataset(db, tenant.tenant_id, dataset_id)
    return {"status": "accepted", "dataset_id": dataset_id}


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED, tags=["documents"])
async def delete_document(document_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    services.soft_delete_document(db, tenant.tenant_id, document_id)
    return {"status": "accepted", "document_id": document_id}


@router.get("/jobs/{job_id}", tags=["jobs"], response_model=JobOut)
async def get_job(job_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> JobOut:
    return services.get_job(db, tenant.tenant_id, job_id)


@router.post("/query", tags=["query"], response_model=QueryResponse)
async def query(request: QueryRequest, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> QueryResponse:
    rewritten = rewriter.rewrite_query(request.query, tenant.tenant_id) if request.rewrite else None
    qtext = rewritten or request.query
    
    # Use the first dataset's embedder and rerank settings if specified, otherwise default
    query_embedder = None
    rerank_enabled = False
    rerank_model = None
    rerank_top_k = None
    rerank_min_score = None
    if request.dataset_ids:
        first_ds = db.query(models.Dataset).filter(
            models.Dataset.id == request.dataset_ids[0],
            models.Dataset.tenant_id == tenant.tenant_id
        ).first()
        if first_ds:
            query_embedder = first_ds.embedder
            rerank_enabled = bool(first_ds.rerank_enabled)
            rerank_model = first_ds.rerank_model
            rerank_top_k = first_ds.rerank_top_k
            rerank_min_score = first_ds.rerank_min_score
    
    retrieval_k = request.k
    if rerank_enabled and rerank_top_k:
        retrieval_k = max(request.k, rerank_top_k)

    vector = embedder.embed_texts([qtext], model_name=query_embedder)[0]
    dataset_ids = request.dataset_ids or []
    results_raw = vs.query(tenant.tenant_id, dataset_ids, vector, k=retrieval_k, filters=request.filters)
    bm25_hits = []
    if settings.enable_bm25 and dataset_ids and bm25_client:
        bm25_hits = bm25_client.search(tenant.tenant_id, dataset_ids, qtext, k=retrieval_k)
    # results_raw expected format: list of dict with payload keys
    results = []
    for hit in results_raw:
        payload = hit.get("payload", {})
        doc_id = payload.get("document_id") or ""
        ds_id = payload.get("dataset_id") or ""
        results.append(
            {
                "chunk_id": hit.get("id", "") or "",
                "document_id": doc_id,
                "dataset_id": ds_id,
                "score": hit.get("score", 0.0),
                "text": payload.get("text", "") or "",
                "source_uri": payload.get("source_uri"),
                "meta": payload.get("meta"),
            }
        )
    merged = {}
    for r in results:
        merged[r["chunk_id"]] = r
    for hit in bm25_hits:
        cid = hit.get("id", "") or ""
        payload = hit.get("payload", {})
        doc_id = payload.get("document_id") or ""
        ds_id = payload.get("dataset_id") or ""
        if cid in merged:
            merged[cid]["score"] += hit.get("score", 0.0)
        else:
            merged[cid] = {
                "chunk_id": cid,
                "document_id": doc_id,
                "dataset_id": ds_id,
                "score": hit.get("score", 0.0),
                "text": payload.get("text", "") or "",
                "source_uri": payload.get("source_uri"),
                "meta": payload.get("meta"),
            }
    merged_list = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)[: retrieval_k]
    min_score = request.min_score
    if min_score is None:
        min_score = settings.query_min_score
    if min_score is not None:
        merged_list = [hit for hit in merged_list if hit.get("score", 0) >= min_score]
    rerank_applied = False
    rerank_applied_model = None
    if rerank_enabled:
        reranked, rerank_applied, rerank_applied_model = reranker.rerank_with_metadata(
            qtext,
            merged_list,
            model_name=rerank_model,
            top_k=rerank_top_k,
            min_score=rerank_min_score,
        )
    else:
        reranked = merged_list
    reranked = reranked[: request.k]
    answer = None
    if request.answer:
        if request.answer_model:
            allowed_chat_models = get_allowed_model_names(db, ModelType.chat)
            if request.answer_model not in allowed_chat_models:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat model not allowed")
        answer = answerer.generate_answer(request.query, reranked, request.answer_model)
    try:
        services.log_query(db, tenant.tenant_id, request.query, request.dataset_ids)
    except Exception:
        pass
    return QueryResponse(
        query=request.query,
        rewritten=rewritten,
        results=reranked,
        answer=answer,
        rerank_applied=rerank_applied,
        rerank_model=rerank_applied_model,
    )


@router.get("/query/history", tags=["query"], response_model=QueryHistoryResponse)
async def query_history(
    page: int = 1,
    page_size: int = 20,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> QueryHistoryResponse:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be between 1 and 100")
    return services.list_query_history(db, tenant.tenant_id, page, page_size)


@router.get("/query/stats/daily", tags=["query"], response_model=QueryDailyStatsResponse)
async def query_daily_stats(
    days: int = 14,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> QueryDailyStatsResponse:
    if days < 1 or days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="days must be between 1 and 90")
    return services.get_query_daily_stats(db, tenant.tenant_id, days)


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED, tags=["maintenance"])
async def reindex(dataset_id: str, embedder: Optional[str] = None, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    ds = services.ensure_dataset(db, tenant.tenant_id, dataset_id)
    allowed_embedders = get_allowed_model_names(db, ModelType.embedder)
    if embedder and embedder not in allowed_embedders:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedder not allowed")
    target_embedder = embedder or ds.embedder
    job_id = services.create_reindex_job(db, tenant.tenant_id, dataset_id, target_embedder)
    services.enqueue_reindex_job(job_id, tenant.tenant_id, dataset_id, target_embedder)
    return {"status": "accepted", "job_id": job_id, "dataset_id": dataset_id, "embedder": target_embedder}


# Authentication endpoints
@router.post("/auth/login", tags=["auth"], response_model=LoginResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint with JWT authentication."""
    from app.auth import authenticate_user, create_access_token
    
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    profile = get_or_create_user_profile(db, user.id)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            profile=UserProfileOut(show_quick_start=profile.show_quick_start),
        )
    )


@router.get("/auth/me", tags=["auth"], response_model=UserOut)
async def get_current_user(
    current_user: User = Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Get current user info from JWT token."""
    profile = get_or_create_user_profile(db, current_user.id)
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        profile=UserProfileOut(show_quick_start=profile.show_quick_start),
    )


@router.put("/auth/profile", tags=["auth"], response_model=UserProfileOut)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    profile = update_user_profile(db, current_user.id, payload.show_quick_start)
    return UserProfileOut(show_quick_start=profile.show_quick_start)


@router.post("/auth/logout", tags=["auth"])
async def logout():
    """
    Logout endpoint.
    In production, this should invalidate the JWT token.
    """
    return {"status": "ok", "message": "Logged out successfully"}
