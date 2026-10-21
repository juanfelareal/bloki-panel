#!/usr/bin/env python3
"""
Bloki · Landings por avatar con la estructura exacta de Plenara Hydra.

    python3 build.py              # borrador: muestra en rojo lo que falta (reseñas, UGC, valores)
    python3 build.py --publicar   # oculta las secciones que todavía no tienen contenido real

Genera  ./<slug>/index.html  por avatar  +  ./index.html  (tablero con todos).
El contenido compartido vive en BASE; cada avatar (avatares.py) solo sobreescribe lo suyo.
"""
import json, sys, copy, html
from pathlib import Path
from avatares import AVATARES

ROOT = Path(__file__).parent
PUBLICAR = '--publicar' in sys.argv

# ─────────────────────────────────────────────────────────────
# CONFIG de tienda: completar antes de publicar.
# El botón arma un permalink /cart/VARIANTE:CANT (vacía el carrito y va al checkout),
# igual que Plenara (clear → add → /checkout).
# El descuento por cantidad debe existir en Shopify como DESCUENTO AUTOMÁTICO por cantidad
# (2 und = -$19.900, 3 und = -$69.800). Si prefieres código, ponlo en discount_codes.
# ─────────────────────────────────────────────────────────────
CONFIG = {
    'store': '',                 # ej. 'blokipresente.co'
    'unit_price': 89900,
    'variants': {                # color → ID de variante en Shopify
        'Amarillo': '', 'Morado': '', 'Negro': '',
    },
    'discount_codes': {},        # ej. {'2': 'BLOKI2', '3': 'BLOKI3'} si no usas descuento automático
    'popup_code': '[CÓDIGO]',    # código que entrega el popup (crear en Shopify)
    'popup_delay': 12,           # segundos; 0 = solo con el botón flotante
}
COLORS = [('Amarillo', '#F5D76E'), ('Morado', '#C5A8E8'), ('Negro', '#1C1C1C')]

# Planes por cantidad (como Plenara: 1 variante, el descuento es por cantidad).
# 2 unidades $159.900 (aprobado 2026-10-20); 3 unidades es el combo vigente.
PLANES = [
    {'qty': 1, 'price': 89900},
    {'qty': 2, 'price': 159900},
    {'qty': 3, 'price': 199900},
]

def money(n):
    return '$' + f'{n:,.0f}'.replace(',', '.')

# ─────────────────────────────────────────────────────────────
# Íconos de línea (24×24, stroke)
# ─────────────────────────────────────────────────────────────
P = {
    'nfc': '<path d="M6 8.5a6 6 0 0 1 0 7"/><path d="M9.5 6a10 10 0 0 1 0 12"/><path d="M13 3.5a14 14 0 0 1 0 17"/>',
    'battery': '<rect x="3" y="7" width="16" height="10" rx="2"/><path d="M21 11v2"/><path d="M4 20 20 4"/>',
    'app': '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    'android': '<rect x="5" y="9" width="14" height="10" rx="2"/><path d="M8 9a4 4 0 0 1 8 0"/><path d="M7 5l1.5 2M17 5l-1.5 2"/>',
    'palette': '<circle cx="12" cy="12" r="9"/><circle cx="8" cy="10" r="1.2"/><circle cx="12" cy="7.5" r="1.2"/><circle cx="16" cy="10" r="1.2"/><path d="M12 21a2.5 2.5 0 0 1 0-5h2"/>',
    'lock': '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    'hand': '<path d="M8 13V6a1.5 1.5 0 0 1 3 0v6"/><path d="M11 11V4.5a1.5 1.5 0 0 1 3 0V11"/><path d="M14 11V6a1.5 1.5 0 0 1 3 0v7a7 7 0 0 1-7 7h-.5A5.5 5.5 0 0 1 5 16l-1-3a1.5 1.5 0 0 1 2.6-1.4L8 13"/>',
    'chart': '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    'moon': '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M5 19l1.4-1.4M17.6 6.4 19 5"/>',
    'kid': '<circle cx="12" cy="6" r="3"/><path d="M6 21v-5a6 6 0 0 1 12 0v5"/>',
    'users': '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20a6 6 0 0 1 12 0M15 20a4.5 4.5 0 0 1 7-3.7"/>',
    'heart': '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z"/>',
    'brief': '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    'book': '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2Z"/><path d="M4 19V5M19 19v2H6"/>',
    'gift': '<rect x="3" y="9" width="18" height="12" rx="1.5"/><path d="M3 13h18M12 9v12"/><path d="M12 9S10.5 4 8 4.5 7.5 9 12 9Zm0 0s1.5-5 4-4.5S16.5 9 12 9Z"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'loop': '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>',
    'trophy': '<path d="M8 4h8v5a4 4 0 0 1-8 0Z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 21h8M9 17h6"/>',
    'eye': '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    'bed': '<path d="M3 18V7M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5"/><circle cx="7" cy="11" r="1.6"/>',
    'fork': '<path d="M7 3v8a2 2 0 0 0 2 2v8M5 3v5M9 3v5M17 3c-2 0-3 3-3 6s1 4 3 4v8"/>',
    'car': '<path d="M5 16V11l2-5h10l2 5v5"/><path d="M3 16h18v3H3zM7 19v2M17 19v2"/>',
    'shield': '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6Z"/><path d="m9 12 2 2 4-4"/>',
    'spark': '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    'plane': '<path d="M10 14 3 11l1.5-1.5L11 11l5-6a1.5 1.5 0 0 1 2 2l-6 5 1.5 6.5L12 20l-3-7"/>',
    'cart': '<path d="M3 4h2l2.5 11h10.5l2-8H6.5"/><circle cx="9" cy="19" r="1.5"/><circle cx="17" cy="19" r="1.5"/>',
    'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
}
def icon(name, sw=1.6):
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{P.get(name, P["spark"])}</svg>'

