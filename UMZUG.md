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

## Seit 17.11.2026: Umzugsseite für alle Besucher

Die alte Seite zeigt allen Besuchern `umzug.html` (Status 503 = „kurz weg“, Google behält die Seite).
Das steuert der Block `# BEGIN SC1911 Umzugsseite` oben in `public_html/.htaccess` auf dem Webspace.
Offen bleiben: angemeldete Admins, `wp-admin`, `wp-login.php`, `wp-json` (braucht `weiterleitungen.py`), `neu-test/`, `neu-probe/`.
**Abschalten:** den Block löschen (Sicherung davor: `~/htaccess-vor-umzugsseite-20261117-0737`).
Beim Umzug verschwindet er von selbst (die alte `.htaccess` wandert mit ins WordPress-Archiv).
Achtung: `umzug.py zurueck` holt ihn mit zurück – danach den Block löschen, wenn das WordPress wieder sichtbar sein soll.

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

8. **Newsletter**: im Worker (`ToolsUebersicht/admin-worker.js`) `NL_SEITE_URL` auf
   `https://www.sc1911-heiligenstadt.de/newsletter.html` stellen und deployen.
9. **Prüfen**: Startseite, ein alter Beitragslink (z. B. `/2026/10/04/ende-im-achtelfinale-2/`),
   Impressum, Datenschutz, Newsletter-Anmeldung, Handy-Ansicht.
10. **Google Search Console**: Domain anmelden, `sitemap.xml` einreichen.

## Danach

- Automatisches Hochladen: läuft schon (seit 16.11.2026) nach jedem Veröffentlichen in den Testordner
  `public_html/neu-test/` (Secret `HETZNER_SSH_KEY`, Schlüssel liegt bei Michel unter `%USERPROFILE%\.ssh\sch_hetzner`).
  Nach dem Umzug in `.github/workflows/seite.yml` das `ZIEL` auf `public_html/` stellen, `--exclude .htaccess` entfernen
  und den Umzugs-Schalter in den Schritt aufnehmen. Vorsicht: `--delete` würde dann alles im Webordner löschen,
  was nicht im GitHub-Bau steckt – auch die **Beiträge aus 2025** (nicht im Repo) und ihre Karten in den News.
  Erst umstellen, wenn diese Frage gelöst ist (z. B. ohne `--delete` und mit Ausnahme für die 2025-Dateien).
- WordPress-Sicherung einige Wochen aufheben.
- **Instagram-Beiträge** (16.11.2026): Meta-App „SCH Webseite“ (Business-Portfolio „SCH Webseite“, das Vereins-Portfolio
  ist für Werbung gesperrt), Anwendungsfall „Instagram API with Unified Login“, beide Konten als Instagram-Tester.
  Secrets `IG_TOKEN` (Verein → Startseite) und `IG_TOKEN_NACHWUCHS` (Nachwuchs → seiten/nachwuchs.html),
  Systemnutzer-Tokens ohne Ablauf. Findet `.github/instagram.py` die Konto-ID nicht, Repo-Variable `IG_ID` bzw.
  `IG_ID_NACHWUCHS` setzen (Nummer 1784… aus der Meta-App).
- Auftragsverarbeitungsvertrag mit Hetzner prüfen (in der konsoleH abschließbar).
