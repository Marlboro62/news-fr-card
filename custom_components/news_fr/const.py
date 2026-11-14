"""Constantes de l'intégration Actualités France."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "news_fr"
VERSION: Final = "0.1.3b1"
NAME: Final = "Actualités France"

CONF_SOURCES: Final = "sources"
CONF_CUSTOM: Final = "custom_feeds"
CONF_ITEMS: Final = "items"
CONF_SCAN_MINUTES: Final = "scan_minutes"

DEFAULT_SOURCES: Final = ["lemonde", "bfmtv", "cnews", "leparisien"]
DEFAULT_ITEMS: Final = 20
MIN_ITEMS: Final = 5
MAX_ITEMS: Final = 50
DEFAULT_SCAN_MINUTES: Final = 15
MIN_SCAN_MINUTES: Final = 10

# Médias proposés : flux RSS publics (titres et résumés), l'article reste sur le site du média
SOURCES: Final[dict[str, dict[str, str]]] = {
    "lemonde": {"name": "Le Monde", "url": "https://www.lemonde.fr/rss/une.xml", "site": "https://www.lemonde.fr"},
    "bfmtv": {"name": "BFMTV", "url": "https://www.bfmtv.com/rss/news-24-7/", "site": "https://www.bfmtv.com"},
    # CNews ne publie pas de flux RSS classique : plan du site Google Actualités (titres, sans résumé)
    "cnews": {"name": "CNews", "url": "https://www.cnews.fr/googlenews.xml", "site": "https://www.cnews.fr"},
    "leparisien": {"name": "Le Parisien", "url": "https://feeds.leparisien.fr/leparisien/rss", "site": "https://www.leparisien.fr"},
    "franceinfo": {"name": "franceinfo", "url": "https://www.francetvinfo.fr/titres.rss", "site": "https://www.francetvinfo.fr"},
    "lefigaro": {"name": "Le Figaro", "url": "https://www.lefigaro.fr/rss/figaro_actualites.xml", "site": "https://www.lefigaro.fr"},
    "20minutes": {"name": "20 Minutes", "url": "https://www.20minutes.fr/feeds/rss-une.xml", "site": "https://www.20minutes.fr"},
    "liberation": {
        "name": "Libération",
        "url": "https://www.liberation.fr/arc/outboundfeeds/rss-all/collection/accueil-une/?outputType=xml",
        "site": "https://www.liberation.fr",
    },
    "ouestfrance": {"name": "Ouest-France", "url": "https://www.ouest-france.fr/rss/une", "site": "https://www.ouest-france.fr"},
    "france24": {"name": "France 24", "url": "https://www.france24.com/fr/rss", "site": "https://www.france24.com/fr/"},
}

# Fichier de la carte, servi par Home Assistant et chargé dans l'interface
CARD_URL: Final = f"/{DOMAIN}/news-fr-card.js"
CARD_FILE: Final = "frontend/news-fr-card.js"
