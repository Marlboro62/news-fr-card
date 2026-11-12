"""Paramétrage, capteurs et panne d'un flux (sites simulés)."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.news_fr.const import CONF_CUSTOM, CONF_ITEMS, CONF_SCAN_MINUTES, CONF_SOURCES, DOMAIN, SOURCES

from .test_feed import RSS

EMPTY = b'<?xml version="1.0"?><rss version="2.0"><channel><title>Vide</title></channel></rss>'


def mock_rest(aioclient_mock):
    """Autres flux (dont ceux lus pour l'Alerte Enlèvement) : vides. Les flux simulés avant restent prioritaires."""
    for src in SOURCES.values():
        aioclient_mock.get(src["url"], content=EMPTY)


OPTS = {CONF_SOURCES: ["lemonde", "bfmtv"], CONF_CUSTOM: "", CONF_ITEMS: 20, CONF_SCAN_MINUTES: 15}


async def test_parametrage(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(SOURCES["lemonde"]["url"], content=RSS)
    aioclient_mock.get(SOURCES["bfmtv"]["url"], content=RSS)
    mock_rest(aioclient_mock)
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
    alert = [s for s in hass.states.async_all("binary_sensor")]
    assert len(alert) == 1 and alert[0].state == "off"


async def test_un_flux_en_panne(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(SOURCES["lemonde"]["url"], content=RSS)
    aioclient_mock.get(SOURCES["bfmtv"]["url"], status=503)
    mock_rest(aioclient_mock)
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
    mock_rest(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, title="Actualités France", options=OPTS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.config_entries.async_update_entry(entry, options={**OPTS, CONF_SOURCES: ["lemonde"]})
    await hass.async_block_till_done()
    reg = er.async_get(hass)
    assert len(er.async_entries_for_config_entry(reg, entry.entry_id)) == 1


async def test_gros_flux_lu_en_entier(hass: HomeAssistant, aioclient_mock):
    """Flux de plusieurs centaines de Ko : lu jusqu'au bout (un seul read() pouvait le tronquer)."""
    items = "".join(
        f"<item><title>Titre {i}</title><link>https://exemple.fr/{i}</link><description>{'x' * 900}</description>"
        f"<pubDate>Wed, 11 Nov 2026 18:{i % 60:02d}:00 +0100</pubDate></item>"
        for i in range(400)
    )
    big = f'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>{items}</channel></rss>'.encode()
    aioclient_mock.get(SOURCES["lemonde"]["url"], content=big)
    mock_rest(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, title="Actualités France", options={**OPTS, CONF_SOURCES: ["lemonde"]})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    st = hass.states.get("sensor.actualites_france_le_monde")
    assert st.state == "20" and not st.attributes["error"]
