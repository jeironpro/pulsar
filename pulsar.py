#!/usr/bin/env python3

import argparse
import json
import re
import sys
from typing import Any

__version__ = "2.0.1"

__all__ = [
    "PSRLexError",
    "PSRParseError",
    "lex_psr",
    "parse",
    "BlockNode",
    "AttributeNode",
    "ValueNode",
    "build_block",
    "build_document",
    "resolve_value",
    "dump_value",
    "serialize_block",
    "dump_psr",
    "load_psr",
    "validate_block",
    "validate_psr",
    "load_schema",
    "main",
]


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
        elif ch == ":" and i + 1 < len(line) and line[i + 1] == ":" and not in_quotes:
            return i
    return -1


def lex_psr(text: str) -> list[dict]:
    id_re = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    tokens: list[dict] = []
    lines = text.splitlines()
    in_multiline = False
    multiline_key = None
    multiline_start = 0
    multiline_content = []

    for lineno, line in enumerate(lines, start=1):
        raw = line

        # multiline mode: consume raw lines verbatim (preserva vacias y '::')
        if in_multiline:
            stripped = line.strip()
            if stripped == ">>":
                in_multiline = False
                content = "\n".join(multiline_content)
                tokens.append(
                    {
                        "type": "ATTRIBUTE",
                        "key": multiline_key,
                        "value": content,
                        "line": multiline_start,
                        "column": 0,
                    }
                )
            else:
                multiline_content.append(raw)
            continue

        stripped = line.strip()

        cpos = _comment_end(stripped)
        if cpos >= 0:
            stripped = stripped[:cpos].strip()
        if not stripped:
            continue

        if stripped.startswith("->"):
            block_name = stripped[2:].strip()
            if not block_name:
                raise PSRLexError(f'Line {lineno}: missing block name after "->"')
            if not id_re.match(block_name):
                raise PSRLexError(f"Line {lineno}: invalid block name -> {block_name}")
            col = raw.index("->") + 1
            tokens.append(
                {"type": "BLOCK_START", "value": block_name, "line": lineno, "column": col}
            )

        elif stripped == "<-":
            col = raw.index("<-") + 1
            tokens.append({"type": "BLOCK_END", "value": "<-", "line": lineno, "column": col})

        elif stripped.startswith("-") and not stripped.startswith("->"):
            col = raw.index("-") + 1
            raise PSRLexError(f"Line {lineno} col {col}: incomplete operator")

        elif stripped.startswith("<") and not stripped.startswith("<-"):
            col = raw.index("<") + 1
            raise PSRLexError(f"Line {lineno} col {col}: incomplete operator")

        elif ">>" in stripped:
            key, val = map(str.strip, stripped.split(">>", 1))
            if not key:
                raise PSRLexError(f"Line {lineno}: missing attribute key")
            if not id_re.match(key):
                raise PSRLexError(f"Line {lineno}: invalid attribute name -> {key}")

            # valor multilinea
            if val == "<<":
                in_multiline = True
                multiline_key = key
                multiline_start = lineno
                multiline_content = []
                continue

            if "," in val:
                raise PSRLexError(f'Line {lineno}: commas not allowed (use "|" for lists)')

            col = raw.index(">>") + 1
            tokens.append(
                {"type": "ATTRIBUTE", "key": key, "value": val, "line": lineno, "column": col}
            )

        else:
            raise PSRLexError(f"Line {lineno}: unrecognized line -> {line}")

    if in_multiline:
        raise PSRLexError(f"Line {multiline_start}: unclosed multiline")

    last_line = lineno if lines else 0
    tokens.append({"type": "EOF", "value": "", "line": last_line + 1, "column": 0})
    return tokens


