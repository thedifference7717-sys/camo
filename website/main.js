// CAMO site: launch clock, headline decrypt, and the living camo field with its scope.
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

  // ---- living camo field ---------------------------------------------------
  var canvas = document.getElementById('camo-field');
  if (!canvas || !canvas.getContext) return;
  var hero = canvas.parentNode, ctx = canvas.getContext('2d');

  var BG = [11, 15, 12];
  var PAL = [[46, 71, 44], [62, 91, 58], [86, 116, 76], [111, 138, 94]]; // logo greens, dark -> light
  var AMBER = [224, 166, 58];
  function mix(a, b, k) { return 'rgb(' + a.map(function (v, i) { return Math.round(v + (b[i] - v) * k); }).join(',') + ')'; }
  var DIM = PAL.map(function (c) { return mix(c, BG, 0.5); });
  var BRIGHT = PAL.map(function (c) { return mix(c, [255, 255, 255], 0.06); });
  var GLOW = [mix(AMBER, BG, 0.25), mix(AMBER, BG, 0.05)];

  function hash(x, y) { var h = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return h - Math.floor(h); }
  function noise(x, y) {
    var ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
    var a = hash(ix, iy), b = hash(ix + 1, iy), c = hash(ix, iy + 1), d = hash(ix + 1, iy + 1);
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
  }

  var W, H, dpr, C, cols, rows, mask, levels, wordBox;
  var scope = { x: 0, y: 0, tx: 0, ty: 0, r: 120 }, lastInput = -1e9, t0 = performance.now();

  function buildMask() {
    var off = document.createElement('canvas'); off.width = cols; off.height = rows;
    var o = off.getContext('2d'), wide = W > 900;
    var wordW = wide ? cols * 0.36 : cols * 0.82;
    var size = Math.max(6, Math.floor(wordW / 2.9));
    o.font = '700 ' + size + 'px "Chakra Petch", system-ui, sans-serif';
    o.textBaseline = 'middle'; o.textAlign = 'center';
    var cx = wide ? cols * 0.76 : cols * 0.5;
    var cy = wide ? rows * 0.5 : rows - Math.max(size * 0.8, (130 / C));
    o.fillStyle = '#fff'; o.fillText('CAMO', cx, cy);
    var d = o.getImageData(0, 0, cols, rows).data;
    mask = new Uint8Array(cols * rows);
    var minX = cols, maxX = 0, minY = rows, maxY = 0, n = 0;
    for (var i = 0; i < cols * rows; i++) if (d[i * 4 + 3] > 110) {
      mask[i] = 1; n++;
      var x = i % cols, y = (i / cols) | 0;
      if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    wordBox = n ? { x: (minX + maxX + 1) / 2 * C, y: (minY + maxY + 1) / 2 * C, w: (maxX - minX + 1) * C, h: (maxY - minY + 1) * C, n: n }
                : { x: W * 0.7, y: H * 0.5, w: 1, h: 1, n: 0 };
  }

  function resize() {
    var r = hero.getBoundingClientRect();
    W = Math.max(1, Math.round(r.width)); H = Math.max(1, Math.round(r.height));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    C = W < 600 ? 11 : 14;
    cols = Math.ceil(W / C); rows = Math.ceil(H / C);
    levels = new Uint8Array(cols * rows);
    scope.r = Math.max(80, Math.min(170, Math.min(W, H) * 0.17));
    buildMask();
    if (lastInput < 0) { scope.x = scope.tx = wordBox.x - wordBox.w * 0.35; scope.y = scope.ty = wordBox.y; }
  }

  function computeLevels(t) {
    for (var y = 0; y < rows; y++) for (var x = 0; x < cols; x++) {
      var n = 0.65 * noise(x * 0.085 + t * 0.35, y * 0.085) + 0.35 * noise(x * 0.21 - 40, y * 0.21 - t * 0.5);
      levels[y * cols + x] = n < 0.4 ? 0 : n < 0.5 ? 1 : n < 0.6 ? 2 : 3;
    }
  }

  function draw(now) {
    var t = reduceMotion ? 0 : (now - t0) / 1000;
    computeLevels(t);
    var x, y, i, lv;
    for (y = 0; y < rows; y++) for (x = 0; x < cols; x++) {
      i = y * cols + x; lv = levels[i];
      if (mask[i]) lv = lv < 3 ? lv + 1 : 3; // the word sits one shade lighter: there, if you look for it
      ctx.fillStyle = DIM[lv];
      ctx.fillRect(x * C, y * C, C, C);
    }
    // scope: sharper colours and the hidden word lit up
    var R = scope.r, sx = scope.x, sy = scope.y, seen = 0;
    ctx.save();
    ctx.beginPath(); ctx.arc(sx, sy, R, 0, Math.PI * 2); ctx.clip();
    var x0 = Math.max(0, Math.floor((sx - R) / C)), x1 = Math.min(cols - 1, Math.floor((sx + R) / C));
    var y0 = Math.max(0, Math.floor((sy - R) / C)), y1 = Math.min(rows - 1, Math.floor((sy + R) / C));
    for (y = y0; y <= y1; y++) for (x = x0; x <= x1; x++) {
      i = y * cols + x;
      if (mask[i]) {
        ctx.fillStyle = GLOW[levels[i] & 1];
        var dx = (x + 0.5) * C - sx, dy = (y + 0.5) * C - sy;
        if (dx * dx + dy * dy < R * R) seen++;
      } else ctx.fillStyle = BRIGHT[levels[i]];
      ctx.fillRect(x * C, y * C, C, C);
    }
    ctx.fillStyle = 'rgba(8,11,9,0.22)';
    var scanOff = reduceMotion ? 0 : Math.floor(t * 12) % 4;
    for (y = Math.floor(sy - R) + scanOff; y < sy + R; y += 4) ctx.fillRect(sx - R, y, R * 2, 1.5);
    var g = ctx.createRadialGradient(sx, sy, R * 0.55, sx, sy, R);
    g.addColorStop(0, 'rgba(8,11,9,0)'); g.addColorStop(1, 'rgba(8,11,9,0.55)');
    ctx.fillStyle = g; ctx.fillRect(sx - R, sy - R, R * 2, R * 2);
    ctx.restore();

    // reticle
    var locked = wordBox.n && seen > wordBox.n * 0.18;
    var ink = locked ? 'rgba(224,166,58,0.95)' : 'rgba(201,214,184,0.8)';
    ctx.strokeStyle = ink; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(sx, sy, R, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(sx, sy, R + 6, -0.35, 0.35); ctx.stroke();
    ctx.beginPath(); ctx.arc(sx, sy, R + 6, Math.PI - 0.35, Math.PI + 0.35); ctx.stroke();
    var gap = 10;
    ctx.beginPath();
    ctx.moveTo(sx - R, sy); ctx.lineTo(sx - gap, sy); ctx.moveTo(sx + gap, sy); ctx.lineTo(sx + R, sy);
    ctx.moveTo(sx, sy - R); ctx.lineTo(sx, sy - gap); ctx.moveTo(sx, sy + gap); ctx.lineTo(sx, sy + R);
    for (var k = 1; k <= 3; k++) {
      var m = (R / 4) * k;
      ctx.moveTo(sx - m, sy - 4); ctx.lineTo(sx - m, sy + 4); ctx.moveTo(sx + m, sy - 4); ctx.lineTo(sx + m, sy + 4);
      ctx.moveTo(sx - 4, sy + m); ctx.lineTo(sx + 4, sy + m);
    }
    ctx.stroke();
    ctx.fillStyle = ink;
    ctx.fillRect(sx - 1.5, sy - 1.5, 3, 3);
    ctx.font = '600 11px "JetBrains Mono", ui-monospace, monospace';
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    var lx = sx + R * 0.72, ly = sy - R * 0.72;
    if (lx + 130 > W) lx = sx - R * 0.72 - 130;
    ctx.fillText(locked ? 'TARGET ACQUIRED' : 'SCANNING…', lx, ly);
    ctx.fillStyle = 'rgba(154,165,147,0.9)';
    ctx.fillText('X' + String(Math.round(sx)).padStart(4, '0') + ' Y' + String(Math.round(sy)).padStart(4, '0'), lx, ly + 15);
  }

  // input: the scope follows the pointer; idle, it sweeps on its own past the hidden word
  function aim(e) {
    var r = hero.getBoundingClientRect();
    var x = e.clientX - r.left, y = e.clientY - r.top;
    if (x < 0 || y < 0 || x > r.width || y > r.height) return;
    scope.tx = x; scope.ty = y; lastInput = performance.now();
    if (reduceMotion) { scope.x = x; scope.y = y; request(); }
  }
  window.addEventListener('pointermove', aim, { passive: true });
  window.addEventListener('pointerdown', aim, { passive: true });

  var running = false, visible = true, raf = 0, lastFrame = 0;
  function step(now) {
    raf = 0;
    if (!running) return;
    if (now - lastFrame >= 33) { // ~30 fps is plenty
      lastFrame = now;
      if (now - lastInput > 3500) {
        var t = (now - t0) / 1000;
        var ax = Math.min(wordBox.w * 0.5, Math.max(0, W - scope.r * 0.8 - wordBox.x));
        scope.tx = wordBox.x + Math.sin(t * 0.45) * ax;
        scope.ty = wordBox.y + Math.sin(t * 0.9 + 0.6) * Math.min(wordBox.h * 0.4, scope.r * 0.5);
      }
      scope.x += (scope.tx - scope.x) * 0.14;
      scope.y += (scope.ty - scope.y) * 0.14;
      draw(now);
    }
    raf = requestAnimationFrame(step);
  }
  function request() { if (reduceMotion) { requestAnimationFrame(draw); } }
  function update() {
    var should = visible && !document.hidden && !reduceMotion;
    if (should && !running) { running = true; if (!raf) raf = requestAnimationFrame(step); }
    if (!should) running = false;
  }

  function init() {
    resize();
    if (reduceMotion) { scope.x = wordBox.x; scope.y = wordBox.y; draw(t0); }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { visible = es[0].isIntersecting; update(); }).observe(hero);
    }
    document.addEventListener('visibilitychange', update);
    var rt = 0;
    window.addEventListener('resize', function () {
      clearTimeout(rt);
      rt = setTimeout(function () { resize(); if (reduceMotion) draw(performance.now()); }, 120);
    });
    update();
  }
  // wait for the display font so the hidden word has the right shape
  if (document.fonts && document.fonts.load) {
    Promise.all([document.fonts.load('700 40px "Chakra Petch"'), document.fonts.load('600 11px "JetBrains Mono"')])
      .then(init, init);
  } else init();
})();
