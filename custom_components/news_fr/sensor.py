"""Un capteur par média : nombre d'articles lus, articles en attributs pour la carte."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NewsConfigEntry
from .const import DOMAIN, NAME, VERSION
from .coordinator import NewsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: NewsConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    wanted = {f"{entry.entry_id}_{key}" for key in coordinator.sources}
    # média retiré dans les options : son capteur est supprimé au lieu de rester « indisponible »
    reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        if ent.domain == "sensor" and ent.unique_id not in wanted:
            reg.async_remove(ent.entity_id)
    async_add_entities(NewsSensor(coordinator, key) for key in coordinator.sources)


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or NAME,
        manufacturer="Marlboro62 (non officiel)",
        model="Flux RSS des médias français",
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
    )


class NewsSensor(CoordinatorEntity[NewsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:newspaper-variant-outline"
    _attr_native_unit_of_measurement = "articles"
    # articles destinés à la carte : pas d'historique dans la base de Home Assistant
    _unrecorded_attributes = frozenset({"articles", "site", "error"})

    def __init__(self, coordinator: NewsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = coordinator.sources[key]["name"]
        self._attr_device_info = device_info(entry)

    @property
    def _data(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self._key, {})

    @property
    def native_value(self) -> int:
        return len(self._data.get("articles", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self._data
        return {
            "source": self._key,
            "site": d.get("site"),
            "updated": d.get("updated"),
            "error": d.get("error"),
            "articles": d.get("articles", []),
        }
