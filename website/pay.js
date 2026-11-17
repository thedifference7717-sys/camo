// camocoin.org/pay#camo:<address>?tx_amount=..&tx_description=..
// Everything after '#' stays in the browser (never sent to the server). No network requests are made here.
(function () {
  var raw = decodeURIComponent((location.hash || '').slice(1));
  var m = /^camo:(?:\/\/)?([1-9A-HJ-NP-Za-km-z]{95,106})(?:\?(.*))?$/.exec(raw);
  var $ = function (id) { return document.getElementById(id); };
  if (!m) { $('bad').hidden = false; return; }
  var addr = m[1], params = {};
  (m[2] || '').split('&').forEach(function (kv) {
    var i = kv.indexOf('=');
    if (i > 0) params[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1).replace(/\+/g, ' '));
  });
  var amt = params.tx_amount && /^\d+(\.\d{1,12})?$/.test(params.tx_amount) ? params.tx_amount : null;
  $('amt').textContent = amt || 'Any amount';
  if (!amt) document.querySelector('.pay-unit').hidden = true;
  if (params.tx_description) { $('note').textContent = 'For: ' + params.tx_description.slice(0, 60); $('note').hidden = false; }
  $('addr').textContent = addr;
  var q = [];
  if (amt) q.push('tx_amount=' + amt);
  if (params.tx_description) q.push('tx_description=' + encodeURIComponent(params.tx_description.slice(0, 60)));
  $('open').href = 'camo:' + addr + (q.length ? '?' + q.join('&') : '');
  $('copy').addEventListener('click', function () {
    navigator.clipboard.writeText(addr).then(function () { $('copied').hidden = false; });
  });
  $('req').hidden = false;
})();
