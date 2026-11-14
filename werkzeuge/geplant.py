"""Geplante Redaktionsbeiträge: ist einer fällig, aber noch nicht live?

Aufruf (vom Ablauf .github/workflows/geplant.yml alle 15 Minuten):  python3 werkzeuge/geplant.py
Gibt die fälligen Beiträge aus und schreibt "faellig=1" nach $GITHUB_OUTPUT, wenn die Seite neu
gebaut werden muss. Fällig = "geplant" ist erreicht (deutsche Zeit, höchstens 3 Tage her) und die
Beitragsseite ist auf der Website noch nicht zu finden.
"""
import datetime
import glob
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from beitraege import ADRESSE, REPO, jetzt_berlin  # noqa: E402


def ist_live(seite):
    url = f"{ADRESSE}seiten/{seite}"
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SCH-Webseite (geplante Beitraege)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code != 404
    except Exception:
        return True  # im Zweifel nichts anstoßen


def main():
    jetzt = jetzt_berlin()
    frueheste = (datetime.datetime.strptime(jetzt, "%Y-%m-%dT%H:%M") - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    faellig = []
    for pfad in sorted(glob.glob(os.path.join(REPO, "inhalte/beitraege/*.json"))):
        try:
            d = json.load(open(pfad, encoding="utf-8"))
        except Exception:
            continue
        geplant = str(d.get("geplant") or "")
        if d.get("entwurf") or not geplant or not (frueheste <= geplant <= jetzt):
            continue
        slug = os.path.basename(pfad)[:-5]
        if not ist_live(f"beitrag-{slug}.html"):
            faellig.append(f"{geplant}  {d.get('titel') or slug}")
    if faellig:
        print("Fällig, aber noch nicht online:\n  " + "\n  ".join(faellig))
    else:
        print(f"Nichts fällig ({jetzt}).")
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"faellig={1 if faellig else 0}\n")


if __name__ == "__main__":
    main()