# ─────────────────────────────────────────────────────────────
# BASE: contenido compartido por todas las landings (voz de MARCA:
# plana, sin emojis, sin frases prohibidas, nombrar la escena).
# ─────────────────────────────────────────────────────────────
MODOS = {
    'trabajo':  {'name': 'Trabajo', 'apps': 6, 'color': 'yellow', 'role': 'La jornada',
                 'bullets': ['Redes y video bloqueados en horario laboral', 'Correo, Drive y el chat del trabajo quedan libres', 'Lo terminas tú, no una notificación'],
                 'scene': 'La tarea era de veinte minutos. El "ya miro una cosa" la volvió de dos horas.'},
    'lectura':  {'name': 'Lectura', 'apps': 4, 'color': 'mint', 'role': 'La página 38',
                 'bullets': ['Bloquea lo que interrumpe una página', 'Deja libre el lector de libros', 'Para leer más de dos párrafos seguidos'],
                 'scene': 'Llevas cuatro meses en la página 38.'},
    'romantico':{'name': 'Romántico', 'apps': 8, 'color': 'coral', 'role': 'La mesa',
                 'bullets': ['Para la comida, la cama o el plan del sábado', 'Llamadas y WhatsApp siguen entrando', 'Lo pueden activar los dos con el mismo Bloki'],
                 'scene': 'Revisar el celular en la mesa no significa nada. Hasta que la otra persona lo cuenta.'},
    'viajes':   {'name': 'Viajes', 'apps': 5, 'color': 'orange', 'role': 'El paseo',
                 'bullets': ['Maps, cámara y reservas libres', 'Redes bloqueadas mientras estás allá', 'Las fotos se suben cuando vuelvas'],
                 'scene': 'Viniste hasta acá para verlo por la pantalla.'},
    'dormir':   {'name': 'Dormir', 'apps': 9, 'color': 'lilac', 'role': 'La última hora',
                 'bullets': ['Bloquea lo que te tiene despierto a la 1', 'Alarma y llamadas siguen funcionando', 'Bloki se queda fuera del cuarto'],
                 'scene': 'Dijiste "el último" a las 11:40.'},
    'estudio':  {'name': 'Estudio', 'apps': 7, 'color': 'yellow', 'role': 'El parcial',
                 'bullets': ['Bloquea redes, juegos y video', 'Deja libres calculadora, apuntes y la plataforma de clase', 'Compite con tus amigos por horas bloqueadas'],
                 'scene': 'Cuatro horas sentado. Cuarenta minutos estudiando.'},
    'conducir': {'name': 'Conducir', 'apps': 3, 'color': 'mint', 'role': 'El semáforo',
                 'bullets': ['Bloquea chats y redes mientras manejas', 'Maps y música quedan libres', 'Bloki puede vivir en el carro'],
                 'scene': 'Lo leíste en un semáforo. Después en movimiento.'},
    'parental': {'name': 'Control parental', 'apps': 10, 'color': 'coral', 'role': 'La media hora',
                 'bullets': ['El modo más estricto: 10 apps bloqueadas', 'Lo activas tú y Bloki se queda contigo', 'Llamadas a la familia siempre libres'],
                 'scene': 'Le dijiste media hora. Van dos.'},
}

