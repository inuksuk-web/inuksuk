# Convenciones de Inuksuk

## Estructura del motor

```
inuksuk/
├── generador/construir.py   # el generador
├── base/
│   ├── base.html            # esqueleto común: cabecera, menú y pie
│   └── base.css             # variables de tema y estilos comunes
├── modulos/
│   └── <nombre>/
│       ├── modulo.yml       # descripción y parámetros admitidos
│       ├── plantilla.html   # fragmento Jinja2 con el contenido de la página
│       └── estilo.css       # estilos del módulo (opcional)
└── ejemplo/inuksuk.yml      # configuración de ejemplo
```

## Nombres de módulo

- En minúsculas, sin tildes ni espacios: `inicio`, `galeria`, `blog`, `tienda`, `contacto`.
- El nombre de la carpeta es el nombre que se usa en `inuksuk.yml`.

## CSS

- Cada módulo escribe todas sus reglas con el prefijo `.mod-<nombre>` (estilo BEM: `.mod-inicio__titulo`, `.mod-inicio__boton`).
- El `<body>` de cada página lleva la clase `mod-<nombre>` del módulo que la genera.
- Los colores, fuentes y espacios se toman de las variables de `base.css` (`var(--color-primario)`…). No se escriben colores fijos en los módulos.
- Al compilar, `base.css`, el bloque de tema de la web y el `estilo.css` de cada módulo incluido se unen en un único `estilos.css`, en el orden de la configuración. Los módulos que no se usan no aportan CSS.

## modulo.yml

```yaml
nombre: inicio
descripcion: Frase que explica qué hace el módulo.
menu: Inicio                 # texto por defecto en el menú

parametros:
  titulo:
    tipo: texto              # texto | entero | booleano | lista | diccionario | medio
    obligatorio: true
    descripcion: Título principal.
  columnas:
    tipo: entero
    defecto: 3
  estilo:
    tipo: texto
    opciones: [claro, oscuro]
```

- `tipo: medio` acepta `drive:ID`, una URL o una ruta relativa; el generador lo convierte en URL.
- Todos los módulos admiten además `menu` (texto del menú), `ruta` (carpeta de la página) y `oculto` (no aparece en el menú).
- Un parámetro desconocido, un tipo incorrecto o la falta de uno obligatorio detienen la compilación con un mensaje claro.

## inuksuk.yml (configuración de cada web)

```yaml
sitio:
  nombre: Figuralba
  idioma: es
  tema: {color_primario: "#7a3db8"}

modulos:
  - inicio:  {titulo: "Bienvenidos"}
  - galeria: {carpeta: "drive:1XyZ...", columnas: 3}
```

- Una línea por módulo, con sus parámetros entre llaves.
- El orden de la lista es el orden del menú; el primer módulo es la portada.
- Las claves de `tema` se convierten en variables CSS: `color_primario` → `--color-primario`.
- Una carpeta `estatico/` junto a `inuksuk.yml` se copia tal cual a la web (favicon, imágenes propias…).

## Rutas

- La portada se genera en `index.html`; el resto en `<ruta>/index.html`.
- Todos los enlaces son relativos, para que la web funcione igual en un dominio propio que en `usuario.github.io/repositorio/`.
