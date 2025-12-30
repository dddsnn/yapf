import textwrap

import libcst as cst

from yapf.yapflib import format
from yapf.yapflib import style

from yapftests import yapf_test_helper


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
    formatter = format.CallFormatter(module, self.config)
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

  def testRemovesExtraneousWhitespaceAfterStars(self):
    unformatted_code = textwrap.dedent("""\
        function_name(*  args, **  kwargs)
    """)
    expected_formatted_code = textwrap.dedent("""\
        function_name(*args, **kwargs)
    """)
    self._Check(unformatted_code, expected_formatted_code)
