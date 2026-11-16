#!/usr/bin/env python3
"""Baut Impressum und Datenschutzerklärung der neuen Vereinsseite.

Aufruf (im Repo-Ordner):  python werkzeuge/rechtliches.py

Schreibt
- seiten/impressum.html        Impressum (Angaben wie auf der alten Seite, Stand WordPress 06.04.2026)
- seiten/datenschutz-neu.html  vollständige Datenschutzerklärung für die Zeit NACH dem Umzug
                               (Auslieferung vom Webspace bei Hetzner). Bis zum Umzug gilt
                               seiten/datenschutz.html (Vorschau auf GitHub Pages); am Umzugstag
                               ersetzt der Umzugs-Schalter sie durch diese Datei.
Rahmen (Kopf, Menü, Fußzeile) kommt aus seiten/datenschutz.html, damit beide aussehen wie die übrigen Seiten.
"""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORLAGE = "seiten/datenschutz.html"
STAND = "16.11.2026"

IMPRESSUM = """
<h2>Angaben gemäß § 5 DDG</h2>
<p>1. SC 1911 Heiligenstadt e.V.<br>Leineberg 2<br>37308 Heilbad Heiligenstadt</p>
<h2>Vertreten durch den Vorstand</h2>
<p>Thadäus König, Manuel Lubojanski, Christoph Rodenstock, Sebastian Möhlhenrich, Michael Apel</p>
<h2>Kontakt</h2>
<p>Telefon: +49 3606 612202<br>Telefax: +49 3606 509091<br>E-Mail: <a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a></p>
<p>Erreicht ihr uns telefonisch nicht, schreibt uns gern eine Mail. Wir melden uns!</p>
<h2>Registereintrag</h2>
<p>Vereinsregister: Amtsgericht Heilbad Heiligenstadt<br>Vereinsregisternummer: 400083<br>LSB-Nr.: 150004</p>
<h2>Umsatzsteuer</h2>
<p>USt-IdNr.: DE 157/142/07749</p>
<h2>Verbraucherstreitbeilegung</h2>
<p>Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>
<h2>Haftung für Inhalte</h2>
<p>Als Diensteanbieter sind wir für eigene Inhalte auf diesen Seiten nach den allgemeinen Gesetzen verantwortlich. Wir sind jedoch nicht verpflichtet, übermittelte oder gespeicherte fremde Informationen zu überwachen oder nach Umständen zu forschen, die auf eine rechtswidrige Tätigkeit hinweisen. Verpflichtungen zur Entfernung oder Sperrung der Nutzung von Informationen nach den allgemeinen Gesetzen bleiben unberührt. Eine Haftung ist erst ab dem Zeitpunkt der Kenntnis einer konkreten Rechtsverletzung möglich. Sobald wir von einer Rechtsverletzung erfahren, entfernen wir den Inhalt umgehend.</p>
<h2>Haftung für Links</h2>
<p>Unsere Seite enthält Links zu Seiten anderer Anbieter, auf deren Inhalte wir keinen Einfluss haben. Für diese Inhalte ist der jeweilige Anbieter verantwortlich. Bei Bekanntwerden von Rechtsverletzungen entfernen wir solche Links umgehend.</p>
<h2>Urheberrecht</h2>
<p>Die Texte und Bilder auf dieser Seite unterliegen dem deutschen Urheberrecht. Vervielfältigung, Bearbeitung und Verbreitung außerhalb der Grenzen des Urheberrechts brauchen die schriftliche Zustimmung des Vereins bzw. der jeweiligen Urheber.</p>
<p><a href="datenschutz.html">Zur Datenschutzerklärung</a></p>
"""

