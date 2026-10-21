"""Convierte las landings de Bloki en un tema de Shopify (carpeta shopify-theme/).

    python3 shopify_theme.py
    shopify theme push --path shopify-theme --store bloki-n8rfudtw.myshopify.com --unpublished --theme "Bloki"

- Inicio y página de producto = landing general. Cada avatar = página /pages/<slug> con plantilla page.<slug>.
- Los IDs de variante salen del producto con handle "bloki" (no hay que copiarlos a mano).
- El botón de compra usa /cart/VARIANTE:CANT (relativo) → checkout. Los descuentos por cantidad
  son automáticos en Shopify (Dúo −$19.900, Combo −$69.800).
- Sale en modo publicado: sin etiquetas de borrador, sin testimonios de ejemplo, sin [CONFIRMAR]/[COMPLETAR],
  y sin el popup de descuento (no hay código real todavía).
"""
import re, shutil, json
from pathlib import Path
import build
from avatares import AVATARES

build.PUBLICAR = True
ROOT = Path(__file__).parent
OUT = ROOT / 'shopify-theme'
HANDLE = 'bloki'

def asset_name(path):
    # Shopify no admite subcarpetas en assets/: pagos/visa.svg -> pago-visa.svg
    return path.replace('pagos/', 'pago-')

def to_liquid(page_html):
    body = page_html.split('<body>', 1)[1].rsplit('</body>', 1)[0]
    body = re.sub(r'\.\./assets/([\w./-]+)', lambda m: "{{ '%s' | asset_url }}" % asset_name(m.group(1)), body)
    # textos pendientes: nunca en la tienda
    body = body.replace('un código de [CONFIRMAR]% para', 'un código de descuento para')
    body = re.sub(r'\s*\[(?:CONFIRMAR|COMPLETAR)[^\]]*\]', '', body)
    # config de compra: variantes reales del producto y carrito relativo
    def fix_cfg(m):
        cfg = json.loads(m.group(1))
        cfg['store'] = ''
        cfg['popupDelay'] = 0
        cfg['variants'] = '__VARIANTS__'
        txt = json.dumps(cfg, ensure_ascii=False)
        liquid = ('{%- assign bk = all_products["' + HANDLE + '"] -%}{ '
                  '{%- for v in bk.variants -%}{{ v.option1 | json }}:{{ v.id }}{% unless forloop.last %},{% endunless %}{%- endfor -%}}')
        return '<script type="application/json" id="bk-config">' + txt.replace('"__VARIANTS__"', liquid) + '</script>'
    body = re.sub(r'<script type="application/json" id="bk-config">(.*?)</script>', fix_cfg, body, flags=re.S)
    body = body.replace('<script src="{{', '<script defer src="{{')
    body = body.replace('<footer style="padding:30px 16px 110px;text-align:center;font-size:11px;color:var(--ink-muted)">Bloki · Hecho en Colombia</footer>',
                        "{% render 'bloki-footer' %}")
    return body

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
{{ content_for_layout }}
</body>
</html>
'''

# Páginas de Shopify que no son landing (políticas, búsqueda, 404…): mismo estilo, simples.
PLAIN = '''<div class="announce"><b class="tag">BLOKI</b>Tu compañero físico que bloquea las apps que eliges</div>
<header class="header"><div class="header__in"><span></span>
  <a class="header__logo" href="{{ routes.root_url }}"><img src="{{ 'bloki-wordmark.png' | asset_url }}" alt="Bloki" width="64" height="26"></a>
  <a class="header__cart" href="{{ routes.root_url }}#comprar" aria-label="Comprar"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 4h2l2.4 11h11L21 7H6.2"/><circle cx="9" cy="20" r="1.3"/><circle cx="18" cy="20" r="1.3"/></svg></a>
