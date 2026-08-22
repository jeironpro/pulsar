#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import sys
import argparse
from typing import List, Dict, Any, Optional, Tuple

# ----------------------------
# Excepciones
# ----------------------------
class PSRParseError(Exception):
    pass

class PSRLexError(Exception):
    pass

_MAX_DEPTH = 200

# ----------------------------
# Lexer
# ----------------------------
def _comment_end(line: str) -> int:
    in_quotes = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ':' and i + 1 < len(line) and line[i+1] == ':' and not in_quotes:
            return i
    return -1

def lex_psr(text: str) -> List[dict]:
    id_re = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
    tokens: List[dict] = []
    lines = text.splitlines()
    in_multiline = False
    multiline_key = None
    multiline_start = 0
    multiline_content = []

    for lineno, line in enumerate(lines, start=1):
        raw = line
        stripped = line.strip()

        cpos = _comment_end(stripped)
        if cpos >= 0:
            stripped = stripped[:cpos].strip()
        if not stripped:
            continue

        # multiline mode
        if in_multiline:
            if stripped == '>>':
                in_multiline = False
                content = '\n'.join(multiline_content)
                tokens.append({'type': 'ATTRIBUTE', 'key': multiline_key,
                               'value': content, 'line': multiline_start, 'column': 0})
            else:
                multiline_content.append(raw)
            continue

        if stripped.startswith('->'):
            block_name = stripped[2:].strip()
            if not block_name:
                raise PSRLexError(f'Línea {lineno}: falta el nombre del bloque después de "->"')
            if not id_re.match(block_name):
                raise PSRLexError(f'Línea {lineno}: nombre de bloque inválido -> {block_name}')
            col = raw.index('->') + 1
            tokens.append({'type':'BLOCK_START', 'value':block_name,
                           'line':lineno, 'column':col})

        elif stripped == '<-':
            col = raw.index('<-') + 1
            tokens.append({'type':'BLOCK_END', 'value':'<-',
                           'line':lineno, 'column':col})

        elif stripped.startswith('-') and not stripped.startswith('->'):
            col = raw.index('-') + 1
            raise PSRLexError(f'Línea {lineno} col {col}: operador incompleto')

        elif stripped.startswith('<') and not stripped.startswith('<-'):
            col = raw.index('<') + 1
            raise PSRLexError(f'Línea {lineno} col {col}: operador incompleto')

        elif '>>' in stripped:
            key, val = map(str.strip, stripped.split('>>', 1))
            if not key:
                raise PSRLexError(f'Línea {lineno}: falta la clave del atributo')
            if not id_re.match(key):
                raise PSRLexError(f'Línea {lineno}: nombre de atributo inválido -> {key}')

            # multiline value
            if val == '<<':
                in_multiline = True
                multiline_key = key
                multiline_start = lineno
                multiline_content = []
                continue

            if ',' in val:
                raise PSRLexError(f'Línea {lineno}: comas no permitidas (use "|" para listas)')

            col = raw.index('>>') + 1
            tokens.append({'type':'ATTRIBUTE', 'key':key, 'value':val,
                           'line':lineno, 'column':col})

        else:
            raise PSRLexError(f'Línea {lineno}: línea no reconocida -> {line}')

    if in_multiline:
        raise PSRLexError(f'Línea {multiline_start}: multiline sin cerrar')

    last_line = lineno if lines else 0
    tokens.append({'type':'EOF', 'value':'', 'line':last_line + 1, 'column':0})
    return tokens

