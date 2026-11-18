<?php
// Auto-Einrichtung für Outlook (klassisch). Outlook schickt per POST ein kleines XML mit der
// Mail-Adresse an /autodiscover/autodiscover.xml; die .htaccess auf dem Server leitet das hierher.
// Es wird nichts gespeichert. Server: dedi1977.your-server.de (passt zum Zertifikat).
$server = 'dedi1977.your-server.de';
$adresse = '';
$roh = file_get_contents('php://input', false, null, 0, 10000);
if ($roh && preg_match('#<EMailAddress>\s*([^<\s]+)\s*</EMailAddress>#i', $roh, $m)) {
    $adresse = $m[1];
}
if (!preg_match('/^[A-Za-z0-9._%+-]+@sc1911-heiligenstadt\.de$/i', $adresse)) {
    $adresse = '';
}
$login = $adresse !== '' ? '<LoginName>' . htmlspecialchars($adresse, ENT_XML1) . '</LoginName>' : '';
header('Content-Type: application/xml; charset=utf-8');
header('Cache-Control: no-store');
echo '<?xml version="1.0" encoding="utf-8"?>', "\n";
?>
<Autodiscover xmlns="http://schemas.microsoft.com/exchange/autodiscover/responseschema/2006">
  <Response xmlns="http://schemas.microsoft.com/exchange/autodiscover/outlook/responseschema/2006a">
    <Account>
      <AccountType>email</AccountType>
      <Action>settings</Action>
      <Protocol>
        <Type>IMAP</Type>
        <Server><?= $server ?></Server>
        <Port>993</Port>
        <DomainRequired>off</DomainRequired>
        <?= $login ?>

        <SPA>off</SPA>
        <SSL>on</SSL>
        <AuthRequired>on</AuthRequired>
      </Protocol>
      <Protocol>
        <Type>SMTP</Type>
        <Server><?= $server ?></Server>
        <Port>465</Port>
        <DomainRequired>off</DomainRequired>
        <?= $login ?>

        <SPA>off</SPA>
        <SSL>on</SSL>
        <AuthRequired>on</AuthRequired>
        <UsePOPAuth>on</UsePOPAuth>
        <SMTPLast>off</SMTPLast>
      </Protocol>
    </Account>
  </Response>
</Autodiscover>