BASE = {
    'announce': 'Combo x3 con <b>$69.800</b> de ahorro',
    'accent': 'yellow',
    'hero_img': 'bloki-frente.png',
    'gift': {'title': '8 playlists, una para cada modo', 'sub': 'Trabajo, Lectura, Dormir… cada modo con su música. Bloqueas, le das play y a lo tuyo', 'value': ''},
    'micro': ['App incluida, sin suscripción', 'Envío a toda Colombia'],
    'chips': [
        ('nfc', 'NFC SIN BATERÍA', 'yellow'),
        ('app', 'APP SIN SUSCRIPCIÓN', 'mint'),
        ('android', 'IPHONE Y ANDROID', 'lilac'),
        ('palette', '3 COLORES', 'coral'),
    ],
    'voices_eyebrow': 'Lo que cuenta la gente',
    'voices_note': 'Comentarios públicos en Reddit sobre intentar usar menos el celular, traducidos. No son clientes de Bloki.',
    'buy': {
        'pill': 'Diseñado y fabricado en Colombia',
        'sub': 'Tu compañero físico que bloquea las apps que eliges.',
        'lead': 'Lo acercas al celular y las apps dejan de abrir. Para que vuelvan, tienes que <b>volver a él</b>.',
        'checks': [
            '<b>Bloqueas con un toque.</b> Sin contraseña ni código.',
            '<b>Para desbloquear tienes que pararte.</b> Las apps solo vuelven cuando acercas el celular a Bloki.',
            '<b>Racha, intentos frenados y retos</b> con amigos en la app.',
        ],
        'ship': 'Llega en 2 a 5 días hábiles · Envío a toda Colombia',
        'cta': 'Comprar ahora →',
        'trust': ['Envío a toda Colombia', 'Garantía 60 días', 'Pago seguro'],
        'pay': ['PSE', 'Nequi', 'Bancolombia', 'VISA', 'Mastercard'],
    },
    'plans': [
        {'name': '1 Bloki', 'desc': 'Para ti.', 'badge': ''},
        {'name': '2 Bloki', 'desc': 'Uno en la casa y otro en la oficina, o para el reto 1 vs 1.', 'badge': 'RECOMENDADO'},
        {'name': 'Combo x3', 'desc': 'Tres colores. Para la casa, para regalar o para armar el reto.', 'badge': 'MEJOR PRECIO', 'badge_y': True},
    ],
    'default_plan': 2,
    'why': {
        'eyebrow': 'Por qué sí funciona',
        'title': 'Por qué el límite de pantalla te duró una semana',
        'text': 'El límite de pantalla tiene un botón que dice "Ignorar límite", y está en el mismo celular. Las apps borradas se vuelven a bajar en cuarenta segundos. Con Bloki, <b>para desbloquear tienes que levantarte e ir hasta donde lo dejaste.</b>',
    },
    'guarantee': {'title': 'Garantía de 60 días', 'text': 'Si no cambia tu vida, <b>te devolvemos el dinero.</b> Sin preguntas.'},
    'details': [
        ('Qué es', '<p>Un compañero físico con un chip NFC adentro, más una app. No tiene batería y no se carga. Se compra una vez.</p>', True),
        ('Qué trae la caja', '<p><b>1 Bloki</b>, en el color que elegiste.</p><p><b>Instrucciones de uso.</b> De la caja a tu primer bloqueo en un par de minutos.</p><p><b>Tu bienvenida a la comunidad Bloki.</b> Retos, ranking y gente bloqueando contigo.</p>', False),
        ('Cómo se usa', '<p>Abres la app y eliges qué apps se bloquean. Acercas la parte de arriba del celular a Bloki y el modo se activa. Para desbloquear, vuelves a acercarlo.</p>', False),
        ('Compatibilidad', '<p>iPhone y Android con NFC. La mayoría de celulares desde 2015 lo tienen. Cada Bloki se vincula a un solo celular: si son dos, cada uno necesita el suyo.</p>', False),
        ('Envíos, cambios y garantía', '<p>Envío a toda Colombia, de 2 a 5 días hábiles.</p><p><b>60 días de garantía:</b> lo devuelves y te devolvemos el dinero, sin preguntas.</p>', False),
    ],
    'modes_title': 'Ocho modos. <em>Ocho escenas.</em>',
    'modes_sub': 'Cada uno trae sus apps ya elegidas. Los ajustas cuando quieras. Desliza para verlos.',
    'modes_datum': 'NFC · 0 baterías · 8 modos · 1 toque',
    'modes_order': ['trabajo', 'dormir', 'romantico', 'estudio', 'lectura', 'parental', 'viajes', 'conducir'],
    'cmp_title': '¿Por qué un compañero físico y no otra app?',
    'cmp_cols': ['Bloki', 'Límite de pantalla', 'Apps de bloqueo'],
    'cmp_rows': [
        ('El bloqueo no se quita desde el celular', 'si', 'no', 'no'),
        ('No se apaga con "Ignorar límite"', 'si', 'no', 'Algunas'),
        ('Se paga una vez, sin mensualidad', 'si', 'si', 'Casi nunca'),
        ('Cuenta los intentos frenados', 'si', 'no', 'Algunas'),
        ('Retos y ranking con amigos', 'si', 'no', 'no'),
        ('Lo ves sobre la mesa', 'si', 'no', 'no'),
    ],
    'cmp_note': 'El límite de pantalla es gratis y ya viene en tu celular. Si te funciona, no necesitas Bloki.',
    'faq': [
        ('¿No es solo un chip NFC caro?', '<p>Adentro tiene un chip NFC, sí. Lo que pagas es el compañero físico, la app completa de por vida sin mensualidad, los ocho modos, los retos y el ranking. Y es un compañero que da gusto dejar a la vista: el que se guarda en un cajón no se usa.</p>'),
        ('¿La app se paga aparte?', '<p>No. Va incluida, de por vida, sin suscripción ni cobros después.</p>'),
        ('¿Puedo saltarme el bloqueo?', '<p>Si de verdad quieres, sí. Hay modo estricto, pero ningún bloqueo de software es una cárcel. Lo que hace Bloki es que volver cueste más que quedarte afuera, y que si terminas antes, ese día no sume para tu racha.</p>'),
        ('¿Qué pasa con las llamadas y WhatsApp?', '<p>Las llamadas nunca se bloquean: ni Apple ni Google lo permiten. WhatsApp queda libre por defecto. Si lo agregas, la app te avisa antes.</p>'),
        ('¿Qué pasa si se me pierde?', '<p>Cada Bloki trae <b>3 desbloqueos de emergencia</b>. Respondes tu pregunta de seguridad y tus apps se desbloquean. Si necesitas más, los encuentras dentro de la app.</p>'),
    ],
    'faq_cases_title': '¿Me sirve en mi caso?',
    'popup': {'title': 'Tienes un descuento esperando', 'text': 'Déjanos tu correo y te mandamos el código para tu primer Bloki.', 'cta': 'Quiero el código', 'no': 'Ahora no'},
    'sticky_label': 'Quiero mi Bloki',
}

# ─────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────
def todo_tag(txt):
    return '' if PUBLICAR else f'<span class="todo-tag">PENDIENTE · {txt}</span>'

def carousel(items_html, cls=''):
    return (f'<div class="carousel {cls}"><div class="track">{items_html}</div>'
            '<div class="c-nav"><button type="button" data-prev aria-label="Anterior">‹</button>'
            '<span class="c-dots"></span><button type="button" data-next aria-label="Siguiente">›</button></div></div>')

