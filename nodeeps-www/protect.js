// snapvoice — Pflichtangaben/Kontakt erst im Browser einsetzen, damit der Name & die
// E-Mail NICHT im Klartext im HTML-Quelltext stehen. Schützt gegen einfache Crawler /
// E-Mail-Harvester — KEINE echte Verschlüsselung (JS-fähige Bots können es auslesen).
(function () {
  // ============ HIER EIGENE WERTE EINTRAGEN ============
  // base64 erzeugen, z. B. im Terminal:   echo -n 'Max Mustermann' | base64
  var NAME_B64  = "TWF4IE11c3Rlcm1hbm4=";   // base64 von "Max Mustermann" — ERSETZEN
  var PHONE_B64 = "";                         // optional: echo -n '+49 30 1234567' | base64
  var MAIL_USER = "info";
  var MAIL_DOMAIN = "snapvoice.de";
  // ====================================================

  function dec(s) { try { return decodeURIComponent(escape(atob(s))); } catch (e) { return ""; } }
  function fill(sel, val) {
    document.querySelectorAll(sel).forEach(function (el) { el.textContent = val; });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (NAME_B64)  fill('[data-prot="name"]',  dec(NAME_B64));
    if (PHONE_B64) fill('[data-prot="phone"]', dec(PHONE_B64));
    var addr = MAIL_USER + "@" + MAIL_DOMAIN;
    document.querySelectorAll('[data-prot="mail"]').forEach(function (el) {
      el.textContent = addr;
      el.setAttribute("href", "mailto:" + addr);
    });
  });
})();
