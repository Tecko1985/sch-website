<?php
// Zahlen der Besucherstatistik für die Redaktion (admin/, Bereich „Statistik“).
// Nur mit gültigem Redaktions-Zugangsschlüssel: Der Schlüssel kommt per POST (Feld "schluessel") und
// wird bei GitHub geprüft – er muss Schreibrecht auf Tecko1985/sch-website haben, wie beim Anmelden in
// der Redaktion. Gespeichert wird nur ein SHA-256 des Schlüssels für 10 Minuten (spart GitHub-Abfragen).
// Kein CORS: nur die Redaktion auf www.sc1911-heiligenstadt.de selbst kann die Zahlen lesen.
// Freigegeben im Job "hetzner" (seite.yml) mit festem SHA-256 – nach jeder Änderung dort eintragen.

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function antwort($code, $daten) { http_response_code($code); echo json_encode($daten, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE); exit; }

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') antwort(405, array('fehler' => 'Nur POST'));

$schluessel = (string)($_POST['schluessel'] ?? '');
if (!preg_match('/^(gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,255}$/', $schluessel)) antwort(401, array('fehler' => 'Kein gültiger Schlüssel'));

$ordner = dirname(__DIR__, 2) . '/statistik-daten';
if (!is_dir($ordner)) @mkdir($ordner, 0700, true);

// ---------------------------------------------------------------- Schlüssel prüfen
$zugang = $ordner . '/zugang.json';
$kennung = hash('sha256', $schluessel);
$gemerkt = is_file($zugang) ? json_decode((string)@file_get_contents($zugang), true) : array();
if (!is_array($gemerkt)) $gemerkt = array();
$jetzt = time();
foreach ($gemerkt as $k => $bis) { if ($bis < $jetzt) unset($gemerkt[$k]); }

if (!isset($gemerkt[$kennung])) {
  $kopf = array('Authorization: Bearer ' . $schluessel, 'Accept: application/vnd.github+json',
                'X-GitHub-Api-Version: 2022-11-28', 'User-Agent: SCH-Statistik');
  $url = 'https://api.github.com/repos/Tecko1985/sch-website';
  $code = 0; $text = '';
  if (function_exists('curl_init')) {
    $c = curl_init($url);
    curl_setopt_array($c, array(CURLOPT_HTTPHEADER => $kopf, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 15));
    $text = (string)curl_exec($c);
    $code = (int)curl_getinfo($c, CURLINFO_HTTP_CODE);
    curl_close($c);
  } else {
    $ctx = stream_context_create(array('http' => array('header' => implode("\r\n", $kopf), 'timeout' => 15, 'ignore_errors' => true)));
    $text = (string)@file_get_contents($url, false, $ctx);
    if (isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m)) $code = (int)$m[1];
  }
  $repo = json_decode($text, true);
  if ($code !== 200 || empty($repo['permissions']['push'])) antwort(403, array('fehler' => 'Schlüssel ohne Schreibrecht für die Redaktion'));
  $gemerkt[$kennung] = $jetzt + 600;
  @file_put_contents($zugang, json_encode($gemerkt), LOCK_EX);
}

// ---------------------------------------------------------------- Zahlen
$monate = max(1, min(24, (int)($_POST['monate'] ?? 3)));
$tage = array();
$d = new DateTime('first day of this month', new DateTimeZone('Europe/Berlin'));
for ($i = 0; $i < $monate; $i++) {
  $datei = $ordner . '/' . $d->format('Y-m') . '.json';
  if (is_file($datei)) {
    $inhalt = json_decode((string)@file_get_contents($datei), true);
    if (is_array($inhalt)) $tage = $tage + $inhalt;
  }
  $d->modify('-1 month');
}
ksort($tage);
antwort(200, array('tage' => $tage, 'stand' => date('c')));