DATENSCHUTZ = """
<p class="fb-lead">Hier steht, welche Daten beim Besuch dieser Seite anfallen, wofür wir sie brauchen und welche Rechte ihr habt. Kurz gesagt: keine Cookies, keine Besucherzählung, nichts von Werbenetzwerken.</p>
<h2>1. Verantwortlich</h2>
<p>1. SC 1911 Heiligenstadt e.V.<br>Leineberg 2, 37308 Heilbad Heiligenstadt<br>Telefon: +49 3606 612206<br>E-Mail: <a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a></p>
<p>Unseren Datenschutzbeauftragten erreicht ihr über dieselben Kontaktdaten.</p>
<h2>2. Aufruf der Seite</h2>
<p>Die Seite liegt auf einem Webserver der Hetzner Online GmbH, Industriestr. 25, 91710 Gunzenhausen, in Deutschland. Beim Aufruf schickt euer Browser technisch nötige Daten an den Server: IP-Adresse, Datum und Uhrzeit, die aufgerufene Seite, die Seite, von der ihr kommt, sowie Browser und Betriebssystem. Der Server speichert sie für begrenzte Zeit in Protokolldateien. Wir brauchen sie, um die Seite sicher und fehlerfrei auszuliefern und Angriffe zu erkennen (Art. 6 Abs. 1 lit. f DSGVO). Wir führen diese Daten nicht mit anderen zusammen. Hetzner arbeitet für uns als Auftragsverarbeiter nach Art. 28 DSGVO.</p>
<h2>3. Keine Cookies, keine Statistik</h2>
<p>Die Seite setzt keine Cookies und zählt keine Besuche. Schriften, Bilder und Skripte liegen auf unserem eigenen Webserver; beim Anschauen werden keine Inhalte von Google, Facebook oder anderen Anbietern nachgeladen. Ausnahmen stehen unten bei Newsletter und FuPa.</p>
<p>Auf der Startseite fragt die Seite beim Laden unseren Serverdienst bei Cloudflare (siehe Newsletter), ob gerade ein Hinweis aktiv ist, etwa zu einem Fußballcamp. Dabei wird eure IP-Adresse übertragen, gespeichert wird nichts. Klickt ihr einen Hinweis weg, merkt sich euer Browser das für 7 Tage im lokalen Speicher (kein Cookie, es wird nichts an uns geschickt).</p>
<h2 id="newsletter">4. Newsletter</h2>
<p>Meldet ihr euch für unseren Newsletter an, speichern wir eure E-Mail-Adresse, freiwillig euren Vornamen und wann ihr euch angemeldet und bestätigt habt. Rechtsgrundlage ist eure Einwilligung (Art. 6 Abs. 1 lit. a DSGVO). Zuerst kommt eine Mail mit einem Bestätigungslink. Erst nach dem Klick seid ihr angemeldet. Klickt ihr nicht, löschen wir die Adresse nach 7 Tagen.</p>
<p>Als Dankeschön kann die Bestätigung Gutscheincodes unserer Partnerfirmen enthalten. Welcher Code das ist, speichern wir bei eurer Adresse; berechtigte Personen im Verein sehen ihn. Die Partner bekommen keine Daten von euch, nur eine Liste der Codes ohne Namen. Den Code löst ihr selbst bei ihnen ein. Damit der Newsletter-Kasten zeigen kann, welche Partner gerade etwas dazugeben, fragt die Startseite beim Laden unseren Serverdienst (siehe unten) nach dieser Liste; dabei wird eure IP-Adresse übertragen, gespeichert wird nichts.</p>
<p>Gespeichert werden die Daten auf dem Datenspeicher (Nextcloud) des Vereins bei einem Anbieter innerhalb der EU. Auf dem Weg dorthin laufen sie über einen Serverdienst von Cloudflare. Die Mails verschickt der Mail-Dienst Brevo. Betrieben wird das für den Verein von Clubdach (Michel Brunner, Heilbad Heiligenstadt) als Auftragsverarbeiter nach Art. 28 DSGVO. Bei Cloudflare und Brevo ist eine Übermittlung in Länder außerhalb der EU nicht ausgeschlossen. Die Liste sehen nur berechtigte Personen im Verein. Eine Weitergabe an Dritte findet nicht statt.</p>
<p>Abmelden könnt ihr euch jederzeit über den Link in jeder Mail. Dann löschen wir eure Adresse ganz. Einmal am Tag legen wir eine Sicherungskopie in einem Speicher bei Cloudflare in der EU ab; jede Kopie wird nach 30 Tagen gelöscht. Bis dahin kann eure Adresse dort noch stehen.</p>
<h2>5. FuPa erst nach Klick</h2>
<p>Tabellen, Spielpläne und Statistiken von FuPa laden wir erst, wenn ihr auf „FuPa-Inhalte laden“ klickt. Vorher geht keine Anfrage an FuPa. Nach dem Klick überträgt euer Browser Daten wie die IP-Adresse an die FuPa GmbH. Mehr dazu in der <a href="https://www.fupa.net/about/privacy-policy">Datenschutzerklärung von FuPa</a>.</p>
<h2>6. Instagram-Beiträge</h2>
<p>Die neuesten Beiträge von unserem Instagram-Konto holen wir regelmäßig selbst ab und legen Bilder und Text auf unserem Webserver ab. Beim Anschauen geht deshalb keine Anfrage an Instagram oder Meta. Erst wenn ihr auf einen Beitrag klickt, öffnet sich Instagram. Gezeigt werden nur die neuesten Beiträge; ein Beitrag, der auf Instagram gelöscht oder archiviert wird, verschwindet in der Regel nach wenigen Stunden auch hier.</p>
<h2>7. E-Mail an uns</h2>
<p>Schreibt ihr uns eine Mail, nutzen wir eure Angaben nur, um die Anfrage zu beantworten (Art. 6 Abs. 1 lit. b und f DSGVO). Wir löschen sie, wenn die Sache erledigt ist und keine Aufbewahrungspflicht besteht.</p>
<h2>8. Links zu anderen Seiten</h2>
<p>Links zu fussball.de, Facebook, Instagram, staige.tv oder den Shops öffnen fremde Seiten. Erst dann gelten deren Datenschutzregeln.</p>
<h2>9. Eure Rechte</h2>
<p>Ihr habt das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch gegen Verarbeitungen auf Grundlage berechtigter Interessen (Art. 21). Eine Einwilligung, etwa für den Newsletter, könnt ihr jederzeit für die Zukunft widerrufen. Schreibt uns dazu an <a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a>.</p>
<p>Ihr könnt euch außerdem bei einer Datenschutz-Aufsichtsbehörde beschweren, in Thüringen beim Thüringer Landesbeauftragten für den Datenschutz und die Informationsfreiheit (TLfDI), Häßlerstraße 8, 99096 Erfurt.</p>
<p class="sp-datum">Stand: __STAND__</p>
"""


