"""Convierte las landings de Bloki en un tema de Shopify editable (carpeta shopify-theme/).

    python3 shopify_theme.py
    shopify theme push --path shopify-theme --store bloki-n8rfudtw.myshopify.com --theme 189637034183

- Cada bloque de la landing es una sección propia (galería + compra, por qué, ficha, dolores,
  comparativa, preguntas). En el editor de temas se mueven, se quitan, se duplican y cada texto,
  imagen, plan, pregunta o fila es un campo o un bloque.
- Barra de anuncio + encabezado van en el grupo "header"; pie + barra fija de compra en el grupo "footer".
- Inicio y producto = landing general. Cada avatar = página /pages/<slug> con plantilla page.<slug>.
  Este script solo llena el contenido inicial: después de subirlo, lo que se edite en Shopify manda.
  Volver a subir las plantillas (templates/*.json, sections/*-group.json) PISA lo editado en el editor:
  para cambios de código, subir con --only sections/bk-*.liquid snippets assets.
- Las imágenes salen de Archivos de Shopify (shopify://shop_images/...) para que se cambien con el selector.
- Los IDs de variante salen del producto elegido en la sección (por defecto, handle "bloki").
"""
import re, shutil, json
from pathlib import Path
import build
from avatares import AVATARES

build.PUBLICAR = True
ROOT = Path(__file__).parent
OUT = ROOT / 'shopify-theme'
HANDLE = 'bloki'
COLORES = '\n'.join(f'{n}: {h}' for n, h in build.COLORS)

def asset_name(path):
    # Shopify no admite subcarpetas en assets/: pagos/visa.svg -> pago-visa.svg
    return path.replace('pagos/', 'pago-')

def img(name):
    return f'shopify://shop_images/{name}'

def clean(s):
    """Textos pendientes: nunca en la tienda."""
    s = s.replace('un código de [CONFIRMAR]% para', 'un código de descuento para')
    return re.sub(r'\s*\[(?:CONFIRMAR|COMPLETAR)[^\]]*\]', '', s)

def deep_clean(v):
    if isinstance(v, str): return clean(v)
    if isinstance(v, list): return [deep_clean(x) for x in v]
    if isinstance(v, tuple): return tuple(deep_clean(x) for x in v)
    if isinstance(v, dict): return {k: deep_clean(x) for k, x in v.items()}
    return v

# ─────────────────────────────────────────────────────────────
# Piezas comunes de los schemas
# ─────────────────────────────────────────────────────────────
ICON_LABELS = {
    'nfc': 'NFC', 'battery': 'Sin batería', 'app': 'Celular / app', 'android': 'Android', 'palette': 'Colores',
    'lock': 'Candado', 'hand': 'Mano', 'chart': 'Gráfica', 'moon': 'Luna', 'sun': 'Sol', 'kid': 'Niño', 'users': 'Personas',
    'heart': 'Corazón', 'brief': 'Maletín', 'book': 'Libro', 'gift': 'Regalo', 'clock': 'Reloj', 'loop': 'Ciclo',
    'trophy': 'Trofeo', 'eye': 'Ojo', 'bed': 'Cama', 'fork': 'Comida', 'car': 'Carro', 'shield': 'Escudo',
    'spark': 'Destello', 'plane': 'Avión', 'cart': 'Carrito', 'menu': 'Menú', 'sliders': 'Ajustes',
}
ICON_SETTING = {'type': 'select', 'id': 'icon', 'label': 'Ícono', 'default': 'spark',
                'options': [{'value': k, 'label': ICON_LABELS.get(k, k)} for k in build.P]}
FONDO = {'type': 'select', 'id': 'fondo', 'label': 'Fondo', 'default': '',
         'options': [{'value': '', 'label': 'Blanco hueso'}, {'value': 'sec--deep', 'label': 'Gris claro'}]}
ESPACIO = {'type': 'checkbox', 'id': 'tight', 'label': 'Menos espacio arriba y abajo', 'default': False}

def schema(d):
    return '\n{% schema %}\n' + json.dumps(d, ensure_ascii=False, indent=2) + '\n{% endschema %}\n'

SEC_CLASS = ('{%- capture cls -%}sec{% if section.settings.tight %} sec--tight{% endif %}'
             '{% if section.settings.fondo != blank %} {{ section.settings.fondo }}{% endif %}{%- endcapture -%}')

# ─────────────────────────────────────────────────────────────
# Snippets
# ─────────────────────────────────────────────────────────────
def snippet_icon():
    out = ["{%- comment -%} {% render 'bk-icon', name: 'lock', sw: 1.3 %} {%- endcomment -%}",
           '{%- assign sw = sw | default: 1.6 -%}',
           '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{{ sw }}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">',
           '{%- case name -%}']
    for k, v in build.P.items():
        out.append(f"{{%- when '{k}' -%}}{v}")
    out += ['{%- else -%}' + build.P['spark'], '{%- endcase -%}</svg>']
    return '\n'.join(out) + '\n'

# Diapositiva de texto de la galería. Ítems: una línea por ítem, "Título | descripción".
SNIPPET_INFO = '''{%- assign s = b.settings -%}
{%- assign lines = s.items | newline_to_br | split: '<br />' -%}
{%- capture li -%}{%- for l in lines -%}{%- assign parts = l | split: '|' -%}{%- assign t = parts[0] | strip -%}{%- if t != blank -%}<li><b>{{ t }}</b>{{ parts[1] | strip }}</li>{%- endif -%}{%- endfor -%}{%- endcapture -%}
{%- case s.kind -%}
{%- when 'data' -%}
<div class="info info--ink"><span class="info__k">{{ s.k }}</span><span class="info__big">{{ s.big }}</span><p class="info__t" style="margin-top:6px">{{ s.t }}</p><ul style="color:var(--ink)">{{ li }}</ul>{% if s.src != blank %}<p style="font-size:9.5px;color:var(--ink-muted);margin:10px 0 0">Fuente: {{ s.src }}</p>{% endif %}</div>
{%- when 'vs' -%}
<div class="info" style="background:var(--paper)"><span class="info__k">{{ s.k }}</span><p class="info__t">{{ s.t }}</p><ul>{{ li }}</ul></div>
{%- else -%}
<div class="info"><span class="info__k">{{ s.k }}</span><p class="info__t">{{ s.t }}</p><ol>{{ li }}</ol></div>
{%- endcase -%}
'''

# Precio en pesos (entero) → "$89.900" con el formato de la tienda.
SNIPPET_MONEY = '{{- n | times: 100 | money_without_trailing_zeros -}}'

def product_lookup(setting):
    """Producto de la sección → el de la página de producto → handle "bloki"."""
    return ('{%- liquid\n'
            f'  assign bk_product = {setting}\n'
            '  if bk_product == blank and product != blank\n    assign bk_product = product\n  endif\n'
            f"  if bk_product == blank\n    assign bk_product = all_products['{HANDLE}']\n  endif\n"
            '-%}')

# ─────────────────────────────────────────────────────────────
# Secciones
# ─────────────────────────────────────────────────────────────
SECTIONS = {}

