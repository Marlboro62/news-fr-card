"""Lecture des flux : RSS 2.0, Atom et plan du site Google Actualités (bibliothèque standard seulement)."""
from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import hashlib
import html
import re
from typing import Any
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

SUMMARY_MAX = 600
_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")
_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.I)
_LOCAL = re.compile(r"^\{[^}]*\}")


def _local(tag: str) -> str:
    """Nom de balise sans espace de noms (media:content → content)."""
    return _LOCAL.sub("", tag)


def _text(value: str | None, limit: int | None = None) -> str:
    text = _SPACES.sub(" ", html.unescape(_TAGS.sub(" ", value or ""))).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
    return text


def _web(url: str | None) -> str | None:
    """Liens et images : seulement des adresses web (http/https)."""
    url = (url or "").strip()
    return url if url.startswith(("https://", "http://")) else None


_MONTHS = {"janv": 1, "jan": 1, "févr": 2, "fevr": 2, "fév": 2, "feb": 2, "mars": 3, "mar": 3, "avr": 4, "apr": 4, "mai": 5, "may": 5,
           "juin": 6, "jun": 6, "juil": 7, "jul": 7, "août": 8, "aout": 8, "aug": 8, "sept": 9, "sep": 9, "oct": 10,
           "nov": 11, "déc": 12, "dec": 12}
_LOOSE = re.compile(r"(\d{1,2})\s+([a-zéû]+)\.?\s+(\d{4})(?:\s+(?:à\s+)?(\d{1,2})[:h](\d{2})(?::(\d{2}))?)?", re.I)


def _date(value: str | None) -> str | None:
    """Date de l'article : RSS (RFC 822), ISO 8601 (Atom, Google Actualités) ou date en toutes lettres (« 11 nov. 2026 18:30 »)."""
    value = (value or "").strip()
    if not value:
        return None
    when = None
    try:
        when = parsedate_to_datetime(value)  # « Wed, 11 Nov 2026 18:00:00 +0100 »
    except (TypeError, ValueError, IndexError):
        pass
    if when is None:
        try:
            when = datetime.fromisoformat(value.replace("Z", "+00:00"))  # « 2026-11-11T18:00:00+01:00 », « 2026-11-11 18:00:00 »
        except ValueError:
            pass
    if when is None and (m := _LOOSE.search(value)):
        name = m.group(2).lower()
        month = next((v for k, v in sorted(_MONTHS.items(), key=lambda kv: -len(kv[0])) if name.startswith(k)), None)
        if month:
            try:
                when = datetime(int(m.group(3)), month, int(m.group(1)), int(m.group(4) or 0), int(m.group(5) or 0),
                                int(m.group(6) or 0), tzinfo=ZoneInfo("Europe/Paris"))
            except ValueError:
                when = None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=ZoneInfo("Europe/Paris"))  # médias français : heure de Paris
    return when.astimezone(UTC).isoformat()  # en UTC : les dates se comparent et se trient telles quelles


_URL_DAY = re.compile(r"[/-](\d{2})-(\d{2})-(\d{4})(?=[/-])")


def _url_day(url: str) -> str | None:
    """Jour de publication inscrit dans l'adresse (Le Parisien : « …-12-11-2026-ID.php »), à défaut de date dans le flux."""
    if m := _URL_DAY.search(url):
        try:
            day = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=ZoneInfo("Europe/Paris"))
        except ValueError:
            return None
        return day.astimezone(UTC).isoformat()
    return None


def _children(node: ET.Element) -> dict[str, list[ET.Element]]:
    out: dict[str, list[ET.Element]] = {}
    for child in node:
        out.setdefault(_local(child.tag), []).append(child)
    return out


def _first(kids: dict[str, list[ET.Element]], *names: str) -> str | None:
    for name in names:
        for el in kids.get(name, []):
            if el.text and el.text.strip():
                return el.text
    return None


def _image(item: ET.Element, kids: dict[str, list[ET.Element]], raw_summary: str | None) -> str | None:
    for el in kids.get("enclosure", []):  # RSS : <enclosure url=… type="image/jpeg">
        if (el.get("type") or "image").startswith("image") and _web(el.get("url")):
            return _web(el.get("url"))
    for el in item.iter():  # media:content / media:thumbnail (éventuellement dans media:group)
        if el is item:
            continue
        name = _local(el.tag)
        if name == "thumbnail" and _web(el.get("url")):
            return _web(el.get("url"))
        if name == "content" and el.get("url") and (el.get("medium") or el.get("type") or "image").startswith("image"):
            return _web(el.get("url"))
    for el in kids.get("image", []):  # Google Actualités : <image:image><image:loc>
        for sub in el:
            if _local(sub.tag) == "loc" and _web(sub.text):
                return _web(sub.text)
    if raw_summary and (m := _IMG.search(html.unescape(raw_summary))):  # première image du résumé
        return _web(m.group(1))
    return None


