// Launch countdown. Without JavaScript the panel still shows the fixed date.
(function () {
  var el = document.getElementById('countdown');
  if (!el) return;
  var launch = Date.parse(el.getAttribute('data-launch'));
  function tick() {
    var ms = launch - Date.now();
    if (ms <= 0) { el.textContent = 'LIVE'; return; }
    var days = Math.ceil(ms / 86400000);
    if (days > 1) { el.textContent = 'T-' + days + ' DAYS'; return; }
    var h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60;
    el.textContent = 'T-' + String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  }
  tick();
  setInterval(tick, 30000);
})();
