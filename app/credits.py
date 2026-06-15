"""Credit-/Kontingent-Modell fuer verkaufte API-Keys.

Keys werden in ``.env`` als ``API_KEYS`` hinterlegt (komma-/whitespace-getrennt,
max. ``MAX_KEYS``). Jeder Key erlaubt ``CREDITS_PER_KEY`` (Default 120) Abfragen;
der Verbrauch wird pro Key in Redis gezaehlt (Schluessel = SHA-256 des Keys, der
Klartext-Key landet also nie in Redis).

Bewusst schlank: kein DB-Schema, keine Migration – ein Solo-tauglicher Mechanismus,
der zum bestehenden Redis (Rate-Limit) passt. Faellt ohne Redis *offen* aus (zaehlt
dann nicht), analog zum Rate-Limiter – eine Redis-Stoerung soll zahlende Kund:innen
nicht aussperren.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re

import ratelimit

_log = logging.getLogger("einvoice.credits")

MAX_KEYS = 100
_SPLIT = re.compile(r"[\s,]+")


def _split(raw: str) -> list[str]:
    return [k for k in _SPLIT.split(raw.strip()) if k]


def _keys() -> list[str]:
    """Gueltige Keys aus der Umgebung – auf MAX_KEYS gedeckelt."""
    return _split(os.environ.get("API_KEYS", ""))[:MAX_KEYS]


def enabled() -> bool:
    """True, sobald mindestens ein Key konfiguriert ist -> API ist abgesichert."""
    return len(_keys()) > 0


def count() -> int:
    return len(_keys())


def limit() -> int:
    return int(os.environ.get("CREDITS_PER_KEY", "120"))


def is_valid(key: str) -> bool:
    return bool(key) and key in set(_keys())


def _counter(key: str) -> str:
    return "credits:" + hashlib.sha256(key.encode()).hexdigest()


async def consume(key: str) -> tuple[bool, int, int]:
    """Eine Abfrage verbuchen. Liefert ``(erlaubt, verbraucht, limit)``.

    Ohne/bei kaputtem Redis: fail-open (erlaubt, Zaehler 0) – nicht abrechenbar,
    aber legitime Nutzung wird nicht blockiert."""
    lim = limit()
    cl = ratelimit.client()
    if cl is None:
        return True, 0, lim
    try:
        used = await cl.incr(_counter(key))
        return used <= lim, int(used), lim
    except Exception as exc:  # pragma: no cover - defensiv
        _log.warning("credit consume failed, allowing: %s", exc)
        return True, 0, lim


async def usage(key: str) -> tuple[int, int]:
    """Aktuellen Verbrauch lesen, ohne zu verbuchen. ``(verbraucht, limit)``."""
    lim = limit()
    cl = ratelimit.client()
    if cl is None:
        return 0, lim
    try:
        v = await cl.get(_counter(key))
        return (int(v) if v else 0), lim
    except Exception as exc:  # pragma: no cover - defensiv
        _log.warning("credit usage read failed: %s", exc)
        return 0, lim


def log_status() -> None:
    """Beim Start: wie viele Keys aktiv sind (und ob welche ueber dem Limit liegen)."""
    provided = len(_split(os.environ.get("API_KEYS", "")))
    if provided == 0:
        return
    msg = f"API_KEYS aktiv: {min(provided, MAX_KEYS)} (je {limit()} Credits)"
    if provided > MAX_KEYS:
        msg += f"; {provided - MAX_KEYS} ueber dem Maximum ({MAX_KEYS}) ignoriert"
    _log.info(msg)
