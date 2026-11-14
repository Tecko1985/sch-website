"""Live-Ticker während der Spiele (Ablauf .github/workflows/live.yml).

  python3 werkzeuge/live.py pruefen   -> steht ein SCH-Spiel an oder läuft eins? (GITHUB_OUTPUT aktiv=1)
  python3 werkzeuge/live.py laufen    -> fragt bis kurz nach Abpfiff jede Minute den FuPa-Ticker ab und legt
                                         ticker.json auf den Branch "live" (nur diese eine Datei, ohne Verlauf).
  python3 werkzeuge/live.py probe     -> schreibt ticker.json einmal nach stdout (zum Testen, ohne Push)

Die Website (live.js: Startseite und seiten/live.html) liest ticker.json über GitHub, nicht bei FuPa.
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fupa_ticker  # noqa: E402
import spiele  # noqa: E402
import spielbericht  # noqa: E402

VORLAUF = datetime.timedelta(minutes=45)      # so lange vor Anpfiff geht es los
SPIELDAUER = datetime.timedelta(minutes=150)  # danach gilt ein Spiel ohne FuPa-Ende als vorbei
NACHLAUF = datetime.timedelta(minutes=15)     # so lange nach Abpfiff läuft der Ablauf weiter
HOECHSTENS = datetime.timedelta(hours=5)
TAKT = 60  # Sekunden


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def anpfiff(m):
    return datetime.datetime.fromisoformat(m["kickoff"])


def mannschaft(kuerzel):
    if kuerzel == "m1":
        return "1. Mannschaft"
    if kuerzel == "m2":
        return "2. Mannschaft"
    return spiele.JUGEND.get(kuerzel, (kuerzel.upper(), False))[0]


def anstehende():
    """SCH-Spiele aller Mannschaften der Startseite, die jetzt anstehen oder laufen."""
    t = jetzt()
    aus = []
    for m in spiele.spiele_von_fupa():
        seite, kuerzel = spiele.sch_team(m)
        if not seite or not m.get("kickoff"):
            continue
        a = anpfiff(m)
        if a - VORLAUF <= t <= a + SPIELDAUER:
            aus.append((m["slug"], kuerzel))
    return aus


def team(t):
    name = fupa_ticker._teamname(t)
    sch = "1911 Heiligenstadt" in name
    return {"name": name, "kurz": "SCH" if sch else ((t.get("name") or {}).get("middle") if isinstance(t.get("name"), dict) else "") or name,
            "sch": sch, "wappen": spielbericht.SCH_WAPPEN if sch
            else (spielbericht.wappen_fuer(name) or spielbericht.LEER_WAPPEN)}


def mit_ticker(m):
    return bool(m.get("tickerType")) or "ticker" in (m.get("flags") or [])


_AUFSTELLUNG = {}  # slug -> (Zeitpunkt, Aufstellung oder None)


def aufstellung(slug, m):
    """Aufstellung höchstens alle 5 Minuten neu bei FuPa holen (vor Anpfiff kann sie sich noch ändern)."""
    zeit, auf = _AUFSTELLUNG.get(slug, (None, None))
    if zeit is None or jetzt() - zeit > datetime.timedelta(minutes=5):
        try:
            auf = fupa_ticker.aufstellung(slug, m) or auf
        except Exception as fehler:
            print(f"  {slug}: Aufstellung nicht geladen ({fehler})", file=sys.stderr)
        _AUFSTELLUNG[slug] = (jetzt(), auf)
    return auf


def lage(slug, kuerzel):
    m = fupa_ticker.spiel(slug)
    if not mit_ticker(m):
        return None  # ohne FuPa-Ticker gibt es nichts zu zeigen
    try:
        ev = fupa_ticker.ereignisse(fupa_ticker.stream(slug))
    except Exception:
        ev = []
    abpfiff = any(e["art"] == "pfiff" and e["kopf"].lower().startswith("abpfiff") for e in ev)
    angepfiffen = any(e["art"] == "pfiff" for e in ev) or m.get("section") == "LIVE"
    status = "ende" if abpfiff or m.get("section") == "POST" else "live" if angepfiffen else "vor"
    minute = next((e["min"] for e in ev if e["sort"] > 0), "") if status == "live" else ""
    auf = fupa_ticker.mit_ereignissen(aufstellung(slug, m), ev)
    return {
        "slug": slug, "fupa": f"https://www.fupa.net/match/{slug}", "mannschaft": mannschaft(kuerzel),
        "wettbewerb": spiele.wettbewerb((m.get("competition") or {}).get("middleName") or (m.get("competition") or {}).get("name")),
        "anstoss": m.get("kickoff"), "status": status, "minute": minute,
        "heim": team(m.get("homeTeam") or {}), "gast": team(m.get("awayTeam") or {}),
        "tore": [m.get("homeGoal"), m.get("awayGoal")],
        "ereignisse": [{k: e[k] for k in ("min", "art", "kopf", "text", "stand")} for e in ev],
        **({"aufstellung": auf} if auf else {}),
    }


def daten(liste):
    spiele_ = []
    for slug, kuerzel in liste:
        try:
            x = lage(slug, kuerzel)
            if x:
                spiele_.append(x)
        except Exception as fehler:
            print(f"  {slug}: {fehler}", file=sys.stderr)
    spiele_.sort(key=lambda s: (s["status"] != "live", s["mannschaft"] != "1. Mannschaft", s["anstoss"] or ""))
    return {"aktualisiert": jetzt().isoformat(timespec="seconds"), "spiele": spiele_}


def veroeffentlichen(inhalt):
    """ticker.json als einzigen Commit auf den Branch "live" legen (Verlauf wird jedes Mal ersetzt)."""
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "ticker.json"), "w", encoding="utf-8") as f:
            json.dump(inhalt, f, ensure_ascii=False, separators=(",", ":"))
        git = ["git", "-C", d, "-c", "user.name=Live-Ticker", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com"]
        subprocess.run(git + ["init", "-q", "-b", "live"], check=True)
        subprocess.run(git + ["add", "ticker.json"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "Live-Ticker"], check=True)
        subprocess.run(git + ["push", "-q", "--force", f"https://x-access-token:{token}@github.com/{repo}.git", "HEAD:live"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def laufen():
    start, liste, zuletzt, alt, ende_seit = jetzt(), [], None, None, None
    while jetzt() - start < HOECHSTENS:
        if zuletzt is None or jetzt() - zuletzt > datetime.timedelta(minutes=10):
            try:  # Spielliste alle 10 Minuten neu (z. B. Anpfiff eines weiteren Spiels)
                neu = anstehende()
                liste = neu + [x for x in liste if x not in neu]
            except Exception as fehler:
                print(f"Spielliste nicht geladen: {fehler}", file=sys.stderr)
            zuletzt = jetzt()
        if not liste:
            print("Kein Spiel.")
            break
        inhalt = daten(liste)
        if not inhalt["spiele"]:
            # (noch) kein Spiel mit FuPa-Ticker: weiter warten, solange eines ansteht
            time.sleep(TAKT)
            continue
        vergleich = json.dumps(inhalt["spiele"], sort_keys=True)
        if vergleich != alt:
            try:
                veroeffentlichen(inhalt)
                alt = vergleich
                print(jetzt().strftime("%H:%M:%S"), " · ".join(f'{s["mannschaft"]} {s["status"]} {s["tore"]}' for s in inhalt["spiele"]))
            except subprocess.CalledProcessError as fehler:
                print(f"Push fehlgeschlagen: {fehler}", file=sys.stderr)
        alle_aus = all(s["status"] == "ende" for s in inhalt["spiele"]) or all(
            jetzt() > anpfiff({"kickoff": s["anstoss"]}) + SPIELDAUER for s in inhalt["spiele"] if s["anstoss"])
        if alle_aus:
            ende_seit = ende_seit or jetzt()
            if jetzt() - ende_seit > NACHLAUF:
                print("Alle Spiele vorbei.")
                break
        else:
            ende_seit = None
        time.sleep(TAKT)


def main():
    art = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if art == "pruefen":
        liste = [x for x in anstehende() if mit_ticker(fupa_ticker.spiel(x[0]))]
        print("Anstehend mit Ticker:", liste or "nichts")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"aktiv={'1' if liste else '0'}\n")
    elif art == "laufen":
        laufen()
    else:
        slugs = sys.argv[2:]
        liste = [(s, "m1") for s in slugs] or anstehende()
        print(json.dumps(daten(liste), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
