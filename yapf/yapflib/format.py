import libcst as cst

from yapf.yapflib import split, style

VisitorLeaveUpdate = (
    cst.CSTNodeT | cst.RemovalSentinel | cst.FlattenSentinel[cst.CSTNodeT])


class BaseFormatter(cst.CSTTransformer):

  def __init__(self, module: cst.Module, config: style.Config):
    self._module = module
    self._config = config

  def leave_Comma(self,
                  original_node: cst.Comma,
                  updated_node: cst.Comma,
                  *,
                  no_whitespace_after: bool = False) -> VisitorLeaveUpdate:
    whitespace_after_str = ' '
    if no_whitespace_after:
      whitespace_after_str = ''
    return updated_node.with_changes(
        whitespace_before=cst.SimpleWhitespace(''),
        whitespace_after=cst.SimpleWhitespace(whitespace_after_str))


class ModuleFormatter(BaseFormatter):

  def __init__(self, module: cst.Module, config: style.Config):
    super().__init__(module, config)
    self._current_indent_level = 0

  def visit_Module(self, node: cst.Module) -> bool:
    if node is not self._module:
      raise ValueError(
          "Moduel formatter is visiting a module its not been configured for.")
    return True

  def leave_Module(self, original_node: cst.Module,
                   updated_node: cst.Module) -> VisitorLeaveUpdate:
    return updated_node.with_changes(has_trailing_newline=True)

  def visit_IndentedBlock(self, node: cst.IndentedBlock) -> bool:
    self._current_indent_level += 1
    return True

  def leave_IndentedBlock(
      self, original_node: cst.IndentedBlock,
      updated_node: cst.IndentedBlock) -> VisitorLeaveUpdate:
    assert self._current_indent_level > 0
    self._current_indent_level -= 1
    indent_char = '\t' if self._config['USE_TABS'] else ' '
    indent = indent_char * self._config['INDENT_WIDTH']
    return updated_node.with_changes(indent=indent)

  def visit_Call(self, node: cst.Call) -> bool:
    # Handled on leave by a special formatter.
    return False

  def leave_Call(self, original_node: cst.Call,
                 updated_node: cst.Call) -> VisitorLeaveUpdate:
    assert original_node is updated_node  # We've not visited children.
    call_formatter = CallFormatter(self._module, self._config, updated_node)
    return updated_node.visit(call_formatter)

  def leave_SimpleStatementLine(
      self, original_node: cst.SimpleStatementLine,
      updated_node: cst.SimpleStatementLine) -> VisitorLeaveUpdate:
    return split.split_line(self._config, updated_node,
                            self._current_indent_level)


class CallFormatter(BaseFormatter):

  def __init__(self, module: cst.Module, config: style.Config, call: cst.Call):
    super().__init__(module, config)
    self._call = call
    self._call_formatter_stack = []

  def visit_Call(self, node: cst.Call) -> bool:
    if node is not self._call:
      # This is a nested call somewhere in ours, we want a different formatter
      # to handle it.
      self._call_formatter_stack.append(
          CallFormatter(self._module, self._config, node))
      return False
    return True

  def leave_Call(self, original_node: cst.Call,
                 updated_node: cst.Call) -> VisitorLeaveUpdate:
    try:
      call_formatter = self._call_formatter_stack.pop()
      # There is a nested formatter that handles this call.
      return updated_node.visit(call_formatter)
    except IndexError:
      if original_node is not self._call:
        raise ValueError(
            "Call formatter is leaving a call that's not its own, but there is "
            "no nested formatter.")
      return updated_node.with_changes(
          whitespace_after_func=cst.SimpleWhitespace(''),
          whitespace_before_args=cst.SimpleWhitespace(''))

  def leave_Arg(self, original_node: cst.Arg,
                updated_node: cst.Arg) -> VisitorLeaveUpdate:
    return updated_node.with_changes(
        whitespace_after_star=cst.SimpleWhitespace(''),
        whitespace_after_arg=cst.SimpleWhitespace(''))

  def leave_Comma(self, original_node: cst.Comma,
                  updated_node: cst.Comma) -> VisitorLeaveUpdate:
    if self._call.args and self._call.args[-1].comma is original_node:
      return super().leave_Comma(
          original_node, updated_node, no_whitespace_after=True)
    return super().leave_Comma(original_node, updated_node)
