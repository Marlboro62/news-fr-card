"""Paramétrage : médias suivis, flux ajoutés à la main, nombre d'articles, fréquence de lecture."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CUSTOM,
    CONF_ITEMS,
    CONF_SCAN_MINUTES,
    CONF_SOURCES,
    DEFAULT_ITEMS,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_SOURCES,
    DOMAIN,
    MAX_ITEMS,
    MIN_ITEMS,
    MIN_SCAN_MINUTES,
    NAME,
    SOURCES,
)
from .feed import parse_custom


def _schema(values: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_SOURCES, default=values.get(CONF_SOURCES, DEFAULT_SOURCES)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[selector.SelectOptionDict(value=k, label=v["name"]) for k, v in SOURCES.items()],
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
        vol.Optional(CONF_CUSTOM, description={"suggested_value": values.get(CONF_CUSTOM, "")}): selector.TextSelector(
            selector.TextSelectorConfig(multiline=True)
        ),
        vol.Required(CONF_ITEMS, default=values.get(CONF_ITEMS, DEFAULT_ITEMS)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=MIN_ITEMS, max=MAX_ITEMS, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_SCAN_MINUTES, default=values.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=MIN_SCAN_MINUTES, max=240, step=5, mode=selector.NumberSelectorMode.BOX,
                                          unit_of_measurement="min")
        ),
    })


def _check(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    data = {
        CONF_SOURCES: [k for k in user_input.get(CONF_SOURCES, []) if k in SOURCES],
        CONF_CUSTOM: (user_input.get(CONF_CUSTOM) or "").strip(),
        CONF_ITEMS: int(user_input.get(CONF_ITEMS, DEFAULT_ITEMS)),
        CONF_SCAN_MINUTES: int(user_input.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)),
    }
    errors: dict[str, str] = {}
    lines = [ln for ln in data[CONF_CUSTOM].splitlines() if ln.strip()]
    if len(parse_custom(data[CONF_CUSTOM])) != len(lines):
        errors[CONF_CUSTOM] = "bad_custom"
    elif not data[CONF_SOURCES] and not lines:
        errors["base"] = "no_source"
    return data, errors


class NewsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _check(user_input)
            if not errors:
                return self.async_create_entry(title=NAME, data={}, options=data)
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NewsOptionsFlow()


class NewsOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _check(user_input)
            if not errors:
                return self.async_create_entry(data=data)
        values = user_input or {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(values), errors=errors)