def cta(label='Pedir ahora →'):
    return f'<a class="btn btn--block" href="#comprar" data-goto-buy>{label}</a>'

def s_announce(a):
    return f'<div class="announce"><b class="tag">OFERTA</b>{a["announce"]}</div>'

def s_header(a):
    return f'''<header class="header"><div class="header__in">
  <details class="menu"><summary aria-label="Menú">{icon("menu")}</summary>
    <nav class="menu__panel"><a href="#comprar" data-goto-buy>Comprar</a><a href="#como-funciona">Cómo funciona</a><a href="#preguntas">Preguntas</a></nav></details>
  <a class="header__logo" href="#top"><img src="../assets/bloki-wordmark.png" alt="Bloki" width="64" height="26"></a>
  <a class="header__cart" href="#comprar" data-goto-buy aria-label="Comprar">{icon("cart")}</a>
</div></header>'''

def s_hero(a):
    g = a['gift']
    badge = f'Gratis · {g["value"]}' if g.get('value') else 'Gratis'
    pills = ''.join(f'<li>{icon(i, 1.3)}<span>{t}</span></li>' for i, t in a['hero_pills'])
    micro = ''.join(f'<li>{m}</li>' for m in a['micro'])
    return f'''<section class="hero" id="top">
  <div class="hero__media">
    <img class="hero__toy" src="../assets/{a["hero_img"]}" alt="Bloki, tu compañero físico que bloquea las apps que eliges" width="420" height="420">
    <div class="gift"><span class="gift__badge">{badge}</span><span class="gift__txt"><b>{g["title"]}</b>{g["sub"]}. Incluida con tu pedido.</span></div>
  </div>
  <div class="wrap hero__copy">
    <h1>{a["h1"]}</h1>
    <p class="hero__sub">{a["hero_sub"]}</p>
    <ul class="hero__pills">{pills}</ul>
    {cta()}
    <ul class="micro">{micro}</ul>
  </div>
</section>'''

def s_voices(a):
    cards = ''.join(f'<article class="voice"><p class="voice__q">"{q}"</p><p class="voice__src"><b>{who}</b> · <a href="{url}" target="_blank" rel="noopener">fuente</a></p></article>'
                    for q, who, url in a['voices'])
    return f'''<section class="sec"><div class="wrap">
  <div class="center"><span class="eyebrow">{a["voices_eyebrow"]}</span>
  <h2 class="h2">{a["voices_title"]}</h2>
  <p class="small" style="margin:0 0 18px">{a["voices_note"]}</p></div>
  {carousel(cards)}
  <div style="margin-top:20px">{cta()}</div>
</div></section>'''

def info_slide(s):
    if s['type'] == 'steps':
        li = ''.join(f'<li><b>{t}</b>{d}</li>' for t, d in s['items'])
        return f'<div class="info"><span class="info__k">{s["k"]}</span><p class="info__t">{s["t"]}</p><ol>{li}</ol></div>'
    if s['type'] == 'data':
        li = ''.join(f'<li><b>{t}</b>{d}</li>' for t, d in s['items'])
        return (f'<div class="info info--ink"><span class="info__k">{s["k"]}</span><span class="info__big">{s["big"]}</span>'
                f'<p class="info__t" style="margin-top:6px">{s["t"]}</p><ul style="color:var(--ink)">{li}</ul>'
                f'<p style="font-size:9.5px;color:var(--ink-muted);margin:10px 0 0">Fuente: {s["src"]}</p></div>')
    if s['type'] == 'vs':
        li = ''.join(f'<li><b>{t}</b>{d}</li>' for t, d in s['items'])
        return f'<div class="info" style="background:var(--paper)"><span class="info__k">{s["k"]}</span><p class="info__t">{s["t"]}</p><ul>{li}</ul></div>'
    return ''

def s_gallery(a):
    chips = ''.join(f'<div class="chip">{icon(i, 1.3)}<span>{t}</span></div>' for i, t, c in a['chips'])
    slides, thumbs = '', ''
    for k, s in enumerate(a['gallery']):
        on = ' on' if k == 0 else ''
        if 'img' in s:
            cover = ' gal__slide--cover' if s.get('cover') else ''
            bg = ''
            slides += f'<div class="gal__slide{cover}{on}"{bg}><img src="../assets/{s["img"]}" alt="{s.get("alt", "Bloki")}"{"" if k == 0 else " loading=\"lazy\""}></div>'
            thumbs += f'<button type="button" class="{on.strip()}" aria-label="Imagen {k+1}"><img src="../assets/{s["img"]}" alt=""></button>'
        else:
            slides += f'<div class="gal__slide{on}">{info_slide(s)}</div>'
            thumbs += f'<button type="button" class="{on.strip()}" aria-label="Imagen {k+1}"><span class="t-info">{s["thumb"]}</span></button>'
    return f'''<section class="sec sec--tight" id="top"><div class="wrap">
  <div class="gal"><div class="chips">{chips}</div>
    <div><div class="gal__main">{slides}<div class="gal__arrows"><button type="button" data-gal-prev aria-label="Anterior">‹</button><button type="button" data-gal-next aria-label="Siguiente">›</button></div></div>
    <div class="thumbs">{thumbs}</div></div></div>
</div></section>'''

