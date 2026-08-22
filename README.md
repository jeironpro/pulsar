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
* Sensible a mayúsculas en claves (`tipo`, `atributos`, `hijos`)

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
psr_file        = meta_section , data_section ;

meta_section    = "_meta" , block ;

data_section    = "data" , block ;

block           = block_start , { statement } , block_end ;

block_start     = "->" , WS , identifier , EOL ;
block_end       = "<-" , EOL ;

statement       = attribute | block ;

attribute       = identifier , WS , ">>" , WS , value , EOL ;

value           = list | boolean | number | string | multiline ;

list            = value , { WS , "|" , WS , value } ;

boolean         = "true" | "false" ;

number          = int | float ;
int             = digit , { digit } ;
float           = digit , { digit } , "." , digit , { digit } ;

string          = quoted_string | bare_string ;
quoted_string   = '"' , { char } , '"' ;
bare_string     = identifier ;

multiline       = "<<" , EOL , { multiline_char } , ">>" ;

identifier      = letter , { letter | digit | "-" | "_" } ;

letter          = "a"…"z" | "A"…"Z" ;
digit           = "0"…"9" ;

char            = ? any character except '"' ? ;
multiline_char  = ? any character except '>>' ? ;

WS              = { " " | "\t" } ;
EOL             = "\n" | "\r\n" ;
```

---

## 3. Lexer (Tokenización)

El **lexer** es responsable de convertir el texto plano de un archivo `.psr` en una secuencia ordenada de *tokens*. El parser **nunca** trabaja con texto crudo, solo con tokens.

### 3.1 Objetivos del lexer

* Ignorar espacios irrelevantes y líneas vacías
* Detectar errores léxicos temprano
* Producir tokens simples, predecibles y serializables
* No aplicar lógica semántica (eso es trabajo del parser)

---

### 3.2 Tipos de tokens

| Token               | Descripción                 | Ejemplo               |
| ------------------- | --------------------------- | --------------------- |
| `BLOCK_START`       | Inicio de bloque            | `-> user`             |
| `BLOCK_END`         | Fin de bloque               | `<-`                  |
| `IDENTIFIER`        | Nombre de bloque o atributo | `user`, `age`         |
| `ATTR_ASSIGN`       | Operador de atributo        | `>>`                  |
| `LIST_SEPARATOR`    | Separador de lista          | <code>\`\|\`</code>   |
| `BOOLEAN`           | Booleano literal            | `true`, `false`       |
| `NUMBER`            | Entero o decimal            | `30`, `3.14`          |
| `STRING`            | String simple o quoted      | `Juan`, `"hola"`      |
| `MULTILINE_START`   | Inicio multilinea           | `<<`                  |
| `MULTILINE_END`     | Fin multilinea              | `>>`                  |
| `MULTILINE_CONTENT` | Contenido literal           | texto libre           |
| `EOL`               | Fin de línea                | —                     |
| `EOF`               | Fin de archivo              | —                     |

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
Token = {
    "type": "IDENTIFIER",
    "value": "user",
    "line": 12,
    "column": 5
}
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

Salida (simplificada):

```
BLOCK_START(user)
IDENTIFIER(name) ATTR_ASSIGN STRING(Juan)
IDENTIFIER(skills) ATTR_ASSIGN STRING(python) LIST_SEPARATOR STRING(go)
BLOCK_END
EOF
```

Este lexer es la base del **parser AST** del Paso 4.

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
    "kind": "int" | "float" | "bool" | "string" | "list",
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
3. Resolver `ValueNode` a tipos Python (`str`, `int`, `float`, `bool`, `list`)

```python
def build_block(block_node):
    # Construye un dict Python a partir del AST
    block_dict = {
        'tipo': block_node.name,
        'atributos': {},
        'hijos': []
    }

    for attr in block_node.attributes:
        block_dict['atributos'][attr.key] = resolve_value(attr.value)

    for child in block_node.children:
        block_dict['hijos'].append(build_block(child))

    return block_dict


def resolve_value(value_node):
    if value_node.kind == 'list':
        return [resolve_value(v) for v in value_node.value]
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
Usage: psr [OPTIONS] COMMAND [ARGS]...

Commands:
  parse      Parsear un archivo .psr y mostrar AST
  validate   Validar un archivo .psr contra un schema
  dump       Serializar un objeto Python a .psr
  version    Mostrar versión de PULSAR
```

Opciones globales:

* `--file, -f` → archivo de entrada
* `--schema, -s` → archivo schema (JSON / PSR)
* `--output, -o` → archivo de salida (para dump)
* `--verbose, -v` → modo detallado

---

## 6.2 Comandos principales

### 6.2.1 Parsear

```bash
psr parse -f users.psr
```

* Muestra AST o errores léxicos/sintácticos
* Salida: JSON por defecto

### 6.2.2 Validar

```bash
psr validate -f users.psr -s user_schema.json
```

* Usa la estructura Python generada por el Builder
* Devuelve errores de schema o confirmación de validez

### 6.2.3 Serializar / Dump

```bash
psr dump -f users.psr -o out.psr
```

* Convierte dict/list Python a texto PULSAR
* Puede ser usada para round-trip (parse → dump)

### 6.2.4 Mostrar versión

```bash
psr version
```

* Muestra versión actual (1.0)

---

## 6.3 Implementación mínima Python

```python
# ----------------------------
# CLI manual
# ----------------------------
def main():
    if len(sys.argv) < 2:
        print("Uso: python pulsar.py [parse|dump|validate|version] opciones")
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]
    opts = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i+1].startswith("--"):
                opts[key] = args[i+1]
                i += 1
            else:
                opts[key] = True
        elif args[i].startswith("-"):
            key = args[i][1:]
            if i + 1 < len(args) and not args[i+1].startswith("-"):
                opts[key] = args[i+1]
                i += 1
            else:
                opts[key] = True
        i += 1

    try:
        if cmd == "version":
            print("PULSAR CLI v2.0.0")
            return

        elif cmd == "parse":
            file_path = opts.get("file") or opts.get("f")
            if not file_path: raise ValueError("Debe indicar --file o -f")
            ast = load_psr(file_path)
            print(json.dumps(build_document(ast), indent=4))

        elif cmd == "dump":
            file_path = opts.get("file") or opts.get("f")
            output = opts.get("output") or opts.get("o")
            if not file_path: raise ValueError("Debe indicar --file o -f")
            ast = load_psr(file_path)
            data = build_document(ast)
            dump_psr(data, output)
            print(f"Dump file created at: {output or 'stdout'}")

        elif cmd == "validate":
            file_path = opts.get("file") or opts.get("f")
            schema_path = opts.get("schema") or opts.get("s")
            if not file_path or not schema_path:
                raise ValueError("Debe indicar --file/-f y --schema/-s")
            ast = load_psr(file_path)
            data = build_document(ast)
            with open(schema_path) as f:
                sch = json.load(f)
            errs = validate_psr(data, sch)
            if errs:
                for e in errs:
                    print("Error:", e)
            else:
                print("File valid ✅")
        else:
            print(f"Comando desconocido: {cmd}")

    except Exception as e:
        print("Error:", e)

if __name__=="__main__":
    main()
```

---

PULSAR 1.0