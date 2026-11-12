"""Alerte Enlèvement : détection dans les titres des médias signataires de la convention.

Le dispositif officiel n'a ni flux ni API ; quand il est déclenché, les médias partenaires doivent diffuser l'alerte
au moins trois heures. L'alerte est considérée en cours quand au moins deux médias différents la titrent dans les
dernières heures, et terminée dès qu'un article annonce sa levée (ou que l'enfant est retrouvé).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import re
from typing import Any

# Médias lus en permanence pour la détection, même s'ils ne sont pas cochés (pas de capteur ni d'onglet)
ALERT_SOURCES = ("franceinfo", "lemonde", "bfmtv", "20minutes", "leparisien")
WINDOW = timedelta(hours=6)
MIN_SOURCES = 2

_ALERT = re.compile(r"alerte[\s\-‑–]*enl[eèé]vement", re.I)
_END = re.compile(r"\blev[ée]e?s?\b|\blev[ée]e de l|retrouv[ée]e?s?|lib[ée]r[ée]e?s?|sains? et saufs?|saine? et sauve|fin de l.alerte", re.I)
# articles de fond sur le dispositif : jamais une alerte en cours
_ABOUT = re.compile(r"\bans du dispositif|anniversaire|\bbilan\b|qu.est.ce que|comment fonctionne|dispositif .{0,20}a \d+ ans", re.I)


def _when(art: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromisoformat(art.get("published") or "")
    except ValueError:
        return None


def detect(feeds: dict[str, dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    """État de l'alerte d'après les articles lus : {"active": bool, ...détails de l'alerte}."""
    now = now or datetime.now(UTC)
    since = now - WINDOW
    hits: list[tuple[datetime, str, dict[str, Any]]] = []
    ends: list[datetime] = []
    for key, feed in feeds.items():
        for art in feed.get("articles", []):
            title = art.get("title") or ""
            when = _when(art)
            if not when or when < since or when > now + timedelta(minutes=30) or not _ALERT.search(title):
                continue
            if _ABOUT.search(title):
                continue
            if _END.search(title):
                ends.append(when)
            else:
                hits.append((when, key, {**art, "source_name": feed.get("name", key)}))
    sources = {key for _, key, _ in hits}
    if len(sources) < MIN_SOURCES:
        return {"active": False}
    start = min(w for w, _, _ in hits)
    if any(e >= start for e in ends):
        return {"active": False, "ended": max(ends).isoformat()}
    # article le plus complet pour la fenêtre : photo et résumé d'abord, puis le plus récent
    best = max(hits, key=lambda h: (bool(h[2].get("image")), bool(h[2].get("summary")), h[0]))[2]
    first = min(hits, key=lambda h: h[0])[2]
    return {
        "active": True,
        "id": hashlib.sha1(f"{start.isoformat()}|{first.get('title')}".encode()).hexdigest()[:12],
        "since": start.isoformat(),
        "title": best.get("title"),
        "summary": best.get("summary"),
        "image": best.get("image"),
        "url": best.get("url"),
        "source": best.get("source_name"),
        "sources": sorted({h[2]["source_name"] for h in hits}),
    }