SECTIONS['bk-announce'] = '''<div class="announce">{% if section.settings.tag != blank %}<b class="tag">{{ section.settings.tag }}</b>{% endif %}{{ section.settings.text }}</div>''' + schema({
    'name': 'Barra de anuncio', 'class': 'bk-announce-section',
    'settings': [
        {'type': 'text', 'id': 'tag', 'label': 'Etiqueta', 'default': 'OFERTA'},
        {'type': 'inline_richtext', 'id': 'text', 'label': 'Texto', 'default': 'Combo x3 con <b>$69.800</b> de ahorro'},
    ],
    'presets': [{'name': 'Barra de anuncio'}],
    'enabled_on': {'groups': ['header']},
})

SECTIONS['bk-header'] = '''<header class="header"><div class="header__in">
  {%- if section.blocks.size > 0 -%}
  <details class="menu"><summary aria-label="Menú">{% render 'bk-icon', name: 'menu' %}</summary>
    <nav class="menu__panel">{%- for block in section.blocks -%}<a href="{{ block.settings.url }}"{% if block.settings.url contains '#comprar' %} data-goto-buy{% endif %} {{ block.shopify_attributes }}>{{ block.settings.label }}</a>{%- endfor -%}</nav></details>
  {%- else -%}<span></span>{%- endif -%}
  <a class="header__logo" href="{{ routes.root_url }}">
    {%- if section.settings.logo != blank -%}
      <img src="{{ section.settings.logo | image_url: width: 256 }}" alt="{{ shop.name }}" width="64" height="{{ 64 | divided_by: section.settings.logo.aspect_ratio | round }}">
    {%- else -%}<img src="{{ 'bloki-wordmark.png' | asset_url }}" alt="{{ shop.name }}" width="64" height="26">{%- endif -%}
  </a>
  <a class="header__cart" href="{{ routes.root_url }}#comprar" data-goto-buy aria-label="Comprar">{% render 'bk-icon', name: 'cart' %}</a>
</div></header>''' + schema({
    'name': 'Encabezado', 'class': 'bk-header-section',
    'settings': [{'type': 'image_picker', 'id': 'logo', 'label': 'Logo'}],
    'blocks': [{'type': 'link', 'name': 'Enlace del menú', 'settings': [
        {'type': 'text', 'id': 'label', 'label': 'Texto', 'default': 'Preguntas'},
        {'type': 'text', 'id': 'url', 'label': 'Enlace', 'default': '#preguntas',
         'info': '#comprar baja a la caja de compra, #como-funciona a la ficha y #preguntas a las preguntas. También sirve /pages/...'},
    ]}],
    'presets': [{'name': 'Encabezado'}],
    'enabled_on': {'groups': ['header']},
})

