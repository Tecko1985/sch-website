"""Kader der 2. Mannschaft von FuPa holen und in seiten/zweite-mannschaft.html einbauen.

Aufbau wie seiten/erste-mannschaft.html (Mannschaftsfoto oben, Gruppen Tor/Abwehr/Mittelfeld/Angriff/Trainerstab).
Die Fotos werden einmal heruntergeladen und unter assets/kader-zweite/ abgelegt, damit beim Besuch der Seite
keine Daten an FuPa gehen.

Aufruf (im Repo-Ordner):  python3 werkzeuge/kader_zweite.py
Danach die Seite prüfen und committen. Nur Python-Standardbibliothek.
"""
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spielvorschau import saison  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEITE = os.path.join(REPO, "seiten/zweite-mannschaft.html")
ORDNER = "assets/kader-zweite"
GRUPPEN = [("Torwart", "Tor"), ("Abwehr", "Abwehr"), ("Mittelfeld", "Mittelfeld"), ("Angriff", "Angriff")]
UA = {"User-Agent": "SCH-Website"}
# Stehen bei FuPa im Kader, sollen auf unserer Seite aber nicht erscheinen (Wunsch Redaktion, 15.11.2026).
# Daniel Papst nur als Spieler – im Trainerstab bleibt er.
NICHT_ZEIGEN = {"Kai Rhöse", "Pascal Köhler", "Fabio Dornieden", "Jonas Grimm", "Jannis Mähler",
                "Paul Opfermann", "Daniel Papst", "Lucas Roth", "Jagar Jargees Ali"}


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def bild(pfad, groesse, name):
    """FuPa-Bild in der Größe laden und unter assets/kader-zweite/<name>.webp speichern."""
    ziel = f"{ORDNER}/{name}.webp"
    daten = hole(f"{pfad}{groesse}.webp")
    os.makedirs(os.path.join(REPO, ORDNER), exist_ok=True)
    with open(os.path.join(REPO, ziel), "wb") as f:
        f.write(daten)
    return ziel


def karte(p):
    e = html.escape
    vor, nach = p["firstName"].strip(), p["lastName"].strip()
    voll = f"{vor} {nach}"
    if p["image"] and not p["image"].get("svg"):
        foto = f'<img src="../{bild(p["image"]["path"], "480x600", p["slug"])}" alt="{e(voll)}" loading="lazy">'
    else:
        foto = '<span class="sp-ohnebild kd-ohnebild" aria-hidden="true"></span>'
    nr = f'<b>{p["jerseyNumber"]}</b>' if p.get("jerseyNumber") else ""
    rolle = f'<small class="kd-rolle">{e(p.get("role") or "")}</small>' if p.get("rolle") and p.get("role") else ""
    return f'<div class="sp-spieler">{foto}{nr}<span class="kd-name"><em>{e(vor)}</em> {e(nach)}{rolle}</span></div>'


def gruppe(titel, leute):
    if not leute:
        return ""
    return ('<div class="sp-kader kd-raster"><div class="kd-gruppe"><h2>' + html.escape(titel) + "</h2></div>"
            + "".join(karte(p) for p in leute) + "</div>")


def main():
    slug = f"1-sc-1911-heiligenstadt-m2-{saison()}"
    d = json.loads(hole(f"https://api.fupa.net/v1/teams/{slug}/squad"))
    spieler = [p for p in d["players"] if not p.get("isDeactivated")
               and f'{p["firstName"].strip()} {p["lastName"].strip()}' not in NICHT_ZEIGEN]
    ordnung = lambda p: (p.get("jerseyNumber") is None, p.get("jerseyNumber") or 0, p["lastName"])
    teile = []
    for pos, titel in GRUPPEN:
        teile.append(gruppe(titel, sorted([p for p in spieler if p.get("position") == pos], key=ordnung)))
    trainer = [dict(c, rolle=True) for c in d.get("coaches", [])]
    teile.append(gruppe("Trainerstab", trainer))
    kader = "".join(teile)

    s = open(SEITE, encoding="utf-8").read()
    # Mannschaftsfoto als Kopf wie bei der Ersten
    tb = (d.get("info") or {}).get("teamImage") or {}
    if tb.get("path") and not tb.get("svg"):
        foto = bild(tb["path"], "1920x1080", "mannschaft")
        s = re.sub(r'<div class="sch-reporthero sp-held[^"]*"><img [^>]*>',
                   f'<div class="sch-reporthero sp-held kd-held"><img src="../{foto}" alt="Mannschaftsfoto der 2. Mannschaft" '
                   'width="1920" height="1080" fetchpriority="high" style="object-position:50% 45%">', s, count=1)
    s = s.replace('<main class="sch-report sp-seite">', '<main class="sch-report sp-seite kd-seite">', 1)
    # Kaderblock zwischen den Markierungen ersetzen (beim ersten Mal: FuPa-Widget samt Überschrift)
    neu = f"<!--kader-->{kader}<!--/kader-->"
    if "<!--kader-->" in s:
        s = re.sub(r"<!--kader-->.*?<!--/kader-->", lambda m: neu, s, count=1, flags=re.S)
    else:
        s, n = re.subn(r'<h2>2\. Mannschaft – Der Kader [^<]*</h2><div class="sp-fupa".*?</button></div>', lambda m: neu, s,
                       count=1, flags=re.S)
        if not n:
            sys.exit("Kaderstelle in zweite-mannschaft.html nicht gefunden")
    if "<!--kader-->" in s and "fupa.js" in s and "sp-fupa" not in s:
        s = s.replace('<script src="../fupa.js"></script>', "")
    open(SEITE, "w", encoding="utf-8").write(s)
    print(f"{len(spieler)} Spieler, {len(trainer)} Trainer eingebaut ({saison()}).")


if __name__ == "__main__":
    main()