# ----------------------------
# Parser + AST
# ----------------------------
class ValueNode:
    def __init__(self, raw: str, kind: str = 'string'):
        self.raw = raw
        self.kind = kind
        self.value = self._parse()

    def __repr__(self) -> str:
        return f'ValueNode({self.raw!r}, kind={self.kind!r}, value={self.value!r})'

    def _parse(self) -> Any:
        val = self.raw.strip()

        if (len(val) >= 2 and val[0] == '"' and val[-1] == '"'
                and '"' not in val[1:-1]):
            self.kind = 'string'
            return val[1:-1]

        if len(val) >= 2 and val[0] == '{' and val[-1] == '}':
            self.kind = 'object'
            return self._parse_object(val[1:-1])

        if '|' in val:
            self.kind = 'list'
            return [ValueNode(v.strip()) for v in val.split('|') if v.strip()]

        if val.lower() == 'true':
            self.kind = 'bool'
            return True
        if val.lower() == 'false':
            self.kind = 'bool'
            return False

        try:
            if '.' in val:
                self.kind = 'float'
                return float(val)
            if len(val) > 1 and val[0] == '0':
                self.kind = 'string'
                return val
            self.kind = 'int'
            return int(val)
        except (ValueError, TypeError):
            self.kind = 'string'
            return val

    def _parse_object(self, content: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for part in content.split('|'):
            part = part.strip()
            if not part or '>>' not in part:
                continue
            k, v = map(str.strip, part.split('>>', 1))
            result[k] = resolve_value(ValueNode(v))
        return result

class AttributeNode:
    def __init__(self, key: str, value: str, lineno: int):
        self.type = 'attribute'
        self.key = key
        self.value = ValueNode(value)
        self.lineno = lineno

    def __repr__(self) -> str:
        return f'AttributeNode({self.key!r}, lineno={self.lineno})'

class BlockNode:
    def __init__(self, name: str, lineno: int):
        self.type = 'block'
        self.name = name
        self.attributes: List[AttributeNode] = []
        self.children: List[BlockNode] = []
        self.lineno = lineno

    def __repr__(self) -> str:
        return f'BlockNode({self.name!r}, attrs={len(self.attributes)}, children={len(self.children)})'

def parse(tokens: List[dict]) -> List[BlockNode]:
    stack: List[BlockNode] = []
    ast: List[BlockNode] = []
    for tok in tokens:
        if tok['type'] == 'BLOCK_START':
            node = BlockNode(tok['value'], tok['line'])
            if stack:
                stack[-1].children.append(node)
            else:
                ast.append(node)
            stack.append(node)
        elif tok['type'] == 'BLOCK_END':
            if not stack:
                raise PSRParseError(f'Cierre sin apertura en línea {tok["line"]}')
            stack.pop()
        elif tok['type'] == 'ATTRIBUTE':
            if not stack:
                raise PSRParseError(f'Atributo fuera de bloque en línea {tok["line"]}')
            stack[-1].attributes.append(AttributeNode(tok['key'], tok['value'], tok['line']))
        elif tok['type'] == 'EOF':
            break
    if stack:
        raise PSRParseError('Bloque(s) sin cerrar')
    return ast

# ----------------------------
# Builder / Normalización
# ----------------------------
def build_block(block_node: BlockNode, depth: int = 0) -> Dict[str, Any]:
    if depth > _MAX_DEPTH:
        raise PSRParseError('Excedida profundidad máxima de anidamiento')
    atributos: Dict[str, Any] = {}
    for attr in block_node.attributes:
        if attr.key in atributos:
            raise PSRParseError(f'Clave duplicada "{attr.key}" en bloque "{block_node.name}" línea {attr.lineno}')
        atributos[attr.key] = resolve_value(attr.value)
    block_dict = {
        'tipo': block_node.name,
        'atributos': atributos,
        'hijos': [build_block(c, depth + 1) for c in block_node.children]
    }
    return block_dict

def resolve_value(vnode: ValueNode) -> Any:
    if isinstance(vnode.value, list):
        return [resolve_value(v) for v in vnode.value]
    return vnode.value

def build_document(ast: List[BlockNode]) -> List[Dict[str, Any]]:
    return [build_block(node) for node in ast]

# ----------------------------
# Serializer
# ----------------------------
def _needs_quotes(s: str) -> bool:
    if s == '' or s != s.strip():
        return True
    if s.lower() in ('true', 'false'):
        return True
    for ch in ('|', '{', '}', '::'):
        if ch in s:
            return True
    try:
        if '.' in s:
            float(s)
        elif len(s) > 1 and s[0] == '0':
            return False
        else:
            int(s)
        return True
    except ValueError:
        return False

def dump_value(value: Any) -> str:
    if isinstance(value, dict):
        items = ' | '.join(f'{k} >> {dump_value(v)}' for k, v in value.items())
        return f'{{ {items} }}'
    if isinstance(value, list):
        return ' | '.join(dump_value(v) for v in value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if '\n' in s:
        return '<<\n' + s + '\n>>'
    if _needs_quotes(s):
        return '"' + s.replace('"', "'") + '"'
    return s

def serialize_block(block: Dict[str, Any], indent: int = 0) -> str:
    pad = ' '*indent
    lines = [f'{pad}-> {block["tipo"]}']
    for k, v in block['atributos'].items():
        dv = dump_value(v)
        if dv.startswith('<<\n'):
            lines.append(f'{pad}    {k} >> <<')
            lines.append(dv[3:-3])
            lines.append(f'{pad}    >>')
        else:
            lines.append(f'{pad}    {k} >> {dv}')
    for c in block['hijos']:
        lines.append(serialize_block(c, indent+4))
    lines.append(f'{pad}<-')
    return '\n'.join(lines)

def dump_psr(blocks: List[Dict[str, Any]], file_path: Optional[str] = None) -> Optional[str]:
    text = '\n\n'.join(serialize_block(b) for b in blocks)
    if file_path:
        with open(file_path,'w',encoding='utf-8') as f:
            f.write(text)
    else:
        return text

# ----------------------------
# Loader
# ----------------------------
def load_psr(file_path: str) -> List[BlockNode]:
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        text = f.read()
    tokens = lex_psr(text)
    ast = parse(tokens)
    return ast

# ----------------------------
# Validator
# ----------------------------
def _type_matches(tipo_str: str, value: Any) -> bool:
    if tipo_str == 'int' and isinstance(value, bool):
        return False
    mapping: Dict[str, type] = {'str': str, 'int': int, 'float': float, 'bool': bool}
    if tipo_str not in mapping:
        return True
    return isinstance(value, mapping[tipo_str])

def validate_block(block: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if block['tipo'] != schema['tipo']:
        errors.append(f'Tipo bloque esperado {schema["tipo"]} encontrado {block["tipo"]}')
    for k, attr_sch in schema.get('atributos', {}).items():
        if attr_sch.get('obligatorio') and k not in block['atributos']:
            errors.append(f'Atributo obligatorio {k} ausente en {block["tipo"]}')
        elif k in block['atributos']:
            v = block['atributos'][k]
            t = attr_sch['tipo']
            if t == 'list':
                if not isinstance(v, list):
                    errors.append(f'{k} debe ser lista en {block["tipo"]}')
                elif 'items_tipo' in attr_sch:
                    for i, item in enumerate(v):
                        if not _type_matches(attr_sch['items_tipo'], item):
                            errors.append(f'{k}[{i}] debe ser {attr_sch["items_tipo"]} en {block["tipo"]}')
            else:
                if not _type_matches(t, v):
                    errors.append(f'{k} debe ser {t} en {block["tipo"]}')
    for i, child_sch in enumerate(schema.get('hijos', [])):
        if i < len(block['hijos']):
            errors.extend(validate_block(block['hijos'][i], child_sch))
    if len(block['hijos']) > len(schema.get('hijos', [])):
        errors.append(f'Bloque {block["tipo"]} tiene más hijos de los esperados')
    return errors

def validate_psr(data: List[Dict[str, Any]], schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for b in data:
        errors.extend(validate_block(b, schema))
    return errors

# ----------------------------
# Schema loader (.json / .psr)
# ----------------------------
def _expand_psr_schema(block: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {'tipo': block['tipo'], 'atributos': {}, 'hijos': []}
    for k, v in block.get('atributos', {}).items():
        if isinstance(v, str):
            result['atributos'][k] = {'tipo': v}
        else:
            result['atributos'][k] = v
    for child in block.get('hijos', []):
        result['hijos'].append(_expand_psr_schema(child))
    return result

def load_schema(path: str) -> Any:
    if path.endswith('.psr'):
        ast = load_psr(path)
        docs = build_document(ast)
        if len(docs) == 1:
            return _expand_psr_schema(docs[0])
        return [_expand_psr_schema(d) for d in docs]
    with open(path, encoding='utf-8') as f:
        return json.load(f)

# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(
        prog='pulsar',
        description='Parser y herramientas para formato PULSAR (.psr)',
        epilog='Ejemplos:\n'
               '  pulsar parse -f datos.psr\n'
               '  pulsar dump -f datos.psr -o salida.psr\n'
               '  pulsar validate -f datos.psr -s schema.json\n'
               '  pulsar version',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p_parse = sub.add_parser('parse', help='Parsear .psr y mostrar JSON',
                             description='Parsea un archivo .psr y muestra su estructura en JSON.')
    p_parse.add_argument('-f', '--file', required=True, help='Archivo .psr de entrada')

    p_dump = sub.add_parser('dump', help='Serializar .psr a texto',
                            description='Parsea y re-serializa un .psr (round-trip).')
    p_dump.add_argument('-f', '--file', required=True, help='Archivo .psr de entrada')
    p_dump.add_argument('-o', '--output', help='Archivo de salida (stdout si se omite)')

    p_val = sub.add_parser('validate', help='Validar .psr contra un schema',
                           description='Valida un .psr contra un schema JSON o .psr.')
    p_val.add_argument('-f', '--file', required=True, help='Archivo .psr de entrada')
    p_val.add_argument('-s', '--schema', required=True, help='Schema (.json o .psr)')

    p_ver = sub.add_parser('version', help='Mostrar versión',
                           description='Muestra la versión actual de PULSAR.')

    args = parser.parse_args()

    try:
        if args.command == 'version':
            print('PULSAR CLI v1.0')
            return

        if args.command == 'parse':
            ast = load_psr(args.file)
            print(json.dumps(build_document(ast), indent=4))

        elif args.command == 'dump':
            ast = load_psr(args.file)
            data = build_document(ast)
            text = dump_psr(data)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f'Archivo dump creado en: {args.output}')
            else:
                print(text, end='')

        elif args.command == 'validate':
            ast = load_psr(args.file)
            data = build_document(ast)
            schema = load_schema(args.schema)
            errs = validate_psr(data, schema)
            if errs:
                for e in errs:
                    print('Error:', e)
                sys.exit(1)
            else:
                print('Archivo válido ✅')

    except (PSRLexError, PSRParseError, FileNotFoundError,
            json.JSONDecodeError, ValueError) as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
