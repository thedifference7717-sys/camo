// CAMO home page: launch clock and headline decrypt.
// No dependencies, no network. Everything degrades to static content without JavaScript.
(function () {
  'use strict';
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- launch clock --------------------------------------------------------
  var clock = document.getElementById('countdown');
  if (clock) {
    var launch = Date.parse(clock.getAttribute('data-launch'));
    var cells = {};
    ['d', 'h', 'm', 's'].forEach(function (u) { cells[u] = clock.querySelector('[data-unit="' + u + '"]'); });
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var tick = function () {
      var ms = Math.max(0, launch - Date.now());
      var s = Math.floor(ms / 1000);
      cells.d.textContent = pad(Math.floor(s / 86400));
      cells.h.textContent = pad(Math.floor(s / 3600) % 24);
      cells.m.textContent = pad(Math.floor(s / 60) % 60);
      cells.s.textContent = pad(s % 60);
      if (ms === 0) clock.classList.add('live');
      clock.setAttribute('aria-label', ms === 0 ? 'Mainnet is live'
        : Math.floor(s / 86400) + ' days ' + (Math.floor(s / 3600) % 24) + ' hours until mainnet launch');
    };
    tick();
    setInterval(tick, 1000);
  }

  // ---- headline decrypt ----------------------------------------------------
  var GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&<>/';
  function decrypt(el, delay) {
    var final = el.textContent, start = null, dur = 650 + final.length * 22;
    function frame(ts) {
      if (start === null) start = ts;
      var t = ts - start - delay, out = '';
      for (var i = 0; i < final.length; i++) {
        var c = final[i];
        var at = (i / final.length) * dur * 0.7 + dur * 0.3;
        out += (c === ' ' || t >= at) ? c : GLYPHS[(Math.random() * GLYPHS.length) | 0];
      }
      el.textContent = out;
      if (t < dur) requestAnimationFrame(frame); else el.textContent = final;
    }
    requestAnimationFrame(frame);
  }
  if (!reduceMotion) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-decrypt]'), function (el, i) { decrypt(el, i * 140); });
  }
})();
