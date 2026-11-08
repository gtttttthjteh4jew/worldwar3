from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from database.db import SessionLocal
from database.models import Country

LOGGER = logging.getLogger("worldwar3_bot.construction_maintenance")


async def construction_maintenance_worker(app=None):
    """Finalize elapsed building and missile-tech constructions without requiring a user click."""
    await asyncio.sleep(2)
    while True:
        try:
            with SessionLocal() as session:
                from services.game import finalize_construction, finalize_missile_tech_upgrade
                from services.economy import get_missiles_config
                countries = session.scalars(select(Country)).all()
                cfg = get_missiles_config(session) or {}
                for country in countries:
                    completed = finalize_construction(country, session=session)
                    changed = bool(completed)
                    for item in (cfg.get("items", []) or []):
                        mid = item.get("id")
                        if mid is None:
                            continue
                        try:
                            completed, data = finalize_missile_tech_upgrade(session, country.id, str(mid))
                            changed = changed or bool(completed)
                        except Exception:
                            LOGGER.exception("Missile technology finalization failed for country=%s missile=%s", country.id, mid)
                    if changed:
                        session.flush()
                session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Construction maintenance cycle failed")
        await asyncio.sleep(5)
