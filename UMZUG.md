# Umzug der Vereinsseite – Ablauf für den Umzugstag

Ziel: Die neue Seite ersetzt das WordPress auf www.sc1911-heiligenstadt.de.
Sie kommt auf den **Webspace bei Hetzner** (dedi1977.your-server.de), wo heute das WordPress liegt.
**Das Adressbuch (DNS) bei netmedia4you bleibt unverändert, die E-Mails bei Hetzner auch.**

## Schon vorbereitet

| Was | Wo |
|---|---|
| Weiterleitungen alter WordPress-Adressen (457 Stück, 301) | `.htaccess` ← `werkzeuge/weiterleitungen.py` |
| Impressum | `seiten/impressum.html` ← `werkzeuge/rechtliches.py` |
| Datenschutzerklärung für den Betrieb bei Hetzner | `seiten/datenschutz-neu.html` ← `werkzeuge/rechtliches.py` |
| Camp- und Popup-Fenster (vorher WordPress-Plugins) | `assets/fenster/`, eingebunden in `index.html` und `neu/index.html` |
| Platzhalter „Wir ziehen um“ | `umzug.html` ← `werkzeuge/umzug_seite.py` |
| Umzugs-Schalter (noindex raus, Domain, Impressum/Datenschutz verlinken, robots.txt, sitemap.xml) | `werkzeuge/umzug_schalter.py` |

**Beiträge aus 2025** (163 Stück mit Fotos) liegen bewusst **nicht** im Repo, weil das Repo öffentlich ist:
gesichert unter `E:\Vereine\SCH\_umzug\beitraege-2025\` (Michels Rechner). Sie kommen erst beim Umzug dazu.

## UMGEZOGEN am 17.11.2026

`python werkzeuge/umzug.py echt --ja` lief durch, alle Prüfungen ok. Seitdem ist www.sc1911-heiligenstadt.de die neue Seite.
- WordPress liegt unverändert unter `~/umzug-alt-wordpress-2026-11-17` (Server), Sicherung unter
  `E:\Vereine\SCH\_umzug\wp-sicherung-2026-11-17\` (Michels Rechner).
- Vor dem Umzug zeigte das WordPress kurz allen Besuchern `umzug.html` (Block `# BEGIN SC1911 Umzugsseite` in seiner
  `.htaccess`). Der Block steckt noch im beiseitegelegten WordPress: nach `umzug.py zurueck` löschen.
- `werkzeuge/weiterleitungen.py` geht seit dem Umzug nicht mehr (holt die Liste aus dem alten WordPress).
  Die fertige `.htaccess` liegt auf dem Server und wird vom Auto-Upload nie überschrieben.

## Am Umzugstag

Alles in einem Befehl (im Repo-Ordner, braucht den Schlüssel `%USERPROFILE%\.ssh\sch_hetzner`):

```
python werkzeuge/umzug.py probe          # vorher: Generalprobe nach /neu-probe/, WordPress bleibt
python werkzeuge/umzug.py echt --ja      # DER Umzug
python werkzeuge/umzug.py zurueck --ja   # nur im Notfall: WordPress wieder zurück
```

`echt` macht der Reihe nach:
1. **WordPress sichern**: Datenbank `sccnld_db1` und alle Dateien nach `E:\Vereine\SCH\_umzug\wp-sicherung-<datum>\`.
2. **Seite bauen** wie GitHub (Repo-Dateien, Redaktionsbeiträge, `neu/`, Suchindex).
3. **Beiträge aus 2025** aus `_umzug\beitraege-2025\` dazu, ihre Karten in News und Archiv.
4. **Weiterleitungen** alter WordPress-Adressen frisch erzeugen (`.htaccess`, holt neue Beiträge mit;
   Beiträge bis Juni 2025 -> Archiv).
5. **Schalter umlegen** (noindex raus, Domain, Datenschutz für Hetzner, robots.txt, sitemap.xml).
6. **Hochladen** in `~/umzug-neu` (außerhalb des Webordners), dann **umschalten**: das WordPress wird nach
   `~/umzug-alt-wordpress-<datum>` **verschoben** (nicht gelöscht), die neue Seite in `public_html`. Dauert Sekunden.
7. **Prüfen**: Startseite, News, Impressum, Datenschutz, Suche, Newsletter, eine alte Beitragsadresse (301).

Generalprobe am 16.11.2026: alles ok (3104 Dateien, 158 MB, 406 Beiträge in der Liste, Weiterleitungen gehen).
Sicherung des WordPress vom selben Tag: `E:\Vereine\SCH\_umzug\wp-sicherung-2026-11-16\` (5,3 GB + Datenbank).

Danach von Hand:

8. **Newsletter** (erledigt 17.11.2026): im Worker (`ToolsUebersicht/admin-worker.js`) `NL_SEITE_URL` auf
   `https://www.sc1911-heiligenstadt.de/newsletter.html` stellen und deployen.
9. **Prüfen**: Startseite, ein alter Beitragslink (z. B. `/2026/10/04/ende-im-achtelfinale-2/`),
   Impressum, Datenschutz, Newsletter-Anmeldung, Handy-Ansicht.
10. **Google Search Console**: Domain anmelden, `sitemap.xml` einreichen.

## Danach

- **Automatisches Hochladen auf die echte Seite** (seit 17.11.2026): Job `hetzner` in `.github/workflows/seite.yml`
  baut nach jedem Veröffentlichen mit `python werkzeuge/umzug.py live <ordner>` (wie beim Umzug, aber ohne neue
  `.htaccess`) und lädt nach `public_html/` mit `--delete` (ausgenommen `.htaccess`, `google*.html`, `.well-known/`).
  Die **Beiträge aus 2025** holt er dafür vom Server aus `~/beitraege-2025` (außerhalb des Webordners, nicht im Repo).
  Fehlen sie dort oder kommen weniger als 3000 Dateien heraus, bricht er ab, statt zu löschen.
  Wer einen 2025-Beitrag in `E:\Vereine\SCH\_umzug\beitraege-2025\` ändert, muss den Ordner wieder nach `~/beitraege-2025` hochladen.
  Secret `HETZNER_SSH_KEY`, Schlüssel bei Michel unter `%USERPROFILE%\.ssh\sch_hetzner`. Den Testordner `neu-test/` gibt es nicht mehr.
- WordPress-Sicherung einige Wochen aufheben.
- **Instagram-Beiträge** (16.11.2026): Meta-App „SCH Webseite“ (Business-Portfolio „SCH Webseite“, das Vereins-Portfolio
  ist für Werbung gesperrt), Anwendungsfall „Instagram API with Unified Login“, beide Konten als Instagram-Tester.
  Secrets `IG_TOKEN` (Verein → Startseite) und `IG_TOKEN_NACHWUCHS` (Nachwuchs → seiten/nachwuchs.html),
  Systemnutzer-Tokens ohne Ablauf. Findet `.github/instagram.py` die Konto-ID nicht, Repo-Variable `IG_ID` bzw.
  `IG_ID_NACHWUCHS` setzen (Nummer 1784… aus der Meta-App).
- Auftragsverarbeitungsvertrag mit Hetzner prüfen (in der konsoleH abschließbar).
