#!/usr/bin/env python3
"""Baut Beiträge aus der Redaktionsoberfläche (/admin/) in die Seite ein.

Aufruf:  python3 werkzeuge/beitraege.py ZIELORDNER
(im Pages-Bau: python3 werkzeuge/beitraege.py _site)

Liest inhalte/beitraege/*.json aus dem Repo und schreibt in ZIELORDNER:
- seiten/beitrag-<slug>.html  (eine Seite je Beitrag, im Aufbau der übrigen Beitragsseiten)
- seiten/news.html            (die letzten 20 Beiträge, neueste zuerst, mit Link zum Archiv)
- seiten/archiv.html          (Liste aller Beiträge, neueste zuerst)
- index.html                  (die drei neuesten und „Was läuft weiter beim SCH?“)
- neu/index.html              (News-Schiene im neuen Design)
Die Unterseiten unter neu/ entstehen danach mit werkzeuge/neu_seiten.py.

Das Repo selbst bleibt unverändert: Erzeugt wird nur im Zielordner.
"""
import datetime
import glob
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spielbericht  # noqa: E402  Spielbericht-Seiten im Aufbau von spielbericht-erfurt.html
import spieltag  # noqa: E402
import spiele  # noqa: E402  „Aktuelle Spiele“ auf der Startseite
import spielvorschau  # noqa: E402  Spielinfo-Seiten für kommende Spiele

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORLAGE = "seiten/beitrag-serie-haelt-weiter.html"
SB_VORLAGE = "spielbericht-erfurt.html"  # Rahmen (Kopf, Menü, Fuß) für Beiträge der Rubrik „Spielbericht“
ADRESSE = "https://tecko1985.github.io/sch-website/"

try:
    from PIL import Image
except ImportError:  # Ohne Pillow fehlen nur width/height an den Startseitenbildern
    Image = None


# ---------------------------------------------------------------- Text säubern
ERLAUBT = {"p", "br", "strong", "b", "em", "i", "u", "h2", "h3", "ul", "ol", "li", "a", "blockquote"}
LEER = {"br"}


