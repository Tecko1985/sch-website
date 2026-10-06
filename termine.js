// Filter auf der Termine-Seite: Alle / Herren / Nachwuchs / Heimspiele
(function () {
  var knoepfe = document.querySelectorAll('.tm-filter button');
  var tage = document.querySelectorAll('.tm-tag');
  var leer = document.querySelector('.tm-leer');
  function zeige(filter) {
    var sichtbar = 0;
    tage.forEach(function (tag) {
      var imTag = 0;
      tag.querySelectorAll('.tm-spiel').forEach(function (sp) {
        var an = filter === 'alle' || sp.classList.contains(filter);
        sp.hidden = !an;
        if (an) imTag++;
      });
      tag.hidden = imTag === 0;
      sichtbar += imTag;
    });
    if (leer) leer.hidden = sichtbar > 0;
  }
  knoepfe.forEach(function (k) {
    k.addEventListener('click', function () {
      knoepfe.forEach(function (x) { x.setAttribute('aria-pressed', x === k ? 'true' : 'false'); });
      zeige(k.getAttribute('data-filter'));
    });
  });
})();