# Galería + caja de compra: una sola sección porque en computador van lado a lado.
SECTIONS['bk-producto'] = product_lookup('section.settings.product') + '''
{%- liquid
  assign ss = section.settings
  assign unit = bk_product.price | divided_by: 100
  assign col_names = ''
  assign col_hex = ''
  assign cl = ss.colores | newline_to_br | split: '<br />'
  for l in cl
    assign parts = l | split: ':'
    assign nm = parts[0] | strip
    if nm != blank
      assign hx = parts[1] | strip
      assign col_names = col_names | append: nm | append: '|'
      assign col_hex = col_hex | append: hx | append: '|'
    endif
  endfor
  assign col_names = col_names | split: '|'
  assign col_hex = col_hex | split: '|'
  assign ncol = col_names.size
  assign start = ss.color_start | plus: 0
-%}
<div class="pdp">
<section class="sec sec--tight" id="top"><div class="wrap">
  <div class="gal"><div class="chips">
    {%- for block in section.blocks -%}{%- if block.type == 'chip' -%}
      <div class="chip" {{ block.shopify_attributes }}>{% render 'bk-icon', name: block.settings.icon, sw: 1.3 %}<span>{{ block.settings.text }}</span></div>
    {%- endif -%}{%- endfor -%}
  </div>
  <div><div class="gal__main">
    {%- assign k = 0 -%}
    {%- for block in section.blocks -%}
      {%- if block.type == 'imagen' or block.type == 'info' -%}
      <div class="gal__slide{% if block.type == 'imagen' %} gal__slide--cover{% endif %}{% if k == 0 %} on{% endif %}" {{ block.shopify_attributes }}>
        {%- if block.type == 'imagen' -%}
          {%- if block.settings.image != blank -%}
            {%- if k == 0 -%}{%- assign ld = 'eager' -%}{%- else -%}{%- assign ld = 'lazy' -%}{%- endif -%}
            {{ block.settings.image | image_url: width: 1400 | image_tag: alt: block.settings.alt, loading: ld, widths: '600,900,1200,1400', sizes: '(min-width: 1024px) 55vw, 100vw' }}
          {%- endif -%}
        {%- else -%}{% render 'bk-info', b: block %}{%- endif -%}
      </div>
      {%- assign k = k | plus: 1 -%}
      {%- endif -%}
    {%- endfor -%}
    <div class="gal__arrows"><button type="button" data-gal-prev aria-label="Anterior">‹</button><button type="button" data-gal-next aria-label="Siguiente">›</button></div></div>
    <div class="thumbs">
    {%- assign k = 0 -%}
    {%- for block in section.blocks -%}
      {%- if block.type == 'imagen' or block.type == 'info' -%}
      <button type="button" class="{% if k == 0 %}on{% endif %}" aria-label="Imagen {{ k | plus: 1 }}">
        {%- if block.type == 'imagen' -%}{%- if block.settings.image != blank -%}<img src="{{ block.settings.image | image_url: width: 160 }}" alt="" loading="lazy">{%- endif -%}
        {%- else -%}<span class="t-info">{{ block.settings.thumb }}</span>{%- endif -%}
      </button>
      {%- assign k = k | plus: 1 -%}
      {%- endif -%}
    {%- endfor -%}
    </div></div></div>
</div></section>

<section class="sec buy" id="comprar"><div class="wrap">
  <div class="buy__card">
    <div class="buy__top"><span>{% if ss.launch != blank %}<span class="launch">{{ ss.launch }}</span>{% endif %}</span>{% if ss.pill != blank %}<span class="pill">{% if ss.flag %}<svg class="flag" viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="1" fill="#FCD116"/><rect y="1" width="3" height=".5" fill="#003893"/><rect y="1.5" width="3" height=".5" fill="#CE1126"/></svg>{% endif %}{{ ss.pill }}</span>{% endif %}</div>
    <h1 class="buy__title">{{ ss.title | default: bk_product.title }}</h1>
    {%- if ss.sub != blank %}<p class="buy__sub">{{ ss.sub }}</p>{% endif %}
    {%- if ss.lead != blank %}<p class="buy__lead">{{ ss.lead }}</p>{% endif %}
    {%- if ss.guar_text != blank %}<div class="guar-bar"><span class="guar__seal">{{ ss.guar_days }}<small>DÍAS</small></span><p>{{ ss.guar_text }}</p></div>{% endif %}
    <ul class="checks">
      {%- for block in section.blocks -%}{%- if block.type == 'check' -%}
        <li {{ block.shopify_attributes }}><span class="ck{% if block.settings.gift %} ck--gift{% endif %}"></span><span>{{ block.settings.text }}</span></li>
      {%- endif -%}{%- endfor -%}
    </ul>
    {%- if ss.ship != blank %}<p class="ship"><i></i><span{% if ss.eta %} data-eta{% endif %}>{{ ss.ship }}</span></p>{% endif %}
    <div class="plans" role="radiogroup" aria-label="Elige tu plan">
    {%- for block in section.blocks -%}{%- if block.type == 'plan' -%}
      {%- liquid
        assign bs = block.settings
        assign qty = bs.qty
        assign price = bs.price
        assign full = unit | times: qty
        assign each = price | divided_by: qty
        assign save = full | minus: price
      -%}
      <div class="plan{% if bs.default %} on{% endif %}" role="radio" tabindex="0" aria-checked="{{ bs.default }}" data-qty="{{ qty }}" data-price="{{ price }}" {{ block.shopify_attributes }}>
        {%- if bs.badge != blank %}<span class="plan__badge{% if bs.badge_y %} plan__badge--y{% endif %}">{{ bs.badge }}</span>{% endif %}
        <div class="plan__row"><span class="plan__dot"></span>
          <div><p class="plan__name">{{ bs.name }}</p>
          <p class="plan__desc">{% render 'bk-money', n: each %} c/u{% if save > 0 %}<span class="plan__save">AHORRA {% render 'bk-money', n: save %}</span>{% endif %}{% if bs.perk != blank %}<span class="plan__perk">{{ bs.perk }}</span>{% endif %}</p></div>
          <p class="plan__price"><strong>{% render 'bk-money', n: price %}</strong>{% if save > 0 %}<s>{% render 'bk-money', n: full %}</s>{% endif %}</p></div>
        <div class="colors">
        {%- for u in (1..qty) -%}
          {%- assign ci = u | minus: 1 | plus: start | modulo: ncol -%}
          <div class="colors__row"><span>{% if qty > 1 %}Bloki {{ u }}{% else %}Color{% endif %}: <b>{{ col_names[ci] }}</b></span><span class="sw">
            {%- for n in col_names -%}<button type="button" class="{% if forloop.index0 == ci %}on{% endif %}" style="--c:{{ col_hex[forloop.index0] }}" data-color="{{ n }}" aria-label="{{ n }}"></button>{%- endfor -%}
          </span></div>
        {%- endfor -%}
        </div></div>
    {%- endif -%}{%- endfor -%}
    </div>
    <div class="total"><span>Total</span><span><strong data-total></strong><s data-compare hidden></s><span class="save" data-save hidden></span></span></div>
    <button type="button" class="btn btn--block" data-buy>{{ ss.cta }}</button>
    <p class="buy__err" role="alert"></p>
    {%- if ss.cta_note != blank %}<p class="buy__note">{{ ss.cta_note }}</p>{% endif %}
    {%- if ss.tip_q != blank %}
    <div class="tip"><button type="button" class="tip__btn" aria-describedby="tip-{{ section.id }}">{{ ss.tip_q }} <span class="tip__i" aria-hidden="true">i</span></button>
      <span class="tip__box" role="tooltip" id="tip-{{ section.id }}">{{ ss.tip_a }}</span></div>
    {%- endif %}
    {%- assign trust = ss.trust | newline_to_br | split: '<br />' -%}
    <ul class="micro">{%- for t in trust -%}{%- assign tt = t | strip -%}{%- if tt != blank -%}<li>{{ tt }}</li>{%- endif -%}{%- endfor -%}</ul>
    <div class="pay">
      {%- if ss.pay_pse %}<img class="pay--pse" src="{{ 'pago-pse.svg' | asset_url }}" alt="PSE" loading="lazy">{% endif -%}
      {%- if ss.pay_nequi %}<img class="pay--nequi" src="{{ 'pago-nequi.svg' | asset_url }}" alt="Nequi" loading="lazy">{% endif -%}
      {%- if ss.pay_bancolombia %}<img class="pay--bancolombia" src="{{ 'pago-bancolombia.svg' | asset_url }}" alt="Bancolombia" loading="lazy">{% endif -%}
      {%- if ss.pay_visa %}<img class="pay--visa" src="{{ 'pago-visa.svg' | asset_url }}" alt="VISA" loading="lazy">{% endif -%}
      {%- if ss.pay_mastercard %}<img class="pay--mastercard" src="{{ 'pago-mastercard.svg' | asset_url }}" alt="Mastercard" loading="lazy">{% endif -%}
    </div>
  </div>
</div></section>
</div>
<script type="application/json" id="bk-config">{"slug":{{ template.suffix | default: template.name | json }},"store":"","unitPrice":{{ unit }},"variants":{ {%- for v in bk_product.variants -%}{{ v.option1 | json }}:{{ v.id }}{% unless forloop.last %},{% endunless %}{%- endfor -%} },"discountCodes":{},"popupCode":"","popupDelay":0}</script>''' + schema({
    'name': 'Galería y compra', 'max_blocks': 50,
    'settings': [
        {'type': 'product', 'id': 'product', 'label': 'Producto', 'info': 'De aquí salen el precio unitario y los colores (variantes).'},
        {'type': 'header', 'content': 'Encabezado de la caja'},
        {'type': 'text', 'id': 'launch', 'label': 'Texto de arriba', 'default': 'Precio de lanzamiento por tiempo limitado'},
        {'type': 'text', 'id': 'pill', 'label': 'Sello', 'default': 'Diseñado y fabricado en Colombia'},
        {'type': 'checkbox', 'id': 'flag', 'label': 'Bandera de Colombia en el sello', 'default': True},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'info': 'Vacío = nombre del producto'},
        {'type': 'inline_richtext', 'id': 'sub', 'label': 'Subtítulo'},
        {'type': 'inline_richtext', 'id': 'lead', 'label': 'Descripción'},
        {'type': 'header', 'content': 'Franja de garantía'},
        {'type': 'text', 'id': 'guar_days', 'label': 'Días (sello)', 'default': '30'},
        {'type': 'inline_richtext', 'id': 'guar_text', 'label': 'Texto', 'info': 'Vacío = no se muestra la franja'},
        {'type': 'header', 'content': 'Envío'},
        {'type': 'text', 'id': 'ship', 'label': 'Texto de envío', 'default': 'Llega en 2 a 5 días hábiles · Envío a toda Colombia'},
        {'type': 'checkbox', 'id': 'eta', 'label': 'Reemplazar por la fecha de entrega calculada', 'default': True,
         'info': 'Hora Bogotá, corte a las 12 m., 2 a 3 días hábiles, sin festivos.'},
        {'type': 'header', 'content': 'Planes y colores'},
        {'type': 'textarea', 'id': 'colores', 'label': 'Colores', 'default': COLORES,
         'info': 'Una línea por color: "Nombre: #código". El nombre debe ser igual al de la variante en Shopify.'},
        {'type': 'select', 'id': 'color_start', 'label': 'Color que sale elegido primero', 'default': '0',
         'options': [{'value': str(i), 'label': n} for i, (n, _) in enumerate(build.COLORS)]},
        {'type': 'paragraph', 'content': 'Los precios de los planes son lo que se muestra. El descuento real lo hacen los descuentos automáticos de Shopify (Descuentos): si cambias un precio aquí, cámbialo también allá.'},
        {'type': 'header', 'content': 'Botón y confianza'},
        {'type': 'text', 'id': 'cta', 'label': 'Botón de compra', 'default': 'Comprar ahora →'},
        {'type': 'inline_richtext', 'id': 'cta_note', 'label': 'Línea debajo del botón'},
        {'type': 'text', 'id': 'tip_q', 'label': 'Ayuda debajo del botón', 'default': '¿Y si se me pierde?'},
        {'type': 'inline_richtext', 'id': 'tip_a', 'label': 'Respuesta de la ayuda'},
        {'type': 'textarea', 'id': 'trust', 'label': 'Frases de confianza', 'info': 'Una por línea'},
        {'type': 'checkbox', 'id': 'pay_pse', 'label': 'Logo PSE', 'default': True},
        {'type': 'checkbox', 'id': 'pay_nequi', 'label': 'Logo Nequi', 'default': True},
        {'type': 'checkbox', 'id': 'pay_bancolombia', 'label': 'Logo Bancolombia', 'default': True},
        {'type': 'checkbox', 'id': 'pay_visa', 'label': 'Logo VISA', 'default': True},
        {'type': 'checkbox', 'id': 'pay_mastercard', 'label': 'Logo Mastercard', 'default': True},
    ],
    'blocks': [
        {'type': 'chip', 'name': 'Ícono lateral', 'settings': [
            ICON_SETTING, {'type': 'text', 'id': 'text', 'label': 'Texto', 'default': 'NFC SIN BATERÍA'}]},
        {'type': 'imagen', 'name': 'Galería: imagen', 'settings': [
            {'type': 'image_picker', 'id': 'image', 'label': 'Imagen'},
            {'type': 'text', 'id': 'alt', 'label': 'Texto alternativo', 'default': 'Bloki'}]},
        {'type': 'info', 'name': 'Galería: texto', 'settings': [
            {'type': 'select', 'id': 'kind', 'label': 'Estilo', 'default': 'steps', 'options': [
                {'value': 'steps', 'label': 'Lista numerada'}, {'value': 'data', 'label': 'Dato grande'}, {'value': 'vs', 'label': 'Comparación'}]},
            {'type': 'text', 'id': 'thumb', 'label': 'Miniatura', 'default': 'INFO'},
            {'type': 'text', 'id': 'k', 'label': 'Etiqueta'},
            {'type': 'text', 'id': 'big', 'label': 'Número grande', 'info': 'Solo en "Dato grande"'},
            {'type': 'text', 'id': 't', 'label': 'Título'},
            {'type': 'textarea', 'id': 'items', 'label': 'Ítems', 'info': 'Uno por línea: Título | descripción'},
            {'type': 'text', 'id': 'src', 'label': 'Fuente', 'info': 'Solo en "Dato grande"'}]},
        {'type': 'check', 'name': 'Caja: beneficio', 'settings': [
            {'type': 'inline_richtext', 'id': 'text', 'label': 'Texto', 'default': '<b>Bloqueas con un toque.</b> Sin contraseña ni código.'},
            {'type': 'checkbox', 'id': 'gift', 'label': 'Marcar como regalo', 'default': False}]},
        {'type': 'plan', 'name': 'Caja: plan', 'settings': [
            {'type': 'inline_richtext', 'id': 'name', 'label': 'Nombre', 'default': '<b>Individual</b> · 1 Bloki'},
            {'type': 'number', 'id': 'qty', 'label': 'Cantidad', 'default': 1},
            {'type': 'number', 'id': 'price', 'label': 'Precio total (sin puntos)', 'default': 89900},
            {'type': 'text', 'id': 'perk', 'label': 'Extra (ej. Envío gratis)', 'info': 'Solo se muestra. El envío gratis real es el descuento automático "Envío gratis desde 2 Bloki".'},
            {'type': 'text', 'id': 'badge', 'label': 'Etiqueta'},
            {'type': 'checkbox', 'id': 'badge_y', 'label': 'Etiqueta en amarillo', 'default': False},
            {'type': 'checkbox', 'id': 'default', 'label': 'Plan elegido al entrar', 'default': False}]},
    ],
    'presets': [{'name': 'Galería y compra'}],
})

