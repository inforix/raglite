import uuid
from sqlalchemy.orm import Session

from app.config import get_settings
from infra import models


def get_app_settings_db(db: Session) -> models.AppSettings:
    settings_row = db.query(models.AppSettings).first()
    if settings_row:
        return settings_row
    cfg = get_settings()
    settings_row = models.AppSettings(
        id=str(uuid.uuid4()),
        default_embedder=cfg.default_embedder,
        default_chat_model=cfg.default_chat_model,
    )
    db.add(settings_row)
    db.commit()
    db.refresh(settings_row)
    return settings_row


def update_app_settings_db(db: Session, default_embedder: str | None, default_chat_model: str | None) -> models.AppSettings:
    settings_row = get_app_settings_db(db)
    if default_embedder:
        settings_row.default_embedder = default_embedder
    if default_chat_model:
        settings_row.default_chat_model = default_chat_model
    db.commit()
    db.refresh(settings_row)
    return settings_row
