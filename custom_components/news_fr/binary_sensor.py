"""Capteur « Alerte enlèvement » : actif tant qu'une alerte est diffusée par les médias signataires."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NewsConfigEntry
from .coordinator import NewsCoordinator
from .sensor import device_info


async def async_setup_entry(hass: HomeAssistant, entry: NewsConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([KidnapAlertSensor(entry.runtime_data)])


class KidnapAlertSensor(CoordinatorEntity[NewsCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "kidnap_alert"
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _unrecorded_attributes = frozenset({"summary", "image", "url", "sources", "alert_id"})

    def __init__(self, coordinator: NewsCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_kidnap_alert"
        self._attr_device_info = device_info(entry)

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.alert.get("active"))

    @property
    def icon(self) -> str:
        return "mdi:account-alert" if self.is_on else "mdi:account-check-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        a = self.coordinator.alert
        if not a.get("active"):
            return {"ended": a.get("ended")}
        return {
            "alert_id": a.get("id"),
            "since": a.get("since"),
            "title": a.get("title"),
            "summary": a.get("summary"),
            "image": a.get("image"),
            "url": a.get("url"),
            "source": a.get("source"),
            "sources": a.get("sources"),
            "phone": "197",
        }