def _article(item: ET.Element) -> dict[str, Any] | None:
    kids = _children(item)
    news = kids.get("news", [])
    news_kids = _children(news[0]) if news else {}
    title = _text(_first(kids, "title") or _first(news_kids, "title"), 300)
    url = None
    for el in kids.get("link", []):  # Atom : <link href=… rel="alternate">
        if el.get("href") and (el.get("rel") or "alternate") == "alternate":
            url = _web(el.get("href"))
            break
        if el.text:
            url = _web(el.text)
            break
    url = url or _web(_first(kids, "loc"))
    if not title or not url:
        return None
    raw_summary = _first(kids, "description", "summary", "content")
    summary = _text(raw_summary, SUMMARY_MAX)
    published = _date(_first(kids, "pubDate", "published", "updated", "date") or _first(news_kids, "publication_date"))
    date_only = False
    if not published and (published := _url_day(url)):
        date_only = True  # jour seulement : la carte affiche « aujourd'hui », « hier » ou la date
    guid = (_first(kids, "guid", "id") or url).strip()
    return {
        "id": hashlib.sha1(guid.encode()).hexdigest()[:12],
        "title": title,
        "url": url,
        "summary": summary if summary != title else "",
        "image": _image(item, kids, raw_summary),
        "published": published,
        "date_only": date_only,
        "author": _text(_first(kids, "creator", "author"), 80) or None,
    }


_BARE_AMP = re.compile(rb"&(?!(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#[0-9]{1,7}|#x[0-9a-fA-F]{1,6});)")
_CTRL = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HTML_ENTITY = re.compile(rb"&([a-zA-Z][a-zA-Z0-9]{1,31});")
_XML_ENTITIES = {b"amp", b"lt", b"gt", b"quot", b"apos"}


def _repair(data: bytes) -> bytes:
    """Répare les fautes courantes des flux : « & » non échappé, entités HTML (&nbsp;…), caractères de contrôle."""
    data = _CTRL.sub(b"", data)
    data = _BARE_AMP.sub(b"&amp;", data)

    def entity(m: re.Match[bytes]) -> bytes:
        name = m.group(1)
        if name in _XML_ENTITIES:
            return m.group(0)
        char = html.unescape(f"&{name.decode()};")
        return char.encode("utf-8") if char != f"&{name.decode()};" else b"&amp;" + name + b";"

    return _HTML_ENTITY.sub(entity, data)


def parse_feed(data: bytes, limit: int) -> list[dict[str, Any]]:
    """Articles du flux, du plus récent au plus ancien. ValueError si le flux est illisible."""
    head = data[:512].lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html")) or not head:
        raise ValueError("le site renvoie une page web (ou une page vide) au lieu du flux")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as err:
        # flux mal formé (« & » non échappé, caractère de contrôle) : nouvel essai après réparation
        try:
            root = ET.fromstring(_repair(data))
        except ET.ParseError:
            raise ValueError(f"flux illisible ({err})") from err
    kind = _local(root.tag)
    if kind == "rss":
        items = [el for ch in root if _local(ch.tag) == "channel" for el in ch if _local(el.tag) == "item"]
    elif kind == "RDF":
        items = [el for el in root if _local(el.tag) == "item"]
    elif kind == "feed":
        items = [el for el in root if _local(el.tag) == "entry"]
    elif kind == "urlset":
        items = [el for el in root if _local(el.tag) == "url"]
    else:
        raise ValueError(f"format inconnu ({kind})")
    out = _dedupe([a for a in (_article(i) for i in items) if a])
    out.sort(key=lambda a: a["published"] or "", reverse=True)
    return out[:limit]


def _title_key(title: str) -> str:
    """Titre comparable : sans emoji ni ponctuation en tête, sans casse ni espaces multiples."""
    return _SPACES.sub(" ", re.sub(r"^[^\w«\"']+", "", title, flags=re.U)).strip().casefold()


def _dedupe(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Même titre publié deux fois dans le flux (ex. France 24 : « 🔴 » direct + article) : une seule entrée,
    celle qui a un résumé et une image, à la place de la première."""
    kept: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for art in articles:
        key = _title_key(art["title"])
        if key not in kept:
            kept[key] = len(out)
            out.append(art)
            continue
        cur = out[kept[key]]
        score = lambda a: (bool(a.get("summary")), bool(a.get("image")))  # noqa: E731
        if score(art) > score(cur):
            out[kept[key]] = {**art, "published": cur["published"] or art["published"]}
    return out


def parse_custom(text: str | None) -> dict[str, dict[str, str]]:
    """Flux ajoutés par l'utilisateur : une ligne « Nom | https://adresse-du-flux »."""
    out: dict[str, dict[str, str]] = {}
    for line in (text or "").splitlines():
        if "|" not in line:
            continue
        name, url = (p.strip() for p in line.split("|", 1))
        if name and _web(url):
            key = "perso_" + hashlib.sha1(url.encode()).hexdigest()[:8]
            out[key] = {"name": name[:40], "url": url, "site": url}
    return out
