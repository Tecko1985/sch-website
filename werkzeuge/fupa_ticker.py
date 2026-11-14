"""FuPa-Liveticker lesen und in unser Format bringen.

Genutzt von:
- werkzeuge/spielbericht.py: Spielberichte zeigen den FuPa-Ticker (Texte, Tore, Wechsel, Karten, Pfiffe),
  wenn in der Redaktion kein eigener Ticker steht.
- werkzeuge/live.py: Live-Ticker während des Spiels (Startseite und seiten/live.html).

Nur Python-Standardbibliothek. Der Browser fragt nie selbst bei FuPa an (FuPa erlaubt das fremden
Seiten nicht, und so gehen keine Besucherdaten an FuPa).
"""
import json
import re
import urllib.request

API = "https://api.fupa.net"


def hole_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SCH-Webseite)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def hole_text(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SCH-Webseite)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def slug_aus_link(link):
    """„https://www.fupa.net/match/<slug>“ (auch mit /ticker o. ä. dahinter) -> slug"""
    m = re.search(r"fupa\.net/match/([a-z0-9-]+)", link or "")
    return m.group(1) if m else None


def spiel(slug):
    return hole_json(f"{API}/v1/matches/{slug}")


def stream(slug):
    return hole_json(f"{API}/v2/matches/{slug}/stream")


def _name(rolle):
    p = (rolle or {}).get("player") or {}
    return " ".join(x for x in (p.get("firstName"), p.get("lastName")) if x).strip()


def _teamname(t):
    if not isinstance(t, dict):
        return ""
    n = t.get("name")
    if isinstance(n, dict):
        return n.get("full") or n.get("middle") or ""
    return n or ""


def kurz(name):
    return "SCH" if "1911 Heiligenstadt" in (name or "") else (name or "")


def ereignisse(daten):
    """Stream -> Liste von Einträgen, neueste zuerst.

    Eintrag: {"sort": float, "min": "45+1", "art": tor|wechsel|karte|gelb|pfiff|text,
              "kopf": str, "text": str, "stand": "1:0" oder "", "team": Teamname oder ""}
    """
    aus = []
    for roh in daten or []:
        if roh.get("type") != "matchevent":
            continue
        x = roh.get("entity") or {}
        typ, unter = x.get("type") or "", (x.get("subtype") or "").lower()
        n, plus = int(x.get("minute") or 0), int(x.get("additionalMinute") or 0)
        eintrag = {"sort": n + plus / 100, "min": f"{n}+{plus}" if plus else str(n), "art": "text",
                   "kopf": "", "text": (x.get("text") or "").strip(), "stand": "", "team": kurz(_teamname(x.get("team")))}
        if typ == "goal":
            art = " (Strafstoß)" if "penalty" in unter else " (Eigentor)" if "own" in unter else " (Kopfball)" if "head" in unter else ""
            vor = _name(x.get("secondaryRole")) if "penalty" not in unter and "own" not in unter else ""
            if "own" not in unter:
                eintrag["_tor"] = _name(x.get("primaryRole"))
            eintrag.update(art="tor", kopf=f"Tor für {eintrag['team']}" if eintrag["team"] else "Tor",
                           text=(_name(x.get("primaryRole")) or "Tor") + art + (f", Vorlage {vor}" if vor else "") + ".")
            if x.get("homeGoal") is not None and x.get("awayGoal") is not None:
                eintrag["stand"] = f'{x["homeGoal"]}:{x["awayGoal"]}'
        elif typ == "substitute":
            rein, raus = _name(x.get("primaryRole")), _name(x.get("secondaryRole"))
            if not rein:
                continue
            eintrag["_rein"], eintrag["_raus"] = rein, raus
            eintrag.update(art="wechsel", kopf=f"Wechsel bei {eintrag['team']}" if eintrag["team"] else "Wechsel",
                           text=f"{rein} kommt" + (f" für {raus}" if raus else "") + ".")
        elif typ == "card":
            rot = "red" in unter and "yellow" not in unter
            gelbrot = "yellow" in unter and "red" in unter
            wer = _name(x.get("primaryRole"))
            farbe = "Rote Karte" if rot else "Gelb-Rote Karte" if gelbrot else "Gelbe Karte"
            eintrag["_karte"] = (wer, "rot" if rot else "gelbrot" if gelbrot else "gelb")
            eintrag.update(art="karte" if (rot or gelbrot) else "gelb", kopf=farbe + (f" für {wer}" if wer else ""),
                           text=eintrag["text"] or (eintrag["team"] + "." if eintrag["team"] else ""))
        elif typ == "whistle":
            kopf = eintrag["text"] or "Pfiff"
            if x.get("homeGoal") is not None and x.get("awayGoal") is not None and "start_first" not in unter:
                eintrag["stand"] = f'{x["homeGoal"]}:{x["awayGoal"]}'
            eintrag.update(art="pfiff", kopf=kopf, text="")
        elif typ == "text":
            if not eintrag["text"]:
                continue
        else:
            continue  # Aufstellung eingetragen u. ä.
        aus.append(eintrag)
    aus.sort(key=lambda e: e["sort"], reverse=True)  # FuPa liefert schon so; sicher ist sicher
    return aus


