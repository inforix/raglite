from __future__ import annotations

from typing import Any, Callable

from app.config import get_settings

settings = get_settings()


def _load_celery():
    try:
        from celery import Celery
    except ImportError:  # pragma: no cover - dev placeholder
        return None
    return Celery(
        "raglite",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["workers.tasks"],
    )


celery_app = None


def get_celery_app():
    global celery_app
    if celery_app is None:
        celery_app = _load_celery()
    return celery_app


def task(*args, **kwargs) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator proxy to register Celery tasks lazily."""

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        app = get_celery_app()
        if app is None:
            # attach a .delay shim that calls the function directly
            def delay(*dargs, **dkwargs):
                return fn(*dargs, **dkwargs)

            fn.delay = delay  # type: ignore[attr-defined]
            return fn
        return app.task(*args, **kwargs)(fn)

    return wrapper
