"""Lecture des flux : RSS, Atom, plan Google Actualités, flux ajoutés à la main."""
import pytest

from custom_components.news_fr.feed import parse_custom, parse_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>Media</title>
<item><title>Ancien titre</title><link>https://exemple.fr/a</link><pubDate>Tue, 10 Nov 2026 08:00:00 +0100</pubDate>
  <description>&lt;p&gt;Un &lt;b&gt;résumé&lt;/b&gt; &amp;amp; du texte&lt;/p&gt;</description>
  <enclosure url="https://exemple.fr/a.jpg" type="image/jpeg" length="1"/></item>
<item><title><![CDATA[Nouveau titre « guillemets »]]></title><link>https://exemple.fr/b</link><guid>b-1</guid>
  <pubDate>Wed, 11 Nov 2026 18:30:00 +0100</pubDate><dc:creator>Alice</dc:creator>
  <description><![CDATA[<img src="https://exemple.fr/b-inline.jpg"> Texte <script>alert(1)</script>]]></description>
  <media:content url="https://exemple.fr/b.jpg" medium="image"/></item>
<item><title>Lien dangereux</title><link>javascript:alert(1)</link></item>
</channel></rss>""".encode()

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>A</title>
<entry><title>Entrée Atom</title><link rel="alternate" href="https://atom.fr/1"/><id>tag:1</id>
<updated>2026-11-11T10:00:00Z</updated><summary>Résumé Atom</summary></entry></feed>""".encode()

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
 xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
<url><loc>https://www.cnews.fr/france/article-1</loc>
<news:news><news:publication><news:name>CNEWS</news:name><news:language>fr</news:language></news:publication>
<news:publication_date>2026-11-11T19:00:00+01:00</news:publication_date><news:title>Titre CNews</news:title></news:news>
<image:image><image:loc>https://static.cnews.fr/img.jpg</image:loc></image:image></url></urlset>""".encode()


def test_rss():
    arts = parse_feed(RSS, 10)
    assert [a["title"] for a in arts] == ["Nouveau titre « guillemets »", "Ancien titre"]
    new, old = arts
    assert new["image"] == "https://exemple.fr/b.jpg" and new["author"] == "Alice"
    assert "<" not in new["summary"] and "script" not in new["summary"]
    assert new["published"].startswith("2026-11-11T17:30:00")
    assert old["summary"] == "Un résumé & du texte" and old["image"] == "https://exemple.fr/a.jpg"
    assert parse_feed(RSS, 1)[0]["title"] == "Nouveau titre « guillemets »"


def test_atom_et_plan_google():
    (a,) = parse_feed(ATOM, 5)
    assert a["url"] == "https://atom.fr/1" and a["summary"] == "Résumé Atom"
    (c,) = parse_feed(SITEMAP, 5)
    assert c["title"] == "Titre CNews" and c["url"].endswith("article-1")
    assert c["image"] == "https://static.cnews.fr/img.jpg" and c["summary"] == ""
    assert c["published"].startswith("2026-11-11T18:00:00")


def test_flux_illisible():
    with pytest.raises(ValueError):
        parse_feed(b"<html><body>erreur</body></html>", 5)
    with pytest.raises(ValueError):
        parse_feed(b"pas du xml", 5)


def test_flux_perso():
    out = parse_custom("Mon journal | https://journal.fr/rss\nmauvaise ligne\nX | ftp://non")
    assert [v["name"] for v in out.values()] == ["Mon journal"]


def test_dates():
    from custom_components.news_fr.feed import _date
    assert _date("Wed, 11 Nov 2026 18:30:00 +0100") == "2026-11-11T17:30:00+00:00"
    assert _date("2026-11-11 18:30:00") == "2026-11-11T17:30:00+00:00"  # sans fuseau : heure de Paris
    assert _date("mer., 11 nov. 2026 18:30:00") == "2026-11-11T17:30:00+00:00"
    assert _date("11 novembre 2026 à 18h30") == "2026-11-11T17:30:00+00:00"
    assert _date("pas une date") is None
