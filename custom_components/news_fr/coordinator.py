"""Lecture périodique des flux : un appel par média, en parallèle, avec ETag / Last-Modified."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CUSTOM,
    CONF_ITEMS,
    CONF_SCAN_MINUTES,
    CONF_SOURCES,
    DEFAULT_ITEMS,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_SOURCES,
    DOMAIN,
    MIN_SCAN_MINUTES,
    SOURCES,
    VERSION,
)
from .feed import parse_custom, parse_feed

_LOGGER = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=20)
MAX_BYTES = 5 * 1024 * 1024
HEADERS = {
    "User-Agent": f"Mozilla/5.0 (compatible; HomeAssistant-news_fr/{VERSION})",
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
}


def entry_sources(entry: ConfigEntry) -> dict[str, dict[str, str]]:
    """Médias suivis : ceux cochés dans la liste, puis les flux ajoutés à la main."""
    opts = {**entry.data, **entry.options}
    chosen = {k: SOURCES[k] for k in opts.get(CONF_SOURCES, DEFAULT_SOURCES) if k in SOURCES}
    return {**chosen, **parse_custom(opts.get(CONF_CUSTOM))}


class NewsCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        opts = {**entry.data, **entry.options}
        minutes = max(MIN_SCAN_MINUTES, int(opts.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)))
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(minutes=minutes))
        self.sources = entry_sources(entry)
        self.items = int(opts.get(CONF_ITEMS, DEFAULT_ITEMS))
        self._session = async_get_clientsession(hass)
        self._cache: dict[str, dict[str, Any]] = {}  # dernier résultat lu, gardé si un flux est en panne
        self._etag: dict[str, tuple[str | None, str | None]] = {}

    async def _fetch(self, key: str, src: dict[str, str]) -> dict[str, Any]:
        prev = self._cache.get(key, {})
        headers = dict(HEADERS)
        etag, modified = self._etag.get(key, (None, None))
        if prev.get("articles") and etag:
            headers["If-None-Match"] = etag
        if prev.get("articles") and modified:
            headers["If-Modified-Since"] = modified
        result = {"name": src["name"], "site": src["site"], "articles": prev.get("articles", []), "error": None,
                  "checked": datetime.now(UTC).isoformat(), "updated": prev.get("updated")}
        try:
            async with self._session.get(src["url"], headers=headers, timeout=TIMEOUT, allow_redirects=True) as resp:
                if resp.status == 304:
                    return result
                if resp.status >= 400:
                    raise ValueError(f"le site répond {resp.status}")
                data = await resp.content.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("flux trop volumineux")
                articles = await self.hass.async_add_executor_job(parse_feed, data, self.items)
                self._etag[key] = (resp.headers.get("ETag"), resp.headers.get("Last-Modified"))
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            result["error"] = str(err) or type(err).__name__
            _LOGGER.warning("Flux %s (%s) : %s", src["name"], src["url"], result["error"])
            return result
        result["articles"] = articles
        result["updated"] = result["checked"]
        return result

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        keys = list(self.sources)
        results = await asyncio.gather(*(self._fetch(k, self.sources[k]) for k in keys))
        self._cache = dict(zip(keys, results, strict=True))
        if keys and all(r["error"] and not r["articles"] for r in results):
            raise UpdateFailed("aucun flux lisible : " + " ; ".join(f"{r['name']} : {r['error']}" for r in results))
        return self._cache
