#!/usr/bin/env python3
"""Erzeugt die Unterseiten des neuen Designs unter /neu/ aus den bestehenden Seiten.

Aufruf im Repo-Hauptordner:  python3 werkzeuge/neu_seiten.py

Gelesen werden seiten/*.html, spielbericht-erfurt.html und newsletter.html.
Übernommen werden Titel, Beschreibung, Kopf (Rubrik, Überschrift, Datum, Bild)
und der Inhalt; Kopfleiste, Fuß und Gestaltung kommen aus dem neuen Design.
Nach Änderungen an den alten Seiten das Skript einfach erneut laufen lassen.
"""
import glob
import html
import os
import re

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(WURZEL)

# Seiten, die es im neuen Design auf oberster Ebene gibt
NEU_OBEN = ("index.html", "spielbericht-erfurt.html", "newsletter.html")

NAV = [
    ("seiten/termine.html", "Termine"),
    ("seiten/news.html", "News"),
    ("seiten/fussball.html", "Teams"),
    ("seiten/verein.html", "Verein"),
    ("seiten/sponsoren.html", "Partner"),
    ("seiten/fanshop.html", "Fanshop"),
]
# Welche Unterseiten zu welchem Menüpunkt gehören (für die Markierung im Menü)
BEREICH = {
    "seiten/termine.html": ["termine", "spieluebersicht", "spielplan-zweite", "tabelle", "tabelle-zweite", "statistik", "statistik-zweite"],
    "seiten/news.html": ["news", "beitrag-", "stadionheft", "gewinnspiel", "spielbericht"],
    "seiten/fussball.html": ["fussball", "herren", "erste-mannschaft", "zweite-mannschaft", "alte-herren", "nachwuchs", "u1", "e1", "e2", "f1", "f2", "bambini", "grundlagenausbildung", "leistungsfoerderung", "konzeptpapier"],
    "seiten/verein.html": ["verein", "geschichte", "vorstand", "satzung", "sportstaetten", "mitglied", "abteilungen", "tennis", "volleyball", "tischtennis", "radsport", "breitensport", "reha-sport", "yoga", "wandern", "dart", "kurstadtlauf", "datenschutz"],
    "seiten/sponsoren.html": ["sponsoren"],
    "seiten/fanshop.html": ["fanshop"],
}


def kopfleiste(p, aktiv=None):
    links = []
    for ziel, text in NAV:
        cur = ' aria-current="page"' if ziel == aktiv else ""
        links.append(f'    <a href="{p}{ziel}"{cur}>{text}</a>')
    return f"""<header class="leiste">
  <a class="wappen" href="{p}./" aria-label="1. SC 1911 Heiligenstadt, Startseite"><img src="{p}../assets/logo.png" alt="" width="827" height="945"></a>
  <nav class="nav" id="nav" aria-label="Hauptnavigation">
{chr(10).join(links)}
  </nav>
  <a class="leiste-cta" href="{p}seiten/mitglied-werden.html">Mitglied werden</a>
  <button class="menu" type="button" aria-expanded="false" aria-controls="nav">Menü</button>
</header>"""


def fuss(p):
    return f"""<footer class="fuss">
  <div class="fuss-post">
    <p>Spieltage, Termine und Neues aus dem Nachwuchs per E-Mail.</p>
    <a class="knopf knopf-hell" href="{p}newsletter.html">Newsletter abonnieren</a>
  </div>
  <div class="fuss-raster">
    <div>
      <h2>1. SC 1911 Heiligenstadt e. V.</h2>
      <p>Leineberg 2<br>37308 Heilbad Heiligenstadt</p>
      <p><a href="tel:+493606612206">03606 612206</a><br><a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a></p>
      <p>Geschäftsstelle Dienstag und Donnerstag 17 bis 19 Uhr</p>
    </div>
    <div>
      <h2>Vorstand</h2>
      <dl>
        <dt>Präsident</dt><dd>Thadäus König</dd>
        <dt>Vizepräsidenten</dt><dd>Manuel Lubojanski, Christoph Rodenstock</dd>
        <dt>Schatzmeister</dt><dd>Sebastian Möhlhenrich</dd>
        <dt>Kommunikation und Medien</dt><dd>Michael Apel</dd>
        <dt>Geschäftsstelle</dt><dd>Uwe Meinold</dd>
      </dl>
    </div>
    <div>
      <h2>Folgen</h2>
      <p><a href="https://www.instagram.com/sc1911heiligenstadt/">Instagram</a><br><a href="https://www.facebook.com/1-SC-1911-Heiligenstadt-News-443349765710542/">Facebook</a><br><a href="https://staige.tv/video/563643">Spiele im Livestream</a></p>
    </div>
  </div>
  <p class="fuss-jahr" aria-hidden="true">1911</p>
  <p class="fuss-recht"><span>© 1. SC 1911 Heiligenstadt e. V.</span><a href="https://www.sc1911-heiligenstadt.de/impressum-2/">Impressum</a><a href="{p}seiten/datenschutz.html">Datenschutz</a></p>
</footer>"""


