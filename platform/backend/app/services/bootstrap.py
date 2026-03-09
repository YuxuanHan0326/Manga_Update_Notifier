from __future__ import annotations

from sqlalchemy.orm import Session

from ..adapters.registry import list_adapters
from ..models import Source


def bootstrap_sources(db: Session) -> None:
    # Idempotent bootstrap so app restart does not duplicate source rows.
    for adapter in list_adapters():
        row = db.query(Source).filter(Source.code == adapter.code).one_or_none()
        if row is None:
            db.add(Source(code=adapter.code, enabled=True, config_json="{}"))
    db.commit()
