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
            eintrag.update(art="tor", kopf=f"Tor für {eintrag['team']}" if eintrag["team"] else "Tor",
                           text=(_name(x.get("primaryRole")) or "Tor") + art + (f", Vorlage {vor}" if vor else "") + ".")
            if x.get("homeGoal") is not None and x.get("awayGoal") is not None:
                eintrag["stand"] = f'{x["homeGoal"]}:{x["awayGoal"]}'
        elif typ == "substitute":
            rein, raus = _name(x.get("primaryRole")), _name(x.get("secondaryRole"))
            if not rein:
                continue
            eintrag.update(art="wechsel", kopf=f"Wechsel bei {eintrag['team']}" if eintrag["team"] else "Wechsel",
                           text=f"{rein} kommt" + (f" für {raus}" if raus else "") + ".")
        elif typ == "card":
            rot = "red" in unter and "yellow" not in unter
            gelbrot = "yellow" in unter and "red" in unter
            wer = _name(x.get("primaryRole"))
            farbe = "Rote Karte" if rot else "Gelb-Rote Karte" if gelbrot else "Gelbe Karte"
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


def finde_spiel(spiele, datum, gegner_worte):
    """Passendes FuPa-Spiel (aus einer Liste von FuPa-Spielen) zu Spieldatum und Gegner."""
    for m in spiele:
        if not str(m.get("kickoff", "")).startswith(datum):
            continue
        namen = " ".join(_teamname(m.get(s)) for s in ("homeTeam", "awayTeam")).lower()
        if any(w in namen for w in gegner_worte):
            return m
    return None