# Video subido a Archivos de Shopify (Contenido → Archivos). Vacío = la sección no se muestra.
VIDEO_REF = ''  # se llena al subir el video: 'shopify://files/videos/bloki-como-funciona.mp4'

SECTIONS['bk-video'] = SEC_CLASS + '''
{%- if section.settings.video != blank or request.design_mode -%}
<section class="{{ cls }}" id="video"><div class="wrap">
  <div class="center">{% if section.settings.eyebrow != blank %}<span class="eyebrow">{{ section.settings.eyebrow }}</span>{% endif %}{% if section.settings.title != blank %}<h2 class="h2">{{ section.settings.title }}</h2>{% endif %}</div>
  <div class="vid">{%- if section.settings.video != blank -%}{{ section.settings.video | video_tag: muted: true, loop: true, playsinline: true, controls: true, preload: 'none', image_size: '1600x' }}{%- else -%}{{ 'lifestyle-1' | placeholder_svg_tag }}{%- endif -%}</div>
</div></section>
{%- endif -%}''' + schema({
    'name': 'Video',
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta', 'default': 'Cómo funciona'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Bloki en un minuto'},
        {'type': 'video', 'id': 'video', 'label': 'Video', 'info': 'Se reproduce sin sonido cuando está a la vista.'},
        FONDO, ESPACIO,
    ],
    'presets': [{'name': 'Video'}],
})

SECTIONS['bk-funciones'] = SEC_CLASS + '''
<section class="{{ cls }}" id="funciones"><div class="wrap">
  {%- if section.settings.eyebrow != blank %}<span class="eyebrow">{{ section.settings.eyebrow }}</span>{% endif %}
  {%- if section.settings.title != blank %}<h2 class="h2">{{ section.settings.title }}</h2>{% endif %}
  <div class="fx"><div class="fx__tabs" role="tablist">
    {%- for block in section.blocks -%}<button type="button" role="tab" class="{% if forloop.first %}on{% endif %}" aria-selected="{{ forloop.first }}" {{ block.shopify_attributes }}>{% render 'bk-icon', name: block.settings.icon, sw: 1.4 %}<span>{{ block.settings.label }}</span></button>{%- endfor -%}
  </div><div class="fx__body">
    {%- for block in section.blocks -%}<div class="fx__panel" role="tabpanel"{% unless forloop.first %} hidden{% endunless %}><h3>{{ block.settings.title }}</h3>{{ block.settings.text }}</div>{%- endfor -%}
  </div></div>
</div></section>''' + schema({
    'name': 'Funciones en pestañas', 'max_blocks': 10,
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta', 'default': 'La app'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Lo que hace la app'},
        dict(FONDO, default='sec--deep'), ESPACIO,
    ],
    'blocks': [{'type': 'tab', 'name': 'Pestaña', 'settings': [
        ICON_SETTING,
        {'type': 'text', 'id': 'label', 'label': 'Nombre de la pestaña', 'default': 'Modos'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Ocho modos listos para usar'},
        {'type': 'richtext', 'id': 'text', 'label': 'Texto', 'default': '<p>Texto</p>'}]}],
    'presets': [{'name': 'Funciones en pestañas'}],
})

