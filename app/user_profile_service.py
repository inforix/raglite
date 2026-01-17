import uuid
from typing import Optional

from sqlalchemy.orm import Session

from infra import models


def get_or_create_user_profile(db: Session, user_id: str) -> models.UserProfile:
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if profile:
        return profile
    profile = models.UserProfile(id=str(uuid.uuid4()), user_id=user_id, show_quick_start=True)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_user_profile(
    db: Session,
    user_id: str,
    show_quick_start: Optional[bool] = None,
) -> models.UserProfile:
    profile = get_or_create_user_profile(db, user_id)
    if show_quick_start is not None:
        profile.show_quick_start = show_quick_start
    db.commit()
    db.refresh(profile)
    return profile

