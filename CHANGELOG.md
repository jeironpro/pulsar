# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado sigue [SemVer](https://semver.org/lang/spec/v2.0.0.html).

## [Sin publicar]

### Modificado — **BREAKING** (será `2.0.0`)

- Contrato de datos en inglés: `tipo/atributos/hijos` → `type/attributes/children`
- Validador: los hijos se emparejan por `type` en lugar de por posición; se exige al menos uno por tipo declarado y se rechazan tipos de hijo no declarados
- Claves de esquema en inglés: `obligatorio/items_tipo/estricto` → `required/items_type/strict`
- Mensajes del parser, validador y CLI en inglés (`Line 4: unclosed block(s)`, `Dump file created at:`, …)
- Versión única centralizada en `pulsar.__version__`; `pyproject.toml` la lee dinámicamente
- Normalización de estilo con ruff (lint + format) y validación de assets locales referenciados por la landing en CI
- README alineado con la implementación real: EBNF sin secciones `_meta`/`data` y con objetos/comentarios/negativos, tokens reales del lexer, `kind` `object` en `ValueNode` y sección CLI con `argparse`

## [1.0.0] - 2026-08-22

### Añadido

- Parser PULSAR completo: lexer → AST → builder con reporte de línea/columna (`pulsar.py`)
- CLI `psr` con comandos `parse`, `dump`, `validate` y `version`
- Serializador con round-trip fiel y esquemas declarables en JSON o en el propio `.psr`
- Suite de pruebas unitarias (90 tests) y empaquetado como `pulsar-psr`
- Landing page publicada en GitHub Pages: hero parallax cósmico (GSAP), playground con el parser real vía Pyodide, terminal CLI animada (Anime.js), carrusel de casos de uso (Swiper), tooltips (Floating UI)
- Infraestructura: CI con matriz Python 3.10–3.14, Dockerfile multi-stage publicado en GHCR, workflow de release automático (tag `v*` → GitHub Release con sdist/wheel), despliegue automático de Pages

### Corregido

- Round-trip de serialización: strings ambiguos (`"42"`, `"true"`, `"a | b"`) se citan para no perder tipo; detección de comillas ya no es codiciosa
- Líneas vacías y marcadores `::` dentro de bloques multilínea se preservan literalmente
- Validador: reporta hijos faltantes según el schema y añade modo estricto opt-in contra atributos no declarados
- Playground: ejemplo *Contacts* tenía un bloque sin cerrar; módulo compartido `PSRHl` omitido por `.gitignore` (`lib/`) nunca llegaba a producción

[1.0.0]: https://github.com/jeironpro/pulsar/releases/tag/v1.0.0