# ------------------------------------------------------------------ Aufstellung
# FuPa liefert die Aufstellung je nach Spiel unter verschiedenen Adressen und in leicht verschiedenen
# Formen. Darum wird hier tolerant gelesen: alle Spielerlisten unter „home…“/„away…“ suchen, Startelf
# und Bank an Schlüsseln oder Feldern erkennen. Klappt nichts, gibt es einfach keine Aufstellung.
AUFSTELLUNG_ADRESSEN = ("/v1/matches/{slug}/lineup", "/v1/matches/{slug}/lineups")
BANK_WORTE = ("sub", "bench", "reserve", "ersatz")


def _spieler(o):
    """FuPa-Spielereintrag -> {"name", "nr", "tw", "kap"} oder None"""
    if not isinstance(o, dict):
        return None
    p = o.get("player") if isinstance(o.get("player"), dict) else o
    name = " ".join(x for x in (p.get("firstName"), p.get("lastName")) if isinstance(x, str) and x).strip()
    if not name or not p.get("lastName"):
        return None
    nr = o.get("jerseyNumber", o.get("shirtNumber", o.get("number", p.get("jerseyNumber"))))
    pos = " ".join(str(o.get(k) or "") for k in ("position", "positionName", "role")).lower()
    return {"name": name, "nr": str(nr) if isinstance(nr, (int, str)) and str(nr).isdigit() else "",
            "tw": bool(o.get("isKeeper") or o.get("goalkeeper") or o.get("isGoalkeeper") or "keeper" in pos or "torwart" in pos),
            "kap": bool(o.get("isCaptain") or o.get("captain") or o.get("isTeamCaptain"))}


def _ist_bank(o, schluessel):
    if any(w in (schluessel or "").lower() for w in BANK_WORTE):
        return True
    if isinstance(o, dict):
        if o.get("isSubstitute") or o.get("substitute") is True or o.get("isBench") or o.get("bench") is True:
            return True
        if o.get("isStarting") is False or o.get("starting") is False or o.get("isStartingEleven") is False:
            return True
        art = str(o.get("lineupType") or o.get("type") or o.get("status") or "").lower()
        if any(w in art for w in BANK_WORTE):
            return True
    return False


def _seite(o, schluessel="", bank=False, aus=None, tiefe=0):
    """Alle Spieler unterhalb von o einsammeln -> {"start": [...], "bank": [...]}"""
    aus = aus if aus is not None else {"start": [], "bank": [], "_namen": set()}
    if tiefe > 6:
        return aus
    if isinstance(o, list):
        for x in o:
            _seite(x, schluessel, bank, aus, tiefe + 1)
    elif isinstance(o, dict):
        sp = _spieler(o)
        if sp:
            if sp["name"] not in aus["_namen"]:
                aus["_namen"].add(sp["name"])
                aus["bank" if bank or _ist_bank(o, "") else "start"].append(sp)
            return aus
        for k, v in o.items():
            if k in ("team", "club", "coach", "trainer", "referee", "image", "events"):
                continue
            if isinstance(v, (list, dict)):
                _seite(v, k, bank or _ist_bank(None, k), aus, tiefe + 1)
    return aus


