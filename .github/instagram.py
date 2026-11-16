# Holt die neuesten Instagram-Beitraege und schreibt sie nach instagram-daten.js:
#   window.SCH_INSTAGRAM           Vereinskonto  -> Karten im Social-Block der Startseite
#   window.SCH_INSTAGRAM_NACHWUCHS Nachwuchskonto -> Block "Neu auf Instagram" auf seiten/nachwuchs.html
# (instagram.js baut daraus die Karten.)
# Laeuft in der GitHub Action .github/workflows/seite.yml. Bilder und instagram-daten.js
# landen NUR im Pages-Artefakt (IG_ZIEL = Kopie der Seite), nie im Repo: ein auf Instagram
# geloeschter Beitrag bliebe sonst fuer immer im oeffentlichen Git-Verlauf (Abnahme 07.10.2026,
# AB3-2). Besucher laden trotzdem nichts von Instagram oder Meta, die Bilder liegen auf Pages.
# index.html fasst der Bot NICHT an (Bugjagd 07.10.2026, T5-11: sonst Merge-Konflikte mit
# jeder Handaenderung, die Startseite ist eine einzige lange Zeile).
#
# Schluessel (nur als GitHub-Secrets), zwei Arten werden erkannt (16.11.2026):
#   - "IG..."  Instagram API with Instagram Login (alt): graph.instagram.com/me/media, laeuft nach
#              60 Tagen ab, wird montags verlaengert (IG_ERNEUERN).
#   - sonst    Systemnutzer-Token aus "Instagram API with Unified Login" (neue Meta-Apps, App
#              "SCH Webseite"): graph.facebook.com/<IG-Konto-ID>/media, laeuft nie ab. Die Konto-ID
#              sucht das Skript selbst; notfalls Repo-Variable IG_ID / IG_ID_NACHWUCHS (keine Secrets).
#
# Umgebung:
#   IG_TOKEN, IG_TOKEN_NACHWUCHS   Schluessel je Konto (fehlt einer, wird das Konto uebersprungen)
#   IG_ID, IG_ID_NACHWUCHS         optional: Instagram-Konto-ID (Zahl, 1784...)
#   IG_ERNEUERN 1 = alte "IG..."-Schluessel um 60 Tage verlaengern, neuer Schluessel nach $RUNNER_TEMP/<Secret-Name>
#   IG_PROBE, IG_PROBE_NACHWUCHS   Pfad zu einer JSON-Datei statt der echten Abfrage (lokaler Test)
#   IG_ZIEL     Pflicht: Ordner, in den instagram-daten.js und assets/instagram/ geschrieben werden
#               (im Workflow _site, nie der Repo-Ordner)
import io, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image

STAMM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.environ.get('IG_ZIEL', '').strip()
ORDNER = os.path.join(ZIEL, 'assets', 'instagram')
ANZAHL = 6
INSTAGRAM = 'https://graph.instagram.com'
FACEBOOK = 'https://graph.facebook.com'
FELDER = 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp'
# (Secret, JS-Variable, Konto, ID-Variable, Probe-Variable)
KONTEN = [
    ('IG_TOKEN', 'SCH_INSTAGRAM', 'sc1911heiligenstadt', 'IG_ID', 'IG_PROBE'),
    ('IG_TOKEN_NACHWUCHS', 'SCH_INSTAGRAM_NACHWUCHS', 'sc1911heiligenstadt_nachwuchs', 'IG_ID_NACHWUCHS', 'IG_PROBE_NACHWUCHS'),
]


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sch-website'}), timeout=30) as r:
        return r.read()


def abfrage(basis, pfad, token, **werte):
    werte['access_token'] = token
    try:
        return json.loads(hole(f'{basis}/{pfad}?{urllib.parse.urlencode(werte)}'))
    except urllib.error.HTTPError as fehler:
        # Meta schreibt den Grund in den Antworttext (ohne Schluessel); die Adresse (mit Schluessel) nie ausgeben.
        try:
            grund = json.loads(fehler.read()).get('error', {}).get('message', '')
        except Exception:
            grund = ''
        raise RuntimeError(f'{basis.split("//")[1]}/{pfad.split("?")[0]}: HTTP {fehler.code} {grund}'.strip()) from None


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


def konto_id(token, konto, id_variable):
    """Instagram-Konto-ID zu einem Systemnutzer-Token suchen (Unified Login)."""
    fest = os.environ.get(id_variable, '').strip()
    if fest:
        return fest
    kandidaten, gruende = [], []
    # 1) Das Token gehoert direkt zum Instagram-Konto
    try:
        ich = abfrage(FACEBOOK, 'me', token, fields='id,username')
        if ich.get('username'):
            kandidaten.append((ich['id'], ich['username']))
    except RuntimeError as fehler:
        print('  me:', fehler); gruende.append(str(fehler))
    # 2) Freigegebene Konten aus den Berechtigungen des Tokens
    try:
        info = abfrage(FACEBOOK, 'debug_token', token, input_token=token).get('data', {})
        for s in info.get('granular_scopes', []):
            if s.get('scope', '').startswith('instagram'):
                for i in s.get('target_ids', []):
                    try:
                        name = abfrage(FACEBOOK, str(i), token, fields='username').get('username', '')
                    except RuntimeError:
                        name = ''
                    kandidaten.append((str(i), name))
    except RuntimeError as fehler:
        print('  debug_token:', fehler); gruende.append(str(fehler))
    # 3) Ueber eine verknuepfte Facebook-Seite
    try:
        for seite in abfrage(FACEBOOK, 'me/accounts', token, fields='instagram_business_account{id,username}').get('data', []):
            ig = seite.get('instagram_business_account') or {}
            if ig.get('id'):
                kandidaten.append((ig['id'], ig.get('username', '')))
    except RuntimeError as fehler:
        print('  me/accounts:', fehler); gruende.append(str(fehler))
    for i, name in kandidaten:
        if name.lower() == konto:
            return i
    ids = {i for i, _ in kandidaten}
    if len(ids) == 1:
        return ids.pop()
    raise RuntimeError(f'Instagram-Konto-ID fuer {konto} nicht gefunden ({len(ids)} Kandidaten) -- '
                       f'Repo-Variable {id_variable} setzen. ' + ' | '.join(gruende))


