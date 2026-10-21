/* Bloki · landing por avatar. Mismo comportamiento que Plenara:
   un solo punto de conversión (el buy box), todos los CTA bajan ahí con
   destello, sticky que aparece a los 700px, popup de descuento.
   El botón de compra arma un permalink de carrito de Shopify:
   /cart/VARIANTE:CANT,VARIANTE:CANT  (vacía el carrito y va al checkout). */
(function () {
  // Cada pieza es opcional: en el tema de Shopify las secciones se pueden quitar o mover,
  // y el editor vuelve a llamar init() cuando recarga una sección.
  var once = function (el, k) { k = '_bk' + (k || ''); if (el[k]) return false; el[k] = 1; return true; };
  var init = function () {
  var cfgEl = document.getElementById('bk-config');
  var cfg = cfgEl ? JSON.parse(cfgEl.textContent) : { variants: {}, unitPrice: 0 };
  var fmt = function (n) { return '$' + Math.round(n).toLocaleString('es-CO').replace(/,/g, '.'); };

  // ── CTA → buy box con destello ──
  document.querySelectorAll('[data-goto-buy]').forEach(function (a) {
    if (once(a)) a.addEventListener('click', function (e) {
      var target = document.getElementById('comprar'), card = document.querySelector('.buy__card');
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setTimeout(function () { card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash'); }, 450);
    });
  });

  // ── Carruseles ──
  document.querySelectorAll('.carousel').forEach(function (c) {
    if (!once(c)) return;
    var track = c.querySelector('.track'), items = track.children, dots = c.querySelector('.c-dots');
    if (dots) for (var i = 0; i < items.length; i++) dots.appendChild(document.createElement('i'));
    var cur = function () {
      var x = track.scrollLeft, best = 0;
      for (var i = 0; i < items.length; i++) if (Math.abs(items[i].offsetLeft - track.offsetLeft - 16 - x) < Math.abs(items[best].offsetLeft - track.offsetLeft - 16 - x)) best = i;
      return best;
    };
    var paint = function () { if (!dots) return; var k = cur(); [].forEach.call(dots.children, function (d, i) { d.classList.toggle('on', i === k); }); };
    var go = function (d) { var k = Math.max(0, Math.min(items.length - 1, cur() + d)); track.scrollTo({ left: items[k].offsetLeft - track.offsetLeft - 16, behavior: 'smooth' }); };
    var p = c.querySelector('[data-prev]'), n = c.querySelector('[data-next]');
    if (p) p.onclick = function () { go(-1); };
    if (n) n.onclick = function () { go(1); };
    track.addEventListener('scroll', function () { requestAnimationFrame(paint); }, { passive: true });
    paint();
  });

  // ── Galería ──
  var slides = document.querySelectorAll('.gal__slide'), thumbs = document.querySelectorAll('.thumbs button'), gi = 0;
  var show = function (i) {
    gi = (i + slides.length) % slides.length;
    slides.forEach(function (s, k) { s.classList.toggle('on', k === gi); });
    thumbs.forEach(function (t, k) { t.classList.toggle('on', k === gi); });
  };
  thumbs.forEach(function (t, k) { t.onclick = function () { show(k); }; });
  var gp = document.querySelector('[data-gal-prev]'), gn = document.querySelector('[data-gal-next]');
  if (gp) gp.onclick = function () { show(gi - 1); };
  if (gn) gn.onclick = function () { show(gi + 1); };

  // ── Planes + colores + total ──
  var plans = document.querySelectorAll('.plan'), sel = null;
  var totalEl = document.querySelector('[data-total]'), cmpEl = document.querySelector('[data-compare]'), saveEl = document.querySelector('[data-save]');
  var pick = function (p) {
    plans.forEach(function (x) { x.classList.toggle('on', x === p); x.setAttribute('aria-checked', x === p); });
    sel = p;
    var qty = +p.dataset.qty, price = +p.dataset.price, full = cfg.unitPrice * qty;
    if (!totalEl) return;
    totalEl.textContent = fmt(price);
    if (full > price) { cmpEl.textContent = fmt(full); cmpEl.hidden = false; saveEl.textContent = 'AHORRAS ' + fmt(full - price); saveEl.hidden = false; }
    else { cmpEl.hidden = true; saveEl.hidden = true; }
  };
  plans.forEach(function (p) {
    if (!once(p)) return;
    p.addEventListener('click', function (e) { if (!e.target.closest('.sw')) pick(p); });
    p.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(p); } });
    p.querySelectorAll('.colors__row').forEach(function (row) {
      row.querySelectorAll('.sw button').forEach(function (b) {
        if (once(b)) b.addEventListener('click', function () {
          row.querySelectorAll('.sw button').forEach(function (x) { x.classList.remove('on'); });
          b.classList.add('on');
          row.querySelector('b').textContent = b.dataset.color;
          pick(p);
        });
      });
    });
  });
  if (plans.length && totalEl) pick(document.querySelector('.plan.on') || plans[0]);

  // ── Fecha estimada de entrega (hora Bogotá) ──
  // Antes de las 12 m. en día hábil sale hoy; si no, sale el siguiente día hábil.
  // Llega entre 2 y 3 días hábiles después de salir, siempre "antes de las 6 p. m.".
  // Festivos de Colombia calculados (Ley Emiliani), así no se vencen.
  var etaEl = document.querySelector('[data-eta]');
  if (etaEl) {
    var DAY = 864e5, utc = function (y, m, d) { return Date.UTC(y, m, d); };
    var festivos = {};
    var addF = function (t) { festivos[new Date(t).toISOString().slice(0, 10)] = 1; };
    var lunes = function (t) { var w = new Date(t).getUTCDay(); return t + ((8 - w) % 7) * DAY; };
    var cargar = function (y) {
      if (festivos['y' + y]) return; festivos['y' + y] = 1;
      [[0, 1], [4, 1], [6, 20], [7, 7], [11, 8], [11, 25]].forEach(function (f) { addF(utc(y, f[0], f[1])); });
      [[0, 6], [2, 19], [5, 29], [7, 15], [9, 12], [10, 1], [10, 11]].forEach(function (f) { addF(lunes(utc(y, f[0], f[1]))); });
      var a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25),
          g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4,
          l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451),
          mes = Math.floor((h + l - 7 * m + 114) / 31) - 1, dia = ((h + l - 7 * m + 114) % 31) + 1, pascua = utc(y, mes, dia);
      [-3, -2, 43, 64, 71].forEach(function (n) { addF(pascua + n * DAY); });
    };
    var habil = function (t) { var dt = new Date(t), w = dt.getUTCDay(); cargar(dt.getUTCFullYear()); return w && w !== 6 && !festivos[dt.toISOString().slice(0, 10)]; };
    var sumar = function (t, n) { while (n > 0) { t += DAY; if (habil(t)) n--; } return t; };
    var bog = new Date(Date.now() - 5 * 36e5), hoy = utc(bog.getUTCFullYear(), bog.getUTCMonth(), bog.getUTCDate());
    var sale = habil(hoy) && bog.getUTCHours() < 12 ? hoy : sumar(hoy, 1);
    var desde = new Date(sumar(sale, 2)), hasta = new Date(sumar(sale, 3));
    var DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'],
        MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    var f1 = DIAS[desde.getUTCDay()] + ' ' + desde.getUTCDate(), f2 = DIAS[hasta.getUTCDay()] + ' ' + hasta.getUTCDate() + ' de ' + MESES[hasta.getUTCMonth()];
    if (desde.getUTCMonth() !== hasta.getUTCMonth()) f1 += ' de ' + MESES[desde.getUTCMonth()];
    etaEl.innerHTML = 'Pide hoy y llega entre el <b>' + f1 + '</b> y el <b>' + f2 + '</b>, antes de las 6:00 p. m.';
  }

  // ── Comprar: permalink de carrito Shopify ──
  var err = document.querySelector('.buy__err'), buyBtn = document.querySelector('[data-buy]');
  if (buyBtn && once(buyBtn)) buyBtn.addEventListener('click', function () {
    if (!sel) return;
    var btn = this, counts = {}, missing = false;
    sel.querySelectorAll('.colors__row .sw button.on').forEach(function (b) {
      var id = cfg.variants[b.dataset.color];
      if (!id) missing = true;
      counts[id] = (counts[id] || 0) + 1;
    });
    if (missing) {
      err.textContent = 'La compra se hace en la tienda (blokipresente.co). Esta es una vista previa.';
      return;
    }
    btn.disabled = true; btn.textContent = 'Procesando...';
    var items = Object.keys(counts).map(function (id) { return id + ':' + counts[id]; }).join(',');
    var url = (cfg.store ? 'https://' + cfg.store : '') + '/cart/' + items;
    if (cfg.discountCodes && cfg.discountCodes[sel.dataset.qty]) url += '?discount=' + encodeURIComponent(cfg.discountCodes[sel.dataset.qty]);
    window.location.href = url;
  });

  // ── Funciones en pestañas ──
  document.querySelectorAll('.fx').forEach(function (fx) {
    var tabs = fx.querySelectorAll('[role=tab]'), panels = fx.querySelectorAll('[role=tabpanel]');
    tabs.forEach(function (t, k) {
      t.onclick = function () {
        tabs.forEach(function (x, i) { x.classList.toggle('on', i === k); x.setAttribute('aria-selected', i === k); });
        panels.forEach(function (p, i) { p.hidden = i !== k; });
      };
    });
  });

  // ── Video: se reproduce (sin sonido) solo cuando está a la vista ──
  if ('IntersectionObserver' in window) document.querySelectorAll('video[data-autoplay], .vid video').forEach(function (v) {
    if (!once(v)) return;
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause(); });
    }, { threshold: 0.4 }).observe(v);
  });

  // ── Sticky a los 700px ──
  var sticky = document.querySelector('.sticky');
  if (sticky && once(window, 'scroll')) window.addEventListener('scroll', function () {
    var buy = document.getElementById('comprar'), st = document.querySelector('.sticky');
    if (!buy || !st) return;
    var r = buy.getBoundingClientRect(), inBuy = r.top < window.innerHeight && r.bottom > 0;
    st.classList.toggle('show', window.scrollY > 700 && !inBuy);
  }, { passive: true });

  // ── Popup de descuento ──
  var pop = document.querySelector('.pop'), teaser = document.querySelector('.teaser');
  if (!pop || !teaser || !once(pop)) return;
  var KEY = 'bloki_pop_' + cfg.slug, seen = false;
  try { seen = sessionStorage.getItem(KEY) === '1'; } catch (e) {}
  var open = function () { pop.classList.add('show'); try { sessionStorage.setItem(KEY, '1'); } catch (e) {} };
  var close = function () { pop.classList.remove('show'); };
  teaser.onclick = open;
  pop.querySelectorAll('[data-pop-close]').forEach(function (b) { b.onclick = close; });
  pop.addEventListener('click', function (e) { if (e.target === pop) close(); });
  if (!seen && cfg.popupDelay) setTimeout(open, cfg.popupDelay * 1000);
  pop.querySelector('form').addEventListener('submit', function (e) {
    e.preventDefault();
    // Conectar a Klaviyo aquí. Mientras tanto solo confirma en pantalla.
    pop.querySelector('.pop__body').innerHTML = '<h3>Listo.</h3><p>Tu código es <b>' + cfg.popupCode + '</b>. Úsalo en el pago.</p><button class="btn btn--block" data-pop-close type="button">Volver</button>';
    pop.querySelector('[data-pop-close]').onclick = close;
  });
  };
  init();
  document.addEventListener('shopify:section:load', init);
})();