SECTIONS['bk-por-que'] = SEC_CLASS + '''
<section class="{{ cls }}"><div class="wrap why">
  <div class="why__card">{% if section.settings.eyebrow != blank %}<span class="why__tag">{{ section.settings.eyebrow }}</span>{% endif %}<h3>{{ section.settings.title }}</h3><p>{{ section.settings.text }}</p></div>
  {%- if section.settings.guar_title != blank %}
  <div class="why__card why__guar"><span class="why__icon">{% render 'bk-icon', name: 'shield', sw: 1.5 %}</span><div><h4>{{ section.settings.guar_title }}</h4><p>{{ section.settings.guar_text }}</p></div></div>
  {%- endif %}
</div></section>''' + schema({
    'name': 'Por qué sí funciona',
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta', 'default': 'Por qué sí funciona'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Por qué el límite de pantalla te duró una semana'},
        {'type': 'inline_richtext', 'id': 'text', 'label': 'Texto'},
        {'type': 'header', 'content': 'Tarjeta de garantía'},
        {'type': 'text', 'id': 'guar_title', 'label': 'Título', 'default': 'Garantía de satisfacción de 30 días', 'info': 'Vacío = no se muestra'},
        {'type': 'inline_richtext', 'id': 'guar_text', 'label': 'Texto'},
        FONDO, dict(ESPACIO, default=True),
    ],
    'presets': [{'name': 'Por qué sí funciona'}],
})

SECTIONS['bk-ficha'] = SEC_CLASS + '''
<section class="{{ cls }}" id="como-funciona"><div class="wrap">
  {%- if section.settings.title != blank %}<h2 class="h2">{{ section.settings.title }}</h2>{% endif %}
  <div class="acc">{%- for block in section.blocks -%}<details{% if block.settings.open %} open{% endif %} {{ block.shopify_attributes }}><summary>{{ block.settings.title }}</summary><div class="acc__body">{{ block.settings.body }}</div></details>{%- endfor -%}</div>
</div></section>''' + schema({
    'name': 'Ficha (desplegables)', 'max_blocks': 30,
    'settings': [{'type': 'text', 'id': 'title', 'label': 'Título (opcional)'}, FONDO, dict(ESPACIO, default=True)],
    'blocks': [{'type': 'item', 'name': 'Desplegable', 'settings': [
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Qué es'},
        {'type': 'richtext', 'id': 'body', 'label': 'Contenido', 'default': '<p>Texto</p>'},
        {'type': 'checkbox', 'id': 'open', 'label': 'Abierto al entrar', 'default': False}]}],
    'presets': [{'name': 'Ficha (desplegables)'}],
})

SECTIONS['bk-dolores'] = SEC_CLASS + '''
<section class="{{ cls }}"><div class="wrap">
  <div class="split"><div class="split__copy">{% if section.settings.eyebrow != blank %}<span class="eyebrow">{{ section.settings.eyebrow }}</span>{% endif %}
  <h2 class="h2 h2--lines">{%- for block in section.blocks -%}{%- if block.type == 'line' -%}<span {{ block.shopify_attributes }}>{{ block.settings.text }}</span>{%- endif -%}{%- endfor -%}</h2>
  {%- if section.settings.text != blank %}<p class="lead">{{ section.settings.text }}</p>{% endif %}
  <div class="pains">{%- for block in section.blocks -%}{%- if block.type == 'pain' -%}<div class="pain" {{ block.shopify_attributes }}><span class="pain__ic">{% render 'bk-icon', name: block.settings.icon, sw: 1.3 %}</span><h3>{{ block.settings.title }}</h3><p>{{ block.settings.text }}</p></div>{%- endif -%}{%- endfor -%}</div></div>
  {%- if section.settings.image != blank %}
  <figure class="figure">{{ section.settings.image | image_url: width: 1200 | image_tag: alt: section.settings.alt, loading: 'lazy', widths: '600,900,1200', sizes: '(min-width: 1024px) 45vw, 100vw' }}</figure>
  {%- endif %}</div>
</div></section>''' + schema({
    'name': '¿Te suena familiar?', 'max_blocks': 20,
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta', 'default': '¿Te suena familiar?'},
        {'type': 'inline_richtext', 'id': 'text', 'label': 'Texto debajo del título'},
        {'type': 'image_picker', 'id': 'image', 'label': 'Foto'},
        {'type': 'text', 'id': 'alt', 'label': 'Texto alternativo de la foto', 'default': 'Bloki morado junto al celular con la app abierta'},
        dict(FONDO, default='sec--deep'), ESPACIO,
    ],
    'blocks': [
        {'type': 'line', 'name': 'Línea del título', 'settings': [{'type': 'text', 'id': 'text', 'label': 'Texto', 'default': 'Sí quieres usarlo menos.'}]},
        {'type': 'pain', 'name': 'Escena', 'settings': [ICON_SETTING,
            {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'En la cama'},
            {'type': 'inline_richtext', 'id': 'text', 'label': 'Texto', 'default': 'Dijiste "el último" a las 11:40.'}]},
    ],
    'presets': [{'name': '¿Te suena familiar?'}],
})

SECTIONS['bk-comparativa'] = SEC_CLASS + '''
<section class="{{ cls }}"><div class="wrap">
  {%- if section.settings.eyebrow != blank %}<span class="eyebrow">{{ section.settings.eyebrow }}</span>{% endif %}
  <h2 class="h2">{{ section.settings.title }}</h2>
  <table class="cmp"><tr><th></th><th class="us">{% if section.settings.image != blank %}<img src="{{ section.settings.image | image_url: width: 120 }}" alt="" loading="lazy">{% endif %}{{ section.settings.col1 }}</th><th>{{ section.settings.col2 }}</th><th>{{ section.settings.col3 }}</th></tr>
  {%- for block in section.blocks -%}
    <tr {{ block.shopify_attributes }}><td>{{ block.settings.label }}</td>
    {%- for v in (1..3) -%}
      {%- assign key = 'v' | append: v -%}{%- assign val = block.settings[key] | strip -%}{%- assign low = val | downcase -%}
      <td{% if v == 1 %} class="us"{% endif %}>{%- if low == 'si' or low == 'sí' -%}<span class="yes">✓</span>{%- elsif low == 'no' -%}<span class="no">✕</span>{%- else -%}<span class="txt">{{ val }}</span>{%- endif -%}</td>
    {%- endfor -%}</tr>
  {%- endfor -%}
  </table>
  {%- if section.settings.note != blank %}<p class="small" style="margin:14px 0 0">{{ section.settings.note }}</p>{% endif %}
</div></section>''' + schema({
    'name': 'Comparativa', 'max_blocks': 20,
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta', 'default': 'Por qué Bloki'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': '¿Por qué un compañero físico y no otra app?'},
        {'type': 'image_picker', 'id': 'image', 'label': 'Foto de la columna Bloki'},
        {'type': 'text', 'id': 'col1', 'label': 'Columna 1', 'default': 'Bloki'},
        {'type': 'text', 'id': 'col2', 'label': 'Columna 2', 'default': 'Límite de pantalla'},
        {'type': 'text', 'id': 'col3', 'label': 'Columna 3', 'default': 'Apps de bloqueo'},
        {'type': 'inline_richtext', 'id': 'note', 'label': 'Nota debajo'},
        FONDO, ESPACIO,
    ],
    'blocks': [{'type': 'row', 'name': 'Fila', 'settings': [
        {'type': 'text', 'id': 'label', 'label': 'Característica', 'default': 'Se paga una vez'},
        {'type': 'paragraph', 'content': 'Escribe "si" para ✓, "no" para ✕, o cualquier otro texto.'},
        {'type': 'text', 'id': 'v1', 'label': 'Columna 1', 'default': 'si'},
        {'type': 'text', 'id': 'v2', 'label': 'Columna 2', 'default': 'no'},
        {'type': 'text', 'id': 'v3', 'label': 'Columna 3', 'default': 'no'}]}],
    'presets': [{'name': 'Comparativa'}],
})

