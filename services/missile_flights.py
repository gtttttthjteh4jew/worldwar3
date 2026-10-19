from __future__ import annotations
import asyncio, json, time, logging
from sqlalchemy import select
from database.db import SessionLocal
from database.models import BotSetting
KEY="missile_flights_v1"
log=logging.getLogger("worldwar3_bot.missiles")
def _load(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key==KEY))
    if not row or not row.value: return {}
    try:
        data=json.loads(row.value); return data if isinstance(data,dict) else {}
    except Exception: return {}
def _save(session,data):
    row=session.scalar(select(BotSetting).where(BotSetting.key==KEY)); raw=json.dumps(data,ensure_ascii=False)
    if row is None: session.add(BotSetting(key=KEY,value=raw))
    else: row.value=raw
def put(session, token, flight):
    data=_load(session); data[str(token)]=flight; _save(session,data)
def get(session, token):
    data=_load(session)
    return data.get(str(token))
def remove(session, token):
    data=_load(session); data.pop(str(token),None); _save(session,data)
def due(session):
    now=time.time(); return [(k,v) for k,v in _load(session).items() if float(v.get("arrival_at",0) or 0)<=now]
async def missile_flight_worker(app):
    await asyncio.sleep(2)
    while True:
        try:
            with SessionLocal() as session: flights=due(session)
            for token,flight in flights:
                try:
                    from handlers.callbacks import _resolve_missile_flight
                    await _resolve_missile_flight(app.bot,flight,None,token)
                finally:
                    with SessionLocal() as session:
                        remove(session,token); session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Persistent missile flight worker error")
        await asyncio.sleep(1)