# ----------------------------
# Parser + AST
# ----------------------------
class ValueNode:
    def __init__(self, raw: str, kind: str = "string"):
        self.raw = raw
        self.kind = kind
        self.value = self._parse()

    def __repr__(self) -> str:
        return f"ValueNode({self.raw!r}, kind={self.kind!r}, value={self.value!r})"

    def _parse(self) -> Any:
        val = self.raw.strip()

        if len(val) >= 2 and val[0] == '"' and val[-1] == '"' and '"' not in val[1:-1]:
            self.kind = "string"
            return val[1:-1]

        if len(val) >= 2 and val[0] == "{" and val[-1] == "}":
            self.kind = "object"
            return self._parse_object(val[1:-1])

        if "|" in val:
            self.kind = "list"
            return [ValueNode(v.strip()) for v in val.split("|") if v.strip()]

        if val.lower() == "true":
            self.kind = "bool"
            return True
        if val.lower() == "false":
            self.kind = "bool"
            return False

        try:
            if "." in val:
                self.kind = "float"
                return float(val)
            if len(val) > 1 and val[0] == "0":
                self.kind = "string"
                return val
            self.kind = "int"
            return int(val)
        except (ValueError, TypeError):
            self.kind = "string"
            return val

    def _parse_object(self, content: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for part in content.split("|"):
            part = part.strip()
            if not part or ">>" not in part:
                continue
            k, v = map(str.strip, part.split(">>", 1))
            result[k] = resolve_value(ValueNode(v))
        return result


class AttributeNode:
    def __init__(self, key: str, value: str, lineno: int):
        self.type = "attribute"
        self.key = key
        self.value = ValueNode(value)
        self.lineno = lineno

    def __repr__(self) -> str:
        return f"AttributeNode({self.key!r}, lineno={self.lineno})"


class BlockNode:
    def __init__(self, name: str, lineno: int):
        self.type = "block"
        self.name = name
        self.attributes: list[AttributeNode] = []
        self.children: list[BlockNode] = []
        self.lineno = lineno

    def __repr__(self) -> str:
        return (
            f"BlockNode({self.name!r}, attrs={len(self.attributes)}, children={len(self.children)})"
        )


def parse(tokens: list[dict]) -> list[BlockNode]:
    stack: list[BlockNode] = []
    ast: list[BlockNode] = []
    for tok in tokens:
        if tok["type"] == "BLOCK_START":
            node = BlockNode(tok["value"], tok["line"])
            if stack:
                stack[-1].children.append(node)
            else:
                ast.append(node)
            stack.append(node)
        elif tok["type"] == "BLOCK_END":
            if not stack:
                raise PSRParseError(f"Close without open at line {tok['line']}")
            stack.pop()
        elif tok["type"] == "ATTRIBUTE":
            if not stack:
                raise PSRParseError(f"Attribute outside block at line {tok['line']}")
            stack[-1].attributes.append(AttributeNode(tok["key"], tok["value"], tok["line"]))
        elif tok["type"] == "EOF":
            break
    if stack:
        raise PSRParseError("Unclosed block(s)")
    return ast


# ----------------------------
# Builder / Normalización
# ----------------------------
def build_block(block_node: BlockNode, depth: int = 0) -> dict[str, Any]:
    if depth > _MAX_DEPTH:
        raise PSRParseError("Max nesting depth exceeded")
    attributes: dict[str, Any] = {}
    for attr in block_node.attributes:
        if attr.key in attributes:
            raise PSRParseError(
                f'Duplicate key "{attr.key}" in block "{block_node.name}" at line {attr.lineno}'
            )
        attributes[attr.key] = resolve_value(attr.value)
    block_dict = {
        "type": block_node.name,
        "attributes": attributes,
        "children": [build_block(c, depth + 1) for c in block_node.children],
    }
    return block_dict


def resolve_value(vnode: ValueNode) -> Any:
    if isinstance(vnode.value, list):
        return [resolve_value(v) for v in vnode.value]
    return vnode.value


def build_document(ast: list[BlockNode]) -> list[dict[str, Any]]:
    return [build_block(node) for node in ast]


# ----------------------------
# Serializer
# ----------------------------
def _needs_quotes(s: str) -> bool:
    if s == "" or s != s.strip():
        return True
    if s.lower() in ("true", "false"):
        return True
    for ch in ("|", "{", "}", "::"):
        if ch in s:
            return True
    try:
        if "." in s:
            float(s)
        elif len(s) > 1 and s[0] == "0":
            return False
        else:
            int(s)
        return True
    except ValueError:
        return False


def dump_value(value: Any) -> str:
    if isinstance(value, dict):
        items = " | ".join(f"{k} >> {dump_value(v)}" for k, v in value.items())
        return f"{{ {items} }}"
    if isinstance(value, list):
        return " | ".join(dump_value(v) for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    s = str(value)
    if "\n" in s:
        return "<<\n" + s + "\n>>"
    if _needs_quotes(s):
        return '"' + s.replace('"', "'") + '"'
    return s


def serialize_block(block: dict[str, Any], indent: int = 0) -> str:
    pad = " " * indent
    lines = [f"{pad}-> {block['type']}"]
    for k, v in block["attributes"].items():
        dv = dump_value(v)
        if dv.startswith("<<\n"):
            lines.append(f"{pad}    {k} >> <<")
            lines.append(dv[3:-3])
            lines.append(f"{pad}    >>")
        else:
            lines.append(f"{pad}    {k} >> {dv}")
    for c in block["children"]:
        lines.append(serialize_block(c, indent + 4))
    lines.append(f"{pad}<-")
    return "\n".join(lines)


def dump_psr(blocks: list[dict[str, Any]], file_path: str | None = None) -> str | None:
    text = "\n\n".join(serialize_block(b) for b in blocks)
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        return text


# ----------------------------
# Loader
# ----------------------------
def load_psr(file_path: str) -> list[BlockNode]:
    with open(file_path, encoding="utf-8-sig") as f:
        text = f.read()
    tokens = lex_psr(text)
    ast = parse(tokens)
    return ast


# ----------------------------
# Validator
# ----------------------------
def _type_matches(type_str: str, value: Any) -> bool:
    if type_str == "int" and isinstance(value, bool):
        return False
    mapping: dict[str, type] = {"str": str, "int": int, "float": float, "bool": bool}
    if type_str not in mapping:
        return True
    return isinstance(value, mapping[type_str])


def validate_block(block: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if block["type"] != schema["type"]:
        errors.append(f"Expected block type {schema['type']} but found {block['type']}")
    for k, attr_schema in schema.get("attributes", {}).items():
        if attr_schema.get("required") and k not in block["attributes"]:
            errors.append(f"Required attribute {k} missing in {block['type']}")
        elif k in block["attributes"]:
            v = block["attributes"][k]
            t = attr_schema["type"]
            if t == "list":
                if not isinstance(v, list):
                    errors.append(f"{k} must be a list in {block['type']}")
                elif "items_type" in attr_schema:
                    for i, item in enumerate(v):
                        if not _type_matches(attr_schema["items_type"], item):
                            errors.append(
                                f"{k}[{i}] must be {attr_schema['items_type']} in {block['type']}"
                            )
            else:
                if not _type_matches(t, v):
                    errors.append(f"{k} must be {t} in {block['type']}")
    if schema.get("strict"):
        for k in block["attributes"]:
            if k not in schema.get("attributes", {}):
                errors.append(f"Attribute {k} not allowed in {block['type']} (strict mode)")
    block_children = block.get("children", [])
    schema_children = schema.get("children", [])

    # Emparejamiento de hijos por type (no por posición): cada tipo declarado
    # en el schema exige al menos un hijo y se valida recursivamente; los tipos
    # de hijo no declarados producen error.
    children_by_type: dict[str, list[dict[str, Any]]] = {}
    for child in block_children:
        children_by_type.setdefault(child["type"], []).append(child)

    declared_types: set[str] = set()
    for child_schema in schema_children:
        ctype = child_schema["type"]
        if ctype in declared_types:
            continue  # declaraciones duplicadas del mismo tipo se validan una vez
        declared_types.add(ctype)
        matches = children_by_type.get(ctype, [])
        if not matches:
            errors.append(f"Block {block['type']} has missing children: {ctype}")
        for match in matches:
            errors.extend(validate_block(match, child_schema))

    for ctype in children_by_type:
        if ctype not in declared_types:
            errors.append(f"Block {block['type']} has undeclared children of type {ctype}")
    return errors


def validate_psr(data: list[dict[str, Any]], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for b in data:
        errors.extend(validate_block(b, schema))
    return errors


# ----------------------------
# Schema loader (.json / .psr)
# ----------------------------
def _expand_psr_schema(block: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"type": block["type"], "attributes": {}, "children": []}
    for k, v in block.get("attributes", {}).items():
        if isinstance(v, str):
            result["attributes"][k] = {"type": v}
        else:
            result["attributes"][k] = v
    for child in block.get("children", []):
        result["children"].append(_expand_psr_schema(child))
    return result


def load_schema(path: str) -> Any:
    if path.endswith(".psr"):
        ast = load_psr(path)
        docs = build_document(ast)
        if len(docs) == 1:
            return _expand_psr_schema(docs[0])
        return [_expand_psr_schema(d) for d in docs]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="pulsar",
        description="Parser and tooling for the PULSAR (.psr) data format",
        epilog="Examples:\n"
        "  pulsar parse -f data.psr\n"
        "  pulsar dump -f data.psr -o out.psr\n"
        "  pulsar validate -f data.psr -s schema.json\n"
        "  pulsar version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"PULSAR CLI v{__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser(
        "parse",
        help="Parse .psr and print JSON",
        description="Parses a .psr file and prints its structure as JSON.",
    )
    p_parse.add_argument("-f", "--file", required=True, help="Input .psr file")

    p_dump = sub.add_parser(
        "dump",
        help="Serialize .psr to text",
        description="Parses and re-serializes a .psr (round-trip).",
    )
    p_dump.add_argument("-f", "--file", required=True, help="Input .psr file")
    p_dump.add_argument("-o", "--output", help="Output file (stdout if omitted)")

    p_val = sub.add_parser(
        "validate",
        help="Validate a .psr against a schema",
        description="Validates a .psr against a JSON or .psr schema.",
    )
    p_val.add_argument("-f", "--file", required=True, help="Input .psr file")
    p_val.add_argument("-s", "--schema", required=True, help="Schema (.json or .psr)")

    sub.add_parser("version", help="Show version", description="Prints the current PULSAR version.")

    args = parser.parse_args()

    try:
        if args.command == "version":
            print(f"PULSAR CLI v{__version__}")
            return

        if args.command == "parse":
            ast = load_psr(args.file)
            print(json.dumps(build_document(ast), indent=4, ensure_ascii=False))

        elif args.command == "dump":
            ast = load_psr(args.file)
            data = build_document(ast)
            text = dump_psr(data)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"Dump file created at: {args.output}")
            else:
                print(text, end="")

        elif args.command == "validate":
            ast = load_psr(args.file)
            data = build_document(ast)
            schema = load_schema(args.schema)
            errs = validate_psr(data, schema)
            if errs:
                for e in errs:
                    print("Error:", e)
                sys.exit(1)
            else:
                print("File valid ✅")

    except (PSRLexError, PSRParseError, OSError, json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
