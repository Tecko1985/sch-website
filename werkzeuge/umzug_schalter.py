#!/usr/bin/env python3
"""Umzugs-Schalter: macht aus der fertig gebauten Vorschau die echte Vereinsseite.

Aufruf (auf eine gebaute Kopie, nie auf das Repo):
    python werkzeuge/umzug_schalter.py _site
    python werkzeuge/umzug_schalter.py _site https://www.sc1911-heiligenstadt.de/

Was er im Ordner ändert:
- noindex raus (Google darf die Seite zeigen) – außer bei Entwürfen (neu/, vorschau/, admin/, umzug.html)
- Adressen der Vorschau (tecko1985.github.io/sch-website/) -> echte Domain, /sch-website/ -> /
- Impressum- und Datenschutz-Links der alten WordPress-Seite -> eigene Seiten
- seiten/datenschutz.html <- seiten/datenschutz-neu.html (Erklärung für den Betrieb bei Hetzner)
- robots.txt und sitemap.xml
Bis zum Umzugstag bleibt alles wie es ist; die Vorschau auf GitHub Pages läuft unverändert weiter.
Am Umzugstag zusätzlich im Worker NL_SEITE_URL auf die neue newsletter.html umstellen.
"""
import datetime
import os
import re
import shutil
import sys
import urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORSCHAU = "https://tecko1985.github.io/sch-website/"
ALT = "https://www.sc1911-heiligenstadt.de/"
ENTWUERFE = ("neu/", "vorschau/", "admin/", "umzug.html")
# Art.-13-Hinweis auf newsletter.html: in der Vorschau GitHub Pages, auf der echten Seite Hetzner
# (Gesamtprüfung 18.11.2026: live stand noch der GitHub-Satz, obwohl Apache bei Hetzner ausliefert).
NL_GITHUB = ("Diese Seite selbst wird über GitHub Pages ausgeliefert, einen Dienst der GitHub B.V. (Teil von "
             "Microsoft): Dein Browser schickt dabei technisch notwendige Daten an GitHub, insbesondere deine "
             "IP-Adresse; GitHub speichert IP-Adressen von Besuchern nach eigenen Angaben zu Sicherheitszwecken, "
             "eine Übermittlung in Länder außerhalb der EU ist auch hier nicht ausgeschlossen.")
NL_HETZNER = ("Diese Seite selbst liegt auf einem Webserver der Hetzner Online GmbH, Industriestr. 25, "
              "91710 Gunzenhausen, in Deutschland, die für uns als Auftragsverarbeiter nach Art. 28 DSGVO arbeitet: "
              "Dein Browser schickt dabei technisch notwendige Daten an den Server, insbesondere deine IP-Adresse; "
              "der Server speichert sie für begrenzte Zeit in Protokolldateien.")
TEXTDATEIEN = (".html", ".js", ".css", ".xml", ".json", ".txt", ".webmanifest")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ziel = os.path.abspath(sys.argv[1])
    domain = (sys.argv[2] if len(sys.argv) > 2 else ALT).rstrip("/") + "/"
    basis = urllib.parse.urlparse(domain).path or "/"  # "/" bzw. "/neu-probe/" bei der Generalprobe
    if ziel == REPO:
        sys.exit("Nicht auf das Repo anwenden – nur auf eine gebaute Kopie (z. B. _site).")
    if not os.path.isfile(os.path.join(ziel, "index.html")):
        sys.exit(f"{ziel}: keine index.html – ist das die gebaute Seite?")

    neu_ds = os.path.join(ziel, "seiten", "datenschutz-neu.html")
    if os.path.isfile(neu_ds):
        shutil.copyfile(neu_ds, os.path.join(ziel, "seiten", "datenschutz.html"))
        os.remove(neu_ds)

    nl = os.path.join(ziel, "newsletter.html")
    if os.path.isfile(nl):
        text = open(nl, encoding="utf-8").read()
        if NL_GITHUB in text:
            open(nl, "w", encoding="utf-8", newline="").write(text.replace(NL_GITHUB, NL_HETZNER))
        elif NL_HETZNER not in text:
            sys.exit("newsletter.html: Hinweis zur Auslieferung (GitHub Pages) nicht gefunden – "
                     "Text geändert? NL_GITHUB in werkzeuge/umzug_schalter.py anpassen.")

    zaehler = {"noindex": 0, "adressen": 0, "rechtliches": 0}
    seiten = []
    for wurzel, ordner, dateien in os.walk(ziel):
        ordner[:] = [o for o in ordner if not o.startswith(".")]
        for name in dateien:
            if not name.endswith(TEXTDATEIEN):
                continue
            pfad = os.path.join(wurzel, name)
            rel = os.path.relpath(pfad, ziel).replace("\\", "/")
            text = open(pfad, encoding="utf-8", errors="surrogateescape").read()
            neu = text
            entwurf = rel.startswith(ENTWUERFE)
            if name.endswith(".html") and not entwurf:
                neu, n = re.subn(r'<meta name="robots" content="noindex">', "", neu)
                zaehler["noindex"] += n
            neu, n = re.subn(re.escape(VORSCHAU), domain, neu)
            zaehler["adressen"] += n
            neu = neu.replace('"/sch-website/', '"' + basis)
            if name.endswith(".html"):
                hoch = os.path.relpath(os.path.join(ziel, "seiten"), wurzel).replace("\\", "/")
                hoch = "" if hoch == "." else hoch + "/"
                for alt, datei in ((ALT + "impressum-2/", "impressum.html"), (ALT + "datenschutz/", "datenschutz.html")):
                    neu, n = re.subn(re.escape(alt), hoch + datei, neu)
                    zaehler["rechtliches"] += n
                if not entwurf and rel != "404.html":
                    seiten.append(rel)
            if neu != text:
                open(pfad, "w", encoding="utf-8", errors="surrogateescape", newline="").write(neu)

    open(os.path.join(ziel, "robots.txt"), "w", encoding="utf-8", newline="\n").write(
        f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /neu/\nDisallow: /vorschau/\n\nSitemap: {domain}sitemap.xml\n")
    heute = datetime.date.today().isoformat()
    eintraege = "".join(
        f"<url><loc>{domain}{'' if s == 'index.html' else s}</loc><lastmod>{heute}</lastmod></url>\n" for s in sorted(seiten))
    open(os.path.join(ziel, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + eintraege + "</urlset>\n")
    print(f"noindex entfernt: {zaehler['noindex']}, Adressen umgestellt: {zaehler['adressen']}, "
          f"Impressum/Datenschutz-Links: {zaehler['rechtliches']}, Sitemap: {len(seiten)} Seiten")


if __name__ == "__main__":
    main()
