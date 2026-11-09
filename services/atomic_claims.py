from sqlalchemy import text


def claim_once(session, key: str, value: str = "1") -> bool:
    """Atomically claim a unique bot-setting key (SQLite-safe).

    Returns True only for the transaction that created the key. The insert is
    part of the caller's transaction, so a rollback releases the claim.
    """
    result = session.execute(
        text("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (:key, :value)"),
        {"key": str(key), "value": str(value)},
    )
    session.flush()
    return bool(result.rowcount == 1)
