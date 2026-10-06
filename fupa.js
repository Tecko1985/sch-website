// FuPa-Inhalte erst nach Klick laden (Zwei-Klick-Lösung, wie Borlabs auf der Vereinsseite).
// Vorher geht keine Anfrage an FuPa. Ein Klick lädt alle FuPa-Inhalte dieser Seite.
(function () {
  var kaesten = document.querySelectorAll('.sp-fupa[data-inhalt]');
  if (!kaesten.length) return;

  function dekodiere(b64) {
    var bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder('utf-8').decode(bytes);
  }

  // Skripte nacheinander ausführen: externe erst laden, dann das nächste.
  function fuehreAus(skripte, i) {
    if (i >= skripte.length) return;
    var alt = skripte[i], neu = document.createElement('script');
    if (alt.src) {
      neu.src = alt.src;
      neu.onload = neu.onerror = function () { fuehreAus(skripte, i + 1); };
      alt.parentNode.replaceChild(neu, alt);
    } else {
      neu.text = alt.text;
      alt.parentNode.replaceChild(neu, alt);
      fuehreAus(skripte, i + 1);
    }
  }

  function ladeAlle() {
    kaesten.forEach(function (k) {
      if (!k.hasAttribute('data-inhalt')) return;
      var ziel = document.createElement('div');
      ziel.className = 'sp-fupa-geladen';
      ziel.innerHTML = dekodiere(k.getAttribute('data-inhalt'));
      k.replaceWith(ziel);
      fuehreAus(Array.prototype.slice.call(ziel.querySelectorAll('script')), 0);
    });
  }

  kaesten.forEach(function (k) {
    var knopf = k.querySelector('button');
    if (knopf) knopf.addEventListener('click', ladeAlle);
  });
})();