def s_buy(a):
    b = a['buy']
    checks = ''.join(f'<li><span class="ck"></span><span>{c}</span></li>' for c in b['checks'])
    checks += f'<li><span class="ck ck--gift"></span><span><b>Gratis: {a["gift"]["title"]}.</b> {a["gift"]["sub"]}.</span></li>'
    plans = ''
    for k, (pl, base) in enumerate(zip(a['plans'], PLANES)):
        qty, price = base['qty'], base['price']
        full = CONFIG['unit_price'] * qty
        on = (k + 1) == a['default_plan']
        badge = ''
        if pl.get('badge'):
            badge = f'<span class="plan__badge{" plan__badge--y" if pl.get("badge_y") else ""}">{pl["badge"]}</span>'
        save = f'<span class="plan__save">AHORRA {money(full - price)}</span>' if full > price else ''
        strike = f'<s>{money(full)}</s>' if full > price else ''
        tier = {1: 'Individual', 2: 'Dúo', 3: 'Combo'}[qty]
        rows = ''
        for u in range(qty):
            name, _ = COLORS[(u + a.get('color_start', 0)) % len(COLORS)]
            sw = ''.join(f'<button type="button" class="{"on" if n == name else ""}" style="--c:{h}" data-color="{n}" aria-label="{n}"></button>' for n, h in COLORS)
            label = f'Bloki {u+1}' if qty > 1 else 'Color'
            rows += f'<div class="colors__row"><span>{label}: <b>{name}</b></span><span class="sw">{sw}</span></div>'
        note = '' if PUBLICAR or not base.get('todo') else f'<span class="todo-tag" style="margin:8px 0 0 30px">{base["todo"]}</span>'
        plans += f'''<div class="plan{" on" if on else ""}" role="radio" tabindex="0" aria-checked="{str(on).lower()}" data-qty="{qty}" data-price="{price}">{badge}
      <div class="plan__row"><span class="plan__dot"></span>
        <div><p class="plan__name"><b>{tier}</b> · {qty} Bloki</p>
        <p class="plan__desc">{money(price / qty)} c/u{save}</p></div>
        <p class="plan__price"><strong>{money(price)}</strong>{strike}</p></div>
      <div class="colors">{rows}</div>{note}</div>'''
    trust = ''.join(f'<li>{t}</li>' for t in b['trust'])
    pay = ''.join(f'<img class="pay--{p.lower()}" src="../assets/pagos/{p.lower()}.svg" alt="{p}" loading="lazy">' for p in b['pay'])
    rating = '<span class="launch">Precio de lanzamiento por tiempo limitado</span>'
    return f'''<section class="sec buy" id="comprar"><div class="wrap">
  <div class="buy__card">
    <div class="buy__top"><span>{rating}</span><span class="pill"><svg class="flag" viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="1" fill="#FCD116"/><rect y="1" width="3" height=".5" fill="#003893"/><rect y="1.5" width="3" height=".5" fill="#CE1126"/></svg>{b["pill"]}</span></div>
    <h1 class="buy__title">Bloki</h1>
    <p class="buy__sub">{b["sub"]}</p>
    <p class="buy__lead">{b["lead"]}</p>
    <div class="guar-bar"><span class="guar__seal">60<small>DÍAS</small></span><p><b>{a["guarantee"]["title"]}.</b> {a["guarantee"]["text"]}</p></div>
    <ul class="checks">{checks}</ul>
    <p class="ship"><i></i><span data-eta>{b["ship"]}</span></p>
    <div class="plans" role="radiogroup" aria-label="Elige tu plan">{plans}</div>
    <div class="total"><span>Total</span><span><strong data-total></strong><s data-compare hidden></s><span class="save" data-save hidden></span></span></div>
    <button type="button" class="btn btn--block" data-buy>{b["cta"]}</button>
    <p class="buy__err" role="alert"></p>
    <div class="tip"><button type="button" class="tip__btn" aria-describedby="tip-perdida">¿Y si se me pierde? <span class="tip__i" aria-hidden="true">i</span></button>
      <span class="tip__box" role="tooltip" id="tip-perdida">Cada Bloki trae <b>3 desbloqueos de emergencia</b>. Respondes tu pregunta de seguridad y tus apps se desbloquean. Si necesitas más, los encuentras dentro de la app.</span></div>
    <ul class="micro">{trust}</ul>
    <div class="pay">{pay}</div>
  </div>
</div></section>'''

def s_why(a):
    w, g = a['why'], a['guarantee']
    return f'''<section class="sec sec--tight"><div class="wrap why">
  <div class="why__card"><span class="why__tag">{w["eyebrow"]}</span><h3>{w["title"]}</h3><p>{w["text"]}</p></div>
  <div class="why__card why__guar"><span class="why__icon">{icon("shield", 1.5)}</span><div><h4>{g["title"]}</h4><p>{g["text"]}</p></div></div>
</div></section>'''

def acc(items, first_open=True):
    out = ''
    for i, it in enumerate(items):
        t, body = it[0], it[1]
        op = it[2] if len(it) > 2 else (first_open and i == 0)
        out += f'<details{" open" if op else ""}><summary>{t}</summary><div class="acc__body">{body}</div></details>'
    return f'<div class="acc">{out}</div>'

