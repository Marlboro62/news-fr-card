"""Lecture des flux : RSS 2.0, Atom et plan du site Google Actualités (bibliothèque standard seulement)."""
from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import hashlib
import html
import re
from typing import Any
import xml.etree.ElementTree as ET

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


def _date(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        when = parsedate_to_datetime(value)  # RSS : « Wed, 11 Nov 2026 18:00:00 +0100 »
    except (TypeError, ValueError, IndexError):
        try:
            when = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Atom, Google Actualités
        except ValueError:
            return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.isoformat()


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
    guid = (_first(kids, "guid", "id") or url).strip()
    return {
        "id": hashlib.sha1(guid.encode()).hexdigest()[:12],
        "title": title,
        "url": url,
        "summary": summary if summary != title else "",
        "image": _image(item, kids, raw_summary),
        "published": published,
        "author": _text(_first(kids, "creator", "author"), 80) or None,
    }


def parse_feed(data: bytes, limit: int) -> list[dict[str, Any]]:
    """Articles du flux, du plus récent au plus ancien. ValueError si le flux est illisible."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as err:
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
    out = [a for a in (_article(i) for i in items) if a]
    out.sort(key=lambda a: a["published"] or "", reverse=True)
    return out[:limit]


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
