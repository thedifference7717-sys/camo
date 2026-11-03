// CAMO opening screen: a living pixel-camo field with the word CAMO hidden in it.
// Aim the scope at the word; once it reads TARGET ACQUIRED, click to enter the site.
// No dependencies, no network. Without JavaScript the "Enter site" link still works.
(function () {
  'use strict';
  var HOME = 'home.html';
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var canvas = document.getElementById('camo-field');
  var status = document.getElementById('scope-status');
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext('2d');
  var touchy = window.matchMedia && window.matchMedia('(hover: none)').matches;

  var BG = [11, 15, 12];
  var PAL = [[46, 71, 44], [62, 91, 58], [86, 116, 76], [111, 138, 94]]; // logo greens, dark -> light
  var AMBER = [224, 166, 58];
  function mix(a, b, k) { return 'rgb(' + a.map(function (v, i) { return Math.round(v + (b[i] - v) * k); }).join(',') + ')'; }
  var DIM = PAL.map(function (c) { return mix(c, BG, 0.42); });
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
  var scope = { x: 0, y: 0, tx: 0, ty: 0, r: 120, base: 120 };
  var t0 = performance.now(), lastInput = t0 - 1500, locked = false, entering = false, placed = false;

  function buildMask() {
    var off = document.createElement('canvas'); off.width = cols; off.height = rows;
    var o = off.getContext('2d');
    var wordW = W > 900 ? cols * 0.46 : cols * 0.84;
    var size = Math.max(6, Math.floor(wordW / 2.9));
    o.font = '700 ' + size + 'px "Chakra Petch", system-ui, sans-serif';
    o.textBaseline = 'middle'; o.textAlign = 'center';
    o.fillStyle = '#fff'; o.fillText('CAMO', cols * 0.5, rows * 0.5);
    var d = o.getImageData(0, 0, cols, rows).data;
    mask = new Uint8Array(cols * rows);
    var minX = cols, maxX = 0, minY = rows, maxY = 0, n = 0;
    for (var i = 0; i < cols * rows; i++) if (d[i * 4 + 3] > 110) {
      mask[i] = 1; n++;
      var x = i % cols, y = (i / cols) | 0;
      if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    wordBox = n ? { x: (minX + maxX + 1) / 2 * C, y: (minY + maxY + 1) / 2 * C, w: (maxX - minX + 1) * C, h: (maxY - minY + 1) * C, n: n }
                : { x: W / 2, y: H / 2, w: 1, h: 1, n: 0 };
  }

  function resize() {
    W = Math.max(1, window.innerWidth); H = Math.max(1, window.innerHeight);
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    C = W < 600 ? 11 : 14;
    cols = Math.ceil(W / C); rows = Math.ceil(H / C);
    levels = new Uint8Array(cols * rows);
    scope.base = scope.r = Math.max(80, Math.min(180, Math.min(W, H) * 0.18));
    buildMask();
    if (!placed) { placed = true; scope.x = scope.tx = W * 0.15; scope.y = scope.ty = H * 0.28; }
  }

  function computeLevels(t) {
    for (var y = 0; y < rows; y++) for (var x = 0; x < cols; x++) {
      var n = 0.65 * noise(x * 0.085 + t * 0.35, y * 0.085) + 0.35 * noise(x * 0.21 - 40, y * 0.21 - t * 0.5);
      levels[y * cols + x] = n < 0.4 ? 0 : n < 0.5 ? 1 : n < 0.6 ? 2 : 3;
    }
  }

  function setStatus(isLocked) {
    if (!status || status.getAttribute('data-locked') === String(isLocked)) return;
    status.setAttribute('data-locked', String(isLocked));
    document.body.classList.toggle('locked', isLocked);
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
    for (y = Math.max(0, Math.floor(sy - R)) + scanOff; y < Math.min(H, sy + R); y += 4) ctx.fillRect(Math.max(0, sx - R), y, Math.min(W, R * 2), 1.5);
    var g = ctx.createRadialGradient(sx, sy, R * 0.55, sx, sy, R);
    g.addColorStop(0, 'rgba(8,11,9,0)'); g.addColorStop(1, 'rgba(8,11,9,0.55)');
    ctx.fillStyle = g; ctx.fillRect(sx - R, sy - R, R * 2, R * 2);
    ctx.restore();

    locked = entering || (wordBox.n > 0 && seen > wordBox.n * 0.18);
    setStatus(locked);
    if (entering) return;

    // reticle
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
    if (lx + 150 > W) lx = sx - R * 0.72 - 150;
    if (lx < 8) { lx = Math.max(8, sx - 60); ly = sy - R - 26; }
    if (ly < 20) ly = sy + R + 22;
    ctx.fillText(locked ? 'TARGET ACQUIRED' : 'SCANNING…', lx, ly);
    ctx.fillStyle = 'rgba(154,165,147,0.9)';
    ctx.fillText(locked ? (touchy ? 'TAP TO ENTER' : 'CLICK TO ENTER') : 'X' + String(Math.round(sx)).padStart(4, '0') + ' Y' + String(Math.round(sy)).padStart(4, '0'), lx, ly + 15);
  }

  // enter: the scope opens out to fill the screen, then the main site loads
  function enter() {
    if (entering) return;
    entering = true; document.body.classList.add('entering');
    if (reduceMotion) { location.href = HOME; return; }
    var start = performance.now(), from = scope.r, to = Math.hypot(W, H) * 1.05;
    (function grow(now) {
      var k = Math.min(1, (now - start) / 650), e = k * k * (3 - 2 * k);
      scope.r = from + (to - from) * e;
      draw(now);
      if (k < 1) requestAnimationFrame(grow); else location.href = HOME;
    })(start);
  }

  function aimAt(e) {
    if (!e.clientX && !e.clientY) return; // synthetic event at the corner, not a real aim
    scope.tx = e.clientX; scope.ty = e.clientY; lastInput = performance.now();
    if (reduceMotion) { scope.x = scope.tx; scope.y = scope.ty; requestAnimationFrame(draw); }
  }
  canvas.addEventListener('pointermove', aimAt, { passive: true });
  canvas.addEventListener('click', function (e) {
    var dx = e.clientX - scope.x, dy = e.clientY - scope.y;
    if (locked && dx * dx + dy * dy <= scope.r * scope.r) { enter(); return; }
    aimAt(e); // touch: a tap moves the scope there; tap again once it locks on
    if (!reduceMotion) { scope.x += (scope.tx - scope.x) * 0.6; scope.y += (scope.ty - scope.y) * 0.6; }
  });
  window.addEventListener('pageshow', function (e) { // coming back with the Back button
    if (e.persisted) { entering = false; document.body.classList.remove('entering'); scope.r = scope.base; }
  });

  var running = false, raf = 0, lastFrame = 0;
  function step(now) {
    raf = 0;
    if (!running) return;
    if (!entering && now - lastFrame >= 33) { // ~30 fps is plenty
      lastFrame = now;
      if (now - lastInput > 3000) { // idle: sweep across the word so people see what's hiding
        var t = (now - t0) / 1000;
        scope.tx = wordBox.x + Math.sin(t * 0.4 - 1.2) * Math.max(wordBox.w * 0.55, scope.r);
        scope.ty = wordBox.y + Math.sin(t * 0.8) * Math.min(wordBox.h * 0.45, scope.r * 0.6);
      }
      scope.x += (scope.tx - scope.x) * 0.14;
      scope.y += (scope.ty - scope.y) * 0.14;
      draw(now);
    }
    raf = requestAnimationFrame(step);
  }
  function update() {
    var should = !document.hidden && !reduceMotion;
    if (should && !running) { running = true; if (!raf) raf = requestAnimationFrame(step); }
    if (!should) running = false;
  }

  function init() {
    resize();
    if (reduceMotion) { scope.x = scope.tx = wordBox.x; scope.y = scope.ty = wordBox.y; draw(t0); }
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
