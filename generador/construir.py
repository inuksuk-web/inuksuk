#!/usr/bin/env python3
"""
Inuksuk — generador de webs estáticas modulares.

Lee la configuración de una web (inuksuk.yml), valida cada módulo frente a su
modulo.yml, genera una página HTML por módulo y une en un único estilos.css
el CSS base y el de los módulos incluidos.

Uso:
    python generador/construir.py --config ejemplo/inuksuk.yml --salida _site
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

RAIZ_MOTOR = Path(__file__).resolve().parent.parent

# Parámetros que admite cualquier módulo, además de los de su modulo.yml.
PARAMETROS_COMUNES = {
    "menu": {"tipo": "texto", "descripcion": "Texto del enlace en el menú."},
    "ruta": {"tipo": "texto", "descripcion": "Carpeta de la página (por defecto, el nombre del módulo)."},
    "oculto": {"tipo": "booleano", "defecto": False, "descripcion": "Genera la página pero no la muestra en el menú."},
}

TIPOS = {
    "texto": str,
    "entero": int,
    "booleano": bool,
    "lista": list,
    "diccionario": dict,
    "medio": str,
}


class ErrorConfiguracion(Exception):
    """Error en inuksuk.yml o en un modulo.yml."""


@dataclass
class Modulo:
    nombre: str
    definicion: dict
    parametros: dict
    carpeta: Path
    ruta: str = ""
    archivo: str = ""
    profundidad: int = 0
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lectura de archivos
# ---------------------------------------------------------------------------

def leer_yaml(ruta: Path) -> dict:
    try:
        with ruta.open(encoding="utf-8") as f:
            datos = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise ErrorConfiguracion(f"No existe el archivo {ruta}")
    except yaml.YAMLError as e:
        raise ErrorConfiguracion(f"YAML no válido en {ruta}:\n{e}")
    if not isinstance(datos, dict):
        raise ErrorConfiguracion(f"{ruta} debe contener un diccionario en su nivel superior")
    return datos


# ---------------------------------------------------------------------------
# Medios (provisional hasta H3, issue #11)
# ---------------------------------------------------------------------------

def resolver_medio(valor: str | None) -> str | None:
    """Convierte una referencia de medio en una URL.

    Único punto del motor que sabe cómo se sirven los medios. Formatos:
      - drive:ID  → imagen pública de Google Drive
      - http(s):// o ruta relativa → se devuelve tal cual
    """
    if not valor:
        return valor
    if valor.startswith("drive:"):
        identificador = valor.split(":", 1)[1].strip()
        # Método no documentado por Google; puede cambiar. Ver issue #11.
        return f"https://lh3.googleusercontent.com/d/{identificador}"
    return valor


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

def normalizar_lista_modulos(config: dict) -> list[tuple[str, dict]]:
    """Convierte la lista 'modulos' en pares (nombre, parámetros).

    Admite tanto '- inicio: {titulo: ...}' como '- inicio' sin parámetros.
    """
    lista = config.get("modulos")
    if not isinstance(lista, list) or not lista:
        raise ErrorConfiguracion("La configuración debe tener una lista 'modulos' con al menos un módulo")

    pares = []
    for i, entrada in enumerate(lista, start=1):
        if isinstance(entrada, str):
            pares.append((entrada, {}))
        elif isinstance(entrada, dict) and len(entrada) == 1:
            nombre, params = next(iter(entrada.items()))
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise ErrorConfiguracion(f"Módulo {i} ('{nombre}'): los parámetros deben ir entre llaves {{...}}")
            pares.append((nombre, params))
        else:
            raise ErrorConfiguracion(f"Módulo {i}: cada línea debe tener la forma '- nombre: {{parametros}}'")
    return pares


def validar_parametros(nombre: str, definicion: dict, params: dict) -> dict:
    esquema = {**PARAMETROS_COMUNES, **(definicion.get("parametros") or {})}
    errores = []

    for clave in params:
        if clave not in esquema:
            admitidos = ", ".join(sorted(esquema))
            errores.append(f"parámetro desconocido '{clave}' (admitidos: {admitidos})")

    resultado = {}
    for clave, regla in esquema.items():
        if clave in params:
            valor = params[clave]
            tipo = regla.get("tipo", "texto")
            esperado = TIPOS.get(tipo)
            if esperado is None:
                errores.append(f"tipo '{tipo}' no reconocido en modulo.yml para '{clave}'")
            elif tipo == "entero" and isinstance(valor, bool):
                errores.append(f"'{clave}' debe ser {tipo}")
            elif not isinstance(valor, esperado):
                errores.append(f"'{clave}' debe ser {tipo}, no {type(valor).__name__}")
            elif "opciones" in regla and valor not in regla["opciones"]:
                errores.append(f"'{clave}' debe ser uno de {regla['opciones']}")
            if tipo == "medio" and isinstance(valor, str):
                valor = resolver_medio(valor)
            resultado[clave] = valor
        elif regla.get("obligatorio"):
            errores.append(f"falta el parámetro obligatorio '{clave}'")
        else:
            resultado[clave] = regla.get("defecto")

    if errores:
        detalle = "\n  - ".join(errores)
        raise ErrorConfiguracion(f"Módulo '{nombre}':\n  - {detalle}")
    return resultado


def cargar_modulos(config: dict, motor: Path) -> list[Modulo]:
    modulos = []
    rutas_usadas = set()

    for posicion, (nombre, params) in enumerate(normalizar_lista_modulos(config)):
        carpeta = motor / "modulos" / nombre
        if not carpeta.is_dir():
            disponibles = ", ".join(sorted(p.name for p in (motor / "modulos").iterdir() if p.is_dir()))
            raise ErrorConfiguracion(f"No existe el módulo '{nombre}' (disponibles: {disponibles})")

        definicion = leer_yaml(carpeta / "modulo.yml")
        valores = validar_parametros(nombre, definicion, params)

        # El primer módulo es la portada (index.html en la raíz).
        if posicion == 0:
            ruta = ""
        else:
            ruta = (valores.get("ruta") or nombre).strip("/")
        if ruta in rutas_usadas:
            raise ErrorConfiguracion(
                f"Dos módulos generan la misma página ('{ruta or 'index'}'). "
                f"Usa el parámetro 'ruta' para diferenciarlos."
            )
        rutas_usadas.add(ruta)

        modulo = Modulo(nombre=nombre, definicion=definicion, parametros=valores, carpeta=carpeta)
        modulo.ruta = ruta
        modulo.archivo = f"{ruta}/index.html" if ruta else "index.html"
        modulo.profundidad = len(ruta.split("/")) if ruta else 0
        modulos.append(modulo)

    return modulos


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def css_tema(tema: dict | None) -> str:
    """Genera un bloque :root con las variables de tema de la web."""
    if not tema:
        return ""
    lineas = [f"  --{str(k).replace('_', '-')}: {v};" for k, v in tema.items()]
    return ":root {\n" + "\n".join(lineas) + "\n}\n"


def unir_css(motor: Path, modulos: list[Modulo], tema: dict | None) -> str:
    partes = ["/* Generado por Inuksuk. No editar: se sobrescribe en cada compilación. */\n"]
    partes.append("/* ---- base ---- */\n" + (motor / "base" / "base.css").read_text(encoding="utf-8"))

    bloque_tema = css_tema(tema)
    if bloque_tema:
        partes.append("/* ---- tema de la web ---- */\n" + bloque_tema)

    vistos = set()
    for m in modulos:
        if m.nombre in vistos:
            continue
        vistos.add(m.nombre)
        css = m.carpeta / "estilo.css"
        if css.exists():
            partes.append(f"/* ---- módulo: {m.nombre} ---- */\n" + css.read_text(encoding="utf-8"))
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def prefijo(profundidad: int) -> str:
    """Ruta relativa hasta la raíz de la web (funciona en GitHub Pages de proyecto)."""
    return "../" * profundidad


def construir_menu(modulos: list[Modulo]) -> list[dict]:
    menu = []
    for m in modulos:
        if m.parametros.get("oculto"):
            continue
        titulo = m.parametros.get("menu") or m.definicion.get("menu") or m.nombre.capitalize()
        menu.append({"titulo": titulo, "ruta": m.ruta, "nombre": m.nombre})
    return menu


def crear_entorno(motor: Path) -> Environment:
    entorno = Environment(
        loader=FileSystemLoader([str(motor / "base"), str(motor / "modulos")]),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    entorno.filters["medio"] = resolver_medio
    entorno.filters["parrafos"] = lambda texto: [p.strip() for p in str(texto or "").split("\n\n") if p.strip()]
    return entorno


def construir(config_path: Path, salida: Path, motor: Path = RAIZ_MOTOR) -> list[Path]:
    config = leer_yaml(config_path)
    sitio = config.get("sitio") or {}
    if not sitio.get("nombre"):
        raise ErrorConfiguracion("Falta 'sitio.nombre' en la configuración")

    modulos = cargar_modulos(config, motor)
    menu = construir_menu(modulos)
    entorno = crear_entorno(motor)
    base = entorno.get_template("base.html")

    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)

    generados = []
    for m in modulos:
        raiz = prefijo(m.profundidad)
        contexto = {"sitio": sitio, "p": m.parametros, "raiz": raiz, "modulo": m.nombre}
        contenido = entorno.get_template(f"{m.nombre}/plantilla.html").render(**contexto)
        titulo_pagina = m.parametros.get("titulo") or m.parametros.get("menu") or m.definicion.get("menu") or m.nombre
        html = base.render(
            sitio=sitio,
            menu=menu,
            actual=m.ruta,
            raiz=raiz,
            modulo=m.nombre,
            titulo_pagina=titulo_pagina,
            es_portada=(m.ruta == ""),
            contenido=contenido,
        )
        destino = salida / m.archivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
        generados.append(destino)

    (salida / "estilos.css").write_text(unir_css(motor, modulos, sitio.get("tema")), encoding="utf-8")
    generados.append(salida / "estilos.css")

    # Evita que GitHub Pages procese el resultado con Jekyll.
    (salida / ".nojekyll").write_text("", encoding="utf-8")

    # Archivos estáticos propios de la web (carpeta 'estatico' junto a inuksuk.yml).
    estatico = config_path.parent / "estatico"
    if estatico.is_dir():
        shutil.copytree(estatico, salida, dirs_exist_ok=True)

    return generados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera una web estática a partir de inuksuk.yml")
    parser.add_argument("--config", default="inuksuk.yml", type=Path, help="Archivo de configuración de la web")
    parser.add_argument("--salida", default="_site", type=Path, help="Carpeta donde se escribe la web generada")
    parser.add_argument("--motor", default=RAIZ_MOTOR, type=Path, help="Carpeta raíz del motor Inuksuk")
    args = parser.parse_args(argv)

    try:
        generados = construir(args.config, args.salida, args.motor)
    except ErrorConfiguracion as e:
        print(f"Error de configuración: {e}", file=sys.stderr)
        return 1

    print(f"Web generada en {args.salida}/ ({len(generados)} archivos)")
    for ruta in generados:
        print(f"  {ruta.relative_to(args.salida)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