def baue(vorlage, datei, titel, kicker, inhalt, beschreibung):
    t = vorlage
    t = re.sub(r"<title>.*?</title>", f"<title>{titel} · 1. SC 1911 Heiligenstadt</title>", t, count=1, flags=re.S)
    t = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + beschreibung, t, count=1)
    t = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + f"{titel} · 1. SC 1911 Heiligenstadt", t, count=1)
    t = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1) + beschreibung, t, count=1)
    t = re.sub(r'(<meta property="og:url" content="[^"]*/)seiten/[^"]*', lambda m: m.group(1) + "seiten/" + datei, t, count=1)
    held = (f'<div class="sch-reporthero sp-held"><img src="../assets/hero.jpg" alt=""><div><span>{kicker}</span>'
            f"<h1>{titel}</h1></div></div>")
    main = f'<main class="sch-report sp-seite">{held}<article class="sp-inhalt">\n{inhalt.strip()}\n</article>'
    t, n = re.subn(r'<main class="sch-report sp-seite">.*?</article>', lambda m: main, t, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("Vorlage ohne <main class=\"sch-report sp-seite\">…</article>")
    with open(os.path.join(REPO, "seiten", datei), "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    print("seiten/" + datei)


def main():
    vorlage = open(os.path.join(REPO, VORLAGE), encoding="utf-8").read()
    baue(vorlage, "impressum.html", "Impressum", "Unser Verein", IMPRESSUM,
         "Impressum des 1. SC 1911 Heiligenstadt e.V.")
    baue(vorlage, "datenschutz-neu.html", "Datenschutzerklärung", "Unser Verein", DATENSCHUTZ.replace("__STAND__", STAND),
         "Datenschutzerklärung des 1. SC 1911 Heiligenstadt e.V.: keine Cookies, keine Statistik.")


if __name__ == "__main__":
    main()
