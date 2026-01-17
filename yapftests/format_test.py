import textwrap
import unittest.mock as um

import libcst as cst
import pytest
from precisely import anything, assert_that

from yapf.yapflib import format, split, style
from yapftests import yapf_test_helper
from yapftests.utils import called_exactly_with, mock_call


class MockedSplitLine(um.Mock):

  def __init__(self):
    super().__init__(spec=split.split_line, side_effect=self.call)
    self._return_lines = None

  def call(self, config: style.Config, line: cst.SimpleStatementLine,
           current_indent_level: int) -> cst.SimpleStatementLine:
    if self._return_lines is not None:
      return self._return_lines.pop(0)
    return line

  def append_return_line(self, line_string: str):
    line = cst.parse_statement(line_string)
    assert isinstance(line, cst.SimpleStatementLine)
    self._return_lines = self._return_lines or []
    self._return_lines.append(line)


@pytest.fixture(autouse=True)
def mocked_split_line(monkeypatch: pytest.MonkeyPatch) -> MockedSplitLine:
  monkeypatch.setattr(split, 'split_line', MockedSplitLine())
  return split.split_line


class FormatterTest(yapf_test_helper.YAPFTest):

  def setUp(self):  # pylint: disable=g-missing-super-call
    self.config = style.CreatePEP8Style()