SECTIONS['bk-faq'] = SEC_CLASS + '''
<section class="{{ cls }}" id="preguntas"><div class="wrap">
  <div class="faq"><div class="faq__head">{% if section.settings.eyebrow != blank %}<span class="eyebrow">{{ section.settings.eyebrow }}</span>{% endif %}
  <h2 class="h2">{{ section.settings.title }}</h2></div>
  <div class="faq__list"><div class="acc">{%- for block in section.blocks -%}<details {{ block.shopify_attributes }}><summary>{{ block.settings.q }}</summary><div class="acc__body">{{ block.settings.a }}</div></details>{%- endfor -%}</div></div></div>
</div></section>''' + schema({
    'name': 'Preguntas frecuentes', 'max_blocks': 40,
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta', 'default': 'Preguntas'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Lo que más nos preguntan'},
        dict(FONDO, default='sec--deep'), ESPACIO,
    ],
    'blocks': [{'type': 'q', 'name': 'Pregunta', 'settings': [
        {'type': 'text', 'id': 'q', 'label': 'Pregunta', 'default': '¿La app se paga aparte?'},
        {'type': 'richtext', 'id': 'a', 'label': 'Respuesta', 'default': '<p>No.</p>'}]}],
    'presets': [{'name': 'Preguntas frecuentes'}],
})

# Sección libre para agregar contenido nuevo desde el editor sin tocar código.
SECTIONS['bk-texto'] = SEC_CLASS + '''
<section class="{{ cls }}"><div class="wrap{% if section.settings.center %} center{% endif %}">
  {%- if section.settings.eyebrow != blank %}<span class="eyebrow">{{ section.settings.eyebrow }}</span>{% endif %}
  {%- if section.settings.title != blank %}<h2 class="h2">{{ section.settings.title }}</h2>{% endif %}
  {%- if section.settings.text != blank %}<div class="lead">{{ section.settings.text }}</div>{% endif %}
  {%- if section.settings.image != blank %}<figure class="figure">{{ section.settings.image | image_url: width: 1400 | image_tag: loading: 'lazy', widths: '600,900,1400' }}</figure>{% endif %}
  {%- if section.settings.button != blank %}<a class="btn btn--block" href="#comprar" data-goto-buy>{{ section.settings.button }}</a>{% endif %}
</div></section>''' + schema({
    'name': 'Texto e imagen',
    'settings': [
        {'type': 'text', 'id': 'eyebrow', 'label': 'Etiqueta'},
        {'type': 'text', 'id': 'title', 'label': 'Título', 'default': 'Título'},
        {'type': 'richtext', 'id': 'text', 'label': 'Texto'},
        {'type': 'image_picker', 'id': 'image', 'label': 'Imagen'},
        {'type': 'text', 'id': 'button', 'label': 'Botón que baja a la compra', 'info': 'Vacío = sin botón'},
        {'type': 'checkbox', 'id': 'center', 'label': 'Centrado', 'default': False},
        FONDO, ESPACIO,
    ],
    'presets': [{'name': 'Texto e imagen'}],
})

SECTIONS['bk-sticky'] = product_lookup('section.settings.product') + '''
<div class="sticky" aria-hidden="true"><div class="sticky__in">
  {%- if section.settings.image != blank %}<img src="{{ section.settings.image | image_url: width: 120 }}" alt="">{% endif %}
  <span class="sticky__info"><strong>{{ section.settings.title | default: bk_product.title }}</strong>{{ section.settings.from }} <b>{{ bk_product.price | money_without_trailing_zeros }}</b></span>
  <a class="btn" href="#comprar" data-goto-buy tabindex="-1">{{ section.settings.label }}</a>
</div></div>''' + schema({
    'name': 'Barra fija de compra',
    'settings': [
        {'type': 'paragraph', 'content': 'Aparece al bajar, solo en páginas que tienen la sección "Galería y compra".'},
        {'type': 'product', 'id': 'product', 'label': 'Producto'},
        {'type': 'image_picker', 'id': 'image', 'label': 'Miniatura'},
        {'type': 'text', 'id': 'title', 'label': 'Nombre', 'info': 'Vacío = nombre del producto'},
        {'type': 'text', 'id': 'from', 'label': 'Antes del precio', 'default': 'Desde'},
        {'type': 'text', 'id': 'label', 'label': 'Botón', 'default': 'Quiero mi Bloki'},
    ],
    'presets': [{'name': 'Barra fija de compra'}],
    'enabled_on': {'groups': ['footer']},
})

SECTIONS['bk-footer'] = '''<footer class="foot"><div class="wrap">
  {%- if section.settings.logo != blank -%}<img src="{{ section.settings.logo | image_url: width: 256 }}" alt="{{ shop.name }}" width="64" height="{{ 64 | divided_by: section.settings.logo.aspect_ratio | round }}">
  {%- else -%}<img src="{{ 'bloki-wordmark.png' | asset_url }}" alt="{{ shop.name }}" width="64" height="26">{%- endif -%}
  {%- if section.settings.text != blank %}<p>{{ section.settings.text }}</p>{% endif %}
  <nav>
    {%- if section.settings.policies -%}{%- for policy in shop.policies -%}<a href="{{ policy.url }}">{{ policy.title }}</a>{%- endfor -%}{%- endif -%}
    {%- for block in section.blocks -%}<a href="{{ block.settings.url }}" {{ block.shopify_attributes }}>{{ block.settings.label }}</a>{%- endfor -%}
    {%- if section.settings.contact and shop.email != blank -%}<a href="mailto:{{ shop.email }}">Contacto</a>{%- endif -%}
  </nav>
  <small>© {{ 'now' | date: '%Y' }} {{ section.settings.copy }}</small>
</div></footer>''' + schema({
    'name': 'Pie de página',
    'settings': [
        {'type': 'image_picker', 'id': 'logo', 'label': 'Logo'},
        {'type': 'inline_richtext', 'id': 'text', 'label': 'Texto', 'default': 'Tu compañero físico que bloquea las apps que eliges. Diseñado y fabricado en Colombia.'},
        {'type': 'checkbox', 'id': 'policies', 'label': 'Mostrar políticas', 'default': True},
        {'type': 'checkbox', 'id': 'contact', 'label': 'Mostrar contacto (correo de la tienda)', 'default': True},
        {'type': 'text', 'id': 'copy', 'label': 'Nombre en el ©', 'default': 'Bloki'},
    ],
    'blocks': [{'type': 'link', 'name': 'Enlace', 'settings': [
        {'type': 'text', 'id': 'label', 'label': 'Texto', 'default': 'Instagram'},
        {'type': 'url', 'id': 'url', 'label': 'Enlace'}]}],
    'presets': [{'name': 'Pie de página'}],
    'enabled_on': {'groups': ['footer']},
})

# ─────────────────────────────────────────────────────────────
# Contenido inicial de cada plantilla (sale de BASE + avatar)
# ─────────────────────────────────────────────────────────────
def sec(type_, settings, items=()):
    d = {'type': type_, 'settings': settings}
    if items:
        d['blocks'], d['block_order'] = {}, []
        for i, (t, st) in enumerate(items):
            bid = f'{t}_{i+1}'
            d['blocks'][bid] = {'type': t, 'settings': st}
            d['block_order'].append(bid)
    return d