def s_mega(a):
    details = acc(a['details'])
    lines = ''.join(f'<span>{l}</span>' for l in a['pain_lines'])
    pains = ''.join(f'<div class="pain"><span class="pain__ic">{icon(i, 1.3)}</span><h3>{t}</h3><p>{d}</p></div>' for i, t, d in a['pains'])
    res = ''.join(f'<li><span class="list__ic">{icon(i, 1.3)}</span><div><h3>{t}</h3><p>{d}</p></div></li>' for i, t, d in a['results'])
    return f'''<section class="sec sec--tight" id="como-funciona"><div class="wrap">{details}</div></section>
<section class="sec sec--deep"><div class="wrap">
  <div class="split"><div class="split__copy"><span class="eyebrow">¿Te suena familiar?</span>
  <h2 class="h2 h2--lines">{lines}</h2>
  <p class="lead">{a["pain_text"]}</p>
  <div class="pains">{pains}</div></div>
  <figure class="figure"><img src="../assets/{a.get("pain_img", "bloki-morado-app.jpg")}" alt="Bloki morado junto al celular con la app abierta" loading="lazy"></figure></div>
</div></section>'''

def s_modes(a):
    cards = ''
    for key in a['modes_order']:
        m = MODOS[key]
        li = ''.join(f'<li>{b}</li>' for b in m['bullets'])
        cards += f'''<article class="mode"><div class="mode__top"><span class="mode__dose">{m["apps"]} apps bloqueadas</span><img src="../assets/bloki-render.png" alt="" loading="lazy"></div>
      <div class="mode__body"><span class="mode__role">{m["role"]}</span><h3 class="mode__name">{m["name"]}</h3><ul>{li}</ul><p>{m["scene"]}</p></div></article>'''
    return f'''<section class="sec sec--deep"><div class="wrap">
  <span class="eyebrow">Los modos</span>
  <h2 class="h2">{a["modes_title"]}</h2>
  <p class="lead">{a["modes_sub"]}</p>
  <span class="datum">{a["modes_datum"]}</span>
  {carousel(cards)}
  <p class="small" style="margin:14px 0 0">Las llamadas nunca se bloquean. WhatsApp queda libre por defecto en todos los modos.</p>
</div></section>'''

def s_timeline(a):
    li = ''
    for k, (when, t, d, tags, hl) in enumerate(a['timeline']):
        tg = ''.join(f'<span>{x}</span>' for x in tags)
        li += f'''<li class="{"hl" if hl else ""}"><span class="tl__n">{k+1}</span><div class="tl__card"><span class="tl__when">{when}</span><h3>{t}</h3><p>{d}</p>
      <div class="tl__who">LO QUE TRABAJA AQUÍ</div><div class="tags">{tg}</div></div></li>'''
    return f'''<section class="sec"><div class="wrap">
  <span class="eyebrow">Las primeras semanas</span>
  <h2 class="h2">{a["timeline_title"]}</h2>
  <p class="lead">{a["timeline_sub"]}</p>
  <ol class="tl">{li}</ol>
  <p class="bridge">{a["bridge"]}</p>
</div></section>'''

def s_ugc(a):
    if PUBLICAR and not a.get('ugc_real'):
        return ''
    cards = ''
    for who, brief, tags in a['ugc']:
        tg = ''.join(f'<span>{t}</span>' for t in tags)
        cards += f'''<article class="ugc todo"><div class="ugc__ph"><div><b>FOTO REAL DEL CLIENTE</b>{brief}</div></div>
      <div class="ugc__body"><p class="ugc__q">[Testimonio real, con permiso del cliente]</p><div class="ugc__who">{who}</div><div class="tags">{tg}</div></div></article>'''
    return f'''<section class="sec sec--deep"><div class="wrap">
  <div class="center">{todo_tag("testimonios con foto")}<h2 class="h2">{a["ugc_title"]}</h2>
  <p class="small" style="margin:0 0 18px">Cada tarjeta dice a quién buscar y qué objeción tiene que tumbar.</p></div>
  {carousel(cards)}
  <div style="margin-top:20px">{cta()}</div>
</div></section>'''

def s_compare(a):
    def cell(v, us=False):
        cls = ' class="us"' if us else ''
        if v == 'si': return f'<td{cls}><span class="yes">✓</span></td>'
        if v == 'no': return f'<td{cls}><span class="no">✕</span></td>'
        return f'<td{cls}><span class="txt">{v}</span></td>'
    head = f'<tr><th></th><th class="us"><img src="../assets/bloki-lila-tejido.jpg" alt="">{a["cmp_cols"][0]}</th><th>{a["cmp_cols"][1]}</th><th>{a["cmp_cols"][2]}</th></tr>'
    rows = ''.join(f'<tr><td>{r[0]}</td>{cell(r[1], True)}{cell(r[2])}{cell(r[3])}</tr>' for r in a['cmp_rows'])
    return f'''<section class="sec"><div class="wrap">
  <span class="eyebrow">Por qué Bloki</span>
  <h2 class="h2">{a["cmp_title"]}</h2>
  <table class="cmp">{head}{rows}</table>
  <p class="small" style="margin:14px 0 0">{a["cmp_note"]}</p>
</div></section>'''

def s_faq(a):
    return f'''<section class="sec sec--deep" id="preguntas"><div class="wrap">
  <div class="faq"><div class="faq__head"><span class="eyebrow">Preguntas</span>
  <h2 class="h2">Lo que más nos preguntan</h2></div>
  <div class="faq__list">{acc([q for q in a["faq"] if q[0].startswith("¿Qué pasa si se me pierde")] + a["faq_cases"] + [q for q in a["faq"] if not q[0].startswith("¿Qué pasa si se me pierde")], first_open=False)}</div></div>
</div></section>'''

