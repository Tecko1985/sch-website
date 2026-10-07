# Holt die neuesten Instagram-Beitraege und baut sie als Karten in index.html ein.
# Laeuft in der GitHub Action .github/workflows/instagram.yml. Die Bilder landen im Repo,
# Besucher laden also nichts von Instagram oder Meta.
#
# Umgebung:
#   IG_TOKEN    Zugangsschluessel (Instagram API with Instagram Login), nur als GitHub-Secret
#   IG_ERNEUERN 1 = Schluessel um 60 Tage verlaengern, neuer Schluessel nach $RUNNER_TEMP/ig_token
#   IG_PROBE    Pfad zu einer JSON-Datei statt der echten Abfrage (lokaler Test)
import html, io, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image

STAMM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDNER = os.path.join(STAMM, 'assets', 'instagram')
ANZAHL = 6
API = 'https://graph.instagram.com'
KONTO = 'https://www.instagram.com/sc1911heiligenstadt/'


def hole(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sch-website'}), timeout=30) as r:
        return r.read()


def abfrage(pfad, token, **werte):
    werte['access_token'] = token
    return json.loads(hole(f'{API}/{pfad}?{urllib.parse.urlencode(werte)}'))


def kurz(text, laenge=150):
    text = re.sub(r'\s+', ' ', text or '').strip()
    if len(text) <= laenge: return text
    return text[:laenge].rsplit(' ', 1)[0].rstrip('.,;:–-') + ' …'


def karte(b, datei):
    zeit = datetime.strptime(b['timestamp'], '%Y-%m-%dT%H:%M:%S%z').astimezone(ZoneInfo('Europe/Berlin'))
    datum = zeit.strftime('%d.%m.%Y')
    art = {'VIDEO': 'Video', 'CAROUSEL_ALBUM': 'Bilderserie'}.get(b.get('media_type'), 'Bild')
    text = kurz(b.get('caption'))
    return ('<a class="sch-socialcard sch-igpost" href="' + html.escape(b['permalink']) + '">'
            '<div class="sch-socialvisual"><img src="assets/instagram/' + datei + '" alt="' + art + ' zum Instagram-Beitrag vom ' + datum + '" loading="lazy">'
            '<div class="sch-socialcaption"><span>INSTAGRAM · <time datetime="' + zeit.isoformat() + '">' + datum + '</time></span>'
            + ('<p class="sch-igtext">' + html.escape(text) + '</p>' if text else '') +
            '<span class="sch-socialcta">Auf Instagram ansehen</span></div></div>'
            '<div class="sch-socialfooter"><img src="assets/logo.png" alt=""><span>sc1911heiligenstadt</span><b aria-label="Instagram">◎</b></div></a>')


def main():
    token = os.environ.get('IG_TOKEN', '').strip()
    probe = os.environ.get('IG_PROBE')
    if not token and not probe:
        print('Kein IG_TOKEN gesetzt, nichts zu tun.')
        return
    if token: print('::add-mask::' + token)

    if token and os.environ.get('IG_ERNEUERN') == '1':
        neu = abfrage('refresh_access_token', token, grant_type='ig_refresh_token')
        print('::add-mask::' + neu['access_token'])
        open(os.path.join(os.environ.get('RUNNER_TEMP', STAMM), 'ig_token'), 'w').write(neu['access_token'])
        print('Schluessel verlaengert, gueltig noch', neu.get('expires_in', 0) // 86400, 'Tage.')

    if probe:
        beitraege = json.load(open(probe, encoding='utf-8'))['data']
    else:
        beitraege = abfrage('me/media', token, fields='id,caption,media_type,media_url,thumbnail_url,permalink,timestamp', limit=ANZAHL)['data']
    beitraege = beitraege[:ANZAHL]

    os.makedirs(ORDNER, exist_ok=True)
    karten, behalten = [], set()
    for b in beitraege:
        quelle = b.get('thumbnail_url') if b.get('media_type') == 'VIDEO' else b.get('media_url')
        if not quelle or not b.get('permalink'): continue
        datei = re.sub(r'[^0-9A-Za-z_]', '', str(b['id'])) + '.webp'
        ziel = os.path.join(ORDNER, datei)
        if not os.path.exists(ziel):
            bild = Image.open(io.BytesIO(hole(quelle))).convert('RGB')
            bild.thumbnail((800, 800))
            bild.save(ziel, 'WEBP', quality=80)
        behalten.add(datei)
        karten.append(karte(b, datei))
    for alt in os.listdir(ORDNER):
        if alt not in behalten: os.remove(os.path.join(ORDNER, alt))

    seite = os.path.join(STAMM, 'index.html')
    s = open(seite, encoding='utf-8').read()
    neu = re.sub(r'<!--instagram-->.*?<!--/instagram-->', lambda m: '<!--instagram-->' + ''.join(karten) + '<!--/instagram-->', s, count=1, flags=re.S)
    if neu == s and '<!--instagram-->' not in s:
        sys.exit('Marke <!--instagram--> fehlt in index.html')
    open(seite, 'w', encoding='utf-8', newline='').write(neu)
    print(len(karten), 'Beitraege eingebaut.')


main()