</div></header>
<main class="plain"><div class="wrap">%s</div></main>
{%% render 'bloki-footer' %%}'''

FOOTER = '''<footer class="foot"><div class="wrap">
  <img src="{{ 'bloki-wordmark.png' | asset_url }}" alt="Bloki" width="64" height="26">
  <p>Tu compañero físico que bloquea las apps que eliges. Diseñado y fabricado en Colombia.</p>
  <nav>
    {%- for policy in shop.policies -%}<a href="{{ policy.url }}">{{ policy.title }}</a>{%- endfor -%}
    {%- if shop.email != blank -%}<a href="mailto:{{ shop.email }}">Contacto</a>{%- endif -%}
  </nav>
  <small>© {{ 'now' | date: '%Y' }} Bloki</small>
</div></footer>'''

SHOP_CSS = '''/* Piezas propias del tema de Shopify (el resto viene de bloki-landing.css) */
.teaser,.pop{display:none!important}
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

def section(name, body):
    return body + '\n{% schema %}\n' + json.dumps({'name': name, 'settings': []}, ensure_ascii=False) + '\n{% endschema %}\n'

def tpl(section_type):
    return json.dumps({'sections': {'main': {'type': section_type, 'settings': {}}}, 'order': ['main']}, indent=2)

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ['layout', 'templates', 'templates/customers', 'sections', 'snippets', 'assets', 'config', 'locales']:
        (OUT / d).mkdir(parents=True, exist_ok=True)

    # assets
    for f in (ROOT / 'assets').rglob('*'):
        if f.is_file() and f.suffix in {'.css', '.js', '.jpg', '.png', '.svg'} and not f.name.startswith('panel'):
            rel = f.relative_to(ROOT / 'assets').as_posix()
            shutil.copy(f, OUT / 'assets' / asset_name(rel))
    js = (OUT / 'assets' / 'bloki-landing.js').read_text()
    (OUT / 'assets' / 'bloki-shopify.css').write_text(SHOP_CSS)

    (OUT / 'layout' / 'theme.liquid').write_text(LAYOUT)
    (OUT / 'snippets' / 'bloki-footer.liquid').write_text(FOOTER)

    # landings
    for slug, over in AVATARES.items():
        a = build.merge(build.BASE, over)
        body = to_liquid(build.render(slug, a))
        (OUT / 'sections' / f'bloki-{slug}.liquid').write_text(section(f'Landing {a["avatar"]}'[:25], body))
        if slug != 'general':
            (OUT / 'templates' / f'page.{slug}.json').write_text(tpl(f'bloki-{slug}'))
    (OUT / 'templates' / 'index.json').write_text(tpl('bloki-general'))
    (OUT / 'templates' / 'product.json').write_text(tpl('bloki-general'))

    # páginas simples
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
        (OUT / 'sections' / f'plain-{name}.liquid').write_text(section(f'Página {name}'[:25], PLAIN % html))
        (OUT / 'templates' / f'{name}.json').write_text(tpl(f'plain-{name}'))
    (OUT / 'layout' / 'password.liquid').write_text(LAYOUT)
    (OUT / 'templates' / 'gift_card.liquid').write_text("{% layout none %}<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><title>Tarjeta de regalo</title>{{ content_for_header }}</head><body><h1>{{ gift_card.balance | money }}</h1><p>{{ gift_card.code }}</p></body></html>")
    for c in ['login', 'register', 'account', 'order', 'addresses', 'activate_account', 'reset_password']:
        (OUT / 'templates' / 'customers' / f'{c}.liquid').write_text("<main class=\"plain\"><div class=\"wrap\"><h1>Cuenta</h1><p class=\"rte\">Para dudas con tu pedido, escríbenos.</p></div></main>")

    (OUT / 'config' / 'settings_schema.json').write_text(json.dumps([{'name': 'theme_info', 'theme_name': 'Bloki', 'theme_version': '1.0.0', 'theme_author': 'LA REAL', 'theme_documentation_url': 'https://juanfelareal.github.io/bloki-panel/', 'theme_support_url': 'https://juanfelareal.github.io/bloki-panel/'}], indent=2))
    (OUT / 'config' / 'settings_data.json').write_text(json.dumps({'current': {}}, indent=2))
    (OUT / 'locales' / 'es.default.json').write_text(json.dumps({'general': {'title': 'Bloki'}}, indent=2))
    print(f'  ✓ tema en {OUT}')

if __name__ == '__main__':
    main()
