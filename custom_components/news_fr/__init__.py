"""Actualités France : titres et résumés des flux RSS des médias français, avec leur carte.

Intégration non officielle, sans lien avec les médias cités. Les articles restent sur le site de chaque média.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_COMPONENT_LOADED, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_FILE, CARD_URL, DOMAIN, VERSION
from .coordinator import NewsCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type NewsConfigEntry = ConfigEntry[NewsCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Carte servie par Home Assistant et chargée dans l'interface : aucune ressource à ajouter."""
    if hass.http is None:
        return True
    from homeassistant.components.http import StaticPathConfig

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / CARD_FILE), cache_headers=False)]
    )
    if "frontend" in hass.config.components:
        _add_card(hass)
    else:
        @callback
        def _frontend_loaded(event: Event) -> None:
            if event.data.get("component") == "frontend":
                _add_card(hass)
                unsub()

        unsub = hass.bus.async_listen(EVENT_COMPONENT_LOADED, _frontend_loaded)
    return True


@callback
def _add_card(hass: HomeAssistant) -> None:
    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")


async def async_setup_entry(hass: HomeAssistant, entry: NewsConfigEntry) -> bool:
    coordinator = NewsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _reload(hass: HomeAssistant, entry: NewsConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NewsConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
