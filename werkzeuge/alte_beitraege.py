#!/usr/bin/env python3
"""Beiträge der alten Vereinsseite (sc1911-heiligenstadt.de, WordPress) übernehmen.

Aufruf (im Repo-Ordner):
    python3 werkzeuge/alte_beitraege.py 2026        # alle Beiträge aus 2026
    python3 werkzeuge/alte_beitraege.py 2025        # später: die aus 2025

Für jeden Beitrag entsteht seiten/beitrag-<slug>.html im Aufbau der übrigen Beitragsseiten
(Titelbild ganz oben, Text, Bildergalerie). Titelbild und Galeriefotos werden einmal geladen, verkleinert und
als WebP (mit Pillow, sonst JPEG) unter assets/seiten/ abgelegt. Die Karte kommt in seiten/news.html – der Pages-Bau
(werkzeuge/beitraege.py) zeigt daraus die neuesten 20 unter News und alle im Archiv.

Schon vorhandene Beiträge (gleiche Seite oder gleicher Titel am selben/Nachbartag) werden übersprungen,
das Skript kann also gefahrlos mehrfach laufen. Für kleine Bilddateien mit Pillow aufrufen (pip install pillow); ohne Pillow nimmt es sips (macOS) und JPEG.
"""
import concurrent.futures
import datetime
import glob
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beitraege as bt  # noqa: E402  saeubern, baue_seite, baue_karten, ersetze_block …

REPO = bt.REPO
ALT = "https://www.sc1911-heiligenstadt.de"
UA = {"User-Agent": "SCH-Website"}
BILDORDNER = "assets/seiten"
QUALITAET = 62  # WebP-Qualität: Fotos bleiben scharf, Dateien klein
# Alte Beiträge, die bewusst nicht übernommen werden (Slug), z. B. weil es sie schon aus der Redaktion gibt
AUSLASSEN = {
    "weiter-gehts",  # Spielbericht SCH – Wacker Nordhausen 4:0, liegt als Redaktionsbeitrag vor
}

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = ImageOps = None


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def lade_posts(jahr):
    posts, seite = [], 1
    while True:
        url = (f"{ALT}/wp-json/wp/v2/posts?per_page=100&page={seite}&after={jahr}-01-01T00:00:00"
               f"&before={jahr + 1}-01-01T00:00:00&_embed=wp:featuredmedia")
        try:
            teil = json.loads(hole(url))
        except urllib.error.HTTPError as e:
            if e.code == 400:  # Seite hinter dem Ende
                break
            raise
        if not teil:
            break
        posts += teil
        seite += 1
    return posts


def schluessel(titel):
    return re.sub(r"[^a-z0-9äöüß]", "", html.unescape(titel).lower())


def bild_speichern(url, groesse):
    """Bild laden, auf `groesse` px (längste Seite) verkleinern und speichern. Gibt den Repo-Pfad zurück.

    Mit Pillow (pip install pillow) als WebP, sonst über sips als JPEG (deutlich größer)."""
    stamm = hashlib.sha1(url.encode()).hexdigest()[:14]
    name = stamm + (".webp" if Image else ".jpg")
    ziel = os.path.join(REPO, BILDORDNER, name)
    if not os.path.exists(ziel):
        daten = hole(url)
        if Image:
            bild = Image.open(io.BytesIO(daten))
            bild = ImageOps.exif_transpose(bild).convert("RGB")
            bild.thumbnail((groesse, groesse), Image.LANCZOS)
            bild.save(ziel, "WEBP", quality=QUALITAET, method=6)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                roh = os.path.join(tmp, "roh" + os.path.splitext(urllib.parse.urlparse(url).path)[1].lower())
                open(roh, "wb").write(daten)
                subprocess.run(["sips", "-Z", str(groesse), "-s", "format", "jpeg", "-s", "formatOptions", "60",
                                roh, "--out", ziel], check=True, capture_output=True)
    return f"{BILDORDNER}/{name}"


def groesstes(img_tag, grenze=1600):
    """Aus src/srcset die größte Fassung bis `grenze` px Breite."""
    src = re.search(r'\ssrc="([^"]+)"', img_tag)
    beste, bw = (src.group(1) if src else ""), 0
    ss = re.search(r'srcset="([^"]+)"', img_tag)
    if ss:
        for teil in ss.group(1).split(","):
            t = teil.strip().split()
            if len(t) == 2 and t[1].endswith("w"):
                w = int(t[1][:-1])
                if bw < w <= grenze:
                    beste, bw = t[0], w
    return html.unescape(beste)