def _seiten_finden(daten, heim_name=""):
    """Rohdaten -> (heim, gast) als Python-Objekte, die die Spieler enthalten, oder (None, None)"""
    if isinstance(daten, dict):
        for h, g in (("homeTeam", "awayTeam"), ("home", "away"), ("homeLineup", "awayLineup"),
                     ("homeTeamLineup", "awayTeamLineup"), ("homePlayers", "awayPlayers")):
            if daten.get(h) is not None and daten.get(g) is not None:
                return daten[h], daten[g]
        for k in ("lineup", "lineups", "data"):
            if isinstance(daten.get(k), (dict, list)):
                return _seiten_finden(daten[k], heim_name)
    if isinstance(daten, list) and len(daten) == 2 and all(isinstance(x, dict) for x in daten):
        a, b = daten
        seite_a = str(a.get("side") or a.get("type") or "").lower()
        if seite_a.startswith("away") or (heim_name and heim_name in (_teamname(b.get("team")) or "")):
            a, b = b, a
        return a, b
    return None, None


def aufstellung(slug, m=None):
    """FuPa-Aufstellung eines Spiels -> {"heim": {"start": [...], "bank": [...]}, "gast": {...}} oder None.
    Spieler: {"name", "nr", "tw", "kap"}; Tore, Karten und Wechsel schreibt mit_ereignissen() dazu."""
    quellen = [m or {}]
    for adresse in AUFSTELLUNG_ADRESSEN:
        try:
            quellen.append(hole_json(API + adresse.format(slug=slug), timeout=15))
        except Exception:
            continue
    heim_name = _teamname((m or {}).get("homeTeam"))
    for q in quellen:
        h, g = _seiten_finden(q, heim_name)
        if h is None:
            continue  # (im Spiel selbst stehen unter homeTeam/awayTeam meist nur die Vereine)
        heim, gast = _seite(h), _seite(g)
        if len(heim["start"]) + len(gast["start"]) >= 7:
            for x in (heim, gast):
                del x["_namen"]
            return {"heim": heim, "gast": gast}
    return None


def mit_ereignissen(auf, ev):
    """Kopie der Aufstellung mit Toren, Karten und Wechseln aus den Ticker-Ereignissen."""
    if not auf:
        return None
    neu = json.loads(json.dumps(auf))
    for seite in neu.values():
        _ereignisse_eintragen(seite, ev)
    return neu


def _gleich(a, b):
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    return bool(a and b) and (a == b or a.split()[-1] == b.split()[-1] and (a in b or b in a or a[0] == b[0]))


def _ereignisse_eintragen(seite, ev):
    for sp in seite["start"] + seite["bank"]:
        for e in sorted(ev, key=lambda x: x["sort"]):
            if _gleich(e.get("_tor"), sp["name"]):
                sp["tore"] = sp.get("tore", 0) + 1
            if _gleich(e.get("_rein"), sp["name"]):
                sp["ein"] = e["min"]
            if _gleich(e.get("_raus"), sp["name"]):
                sp["aus"] = e["min"]
            if e.get("_karte") and _gleich(e["_karte"][0], sp["name"]):
                sp["karte"] = e["_karte"][1]


def finde_spiel(spiele, datum, gegner_worte):
    """Passendes FuPa-Spiel (aus einer Liste von FuPa-Spielen) zu Spieldatum und Gegner."""
    for m in spiele:
        if not str(m.get("kickoff", "")).startswith(datum):
            continue
        namen = " ".join(_teamname(m.get(s)) for s in ("homeTeam", "awayTeam")).lower()
        if any(w in namen for w in gegner_worte):
            return m
    return None
