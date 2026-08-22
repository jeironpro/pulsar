import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pulsar import (
    BlockNode,
    PSRLexError,
    PSRParseError,
    ValueNode,
    _comment_end,
    _expand_psr_schema,
    _needs_quotes,
    _type_matches,
    build_block,
    build_document,
    dump_psr,
    dump_value,
    lex_psr,
    parse,
    validate_psr,
)


class TestLexer(unittest.TestCase):
    def test_basic_tokens(self):
        tokens = lex_psr("-> user\n    name >> Juan\n<-\n")
        types = [t["type"] for t in tokens]
        self.assertIn("BLOCK_START", types)
        self.assertIn("BLOCK_END", types)
        self.assertIn("ATTRIBUTE", types)
        self.assertIn("EOF", types)

    def test_block_start_value(self):
        tokens = lex_psr("-> user\n<-\n")
        self.assertEqual(tokens[0]["value"], "user")

    def test_block_end(self):
        tokens = lex_psr("-> x\n<-\n")
        self.assertEqual(tokens[1]["type"], "BLOCK_END")

    def test_attribute_key_value(self):
        tokens = lex_psr("-> x\n    age >> 30\n<-\n")
        attr = [t for t in tokens if t["type"] == "ATTRIBUTE"][0]
        self.assertEqual(attr["key"], "age")
        self.assertEqual(attr["value"], "30")

    def test_empty_file(self):
        tokens = lex_psr("")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0]["type"], "EOF")

    def test_comment_full_line(self):
        tokens = lex_psr(":: comment\n-> x\n<-\n")
        self.assertEqual(tokens[0]["type"], "BLOCK_START")

    def test_inline_comment(self):
        tokens = lex_psr("-> x\n    name >> Juan :: comment\n<-\n")
        attr = [t for t in tokens if t["type"] == "ATTRIBUTE"][0]
        self.assertEqual(attr["value"], "Juan")

    def test_comment_inside_quotes_preserved(self):
        tokens = lex_psr('-> x\n    name >> "hello :: world"\n<-\n')
        attr = [t for t in tokens if t["type"] == "ATTRIBUTE"][0]
        self.assertEqual(attr["value"], '"hello :: world"')

    def test_column_tracking(self):
        tokens = lex_psr("-> user\n<-\n")
        start = [t for t in tokens if t["type"] == "BLOCK_START"][0]
        end = [t for t in tokens if t["type"] == "BLOCK_END"][0]
        self.assertIn("column", start)
        self.assertIn("column", end)

    def test_multiline(self):
        tokens = lex_psr("-> x\n    bio >> <<\nline1\nline2\n>>\n<-\n")
        attr = [t for t in tokens if t["type"] == "ATTRIBUTE"][0]
        self.assertEqual(attr["value"], "line1\nline2")
        self.assertEqual(attr["key"], "bio")

    def test_multiline_preserves_blank_lines(self):
        tokens = lex_psr("-> x\n    bio >> <<\nline1\n\nline3\n>>\n<-\n")
        attr = [t for t in tokens if t["type"] == "ATTRIBUTE"][0]
        self.assertEqual(attr["value"], "line1\n\nline3")

    def test_multiline_preserves_comment_markers(self):
        tokens = lex_psr("-> x\n    bio >> <<\nnota :: comentario\n>>\n<-\n")
        attr = [t for t in tokens if t["type"] == "ATTRIBUTE"][0]
        self.assertEqual(attr["value"], "nota :: comentario")

    def test_round_trip_multiline_blank_lines(self):
        original = "-> x\n    bio >> <<\nline1\n\nline3\n>>\n<-\n"
        data = build_document(parse(lex_psr(original)))
        self.assertEqual(data[0]["attributes"]["bio"], "line1\n\nline3")
        text = dump_psr(data)
        data2 = build_document(parse(lex_psr(text)))
        self.assertEqual(data, data2)

    def test_error_empty_block_name(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-> \n<-\n")

    def test_error_bad_block_name(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-> 123bad\n<-\n")

    def test_error_bad_attr_name(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-> x\n    123name >> val\n<-\n")

    def test_error_comma_in_value(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-> x\n    name >> Juan,\n<-\n")

    def test_error_incomplete_operator_dash(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-bad\n")

    def test_error_incomplete_operator_lt(self):
        with self.assertRaises(PSRLexError):
            lex_psr("<bad\n")

    def test_error_unclosed_multiline(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-> x\n    bio >> <<\ncontent\n<-\n")

    def test_error_missing_key(self):
        with self.assertRaises(PSRLexError):
            lex_psr("-> x\n    >> val\n<-\n")

    def test_whitespace_lines_skipped(self):
        tokens = lex_psr("\n\n-> x\n\n<-\n\n")
        self.assertEqual(tokens[0]["type"], "BLOCK_START")

    def test_identifier_regex_valid(self):
        tokens = lex_psr("-> my-var_1\n<-\n")
        self.assertEqual(tokens[0]["value"], "my-var_1")


class TestParser(unittest.TestCase):
    def test_simple_block(self):
        ast = parse(lex_psr("-> user\n<-\n"))
        self.assertEqual(len(ast), 1)
        self.assertEqual(ast[0].name, "user")

    def test_multiple_blocks(self):
        ast = parse(lex_psr("-> a\n<-\n-> b\n<-\n"))
        self.assertEqual(len(ast), 2)
        self.assertEqual(ast[0].name, "a")
        self.assertEqual(ast[1].name, "b")

    def test_nested_block(self):
        ast = parse(lex_psr("-> a\n    -> b\n    <-\n<-\n"))
        self.assertEqual(len(ast), 1)
        self.assertEqual(len(ast[0].children), 1)
        self.assertEqual(ast[0].children[0].name, "b")

    def test_attributes(self):
        ast = parse(lex_psr("-> a\n    x >> 1\n    y >> hello\n<-\n"))
        attrs = ast[0].attributes
        self.assertEqual(len(attrs), 2)
        self.assertEqual(attrs[0].key, "x")
        self.assertEqual(attrs[1].key, "y")

    def test_error_unclosed_block(self):
        with self.assertRaises(PSRParseError):
            parse(lex_psr("-> a\n"))

    def test_error_close_without_open(self):
        with self.assertRaises(PSRParseError):
            parse(lex_psr("<-\n"))

    def test_error_attribute_outside_block(self):
        with self.assertRaises(PSRParseError):
            parse(lex_psr("x >> 1\n"))

    def test_empty_document(self):
        ast = parse(lex_psr(""))
        self.assertEqual(ast, [])


class TestBuilder(unittest.TestCase):
    def test_simple_document(self):
        ast = parse(lex_psr("-> user\n    name >> Juan\n<-\n"))
        doc = build_document(ast)
        self.assertEqual(doc[0]["type"], "user")
        self.assertEqual(doc[0]["attributes"]["name"], "Juan")

    def test_int_value(self):
        ast = parse(lex_psr("-> x\n    n >> 42\n<-\n"))
        doc = build_document(ast)
        self.assertIsInstance(doc[0]["attributes"]["n"], int)
        self.assertEqual(doc[0]["attributes"]["n"], 42)

    def test_float_value(self):
        ast = parse(lex_psr("-> x\n    n >> 3.14\n<-\n"))
        doc = build_document(ast)
        self.assertIsInstance(doc[0]["attributes"]["n"], float)
        self.assertEqual(doc[0]["attributes"]["n"], 3.14)

    def test_bool_true(self):
        ast = parse(lex_psr("-> x\n    flag >> true\n<-\n"))
        doc = build_document(ast)
        self.assertIsInstance(doc[0]["attributes"]["flag"], bool)
        self.assertTrue(doc[0]["attributes"]["flag"])

    def test_bool_false(self):
        ast = parse(lex_psr("-> x\n    flag >> false\n<-\n"))
        doc = build_document(ast)
        self.assertFalse(doc[0]["attributes"]["flag"])

    def test_list_value(self):
        ast = parse(lex_psr("-> x\n    items >> a | b | c\n<-\n"))
        doc = build_document(ast)
        self.assertEqual(doc[0]["attributes"]["items"], ["a", "b", "c"])

    def test_quoted_string(self):
        ast = parse(lex_psr('-> x\n    name >> "Juan Perez"\n<-\n'))
        doc = build_document(ast)
        self.assertEqual(doc[0]["attributes"]["name"], "Juan Perez")

    def test_object_value(self):
        ast = parse(lex_psr("-> x\n    m >> { city >> Madrid | country >> Spain }\n<-\n"))
        doc = build_document(ast)
        obj = doc[0]["attributes"]["m"]
        self.assertIsInstance(obj, dict)
        self.assertEqual(obj["city"], "Madrid")
        self.assertEqual(obj["country"], "Spain")

    def test_multiline_value(self):
        ast = parse(lex_psr("-> x\n    bio >> <<\nline1\nline2\n>>\n<-\n"))
        doc = build_document(ast)
        self.assertEqual(doc[0]["attributes"]["bio"], "line1\nline2")

    def test_nested_build(self):
        ast = parse(lex_psr("-> a\n    -> b\n        x >> 1\n    <-\n<-\n"))
        doc = build_document(ast)
        self.assertEqual(doc[0]["children"][0]["type"], "b")
        self.assertEqual(doc[0]["children"][0]["attributes"]["x"], 1)

    def test_duplicate_key_error(self):
        ast = parse(lex_psr("-> a\n    x >> 1\n    x >> 2\n<-\n"))
        with self.assertRaises(PSRParseError):
            build_document(ast)


class TestSerializer(unittest.TestCase):
    def test_serialize_basic(self):
        data = [{"type": "user", "attributes": {"name": "Juan"}, "children": []}]
        text = dump_psr(data)
        self.assertIn("-> user", text)
        self.assertIn("name >> Juan", text)
        self.assertIn("<-", text)

    def test_serialize_int(self):
        data = [{"type": "x", "attributes": {"n": 42}, "children": []}]
        text = dump_psr(data)
        self.assertIn("n >> 42", text)

    def test_serialize_bool(self):
        data = [{"type": "x", "attributes": {"a": True, "b": False}, "children": []}]
        text = dump_psr(data)
        self.assertIn("a >> true", text)
        self.assertIn("b >> false", text)

    def test_serialize_list(self):
        data = [{"type": "x", "attributes": {"items": ["a", "b", "c"]}, "children": []}]
        text = dump_psr(data)
        self.assertIn("a | b | c", text)

    def test_serialize_object(self):
        data = [{"type": "x", "attributes": {"m": {"city": "Madrid"}}, "children": []}]
        text = dump_psr(data)
        self.assertIn("{ city >> Madrid }", text)

    def test_serialize_nested(self):
        data = [
            {
                "type": "a",
                "attributes": {},
                "children": [{"type": "b", "attributes": {"x": 1}, "children": []}],
            }
        ]
        text = dump_psr(data)
        self.assertIn("-> a", text)
        self.assertIn("-> b", text)
        self.assertIn("x >> 1", text)

    def test_round_trip_simple(self):
        original = "-> user\n    name >> Juan\n    age >> 30\n<-\n"
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def test_round_trip_all_types(self):
        original = (
            "-> item\n"
            '    name >> "hello world"\n'
            "    count >> 42\n"
            "    ratio >> 3.14\n"
            "    flag >> true\n"
            "    tags >> a | b | c\n"
            "    meta >> { x >> 1 | y >> 2 }\n"
            "<-\n"
        )
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def test_round_trip_multiline(self):
        original = "-> x\n    bio >> <<\nline1\nline2\n>>\n<-\n"
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def test_round_trip_nested(self):
        original = "-> parent\n    name >> root\n    -> child\n        val >> 1\n    <-\n<-\n"
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def _round_trip(self, source: str):
        data = build_document(parse(lex_psr(source)))
        text = dump_psr(data)
        return data, build_document(parse(lex_psr(text)))

    def test_round_trip_numeric_string(self):
        original = '-> x\n    a >> "42"\n    b >> "3.14"\n    c >> "-7"\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["a"], "42")
        self.assertEqual(data[0]["attributes"]["b"], "3.14")
        self.assertEqual(data[0]["attributes"]["c"], "-7")
        self.assertEqual(data, data2)

    def test_round_trip_bool_string(self):
        original = '-> x\n    a >> "true"\n    b >> "False"\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["a"], "true")
        self.assertEqual(data[0]["attributes"]["b"], "False")
        self.assertEqual(data, data2)

    def test_round_trip_pipe_in_string(self):
        original = '-> x\n    cmd >> "a | b | c"\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["cmd"], "a | b | c")
        self.assertEqual(data, data2)

    def test_round_trip_braces_in_string(self):
        original = '-> x\n    tpl >> "{ x >> 1 }"\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["tpl"], "{ x >> 1 }")
        self.assertEqual(data, data2)

    def test_round_trip_comment_marker_string(self):
        original = '-> x\n    note >> "hola :: mundo"\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["note"], "hola :: mundo")
        self.assertEqual(data, data2)

    def test_round_trip_empty_and_whitespace_strings(self):
        original = '-> x\n    a >> ""\n    b >> "  padded  "\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["a"], "")
        self.assertEqual(data[0]["attributes"]["b"], "  padded  ")
        self.assertEqual(data, data2)

    def test_round_trip_leading_zero_string(self):
        original = "-> x\n    code >> 007\n<-\n"
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["code"], "007")
        self.assertEqual(data, data2)

    def test_round_trip_list_with_ambiguous_items(self):
        original = '-> x\n    items >> "1" | two | "true"\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["items"], ["1", "two", "true"])
        self.assertEqual(data, data2)

    def test_round_trip_object_with_ambiguous_values(self):
        original = '-> x\n    m >> { n >> "42" | ok >> "false" }\n<-\n'
        data, data2 = self._round_trip(original)
        self.assertEqual(data[0]["attributes"]["m"], {"n": "42", "ok": "false"})
        self.assertEqual(data, data2)

    def test_needs_quotes_cases(self):
        self.assertTrue(_needs_quotes(""))
        self.assertTrue(_needs_quotes(" pad "))
        self.assertTrue(_needs_quotes("42"))
        self.assertTrue(_needs_quotes("-3.5"))
        self.assertTrue(_needs_quotes("True"))
        self.assertTrue(_needs_quotes("a|b"))
        self.assertTrue(_needs_quotes("{ x }"))
        self.assertTrue(_needs_quotes("a :: b"))
        self.assertFalse(_needs_quotes("hello world"))
        self.assertFalse(_needs_quotes("007"))
        self.assertFalse(_needs_quotes("v1.0"))

    def test_dump_value_preserves_types(self):
        self.assertEqual(dump_value(42), "42")
        self.assertEqual(dump_value(3.14), "3.14")
        self.assertEqual(dump_value(True), "true")
        self.assertEqual(dump_value("plain"), "plain")
        self.assertEqual(dump_value("42"), '"42"')


class TestValidator(unittest.TestCase):
    def test_valid_simple(self):
        data = [{"type": "user", "attributes": {"name": "Juan"}, "children": []}]
        schema = {"type": "user", "attributes": {"name": {"type": "str"}}, "children": []}
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])

    def test_wrong_type(self):
        data = [{"type": "admin", "attributes": {}, "children": []}]
        schema = {"type": "user", "attributes": {}, "children": []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_missing_required_attr(self):
        data = [{"type": "user", "attributes": {}, "children": []}]
        schema = {
            "type": "user",
            "attributes": {"name": {"type": "str", "required": True}},
            "children": [],
        }
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_wrong_type_int(self):
        data = [{"type": "x", "attributes": {"n": "hello"}, "children": []}]
        schema = {"type": "x", "attributes": {"n": {"type": "int"}}, "children": []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_wrong_type_bool_not_int(self):
        data = [{"type": "x", "attributes": {"n": True}, "children": []}]
        schema = {"type": "x", "attributes": {"n": {"type": "int"}}, "children": []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_list_type(self):
        data = [{"type": "x", "attributes": {"items": [1, 2, 3]}, "children": []}]
        schema = {
            "type": "x",
            "attributes": {"items": {"type": "list", "items_type": "int"}},
            "children": [],
        }
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])

    def test_list_type_wrong_item(self):
        data = [{"type": "x", "attributes": {"items": [1, "bad", 3]}, "children": []}]
        schema = {
            "type": "x",
            "attributes": {"items": {"type": "list", "items_type": "int"}},
            "children": [],
        }
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_extra_children(self):
        data = [
            {
                "type": "x",
                "attributes": {},
                "children": [{"type": "y", "attributes": {}, "children": []}],
            }
        ]
        schema = {"type": "x", "attributes": {}, "children": []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_valid_children(self):
        data = [
            {
                "type": "x",
                "attributes": {},
                "children": [{"type": "y", "attributes": {"val": 1}, "children": []}],
            }
        ]
        schema = {
            "type": "x",
            "attributes": {},
            "children": [{"type": "y", "attributes": {"val": {"type": "int"}}, "children": []}],
        }
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])

    def test_missing_children_reported(self):
        data = [{"type": "a", "attributes": {}, "children": []}]
        schema = {
            "type": "a",
            "attributes": {},
            "children": [
                {"type": "b", "attributes": {}, "children": []},
                {"type": "c", "attributes": {}, "children": []},
            ],
        }
        errs = validate_psr(data, schema)
        self.assertEqual(len(errs), 1)
        self.assertIn("missing", errs[0])
        self.assertIn("b, c", errs[0])

    def test_partial_missing_children(self):
        data = [
            {
                "type": "a",
                "attributes": {},
                "children": [{"type": "b", "attributes": {}, "children": []}],
            }
        ]
        schema = {
            "type": "a",
            "attributes": {},
            "children": [
                {"type": "b", "attributes": {}, "children": []},
                {"type": "c", "attributes": {}, "children": []},
            ],
        }
        errs = validate_psr(data, schema)
        self.assertEqual(len(errs), 1)
        self.assertIn("c", errs[0])

    def test_lenient_allows_extra_attrs(self):
        data = [{"type": "x", "attributes": {"extra": 1}, "children": []}]
        schema = {"type": "x", "attributes": {}, "children": []}
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])

    def test_strict_rejects_extra_attrs(self):
        data = [{"type": "x", "attributes": {"extra": 1, "ok": 2}, "children": []}]
        schema = {
            "type": "x",
            "strict": True,
            "attributes": {"ok": {"type": "int"}},
            "children": [],
        }
        errs = validate_psr(data, schema)
        self.assertEqual(len(errs), 1)
        self.assertIn("not allowed", errs[0])
        self.assertIn("extra", errs[0])
        self.assertIn("strict", errs[0])


class TestEdgeCases(unittest.TestCase):
    def test_deep_nesting_blocked(self):
        root = BlockNode("root", 1)
        cur = root
        for _ in range(201):
            child = BlockNode("child", 1)
            cur.children.append(child)
            cur = child
        with self.assertRaises(PSRParseError):
            build_block(root)

    def test_value_node_kind_int(self):
        v = ValueNode("42")
        self.assertEqual(v.kind, "int")
        self.assertEqual(v.value, 42)

    def test_value_node_kind_float(self):
        v = ValueNode("3.14")
        self.assertEqual(v.kind, "float")
        self.assertEqual(v.value, 3.14)

    def test_value_node_kind_bool(self):
        v = ValueNode("true")
        self.assertEqual(v.kind, "bool")
        self.assertTrue(v.value)

    def test_value_node_kind_string(self):
        v = ValueNode("hello")
        self.assertEqual(v.kind, "string")
        self.assertEqual(v.value, "hello")

    def test_value_node_kind_list(self):
        v = ValueNode("a | b | c")
        self.assertEqual(v.kind, "list")
        self.assertEqual(len(v.value), 3)

    def test_value_node_kind_quoted(self):
        v = ValueNode('"hello world"')
        self.assertEqual(v.kind, "string")
        self.assertEqual(v.value, "hello world")

    def test_value_node_kind_object(self):
        v = ValueNode("{ x >> 1 | y >> 2 }")
        self.assertEqual(v.kind, "object")
        self.assertEqual(v.value["x"], 1)
        self.assertEqual(v.value["y"], 2)

    def test_comment_end(self):
        self.assertEqual(_comment_end("x :: y"), 2)
        self.assertEqual(_comment_end('"x :: y"'), -1)
        self.assertEqual(_comment_end("no comment"), -1)

    def test_type_matches_int(self):
        self.assertTrue(_type_matches("int", 42))
        self.assertFalse(_type_matches("int", True))

    def test_type_matches_bool(self):
        self.assertTrue(_type_matches("bool", True))
        self.assertFalse(_type_matches("bool", 42))

    def test_type_matches_unknown(self):
        self.assertTrue(_type_matches("unknown_type", "anything"))


class TestExpandPsrSchema(unittest.TestCase):
    def test_expand_simple(self):
        block = {"type": "user", "attributes": {"name": "str"}, "children": []}
        expanded = _expand_psr_schema(block)
        self.assertEqual(expanded["attributes"]["name"], {"type": "str"})

    def test_expand_nested(self):
        block = {
            "type": "x",
            "attributes": {},
            "children": [{"type": "y", "attributes": {"val": "int"}, "children": []}],
        }
        expanded = _expand_psr_schema(block)
        self.assertEqual(expanded["children"][0]["attributes"]["val"], {"type": "int"})


if __name__ == "__main__":
    unittest.main()
