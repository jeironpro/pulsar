# PULSAR (.psr) — Especificación del formato

[![CI](https://github.com/jeironpro/pulsar/actions/workflows/ci.yml/badge.svg)](https://github.com/jeironpro/pulsar/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Lib](https://img.shields.io/badge/pulsar--psr-v2.0.0-gold)](pyproject.toml)

> **Estado:** Draft estable  
> **Librería:** `pulsar-psr` v2.0.0 — desde v2.0 la representación en memoria usa claves en inglés: `type`, `attributes`, `children` (el formato `.psr` no cambia).  
> **Propósito:** Formato de datos estructurados, legible por humanos, jerárquico y extensible, diseñado desde cero (no derivado de JSON/YAML/TOML).  
> **Contribuciones:** leer [CONTRIBUTING](CONTRIBUTING.md).  
> **Desarrollo:** Este formato se desarrollo por la idea de un tipo de archivo diferente a los demas y facil de leer, se creo con la ayuda del modelo/IA ChatGPT.
---

## Instalación

PULSAR se distribuye como paquete Python en PyPI: `pulsar-psr` (Python ≥ 3.10, **sin dependencias**).

```bash
pip install pulsar-psr
```

Instala la librería y el comando `psr`:

```bash
psr version                        # muestra la versión del CLI
psr parse -f datos.psr             # parsea y muestra JSON
psr validate -f datos.psr -s esquema.json   # valida contra un schema
```

Uso como librería:

```python
from pulsar import load_psr, build_document, validate_psr

ast = load_psr("datos.psr")
data = build_document(ast)          # list[dict] con type / attributes / children
```

---

## Filosofía

PULSAR nace con estos principios:

* **Estructura explícita**: todo nodo declara su `tipo`.
* **Jerarquía nativa**: relaciones padre–hijo son de primer nivel.
* **Datos tipados pero flexibles**: atributos simples, listas y objetos.
* **Serialización determinista**: el mismo `.psr` siempre produce la misma estructura.
* **No ambigüedad**: una sintaxis, una interpretación.

PULSAR no busca competir con JSON o YAML, sino **modelar entidades y relaciones** de forma clara.

---

## 1 Extensión y archivo

* Extensión oficial: `.psr`
* Codificación: UTF-8
* Sensible a mayúsculas en claves (`type`, `attributes`, `children`)

---

## 1.1 Modelo de datos

Un archivo `.psr` representa una **colección de nodos raíz**.

### 1.2 Nodo

Un nodo es una entidad con esta estructura conceptual:

* `type` : string (obligatorio)
* `attributes` : mapa clave–valor (opcional)
* `children` : lista de nodos (opcional)

### 1.3 Tipos de valores permitidos

* string
* integer
* float
* boolean (`true | false`)
* lista
* objeto (mapa)

---

## 1.4 Sintaxis `.psr`

### 1.4.1 Estructura general

Un archivo contiene uno o más **bloques de nodo**. Cada bloque se abre con `-> <tipo>` y se cierra con `<-`.

```
-> <tipo>
    <clave> >> <valor>
    ...

    -> <subtipo>
        ...
    <-
<-
```

---

### 1.5 Reglas sintácticas

* `-> <tipo>` inicia un bloque de nodo
* `<-` cierra el bloque actual
* `<tipo>` es un identificador sin espacios
* `>>` separa clave y valor en atributos
* `|` separa elementos en listas
* `"..."` fuerza texto (preserva strings que parecen número o booleano)
* `{ k >> v | ... }` define un objeto inline
* `<<` … `>>` captura texto multilínea literal, hasta una línea con solo `>>`
* No se usan comas
* Los bloques hijos se anidan dentro del bloque padre
* `::` inicia un comentario (todo tras `::` se ignora)

---

## 1.6 Ejemplo válido

Archivo: `users.psr`

```
:: Ejemplo de archivo PULSAR
-> user
    name >> Juan
    age >> 30
    active >> true
    skills >> python | go | rust

    -> address
        city >> Madrid
        zip >> 28000
    <-

<-
-> user
    name >> Ana
    age >> 25
    skills >> javascript | html | css
<-
```

---

## 1.7 Representación en memoria (AST)

Al parsear el ejemplo anterior, el resultado **normalizado** es:

```
[
  {
    "type": "user",
    "attributes": {
      "name": "Juan",
      "age": 30,
      "active": true,
      "skills": ["python", "go", "rust"]
    },
    "children": [
      {
        "type": "address",
        "attributes": {
          "city": "Madrid",
          "zip": 28000
        },
        "children": []
      }
    ]
  },
  {
    "type": "user",
    "attributes": {
      "name": "Ana",
      "age": 25,
      "skills": ["javascript", "html", "css"]
    },
    "children": []
  }
]
```

---

## 1.8 Schema conceptual (v1)

```
PulsarFile := Node+

Node :=
  "type": string
  "attributes"?: Map<string, Value>
  "children"?: List<Node>

Value := string | number | boolean | List<Value> | Map<string, Value>
```

---

## 1.9 Errores sintácticos

Un parser PULSAR **DEBE fallar** si:

* Falta el nombre del bloque después de `->`
* Un bloque no se cierra (`<-` faltante)
* Se usan comas como separadores
* Se repite una clave dentro de `atributos`
* Un atributo aparece fuera de un bloque
* Se encuentra un operador incompleto (`-` sin `>`, `<` sin `-`)
* Se encuentra un símbolo no reconocido

---

**PULSAR .psr — Spec oficial**

---

## 2. Gramática Formal (EBNF)

La siguiente gramática define de forma estricta la sintaxis válida de un archivo **PULSAR (.psr)**. Cualquier implementación oficial debe cumplirla.

```
psr_file        = { block } , EOF ;

block           = block_start , { statement | comment } , block_end ;

block_start     = "->" , WS , identifier , EOL ;
block_end       = "<-" , EOL ;

statement       = attribute | block ;

attribute       = identifier , WS , ">>" , WS , value , EOL ;

value           = list | object | boolean | number | string | multiline ;

list            = value , { WS , "|" , WS , value } ;

object          = "{" , WS , [ pair , { WS , "|" , WS , pair } ] , WS , "}" ;
pair            = identifier , WS , ">>" , WS , value ;

boolean         = "true" | "false" ;

number          = [ "-" ] , ( int | float ) ;
int             = digit , { digit } ;
float           = digit , { digit } , "." , digit , { digit } ;

string          = quoted_string | bare_string ;
quoted_string   = '"' , { char } , '"' ;
bare_string     = { char_no_comma } ;

multiline       = "<<" , EOL , { multiline_char } , ">>" ;

comment         = "::" , { char } , EOL ;

identifier      = letter , { letter | digit | "-" | "_" } ;

letter          = "a"…"z" | "A"…"Z" ;
digit           = "0"…"9" ;

char            = ? any character except '"' ? ;
char_no_comma   = ? any character except ',' ? ;
multiline_char  = ? any character except '>>' ? ;

WS              = { " " | "\t" } ;
EOL             = "\n" | "\r\n" ;
EOF             = ? end of file ? ;
```

Notas de implementación (coinciden con `pulsar.py`):

* Un archivo es una **colección de nodos raíz**: no existen secciones `_meta`/`data`.
* `bare_string` acepta espacios y la mayoría de caracteres (`Juan Perez`, `postgres://localhost/app`); las comas están prohibidas.
* Un número con cero a la izquierda y más de un dígito es **string** (`007` → `"007"`); con punto decimal sí es float (`007.5` → 7.5).
* `quoted_string` no admite comillas dobles internas; el serializador convierte `"` → `'` al citar.

---

## 3. Lexer (Tokenización)

El **lexer** es responsable de convertir el texto plano de un archivo `.psr` en una secuencia ordenada de *tokens*. El parser **nunca** trabaja con texto crudo, solo con tokens.

### 3.1 Objetivos del lexer

* Ignorar espacios irrelevantes y líneas vacías
* Detectar errores léxicos temprano
* Producir tokens simples, predecibles y serializables
* No aplicar lógica semántica (eso es trabajo del parser)

---

### 3.2 Tipos de tokens (implementación real)

| Token         | Descripción                       | Ejemplo           |
| ------------- | --------------------------------- | ----------------- |
| `BLOCK_START` | Inicio de bloque                  | `-> user`         |
| `BLOCK_END`   | Fin de bloque                     | `<-`              |
| `ATTRIBUTE`   | Atributo: clave + valor crudo     | `name >> Juan`    |
| `EOF`         | Fin de archivo                    | —                 |

> La implementación real (`lex_psr`) emite estos 4 tokens. A diferencia de un modelo teórico, el lexer **no** etiqueta literales (`NUMBER`, `BOOLEAN`, `STRING`, `MULTILINE_*`…): entrega el valor como **texto crudo** en el token `ATTRIBUTE` y la inferencia de tipos ocurre en el builder (§5).

---

### 3.3 Reglas léxicas

* El lexer es **line-based** excepto en `multiline`.
* Los comentarios comienzan con `::` y se ignoran completamente.
* El orden de precedencia es crítico:

  1. Multiline
  2. Operadores (`->`, `<-`, `>>`, `|`)
  3. Literales
  4. Identificadores

---

### 3.4 Representación de un token

```python
BLOCK_START = {"type": "BLOCK_START", "value": "user", "line": 1, "column": 2}
ATTRIBUTE   = {"type": "ATTRIBUTE", "key": "name", "value": "Juan", "line": 2, "column": 6}
BLOCK_END   = {"type": "BLOCK_END", "value": "<-", "line": 3, "column": 1}
EOF         = {"type": "EOF", "value": "", "line": 4, "column": 0}
```

---

### 3.5 Flujo del lexer

1. Leer archivo completo
2. Iterar carácter por carácter
3. Emitir tokens
4. Detectar errores léxicos
5. Añadir token `EOF`

---

### 3.6 Errores léxicos

El lexer debe lanzar `PSRLexError` cuando:

* Encuentra un símbolo inválido
* Un multiline no se cierra
* Hay operadores incompletos

---

### 3.7 Ejemplo

Entrada:

```
-> user
    name >> Juan
    skills >> python | go
<-
```

Salida real del lexer (`lex_psr`):

```
BLOCK_START(user)
ATTRIBUTE(name, Juan)
ATTRIBUTE(skills, python | go)
BLOCK_END
EOF
```

Los tipos (`int`, `bool`, listas, objetos…) se resuelven después, en el builder. Este lexer es la base del **parser AST** del Paso 4.

---

# 4. Parser y AST oficial de PULSAR

## Objetivo

Transformar la secuencia de tokens producida por el lexer en una **estructura sintáctica (AST)** que represente fielmente el documento `.psr`, separando **estructura** de **validación**.

El parser **NO** valida tipos ni schemas, solo:

* orden
* jerarquía
* coherencia sintáctica

---

## 4.1 AST (Abstract Syntax Tree)

### 4.1.1 Nodo base

Todos los nodos comparten:

* `type`: tipo de nodo
* `lineno`: línea de origen

---

### 4.1.2 BlockNode

Representa un bloque `-> tipo ... <-`

```python
BlockNode = {
    "type": "block",
    "name": "user",
    "attributes": [AttributeNode, ...],
    "children": [BlockNode, ...],
    "lineno": 1
}
```

Reglas:

* Puede contener atributos y otros bloques
* El orden se preserva

---

### 4.1.3 AttributeNode

Representa una línea `clave >> valor`

```python
AttributeNode = {
    "type": "attribute",
    "key": "age",
    "value": ValueNode,
    "lineno": 3
}
```

---

### 4.1.5 ValueNode

```python
ValueNode = {
    "type": "value",
    "raw": "30",
    "kind": "int" | "float" | "bool" | "string" | "list" | "object",
    "value": 30
}
```

Notas:

* `kind` puede ser inferido o forzado en futuras extensiones
* `raw` conserva el valor original

---

## 4.2 Gramática aplicada (parser real)

```ebnf
Document    ::= Block*
Block       ::= BLOCK_START Attribute* Block* BLOCK_END
Attribute   ::= IDENTIFIER ATTR_OP Value
Value       ::= LITERAL | LIST
```

---

## 4.3 Algoritmo del Parser (stack-based)

```python
def parse(tokens):
    stack = []
    ast = []

    for token in tokens:
        if token.type == BLOCK_START:
            node = BlockNode(token)
            if stack:
                stack[-1].children.append(node)
            else:
                ast.append(node)
            stack.append(node)

        elif token.type == BLOCK_END:
            if not stack:
                raise ParseError("Cierre sin apertura", token.lineno)
            stack.pop()

        elif token.type == ATTRIBUTE:
            if not stack:
                raise ParseError("Atributo fuera de bloque", token.lineno)
            stack[-1].attributes.append(AttributeNode(token))

    if stack:
        raise ParseError("Bloque(s) sin cerrar")

    return ast
```

---

## 4.4 Errores sintácticos detectables

* `BLOCK_END` sin `BLOCK_START`
* Atributo fuera de bloque
* EOF con bloques abiertos
* Tokens inválidos por contexto

---

## 4.5 Resultado del Parser

El parser devuelve un **AST limpio**, que luego se transforma a:

* estructura Python (`dict/list`)
* JSON
* Validación por schema
* Serialización `.psr`

---

## 4.6 Separación de responsabilidades (clave)

| Capa       | Responsabilidad      |
| ---------- | -------------------- |
| Lexer      | Caracteres → Tokens  |
| Parser     | Tokens → AST         |
| Builder    | AST → objetos Python |
| Validator  | Reglas de negocio    |
| Serializer | Python → `.psr`      |

---

# 5. Builder y Normalización de PULSAR

## Objetivo

Convertir el AST producido por el parser en una **estructura de objetos Python lista para uso**, validación y serialización.

* Preservar jerarquía
* Inferir tipos básicos
* Normalizar listas y valores
* Preparar para schema validator

---

## 5.1 Builder Conceptual

Funciona en tres pasos:

1. Recorrer el AST recursivamente
2. Transformar `BlockNode` y `AttributeNode` en diccionarios Python
3. Resolver `ValueNode` a tipos Python (`str`, `int`, `float`, `bool`, `list`, `dict`)

```python
def build_block(block_node):
    # Construye un dict Python a partir del AST
    block_dict = {
        'type': block_node.name,
        'attributes': {},
        'children': []
    }

    for attr in block_node.attributes:
        block_dict['attributes'][attr.key] = resolve_value(attr.value)

    for child in block_node.children:
        block_dict['children'].append(build_block(child))

    return block_dict


def resolve_value(value_node):
    if value_node.kind == 'list':
        return [resolve_value(v) for v in value_node.value]
    elif value_node.kind == 'object':
        return {k: resolve_value(v) for k, v in value_node.value.items()}
    elif value_node.kind == 'int':
        return int(value_node.value)
    elif value_node.kind == 'float':
        return float(value_node.value)
    elif value_node.kind == 'bool':
        return bool(value_node.value)
    else:
        return str(value_node.value)
```

---

## 5.2 Normalización de listas

* Listas de un solo elemento → siempre lista, no scalar
* Espacios y separadores → eliminados o estandarizados
* Lista vacía → `[]`

Ejemplo:

```
skills >> python | go | rust
```

Se transforma a:

```python
['python', 'go', 'rust']
```

---

## 5.3 Transformación completa de documento

```python
def build_document(ast):
    return [build_block(node) for node in ast]
```

Resultado final: **lista de bloques Python**, lista para:

* Validación por schema
* Serialización `.psr`
* Conversión a JSON o YAML

---

## 5.4 Beneficios del Builder

* Separa **AST de uso real**
* Facilita **round-trip parsing + dump**
* Permite extensiones futuras:

  * Tipado avanzado
  * Validación de listas y sub-bloques
  * Export a otros formatos

---

# 6. CLI e Integración Final de PULSAR

## Objetivo

Proveer una **herramienta de línea de comandos** para:

* Parsear archivos `.psr`
* Validar contra schemas
* Serializar / deserializar
* Mostrar errores de manera clara

Esto permite usar PULSAR fuera de Python directamente en proyectos y pipelines.

---

## 6.1 Estructura del CLI

```
Usage: psr [-h] [-V] {parse,dump,validate,version} ...

Commands:
  parse      Parse a .psr file and print JSON
  dump       Re-serialize a .psr file (round-trip)
  validate   Validate a .psr file against a schema
  version    Show version
```

Opciones (por subcomando, construidas con `argparse`):

* `-f, --file` → archivo de entrada (obligatorio en `parse`, `dump` y `validate`)
* `-s, --schema` → archivo schema (JSON o `.psr`; solo `validate`)
* `-o, --output` → archivo de salida (solo `dump`; stdout si se omite)
* `-V, --version` → muestra la versión del CLI (global)
* `-h, --help` → ayuda

---

## 6.2 Comandos principales

### 6.2.1 Parsear

```bash
psr parse -f users.psr
```

* Muestra la estructura o errores léxicos/sintácticos
* Salida: JSON indentado con 4 espacios (`json.dumps(..., indent=4, ensure_ascii=False)`)

### 6.2.2 Validar

```bash
psr validate -f users.psr -s user_schema.json
```

* Usa la estructura Python generada por el Builder
* Los hijos se emparejan por `type` (no por posición): se exige al menos un hijo por tipo declarado y se rechazan tipos de hijo no declarados
* Si es válido: imprime `File valid ✅`
* Si hay errores: imprime `Error: ...` en stderr y termina con código de salida 1

### 6.2.3 Serializar / Dump

```bash
psr dump -f users.psr -o out.psr
```

* Lee el archivo `.psr`, lo parsea y lo re-serializa (round-trip fiel)
* Escribe en `-o` o en stdout si se omite; con `-o` imprime `Dump file created at: <archivo>`

### 6.2.4 Mostrar versión

```bash
psr version
```

* Muestra la versión actual: `PULSAR CLI v2.0.0`

---

## 6.3 Implementación real

El CLI vive en `pulsar.py` y está construido con `argparse` y subcomandos:

* Entry points: consola `psr` (definido en `[project.scripts]` de `pyproject.toml`) y `python -m pulsar` (vía `__main__.py`).
* `main()` define los subcomandos `parse`, `dump`, `validate` y `version` con sus opciones por subcomando (§6.1).
* Los errores esperados (`PSRLexError`, `PSRParseError`, `OSError`, `json.JSONDecodeError`, `ValueError`) se capturan y muestran como `Error: ...` en stderr, con código de salida 1.
* La versión es única y centralizada en `pulsar.__version__` (leída dinámicamente por `pyproject.toml`).
---

## Desarrollo y release

* **Contribuciones:** ver [CONTRIBUTING](CONTRIBUTING.md). Incluye cómo mantener sincronizada la copia del parser en `landing/pulsar.py` con `pulsar.py` (el job `Parser sync (landing)` del CI falla si divergen).
* **CI (`ci.yml`):** ruff, pre-commit, tests en Python 3.10–3.14, sincronía del parser con la landing, y `twine check --strict` sobre el sdist y el wheel.
* **Release:** al crear un tag `v*`, `release.yml` ejecuta los tests, construye sdist + wheel, crea el GitHub Release con los artefactos y publica el paquete en **PyPI** mediante **trusted publishing (OIDC)**, sin tokens en secrets. Requiere registrar una sola vez el publisher en PyPI (owner `jeironpro`, repositorio `pulsar`, workflow `release.yml`).

---

PULSAR 2.0.0
