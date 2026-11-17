"""Spielerfotos für die Tor- und Wechsel-Karten im Liveticker von FuPa holen (1. und 2. Mannschaft, U19).

Spieler der Ersten helfen in der Zweiten aus, U19-Spieler spielen in der Zweiten oder Ersten. Damit auch sie
auf den Karten ein Foto haben, werden die FuPa-Kader dieser drei Mannschaften einmal geladen. Die Fotos landen
klein unter assets/spielerfotos/, die Liste (nur Spieler MIT Foto, die nicht schon mit Foto auf
unserer Kaderseite stehen: Name, Nummer, Bild) in
werkzeuge/spielerfotos.json. Beim Besuch der Seite geht so keine Anfrage an FuPa.

Aufruf (im Repo-Ordner):  python3 werkzeuge/spielerfotos.py
Danach committen. Neu laufen lassen, wenn sich die Kader ändern (z. B. zur neuen Saison).
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spielvorschau import saison  # noqa: E402
import spielerbilder  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDNER = "assets/spielerfotos"
LISTE = os.path.join(REPO, "werkzeuge", "spielerfotos.json")
TEAMS = {"m1": "m1", "m2": "m2", "u19": "u19-1"}
UA = {"User-Agent": "SCH-Website"}


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def main():
    aus, gebraucht = {}, set()
    os.makedirs(os.path.join(REPO, ORDNER), exist_ok=True)
    for team, fupa in TEAMS.items():
        d = json.loads(hole(f"https://api.fupa.net/v1/teams/1-sc-1911-heiligenstadt-{fupa}-{saison()}/squad"))
        liste = []
        for p in d.get("players", []):
            bild = p.get("image") or {}
            if p.get("isDeactivated") or not bild.get("path") or bild.get("svg"):
                continue
            name = f"{p['firstName'].strip()} {p['lastName'].strip()}"
            # Schon mit Foto auf unserer Kaderseite (Erste/Zweite)? Dann nicht doppelt ablegen
            if any(spielerbilder._norm(k["name"]) == spielerbilder._norm(name) and k["bild"]
                   for k in spielerbilder.kader(team)):
                continue
            datei = f"{ORDNER}/{p['slug']}.webp"
            gebraucht.add(os.path.basename(datei))
            if not os.path.exists(os.path.join(REPO, datei)):
                with open(os.path.join(REPO, datei), "wb") as f:
                    f.write(hole(f"{bild['path']}480x600.webp"))
            liste.append({"name": name,
                          "nr": str(p.get("jerseyNumber") or ""), "bild": datei})
        aus[team] = liste
        print(f"{team}: {len(liste)} Spieler mit Foto")
    # Fotos von Spielern, die in keinem Kader mehr stehen, wieder entfernen
    for f in os.listdir(os.path.join(REPO, ORDNER)):
        if f not in gebraucht:
            os.remove(os.path.join(REPO, ORDNER, f))
    with open(LISTE, "w", encoding="utf-8") as f:
        json.dump(aus, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
