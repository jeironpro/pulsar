import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pulsar import (
    lex_psr, parse, build_document, build_block, dump_psr,
    dump_value, serialize_block, validate_psr, resolve_value,
    ValueNode, BlockNode, AttributeNode, PSRLexError, PSRParseError,
    _comment_end, _type_matches, _expand_psr_schema
)


class TestLexer(unittest.TestCase):

    def test_basic_tokens(self):
        tokens = lex_psr('-> user\n    name >> Juan\n<-\n')
        types = [t['type'] for t in tokens]
        self.assertIn('BLOCK_START', types)
        self.assertIn('BLOCK_END', types)
        self.assertIn('ATTRIBUTE', types)
        self.assertIn('EOF', types)

    def test_block_start_value(self):
        tokens = lex_psr('-> user\n<-\n')
        self.assertEqual(tokens[0]['value'], 'user')

    def test_block_end(self):
        tokens = lex_psr('-> x\n<-\n')
        self.assertEqual(tokens[1]['type'], 'BLOCK_END')

    def test_attribute_key_value(self):
        tokens = lex_psr('-> x\n    age >> 30\n<-\n')
        attr = [t for t in tokens if t['type'] == 'ATTRIBUTE'][0]
        self.assertEqual(attr['key'], 'age')
        self.assertEqual(attr['value'], '30')

    def test_empty_file(self):
        tokens = lex_psr('')
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0]['type'], 'EOF')

    def test_comment_full_line(self):
        tokens = lex_psr(':: comment\n-> x\n<-\n')
        self.assertEqual(tokens[0]['type'], 'BLOCK_START')

    def test_inline_comment(self):
        tokens = lex_psr('-> x\n    name >> Juan :: comment\n<-\n')
        attr = [t for t in tokens if t['type'] == 'ATTRIBUTE'][0]
        self.assertEqual(attr['value'], 'Juan')

    def test_comment_inside_quotes_preserved(self):
        tokens = lex_psr('-> x\n    name >> "hello :: world"\n<-\n')
        attr = [t for t in tokens if t['type'] == 'ATTRIBUTE'][0]
        self.assertEqual(attr['value'], '"hello :: world"')

    def test_column_tracking(self):
        tokens = lex_psr('-> user\n<-\n')
        start = [t for t in tokens if t['type'] == 'BLOCK_START'][0]
        end = [t for t in tokens if t['type'] == 'BLOCK_END'][0]
        self.assertIn('column', start)
        self.assertIn('column', end)

    def test_multiline(self):
        tokens = lex_psr('-> x\n    bio >> <<\nline1\nline2\n>>\n<-\n')
        attr = [t for t in tokens if t['type'] == 'ATTRIBUTE'][0]
        self.assertEqual(attr['value'], 'line1\nline2')
        self.assertEqual(attr['key'], 'bio')

    def test_error_empty_block_name(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-> \n<-\n')

    def test_error_bad_block_name(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-> 123bad\n<-\n')

    def test_error_bad_attr_name(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-> x\n    123name >> val\n<-\n')

    def test_error_comma_in_value(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-> x\n    name >> Juan,\n<-\n')

    def test_error_incomplete_operator_dash(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-bad\n')

    def test_error_incomplete_operator_lt(self):
        with self.assertRaises(PSRLexError):
            lex_psr('<bad\n')

    def test_error_unclosed_multiline(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-> x\n    bio >> <<\ncontent\n<-\n')

    def test_error_missing_key(self):
        with self.assertRaises(PSRLexError):
            lex_psr('-> x\n    >> val\n<-\n')

    def test_whitespace_lines_skipped(self):
        tokens = lex_psr('\n\n-> x\n\n<-\n\n')
        self.assertEqual(tokens[0]['type'], 'BLOCK_START')

    def test_identifier_regex_valid(self):
        tokens = lex_psr('-> my-var_1\n<-\n')
        self.assertEqual(tokens[0]['value'], 'my-var_1')


class TestParser(unittest.TestCase):

    def test_simple_block(self):
        ast = parse(lex_psr('-> user\n<-\n'))
        self.assertEqual(len(ast), 1)
        self.assertEqual(ast[0].name, 'user')

    def test_multiple_blocks(self):
        ast = parse(lex_psr('-> a\n<-\n-> b\n<-\n'))
        self.assertEqual(len(ast), 2)
        self.assertEqual(ast[0].name, 'a')
        self.assertEqual(ast[1].name, 'b')

    def test_nested_block(self):
        ast = parse(lex_psr('-> a\n    -> b\n    <-\n<-\n'))
        self.assertEqual(len(ast), 1)
        self.assertEqual(len(ast[0].children), 1)
        self.assertEqual(ast[0].children[0].name, 'b')

    def test_attributes(self):
        ast = parse(lex_psr('-> a\n    x >> 1\n    y >> hello\n<-\n'))
        attrs = ast[0].attributes
        self.assertEqual(len(attrs), 2)
        self.assertEqual(attrs[0].key, 'x')
        self.assertEqual(attrs[1].key, 'y')

    def test_error_unclosed_block(self):
        with self.assertRaises(PSRParseError):
            parse(lex_psr('-> a\n'))

    def test_error_close_without_open(self):
        with self.assertRaises(PSRParseError):
            parse(lex_psr('<-\n'))

    def test_error_attribute_outside_block(self):
        with self.assertRaises(PSRParseError):
            parse(lex_psr('x >> 1\n'))

    def test_empty_document(self):
        ast = parse(lex_psr(''))
        self.assertEqual(ast, [])


class TestBuilder(unittest.TestCase):

    def test_simple_document(self):
        ast = parse(lex_psr('-> user\n    name >> Juan\n<-\n'))
        doc = build_document(ast)
        self.assertEqual(doc[0]['tipo'], 'user')
        self.assertEqual(doc[0]['atributos']['name'], 'Juan')

    def test_int_value(self):
        ast = parse(lex_psr('-> x\n    n >> 42\n<-\n'))
        doc = build_document(ast)
        self.assertIsInstance(doc[0]['atributos']['n'], int)
        self.assertEqual(doc[0]['atributos']['n'], 42)

    def test_float_value(self):
        ast = parse(lex_psr('-> x\n    n >> 3.14\n<-\n'))
        doc = build_document(ast)
        self.assertIsInstance(doc[0]['atributos']['n'], float)
        self.assertEqual(doc[0]['atributos']['n'], 3.14)

    def test_bool_true(self):
        ast = parse(lex_psr('-> x\n    flag >> true\n<-\n'))
        doc = build_document(ast)
        self.assertIsInstance(doc[0]['atributos']['flag'], bool)
        self.assertTrue(doc[0]['atributos']['flag'])

    def test_bool_false(self):
        ast = parse(lex_psr('-> x\n    flag >> false\n<-\n'))
        doc = build_document(ast)
        self.assertFalse(doc[0]['atributos']['flag'])

    def test_list_value(self):
        ast = parse(lex_psr('-> x\n    items >> a | b | c\n<-\n'))
        doc = build_document(ast)
        self.assertEqual(doc[0]['atributos']['items'], ['a', 'b', 'c'])

    def test_quoted_string(self):
        ast = parse(lex_psr('-> x\n    name >> "Juan Perez"\n<-\n'))
        doc = build_document(ast)
        self.assertEqual(doc[0]['atributos']['name'], 'Juan Perez')

    def test_object_value(self):
        ast = parse(lex_psr('-> x\n    m >> { city >> Madrid | country >> Spain }\n<-\n'))
        doc = build_document(ast)
        obj = doc[0]['atributos']['m']
        self.assertIsInstance(obj, dict)
        self.assertEqual(obj['city'], 'Madrid')
        self.assertEqual(obj['country'], 'Spain')

    def test_multiline_value(self):
        ast = parse(lex_psr('-> x\n    bio >> <<\nline1\nline2\n>>\n<-\n'))
        doc = build_document(ast)
        self.assertEqual(doc[0]['atributos']['bio'], 'line1\nline2')

    def test_nested_build(self):
        ast = parse(lex_psr('-> a\n    -> b\n        x >> 1\n    <-\n<-\n'))
        doc = build_document(ast)
        self.assertEqual(doc[0]['hijos'][0]['tipo'], 'b')
        self.assertEqual(doc[0]['hijos'][0]['atributos']['x'], 1)

    def test_duplicate_key_error(self):
        ast = parse(lex_psr('-> a\n    x >> 1\n    x >> 2\n<-\n'))
        with self.assertRaises(PSRParseError):
            build_document(ast)


class TestSerializer(unittest.TestCase):

    def test_serialize_basic(self):
        data = [{'tipo': 'user', 'atributos': {'name': 'Juan'}, 'hijos': []}]
        text = dump_psr(data)
        self.assertIn('-> user', text)
        self.assertIn('name >> Juan', text)
        self.assertIn('<-', text)

    def test_serialize_int(self):
        data = [{'tipo': 'x', 'atributos': {'n': 42}, 'hijos': []}]
        text = dump_psr(data)
        self.assertIn('n >> 42', text)

    def test_serialize_bool(self):
        data = [{'tipo': 'x', 'atributos': {'a': True, 'b': False}, 'hijos': []}]
        text = dump_psr(data)
        self.assertIn('a >> true', text)
        self.assertIn('b >> false', text)

    def test_serialize_list(self):
        data = [{'tipo': 'x', 'atributos': {'items': ['a', 'b', 'c']}, 'hijos': []}]
        text = dump_psr(data)
        self.assertIn('a | b | c', text)

    def test_serialize_object(self):
        data = [{'tipo': 'x', 'atributos': {'m': {'city': 'Madrid'}}, 'hijos': []}]
        text = dump_psr(data)
        self.assertIn('{ city >> Madrid }', text)

    def test_serialize_nested(self):
        data = [{'tipo': 'a', 'atributos': {}, 'hijos': [
            {'tipo': 'b', 'atributos': {'x': 1}, 'hijos': []}
        ]}]
        text = dump_psr(data)
        self.assertIn('-> a', text)
        self.assertIn('-> b', text)
        self.assertIn('x >> 1', text)

    def test_round_trip_simple(self):
        original = '-> user\n    name >> Juan\n    age >> 30\n<-\n'
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def test_round_trip_all_types(self):
        original = (
            '-> item\n'
            '    name >> "hello world"\n'
            '    count >> 42\n'
            '    ratio >> 3.14\n'
            '    flag >> true\n'
            '    tags >> a | b | c\n'
            '    meta >> { x >> 1 | y >> 2 }\n'
            '<-\n'
        )
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def test_round_trip_multiline(self):
        original = '-> x\n    bio >> <<\nline1\nline2\n>>\n<-\n'
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)

    def test_round_trip_nested(self):
        original = (
            '-> parent\n'
            '    name >> root\n'
            '    -> child\n'
            '        val >> 1\n'
            '    <-\n'
            '<-\n'
        )
        ast = parse(lex_psr(original))
        data = build_document(ast)
        text = dump_psr(data)
        ast2 = parse(lex_psr(text))
        data2 = build_document(ast2)
        self.assertEqual(data, data2)


class TestValidator(unittest.TestCase):

    def test_valid_simple(self):
        data = [{'tipo': 'user', 'atributos': {'name': 'Juan'}, 'hijos': []}]
        schema = {'tipo': 'user', 'atributos': {'name': {'tipo': 'str'}}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])

    def test_wrong_tipo(self):
        data = [{'tipo': 'admin', 'atributos': {}, 'hijos': []}]
        schema = {'tipo': 'user', 'atributos': {}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_missing_required_attr(self):
        data = [{'tipo': 'user', 'atributos': {}, 'hijos': []}]
        schema = {'tipo': 'user', 'atributos': {'name': {'tipo': 'str', 'obligatorio': True}}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_wrong_type_int(self):
        data = [{'tipo': 'x', 'atributos': {'n': 'hello'}, 'hijos': []}]
        schema = {'tipo': 'x', 'atributos': {'n': {'tipo': 'int'}}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_wrong_type_bool_not_int(self):
        data = [{'tipo': 'x', 'atributos': {'n': True}, 'hijos': []}]
        schema = {'tipo': 'x', 'atributos': {'n': {'tipo': 'int'}}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_list_type(self):
        data = [{'tipo': 'x', 'atributos': {'items': [1, 2, 3]}, 'hijos': []}]
        schema = {'tipo': 'x', 'atributos': {'items': {'tipo': 'list', 'items_tipo': 'int'}}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])

    def test_list_type_wrong_item(self):
        data = [{'tipo': 'x', 'atributos': {'items': [1, 'bad', 3]}, 'hijos': []}]
        schema = {'tipo': 'x', 'atributos': {'items': {'tipo': 'list', 'items_tipo': 'int'}}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_extra_children(self):
        data = [{'tipo': 'x', 'atributos': {}, 'hijos': [
            {'tipo': 'y', 'atributos': {}, 'hijos': []}
        ]}]
        schema = {'tipo': 'x', 'atributos': {}, 'hijos': []}
        errs = validate_psr(data, schema)
        self.assertGreater(len(errs), 0)

    def test_valid_children(self):
        data = [{'tipo': 'x', 'atributos': {}, 'hijos': [
            {'tipo': 'y', 'atributos': {'val': 1}, 'hijos': []}
        ]}]
        schema = {'tipo': 'x', 'atributos': {}, 'hijos': [
            {'tipo': 'y', 'atributos': {'val': {'tipo': 'int'}}, 'hijos': []}
        ]}
        errs = validate_psr(data, schema)
        self.assertEqual(errs, [])


class TestEdgeCases(unittest.TestCase):

    def test_deep_nesting_blocked(self):
        root = BlockNode('root', 1)
        cur = root
        for _ in range(201):
            child = BlockNode('child', 1)
            cur.children.append(child)
            cur = child
        with self.assertRaises(PSRParseError):
            build_block(root)

    def test_value_node_kind_int(self):
        v = ValueNode('42')
        self.assertEqual(v.kind, 'int')
        self.assertEqual(v.value, 42)

    def test_value_node_kind_float(self):
        v = ValueNode('3.14')
        self.assertEqual(v.kind, 'float')
        self.assertEqual(v.value, 3.14)

    def test_value_node_kind_bool(self):
        v = ValueNode('true')
        self.assertEqual(v.kind, 'bool')
        self.assertTrue(v.value)

    def test_value_node_kind_string(self):
        v = ValueNode('hello')
        self.assertEqual(v.kind, 'string')
        self.assertEqual(v.value, 'hello')

    def test_value_node_kind_list(self):
        v = ValueNode('a | b | c')
        self.assertEqual(v.kind, 'list')
        self.assertEqual(len(v.value), 3)

    def test_value_node_kind_quoted(self):
        v = ValueNode('"hello world"')
        self.assertEqual(v.kind, 'string')
        self.assertEqual(v.value, 'hello world')

    def test_value_node_kind_object(self):
        v = ValueNode('{ x >> 1 | y >> 2 }')
        self.assertEqual(v.kind, 'object')
        self.assertEqual(v.value['x'], 1)
        self.assertEqual(v.value['y'], 2)

    def test_comment_end(self):
        self.assertEqual(_comment_end('x :: y'), 2)
        self.assertEqual(_comment_end('"x :: y"'), -1)
        self.assertEqual(_comment_end('no comment'), -1)

    def test_type_matches_int(self):
        self.assertTrue(_type_matches('int', 42))
        self.assertFalse(_type_matches('int', True))

    def test_type_matches_bool(self):
        self.assertTrue(_type_matches('bool', True))
        self.assertFalse(_type_matches('bool', 42))

    def test_type_matches_unknown(self):
        self.assertTrue(_type_matches('unknown_type', 'anything'))


class TestExpandPsrSchema(unittest.TestCase):

    def test_expand_simple(self):
        block = {'tipo': 'user', 'atributos': {'name': 'str'}, 'hijos': []}
        expanded = _expand_psr_schema(block)
        self.assertEqual(expanded['atributos']['name'], {'tipo': 'str'})

    def test_expand_nested(self):
        block = {'tipo': 'x', 'atributos': {}, 'hijos': [
            {'tipo': 'y', 'atributos': {'val': 'int'}, 'hijos': []}
        ]}
        expanded = _expand_psr_schema(block)
        self.assertEqual(expanded['hijos'][0]['atributos']['val'], {'tipo': 'int'})


if __name__ == '__main__':
    unittest.main()
