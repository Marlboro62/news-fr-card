"""Paramétrage, capteurs et panne d'un flux (sites simulés)."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.news_fr.const import CONF_CUSTOM, CONF_ITEMS, CONF_SCAN_MINUTES, CONF_SOURCES, DOMAIN, SOURCES

from .test_feed import RSS

OPTS = {CONF_SOURCES: ["lemonde", "bfmtv"], CONF_CUSTOM: "", CONF_ITEMS: 20, CONF_SCAN_MINUTES: 15}


async def test_parametrage(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(SOURCES["lemonde"]["url"], content=RSS)
    aioclient_mock.get(SOURCES["bfmtv"]["url"], content=RSS)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    bad = await hass.config_entries.flow.async_configure(result["flow_id"], {**OPTS, CONF_CUSTOM: "pas bon"})
    assert bad["errors"] == {CONF_CUSTOM: "bad_custom"}
    none = await hass.config_entries.flow.async_configure(result["flow_id"], {**OPTS, CONF_SOURCES: []})
    assert none["errors"] == {"base": "no_source"}
    done = await hass.config_entries.flow.async_configure(result["flow_id"], OPTS)
    assert done["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    states = [s for s in hass.states.async_all("sensor")]
    assert len(states) == 2
    st = hass.states.get("sensor.actualites_france_le_monde")
    assert st.state == "2" and st.attributes["articles"][0]["title"] == "Nouveau titre « guillemets »"


async def test_un_flux_en_panne(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(SOURCES["lemonde"]["url"], content=RSS)
    aioclient_mock.get(SOURCES["bfmtv"]["url"], status=503)
    entry = MockConfigEntry(domain=DOMAIN, title="Actualités France", options=OPTS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    bfm = hass.states.get("sensor.actualites_france_bfmtv")
    assert bfm.state == "0" and "503" in bfm.attributes["error"]
    assert hass.states.get("sensor.actualites_france_le_monde").state == "2"


async def test_media_retire(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(SOURCES["lemonde"]["url"], content=RSS)
    aioclient_mock.get(SOURCES["bfmtv"]["url"], content=RSS)
    entry = MockConfigEntry(domain=DOMAIN, title="Actualités France", options=OPTS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.config_entries.async_update_entry(entry, options={**OPTS, CONF_SOURCES: ["lemonde"]})
    await hass.async_block_till_done()
    reg = er.async_get(hass)
    assert len(er.async_entries_for_config_entry(reg, entry.entry_id)) == 1
