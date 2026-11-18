<?php
// Profil-Datei für iPhone, iPad und Mac: richtet das Vereins-Postfach mit einem Antippen ein.
// Die Adresse kommt per POST von /mail/, wird nur für diese Antwort benutzt und nicht gespeichert.
// Das Passwort steht NICHT in der Datei – das Gerät fragt beim Installieren danach.
$adresse = trim((string)($_POST['adresse'] ?? ''));
if (strpos($adresse, '@') === false && $adresse !== '') {
    $adresse .= '@sc1911-heiligenstadt.de';
}
if (!preg_match('/^[A-Za-z0-9._%+-]{1,64}@sc1911-heiligenstadt\.de$/i', $adresse)) {
    http_response_code(400);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
       . '<p style="font:16px system-ui;padding:16px">Bitte eine Vereins-Adresse eingeben, die auf '
       . '<b>@sc1911-heiligenstadt.de</b> endet. <a href="/mail/">Zurück</a></p>';
    exit;
}
$adresse = strtolower($adresse);
$x = htmlspecialchars($adresse, ENT_XML1);
$server = 'dedi1977.your-server.de';

function uuid() {
    $b = random_bytes(16);
    $b[6] = chr((ord($b[6]) & 0x0f) | 0x40);
    $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);
    return strtoupper(vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($b), 4)));
}
$kennung = 'de.sc1911-heiligenstadt.mail.' . preg_replace('/[^a-z0-9]/', '-', $adresse);

header('Content-Type: application/x-apple-aspen-config');
header('Content-Disposition: attachment; filename="SC1911-Mail.mobileconfig"');
header('Cache-Control: no-store');
echo '<?xml version="1.0" encoding="UTF-8"?>', "\n";
?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadType</key><string>Configuration</string>
  <key>PayloadVersion</key><integer>1</integer>
  <key>PayloadIdentifier</key><string><?= $kennung ?></string>
  <key>PayloadUUID</key><string><?= uuid() ?></string>
  <key>PayloadDisplayName</key><string>SC 1911 Mail (<?= $x ?>)</string>
  <key>PayloadDescription</key><string>Richtet das Vereins-Postfach <?= $x ?> ein. Beim Installieren wird nach dem Passwort gefragt.</string>
  <key>PayloadOrganization</key><string>1. SC 1911 Heiligenstadt</string>
  <key>PayloadRemovalDisallowed</key><false/>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>PayloadType</key><string>com.apple.mail.managed</string>
      <key>PayloadVersion</key><integer>1</integer>
      <key>PayloadIdentifier</key><string><?= $kennung ?>.konto</string>
      <key>PayloadUUID</key><string><?= uuid() ?></string>
      <key>PayloadDisplayName</key><string>SC 1911 Mail</string>
      <key>EmailAccountDescription</key><string>SC 1911</string>
      <key>EmailAccountType</key><string>EmailTypeIMAP</string>
      <key>EmailAddress</key><string><?= $x ?></string>
      <key>IncomingMailServerHostName</key><string><?= $server ?></string>
      <key>IncomingMailServerPortNumber</key><integer>993</integer>
      <key>IncomingMailServerUseSSL</key><true/>
      <key>IncomingMailServerAuthentication</key><string>EmailAuthPassword</string>
      <key>IncomingMailServerUsername</key><string><?= $x ?></string>
      <key>OutgoingMailServerHostName</key><string><?= $server ?></string>
      <key>OutgoingMailServerPortNumber</key><integer>465</integer>
      <key>OutgoingMailServerUseSSL</key><true/>
      <key>OutgoingMailServerAuthentication</key><string>EmailAuthPassword</string>
      <key>OutgoingMailServerUsername</key><string><?= $x ?></string>
      <key>OutgoingPasswordSameAsIncomingPassword</key><true/>
    </dict>
  </array>
</dict>
</plist>