def lines(items):
    return '\n'.join(f'{t} | {d}' for t, d in items)

def landing(a):
    b, g, guar = a['buy'], a['gift'], a['guarantee']
    names = {1: 'Individual', 2: 'Dúo', 3: 'Combo'}
    items = [('chip', {'icon': i, 'text': t}) for i, t, _ in a['chips']]
    for s in a['gallery']:
        if 'img' in s:
            items.append(('imagen', {'image': img(s['img']), 'alt': s.get('alt', 'Bloki')}))
        else:
            items.append(('info', {'kind': s['type'], 'thumb': s['thumb'], 'k': s['k'], 't': s['t'], 'big': s.get('big', ''),
                                   'items': lines(s['items']), 'src': s.get('src', '')}))
    items += [('check', {'text': c, 'gift': False}) for c in b['checks']]
    items.append(('check', {'text': f'<b>Gratis: {g["title"]}.</b> {g["sub"]}.', 'gift': True}))
    for k, p in enumerate(build.PLANES):
        pl = a['plans'][k]
        items.append(('plan', {'name': f'<b>{names[p["qty"]]}</b> · {p["qty"]} Bloki', 'qty': p['qty'], 'price': p['price'],
                               'perk': p.get('perk', ''), 'badge': pl.get('badge', ''), 'badge_y': bool(pl.get('badge_y')), 'default': (k + 1) == a['default_plan']}))
    producto = sec('bk-producto', {
        'product': HANDLE, 'launch': 'Precio de lanzamiento por tiempo limitado', 'pill': b['pill'], 'flag': True, 'title': 'Bloki',
        'sub': b['sub'], 'lead': b['lead'], 'guar_days': '30', 'guar_text': f'<b>{guar["title"]}</b> · Sin preguntas',
        'ship': b['ship'], 'eta': True, 'colores': COLORES, 'color_start': str(a.get('color_start', 0) % len(build.COLORS)),
        'cta': b['cta'], 'cta_note': b['cta_note'], 'tip_q': '¿Y si se me pierde?',
        'tip_a': 'Cada Bloki trae <b>3 desbloqueos de emergencia</b>. Respondes tu pregunta de seguridad y tus apps se desbloquean. Si necesitas más, los encuentras dentro de la app.',
        'trust': '\n'.join(b['trust']), 'pay_pse': True, 'pay_nequi': True, 'pay_bancolombia': True, 'pay_visa': True, 'pay_mastercard': True,
    }, items)
    w = a['why']
    why = sec('bk-por-que', {'eyebrow': w['eyebrow'], 'title': w['title'], 'text': w['text'],
                             'guar_title': guar['title'], 'guar_text': guar['text'], 'fondo': '', 'tight': True})
    ficha = sec('bk-ficha', {'title': '', 'fondo': '', 'tight': True},
                [('item', {'title': t, 'body': body, 'open': bool(op)}) for t, body, op in a['details']])
    dolores = sec('bk-dolores', {'eyebrow': '¿Te suena familiar?', 'text': a['pain_text'], 'image': img(a.get('pain_img', 'bloki-morado-app.jpg')),
                                 'alt': 'Bloki morado junto al celular con la app abierta', 'fondo': 'sec--deep', 'tight': False},
                  [('line', {'text': l}) for l in a['pain_lines']] + [('pain', {'icon': i, 'title': t, 'text': d}) for i, t, d in a['pains']])
    cols = a['cmp_cols']
    comparativa = sec('bk-comparativa', {'eyebrow': 'Por qué Bloki', 'title': a['cmp_title'], 'image': img('bloki-lila-tejido.jpg'),
                                         'col1': cols[0], 'col2': cols[1], 'col3': cols[2], 'note': a['cmp_note'], 'fondo': '', 'tight': False},
                      [('row', {'label': r[0], 'v1': r[1], 'v2': r[2], 'v3': r[3]}) for r in a['cmp_rows']])
    perdida = [q for q in a['faq'] if q[0].startswith('¿Qué pasa si se me pierde')]
    resto = [q for q in a['faq'] if not q[0].startswith('¿Qué pasa si se me pierde')]
    faq = sec('bk-faq', {'eyebrow': 'Preguntas', 'title': 'Lo que más nos preguntan', 'fondo': 'sec--deep', 'tight': False},
              [('q', {'q': q, 'a': ans}) for q, ans in perdida + a['faq_cases'] + resto])
    v = a['video']
    video = sec('bk-video', {'eyebrow': v['eyebrow'], 'title': v['title'], 'video': VIDEO_REF, 'fondo': '', 'tight': False})
    funciones = sec('bk-funciones', {'eyebrow': a['features_eyebrow'], 'title': a['features_title'], 'fondo': 'sec--deep', 'tight': False},
                    [('tab', {'icon': i, 'label': lbl, 'title': t, 'text': d}) for i, lbl, t, d in a['features']])
    sections = {'producto': producto, 'video': video, 'funciones': funciones, 'por-que': why, 'ficha': ficha, 'dolores': dolores, 'comparativa': comparativa, 'preguntas': faq}
    return {'sections': sections, 'order': list(sections)}

def groups():
    a = deep_clean(build.BASE)
    header = {'type': 'header', 'name': 'Encabezado', 'sections': {
        'anuncio': sec('bk-announce', {'tag': 'OFERTA', 'text': a['announce']}),
        'encabezado': sec('bk-header', {'logo': img('bloki-wordmark.png')},
                          [('link', {'label': 'Comprar', 'url': '#comprar'}), ('link', {'label': 'Cómo funciona', 'url': '#como-funciona'}),
                           ('link', {'label': 'Preguntas', 'url': '#preguntas'})]),
    }, 'order': ['anuncio', 'encabezado']}
    footer = {'type': 'footer', 'name': 'Pie de página', 'sections': {
        'pie': sec('bk-footer', {'logo': img('bloki-wordmark.png'), 'policies': True, 'contact': True, 'copy': 'Bloki',
                                 'text': 'Tu compañero físico que bloquea las apps que eliges. Diseñado y fabricado en Colombia.'}),
        'barra': sec('bk-sticky', {'product': HANDLE, 'image': img('bloki-lila-tejido.jpg'), 'title': 'Bloki', 'from': 'Desde', 'label': a['sticky_label']}),
    }, 'order': ['pie', 'barra']}
    return header, footer

LAYOUT = '''<!doctype html>
<html lang="es-CO">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ page_title }}{% unless page_title contains shop.name %} · {{ shop.name }}{% endunless %}</title>
{% if page_description %}<meta name="description" content="{{ page_description | escape }}">{% endif %}
<link rel="canonical" href="{{ canonical_url }}">
<meta property="og:site_name" content="{{ shop.name }}">
<meta property="og:title" content="{{ page_title | escape }}">
{% if page_description %}<meta property="og:description" content="{{ page_description | escape }}">{% endif %}
<meta property="og:image" content="https:{{ 'bloki-lila-tejido.jpg' | asset_url }}">
<meta property="og:url" content="{{ canonical_url }}">
<link rel="icon" type="image/png" href="{{ 'bloki-lila-tejido.jpg' | asset_url }}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Mono:wght@400&display=swap" rel="stylesheet">
{{ 'bloki-landing.css' | asset_url | stylesheet_tag }}
{{ 'bloki-shopify.css' | asset_url | stylesheet_tag }}
{{ content_for_header }}
</head>
<body>
%s
<script defer src="{{ 'bloki-landing.js' | asset_url }}"></script>
</body>
</html>
'''

