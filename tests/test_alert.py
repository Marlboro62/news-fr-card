"""Détection de l'Alerte Enlèvement dans les titres des médias."""
from datetime import UTC, datetime, timedelta

from custom_components.news_fr.alert import detect

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def art(title, minutes, **kw):
    return {"title": title, "published": (NOW - timedelta(minutes=minutes)).isoformat(), "url": "https://x.fr/" + title[:5], **kw}


def feeds(**by_source):
    return {k: {"name": k.capitalize(), "articles": v} for k, v in by_source.items()}


def test_deux_medias_declenchent():
    r = detect(feeds(
        franceinfo=[art("Alerte enlèvement déclenchée dans le Nord pour un garçon de 4 ans", 30)],
        lemonde=[art("Une alerte-enlèvement lancée après la disparition d'un enfant", 20, image="https://x.fr/p.jpg", summary="Signalement")],
    ), NOW)
    assert r["active"] and r["image"] == "https://x.fr/p.jpg" and r["sources"] == ["Franceinfo", "Lemonde"]
    assert r["since"] == (NOW - timedelta(minutes=30)).isoformat()


def test_un_seul_media_ne_suffit_pas():
    assert not detect(feeds(franceinfo=[art("Alerte enlèvement déclenchée", 10), art("Alerte enlèvement : appel à témoins", 5)]), NOW)["active"]


def test_levee_de_l_alerte():
    r = detect(feeds(
        franceinfo=[art("Alerte enlèvement déclenchée", 90), art("Alerte enlèvement levée : l'enfant retrouvé sain et sauf", 10)],
        lemonde=[art("Alerte enlèvement : l'enquête progresse", 60)],
    ), NOW)
    assert not r["active"] and r["ended"]


def test_articles_anciens_et_de_fond_ignores():
    assert not detect(feeds(
        franceinfo=[art("Alerte enlèvement déclenchée", 8 * 60)],
        lemonde=[art("Les 20 ans du dispositif Alerte enlèvement", 10)],
        bfmtv=[art("Qu'est-ce que le dispositif alerte enlèvement ?", 5)],
    ), NOW)["active"]
