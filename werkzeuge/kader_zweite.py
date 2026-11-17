"""Kader von FuPa holen und in die Mannschaftsseite einbauen: 2. Mannschaft und U19.

Aufbau wie seiten/erste-mannschaft.html (Mannschaftsfoto oben, Gruppen Tor/Abwehr/Mittelfeld/Angriff/Trainerstab).
Die Fotos werden heruntergeladen und unter assets/kader-zweite/ bzw. assets/kader-u19/ abgelegt, damit beim
Besuch der Seite keine Daten an FuPa gehen. Fotos von Spielern, die nicht mehr im Kader stehen, werden entfernt.

Aufruf (im Repo-Ordner):  python3 werkzeuge/kader_zweite.py        (2. Mannschaft)
                          python3 werkzeuge/kader_zweite.py u19    (A-Junioren / U19)
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
GRUPPEN = [("Torwart", "Tor"), ("Abwehr", "Abwehr"), ("Mittelfeld", "Mittelfeld"), ("Angriff", "Angriff")]
UA = {"User-Agent": "SCH-Website"}
# Stehen bei FuPa im Kader, sollen auf unserer Seite aber nicht erscheinen (Wunsch Redaktion, 15.11.2026).
# Daniel Papst nur als Spieler – im Trainerstab bleibt er.
NICHT_ZEIGEN = {"Kai Rhöse", "Pascal Köhler", "Fabio Dornieden", "Jonas Grimm", "Jannis Mähler",
                "Paul Opfermann", "Daniel Papst", "Lucas Roth", "Jagar Jargees Ali"}

MANNSCHAFTEN = {
    "m2": {"fupa": "m2", "seite": "seiten/zweite-mannschaft.html", "ordner": "assets/kader-zweite",
           "foto_alt": "Mannschaftsfoto der 2. Mannschaft", "nicht_zeigen": NICHT_ZEIGEN,
           # beim ersten Mal: FuPa-Widget samt Überschrift ersetzen
           "alt": r'<h2>2\. Mannschaft – Der Kader [^<]*</h2><div class="sp-fupa".*?</button></div>'},
    "u19": {"fupa": "u19-1", "seite": "seiten/u19.html", "ordner": "assets/kader-u19",
            "foto_alt": "Mannschaftsfoto der A-Junioren (U19)", "nicht_zeigen": set(),
            # beim ersten Mal: Tabelle und Spielplan als FuPa-Widgets ersetzen („Nächste Spiele“ und
            # „Ergebnisse der Saison“ baut beitraege.py ohnehin aus den Spieldaten)
            "alt": r'<h3>Tabelle</h3>\s*<div class="sp-fupa".*?</button></div>\s*<h3>Spielplan</h3>\s*<div class="sp-fupa".*?</button></div>'},
}
ORDNER = MANNSCHAFTEN["m2"]["ordner"]
_GENUTZT = set()


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def bild(pfad, groesse, name):
    """FuPa-Bild in der Größe laden und unter <ORDNER>/<name>.webp speichern."""
    ziel = f"{ORDNER}/{name}.webp"
    _GENUTZT.add(os.path.basename(ziel))
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
    global ORDNER
    kuerzel = sys.argv[1] if len(sys.argv) > 1 else "m2"
    if kuerzel not in MANNSCHAFTEN:
        sys.exit(f"Unbekannte Mannschaft {kuerzel!r} – möglich: {', '.join(MANNSCHAFTEN)}")
    cfg = MANNSCHAFTEN[kuerzel]
    ORDNER = cfg["ordner"]
    seite = os.path.join(REPO, cfg["seite"])
    slug = f"1-sc-1911-heiligenstadt-{cfg['fupa']}-{saison()}"
    d = json.loads(hole(f"https://api.fupa.net/v1/teams/{slug}/squad"))
    spieler = [p for p in d["players"] if not p.get("isDeactivated")
               and f'{p["firstName"].strip()} {p["lastName"].strip()}' not in cfg["nicht_zeigen"]]
    ordnung = lambda p: (p.get("jerseyNumber") is None, p.get("jerseyNumber") or 0, p["lastName"])
    teile = []
    for pos, titel in GRUPPEN:
        teile.append(gruppe(titel, sorted([p for p in spieler if p.get("position") == pos], key=ordnung)))
    trainer = [dict(c, rolle=True) for c in d.get("coaches", [])]
    teile.append(gruppe("Trainerstab", trainer))
    kader = "".join(teile)

    s = open(seite, encoding="utf-8").read()
    # Mannschaftsfoto als Kopf wie bei der Ersten
    tb = (d.get("info") or {}).get("teamImage") or {}
    if tb.get("path") and not tb.get("svg"):
        foto = bild(tb["path"], "1920x1080", "mannschaft")
        s = re.sub(r'<div class="sch-reporthero sp-held[^"]*"><img [^>]*>',
                   f'<div class="sch-reporthero sp-held kd-held"><img src="../{foto}" alt="{cfg["foto_alt"]}" '
                   'width="1920" height="1080" fetchpriority="high" style="object-position:50% 45%">', s, count=1)
    s = s.replace('<main class="sch-report sp-seite">', '<main class="sch-report sp-seite kd-seite">', 1)
    # Kaderblock zwischen den Markierungen ersetzen (beim ersten Mal: FuPa-Widget samt Überschrift)
    neu = f"<!--kader-->{kader}<!--/kader-->"
    if "<!--kader-->" in s:
        s = re.sub(r"<!--kader-->.*?<!--/kader-->", lambda m: neu, s, count=1, flags=re.S)
    else:
        s, n = re.subn(cfg["alt"], lambda m: neu, s, count=1, flags=re.S)
        if not n:
            sys.exit(f"Kaderstelle in {cfg['seite']} nicht gefunden")
    if "<!--kader-->" in s and "fupa.js" in s and "sp-fupa" not in s:
        s = s.replace('<script src="../fupa.js"></script>', "")
    open(seite, "w", encoding="utf-8").write(s)
    # Fotos von Spielern, die nicht mehr im Kader stehen, entfernen
    for f in os.listdir(os.path.join(REPO, ORDNER)):
        if f.endswith(".webp") and f not in _GENUTZT:
            os.remove(os.path.join(REPO, ORDNER, f))
    print(f"{len(spieler)} Spieler, {len(trainer)} Trainer eingebaut ({saison()}).")


if __name__ == "__main__":
    main()