SHOP_CSS = '''/* Piezas propias del tema de Shopify (el resto viene de bloki-landing.css) */
.teaser,.pop{display:none!important}
/* Shopify envuelve cada sección en un div: lo sticky va en el envoltorio */
.bk-header-section{position:sticky;top:0;z-index:50}
.bk-header-section .header{position:relative}
.shopify-section:has(.pdp)+.shopify-section>.sec:first-of-type{border-top:0;padding-top:0}
@media (min-width:1024px){.shopify-section:has(.pdp)+.shopify-section>.sec:first-of-type{padding-top:24px}}
.foot{border-top:1px solid var(--line);padding:36px 0 120px;text-align:center;font-size:12.5px;color:var(--ink-soft)}
.foot img{height:22px;width:auto;margin:0 auto 10px;display:block}
.foot p{margin:0 0 14px}
.foot nav{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 18px;margin-bottom:12px}
.foot a{color:var(--ink-soft);text-decoration:underline;text-underline-offset:3px}
.foot small{color:var(--ink-muted)}
.plain{padding:48px 0 72px;min-height:50vh}
.plain h1{font-size:30px;font-weight:600;letter-spacing:-.03em;margin:0 0 18px}
.plain .rte{color:var(--ink-soft);font-size:15px;line-height:1.65}
.plain .rte h2,.plain .rte h3{color:var(--ink)}
.plain .btn{margin-top:18px}
@media (min-width:1024px){.plain .wrap{max-width:760px}}
'''

def plain_section(name, html):
    return '<main class="plain"><div class="wrap">' + html + '</div></main>' + schema({'name': name[:25], 'settings': []})

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ['layout', 'templates', 'templates/customers', 'sections', 'snippets', 'assets', 'config', 'locales']:
        (OUT / d).mkdir(parents=True, exist_ok=True)

    for f in (ROOT / 'assets').rglob('*'):
        if f.is_file() and f.suffix in {'.css', '.js', '.jpg', '.png', '.svg'} and not f.name.startswith('panel'):
            rel = f.relative_to(ROOT / 'assets').as_posix()
            shutil.copy(f, OUT / 'assets' / asset_name(rel))
    (OUT / 'assets' / 'bloki-shopify.css').write_text(SHOP_CSS)

    (OUT / 'layout' / 'theme.liquid').write_text(LAYOUT.replace('%s', "{% sections 'header-group' %}\n<main id=\"MainContent\">{{ content_for_layout }}</main>\n{% sections 'footer-group' %}"))
    (OUT / 'layout' / 'password.liquid').write_text(LAYOUT.replace('%s', '{{ content_for_layout }}'))

    (OUT / 'snippets' / 'bk-icon.liquid').write_text(snippet_icon())
    (OUT / 'snippets' / 'bk-info.liquid').write_text(SNIPPET_INFO)
    (OUT / 'snippets' / 'bk-money.liquid').write_text(SNIPPET_MONEY)
    for name, src in SECTIONS.items():
        (OUT / 'sections' / f'{name}.liquid').write_text(src)
    header, footer = groups()
    write_json(OUT / 'sections' / 'header-group.json', header)
    write_json(OUT / 'sections' / 'footer-group.json', footer)

    for slug, over in AVATARES.items():
        data = landing(deep_clean(build.merge(build.BASE, over)))
        if slug == 'general':
            write_json(OUT / 'templates' / 'index.json', data)
            write_json(OUT / 'templates' / 'product.json', data)
        else:
            write_json(OUT / 'templates' / f'page.{slug}.json', data)

    plain = {
        'page': '<h1>{{ page.title }}</h1><div class="rte">{{ page.content }}</div>',
        'collection': '<h1>{{ collection.title }}</h1><p class="rte">Bloki es un solo producto.</p><a class="btn" href="{{ routes.root_url }}#comprar">Ver Bloki →</a>',
        'list-collections': '<h1>Colecciones</h1><a class="btn" href="{{ routes.root_url }}#comprar">Ver Bloki →</a>',
        'search': '<h1>Buscar</h1><p class="rte">Bloki es un solo producto.</p><a class="btn" href="{{ routes.root_url }}#comprar">Ver Bloki →</a>',
        '404': '<h1>Esta página no existe</h1><p class="rte">Pero Bloki sí.</p><a class="btn" href="{{ routes.root_url }}">Ir al inicio →</a>',
        'cart': '<h1>Tu carrito</h1>{% if cart.item_count > 0 %}<div class="rte">{% for item in cart.items %}<p>{{ item.quantity }} × {{ item.title }} — {{ item.final_line_price | money }}</p>{% endfor %}<p><b>Total: {{ cart.total_price | money }}</b></p></div><a class="btn" href="{{ routes.root_url }}checkout">Ir a pagar →</a>{% else %}<p class="rte">Está vacío.</p><a class="btn" href="{{ routes.root_url }}#comprar">Ver Bloki →</a>{% endif %}',
        'blog': '<h1>{{ blog.title }}</h1>{% for article in blog.articles %}<p><a href="{{ article.url }}">{{ article.title }}</a></p>{% endfor %}',
        'article': '<h1>{{ article.title }}</h1><div class="rte">{{ article.content }}</div>',
        'password': '<h1>Bloki llega pronto</h1><p class="rte">{{ shop.password_message }}</p>{% form "storefront_password" %}<input class="in" type="password" name="password" placeholder="Contraseña"><button class="btn" type="submit">Entrar</button>{% endform %}',
    }
    for name, html in plain.items():
        (OUT / 'sections' / f'plain-{name}.liquid').write_text(plain_section(f'Página {name}', html))
        write_json(OUT / 'templates' / f'{name}.json', {'sections': {'main': {'type': f'plain-{name}', 'settings': {}}}, 'order': ['main']})
    (OUT / 'templates' / 'gift_card.liquid').write_text("{% layout none %}<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><title>Tarjeta de regalo</title>{{ content_for_header }}</head><body><h1>{{ gift_card.balance | money }}</h1><p>{{ gift_card.code }}</p></body></html>")
    for c in ['login', 'register', 'account', 'order', 'addresses', 'activate_account', 'reset_password']:
        (OUT / 'templates' / 'customers' / f'{c}.liquid').write_text("<main class=\"plain\"><div class=\"wrap\"><h1>Cuenta</h1><p class=\"rte\">Para dudas con tu pedido, escríbenos.</p></div></main>")

    (OUT / 'config' / 'settings_schema.json').write_text(json.dumps([{'name': 'theme_info', 'theme_name': 'Bloki', 'theme_version': '2.0.0', 'theme_author': 'LA REAL', 'theme_documentation_url': 'https://juanfelareal.github.io/bloki-panel/', 'theme_support_url': 'https://juanfelareal.github.io/bloki-panel/'}], indent=2))
    (OUT / 'config' / 'settings_data.json').write_text(json.dumps({'current': {}}, indent=2))
    (OUT / 'locales' / 'es.default.json').write_text(json.dumps({'general': {'title': 'Bloki'}}, indent=2))
    print(f'  ✓ tema en {OUT}')

if __name__ == '__main__':
    main()