class ModuleFormatterTest(FormatterTest):

  def _Check(self, unformatted_code, expected_formatted_code):
    module = cst.parse_module(unformatted_code)
    formatter = format.ModuleFormatter(module, self.config)
    formatted_module = module.visit(formatter)
    self.assertCodeEqual(expected_formatted_code, formatted_module.code)

  def testOnlyAddsNewlineOnEmptyModule(self):
    self._Check('', '\n')

  def testChangesIndentWidthWithOneLevel(self):
    self.config['INDENT_WIDTH'] = 3
    unformatted_code = textwrap.dedent("""\
        if True:
         pass
    """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
           pass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testChangesIndentWidthWithMultipleLevels(self):
    self.config['INDENT_WIDTH'] = 3
    unformatted_code = textwrap.dedent("""\
        if True:
         if True:
              if True:
                pass
    """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
           if True:
              if True:
                 pass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testUsesSingleTabForIndent(self):
    self.config['USE_TABS'] = True
    self.config['INDENT_WIDTH'] = 1
    unformatted_code = textwrap.dedent("""\
        if True:
          pass
    """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
        \tpass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testUsesMultipleTabsForIndent(self):
    self.config['USE_TABS'] = True
    self.config['INDENT_WIDTH'] = 2
    unformatted_code = textwrap.dedent("""\
        if True:
          pass
    """)
    expected_formatted_code = textwrap.dedent("""\
          if True:
          \t\tpass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testKeepsExistingNewlineAtEof(self):
    code = textwrap.dedent("""\
        if True:
            pass
    """)
    self._Check(code, code)

  def testAddsMissingNewlineAtEof(self):
    unformatted_code = textwrap.dedent("""\
          if True:
            pass""")
    expected_formatted_code = textwrap.dedent("""\
          if True:
              pass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInArgs(self):
    unformatted_code = textwrap.dedent("""\
        function_name(arg1,    arg2,  arg3)
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(arg1, arg2, arg3)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInArgs(self):
    unformatted_code = textwrap.dedent("""\
        function_name(arg1,arg2,arg3)
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(arg1, arg2, arg3)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInImport(self):
    unformatted_code = textwrap.dedent("""\
        import a  ,  b
    """)
    expected_formatted_code = textwrap.dedent("""\
        import a, b
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInImport(self):
    unformatted_code = textwrap.dedent("""\
        import a,b
    """)
    expected_formatted_code = textwrap.dedent("""\
        import a, b
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInImportFrom(self):
    unformatted_code = textwrap.dedent("""\
        from x import a  ,  b
    """)
    expected_formatted_code = textwrap.dedent("""\
        from x import a, b
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInImportFrom(self):
    unformatted_code = textwrap.dedent("""\
        from x import a,b
    """)
    expected_formatted_code = textwrap.dedent("""\
        from x import a, b
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInParams(self):
    unformatted_code = textwrap.dedent("""\
        def f(a  ,  b):
            pass
    """)
    expected_formatted_code = textwrap.dedent("""\
        def f(a, b):
            pass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInParams(self):
    unformatted_code = textwrap.dedent("""\
        def f(a,b):
            pass
    """)
    expected_formatted_code = textwrap.dedent("""\
        def f(a, b):
            pass
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInTuple(self):
    unformatted_code = textwrap.dedent("""\
        (a  ,  b)
    """)
    expected_formatted_code = textwrap.dedent("""\
        (a, b)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInTuple(self):
    unformatted_code = textwrap.dedent("""\
        (a,b)
    """)
    expected_formatted_code = textwrap.dedent("""\
        (a, b)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInList(self):
    unformatted_code = textwrap.dedent("""\
        [a  ,  b]
    """)
    expected_formatted_code = textwrap.dedent("""\
        [a, b]
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInList(self):
    unformatted_code = textwrap.dedent("""\
        [a,b]
    """)
    expected_formatted_code = textwrap.dedent("""\
        [a, b]
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInSet(self):
    unformatted_code = textwrap.dedent("""\
        {a  ,  b}
    """)
    expected_formatted_code = textwrap.dedent("""\
        {a, b}
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInSet(self):
    unformatted_code = textwrap.dedent("""\
        {a,b}
    """)
    expected_formatted_code = textwrap.dedent("""\
        {a, b}
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAroundCommasInDict(self):
    unformatted_code = textwrap.dedent("""\
        {a: None  ,  b: None}
    """)
    expected_formatted_code = textwrap.dedent("""\
        {a: None, b: None}
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testAddsMissingWhitespaceAroundCommasInDict(self):
    unformatted_code = textwrap.dedent("""\
        {a: None,b: None}
    """)
    expected_formatted_code = textwrap.dedent("""\
        {a: None, b: None}
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testCallsLineFormatterOnSingleLine(self):
    split.split_line.append_return_line('b = 2')
    unformatted_code = textwrap.dedent("""\
        a = 1
    """)
    expected_formatted_code = textwrap.dedent("""\
        b = 2
    """)
    self._Check(unformatted_code, expected_formatted_code)
    assert_that(split.split_line,
                called_exactly_with(mock_call(self.config, anything, 0)))

  def testCallsLineFormatterOnMultipleLines(self):
    split.split_line.append_return_line('b = 2')
    split.split_line.append_return_line('y = 20')
    unformatted_code = textwrap.dedent("""\
          a = 1
          x = 10
      """)
    expected_formatted_code = textwrap.dedent("""\
          b = 2
          y = 20
      """)
    self._Check(unformatted_code, expected_formatted_code)
    assert_that(
        split.split_line,
        called_exactly_with(
            mock_call(self.config, anything, 0),
            mock_call(self.config, anything, 0)))

  def testCallsLineFormatterWithCorrectIndent(self):
    split.split_line.append_return_line('b = 2')
    split.split_line.append_return_line('y = 20')
    unformatted_code = textwrap.dedent("""\
          if True:
              a = 1
              if True:
                  x = 10
      """)
    expected_formatted_code = textwrap.dedent("""\
          if True:
              b = 2
              if True:
                  y = 20
      """)
    self._Check(unformatted_code, expected_formatted_code)
    assert_that(
        split.split_line,
        called_exactly_with(
            mock_call(self.config, anything, 1),
            mock_call(self.config, anything, 2)))


class CallFormatterTest(FormatterTest):

  def _Check(self, unformatted_code, expected_formatted_code):
    module = cst.parse_module(unformatted_code)
    assert len(module.body) == 1
    line = module.body[0]
    assert len(line.body) == 1 and isinstance(line, cst.SimpleStatementLine)
    expr = line.body[0]
    assert isinstance(expr, cst.Expr)
    call = expr.value
    assert isinstance(call, cst.Call)
    formatter = format.CallFormatter(module, self.config, call)
    formatted_call = call.visit(formatter)
    formatted_module = module.deep_replace(call, formatted_call)
    self.assertCodeEqual(expected_formatted_code, formatted_module.code)

  def testRemovesWhitespaceBeforeArgsList(self):
    unformatted_code = textwrap.dedent("""\
        function_name ()
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name()
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesWhitespaceInEmptyArgsList(self):
    unformatted_code = textwrap.dedent("""\
        function_name(   )
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name()
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesWhitespaceBeforeFirstArg(self):
    unformatted_code = textwrap.dedent("""\
        function_name(  arg1, arg2)
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(arg1, arg2)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAfterLastArg(self):
    unformatted_code = textwrap.dedent("""\
        function_name(arg1, arg2, arg3   )
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(arg1, arg2, arg3)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAfterStars(self):
    unformatted_code = textwrap.dedent("""\
        function_name(*  args, **  kwargs)
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(*args, **kwargs)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testRemovesExtraneousWhitespaceAfterTrailingCommaInArgsList(self):
    self.config['DISABLE_TRAILING_COMMA_HEURISTIC'] = True
    unformatted_code = textwrap.dedent("""\
        function_name(arg1, arg2,   )
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(arg1, arg2,)
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testFormatsSingleNestedCall(self):
    self.config['DISABLE_TRAILING_COMMA_HEURISTIC'] = True
    unformatted_code = textwrap.dedent("""\
        f1( a , f2 (b,c, ) )
    """)
    expected_formatted_code = textwrap.dedent("""\
        f1(a, f2(b, c,))
    """)
    self._Check(unformatted_code, expected_formatted_code)

  def testFormatsMultipleNestedCalls(self):
    self.config['DISABLE_TRAILING_COMMA_HEURISTIC'] = True
    unformatted_code = textwrap.dedent("""\
        f1( a , f2 (f3(b,c,),d, ) )
    """)
    expected_formatted_code = textwrap.dedent("""\
        f1(a, f2(f3(b, c,), d,))
    """)
    self._Check(unformatted_code, expected_formatted_code)
