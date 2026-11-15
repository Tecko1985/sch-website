#!/usr/bin/env python3
"""Einheitliches Hauptmenü für alle Unterseiten setzen.

Aufruf (im Repo-Ordner):  python3 werkzeuge/menue.py

Ersetzt in seiten/*.html, 404.html, newsletter.html und spielbericht-erfurt.html das Menü
<nav class="sch-reportnav …"> durch die aktuelle Fassung: Bereiche (News … Partner) plus Schnellzugriff
Shop, TV und Kontakt wie auf der Startseite; am Handy und Tablet als Aufklappmenü (☰).
Die Vorlage spielbericht-erfurt.html gibt das Menü an Spielberichte und Spielinfos weiter. Stile: menue.css.
Neue Beiträge übernehmen das Menü aus ihrer Vorlage, das Skript muss also nur nach Änderungen am Menü laufen.
Kann gefahrlos mehrfach laufen.
"""
import glob
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BEREICHE = [("news.html", "News"), ("termine.html", "Termine"), ("abteilungen.html", "Abteilungen"),
            ("fussball.html", "Fußball"), ("nachwuchs.html", "Nachwuchs"), ("verein.html", "Verein"),
            ("sponsoren.html", "Partner")]
SVG = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="{}"/></svg>'
SHOP = SVG.format("m8 3-5 3 3 5 2-1v11h8V10l2 1 3-5-5-3M8 3a4 4 0 0 0 8 0")
TV = SVG.format("M2 4h20v14H2zM8 22h8m-4-4v4m-3-12 7 4-7 4z")
MAIL = SVG.format("M3 5h18v14H3zM3 5l9 8 9-8")
BURGER = ('<svg aria-hidden="true" viewBox="0 0 24 24"><path class="sp-zu" d="M3 6h18M3 12h18M3 18h18"/>'
          '<path class="sp-auf" d="M5 5l14 14M19 5 5 19"/></svg>')
TV_URL = "https://staige.tv/team/6272785350393856"
UMSCHALTEN = ("var o=this.parentNode.classList.toggle('offen');"
              "this.setAttribute('aria-expanded',o);this.setAttribute('aria-label',o?'Menü schließen':'Menü öffnen')")

NAV = re.compile(r'<nav class="sch-reportnav (?:sp-nav|sb-kopfnav)"[^>]*>.*?</nav>(?=\s*<main|\s*<div|\s*<header|\s*<article)', re.S)


def menue(alt, kontakt):
    start = re.search(r'<a[^>]*href="([^"]*)index\.html"', alt).group(1)  # Weg zur Startseite
    news = re.search(r'href="([^"]*)news\.html"', alt).group(1)           # Weg zum Ordner seiten/
    aktiv = re.search(r'href="[^"]*?([a-z0-9-]+\.html)" aria-current="page"', alt)
    aktiv = aktiv.group(1) if aktiv else ""
    markiert = ' aria-current="page"'
    links = "".join(f'<a href="{news}{d}"{markiert if d == aktiv else ""}>{t}</a>' for d, t in BEREICHE)
    werkzeuge = (f'<i class="sp-trenner" aria-hidden="true"></i>'
                 f'<a class="sp-tool" href="{news}fanshop.html">{SHOP}<span>Shop</span></a>'
                 f'<a class="sp-tool" href="{TV_URL}" rel="noopener">{TV}<span>TV</span></a>'
                 f'<a class="sp-tool" href="{kontakt}">{MAIL}<span>Kontakt</span></a>')
    return (f'<nav class="sch-reportnav sp-nav" aria-label="Hauptmenü">'
            f'<a class="sp-marke" href="{start}index.html"><img src="{start}sch-startseite/assets/logo.png" alt="SCH">'
            f'<span>1. SC 1911 HEILIGENSTADT</span></a>'
            f'<div class="sp-links" id="sp-menue">{links}{werkzeuge}</div>'
            f'<button class="sp-menueknopf" type="button" aria-expanded="false" aria-controls="sp-menue" '
            f'aria-label="Menü öffnen" onclick="{UMSCHALTEN}">{BURGER}<span>Menü</span></button></nav>')


def main():
    dateien = glob.glob(os.path.join(REPO, "seiten/*.html")) + [
        os.path.join(REPO, n) for n in ("404.html", "newsletter.html", "spielbericht-erfurt.html")]
    geaendert = 0
    for pfad in dateien:
        if not os.path.exists(pfad):
            continue
        text = open(pfad, encoding="utf-8").read()
        m = NAV.search(text)
        if not m:
            continue
        kontakt = "#kontakt" if 'id="kontakt"' in text else "mailto:info@sc1911-heiligenstadt.de"
        neu = text[:m.start()] + menue(m.group(0), kontakt) + text[m.end():]
        if neu != text:
            open(pfad, "w", encoding="utf-8").write(neu)
            geaendert += 1
    print(f"Menü in {geaendert} Dateien gesetzt")


if __name__ == "__main__":
    main()
