"""Current-version-per-id selection (R5). Pure — "today" is injectable."""

from collections.abc import Iterable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.domain.retrieval.fragment import Fragment

CLINIC_TZ = ZoneInfo("Europe/Madrid")


def madrid_today(now: datetime | None = None) -> date:
    """Today's date in the clinic's timezone; `now` must be timezone-aware if given."""
    return (now or datetime.now(CLINIC_TZ)).astimezone(CLINIC_TZ).date()


def select_current_versions(
    fragments: Iterable[Fragment], today: date | None = None
) -> list[Fragment]:
    """Keep, per `source_id`, only fragments of the latest version with vigente_desde <= today.

    Superseded and future-dated versions are dropped; input order is preserved.
    """
    today = today or madrid_today()
    fragments = list(fragments)

    current: dict[str, date] = {}
    for f in fragments:
        if f.vigente_desde <= today and f.vigente_desde > current.get(f.source_id, date.min):
            current[f.source_id] = f.vigente_desde

    return [f for f in fragments if current.get(f.source_id) == f.vigente_desde]
