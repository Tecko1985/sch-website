"""Wochenend-Übersicht („Unsere Spiele am Wochenende im Überblick“) als Spielkarten.

Die Redaktion schreibt die Spiele wie gewohnt als Text, z. B.

    ———————————
    U17 | B1
    SCH vs. SV SCHOTT JENA
    SAMSTAG | 14.NOV.26 | 10:30 Uhr
    KuRa Gesundbrunnen

karten() erkennt diese Blöcke und baut daraus Karten (Mannschaft, Uhrzeit, Paarung mit der Heimmannschaft
zuerst, Heim/Auswärts, Spielort), nach Tag und Uhrzeit sortiert. Text vor der Übersicht (z. B. das Spiel der
Ersten mit Liveticker-Link) bleibt, wie er ist. Lässt sich ein Teil nicht sicher zuordnen, bleibt der ganze
Beitrag unverändert – es geht nie Text verloren.
"""
import datetime
import html
import re

MONATE = {"JAN": 1, "FEB": 2, "MÄR": 3, "MAR": 3, "MRZ": 3, "APR": 4, "MAI": 5, "JUN": 6, "JUL": 7, "AUG": 8,
          "SEP": 9, "OKT": 10, "NOV": 11, "DEZ": 12}
MONATSNAME = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
WOCHENTAG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

TRENNER = re.compile(r"^[—–\-_=*·.\s]{5,}$")
# „SAMSTAG | 14.NOV.26 | 10:30 Uhr“, „Sonntag, 08.11.26 | 13:30 Uhr“, „Samstag / 10.OKT.26 | 12:30“ (+ evtl. Ort)
DATUM = re.compile(r"^(?:🕒\s*)?(?:Mo|Di|Mi|Do|Fr|Sa|So)[a-zä]*\s*[,|/]?\s*(\d{1,2})\.\s*(\d{1,2}|[A-ZÄ]{3})\.?\s*(\d{2}|\d{4})"
                   r"\s*[|,/]?\s*(\d{1,2})[:.](\d{2})(?:\s*Uhr)?\.?\s*(.*)$", re.I)
PAARUNG = re.compile(r"^(.+?)\s+vs\.?\s+(.+?)\.?$", re.I)
# Mannschaft am Zeilenanfang, wenn sie mit der Paarung in einer Zeile steht („U13 / D1 SCH vs. JFC Gera“)
TEAM_VORN = re.compile(r"^((?:U\s?\d{1,2}|Reserve|Herren|Frauen|Alte Herren|Bambini)"
                       r"(?:\s*[|/]\s*[A-Z]\d(?:-Junioren)?)?)\s+(.+\svs\.?\s.+)$", re.I)
WIR = re.compile(r"^(?:1\.\s*)?SC(?:H| 1911 Heiligenstadt| Heiligenstadt)(?:\s+(?:II|III|IV|2|3))?$", re.I)


def _zeilen(text):
    t = re.sub(r"<br\s*/?>", "\n", text)
    t = re.sub(r"</(p|h[1-6]|li|div)>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", z).strip() for z in t.split("\n")]


def _datum(m):
    tag, monat, jahr = int(m.group(1)), m.group(2).upper(), int(m.group(3))
    monat = int(monat) if monat.isdigit() else MONATE.get(monat)
    if not monat:
        return None
    jahr = jahr + 2000 if jahr < 100 else jahr
    try:
        return datetime.date(jahr, monat, tag)
    except ValueError:
        return None


def _team_label(zeile):
    zusatz = ""
    m = re.search(r"\(([^)]+)\)\s*$", zeile)
    if m:
        zusatz, zeile = m.group(1).strip(), zeile[:m.start()].strip()
    teile = [p.strip() for p in re.split(r"\s*[|/]\s*", zeile) if p.strip()]
    # „U15 / C-Junioren / Testspiel“: Junioren-Bezeichnung weglassen, „Testspiel“ ist der Wettbewerb
    teile = [p for p in teile if not re.match(r"^[A-G]-Junioren$", p, re.I)]
    if len(teile) > 1 and re.match(r"(?i)^(testspiel|freundschaftsspiel|pokal|kreispokal|landespokal|turnier|.*liga|.*klasse)$", teile[-1]):
        zusatz = zusatz or teile.pop()
    return " · ".join(teile), zusatz


def _ist_team(zeile):
    return bool(re.match(r"(?i)^(U\s?\d{1,2}|Reserve|Herren|Frauen|Alte Herren|Bambini)\b", zeile)) and " vs" not in zeile.lower()


