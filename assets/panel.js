/* Bloki · panel de control del proyecto.
   Pestañas: Landings (las genera build.py), Escenario financiero y Pendientes.
   Todo se guarda en este navegador (localStorage). Exportar/Importar mueve los datos a otro equipo.
   El modelo financiero es el de Orbit: pauta por día × ROAS = venta; de ahí salen pedidos,
   costo de producto, costos variables, fijos, utilidad, BE ROAS y "a dónde va cada peso". */
(function () {
  var CFG = JSON.parse(document.getElementById('panel-config').textContent);
  var KEY = 'bloki_panel_v1';
  var IVA = 0.19;

  // ── utilidades ──
  var uid = function () { return Math.random().toString(36).slice(2, 9); };
  var money = function (n) {
    if (!isFinite(n)) return '—';
    var s = Math.round(Math.abs(n)).toLocaleString('es-CO').replace(/,/g, '.');
    return (n < 0 ? '−$' : '$') + s;
  };
  var pct = function (n) { return isFinite(n) ? (n * 100).toFixed(1).replace('.', ',') + ' %' : '—'; };
  var xr = function (n) { return isFinite(n) && n > 0 ? n.toFixed(2).replace('.', ',') + 'x' : 'No alcanza'; };
  var int = function (n) { return isFinite(n) ? Math.round(n).toLocaleString('es-CO').replace(/,/g, '.') : '—'; };
  var digits = function (s) { var d = String(s).replace(/\D/g, ''); return d ? +d : 0; };
  var dec = function (s) { var v = parseFloat(String(s).replace(',', '.')); return isNaN(v) ? 0 : v; };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var fmtIn = function (n) { return n ? Math.round(n).toLocaleString('es-CO').replace(/,/g, '.') : ''; };
  var hoy = function () { var d = new Date(Date.now() - 5 * 36e5); return d.toISOString().slice(0, 10); };

  // ── estado inicial (los valores marcados "sup" son supuestos para reemplazar) ──
  var seed = function () {
    return {
      v: 1,
      costeo: {
        iva: true,
        unit: [
          { id: uid(), name: 'Fabricación del Bloki (cuerpo tejido + cara)', amount: 18000, sup: true },
          { id: uid(), name: 'Chip NFC', amount: 1500, sup: true },
          { id: uid(), name: 'Caja', amount: 3500, sup: true },
          { id: uid(), name: 'Instrucciones + tarjeta de bienvenida', amount: 800, sup: true }
        ],
        order: [
          { id: uid(), name: 'Envío nacional', amount: 12000, sup: true },
          { id: uid(), name: 'Empaque de envío', amount: 1200, sup: true }
        ],
        fee: { pct: 2.99, fixed: 900, ivaFee: true }
      },
      pcts: [
        { id: uid(), name: 'Desarrollador de la app', pct: 0, base: 'util', sup: true },
        { id: uid(), name: 'Diseñadores', pct: 0, base: 'util', sup: true }
      ],
      fijos: [
        { id: uid(), name: 'Shopify', amount: 160000, sup: true },
        { id: uid(), name: 'Servidor de la app', amount: 100000, sup: true },
        { id: uid(), name: 'Apple Developer (anual ÷ 12)', amount: 33000, sup: true },
        { id: uid(), name: 'Contenido y creadores', amount: 1500000, sup: true }
      ],
      escenarios: [
        { id: uid(), name: 'Prueba', adsDay: 100000, roas: 2, mix: [60, 25, 15] },
        { id: uid(), name: 'Base', adsDay: 300000, roas: 2.5, mix: [50, 30, 20] },
        { id: uid(), name: 'Escala', adsDay: 1000000, roas: 2.2, mix: [50, 30, 20] }
      ],
      tareas: CFG.tareas.map(function (t) {
        return { id: uid(), title: t[0], owner: t[1] || 'Juanfe', due: t[2] || '', status: t[3] || 'todo', prio: t[4] || 'media' };
      })
    };
  };

  // ── guardado: Supabase (compartido, con clave) + copia local en este navegador ──
  var R = CFG.remote, PKEY = 'bloki_panel_key', PWHO = 'bloki_panel_quien';
  var state = null, base = null, key = null, who = '', saveTimer = null, saving = false, dirty = false;
  try { key = localStorage.getItem(PKEY); who = localStorage.getItem(PWHO) || ''; } catch (e) {}
  var savedEl = document.querySelector('[data-saved]');
  var status = function (t) { savedEl.textContent = t; };
  var hora = function (iso) { return new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }); };
  var rpc = function (fn, body) {
    return fetch(R.url + '/rest/v1/rpc/' + fn, {
      method: 'POST', headers: { apikey: R.key, Authorization: 'Bearer ' + R.key, 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    }).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.message || 'Error'); return j; }); });
  };
  var cacheLocal = function () { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
  var pushNow = function () {
    if (!key) return;
    saving = true; dirty = false; status('Guardando…');
    rpc('panel_save', { p_id: R.id, p_key: key, p_data: state, p_base: base, p_by: who || null }).then(function (res) {
      saving = false;
      if (res.conflict) {
        state = norm(res.data); base = res.updated_at; cacheLocal(); renderAll();
        status('Alguien más guardó a las ' + hora(base) + (res.updated_by ? ' (' + res.updated_by + ')' : '') + '. Cargué esa versión: repite tu último cambio.');
        return;
      }
      base = res.updated_at;
      status('Guardado para todos · ' + hora(base));
      if (dirty) pushNow();
    }).catch(function (err) {
      saving = false; dirty = true;
      status(/clave/i.test(err.message) ? 'La clave cambió. Recarga e ingresa de nuevo.' : 'Sin conexión: guardado solo en este navegador. Reintento en unos segundos…');
      clearTimeout(saveTimer); saveTimer = setTimeout(pushNow, 8000);
    });
  };
  var save = function () {
    cacheLocal(); dirty = true; status('Cambios sin guardar…');
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () { if (!saving) pushNow(); }, 700);
  };
  // trae cambios de los demás cada 20 s, si no estás escribiendo
  setInterval(function () {
    if (!key || saving || dirty || document.hidden) return;
    var a = document.activeElement;
    if (a && /INPUT|SELECT|TEXTAREA/.test(a.tagName) && a.closest('[data-pane]')) return;
    rpc('panel_load', { p_id: R.id, p_key: key }).then(function (res) {
      if (res.updated_at !== base) { state = norm(res.data); base = res.updated_at; cacheLocal(); renderAll(); status('Actualizado con cambios de ' + (res.updated_by || 'otra persona') + ' · ' + hora(base)); }
    }).catch(function () {});
  }, 20000);

  // ── pantalla de clave ──
  var lock = document.querySelector('[data-lock]');
  var lockForm = lock.querySelector('form'), lockMsg = lock.querySelector('[data-lock-msg]');
  var openLock = function (mode, msg) {
    lock.hidden = false; lock.dataset.mode = mode;
    lock.querySelector('[data-lock-title]').textContent = mode === 'claim' ? 'Crea la clave del panel' : 'Ingresa la clave del panel';
    lock.querySelector('[data-lock-sub]').textContent = mode === 'claim'
      ? 'Es la primera vez que se abre. La clave protege los costos y las tareas; compártela solo con tu equipo. Mínimo 8 caracteres.'
      : 'Los datos del panel están protegidos. Pide la clave a quien administra el proyecto.';
    lock.querySelector('[data-lock-confirm]').hidden = mode !== 'claim';
    lockForm.quien.value = who;
    lockMsg.textContent = msg || '';
    setTimeout(function () { lockForm.clave.focus(); }, 50);
  };
  var unlocked = function (res, k) {
    key = k; state = norm(res.data && res.data.v === 1 ? res.data : seed()); base = res.updated_at;
    try { localStorage.setItem(PKEY, k); } catch (e) {}
    lock.hidden = true; cacheLocal(); renderAll();
    status('Guardado para todos · ' + hora(base) + (res.updated_by ? ' · ' + res.updated_by : ''));
  };
  lockForm.addEventListener('submit', function (e) {
    e.preventDefault();
    var k = lockForm.clave.value; who = lockForm.quien.value.trim();
    try { localStorage.setItem(PWHO, who); } catch (er) {}
    lockMsg.textContent = 'Verificando…';
    if (lock.dataset.mode === 'claim') {
      if (k.length < 8) { lockMsg.textContent = 'Mínimo 8 caracteres.'; return; }
      if (k !== lockForm.confirmar.value) { lockMsg.textContent = 'Las dos claves no coinciden.'; return; }
      var local = null; try { local = JSON.parse(localStorage.getItem(KEY)); } catch (er) {}
      var data = local && local.v === 1 ? local : seed();
      rpc('panel_claim', { p_id: R.id, p_key: k, p_data: data, p_by: who || null })
        .then(function (at) { unlocked({ data: data, updated_at: at, updated_by: who }, k); })
        .catch(function (err) { lockMsg.textContent = err.message; });
    } else {
      rpc('panel_load', { p_id: R.id, p_key: k }).then(function (res) { unlocked(res, k); })
        .catch(function (err) { lockMsg.textContent = /clave/i.test(err.message) ? 'Clave incorrecta.' : 'No hay conexión con la base de datos.'; });
    }
  });
  document.querySelector('[data-logout]').onclick = function () {
    try { localStorage.removeItem(PKEY); } catch (e) {}
    key = null; state = null; location.reload();
  };
  var start = function () {
    rpc('panel_status', { p_id: R.id }).then(function (claimed) {
      if (!claimed) return openLock('claim');
      if (!key) return openLock('login');
      return rpc('panel_load', { p_id: R.id, p_key: key }).then(function (res) { unlocked(res, key); })
        .catch(function () { try { localStorage.removeItem(PKEY); } catch (e) {} openLock('login', 'La clave guardada ya no sirve. Ingrésala de nuevo.'); });
    }).catch(function () {
      // sin conexión: muestra la última copia de este navegador, solo lectura de facto
      try { state = JSON.parse(localStorage.getItem(KEY)); } catch (e) {}
      if (!state || state.v !== 1) state = seed();
      norm(state); renderAll(); status('Sin conexión: estás viendo la última copia de este navegador.');
    });
  };

  // ── pestañas ──
  var tabs = document.querySelectorAll('[data-tab]'), panes = document.querySelectorAll('[data-pane]');
  var show = function (name) {
    if (!document.querySelector('[data-pane="' + name + '"]')) name = 'landings';
    tabs.forEach(function (t) { t.classList.toggle('on', t.dataset.tab === name); t.setAttribute('aria-selected', t.dataset.tab === name); });
    panes.forEach(function (p) { p.hidden = p.dataset.pane !== name; });
    document.body.dataset.tab = name;
  };
  tabs.forEach(function (t) { t.onclick = function () { history.replaceState(null, '', '#' + t.dataset.tab); show(t.dataset.tab); }; });
  show(location.hash.slice(1) || 'landings');

  // ══════════════ ESCENARIO FINANCIERO ══════════════
  var fin = document.querySelector('[data-pane="finanzas"]');

  var feeParts = function () {
    var f = state.costeo.fee, k = f.ivaFee ? 1 + IVA : 1;
    return { pct: f.pct / 100 * k, fixed: f.fixed * k };
  };
  var norm = function (st) { if (st && !st.pcts) st.pcts = []; return st; };
  var pctSum = function (b) { return (state.pcts || []).reduce(function (a, r) { return a + (r.base === b ? (+r.pct || 0) : 0); }, 0) / 100; };
  var sum = function (rows) { return rows.reduce(function (a, r) { return a + (+r.amount || 0); }, 0); };

  var calc = function (s) {
    var unitCost = sum(state.costeo.unit), orderCost = sum(state.costeo.order), fee = feeParts();
    var mixT = s.mix.reduce(function (a, b) { return a + (+b || 0); }, 0) || 1;
    var w = s.mix.map(function (m) { return (+m || 0) / mixT; });
    var ticket = 0, upo = 0;
    CFG.planes.forEach(function (p, i) { ticket += w[i] * p.price; upo += w[i] * p.qty; });
    var pauta = s.adsDay * 30, venta = pauta * s.roas;
    var pedidos = ticket ? venta / ticket : 0;
    var neta = state.costeo.iva ? venta / (1 + IVA) : venta;
    var producto = pedidos * upo * unitCost;
    var variables = pedidos * (orderCost + fee.fixed) + venta * fee.pct;
    var fijos = sum(state.fijos);
    var repNeta = neta * pctSum('neta');
    var contrib = neta - producto - variables - repNeta;
    var antes = contrib - pauta - fijos;
    var repUtil = Math.max(0, antes) * pctSum('util');
    var util = antes - repUtil;
    var por = (state.pcts || []).map(function (r) {
      var v = r.base === 'neta' ? neta * (+r.pct || 0) / 100 : Math.max(0, antes) * (+r.pct || 0) / 100;
      return { id: r.id, name: r.name, pct: r.pct, base: r.base, v: v };
    });
    var m = venta ? contrib / venta : 0;
    return {
      ticket: ticket, upo: upo, pauta: pauta, venta: venta, neta: neta, pedidos: pedidos, unidades: pedidos * upo,
      producto: producto, variables: variables, fijos: fijos, contrib: contrib, util: util, repNeta: repNeta, repUtil: repUtil, antes: antes, por: por,
      margen: neta ? util / neta : 0,
      beRoas: m > 0 ? 1 / m : Infinity,
      roasFijos: m > 0 && pauta ? (pauta + fijos) / (m * pauta) : Infinity,
      cpaMax: pedidos ? contrib / pedidos : 0,
      cpa: pedidos ? pauta / pedidos : 0
    };
  };

  var planRow = function (p) {
    var unitCost = sum(state.costeo.unit), orderCost = sum(state.costeo.order), fee = feeParts();
    var neta = state.costeo.iva ? p.price / (1 + IVA) : p.price;
    var prod = p.qty * unitCost, vari = orderCost + fee.fixed + p.price * fee.pct + neta * pctSum('neta');
    var mg = neta - prod - vari;
    return { neta: neta, prod: prod, vari: vari, mg: mg, mgPct: neta ? mg / neta : 0, be: mg > 0 ? p.price / mg : Infinity };
  };

  var costList = function (key, rows, label, unitLabel) {
    var li = rows.map(function (r) {
      return '<div class="cl__row" data-row="' + r.id + '"><input class="in in--name" data-f="name" value="' + esc(r.name) + '" aria-label="Concepto">' +
        '<span class="in-money"><span>$</span><input class="in" data-f="amount" inputmode="numeric" value="' + fmtIn(r.amount) + '" aria-label="Valor"></span>' +
        (r.sup ? '<span class="sup" title="Supuesto: cámbialo por el valor real">Supuesto</span>' : '<span></span>') +
        '<button class="x" data-del aria-label="Quitar">×</button></div>';
    }).join('');
    return '<div class="cl" data-list="' + key + '"><div class="cl__head"><h3>' + label + '</h3><span class="cl__total">' + money(sum(rows)) + '<small>' + unitLabel + '</small></span></div>' +
      li + '<button class="add" data-add>+ Agregar</button></div>';
  };

  var pctList = function () {
    var rows = state.pcts || [];
    var li = rows.map(function (r) {
      return '<div class="cl__row cl__row--pct" data-row="' + r.id + '"><input class="in in--name" data-f="name" value="' + esc(r.name) + '" aria-label="Concepto">' +
        '<span class="in-pct"><input class="in" data-f="pct" inputmode="decimal" value="' + String(r.pct).replace('.', ',') + '" aria-label="Porcentaje"><span>%</span></span>' +
        '<select class="in in--sm" data-f="base" aria-label="Sobre qué se calcula"><option value="util"' + (r.base === 'util' ? ' selected' : '') + '>de la utilidad</option><option value="neta"' + (r.base === 'neta' ? ' selected' : '') + '>de la venta neta</option></select>' +
        (r.sup ? '<span class="sup" title="Supuesto: pon el porcentaje negociado">Supuesto</span>' : '<span></span>') +
        '<button class="x" data-del aria-label="Quitar">×</button></div>';
    }).join('');
    var tn = pctSum('neta') * 100, tu = pctSum('util') * 100, f = function (n) { return n.toFixed(1).replace('.', ',').replace(',0', '') + ' %'; };
    return '<div class="cl" data-list="pcts"><div class="cl__head"><h3>Costos en %</h3><span class="cl__total cl__total--sm">' + f(tn) + '<small>de la venta neta</small> · ' + f(tu) + '<small>de la utilidad</small></span></div>' +
      li + '<button class="add" data-add>+ Agregar</button>' +
      '<p class="note">Sobre la venta neta: se descuenta de cada venta. Sobre la utilidad: se paga solo si el mes deja utilidad, después de producto, variables, pauta y fijos.</p></div>';
  };

  var renderFin = function () {
    var c = state.costeo, f = c.fee;
    var plans = CFG.planes.map(function (p) {
      var r = planRow(p);
      return '<tr><td><b>' + p.name + '</b><small>' + p.qty + ' Bloki</small></td><td>' + money(p.price) + '</td><td>' + money(r.neta) + '</td><td>' + money(r.prod) + '</td><td>' + money(r.vari) +
        '</td><td class="' + (r.mg < 0 ? 'neg' : '') + '"><b>' + money(r.mg) + '</b><small>' + pct(r.mgPct) + '</small></td><td>' + money(Math.max(0, r.mg)) + '</td><td>' + xr(r.be) + '</td></tr>';
    }).join('');

    var R = state.escenarios.map(calc);
    var th = state.escenarios.map(function (s, i) {
      return '<th data-sc="' + s.id + '"><input class="in in--title" data-sf="name" value="' + esc(s.name) + '" aria-label="Nombre del escenario">' +
        '<span class="sc-actions"><button data-dup title="Duplicar">Duplicar</button><button data-sdel title="Borrar">Borrar</button></span></th>';
    }).join('');
    var inputRow = function (label, field, fmt, hint) {
      return '<tr class="sc-in"><td>' + label + (hint ? '<small>' + hint + '</small>' : '') + '</td>' + state.escenarios.map(function (s) {
        return '<td data-sc="' + s.id + '">' + fmt(s) + '</td>';
      }).join('') + '<td></td></tr>';
    };
    var outRow = function (label, key, fmt, cls) {
      return '<tr class="' + (cls || '') + '"><td>' + label + '</td>' + R.map(function (r) {
        var v = r[key];
        return '<td class="' + ((key === 'util' || key === 'margen') && v < 0 ? 'neg' : '') + '">' + fmt(v) + '</td>';
      }).join('') + '<td></td></tr>';
    };
    // fila con desplegable: cuánto le toca a cada participante
    var repRows = function (b, label, key) {
      var people = (state.pcts || []).filter(function (p) { return p.base === b; });
      if (!people.length) return outRow(label, key, money);
      var open = openRep[b];
      var head = '<tr class="rep-head"><td><button class="rep-btn" data-rep="' + b + '" aria-expanded="' + open + '"><span class="rep-car">' + (open ? '▾' : '▸') + '</span>' + label + '</button></td>' +
        R.map(function (r) { return '<td>' + money(r[key]) + '</td>'; }).join('') + '<td></td></tr>';
      if (!open) return head;
      return head + people.map(function (p) {
        return '<tr class="rep-sub"><td>' + esc(p.name) + '<small>' + String(p.pct).replace('.', ',') + ' % ' + (b === 'util' ? 'de la utilidad' : 'de la venta neta') + '</small></td>' +
          R.map(function (r) { var x = r.por.filter(function (q) { return q.id === p.id; })[0]; return '<td>' + money(x ? x.v : 0) + '</td>'; }).join('') + '<td></td></tr>';
      }).join('');
    };
    var bars = R.map(function (r) {
      var tot = r.neta || 1, segs = [['Producto', r.producto], ['Variables', r.variables + r.repNeta], ['Pauta', r.pauta], ['Fijos', r.fijos], ['Participaciones', r.repUtil]];
      var used = segs.reduce(function (a, s) { return a + s[1]; }, 0), u = Math.max(0, r.neta - used);
      var html = segs.concat([['Utilidad', u]]).map(function (s, i) {
        var w = Math.max(0, Math.min(100, s[1] / tot * 100));
        return w > 0 ? '<i class="b' + i + '" style="width:' + w + '%" title="' + s[0] + ' ' + money(s[1]) + '"></i>' : '';
      }).join('');
      return '<td><div class="peso">' + html + '</div>' + (used > r.neta ? '<small class="neg">Los costos pasan la venta</small>' : '') + '</td>';
    }).join('');

    var escala = function () {
      var s = state.escenarios[0]; if (!s) return '';
      var rows = [['Este escenario', 1], ['+50 %', 1.5], ['×2', 2], ['×3', 3]].map(function (k) {
        var r = calc({ adsDay: s.adsDay * k[1], roas: s.roas, mix: s.mix });
        return '<tr><td>' + k[0] + '</td><td>' + money(r.pauta) + '</td><td>' + money(r.venta) + '</td><td>' + int(r.pedidos) + '</td><td class="' + (r.util < 0 ? 'neg' : '') + '"><b>' + money(r.util) + '</b></td></tr>';
      }).join('');
      return rows;
    };

    fin.innerHTML =
      '<section class="pn"><div class="pn__head"><span class="k">1 · Costeo</span><h2>Cuánto cuesta cada Bloki y cada pedido</h2>' +
      '<p>Los valores con la etiqueta <span class="sup">Supuesto</span> son de ejemplo: cámbialos por los reales y la etiqueta desaparece.</p></div>' +
      '<div class="cols">' + costList('unit', c.unit, 'Costo por Bloki', 'por unidad') +
      '<div>' + costList('order', c.order, 'Costo por pedido', 'por pedido') +
      '<div class="fee"><h3>Pasarela de pago</h3><label>% por venta<span class="in-pct"><input class="in" data-fee="pct" inputmode="decimal" value="' + String(f.pct).replace('.', ',') + '"><span>%</span></span></label>' +
      '<label>Fijo por pedido<span class="in-money"><span>$</span><input class="in" data-fee="fixed" inputmode="numeric" value="' + fmtIn(f.fixed) + '"></span></label>' +
      '<label class="chk"><input type="checkbox" data-fee="ivaFee"' + (f.ivaFee ? ' checked' : '') + '> La comisión paga IVA</label></div></div></div>' +
      '<label class="chk chk--wide"><input type="checkbox" data-iva' + (c.iva ? ' checked' : '') + '> Los precios de venta incluyen IVA (19 %): la venta neta es el precio ÷ 1,19</label>' +
      '<div class="tbl"><table class="t"><thead><tr><th>Plan</th><th>Precio</th><th>Venta neta</th><th>Producto</th><th>Variables</th><th>Margen antes de pauta</th><th>CPA máximo</th><th>BE ROAS</th></tr></thead><tbody>' + plans + '</tbody></table></div>' +
      '<p class="note">CPA máximo: lo más que puedes pagar en pauta por un pedido de ese plan sin perder plata (antes de costos fijos). BE ROAS: el ROAS desde el que ese plan deja de perder.</p></section>' +

      '<section class="pn"><div class="pn__head"><span class="k">2 · Fijos y participaciones</span><h2>Lo que se paga cada mes, y lo que se reparte en %</h2></div>' +
      '<div class="cols">' + costList('fijos', state.fijos, 'Costos fijos del mes', 'al mes') + pctList() + '</div></section>' +

      '<section class="pn"><div class="pn__head"><span class="k">3 · Escenarios</span><h2>¿Qué pasa si…?</h2>' +
      '<p>Cambia la pauta por día, el ROAS esperado y cómo se reparten los pedidos entre planes. Todo se recalcula al escribir.</p></div>' +
      '<div class="tbl"><table class="t t--sc"><thead><tr><th></th>' + th + '<th class="add-col"><button class="add" data-addsc>+ Escenario</button></th></tr></thead><tbody>' +
      inputRow('Pauta por día', 'adsDay', function (s) { return '<span class="in-money"><span>$</span><input class="in" data-sf="adsDay" inputmode="numeric" value="' + fmtIn(s.adsDay) + '"></span>'; }) +
      inputRow('ROAS esperado', 'roas', function (s) { return '<span class="in-pct"><input class="in" data-sf="roas" inputmode="decimal" value="' + String(s.roas).replace('.', ',') + '"><span>x</span></span>'; }, 'venta ÷ pauta') +
      inputRow('Pedidos por plan', 'mix', function (s) {
        return '<span class="mix">' + s.mix.map(function (m, i) { return '<label>' + CFG.planes[i].qty + 'u<input class="in" data-mix="' + i + '" inputmode="numeric" value="' + m + '"></label>'; }).join('') + '</span>';
      }, '% de pedidos: 1, 2 y 3 Bloki') +
      outRow('Ticket promedio', 'ticket', money, 'sep') +
      outRow('Pauta del mes', 'pauta', money) +
      outRow('Venta del mes', 'venta', money) +
      outRow('Venta neta (sin IVA)', 'neta', money) +
      outRow('Pedidos', 'pedidos', int) +
      outRow('Bloki vendidos', 'unidades', int) +
      outRow('Costo de producto', 'producto', money) +
      outRow('Envío + pasarela', 'variables', money) +
      repRows('neta', 'Costos en % de la venta neta', 'repNeta') +
      outRow('Costos fijos', 'fijos', money) +
      outRow('Costo por pedido (CPA)', 'cpa', money, 'sep') +
      outRow('CPA máximo', 'cpaMax', money) +
      outRow('BE ROAS', 'beRoas', xr) +
      outRow('ROAS que cubre los fijos', 'roasFijos', xr) +
      outRow('Utilidad antes de participaciones', 'antes', money) +
      repRows('util', 'Participaciones sobre la utilidad', 'repUtil') +
      outRow('Utilidad neta del mes', 'util', money, 'sc-total') +
      outRow('Margen neto', 'margen', pct) +
      '<tr class="sep"><td>A dónde va cada peso<small class="legend"><i class="b0"></i>Producto <i class="b1"></i>Variables <i class="b2"></i>Pauta <i class="b3"></i>Fijos <i class="b4"></i>Participaciones <i class="b5"></i>Utilidad</small></td>' + bars + '<td></td></tr>' +
      '</tbody></table></div>' +
      '<div class="pn__sub"><h3>Si escalas la pauta de «' + esc((state.escenarios[0] || {}).name || '') + '» con el mismo ROAS</h3>' +
      '<div class="tbl"><table class="t"><thead><tr><th></th><th>Pauta del mes</th><th>Venta</th><th>Pedidos</th><th>Utilidad</th></tr></thead><tbody>' + escala() + '</tbody></table></div>' +
      '<p class="note">En la práctica el ROAS suele bajar al escalar. Úsalo como techo, no como promesa.</p></div></section>';
  };

  // edición en vivo sin perder el foco: se recalcula y se restaura el cursor
  var refocus = function (fn, target) {
    var path = null;
    if (target) {
      var row = target.closest('[data-row]'), sc = target.closest('[data-sc]');
      path = { row: row && row.dataset.row, sc: sc && sc.dataset.sc, f: target.dataset.f || target.dataset.sf || target.dataset.fee || (target.dataset.mix != null ? 'mix' + target.dataset.mix : ''), pos: target.selectionStart, len: target.value.length };
    }
    fn();
    if (!path) return;
    var sel = path.row ? '[data-row="' + path.row + '"]' : path.sc ? '[data-sc="' + path.sc + '"]' : '';
    var fsel = path.f.indexOf('mix') === 0 ? '[data-mix="' + path.f.slice(3) + '"]' : '[data-f="' + path.f + '"],[data-sf="' + path.f + '"],[data-fee="' + path.f + '"]';
    var scope = sel ? fin.querySelectorAll(sel) : [fin];
    for (var i = 0; i < scope.length; i++) {
      var el = scope[i].querySelector(fsel);
      if (el) { el.focus(); var p = Math.max(0, path.pos + (el.value.length - path.len)); try { el.setSelectionRange(p, p); } catch (e) {} break; }
    }
  };

  var openRep = { neta: false, util: true };
  var listRows = function (k) { return k === 'fijos' ? state.fijos : k === 'pcts' ? state.pcts : state.costeo[k]; };

  fin.addEventListener('input', function (e) {
    var t = e.target;
    refocus(function () {
      var list = t.closest('[data-list]'), row = t.closest('[data-row]'), sc = t.closest('[data-sc]');
      if (list && row) {
        var rows = listRows(list.dataset.list);
        var r = rows.filter(function (x) { return x.id === row.dataset.row; })[0];
        if (t.dataset.f === 'amount') { r.amount = digits(t.value); r.sup = false; }
        else if (t.dataset.f === 'pct') { r.pct = dec(t.value); r.sup = false; if (/[.,]$/.test(t.value)) { save(); return; } }
        else if (t.dataset.f === 'base') r.base = t.value;
        else r.name = t.value;
      } else if (t.dataset.fee) {
        if (t.dataset.fee === 'pct') state.costeo.fee.pct = dec(t.value);
        if (t.dataset.fee === 'fixed') state.costeo.fee.fixed = digits(t.value);
        if (t.dataset.fee === 'ivaFee') state.costeo.fee.ivaFee = t.checked;
      } else if (t.hasAttribute('data-iva')) {
        state.costeo.iva = t.checked;
      } else if (sc) {
        var s = state.escenarios.filter(function (x) { return x.id === sc.dataset.sc; })[0];
        if (t.dataset.sf === 'name') s.name = t.value;
        if (t.dataset.sf === 'adsDay') s.adsDay = digits(t.value);
        if (t.dataset.sf === 'roas') { s.roas = dec(t.value); if (/[.,]$/.test(t.value)) { save(); return; } }
        if (t.dataset.mix != null) s.mix[+t.dataset.mix] = digits(t.value);
      }
      save(); renderFin();
    }, t.type === 'checkbox' ? null : t);
  });

  fin.addEventListener('click', function (e) {
    var t = e.target, list = t.closest('[data-list]'), rb = t.closest('[data-rep]');
    if (rb) { openRep[rb.dataset.rep] = !openRep[rb.dataset.rep]; renderFin(); return; }
    if (t.hasAttribute('data-add') && list) {
      listRows(list.dataset.list).push(list.dataset.list === 'pcts' ? { id: uid(), name: 'Nueva participación', pct: 0, base: 'util' } : { id: uid(), name: 'Nuevo concepto', amount: 0 });
    } else if (t.hasAttribute('data-del') && list) {
      var id = t.closest('[data-row]').dataset.row;
      var arr = listRows(list.dataset.list); arr.splice(arr.findIndex(function (r) { return r.id === id; }), 1);
    } else if (t.hasAttribute('data-addsc')) {
      state.escenarios.push({ id: uid(), name: 'Nuevo escenario', adsDay: 200000, roas: 2.5, mix: [50, 30, 20] });
    } else if (t.hasAttribute('data-dup')) {
      var src = state.escenarios.filter(function (x) { return x.id === t.closest('[data-sc]').dataset.sc; })[0];
      var copy = JSON.parse(JSON.stringify(src)); copy.id = uid(); copy.name = src.name + ' (copia)';
      state.escenarios.splice(state.escenarios.indexOf(src) + 1, 0, copy);
    } else if (t.hasAttribute('data-sdel')) {
      if (state.escenarios.length === 1) return;
      var sid = t.closest('[data-sc]').dataset.sc;
      state.escenarios = state.escenarios.filter(function (x) { return x.id !== sid; });
    } else return;
    save(); renderFin();
  });

  // ══════════════ PENDIENTES ══════════════
  var pend = document.querySelector('[data-pane="pendientes"]');
  var ST = { todo: 'Por hacer', doing: 'En curso', done: 'Hecho' };
  var PR = { alta: 'Alta', media: 'Media', baja: 'Baja' };
  var filt = { status: 'open', owner: '' };

  var renderPend = function () {
    var owners = state.tareas.map(function (t) { return t.owner; }).filter(function (o, i, a) { return o && a.indexOf(o) === i; }).sort();
    var count = function (s) { return state.tareas.filter(function (t) { return s === 'open' ? t.status !== 'done' : s === 'all' ? true : t.status === s; }).length; };
    var list = state.tareas.filter(function (t) {
      var okS = filt.status === 'all' || (filt.status === 'open' ? t.status !== 'done' : t.status === filt.status);
      return okS && (!filt.owner || t.owner === filt.owner);
    }).sort(function (a, b) {
      if ((a.status === 'done') !== (b.status === 'done')) return a.status === 'done' ? 1 : -1;
      return (a.due || '9999') < (b.due || '9999') ? -1 : (a.due || '9999') > (b.due || '9999') ? 1 : 0;
    });
    var today = hoy();
    var rows = list.map(function (t) {
      var late = t.due && t.due < today && t.status !== 'done';
      return '<div class="task' + (t.status === 'done' ? ' task--done' : '') + '" data-task="' + t.id + '">' +
        '<button class="task__ck" data-toggle aria-label="Marcar como hecha">' + (t.status === 'done' ? '✓' : '') + '</button>' +
        '<input class="in task__title" data-tf="title" value="' + esc(t.title) + '" aria-label="Tarea">' +
        '<input class="in task__owner" data-tf="owner" list="owners" value="' + esc(t.owner) + '" placeholder="Responsable" aria-label="Responsable">' +
        '<input class="in task__due' + (late ? ' late' : '') + '" data-tf="due" type="date" value="' + esc(t.due) + '" aria-label="Fecha">' +
        '<select class="in" data-tf="status" aria-label="Estado">' + Object.keys(ST).map(function (k) { return '<option value="' + k + '"' + (t.status === k ? ' selected' : '') + '>' + ST[k] + '</option>'; }).join('') + '</select>' +
        '<select class="in task__prio prio-' + t.prio + '" data-tf="prio" aria-label="Prioridad">' + Object.keys(PR).map(function (k) { return '<option value="' + k + '"' + (t.prio === k ? ' selected' : '') + '>' + PR[k] + '</option>'; }).join('') + '</select>' +
        '<button class="x" data-tdel aria-label="Borrar tarea">×</button></div>';
    }).join('');
    var chip = function (k, label) { return '<button class="chip-f' + (filt.status === k ? ' on' : '') + '" data-fs="' + k + '">' + label + ' <span>' + count(k) + '</span></button>'; };
    pend.innerHTML =
      '<section class="pn"><div class="pn__head"><span class="k">Pendientes</span><h2>Lo que falta para salir</h2>' +
      '<p>Haz clic en cualquier campo para editarlo. Las tareas vencidas se marcan en rojo.</p></div>' +
      '<form class="task-new" data-new><input class="in" name="title" placeholder="Nueva tarea…" required>' +
      '<input class="in" name="owner" list="owners" placeholder="Responsable" value="Juanfe"><input class="in" name="due" type="date">' +
      '<select class="in" name="prio"><option value="alta">Alta</option><option value="media" selected>Media</option><option value="baja">Baja</option></select>' +
      '<button class="btn-s" type="submit">Agregar</button></form>' +
      '<div class="filters">' + chip('open', 'Abiertas') + chip('todo', 'Por hacer') + chip('doing', 'En curso') + chip('done', 'Hechas') + chip('all', 'Todas') +
      '<select class="in in--sm" data-fo><option value="">Todos los responsables</option>' + owners.map(function (o) { return '<option' + (filt.owner === o ? ' selected' : '') + '>' + esc(o) + '</option>'; }).join('') + '</select></div>' +
      '<div class="tasks">' + (rows || '<p class="empty">No hay tareas con este filtro.</p>') + '</div>' +
      '<datalist id="owners">' + owners.map(function (o) { return '<option value="' + esc(o) + '">'; }).join('') + '</datalist></section>';
  };

  pend.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.target;
    state.tareas.push({ id: uid(), title: f.title.value.trim(), owner: f.owner.value.trim(), due: f.due.value, status: 'todo', prio: f.prio.value });
    save(); renderPend();
    pend.querySelector('[data-new] [name=title]').focus();
  });
  pend.addEventListener('change', function (e) {
    var t = e.target, row = t.closest('[data-task]');
    if (t.hasAttribute('data-fo')) { filt.owner = t.value; renderPend(); return; }
    if (!row || !t.dataset.tf) return;
    var task = state.tareas.filter(function (x) { return x.id === row.dataset.task; })[0];
    task[t.dataset.tf] = t.value.trim ? t.value.trim() : t.value;
    save(); renderPend();
  });
  pend.addEventListener('click', function (e) {
    var t = e.target, row = t.closest('[data-task]');
    if (t.dataset.fs) { filt.status = t.dataset.fs; renderPend(); return; }
    if (!row) return;
    var task = state.tareas.filter(function (x) { return x.id === row.dataset.task; })[0];
    if (t.hasAttribute('data-toggle')) task.status = task.status === 'done' ? 'todo' : 'done';
    else if (t.hasAttribute('data-tdel')) state.tareas = state.tareas.filter(function (x) { return x !== task; });
    else return;
    save(); renderPend();
  });

  // ── exportar / importar ──
  document.querySelector('[data-export]').onclick = function () {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' }));
    a.download = 'bloki-panel-' + hoy() + '.json'; a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  };
  var imp = document.querySelector('[data-import]');
  document.querySelector('[data-import-btn]').onclick = function () { imp.click(); };
  imp.onchange = function () {
    var file = imp.files[0]; if (!file) return;
    var r = new FileReader();
    r.onload = function () {
      try { var s = JSON.parse(r.result); if (s.v !== 1) throw 0; state = norm(s); save(); renderAll(); }
      catch (e) { savedEl.textContent = 'Ese archivo no es un respaldo del panel.'; }
      imp.value = '';
    };
    r.readAsText(file);
  };

  function renderAll() { if (state) { renderFin(); renderPend(); } }
  start();
})();
