import libcst as cst

from yapf.yapflib import style

VisitorLeaveUpdate = (
    cst.CSTNodeT | cst.RemovalSentinel | cst.FlattenSentinel[cst.CSTNodeT])


class BaseFormatter(cst.CSTTransformer):

  def __init__(self, module: cst.Module, config: style.Config):
    self._module = module
    self._config = config


class ModuleFormatter(BaseFormatter):

  def visit_Module(self, node: cst.Module) -> bool:
    if node is not self._module:
      raise ValueError(
          "Formatter is visiting a module its not been configured for.")
    return True

  def leave_Module(self, original_node: cst.Module,
                   updated_node: cst.Module) -> VisitorLeaveUpdate:
    return updated_node.with_changes(has_trailing_newline=True)

  def leave_IndentedBlock(
      self, original_node: cst.IndentedBlock,
      updated_node: cst.IndentedBlock) -> VisitorLeaveUpdate:
    indent_char = '\t' if self._config['USE_TABS'] else ' '
    indent = indent_char * self._config['INDENT_WIDTH']
    return updated_node.with_changes(indent=indent)

  def leave_Call(self, original_node: cst.Call,
                 updated_node: cst.Call) -> VisitorLeaveUpdate:

    return updated_node.with_changes(
        whitespace_after_func=cst.SimpleWhitespace(''))
