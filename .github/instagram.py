# Holt die neuesten Instagram-Beitraege und schreibt sie nach instagram-daten.js
# (window.SCH_INSTAGRAM); instagram.js baut daraus die Karten im Social-Block der Startseite.
# Laeuft in der GitHub Action .github/workflows/seite.yml. Bilder und instagram-daten.js
# landen NUR im Pages-Artefakt (IG_ZIEL = Kopie der Seite), nie im Repo: ein auf Instagram
# geloeschter Beitrag bliebe sonst fuer immer im oeffentlichen Git-Verlauf (Abnahme 07.10.2026,
# AB3-2). Besucher laden trotzdem nichts von Instagram oder Meta, die Bilder liegen auf Pages.
# index.html fasst der Bot NICHT an (Bugjagd 07.10.2026, T5-11: sonst Merge-Konflikte mit
# jeder Handaenderung, die Startseite ist eine einzige lange Zeile).
#
# Umgebung:
#   IG_TOKEN    Zugangsschluessel (Instagram API with Instagram Login), nur als GitHub-Secret
#   IG_ERNEUERN 1 = Schluessel um 60 Tage verlaengern, neuer Schluessel nach $RUNNER_TEMP/ig_token
#   IG_PROBE    Pfad zu einer JSON-Datei statt der echten Abfrage (lokaler Test)
#   IG_ZIEL     Pflicht: Ordner, in den instagram-daten.js und assets/instagram/ geschrieben werden
#               (im Workflow _site, nie der Repo-Ordner)
import io, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image

STAMM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.environ.get('IG_ZIEL', '').strip()
ORDNER = os.path.join(ZIEL, 'assets', 'instagram')
ANZAHL = 6
API = 'https://graph.instagram.com'
KONTO = 'https://www.instagram.com/sc1911heiligenstadt/'


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sch-website'}), timeout=30) as r:
        return r.read()


def abfrage(pfad, token, **werte):
    werte['access_token'] = token
    return json.loads(hole(f'{API}/{pfad}?{urllib.parse.urlencode(werte)}'))


def ausgabe(wert):
    # Ergebnis fuer den Workflow (steps.<id>.outputs.ig): neu | leer; ohne Schluessel bleibt es leer.
    datei = os.environ.get('GITHUB_OUTPUT')
    if datei:
        with open(datei, 'a') as f: f.write('ig=' + wert + '\n')


def kurz(text, laenge=150):
    text = re.sub(r'\s+', ' ', text or '').strip()
    if len(text) <= laenge: return text
    return text[:laenge].rsplit(' ', 1)[0].rstrip('.,;:–-') + ' …'


def karte(b, datei):
    # Nur Daten; das HTML baut instagram.js per DOM (textContent, kein innerHTML).
    zeit = datetime.strptime(b['timestamp'], '%Y-%m-%dT%H:%M:%S%z').astimezone(ZoneInfo('Europe/Berlin'))
    return {
        'href': b['permalink'],
        'bild': datei,
        'art': {'VIDEO': 'Video', 'CAROUSEL_ALBUM': 'Bilderserie'}.get(b.get('media_type'), 'Bild'),
        'datum': zeit.strftime('%d.%m.%Y'),
        'iso': zeit.isoformat(),
        'text': kurz(b.get('caption')),
    }


def main():
    token = os.environ.get('IG_TOKEN', '').strip()
    probe = os.environ.get('IG_PROBE')
    if not token and not probe:
        print('Kein IG_TOKEN gesetzt, nichts zu tun.')
        return
    if not ZIEL or os.path.abspath(ZIEL) == STAMM:
        sys.exit('IG_ZIEL fehlt oder ist der Repo-Ordner -- Instagram-Daten gehoeren nur ins Pages-Artefakt.')
    if token: print('::add-mask::' + token)

    if token and os.environ.get('IG_ERNEUERN') == '1':
        neu = abfrage('refresh_access_token', token, grant_type='ig_refresh_token')
        print('::add-mask::' + neu['access_token'])
        open(os.path.join(os.environ.get('RUNNER_TEMP', STAMM), 'ig_token'), 'w').write(neu['access_token'])
        print('Schluessel verlaengert, gueltig noch', neu.get('expires_in', 0) // 86400, 'Tage.')

    # Mehr holen als gebraucht: Beitraege ohne Bild-Adresse (Meta laesst media_url z. B. bei
    # lizenzierter Musik weg) werden uebersprungen, die naechsten fuellen auf (T5-12).
    if probe:
        antwort = json.load(open(probe, encoding='utf-8'))
    else:
        antwort = abfrage('me/media', token, fields='id,caption,media_type,media_url,thumbnail_url,permalink,timestamp', limit=ANZAHL * 3)
    beitraege = antwort.get('data') if isinstance(antwort, dict) else None
    if not isinstance(beitraege, list):
        sys.exit('Unerwartete Antwort von Instagram (kein data) -- nichts geaendert.')

    os.makedirs(ORDNER, exist_ok=True)
    karten, behalten = [], set()
    for b in beitraege:
        if len(karten) >= ANZAHL: break
        if not isinstance(b, dict): continue
        if b.get('media_type') == 'VIDEO':
            quelle = b.get('thumbnail_url') or b.get('media_url')
        else:
            quelle = b.get('media_url') or b.get('thumbnail_url')
        if not quelle or not b.get('permalink') or not b.get('id') or not b.get('timestamp'): continue
        datei = re.sub(r'[^0-9A-Za-z_]', '', str(b['id'])) + '.webp'
        ziel = os.path.join(ORDNER, datei)
        if not os.path.exists(ziel):
            bild = Image.open(io.BytesIO(hole(quelle))).convert('RGB')
            bild.thumbnail((800, 800))
            bild.save(ziel, 'WEBP', quality=80)
        behalten.add(datei)
        karten.append(karte(b, datei))
    # Leere/lueckenhafte Antwort ({"data": []} oder nur Beitraege ohne Bild): NICHTS schreiben,
    # der Platzhalter aus dem Repo (keine Karten) bleibt im Artefakt. ig=leer sagt dem Workflow:
    # ein geplanter Lauf veroeffentlicht dann nicht, die Seite bleibt, wie sie ist (T5-12).
    if not karten:
        print('Keine verwertbaren Beitraege in der Antwort -- Karten und Bilder bleiben, wie sie sind.')
        ausgabe('leer')
        return
    for alt in os.listdir(ORDNER):
        if alt not in behalten: os.remove(os.path.join(ORDNER, alt))

    # ensure_ascii: auch U+2028/U+2029 aus einer Caption landen als \u-Folge in der JS-Datei
    # (alte Safari werten sie sonst als Zeilenende mitten im String).
    daten = json.dumps(karten, ensure_ascii=True, indent=1)
    text = ('// Wird von der GitHub Action (.github/instagram.py) beim Pages-Bau geschrieben, liegt nicht im Repo.\n'
            'window.SCH_INSTAGRAM = ' + daten + ';\n')
    open(os.path.join(ZIEL, 'instagram-daten.js'), 'wb').write(text.encode('utf-8'))
    print(len(karten), 'Beitraege eingebaut.')
    ausgabe('neu')


main()
