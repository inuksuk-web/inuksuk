# Inuksuk

Motor de webs estáticas modulares. Cada página de la web es un módulo (inicio, blog, tienda, galería, contacto…) y un único archivo de configuración, `inuksuk.yml`, con una línea por módulo, decide qué web se genera.

El nombre viene de los *inuksuit*, los hitos de piedras apiladas que levantan los inuit: piezas sencillas que, combinadas, forman una señal reconocible en el paisaje.

## Cómo funciona

1. Cada web tiene su `inuksuk.yml` con los datos del sitio y la lista de módulos.
2. El generador valida cada módulo frente a su `modulo.yml`.
3. Cada módulo se renderiza con su plantilla Jinja2 dentro del esqueleto común (`base/base.html`).
4. El CSS base y el de los módulos incluidos se unen en un único `estilos.css`.
5. El resultado es HTML estático listo para GitHub Pages.

## Uso

```bash
pip install -r requirements.txt
python generador/construir.py --config ejemplo/inuksuk.yml --salida _site
```

Abre `_site/index.html` en el navegador para ver el resultado.

## Módulos disponibles

| Módulo | Estado | Descripción |
|---|---|---|
| `inicio` | disponible | Portada con título, imagen, texto y botón |
| `galeria` | pendiente (H3) | Galería de imágenes desde una carpeta de Drive |
| `blog` | pendiente (H4) | Entradas en Markdown |
| `contacto` | pendiente (H4) | Formulario de Google Forms |
| `tienda` | pendiente (H4) | Catálogo con enlace de pago o contacto |

## Documentación

- [Convenciones](CONVENCIONES.md): estructura, CSS, formato de `modulo.yml` e `inuksuk.yml`.

## Webs que usan Inuksuk

- [figuralba](https://github.com/inuksuk-web/figuralba)
- [lgdk](https://github.com/inuksuk-web/lgdk)
- [tierras-llanas](https://github.com/inuksuk-web/tierras-llanas)
