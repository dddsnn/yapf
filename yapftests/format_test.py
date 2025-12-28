import textwrap

import libcst as cst

from yapf.yapflib import format
from yapf.yapflib import style

from yapftests import yapf_test_helper


class ModuleFormatterTest(yapf_test_helper.YAPFTest):

  def setUp(self):  # pylint: disable=g-missing-super-call
    self.config = style.CreatePEP8Style()

  def _Check(self, unformatted_code, expected_formatted_code):
    module = cst.parse_module(unformatted_code)
    formatter = format.ModuleFormatter(module, self.config)
    formatted_module = module.visit(formatter)
    self.assertCodeEqual(expected_formatted_code, formatted_module.code)

  def testDoesNothingOnEmptyModule(self):
    self._Check('', '')

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