def _spiele(zeilen):
    """Zeilen der Übersicht -> Liste von Spielen oder None (nicht sicher erkennbar)."""
    spiele, aktuell, rest = [], None, []
    for z in zeilen:
        if not z or TRENNER.match(z):
            continue
        m_team_vorn = TEAM_VORN.match(z)
        if (m_team_vorn or _ist_team(z)) and rest:
            return None
        if m_team_vorn:
            if aktuell and aktuell.get("paarung"):
                spiele.append(aktuell)
            aktuell = {"team": m_team_vorn.group(1)}
            z = m_team_vorn.group(2)
        elif _ist_team(z):
            if aktuell and aktuell.get("paarung"):
                spiele.append(aktuell)
            aktuell = {"team": z}
            continue
        m = PAARUNG.match(z)
        if m and aktuell is not None and "paarung" not in aktuell:
            aktuell["paarung"] = (m.group(1).strip(), m.group(2).strip())
            continue
        m = DATUM.match(z)
        if m and aktuell is not None and "paarung" in aktuell and "datum" not in aktuell:
            d = _datum(m)
            if not d:
                return None
            aktuell["datum"], aktuell["zeit"] = d, f"{int(m.group(4)):02d}:{m.group(5)}"
            ort = m.group(6).strip(" .")
            if ort:
                aktuell["ort"] = ort
            continue
        if aktuell is not None and "datum" in aktuell and "ort" not in aktuell:
            aktuell["ort"] = z.rstrip(".")
            continue
        if aktuell is not None and "datum" in aktuell:
            # Text nach dem letzten Spiel („Auf geht’s!“) ist erlaubt; folgt danach noch ein Spiel -> abbrechen
            rest.append(z)
            continue
        return None
    if aktuell and aktuell.get("paarung"):
        spiele.append(aktuell)
    if any("datum" not in s for s in spiele):
        return None
    return spiele, rest


def _seite(name):
    return bool(WIR.match(name.strip()))


def _karte(s):
    e = lambda x: html.escape(x, quote=True)
    label, zusatz = _team_label(s["team"])
    heim, gast = s["paarung"]
    wir_heim, wir_gast = _seite(heim), _seite(gast)
    art = "heim" if wir_heim and not wir_gast else "auswaerts" if wir_gast and not wir_heim else ""
    namen = "".join(f'<span class="sp-wir">{e(n)}</span>' if _seite(n) else f"<span>{e(n)}</span>" for n in (heim, gast))
    fuss = []
    if art == "heim":
        fuss.append("Heim")
    elif art == "auswaerts":
        fuss.append("Auswärts")
    if zusatz:
        fuss.append(zusatz)
    if s.get("ort"):
        fuss.append(s["ort"])
    return (f'<div class="sp-spiel{" sp-" + art if art else ""}"><div class="sp-spielkopf"><span class="sp-team">{e(label)}</span>'
            f'<time>{e(s["zeit"])}</time></div><div class="sp-paarung">{namen}</div>'
            + (f'<div class="sp-spielfuss">{e(" · ".join(fuss))}</div>' if fuss else "") + "</div>")


def karten(text):
    """HTML eines Beitrags; Übersicht durch Karten ersetzt, sonst unverändert."""
    if not text or " vs" not in text:
        return text
    # Beginn der Übersicht: der Absatz „… im Überblick“, sonst der erste Absatz mit einem Trennstrich-Block
    m = re.search(r"<p>[^<]*im Überblick[^<]*</p>\s*", text, re.I)
    if m:
        vorher, uebersicht, ueberschrift = text[:m.start()], text[m.end():], re.sub(r"<[^>]+>", "", m.group(0)).strip()
    else:
        m = re.search(r"<p>\s*[—–\-_]{5,}", text)
        if not m:
            return text
        # Ein Spiel steht oft schon vor dem ersten Trennstrich: bis zum Absatz mit dessen Mannschaft zurück
        absaetze = [a.start() for a in re.finditer(r"<p>", text[:m.start()])]
        start = m.start()
        for a in reversed(absaetze):
            z = _zeilen(text[a:start])
            if z and z[0] and _ist_team(z[0]):
                start = a
                break
        vorher, uebersicht, ueberschrift = text[:start], text[start:], "Unsere Spiele am Wochenende"
    ergebnis = _spiele(_zeilen(uebersicht))
    if not ergebnis:
        return text
    spiele, rest = ergebnis
    if len(spiele) < 2:
        return text
    tage = {}
    for s in spiele:
        tage.setdefault(s["datum"], []).append(s)
    teile = [f'<div class="sp-spieltag"><h3>{html.escape(ueberschrift)}</h3>']
    for d in sorted(tage):
        titel = f"{WOCHENTAG[d.weekday()]}, {d.day}. {MONATSNAME[d.month]}"
        teile.append(f'<h4>{titel}</h4><div class="sp-spiele">'
                     + "".join(_karte(s) for s in sorted(tage[d], key=lambda s: s["zeit"])) + "</div>")
    teile.append("</div>")
    nachher = "".join(f"<p>{html.escape(z)}</p>" for z in rest)
    return vorher.rstrip() + "\n" + "".join(teile) + ("\n" + nachher if nachher else "")