class Saeuberer(HTMLParser):
    """Lässt nur einfache Textauszeichnung durch; alles andere wird entfernt, Text bleibt."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.aus = []
        self.offen = []
        self.weg = 0  # innerhalb von script/style: Inhalt verwerfen

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "iframe", "object"):
            self.weg += 1
            return
        tag = {"b": "strong", "i": "em", "div": "p", "h1": "h2", "h4": "h3", "h5": "h3", "h6": "h3"}.get(tag, tag)
        if tag not in ERLAUBT:
            return
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            if not re.match(r"^(https?:|mailto:|tel:|#|[a-z0-9./_-]+$)", href, re.I):
                return
            extern = href.startswith("http")
            zusatz = ' rel="noopener"' if extern else ""
            self.aus.append(f'<a href="{html.escape(href, quote=True)}"{zusatz}>')
        else:
            self.aus.append(f"<{tag}>")
        if tag not in LEER:
            self.offen.append(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "iframe", "object"):
            self.weg = max(0, self.weg - 1)
            return
        tag = {"b": "strong", "i": "em", "div": "p", "h1": "h2", "h4": "h3", "h5": "h3", "h6": "h3"}.get(tag, tag)
        if tag in self.offen:
            while self.offen:
                t = self.offen.pop()
                self.aus.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        if self.weg:
            return
        self.aus.append(html.escape(data, quote=False))

    def ergebnis(self):
        while self.offen:
            self.aus.append(f"</{self.offen.pop()}>")
        t = "".join(self.aus)
        t = re.sub(r"<(p|h2|h3|li|blockquote)>(\s|&nbsp;|<br>)*</\1>", "", t)  # leere Blöcke
        t = re.sub(r"(<br>\s*){3,}", "<br><br>", t)
        t = re.sub(r"</(p|h2|h3|ul|ol|blockquote)>\s*", r"</\1>\n", t)
        return t.strip()


ZEILENTRENNER = re.compile("[\\u2028\\u2029]")


def saeubern(roh):
    # Zeilentrenner U+2028/U+2029 (kommen beim Kopieren aus Word/Facebook mit) zeigt kein Browser an:
    # Wörter kleben sonst zusammen („FSV WaltershausenKöllner“). Als echten Zeilenumbruch übernehmen.
    roh = ZEILENTRENNER.sub("<br>", roh or "")
    s = Saeuberer()
    s.feed(roh)
    s.close()
    t = s.ergebnis()
    if t and not t.startswith("<"):
        t = f"<p>{t}</p>"
    return zwischentitel(t)


def zwischentitel(t):
    """Fette Zeile am Absatzanfang (<p><strong>Titel</strong><br>Text</p> oder allein im Absatz) als <h3>.

    So stehen Zwischenüberschriften aus WordPress/Redaktion als echte Überschriften im Beitrag.
    Zitate („…“) und lange fette Sätze bleiben, wie sie sind."""
    def ersetze(m):
        titel = m.group(1).replace(" ", " ").strip()
        rest = (m.group(2) or "").strip()
        if not titel or len(titel) > 110 or titel[0] in "„\"»“'" or titel.endswith((".", "!", "?")) and len(titel) > 70:
            return m.group(0)
        return f"<h3>{titel}</h3>\n" + (f"<p>{rest}</p>" if rest else "")
    return re.sub(r"<p>\s*<strong>([^<]+)(?:<br>\s*)?</strong>\s*(?:<br\s*/?>\s*((?:(?!</p>).)*?))?</p>", ersetze, t, flags=re.S)


def spieldaten_aus_text(d):
    """Spielbericht mit „Spieldaten“ als Fließtext am Ende (Überschrift „Spieldaten“, danach z. B.
    „FSV Waltershausen<br>Köllner - Smudzinski …“, „Schiedsrichter<br>Lenz“): Angaben in die Spieldaten-Felder
    übernehmen und den Block aus dem Text nehmen. So erscheint er im einheitlichen Format
    („Verein: Spieler – Spieler …“, spielbericht.spieldaten). Von Hand ausgefüllte Felder haben Vorrang."""
    m = re.search(r"<h[23]>\s*Spieldaten:?\s*</h[23]>", d["text"])
    if not m:
        return
    rest = d["text"][m.end():]
    sp, gegner = d["spiel"], (d["spiel"].get("gegner") or "").strip().lower()
    erkannt = {}
    # Blöcke: Überschriften und Absätze; „Label<br>Wert“ oder „Label: Wert“
    for block in re.findall(r"<(?:p|h[23])>(.*?)</(?:p|h[23])>", rest, re.S):
        teile = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.split(r"<br\s*/?>", block)]
        teile = [x for x in teile if x]
        if not teile:
            continue
        if len(teile) == 1:
            mm = re.match(r"^([^:]{2,60}):\s*(.+)$", teile[0])
            if not mm:
                continue   # z. B. „FSV Waltershausen - 1. SC 1911 Heiligenstadt“ (Paarung)
            teile = [mm.group(1), mm.group(2)]
        label, wert = teile[0].strip(" :"), " ".join(teile[1:]).strip()
        l = label.lower()
        if l.startswith("schiedsrichter"):
            erkannt["schiedsrichter"] = wert
        elif l.startswith("zuschauer"):
            erkannt["zuschauer"] = wert
        elif l.startswith("trainer"):
            erkannt["trainer"] = wert
        elif l.startswith("tore"):
            erkannt["tore_sch"] = "\n".join(x.strip() for x in re.split(r",\s*(?![^()]*\))", wert) if x.strip())
        elif re.search(r"heiligenstadt|^sch\b", l):
            erkannt["aufstellung_sch"] = re.sub(r"\s+-\s+", " – ", wert)
        elif gegner and (l in gegner or gegner in l or any(w in l for w in gegner.split() if len(w) > 3)):
            erkannt["aufstellung_geg"] = re.sub(r"\s+-\s+", " – ", wert)
    if not erkannt:
        return
    for k, v in erkannt.items():
        if not str(sp.get(k) or "").strip():
            sp[k] = v
    d["text"] = d["text"][:m.start()].rstrip()


# ---------------------------------------------------------------- Hilfen
def datum_de(iso):
    j, m, t = iso.split("-")
    return f"{t}.{m}.{j}"


def kurz(text, n=230):
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + " …"


def masse(ziel, pfad):
    if Image is None:
        return ""
    try:
        with Image.open(os.path.join(ziel, pfad)) as im:
            return f' width="{im.width}" height="{im.height}"'
    except Exception:
        return ""


VORAB_MINUTEN = 40  # so lange vor dem geplanten Termin wird ein Beitrag schon (versteckt) gebaut


def _berlin():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Berlin")
    except Exception:  # ohne Zeitzonendaten: Winterzeit annehmen
        return datetime.timezone(datetime.timedelta(hours=1))


def jetzt_berlin(plus_minuten=0):
    """Aktuelle deutsche Zeit (+ Minuten) als "JJJJ-MM-TTTHH:MM" (der Bau läuft bei GitHub in UTC)."""
    jetzt = datetime.datetime.now(_berlin()) + datetime.timedelta(minutes=plus_minuten)
    return jetzt.strftime("%Y-%m-%dT%H:%M")


def ab_zeit(geplant):
    """ "JJJJ-MM-TTTHH:MM" (deutsche Zeit) -> ISO mit Zeitzone für den Browser"""
    return datetime.datetime.strptime(geplant, "%Y-%m-%dT%H:%M").replace(tzinfo=_berlin()).isoformat()


def vorab_sperre(seite, ab, geplant):
    """Beitragsseite, die sich erst zum geplanten Zeitpunkt selbst zeigt (vorher nur ein Hinweis)."""
    tag, uhr = geplant[8:10] + "." + geplant[5:7] + ".", geplant[11:16]
    kopf = (f'<style>html.vorab-wartet main>*{{display:none!important}}'
            f'html.vorab-wartet main::before{{content:"Dieser Beitrag erscheint am {tag} um {uhr} Uhr.";display:block;'
            f'padding:140px 24px;text-align:center;font:700 22px/1.4 Arial,sans-serif;color:#1b2d4f}}</style>'
            f'<script>(function(){{var ab=Date.parse("{ab}"),h=document.documentElement;if(Date.now()<ab){{h.classList.add("vorab-wartet");'
            f'setTimeout(function(){{h.classList.remove("vorab-wartet")}},ab-Date.now()+50)}}}})();</script>')
    return seite.replace("</head>", kopf + "</head>", 1)


ZUSTAND_SKRIPT = ('<script>(function(){function z(){var n=Date.now(),w=Infinity;'
                  'document.querySelectorAll("[data-ab],[data-bis]").forEach(function(e){'
                  'var a=e.dataset.ab?Date.parse(e.dataset.ab):-Infinity,b=e.dataset.bis?Date.parse(e.dataset.bis):Infinity;'
                  'e.hidden=!(n>=a&&n<b);if(a>n)w=Math.min(w,a);if(b>n)w=Math.min(w,b);});'
                  'if(w<Infinity)setTimeout(z,Math.min(w-n+50,2e9));}z();})();</script>')


def zustand_einbauen(seite):
    """Stil (im Kopf, gegen Aufblitzen) und Skript für Karten mit data-ab/data-bis."""
    stil = "<style>[data-ab][hidden],[data-bis][hidden]{display:none!important}</style>"
    return seite.replace("</head>", stil + "</head>", 1).replace("</body>", ZUSTAND_SKRIPT + "</body>", 1)


def zustaende(liste):
    """[(ab, bis, liste)]: Kartenliste vor und nach jedem geplanten Freischalt-Zeitpunkt (sonst nur eine)."""
    zeiten = sorted({k["ab"] for k in liste if k.get("ab")})
    if not zeiten:
        return [("", "", liste)]
    grenzen = [""] + zeiten + [""]
    return [(grenzen[i], grenzen[i + 1], [k for k in liste if not k.get("ab") or (grenzen[i] and k["ab"] <= grenzen[i])])
            for i in range(len(zeiten) + 1)]


def markiere(karten_html, ab, bis):
    """Karten (oberste <a>/<li>) bekommen data-ab/data-bis; ab in der Zukunft = zunächst versteckt."""
    if not ab and not bis:
        return karten_html
    zusatz = (f' data-ab="{ab}" hidden' if ab else "") + (f' data-bis="{bis}"' if bis else "")
    return re.sub(r'(<a class="(?:sch-post|sch-morecard|sp-karte)"|<li)(?=[ >])', lambda m: m.group(1) + zusatz, karten_html)


def lade_beitraege():
    beitraege = []
    for pfad in sorted(glob.glob(os.path.join(REPO, "inhalte/beitraege/*.json"))):
        try:
            d = json.load(open(pfad, encoding="utf-8"))
        except Exception as e:
            print(f"::warning::{os.path.basename(pfad)} übersprungen: {e}")
            continue
        if d.get("entwurf"):
            continue
        # Geplant: erst ab dem Termin zeigen (deutsche Zeit, "JJJJ-MM-TTTHH:MM"). Liegt der Termin höchstens
        # VORAB_MINUTEN voraus, wird der Beitrag schon gebaut, schaltet sich aber erst zur Sekunde selbst frei
        # (Seite und Karten, siehe vorab_sperre/zustaende) – so wartet niemand auf GitHub.
        d["ab"] = ""
        if d.get("geplant") and str(d["geplant"]) > jetzt_berlin():
            if str(d["geplant"]) > jetzt_berlin(VORAB_MINUTEN):
                print(f"{os.path.basename(pfad)}: geplant für {d['geplant']}, noch nicht gezeigt")
                continue
            d["ab"] = ab_zeit(str(d["geplant"]))
            print(f"{os.path.basename(pfad)}: geplant für {d['geplant']}, vorab gebaut (schaltet sich selbst frei)")
        slug = os.path.basename(pfad)[:-5]
        if not re.match(r"^[a-z0-9-]+$", slug) or not re.match(r"^\d{4}-\d{2}-\d{2}$", d.get("datum", "")):
            print(f"::warning::{slug}: ungültiger Name oder Datum, übersprungen")
            continue
        d["slug"] = slug
        d["seite"] = f"beitrag-{slug}.html"
        d["titel"] = (d.get("titel") or "").strip() or "Ohne Titel"
        d["teaser"] = kurz(d.get("teaser") or d.get("text"), 300)
        d["text"] = saeubern(d.get("text"))
        d["text"] = spieltag.karten(d["text"])  # „Spiele am Wochenende“ als Spielkarten
        d["bild"] = d.get("bild") or ""
        d["galerie"] = [g for g in d.get("galerie", []) if re.match(r"^assets/(?:beitraege|seiten)/[a-z0-9._-]+$", g)]
        if d["bild"] and not re.match(r"^assets/(?:beitraege|seiten)/[a-z0-9._-]+$", d["bild"]):
            d["bild"] = ""
        if not isinstance(d.get("spiel"), dict):
            d["spiel"] = {}
        if d.get("rubrik") == "Spielbericht":
            spieldaten_aus_text(d)
        # Spielbericht ohne eigenes Titelbild: das erste Galeriebild ist Bild 1 (auch für die News-Karte)
        if d.get("rubrik") == "Spielbericht" and not d["bild"] and d["galerie"]:
            d["bild"], d["galerie"] = d["galerie"][0], d["galerie"][1:]
        beitraege.append(d)
    return beitraege


# ---------------------------------------------------------------- Beitragsseite
def baue_seite(ziel, d, vorlage, zusatz="", team=""):
    t = vorlage
    e = lambda s: html.escape(s, quote=True)
    titel = f'{e(d["titel"])} · 1. SC 1911 Heiligenstadt'
    t = re.sub(r"<title>.*?</title>", f"<title>{titel}</title>", t, count=1, flags=re.S)
    t = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + e(d["teaser"]), t, count=1)
    t = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + titel, t, count=1)
    t = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1) + e(d["teaser"]), t, count=1)
    t = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + ADRESSE + "seiten/" + d["seite"], t, count=1)
    og_bild = ADRESSE + d["bild"] if d["bild"] else ADRESSE + "assets/teilen.jpg"
    t = re.sub(r'(<meta property="og:image" content=")[^"]*', lambda m: m.group(1) + og_bild, t, count=1)

    bild = f'<img src="../{d["bild"]}" alt="">' if d["bild"] else '<img src="../assets/hero.jpg" alt="">'
    # sp-kopfbild: Bild ganz und ungeschnitten, Rubrik/Titel/Datum darunter (seiten.css)
    # Neue Beiträge (ab SPONSOREN_AB oder mit neu hochgeladenem Titelbild): SCHeimat-Zeichen unten rechts bei jeder
    # Rubrik, bei Vorberichten zusätzlich die Sponsorenleiste der Mannschaft unten links. Ältere Grafiken haben beides schon.
    # Seit 18.11.2026 setzt werkzeuge/schheimat.py das Zeichen beim Bau ins Bild selbst (auch in Galerien, nur wo es
    # fehlt); deshalb hier keine Einblendung mehr – sonst stünde es doppelt. Vorberichte: Leiste im festen Kopfbild.
    logos = (spielbericht.sponsoren_html(team, "../", marke=False)
             if d.get("rubrik") == "Vorbericht" and spielbericht.leiste_erlaubt(d) else "")
    # Aufbau wie bei Werder Bremen: weißer Kopf mit Rubrik, großer Überschrift, Unterzeile und Datum/Lesezeit,
    # darunter das Titelbild über die ganze Breite (ungeschnitten) mit Bildnachweis, dann der Text
    text = d["text"]
    unterzeile = ""
    m = re.match(r"\s*<h3>(.*?)</h3>\s*", text, re.S)
    if m and len(re.sub(r"<[^>]+>", "", m.group(1))) <= 160:   # erste Zwischenüberschrift wird zur Unterzeile
        unterzeile, text = m.group(1).strip(), text[m.end():]
    woerter = len(re.sub(r"<[^>]+>", " ", text).split())
    minuten = max(1, round(woerter / 200))
    foto = f'<div class="sp-titelfoto-bild">{bild}{logos}</div>' if logos else bild
    held = (f'<header class="sp-kopf2"><span class="sp-rubrik">{e(d.get("rubrik") or "News")}</span>'
            f'<h1>{e(d["titel"])}</h1>' + (f'<p class="sp-unterzeile">{unterzeile}</p>' if unterzeile else "")
            + f'<p class="sp-meta">{datum_de(d["datum"])} | <b>{minuten} Min</b></p></header>'
            f'<figure class="sp-titelfoto">{foto}<figcaption>Foto: SCH</figcaption></figure>')
    inhalt = text + zusatz
    if d["galerie"]:
        inhalt += '\n<div class="sp-galerie">' + "".join(f'<img src="../{g}" alt="" loading="lazy">' for g in d["galerie"]) + "</div>"
    main = f'<main class="sch-report sp-seite sp-neu">{held}<article class="sp-inhalt">\n{inhalt}\n</article>'
    t = re.sub(r'<main class="sch-report sp-seite">.*?</article>', lambda m: main, t, count=1, flags=re.S)
    if d.get("ab"):
        t = vorab_sperre(t, d["ab"], d["geplant"])
    open(os.path.join(ziel, "seiten", d["seite"]), "w", encoding="utf-8").write(t)


def vorbericht_team(d, sb):
    """Mannschaft eines Vorberichts (für die Sponsorenleiste): aus dem zugehörigen Spielbericht, sonst aus der
    Redaktion („Zu welchem Spiel?“), sonst aus dem Text (Liga/Spitzname). Andere Rubriken: keine."""
    if d.get("rubrik") != "Vorbericht":
        return ""
    if sb:
        return (sb.get("spiel") or {}).get("mannschaft") or "m1"
    if (d.get("spiel") or {}).get("mannschaft"):
        return d["spiel"]["mannschaft"]
    text = (d.get("titel") or "") + " " + (d.get("text") or "")
    if re.search(r"(?i)kreisoberliga|reserve|papst-elf|SCH II\b|Heiligenstadt II\b", text):
        return "m2"
    if re.search(r"(?i)thüringenliga|verbandsliga|ludwig-elf", text):
        return "m1"
    return ""


# ---------------------------------------------------------------- Listen
def lies_news(news):
    """Bestehende Karten aus seiten/news.html (alte, eingepflegte Beiträge)."""
    karten = []
    for m in re.finditer(r'<a class="sp-karte" href="([^"]+)">.*?<img src="\.\./([^"]+)".*?<time datetime="([^"]+)">.*?<b>(.*?)</b><span>(.*?)</span>', news, re.S):
        href, bild, datum, titel, text = m.groups()
        karten.append({"seite": href, "bild": bild, "datum": datum[:10], "titel_html": titel, "teaser_html": text})
    return karten


# Emojis, Pfeile/Symbole und Kurzlinks aus Anreißern entfernen (stammen oft aus Facebook-Texten)
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3]+")


def teaser_putzen(t):
    roh = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    for zeichen, ersatz in (("🆚", " gegen "), ("🕒", ", "), ("🏟️", ", "), ("🏟", ", ")):
        roh = roh.replace(zeichen, ersatz)
    roh = EMOJI.sub(" ", roh)
    # „SCHGWO …“ / „FCESCH …“ am Anfang: Kürzel beider Teams ohne Trenner
    roh = re.sub(r"^\s*SCH([A-Z]{2,5})\b", r"SCH – \1", roh)
    roh = re.sub(r"^\s*([A-Z]{2,5})SCH\b", r"\1 – SCH", roh)
    roh = re.sub(r"https?://\S+|\bt1p\.de/\S+", "", roh)
    roh = re.sub(r"\b(?:Der ausführliche Liveticker auf|Zur Liveübertragung|Liveticker auf)\s*:?\s*", "", roh)
    roh = re.sub(r"\s*\|\s*", " | ", roh)
    roh = re.sub(r"\s+([,.:;!?])", r"\1", roh)
    roh = re.sub(r"(,\s*){2,}", ", ", roh)
    roh = re.sub(r"\s{2,}", " ", roh).strip(" |:–-")
    return html.escape(kurz(roh, 220), quote=False)


def alle_eintraege(news, beitraege):
    neue = {d["seite"] for d in beitraege}
    liste = [k for k in lies_news(news) if k["seite"] not in neue]
    for d in beitraege:
        liste.append({"seite": d["seite"], "bild": d["bild"] or "assets/hero.jpg", "datum": d["datum"],
                      "titel_html": html.escape(d["titel"], quote=False), "teaser_html": html.escape(d["teaser"], quote=False),
                      "zeit": d.get("zeit") or "", "ab": d.get("ab") or ""})
    for k in liste:
        k["teaser_html"] = teaser_putzen(k["teaser_html"])
    # Neueste zuerst; bei gleichem Datum neue Redaktionsbeiträge vor alten Einträgen
    liste.sort(key=lambda k: (k["datum"], k.get("zeit", ""), 1 if k["seite"] in neue else 0), reverse=True)
    return liste


NEWS_ANZAHL = 20  # Aktuelles zeigt die letzten 20 (5 Reihen à 4 Kacheln), alles Weitere steht im Archiv


def baue_karten(liste):
    return "".join(
        f'<a class="sp-karte" href="{k["seite"]}"><span class="sp-kartenbild"><img src="../{k["bild"]}" alt="" loading="lazy"></span>'
        f'<span class="sp-kartentext"><time datetime="{k["datum"]}">{datum_de(k["datum"])}</time><b>{k["titel_html"]}</b>'
        f'<span>{k["teaser_html"]}</span><em>Beitrag lesen</em></span></a>'
        for k in liste)


def block_ende(text, start):
    """Stelle direkt hinter dem schließenden </div> des ersten <div …start…>."""
    i = text.find(start)
    j = text.find(">", i) + 1
    tiefe = 1
    for m in re.finditer(r"<(/?)div\b", text[j:]):
        tiefe += -1 if m.group(1) else 1
        if tiefe == 0:
            return j + m.end() + 1  # hinter dem ">" von </div>
    return j


def schreibe_news(ziel, news, liste):
    news = re.sub(r'<p class="sp-knoepfe"><a [^>]*>Ältere Beiträge auf der Vereinsseite</a></p>\s*', "", news)
    neu = ersetze_block(news, '<div class="sp-karten"', "".join(markiere(baue_karten(l[:NEWS_ANZAHL]), a, b) for a, b, l in zustaende(liste)))
    if len(liste) > NEWS_ANZAHL:
        e = block_ende(neu, '<div class="sp-karten"')
        link = (f'<p class="sp-archivlink"><a href="archiv.html">Alle {len(liste)} Beiträge im Archiv</a></p>')
        neu = neu[:e] + link + neu[e:]
    if any(k.get("ab") for k in liste):
        neu = zustand_einbauen(neu)
    open(os.path.join(ziel, "seiten/news.html"), "w", encoding="utf-8").write(neu)
    # Archiv: gleiche Seite, aber mit allen Beiträgen
    arch = ersetze_block(news, '<div class="sp-karten"', "".join(markiere(baue_karten(l), a, b) for a, b, l in zustaende(liste)))
    e = block_ende(arch, '<div class="sp-karten"')
    arch = arch[:e] + '<p class="sp-archivlink"><a href="news.html">← Zurück zu den aktuellen News</a></p>' + arch[e:]
    arch = arch.replace("<title>News · ", "<title>Archiv · ")
    arch = arch.replace('<span>Aktuelles</span><h1>News</h1>', '<span>News</span><h1>Archiv</h1>')
    arch = arch.replace('content="News · 1. SC', 'content="Archiv · 1. SC')
    arch = arch.replace("seiten/news.html", "seiten/archiv.html")
    if any(k.get("ab") for k in liste):
        arch = zustand_einbauen(arch)
    open(os.path.join(ziel, "seiten/archiv.html"), "w", encoding="utf-8").write(arch)


def ersetze_block(text, start, inneres):
    """Ersetzt den Inhalt des ersten <div …start…> bis zum passenden </div>."""
    i = text.find(start)
    if i < 0:
        return text
    j = text.find(">", i) + 1
    tiefe, k = 1, j
    for m in re.finditer(r"<(/?)div\b", text[j:]):
        tiefe += -1 if m.group(1) else 1
        if tiefe == 0:
            k = j + m.start()
            break
    return text[:j] + inneres + text[k:]


def schreibe_start(ziel, liste):
    p = os.path.join(ziel, "index.html")
    s = open(p, encoding="utf-8").read()
    oben, weiter = "", ""
    for a, b, l in zustaende(liste):
        o, w = karten_start(ziel, l)
        oben, weiter = oben + markiere(o, a, b), weiter + markiere(w, a, b)
    s = ersetze_block(s, '<div class="sch-latest"', oben)
    s = ersetze_block(s, '<div class="sch-moregrid"', weiter)
    if any(k.get("ab") for k in liste):
        s = zustand_einbauen(s)
    open(p, "w", encoding="utf-8").write(s)


def karten_start(ziel, liste):
    oben = "".join(
        f'<a class="sch-post" href="seiten/{k["seite"]}"><div class="sch-postimage"><img src="{k["bild"]}" alt="" loading="lazy"{masse(ziel, k["bild"])}></div>'
        f'<div class="sch-postcopy"><time datetime="{k["datum"]}">{datum_de(k["datum"])}</time><h2>{k["titel_html"]}</h2>'
        f'<p class="sch-excerpt">{k["teaser_html"]}</p><span class="sch-read">Beitrag lesen</span></div></a>'
        for k in liste[:3])
    weiter = "".join(
        f'<a class="sch-morecard" href="seiten/{k["seite"]}"><div class="sch-moreimage"><img src="{k["bild"]}" alt="" loading="lazy"{masse(ziel, k["bild"])}></div>'
        f'<div class="sch-morecopy"><time datetime="{k["datum"]}">{datum_de(k["datum"])}</time><h3>{k["titel_html"]}</h3>'
        f'<p>{k["teaser_html"]}</p><span>Beitrag lesen</span></div></a>'
        for k in liste[3:11])
    return oben, weiter


MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def schreibe_neu_start(ziel, liste):
    p = os.path.join(ziel, "neu/index.html")
    if not os.path.exists(p):
        return
    s = open(p, encoding="utf-8").read()
    eintraege = []
    for a, b, l in zustaende(liste):
        eintraege += [markiere(x, a, b) for x in neu_karten(ziel, l)]
    s = re.sub(r'(<ul class="schiene" data-schiene-spur>).*?(\s*</ul>)', lambda mm: mm.group(1) + "\n" + "\n".join(eintraege) + mm.group(2), s, count=1, flags=re.S)
    if any(k.get("ab") for k in liste):
        s = zustand_einbauen(s)
    open(p, "w", encoding="utf-8").write(s)


def neu_karten(ziel, liste):
    eintraege = []
    for k in liste[:8]:
        j, m, t = k["datum"].split("-")
        eintraege.append(
            f'      <li><a href="seiten/{k["seite"]}">\n'
            f'        <figure><img src="../{k["bild"]}" alt="" loading="lazy"{masse(ziel, k["bild"])}></figure>\n'
            f'        <time datetime="{k["datum"]}">{int(t)}. {MONATE[int(m) - 1]}</time>\n'
            f'        <h3>{k["titel_html"]}</h3>\n'
            f'        <p>{html.escape(kurz(k["teaser_html"], 140), quote=False)}</p>\n'
            f'      </a></li>')
    return eintraege


# ---------------------------------------------------------------- Ablauf
# ---------------------------------------------------------------- Wanderseite
# Redaktionsbeiträge über das Wandern erscheinen zusätzlich oben in „News der Abteilung“ auf seiten/wandern.html
# (neuester zuerst, die festen Einträge rücken nach unten). Erkannt am Inhalt, keine eigene Rubrik nötig.
WANDER_FEST = re.compile(r"wanderabteilung|abteilung wandern|wanderfreund|wandertag|wimpelwander|wanderführ|wanderplan", re.I)
WANDER_WORT = re.compile(r"\bwander(?!pokal)\w*", re.I)


def ist_wandern(d):
    rubrik = (d.get("rubrik") or "").lower()
    if rubrik == "wandern":
        return True
    if rubrik in ("spielbericht", "vorbericht"):
        return False
    titel = d.get("titel") or ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", d.get("text") or ""))
    if WANDER_FEST.search(titel + " " + text):
        return True
    im_text = len(WANDER_WORT.findall(text))
    return (bool(WANDER_WORT.search(titel)) and im_text >= 1) or im_text >= 3


def schreibe_wandern(ziel, beitraege):
    pfad = os.path.join(ziel, "seiten", "wandern.html")
    if not os.path.exists(pfad):
        return 0
    liste = sorted((d for d in beitraege if ist_wandern(d)), key=lambda d: (d["datum"], d.get("zeit", "")), reverse=True)
    if not liste:
        return 0
    karten = "".join(
        f'<a class="sp-newskarte" href="{d["seite"]}">'
        + (f'<img src="../{d["bild"]}" alt="" loading="lazy">' if d.get("bild") else "")
        + f'<span>{html.escape(d["titel"], quote=False)}</span></a>\n'
        for d in liste)
    t = open(pfad, encoding="utf-8").read()
    start = '<div class="sp-newsliste">'
    if start not in t:
        return 0
    t = t.replace(start, start + "\n" + karten, 1)
    open(pfad, "w", encoding="utf-8").write(t)
    return len(liste)


def main():
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 werkzeuge/beitraege.py ZIELORDNER")
    ziel = os.path.abspath(sys.argv[1])
    beitraege = lade_beitraege()
    sichtbar = [d for d in beitraege if not d.get("ab")]  # vorab gebaute erscheinen nicht in fremden Seiten
    vorlage = open(os.path.join(REPO, VORLAGE), encoding="utf-8").read()
    sb_vorlage = open(os.path.join(REPO, SB_VORLAGE), encoding="utf-8").read()
    # Spielberichte im Erfurt-Aufbau; dabei merken, welcher Vorbericht zu welchem Spielbericht gehört
    zum_bericht = {}
    # Live-Ticker-Seite (Inhalt lädt live.js) im selben Rahmen wie die Spielberichte
    open(os.path.join(ziel, "seiten", "live.html"), "w", encoding="utf-8").write(spielbericht.live_seite(sb_vorlage, ADRESSE))
    for d in beitraege:
        if d.get("rubrik") == "Spielbericht":
            seite, vb = spielbericht.baue(d, sb_vorlage, sichtbar, ADRESSE)
            if d.get("ab"):
                seite = vorab_sperre(seite, d["ab"], d["geplant"])
            open(os.path.join(ziel, "seiten", d["seite"]), "w", encoding="utf-8").write(seite)
            if vb and vb["slug"] not in zum_bericht and not d.get("ab"):
                zum_bericht[vb["slug"]] = d
    for d in beitraege:
        if d.get("rubrik") == "Spielbericht":
            continue
        sb = zum_bericht.get(d["slug"])
        zusatz = f'\n<p><strong><a href="{sb["seite"]}#spielbericht">Zum Spielbericht</a></strong></p>' if sb else ""
        if d.get("rubrik") == "Vorbericht":
            # Vorbericht im Aufbau der Spielberichte (Kopfbild der Mannschaft, Tafel, Bild unter der Überschrift)
            seite = spielbericht.vorbericht_seite(d, sb_vorlage, ADRESSE, vorbericht_team(d, sb),
                                                  (sb or {}).get("spiel"),
                                                  zusatz.replace('href="', 'href="seiten/') if zusatz else "")
            if d.get("ab"):
                seite = vorab_sperre(seite, d["ab"], d["geplant"])
            open(os.path.join(ziel, "seiten", d["seite"]), "w", encoding="utf-8").write(seite)
            continue
        baue_seite(ziel, d, vorlage, zusatz, vorbericht_team(d, sb))
    news = open(os.path.join(REPO, "seiten/news.html"), encoding="utf-8").read()
    liste = alle_eintraege(news, beitraege)
    schreibe_news(ziel, news, liste)
    schreibe_start(ziel, liste)
    schreibe_neu_start(ziel, liste)
    n = schreibe_wandern(ziel, sichtbar)
    if n:
        print(f"{n} Wanderbeiträge oben auf der Wanderseite.")
    # „Aktuelle Spiele“: Karte zum Spielbericht bekommt Ergebnis und Link
    p = os.path.join(ziel, "index.html")
    start = open(p, encoding="utf-8").read()
    # Kommende Spiele der 1. Mannschaft: eigene Spielinfo-Seite, die Spielkarte verlinkt darauf
    spielinfo = spielvorschau.baue_alle(ziel, sb_vorlage, ADRESSE, sichtbar)
    # Nachwuchs: Spielinfo- bzw. Ergebnisseite für jede Nachwuchskarte (nicht in den News)
    spielinfo.update(spielvorschau.baue_jugend(ziel, start, sb_vorlage, ADRESSE, sichtbar))
    # … und für die ganze Saison, mit „Nächste Spiele“ / „Ergebnisse der Saison“ auf den Mannschaftsseiten
    spielinfo = spielvorschau.baue_saison(ziel, sb_vorlage, ADRESSE, sichtbar, spielinfo)
    spielvorschau.vereinsspiele(ziel)  # für die Redaktion: Mannschaft aus Spieltag und Gegner erkennen
    start = spielvorschau.verlinke_karten(start, spielinfo)
    spielvorschau.verlinke_mannschaftsseiten(ziel, spielinfo)  # „Nächste Spiele“ -> eigene Spielinfo-Seiten
    n = spielvorschau.verlinke_termine(ziel, spielinfo)  # Termine-Seite: „Zum Spiel“ -> eigene Seite
    print(f"Termine: {n} Spiele auf die eigene Spielseite verlinkt.")
    open(p, "w", encoding="utf-8").write(spiele.verlinke_berichte(start, sichtbar))
    print(f"{len(beitraege)} Redaktionsbeiträge eingebaut, {len(liste)} Beiträge in der Liste.")
    # SCHeimat-Zeichen in Galerie- und Beitragsbilder setzen, wo es noch fehlt (nur im Ausgabeordner; nie in ein
    # Git-Repo, damit die Originale unverändert bleiben). Braucht Pillow und numpy.
    if os.path.isdir(os.path.join(ziel, ".git")):
        print("SCHeimat: Ziel ist ein Git-Repo – Zeichen nicht gesetzt.")
    else:
        try:
            import schheimat
        except ImportError as fehler:
            print(f"SCHeimat: Zeichen nicht gesetzt ({fehler}).")
        else:
            schheimat.main(ziel)


if __name__ == "__main__":
    main()
