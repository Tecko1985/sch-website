# Baut das WordPress-Plugin "SC 1911 Startseite" aus der Startseite dieses Repos.
#   python wordpress-plugin/baue-plugin.py      (aus dem Repo-Stamm oder von hier)
# Ergebnis: wordpress-plugin/sc1911-startseite/ und sc1911-startseite.zip (beides nicht im Repo).
# Handgeschrieben sind nur quelle/*.php. vorlage.php, web/ und dateien.json entstehen hier aus
# index.html: die News-Blöcke und die Spielkarten ersetzt das Plugin durch Live-Daten
# (WordPress, FuPa), relative Links zeigen auf die echten WordPress-Seiten.
# Nach jeder Design-Änderung an index.html/CSS/JS: neu bauen und das ZIP in WordPress hochladen.
import io, json, os, re, shutil, sys, zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
STAMM = os.path.dirname(HIER)
NAME = 'sc1911-startseite'
AUS = os.path.join(HIER, NAME)
WEB = os.path.join(AUS, 'web')

# Lokale Seite -> Pfad auf der Vereinsseite (aus der Linkkarte des Seitenbaus, plus Sonderfälle)
LINKKARTE = os.path.join(STAMM, 'werkzeug', 'linkkarte.json')
ZIEL = {'index.html': '/', 'spielbericht-erfurt.html': '/2026/10/04/ende-im-achtelfinale-2/',
        'seiten/termine.html': '/spieluebersicht/', 'seiten/datenschutz.html': '/datenschutz/'}
if os.path.exists(LINKKARTE):
    for url, datei in json.load(open(LINKKARTE, encoding='utf-8')).items():
        if not datei.startswith('beitrag-') and not datei.startswith('..'):
            ZIEL.setdefault('seiten/' + datei, re.sub(r'^https://www\.sc1911-heiligenstadt\.de', '', url).rstrip('/') + '/')
# Bestätigen/Abmelden läuft über die Newsletter-Seite auf GitHub Pages (NL_SEITE_URL im Worker).
EXTERN = {'newsletter.html': 'https://tecko1985.github.io/sch-website/newsletter.html'}
WEGLASSEN = {'instagram-daten.js', 'instagram.js'}   # Instagram-Beiträge baut nur die GitHub Action


def fehler(t):
    sys.exit('FEHLER: ' + t)


def ersetze(s, muster, neu, anzahl=1, flags=re.S):
    s2, n = re.subn(muster, neu, s, flags=flags)
    if n != anzahl: fehler(f'{n} statt {anzahl} Treffer für {muster[:70]}')
    return s2


idx = io.open(os.path.join(STAMM, 'index.html'), encoding='utf-8').read()
kopf = idx[:idx.index('<body')]
rumpf = idx[idx.index('>', idx.index('<body')) + 1:idx.index('</body>')]

# Reste der Offline-Ausgabe
# Die Offline-Leiste gibt es seit b38fe83 nicht mehr in index.html -- daher optional
rumpf = re.sub(r'<div class="offline-bar">.*?</nav></div>', '', rumpf, flags=re.S)
rumpf = re.sub(r'<p class="offline-note">.*?</p>', '', rumpf, flags=re.S)
skripte = re.findall(r'<script src="([^"?]+)[^"]*"[^>]*></script>', rumpf)
rumpf = re.sub(r'<script src="[^"]*"[^>]*></script>', '', rumpf)
if '<script' in rumpf: fehler('Inline-Skript in index.html – im Plugin noch nicht vorgesehen')
stile = re.findall(r'<link rel="stylesheet" href="([^"?]+)[^"]*">', kopf)

# Satz zur Auslieferung über GitHub Pages gilt nur für die Pages-Fassung, nicht für WordPress
rumpf = ersetze(rumpf, r'<span data-nur-pages>.*?</span>', '')

# Live-Daten statt fester Inhalte
rumpf = ersetze(rumpf, r'(<div class="sch-latest"[^>]*>).*?(</div></section>)', r'\1<?php sc1911_sp_neueste(); ?>\2')
rumpf = ersetze(rumpf, r'(<div class="sch-moregrid">).*?(</div></div></section>)', r'\1<?php sc1911_sp_weitere(); ?>\2')
for reihe in ('men', 'reserve', 'youth'):
    rumpf = ersetze(rumpf, r'(id="sch-fixtures-' + reihe + r'".*?)<div class="sch-gametrack" data-initial="\d+">.*?</div>(</div>)',
                    lambda m, r=reihe: m.group(1) + "<?php sc1911_sp_spiele( '" + r + "' ); ?>" + m.group(2))
