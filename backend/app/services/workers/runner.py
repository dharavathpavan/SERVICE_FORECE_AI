"""
Task runner.

``inline`` runs tasks synchronously in the calling process (development and tests).
``celery`` dispatches to a Celery worker when one is configured. The API layer only
ever calls :func:`submit`, so switching modes is a configuration change.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.workers.tasks import (
    TaskResult,
    campaign_dialer_sweep,
    finalize_call_summary,
    ingest_document,
)

logger = logging.getLogger(__name__)

TASK_INGEST_DOCUMENT = "ingest_document"
TASK_FINALIZE_CALL_SUMMARY = "finalize_call_summary"
TASK_CAMPAIGN_DIALER_SWEEP = "campaign_dialer_sweep"


class InlineRunner:
    """Runs tasks immediately, each in its own DB session."""

    name = "inline"

    def ingest_document(self, document_id: str, raw_bytes: bytes) -> TaskResult:
        db = SessionLocal()
        try:
            return ingest_document(db, document_id, raw_bytes)
        finally:
            db.close()

    def finalize_call_summary(self, call_id: str) -> TaskResult:
        db = SessionLocal()
        try:
            return finalize_call_summary(db, call_id)
        finally:
            db.close()

    def campaign_dialer_sweep(self, campaign_id: str, max_calls: int = 5) -> TaskResult:
        db = SessionLocal()
        try:
            return campaign_dialer_sweep(db, campaign_id, max_calls)
        finally:
            db.close()


class CeleryRunner:
    """
    Dispatches to Celery. Requires a running broker (Redis).

    The Celery app is imported lazily so the dependency stays optional; if it is
    missing, calls fail loudly instead of silently no-oping.
    """

    name = "celery"

    def __init__(self) -> None:
        try:
            from celery import Celery  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "WORKER_MODE=celery requires the 'celery' package. Install it or use inline mode."
            ) from exc
        from app.workers.celery_app import celery_app  # type: ignore

        self._app = celery_app

    def _send(self, task_name: str, **kwargs: Any) -> TaskResult:
        self._app.send_task(task_name, kwargs=kwargs)
        return TaskResult(task_name, True, detail={"dispatched": True, "mode": "celery"})

    def ingest_document(self, document_id: str, raw_bytes: bytes) -> TaskResult:
        # Celery cannot ship raw bytes as a message payload; store first, then pass a key.
        raise RuntimeError("Use storage-backed ingestion for celery mode.")

    def finalize_call_summary(self, call_id: str) -> TaskResult:
        return self._send(TASK_FINALIZE_CALL_SUMMARY, call_id=call_id)

    def campaign_dialer_sweep(self, campaign_id: str, max_calls: int = 5) -> TaskResult:
        return self._send(TASK_CAMPAIGN_DIALER_SWEEP, campaign_id=campaign_id, max_calls=max_calls)


_runner_cache: Optional[Any] = None


def get_runner():
    global _runner_cache
    if _runner_cache is None:
        mode = (settings.WORKER_MODE or "inline").lower()
        _runner_cache = CeleryRunner() if mode == "celery" else InlineRunner()
        logger.info("Worker runner initialised: %s", _runner_cache.name)
    return _runner_cache


def set_runner(runner: Optional[Any]) -> None:
    global _runner_cache
    _runner_cache = runner


__all__ = [
    "InlineRunner",
    "CeleryRunner",
    "get_runner",
    "set_runner",
    "TaskResult",
    "TASK_INGEST_DOCUMENT",
    "TASK_FINALIZE_CALL_SUMMARY",
    "TASK_CAMPAIGN_DIALER_SWEEP",
]