def s_reviews(a):
    if PUBLICAR:
        return ''
    return f'''<section class="sec"><div class="wrap">
  <div class="card todo">{todo_tag("widget de reseñas")}
    <div class="rev-head"><h3 style="margin:0">Reseñas de clientes</h3><span class="pill">Escribir una reseña</span></div>
    <p>Aquí va el widget de reseñas (Judge.me) cuando haya compras reales. Plenara muestra reseñas largas, algunas de 4 estrellas, y varias recomiendan llevar más de una unidad. En Bloki, pedirlas por correo a los 14 días de la entrega.</p>
  </div>
</div></section>'''

def s_sticky(a):
    return f'''<div class="sticky" aria-hidden="true"><div class="sticky__in">
  <img src="../assets/bloki-lila-tejido.jpg" alt="">
  <span class="sticky__info"><strong>Bloki</strong>Desde <b>{money(PLANES[0]["price"])}</b></span>
  <a class="btn" href="#comprar" data-goto-buy tabindex="-1">{a["sticky_label"]}</a>
</div></div>'''

def s_popup(a):
    p = a['popup']
    return f'''<button class="teaser" type="button" aria-label="Ver descuento">{icon("gift", 1.8)}</button>
<div class="pop" role="dialog" aria-modal="true" aria-label="Descuento"><div class="pop__box">
  <button class="pop__x" type="button" data-pop-close aria-label="Cerrar">×</button>
  <div class="pop__art"><img src="../assets/bloki-amarillo-mano.jpg" alt=""></div>
  <div class="pop__body"><h3>{p["title"]}</h3><p>{p["text"]}</p>
    <form><input type="email" required placeholder="Tu correo" aria-label="Correo"><button class="btn btn--block" type="submit">{p["cta"]}</button></form>
    <button class="pop__no" type="button" data-pop-close>{p["no"]}</button>
    <p class="pop__legal">Al dejar tu correo aceptas recibir mensajes de Bloki. Puedes salirte cuando quieras.</p></div>
</div></div>'''

def render(slug, a):
    accent = a['accent']
    cfg = {'slug': slug, 'store': CONFIG['store'], 'unitPrice': CONFIG['unit_price'], 'variants': CONFIG['variants'],
           'discountCodes': CONFIG['discount_codes'], 'popupCode': CONFIG['popup_code'], 'popupDelay': CONFIG['popup_delay']}
    draft = '' if PUBLICAR else f'<div class="draft-bar">BORRADOR · {a["avatar"]} · <a href="../index.html">todos</a></div>'
    body = ''.join([s_announce(a), s_header(a), '<div class="pdp">', s_gallery(a), s_buy(a), '</div>', s_why(a),
                    s_mega(a), s_compare(a), s_faq(a)])
    desc = html.escape(a['meta_desc'])
    return f'''<!doctype html>
<html lang="es-CO"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bloki · {html.escape(a["title_tag"])}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="Bloki · {html.escape(a["title_tag"])}"><meta property="og:description" content="{desc}">
<meta property="og:image" content="../assets/bloki-lila-tejido.jpg">
{'' if PUBLICAR else '<meta name="robots" content="noindex">'}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Mono:wght@400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/bloki-landing.css">
<style>.todo-inline{{color:#c2412d}}</style>
</head><body>
{draft}
{body}
<footer style="padding:30px 16px 110px;text-align:center;font-size:11px;color:var(--ink-muted)">Bloki · Hecho en Colombia</footer>
{s_sticky(a)}
{s_popup(a)}
<script type="application/json" id="bk-config">{json.dumps(cfg, ensure_ascii=False)}</script>
<script src="../assets/bloki-landing.js"></script>
</body></html>'''

def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out

# Base de datos del panel (Supabase, proyecto "bloki"). La llave publicable es pública por diseño:
# la tabla no se puede leer ni escribir directo, solo con las funciones que piden la clave del panel.
PANEL_REMOTE = {'url': 'https://mxkkhkafwbictkeytmti.supabase.co', 'key': 'sb_publishable_N4VPC8DmQgmT3Xp1vHy7qA_bxDQuZXf', 'id': 'bloki'}

# Tareas con las que arranca la pestaña Pendientes (después se editan en el navegador).
# (tarea, responsable, fecha AAAA-MM-DD, estado todo|doing|done, prioridad alta|media|baja)
TAREAS_INICIALES = [
    ('Confirmar si un mismo celular puede vincularse a varios Bloki (lo afirma la landing de trabajo)', 'Juanfe', '', 'todo', 'alta'),
    ('Reemplazar los costos supuestos del escenario financiero por los reales', 'Juanfe', '', 'todo', 'alta'),
    ('Crear en Shopify el descuento automático por cantidad (2 = −$19.900, 3 = −$69.800)', 'Juanfe', '', 'todo', 'alta'),
    ('Llenar CONFIG en build.py: tienda e ID de variante de Amarillo, Morado y Negro', 'Juanfe', '', 'todo', 'alta'),
    ('Definir el % del código del reto de 21 días', 'Juanfe', '', 'todo', 'media'),
    ('Validar con la app el mensaje de voz al primer toque (landing de regalo)', 'Juanfe', '', 'todo', 'media'),
    ('Armar las 8 playlists por modo y las de 50 minutos en Spotify', 'Juanfe', '', 'todo', 'media'),
    ('Grabar los 7 audios para dormir', 'Juanfe', '', 'todo', 'media'),
    ('Cargar en la app los 30 retos de familia y las 52 preguntas para la mesa', 'Juanfe', '', 'todo', 'media'),
    ('Medidas y material del Bloki para la ficha', 'Juanfe', '', 'todo', 'media'),
    ('Confirmar: control parental en tablets, ranking sin Bloki, descuento a estudiantes, fecha límite de Navidad, nota de regalo', 'Juanfe', '', 'todo', 'media'),
    ('Decidir si hay pago contra entrega', 'Juanfe', '', 'todo', 'media'),
    ('Conectar el popup a Klaviyo y crear el código de descuento', 'Juanfe', '', 'todo', 'media'),
    ('Conseguir testimonios y reseñas reales con foto', 'Juanfe', '', 'todo', 'media'),
    ('Foto del Bloki morado con la pantalla real de la app', 'Juanfe', '', 'todo', 'baja'),
    ('Logo oficial de PSE en SVG', 'Juanfe', '', 'todo', 'baja'),
    ('Revisar la garantía "Si no cambia tu vida" frente al manual de voz', 'Juanfe', '', 'todo', 'baja'),
    ('Publicar las landings', 'Juanfe', '', 'todo', 'baja'),
    ('Precio de 2 unidades: $159.900', 'Juanfe', '2026-10-20', 'done', 'media'),
    ('Contenido de la caja: 1 Bloki + instrucciones + bienvenida a la comunidad', 'Juanfe', '2026-10-20', 'done', 'media'),
]

