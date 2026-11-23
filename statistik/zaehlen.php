<?php
// Besucherzähler der Vereinsseite (assets/zaehler.js schickt hierher einen Aufruf je Seite).
// Datenschutz: keine Cookies, nichts im Browser gespeichert, KEINE IP-Adresse und keine Browserkennung
// gespeichert. Gezählt werden nur Summen je Tag: Aufrufe, Besuche (Einstieg von außen), aufgerufene
// Seiten, Herkunftsseite (nur der Name, z. B. google.com) und Geräteart (Handy/Computer).
// Die Daten liegen außerhalb des Webordners (~/statistik-daten/JJJJ-MM.json), damit der Upload
// (rsync --delete auf public_html) sie nicht löscht und niemand sie direkt abrufen kann.
// Freigegeben im Job "hetzner" (seite.yml) mit festem SHA-256 – nach jeder Änderung dort eintragen.

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function ende($code) { http_response_code($code); exit; }

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') ende(405);

$ua = (string)($_SERVER['HTTP_USER_AGENT'] ?? '');
if ($ua === '' || preg_match('/bot|crawl|spider|slurp|preview|facebookexternalhit|whatsapp|telegram|headless|lighthouse|pingdom|monitor|python|curl|wget|java\/|go-http|okhttp/i', $ua)) ende(204);

$pfad = (string)($_POST['p'] ?? '');
if (!preg_match('~^/[A-Za-z0-9/._%-]{0,200}$~', $pfad) || strpos($pfad, '..') !== false) ende(400);
$pfad = preg_replace('~/index\.html$~', '/', $pfad);
if (!preg_match('~(/|\.html)$~', $pfad)) ende(204);
foreach (array('/admin/', '/mail/', '/neu/', '/neu-probe/', '/neu-test/', '/vorschau/') as $aus) {
  if (strpos($pfad, $aus) === 0) ende(204);
}

$einstieg = (($_POST['e'] ?? '') === '1');
$quelle = strtolower((string)($_POST['q'] ?? ''));
if (!preg_match('/^[a-z0-9.-]{1,80}$/', $quelle)) $quelle = '';
$quelle = preg_replace('/^(www\d?|m|l|lm|mobile)\./', '', $quelle);
if ($quelle === 'sc1911-heiligenstadt.de') $quelle = '';
if ($quelle === '') $quelle = 'direkt';
$geraet = preg_match('/Mobile|Android|iPhone|iPad|iPod/i', $ua) ? 'handy' : 'computer';

$ordner = dirname(__DIR__, 2) . '/statistik-daten';
if (!is_dir($ordner) && !@mkdir($ordner, 0700, true)) ende(500);

$jetzt = new DateTime('now', new DateTimeZone('Europe/Berlin'));
$tag = $jetzt->format('Y-m-d');
$datei = $ordner . '/' . $jetzt->format('Y-m') . '.json';

$fh = @fopen($datei, 'c+');
if (!$fh) ende(500);
if (!flock($fh, LOCK_EX)) { fclose($fh); ende(500); }
$inhalt = stream_get_contents($fh);
$daten = $inhalt ? json_decode($inhalt, true) : array();
if (!is_array($daten)) $daten = array();
if (!isset($daten[$tag])) $daten[$tag] = array('aufrufe' => 0, 'besuche' => 0, 'seiten' => array(), 'quellen' => array(), 'geraete' => array());
$t =& $daten[$tag];

$t['aufrufe']++;
// Je Tag höchstens 3000 verschiedene Seiten und 300 Herkunftsseiten (gegen Auffüllen mit Unsinn)
if (isset($t['seiten'][$pfad])) $t['seiten'][$pfad]++;
elseif (count($t['seiten']) < 3000) $t['seiten'][$pfad] = 1;
if ($einstieg) {
  $t['besuche']++;
  if (isset($t['quellen'][$quelle])) $t['quellen'][$quelle]++;
  elseif (count($t['quellen']) < 300) $t['quellen'][$quelle] = 1;
  $t['geraete'][$geraet] = ($t['geraete'][$geraet] ?? 0) + 1;
}
unset($t);

ftruncate($fh, 0);
rewind($fh);
fwrite($fh, json_encode($daten, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);
ende(204);