def titelbild_url(p):
    fm = (p.get("_embedded") or {}).get("wp:featuredmedia") or [{}]
    fm = fm[0] if fm else {}
    groessen = (fm.get("media_details") or {}).get("sizes") or {}
    for g in ("1536x1536", "extra_large", "large", "full"):
        if g in groessen and groessen[g].get("source_url"):
            return groessen[g]["source_url"]
    return fm.get("source_url") or ""


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit("Aufruf: python3 werkzeuge/alte_beitraege.py JAHR")
    jahr = int(sys.argv[1])
    posts = lade_posts(jahr)
    print(f"{len(posts)} Beiträge aus {jahr} auf der alten Seite")

    newspfad = os.path.join(REPO, "seiten/news.html")
    news = open(newspfad, encoding="utf-8").read()
    vorhanden = bt.lies_news(news)
    eigene = bt.lade_beitraege()
    bekannt = {}  # Titel-Schlüssel -> Datumsliste (Doppelte erkennen, z. B. Redaktionsbeiträge aus /admin/)
    for k in vorhanden:
        bekannt.setdefault(schluessel(re.sub(r"<[^>]+>", "", k["titel_html"])), []).append(k["datum"])
    for d in eigene:
        bekannt.setdefault(schluessel(d["titel"]), []).append(d["datum"])
    seiten = {os.path.basename(p) for p in glob.glob(os.path.join(REPO, "seiten/beitrag-*.html"))}

    def doppelt(p):
        if p["slug"] in AUSLASSEN or f'beitrag-{p["slug"]}.html' in seiten:
            return True
        tag = datetime.date.fromisoformat(p["date"][:10])
        for d in bekannt.get(schluessel(titel_von(p)), []):
            if abs((datetime.date.fromisoformat(d) - tag).days) <= 2:
                return True
        return False

    neu = [p for p in posts if not doppelt(p)]
    print(f"{len(posts) - len(neu)} schon vorhanden, {len(neu)} werden übernommen")
    # Verweise zwischen alten Beiträgen auf die neuen Seiten umbiegen
    slugs = {p["slug"] for p in posts} | {s[8:-5] for s in seiten}

    def links_umbiegen(text):
        def ersetze(m):
            pfad = urllib.parse.urlparse(html.unescape(m.group(1))).path.strip("/")
            return f'href="beitrag-{pfad}.html"' if pfad in slugs else m.group(0)
        return re.sub(r'href="(https?://(?:www\.)?sc1911-heiligenstadt\.de/[^"#?]*)"', ersetze, text)

    vorlage = open(os.path.join(REPO, bt.VORLAGE), encoding="utf-8").read()

    def bearbeite(p):
        inhalt = p["content"]["rendered"]
        tb = titelbild_url(p)
        bild = bild_speichern(tb, 1600) if tb else ""
        galerie = []
        for tag in re.findall(r"<img\b[^>]*>", inhalt):
            url = groesstes(tag, 1200)
            if url and "/wp-content/uploads/" in url:
                g = bild_speichern(url, 1200)
                if g != bild and g not in galerie:
                    galerie.append(g)
        text = bt.saeubern(links_umbiegen(inhalt))
        text = re.sub(r"<p>\s*(?:&nbsp;|\s)*</p>", "", text)
        teaser = bt.kurz(re.sub(r"\s*\[(?:…|&hellip;|\.\.\.)\]\s*$", "", html.unescape(re.sub(r"<[^>]+>", " ", p["excerpt"]["rendered"]))).strip(), 300)
        d = {"titel": titel_von(p), "datum": p["date"][:10], "rubrik": "News", "teaser": teaser, "text": text,
             "bild": bild, "galerie": galerie, "seite": f'beitrag-{p["slug"]}.html'}
        bt.baue_seite(REPO, d, vorlage)
        return {"seite": d["seite"], "bild": bild or "assets/hero.jpg", "datum": d["datum"],
                "titel_html": html.escape(d["titel"], quote=False), "teaser_html": html.escape(teaser, quote=False)}

    karten = []
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for i, k in enumerate(pool.map(bearbeite, neu), 1):
            karten.append(k)
            if i % 20 == 0:
                print(f"  {i}/{len(neu)} …")

    # Karten in news.html: alle zusammen, neueste zuerst
    liste = vorhanden + karten
    liste.sort(key=lambda k: k["datum"], reverse=True)
    news = bt.ersetze_block(news, '<div class="sp-karten"', bt.baue_karten(liste))
    open(newspfad, "w", encoding="utf-8").write(news)
    print(f"{len(karten)} Beiträge übernommen, {len(liste)} Karten in seiten/news.html")


def titel_von(p):
    t = html.unescape(p["title"]["rendered"]).strip()
    return re.sub(r"^\+{2,}\s*|\s*\+{2,}$", "", t).strip() or "Ohne Titel"


if __name__ == "__main__":
    main()
