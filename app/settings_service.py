import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import ModelConfigCreate, ModelConfigUpdate
from infra import models

cfg = get_settings()


def seed_model_configs_from_settings(db: Session) -> None:
    """Bootstrap model configs from environment defaults if none exist yet."""
    if db.query(models.ModelConfig).count() > 0:
        return
    now = datetime.utcnow()
    seed_rows: List[models.ModelConfig] = []
    for name in cfg.allowed_embedders:
        seed_rows.append(
            models.ModelConfig(
                id=str(uuid.uuid4()),
                name=name,
                type=models.ModelType.embedder.value,
                endpoint="",
                api_key=None,
                model=name,
                created_at=now,
                updated_at=now,
            )
        )
    for name in cfg.allowed_chat_models:
        seed_rows.append(
            models.ModelConfig(
                id=str(uuid.uuid4()),
                name=name,
                type=models.ModelType.chat.value,
                endpoint="",
                api_key=None,
                model=name,
                created_at=now,
                updated_at=now,
            )
        )
    if seed_rows:
        db.add_all(seed_rows)
        db.commit()


def get_model_configs(db: Session, model_type: models.ModelType) -> List[models.ModelConfig]:
    seed_model_configs_from_settings(db)
    return (
        db.query(models.ModelConfig)
        .filter(models.ModelConfig.type == model_type.value)
        .order_by(models.ModelConfig.created_at.asc())
        .all()
    )


def get_allowed_model_names(db: Session, model_type: models.ModelType) -> List[str]:
    configs = get_model_configs(db, model_type)
    return [m.name for m in configs]


def get_model_config_by_name(db: Session, model_type: models.ModelType, name: Optional[str]) -> Optional[models.ModelConfig]:
    if not name:
        return None
    seed_model_configs_from_settings(db)
    return (
        db.query(models.ModelConfig)
        .filter(models.ModelConfig.type == model_type.value, models.ModelConfig.name == name)
        .first()
    )


def ensure_settings_defaults(db: Session, settings_row: Optional[models.AppSettings]) -> models.AppSettings:
    settings_obj = settings_row or db.query(models.AppSettings).first()
    if not settings_obj:
        return get_app_settings_db(db)

    allowed_embedders = get_allowed_model_names(db, models.ModelType.embedder)
    allowed_chat_models = get_allowed_model_names(db, models.ModelType.chat)
    changed = False

    if allowed_embedders and settings_obj.default_embedder not in allowed_embedders:
        settings_obj.default_embedder = allowed_embedders[0]
        changed = True
    if allowed_chat_models and settings_obj.default_chat_model not in allowed_chat_models:
        settings_obj.default_chat_model = allowed_chat_models[0]
        changed = True

    if changed:
        db.commit()
        db.refresh(settings_obj)
    return settings_obj


def get_app_settings_db(db: Session) -> models.AppSettings:
    seed_model_configs_from_settings(db)
    settings_row = db.query(models.AppSettings).first()
    if not settings_row:
        settings_row = models.AppSettings(
            id=str(uuid.uuid4()),
            default_embedder=cfg.default_embedder,
            default_chat_model=cfg.default_chat_model,
        )
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return ensure_settings_defaults(db, settings_row)


def update_app_settings_db(db: Session, default_embedder: str | None, default_chat_model: str | None) -> models.AppSettings:
    settings_row = get_app_settings_db(db)
    if default_embedder:
        settings_row.default_embedder = default_embedder
    if default_chat_model:
        settings_row.default_chat_model = default_chat_model
    db.commit()
    db.refresh(settings_row)
    return settings_row


def create_model_config(db: Session, model_type: models.ModelType, payload: ModelConfigCreate) -> models.ModelConfig:
    seed_model_configs_from_settings(db)
    existing = (
        db.query(models.ModelConfig)
        .filter(models.ModelConfig.name == payload.name, models.ModelConfig.type == model_type.value)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{model_type.value.capitalize()} model with this name already exists",
        )
    now = datetime.utcnow()
    mc = models.ModelConfig(
        id=str(uuid.uuid4()),
        name=payload.name,
        type=model_type.value,
        endpoint=payload.endpoint,
        api_key=payload.api_key,
        model=payload.model,
        created_at=now,
        updated_at=now,
    )
    db.add(mc)
    db.commit()
    db.refresh(mc)

    # Ensure defaults exist
    settings_row = get_app_settings_db(db)
    changed = False
    if model_type == models.ModelType.embedder and not settings_row.default_embedder:
        settings_row.default_embedder = mc.name
        changed = True
    if model_type == models.ModelType.chat and not settings_row.default_chat_model:
        settings_row.default_chat_model = mc.name
        changed = True
    if changed:
        db.commit()
        db.refresh(settings_row)
    return mc


def update_model_config(db: Session, model_id: str, model_type: models.ModelType, payload: ModelConfigUpdate) -> models.ModelConfig:
    seed_model_configs_from_settings(db)
    mc = (
        db.query(models.ModelConfig)
        .filter(models.ModelConfig.id == model_id, models.ModelConfig.type == model_type.value)
        .first()
    )
    if not mc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    old_name = mc.name
    new_name = payload.name or mc.name
    if new_name != mc.name:
        duplicate = (
            db.query(models.ModelConfig)
            .filter(
                models.ModelConfig.name == new_name,
                models.ModelConfig.type == model_type.value,
                models.ModelConfig.id != model_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{model_type.value.capitalize()} model with this name already exists",
            )
        mc.name = new_name

    if payload.endpoint is not None:
        mc.endpoint = payload.endpoint
    if payload.api_key is not None:
        mc.api_key = payload.api_key
    if payload.model is not None:
        mc.model = payload.model

    settings_row = get_app_settings_db(db)
    if new_name != old_name:
        if model_type == models.ModelType.embedder:
            db.query(models.Dataset).filter(models.Dataset.embedder == old_name).update({"embedder": new_name})
            if settings_row.default_embedder == old_name:
                settings_row.default_embedder = new_name
        else:
            if settings_row.default_chat_model == old_name:
                settings_row.default_chat_model = new_name

    mc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mc)
    db.refresh(settings_row)
    return mc


def delete_model_config(db: Session, model_id: str, model_type: models.ModelType) -> None:
    seed_model_configs_from_settings(db)
    mc = (
        db.query(models.ModelConfig)
        .filter(models.ModelConfig.id == model_id, models.ModelConfig.type == model_type.value)
        .first()
    )
    if not mc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    settings_row = get_app_settings_db(db)
    if model_type == models.ModelType.embedder:
        in_use = (
            db.query(models.Dataset)
            .filter(models.Dataset.embedder == mc.name, models.Dataset.deleted_at.is_(None))
            .first()
        )
        if in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Embedder is in use by datasets. Reassign them before deleting.",
            )
        if settings_row.default_embedder == mc.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update the default embedder before deleting this entry.",
            )
    else:
        if settings_row.default_chat_model == mc.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update the default chat model before deleting this entry.",
            )

    db.delete(mc)
    db.commit()