def beitraege_holen(secret, konto, id_variable):
    token = os.environ.get(secret, '').strip()
    if token.startswith('IG'):
        if os.environ.get('IG_ERNEUERN') == '1':
            neu = abfrage(INSTAGRAM, 'refresh_access_token', token, grant_type='ig_refresh_token')
            print('::add-mask::' + neu['access_token'])
            open(os.path.join(os.environ.get('RUNNER_TEMP', STAMM), secret), 'w').write(neu['access_token'])
            print('  Schluessel verlaengert, gueltig noch', neu.get('expires_in', 0) // 86400, 'Tage.')
        return abfrage(INSTAGRAM, 'me/media', token, fields=FELDER, limit=ANZAHL * 3)
    try:
        ig_id = konto_id(token, konto, id_variable)
        print('  Konto-ID gefunden.')
        return abfrage(FACEBOOK, f'{ig_id}/media', token, fields=FELDER, limit=ANZAHL * 3)
    except RuntimeError as fehler:
        # Letzter Versuch: manche neuen Schluessel gelten auch direkt bei graph.instagram.com
        try:
            return abfrage(INSTAGRAM, 'me/media', token, fields=FELDER, limit=ANZAHL * 3)
        except RuntimeError as zweiter:
            raise RuntimeError(f'{fehler} | {zweiter}') from None


def karten_bauen(antwort, behalten):
    beitraege = antwort.get('data') if isinstance(antwort, dict) else None
    if not isinstance(beitraege, list):
        raise RuntimeError('Unerwartete Antwort von Instagram (kein data)')
    # Mehr geholt als gebraucht: Beitraege ohne Bild-Adresse (Meta laesst media_url z. B. bei
    # lizenzierter Musik weg) werden uebersprungen, die naechsten fuellen auf (T5-12).
    karten = []
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
    return karten


def main():
    aktiv = [k for k in KONTEN if os.environ.get(k[0], '').strip() or os.environ.get(k[4])]
    if not aktiv:
        print('Kein Instagram-Schluessel gesetzt, nichts zu tun.')
        return
    if not ZIEL or os.path.abspath(ZIEL) == STAMM:
        sys.exit('IG_ZIEL fehlt oder ist der Repo-Ordner -- Instagram-Daten gehoeren nur ins Pages-Artefakt.')
    for k in aktiv:
        token = os.environ.get(k[0], '').strip()
        if token: print('::add-mask::' + token)

    os.makedirs(ORDNER, exist_ok=True)
    behalten, daten, fehler = set(), {}, []
    for secret, variable, konto, id_variable, probe_variable in aktiv:
        print(f'{konto}:')
        try:
            probe = os.environ.get(probe_variable)
            antwort = json.load(open(probe, encoding='utf-8')) if probe else beitraege_holen(secret, konto, id_variable)
            daten[variable] = karten_bauen(antwort, behalten)
            print(' ', len(daten[variable]), 'Beitraege.')
        except Exception as f:
            print(f'::warning::Instagram {konto}: {f}')
            fehler.append(konto)

    # Leere/lueckenhafte Antwort (nur Beitraege ohne Bild oder nur Fehler): NICHTS schreiben,
    # der Platzhalter aus dem Repo (keine Karten) bleibt im Artefakt. ig=leer sagt dem Workflow:
    # ein geplanter Lauf veroeffentlicht dann nicht, die Seite bleibt, wie sie ist (T5-12).
    if not any(daten.values()):
        print('Keine verwertbaren Beitraege -- Karten und Bilder bleiben, wie sie sind.')
        ausgabe('leer')
        if fehler: sys.exit('Instagram-Abruf fehlgeschlagen: ' + ', '.join(fehler))
        return
    for alt in os.listdir(ORDNER):
        if alt not in behalten: os.remove(os.path.join(ORDNER, alt))

    # ensure_ascii: auch U+2028/U+2029 aus einer Caption landen als \u-Folge in der JS-Datei
    # (alte Safari werten sie sonst als Zeilenende mitten im String).
    text = '// Wird von der GitHub Action (.github/instagram.py) beim Pages-Bau geschrieben, liegt nicht im Repo.\n'
    for _, variable, *_ in KONTEN:
        text += f'window.{variable} = ' + json.dumps(daten.get(variable, []), ensure_ascii=True, indent=1) + ';\n'
    open(os.path.join(ZIEL, 'instagram-daten.js'), 'wb').write(text.encode('utf-8'))
    print(sum(len(v) for v in daten.values()), 'Beitraege eingebaut.')
    ausgabe('neu')
    # Ein Konto hat geklappt, eins nicht: Karten bleiben drin, der Lauf wird trotzdem rot (Mail).
    if fehler: sys.exit('Instagram-Abruf fehlgeschlagen: ' + ', '.join(fehler))


main()