rumpf = ersetze(rumpf, r'<p class="sch-matchsource">Stand: [^<]*Ergebnisse[^<]*</p>', '<?php sc1911_sp_standzeile(); ?>')

# Relative Links und Dateien
dateien = set()


def umbiegen(m):
    attr, pfad = m.group(1), m.group(2)
    nur, _, anker = pfad.partition('#')
    nur = nur.split('?')[0]
    anker = '#' + anker if anker else ''
    if nur in EXTERN: return f'{attr}="{EXTERN[nur]}{anker}"'
    if nur.endswith('.html'):
        if nur not in ZIEL: fehler('kein WordPress-Ziel für ' + nur)
        return f'{attr}="<?php echo esc_url( home_url( \'{ZIEL[nur]}\' ) ); ?>{anker}"'
    if not os.path.isfile(os.path.join(STAMM, nur)): fehler('Datei fehlt: ' + nur)
    dateien.add(nur)
    return f'{attr}="<?php echo esc_url( SC1911_SP_WEB . \'{nur}\' ); ?>"'


rumpf = re.sub(r'\b(href|src)="(?!https?:|mailto:|tel:|#|data:|<\?php)([^"]+)"', umbiegen, rumpf)
if '<?php' in re.sub(r'<\?php.*?\?>', '', rumpf, flags=re.S) or '?>' in re.sub(r'<\?php.*?\?>', '', rumpf, flags=re.S):
    fehler('PHP-Zeichen im Seitentext')

css = [c for c in stile if c not in WEGLASSEN] + ['wp.css']
js = [j for j in skripte if j not in WEGLASSEN]
for c in css + js:
    if c != 'wp.css': dateien.add(c)
    for u in re.findall(r"url\(['\"]?([^'\")]+)", io.open(os.path.join(STAMM, c), encoding='utf-8').read()) if c.endswith('.css') and c != 'wp.css' else []:
        if not u.startswith(('data:', 'http')): dateien.add(os.path.normpath(os.path.join(os.path.dirname(c), u)).replace('\\', '/'))

titel = re.search(r'<title>(.*?)</title>', kopf).group(1)
vorlage = ('<?php\n// Erzeugt von baue-plugin.py aus index.html – nicht von Hand ändern.\n'
           "if ( ! defined( 'ABSPATH' ) ) {\n\texit;\n}\n?><!doctype html><html <?php language_attributes(); ?>><head>"
           '<meta charset="<?php bloginfo( \'charset\' ); ?>"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<?php if ( ! current_theme_supports( 'title-tag' ) ) : ?><title>{titel}</title><?php endif; ?>"
           '<?php wp_head(); ?></head><body <?php body_class( \'sch-startseite\' ); ?>><?php wp_body_open(); ?>\n'
           + rumpf + '\n<?php wp_footer(); ?></body></html>\n')

# Windows gibt frisch geschriebene Ordner manchmal nicht gleich frei: Reste dürfen bleiben,
# ins ZIP kommt nur, was dieser Lauf schreibt.
shutil.rmtree(AUS, ignore_errors=True)
os.makedirs(WEB, exist_ok=True)
geschrieben = []
for q in os.listdir(os.path.join(HIER, 'quelle')):
    geschrieben.append(shutil.copy(os.path.join(HIER, 'quelle', q), os.path.join(AUS if q.endswith('.php') else WEB, q)))
io.open(os.path.join(AUS, 'vorlage.php'), 'w', encoding='utf-8', newline='\n').write(vorlage)
for d in sorted(dateien):
    os.makedirs(os.path.dirname(os.path.join(WEB, d)), exist_ok=True)
    geschrieben.append(shutil.copy(os.path.join(STAMM, d), os.path.join(WEB, d)))
json.dump({'css': css, 'js': js}, open(os.path.join(WEB, 'dateien.json'), 'w', encoding='utf-8'), indent=1)
geschrieben += [os.path.join(AUS, 'vorlage.php'), os.path.join(WEB, 'dateien.json')]

zipname = os.path.join(HIER, NAME + '.zip')
with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in geschrieben:
        z.write(p, os.path.relpath(p, HIER).replace('\\', '/'))
print(f'{len(dateien)} Dateien, CSS {len(css)}, JS {len(js)} -> {zipname} ({os.path.getsize(zipname) // 1024} KB)')