def seite(p, titel, beschreibung, aktiv, kopf, inhalt, skripte):
    skr = "".join(f'<script src="{s}" defer></script>\n' for s in skripte)
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{titel}</title>
<meta name="description" content="{beschreibung}">
<meta name="theme-color" content="#1b2d4f">
<link rel="icon" type="image/png" sizes="32x32" href="{p}../favicon-32.png">
<link rel="apple-touch-icon" href="{p}../apple-touch-icon.png">
<link rel="preload" href="{p}fonts/archivo-latin-wdth-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{p}neu.css?v=3">
<link rel="stylesheet" href="{p}seite.css?v=1">
</head>
<body class="unterseite">
<a class="skip" href="#inhalt">Zum Inhalt springen</a>

{kopfleiste(p, aktiv)}

<main id="inhalt">
{kopf}
{inhalt}
</main>

{fuss(p)}

<script src="{p}neu.js?v=3" defer></script>
{skr}</body>
</html>
"""


def seitenkopf(rubrik, h1, datum, bild, bild_alt=""):
    datum_html = f'<p class="seitenkopf-datum">{datum}</p>' if datum else ""
    rubrik_html = f'<p class="seitenkopf-rubrik">{rubrik}</p>' if rubrik else ""
    bild_html = ""
    if bild:
        bild_html = f'\n  <figure class="seitenkopf-bild"><img src="{bild}" alt="{bild_alt}"></figure>'
    klasse = "seitenkopf mit-bild" if bild else "seitenkopf"
    return f"""<section class="{klasse}">
  <div class="seitenkopf-text">
    {rubrik_html}
    <h1>{h1}</h1>
    {datum_html}
  </div>{bild_html}
