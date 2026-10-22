#!/usr/bin/env python3
"""Baut Beiträge aus der Redaktionsoberfläche (/admin/) in die Seite ein.

Aufruf:  python3 werkzeuge/beitraege.py ZIELORDNER
(im Pages-Bau: python3 werkzeuge/beitraege.py _site)

Liest inhalte/beitraege/*.json aus dem Repo und schreibt in ZIELORDNER:
- seiten/beitrag-<slug>.html  (eine Seite je Beitrag, im Aufbau der übrigen Beitragsseiten)
- seiten/news.html            (Liste aller Beiträge, neueste zuerst)
- index.html                  (die drei neuesten und „Was läuft weiter beim SCH?“)
- neu/index.html              (News-Schiene im neuen Design)
Die Unterseiten unter neu/ entstehen danach mit werkzeuge/neu_seiten.py.

Das Repo selbst bleibt unverändert: Erzeugt wird nur im Zielordner.
"""
import glob
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORLAGE = "seiten/beitrag-serie-haelt-weiter.html"
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


def saeubern(roh):
    s = Saeuberer()
    s.feed(roh or "")
    s.close()
    t = s.ergebnis()
    if t and not t.startswith("<"):
        t = f"<p>{t}</p>"
    return t


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
        slug = os.path.basename(pfad)[:-5]
        if not re.match(r"^[a-z0-9-]+$", slug) or not re.match(r"^\d{4}-\d{2}-\d{2}$", d.get("datum", "")):
            print(f"::warning::{slug}: ungültiger Name oder Datum, übersprungen")
            continue
        d["slug"] = slug
        d["seite"] = f"beitrag-{slug}.html"
        d["titel"] = (d.get("titel") or "").strip() or "Ohne Titel"
        d["teaser"] = kurz(d.get("teaser") or d.get("text"), 300)
        d["text"] = saeubern(d.get("text"))
        d["bild"] = d.get("bild") or ""
        d["galerie"] = [g for g in d.get("galerie", []) if re.match(r"^assets/beitraege/[a-z0-9._-]+$", g)]
        if d["bild"] and not re.match(r"^assets/beitraege/[a-z0-9._-]+$", d["bild"]):
            d["bild"] = ""
        beitraege.append(d)
    return beitraege


# ---------------------------------------------------------------- Beitragsseite
def baue_seite(ziel, d, vorlage):
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
    held = (f'<div class="sch-reporthero sp-held">{bild}<div><span>{e(d.get("rubrik") or "News")}</span>'
            f'<h1>{e(d["titel"])}</h1><p class="sp-datum">{datum_de(d["datum"])}</p></div></div>')
    inhalt = d["text"]
    if d["galerie"]:
        inhalt += '\n<div class="sp-galerie">' + "".join(f'<img src="../{g}" alt="" loading="lazy">' for g in d["galerie"]) + "</div>"
    main = f'<main class="sch-report sp-seite">{held}<article class="sp-inhalt">\n{inhalt}\n</article>'
    t = re.sub(r'<main class="sch-report sp-seite">.*?</article>', lambda m: main, t, count=1, flags=re.S)
    open(os.path.join(ziel, "seiten", d["seite"]), "w", encoding="utf-8").write(t)


# ---------------------------------------------------------------- Listen
def lies_news(news):
    """Bestehende Karten aus seiten/news.html (alte, eingepflegte Beiträge)."""
    karten = []
    for m in re.finditer(r'<a class="sp-karte" href="([^"]+)">.*?<img src="\.\./([^"]+)".*?<time datetime="([^"]+)">.*?<b>(.*?)</b><span>(.*?)</span>', news, re.S):
        href, bild, datum, titel, text = m.groups()
        karten.append({"seite": href, "bild": bild, "datum": datum[:10], "titel_html": titel, "teaser_html": text})
    return karten


def alle_eintraege(news, beitraege):
    neue = {d["seite"] for d in beitraege}
    liste = [k for k in lies_news(news) if k["seite"] not in neue]
    for d in beitraege:
        liste.append({"seite": d["seite"], "bild": d["bild"] or "assets/hero.jpg", "datum": d["datum"],
                      "titel_html": html.escape(d["titel"], quote=False), "teaser_html": html.escape(d["teaser"], quote=False),
                      "zeit": d.get("zeit") or ""})
    # Neueste zuerst; bei gleichem Datum neue Redaktionsbeiträge vor alten Einträgen
    liste.sort(key=lambda k: (k["datum"], k.get("zeit", ""), 1 if k["seite"] in neue else 0), reverse=True)
    return liste


def schreibe_news(ziel, news, liste):
    karten = "".join(
        f'<a class="sp-karte" href="{k["seite"]}"><span class="sp-kartenbild"><img src="../{k["bild"]}" alt="" loading="lazy"></span>'
        f'<span class="sp-kartentext"><time datetime="{k["datum"]}">{datum_de(k["datum"])}</time><b>{k["titel_html"]}</b>'
        f'<span>{k["teaser_html"]}</span><em>Beitrag lesen</em></span></a>'
        for k in liste)
    neu = ersetze_block(news, '<div class="sp-karten"', karten)
    open(os.path.join(ziel, "seiten/news.html"), "w", encoding="utf-8").write(neu)


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
    s = ersetze_block(s, '<div class="sch-latest"', oben)
    s = ersetze_block(s, '<div class="sch-moregrid"', weiter)
    open(p, "w", encoding="utf-8").write(s)


MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def schreibe_neu_start(ziel, liste):
    p = os.path.join(ziel, "neu/index.html")
    if not os.path.exists(p):
        return
    s = open(p, encoding="utf-8").read()
    eintraege = []
    for k in liste[:8]:
        j, m, t = k["datum"].split("-")
        eintraege.append(
            f'      <li><a href="seiten/{k["seite"]}">\n'
            f'        <figure><img src="../{k["bild"]}" alt="" loading="lazy"{masse(ziel, k["bild"])}></figure>\n'
            f'        <time datetime="{k["datum"]}">{int(t)}. {MONATE[int(m) - 1]}</time>\n'
            f'        <h3>{k["titel_html"]}</h3>\n'
            f'        <p>{kurz(html.unescape(k["teaser_html"]), 140)}</p>\n'
            f'      </a></li>')
    s = re.sub(r'(<ul class="schiene" data-schiene-spur>).*?(\s*</ul>)', lambda mm: mm.group(1) + "\n" + "\n".join(eintraege) + mm.group(2), s, count=1, flags=re.S)
    open(p, "w", encoding="utf-8").write(s)


# ---------------------------------------------------------------- Ablauf
def main():
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 werkzeuge/beitraege.py ZIELORDNER")
    ziel = os.path.abspath(sys.argv[1])
    beitraege = lade_beitraege()
    vorlage = open(os.path.join(REPO, VORLAGE), encoding="utf-8").read()
    for d in beitraege:
        baue_seite(ziel, d, vorlage)
    news = open(os.path.join(REPO, "seiten/news.html"), encoding="utf-8").read()
    liste = alle_eintraege(news, beitraege)
    schreibe_news(ziel, news, liste)
    schreibe_start(ziel, liste)
    schreibe_neu_start(ziel, liste)
    print(f"{len(beitraege)} Redaktionsbeiträge eingebaut, {len(liste)} Beiträge in der Liste.")


if __name__ == "__main__":
    main()
