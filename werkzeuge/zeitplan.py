"""Zeitplan-Wächter (Ablauf .github/workflows/zeitplan.yml).

GitHubs zeitgesteuerte Abläufe (cron) starten oft stark verspätet oder gar nicht. Deshalb wartet dieser
Wächter selbst bis zum nächsten Termin und stößt dann den passenden Ablauf an:
- geplanter Redaktionsbeitrag ("geplant") erreicht  -> "Seite bauen"
- SCH-Spiel beginnt in 45 Minuten (alle Mannschaften) -> "Live-Ticker" (wartet selbst auf den FuPa-Ticker)

Der Wächter startet bei jedem Push auf main neu (der neue ersetzt den alten, siehe concurrency) und
startet sich vor Ablauf der GitHub-Höchstlaufzeit selbst neu. Ein stündlicher cron ist nur Rückfallebene.
Nur Python-Standardbibliothek (+ tzdata für die deutsche Zeit).
"""
import datetime
import glob
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geplant  # noqa: E402
import spiele  # noqa: E402
from beitraege import REPO  # noqa: E402

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    BERLIN = datetime.timezone(datetime.timedelta(hours=1))

VORLAUF = datetime.timedelta(minutes=45)       # Live-Ticker so lange vor Anpfiff starten
SPIELFENSTER = datetime.timedelta(minutes=180)  # bis so lange nach Anpfiff gilt ein Spiel als laufend
LAUFZEIT = datetime.timedelta(hours=5, minutes=30)  # danach neu starten (GitHub: höchstens 6 Stunden je Job)


def jetzt():
    return datetime.datetime.now(BERLIN)


def api(pfad, daten=None):
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{pfad}", method="POST" if daten is not None else "GET",
                                 data=json.dumps(daten).encode() if daten is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "User-Agent": "SCH-Zeitplan"})
    with urllib.request.urlopen(req, timeout=30) as r:
        inhalt = r.read()
        return json.loads(inhalt) if inhalt else {}


def starte(ablauf):
    try:
        api(f"actions/workflows/{ablauf}/dispatches", {"ref": "main"})
        print(f"{jetzt():%d.%m. %H:%M:%S}  {ablauf} gestartet")
    except Exception as fehler:
        print(f"{ablauf} nicht gestartet: {fehler}")


def laeuft(ablauf):
    try:
        for status in ("in_progress", "queued"):
            if api(f"actions/workflows/{ablauf}/runs?status={status}&per_page=1").get("total_count"):
                return True
    except Exception:
        pass
    return False


def geplante_termine():
    """Zukünftige "geplant"-Zeitpunkte der Redaktionsbeiträge (deutsche Zeit)."""
    aus = []
    for pfad in glob.glob(os.path.join(REPO, "inhalte/beitraege/*.json")):
        try:
            d = json.load(open(pfad, encoding="utf-8"))
        except Exception:
            continue
        g = str(d.get("geplant") or "")
        if g and not d.get("entwurf"):
            try:
                aus.append(datetime.datetime.strptime(g, "%Y-%m-%dT%H:%M").replace(tzinfo=BERLIN))
            except ValueError:
                pass
    return aus


def anstoesse():
    try:
        return sorted({datetime.datetime.fromisoformat(m["kickoff"]) for m in spiele.spiele_von_fupa()
                       if m.get("kickoff") and spiele.sch_team(m)[0]})
    except Exception as fehler:
        print(f"Spiele nicht geladen: {fehler}")
        return []


def main():
    start = jetzt()
    # Schon fällig, aber noch nicht online (z. B. während eines Neustarts verpasst)?
    if geplant.faellige():
        starte("seite.yml")
    spiel_zeiten = anstoesse()
    if any(a - VORLAUF <= jetzt() <= a + SPIELFENSTER for a in spiel_zeiten) and not laeuft("live.yml"):
        starte("live.yml")
    erledigt = set()
    while True:
        t = jetzt()
        termine = [(g, "seite.yml") for g in geplante_termine() if g > t]
        termine += [(a - VORLAUF, "live.yml") for a in spiel_zeiten if a - VORLAUF > t]
        termine = sorted(x for x in termine if x not in erledigt)
        ende = start + LAUFZEIT
        if not termine or termine[0][0] > ende:
            warte = (ende - t).total_seconds()
            naechstes = f"nächster Termin {termine[0][0]:%d.%m. %H:%M} ({termine[0][1]})" if termine else "kein Termin"
            print(f"{t:%d.%m. %H:%M}  {naechstes} – warte bis zum Neustart")
            time.sleep(max(0, warte))
            if termine:
                starte("zeitplan.yml")  # weiter warten mit frischer Laufzeit
            return
        zeit, ablauf = termine[0]
        print(f"{t:%d.%m. %H:%M}  warte bis {zeit:%d.%m. %H:%M} ({ablauf})")
        time.sleep(max(0, (zeit - jetzt()).total_seconds()) + 20)
        if ablauf == "live.yml" and laeuft("live.yml"):
            print("Live-Ticker läuft schon.")
        else:
            starte(ablauf)
        erledigt.add((zeit, ablauf))


if __name__ == "__main__":
    main()