</section>"""


def titel_schreibweise(text):
    """Überschriften, die komplett in Großbuchstaben kommen, in normale Schreibung bringen."""
    roh = html.unescape(text)
    buchst = [c for c in roh if c.isalpha()]
    if buchst and sum(c.isupper() for c in buchst) / len(buchst) > 0.8 and len(buchst) > 4:
        klein = roh.lower()
        woerter = []
        for w in klein.split(" "):
            woerter.append(w[:1].upper() + w[1:] if w else w)
        # Kleine Füllwörter wieder klein
        satz = " ".join(woerter)
        for kw in [" Am ", " Im ", " Gegen ", " Und ", " Der ", " Die ", " Das ", " In ", " Zum ", " Zur "]:
            satz = satz.replace(kw, kw.lower())
        satz = re.sub(r"\bSch\b", "SCH", satz)
        satz = re.sub(r"\bIi\b", "II", satz)
        satz = satz[:1].upper() + satz[1:]
        return html.escape(satz, quote=False)
    return text


def pfade_unterseite(t):
    """Pfade aus seiten/*.html für neu/seiten/*.html umschreiben."""
    def ersetze(m):
        attr, ziel = m.group(1), m.group(2)
        if ziel.split("#")[0] in NEU_OBEN:
            return f'{attr}="../{ziel}'
        return f'{attr}="../../{ziel}'
    return re.sub(r'(src|href|data-photo|srcset)="\.\./([^"]*)', ersetze, t)


def pfade_oben(t):
    """Pfade aus Seiten der obersten Ebene für neu/*.html umschreiben."""
    t = re.sub(r'(src|href|data-photo)="(assets/|sch-startseite/|favicon|apple-touch)', r'\1="../\2', t)
    return t


def meta(s, name):
    m = re.search(rf'<meta name="{name}" content="([^"]*)"', s)
    return m.group(1) if m else ""


def aktiv_fuer(name):
    for ziel, teile in BEREICH.items():
        if any(name.startswith(t) for t in teile):
            return ziel
    return None


def kopf_aus(main):
    held = re.search(r'<div class="sch-reporthero sp-held">(.*?)</div></div>', main, re.S)
    rubrik = h1 = datum = bild = ""
    if held:
        h = held.group(1)
        m = re.search(r'<img src="([^"]+)"', h)
        bild = m.group(1) if m else ""
        m = re.search(r"<span>(.*?)</span>", h, re.S)
        rubrik = m.group(1).strip() if m else ""
        m = re.search(r"<h1>(.*?)</h1>", h, re.S)
        h1 = m.group(1).strip() if m else ""
        m = re.search(r'<p class="sp-datum">(.*?)</p>', h, re.S)
        datum = m.group(1).strip() if m else ""
    return rubrik, h1, datum, bild


# Bekannte Tippfehler/Testreste in den übernommenen Inhalten
KORREKTUREN = [
    ("Erwachseneshfgiushdfuiehsiushfi<br>", "Erwachsene"),
    ("48 € halbjährlich hhgghhu", "48 € halbjährlich"),
]


def baue_unterseiten():
    os.makedirs("neu/seiten", exist_ok=True)
    anzahl = 0
    for pfad in sorted(glob.glob("seiten/*.html")):
        name = os.path.basename(pfad)
        s = open(pfad, encoding="utf-8").read()
        main = s[s.find("<main"):s.find("</main>")]
        titel = re.search(r"<title>(.*?)</title>", s, re.S).group(1).strip()
        beschreibung = meta(s, "description")
        rubrik, h1, datum, bild = kopf_aus(main)
        h1 = titel_schreibweise(h1)
        if bild.endswith("hero.jpg"):
            bild = ""  # Platzhalter-Stadionbild nicht wiederholen
        bild = pfade_unterseite(f'src="{bild}"')[5:-1] if bild else ""

        a0 = main.find("<article")
        inhalt = main[a0:main.rfind("</article>") + len("</article>")]
        inhalt = inhalt.replace('<article class="sp-inhalt', '<article class="inhalt sp-inhalt', 1)
        # Skripte im Inhalt herauslösen, sie kommen ans Seitenende
        skripte = re.findall(r'<script src="([^"]+)"></script>', inhalt)
        inhalt = re.sub(r'<script src="[^"]+"></script>\s*', "", inhalt)
        for alt, neu in KORREKTUREN:
            inhalt = inhalt.replace(alt, neu)
        inhalt = pfade_unterseite(inhalt)
        skripte = [pfade_unterseite(f'src="{x}"')[5:-1] for x in skripte]
        if 'class="sp-fupa"' in inhalt and "../../fupa.js" not in skripte:
            skripte.append("../../fupa.js")

        kopf = seitenkopf(rubrik, h1, datum, bild)
        out = seite("../", titel, beschreibung, aktiv_fuer(name), kopf, inhalt, skripte)
        open(f"neu/seiten/{name}", "w", encoding="utf-8").write(out)
        anzahl += 1
    return anzahl


def baue_newsletter():
    s = open("newsletter.html", encoding="utf-8").read()
    main = s[s.find("<main"):s.find("</main>")]
    titel = re.search(r"<title>(.*?)</title>", s, re.S).group(1).strip()
    a0 = main.find("<article")
    inhalt = main[a0:main.rfind("</article>") + len("</article>")]
    inhalt = inhalt.replace('<article class="sp-inhalt', '<article class="inhalt sp-inhalt', 1)
    inhalt = pfade_oben(inhalt)
    kopf = seitenkopf("Verein", "Newsletter", "", "")
    out = seite("", titel, meta(s, "description"), None, kopf, inhalt, ["../newsletter.js?v=1"])
    open("neu/newsletter.html", "w", encoding="utf-8").write(out)


def baue_spielbericht():
    s = open("spielbericht-erfurt.html", encoding="utf-8").read()
    main = s[s.find("<main"):s.find("</main>")]
    titel = re.search(r"<title>(.*?)</title>", s, re.S).group(1).strip()
    # Den alten Bildkopf weglassen, der neue Seitenkopf übernimmt
    main = re.sub(r'<div class="sch-reporthero">.*?</div></div>', "", main, count=1, flags=re.S)
    main = main.replace('<main class="sch-report">', '<div class="sch-report inhalt bericht">', 1) + "</div>"
    main = pfade_oben(main)
    kopf = seitenkopf("Thüringer Landespokal, Achtelfinale", "SCH gegen Rot-Weiß Erfurt", "4. Oktober 2026",
                      "../assets/report/46.webp", "Spielszene gegen Rot-Weiß Erfurt")
    out = seite("", titel, meta(s, "description"), "seiten/news.html", kopf, main, ["../sch-startseite/assets/report.js"])
    open("neu/spielbericht-erfurt.html", "w", encoding="utf-8").write(out)


if __name__ == "__main__":
    n = baue_unterseiten()
    baue_newsletter()
    baue_spielbericht()
    print(f"{n} Unterseiten, Newsletter und Spielbericht erzeugt.")