def hub():
    cards = ''
    for slug, over in AVATARES.items():
        a = merge(BASE, over)
        cards += f'''<a class="hub-card" href="{slug}/index.html" >
      <span class="hub-k">{a.get("hub_k", "Avatar")}</span><h2>{a["avatar"]}</h2><p>{a["hub_desc"]}</p>
      <span class="hub-go">Ver landing →</span></a>'''
    names = {1: 'Individual', 2: 'Dúo', 3: 'Combo'}
    cfg = {'planes': [{'qty': p['qty'], 'price': p['price'], 'name': names[p['qty']]} for p in PLANES], 'tareas': TAREAS_INICIALES}
    cfg['remote'] = PANEL_REMOTE
    return f'''<!doctype html><html lang="es-CO"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bloki · Panel del proyecto</title><meta name="robots" content="noindex">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Mono:wght@400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/bloki-landing.css">
<link rel="stylesheet" href="assets/panel.css">
<style>
.hub-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:0;margin-top:8px;border-top:1px solid var(--line)}}
.hub-card{{display:flex;flex-direction:column;gap:10px;padding:26px 24px 26px 0;border-bottom:1px solid var(--line);text-decoration:none;transition:opacity .2s}}
.hub-card:hover{{opacity:.6}}
.hub-card h2{{margin:0;font-size:19px;font-weight:600;letter-spacing:-.02em}}
.hub-card p{{margin:0;font-size:14px;color:var(--ink-soft);line-height:1.55}}
.hub-k{{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-muted)}}
.hub-go{{margin-top:auto;font-size:13px;font-weight:500}}
</style></head><body><main class="panel">
<div class="panel__top">
  <img src="assets/bloki-wordmark.png" alt="Bloki" style="height:26px;width:auto">
  <div class="panel__tools"><span data-saved>Conectando…</span>
    <button class="btn-s" type="button" data-export>Exportar</button><button class="btn-s" type="button" data-import-btn>Importar</button><button class="btn-s" type="button" data-logout>Salir</button>
    <input type="file" accept="application/json" data-import hidden></div>
  <h1>Panel del proyecto</h1>
</div>
<nav class="tabs" role="tablist">
  <button type="button" role="tab" data-tab="landings">Landings</button>
  <button type="button" role="tab" data-tab="finanzas">Escenario financiero</button>
  <button type="button" role="tab" data-tab="pendientes">Pendientes</button>
</nav>
<div data-pane="landings"><section class="pn"><div class="pn__head"><span class="k">8 landings · una por avatar</span>
  <h2>Misma estructura, distinto texto por avatar</h2>
  <p>Galería, caja de compra, por qué sí funciona, ficha, dolores del avatar, comparativa y preguntas. {"" if PUBLICAR else "En borrador, lo que falta aparece con borde rojo."}</p></div>
  <div class="hub-grid">{cards}</div></section></div>
<div class="lock" data-lock hidden><form class="lock__card" autocomplete="on">
  <span class="k">Panel protegido</span><h2 data-lock-title>Ingresa la clave del panel</h2><p data-lock-sub></p>
  <label>Tu nombre<input class="in" name="quien" autocomplete="name" placeholder="Para saber quién guardó cada cambio"></label>
  <label>Clave<input class="in" name="clave" type="password" autocomplete="current-password" required></label>
  <label data-lock-confirm hidden>Repite la clave<input class="in" name="confirmar" type="password" autocomplete="new-password"></label>
  <button class="btn-s btn-s--ink" type="submit">Entrar</button><p class="lock__msg" data-lock-msg></p></form></div>
<div data-pane="finanzas" hidden></div>
<div data-pane="pendientes" hidden></div>
</main>
<script type="application/json" id="panel-config">{json.dumps(cfg, ensure_ascii=False)}</script>
<script src="assets/panel.js"></script>
</body></html>'''

def strip_tags(s):
    import re
    return re.sub(r'<[^>]+>', '', s)

def main():
    for slug, over in AVATARES.items():
        a = merge(BASE, over)
        d = ROOT / slug
        d.mkdir(exist_ok=True)
        (d / 'index.html').write_text(render(slug, a), encoding='utf-8')
        print(f'  ✓ {slug}/index.html')
    (ROOT / 'index.html').write_text(hub(), encoding='utf-8')
    print(f'  ✓ index.html  ({"PUBLICAR" if PUBLICAR else "BORRADOR"})')

if __name__ == '__main__':
    main()
