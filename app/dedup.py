from typing import Optional

from sqlalchemy.orm import Session

from infra import models


def find_duplicate_document(db: Session, tenant_id: str, dataset_id: str, content_hash: str) -> Optional[models.Document]:
    return (
        db.query(models.Document)
        .filter(
            models.Document.tenant_id == tenant_id,
            models.Document.dataset_id == dataset_id,
            models.Document.content_hash == content_hash,
            models.Document.deleted_at.is_(None),
        )
        .first()
    )

