// CAMO network status: reads the Seal Watch feed of each seed node (public JSON in the camo-status repository) and
// shows one overall status. HOLD if any seed says HOLD, else CAUTION if any says CAUTION, else OK if a seed reported
// recently. Text only (textContent), nothing from the feed is ever run or inserted as HTML.
(function () {
  'use strict';
  var BASE = 'https://raw.githubusercontent.com/thedifference7717-sys/camo-status/main/';
  var SEEDS = ['seed1', 'seed2'];
  var STALE = 45 * 60;            // a seed publishes at least every 30 minutes
  var RANK = { OK: 0, CAUTION: 1, HOLD: 2 };
  var TEXT = {
    OK: ['ALL CLEAR', 'Nothing unusual on the network. Services can credit CAMO deposits normally.'],
    CAUTION: ['CAUTION', 'The Seals saw something unusual (a reorganization, a burst of blocks or a hashrate swing). ' +
      'Services should wait for extra confirmations (30 or more) before crediting deposits.'],
    HOLD: ['HOLD DEPOSITS', 'The Seals saw a possible attack (a double-spend attempt or a deep chain reorganization). ' +
      'Services should not credit CAMO deposits until this clears. Coins already in your wallet are not affected.'],
    DRILL: ['HOLD · DRILL', 'This is a scheduled test of the Seals\' HOLD flag, not a real problem. Services that ' +
      'follow the flag pause deposits for the drill, exactly as they would for a real alarm.'],
    UNKNOWN: ['NOT REPORTING', 'No seed has reported in the last 45 minutes. The status feed starts with mainnet on ' +
      'December 14, 2026; after that, this means the watch itself needs attention.']
  };

  function el(id) { return document.getElementById(id); }
  function ago(sec) {
    if (sec < 90) return Math.round(sec) + ' s ago';
    if (sec < 5400) return Math.round(sec / 60) + ' min ago';
    return Math.round(sec / 3600) + ' h ago';
  }
  function fetchSeed(name) {
    return fetch(BASE + name + '.json', { cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { return d && typeof d.status === 'string' && RANK.hasOwnProperty(d.status) ? d : null; })
      .catch(function () { return null; });
  }
  function render(results) {
    var now = Date.now() / 1000, overall = null, list = el('seeds');
    list.textContent = '';
    results.forEach(function (d, i) {
      var li = document.createElement('li');
      var fresh = d && typeof d.updated === 'number' && now - d.updated < STALE;
      var st = fresh ? d.status : 'UNKNOWN';
      if (fresh && (overall === null || RANK[st] > RANK[overall])) overall = st;
      var name = document.createElement('strong');
      name.textContent = SEEDS[i] + ': ' + st;
      li.appendChild(name);
      var info = [];
      if (d && d.network) info.push(String(d.network));
      if (d && typeof d.height === 'number') info.push('height ' + d.height);
      if (d && typeof d.updated === 'number') info.push('reported ' + ago(now - d.updated));
      if (!d) info.push('no report yet');
      li.appendChild(document.createTextNode(' · ' + info.join(' · ')));
      if (fresh && d.reasons && d.reasons.length) {
        var ul = document.createElement('ul');
        d.reasons.slice(0, 5).forEach(function (r) {
          var x = document.createElement('li');
          x.textContent = String(r);
          ul.appendChild(x);
        });
        li.appendChild(ul);
      }
      list.appendChild(li);
    });
    var key = overall || 'UNKNOWN';
    if (key === 'HOLD') {
      var holdReasons = [];
      results.forEach(function (d) {
        if (d && d.status === 'HOLD' && now - d.updated < STALE) holdReasons = holdReasons.concat(d.reasons || []);
      });
      if (holdReasons.length && holdReasons.every(function (r) { return String(r).indexOf('DRILL') === 0; })) key = 'DRILL';
    }
    var box = el('status');
    box.className = 'status-box st-' + (key === 'DRILL' ? 'hold' : key.toLowerCase());
    el('status-word').textContent = TEXT[key][0];
    el('status-text').textContent = TEXT[key][1];
    el('checked').textContent = 'Checked ' + new Date().toUTCString().replace('GMT', 'UTC') + '. Refreshes every minute.';
  }
  function run() { Promise.all(SEEDS.map(fetchSeed)).then(render); }
  run();
  setInterval(run, 60000);
})();
