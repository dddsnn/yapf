import abc
import dataclasses as dc
import typing as t

import libcst as cst
import libcst.metadata as cst_meta

from yapf.yapflib import style

VisitorLeaveUpdate = (
    cst.CSTNodeT | cst.RemovalSentinel | cst.FlattenSentinel[cst.CSTNodeT])


def _indent_string(config: style.Config, indent_level: int) -> str:
  if config['USE_TABS']:
    return indent_level * '\t'
  return indent_level * config['INDENT_WIDTH'] * ' '


def _visual_line_string(config: style.Config, s: str) -> str:
  return s.replace('\t', _indent_string(config, 1))


def split_line(config: style.Config, line: cst.SimpleStatementLine,
               current_indent_level: int) -> cst.SimpleStatementLine:
  module = cst.Module(body=[line])
  while True:
    visual_line_strings = list(
        filter(None, (module.code_for_node(line).split('\n'))))
    # The first line has no indent, we need to add it back.
    visual_line_strings[0] = (
        _indent_string(config, current_indent_level) + visual_line_strings[0])
    # Make sure the length of each line string corresponds to the visual length
    # (i.e. expanded tabs).
    visual_line_strings = [
        _visual_line_string(config, s) for s in visual_line_strings
    ]
    wrapper = cst_meta.MetadataWrapper(module, unsafe_skip_copy=True)
    line_splitter = LineSplitter(config, line, visual_line_strings)
    module = wrapper.visit(line_splitter)
    assert len(module.body) == 1
    line = module.body[0]
    assert isinstance(line, cst.SimpleStatementLine)
    if not line_splitter.has_done_split:
      break
  return line


class SplitPoint(abc.ABC):

  def __init__(self, node: cst.CSTNode, remaining_line_length: int) -> None:
    self._node = node
    self._remaining_line_length = remaining_line_length

  @abc.abstractmethod
  def split(self, line: cst.SimpleStatementLine) -> cst.SimpleStatementLine:
    raise NotImplementedError

  @property
  @abc.abstractmethod
  def remaining_line_length(self) -> int:
    raise NotImplementedError


class CallSplitPoint(SplitPoint):

  def split(self, line: cst.SimpleStatementLine) -> cst.SimpleStatementLine:
    return line.with_deep_changes(
        self._node,
        whitespace_before_args=cst.ParenthesizedWhitespace(
            last_line=cst.SimpleWhitespace(' ')))

  @property
  def remaining_line_length(self):
    return self._remaining_line_length


@dc.dataclass(frozen=True)
class SplitInfo:
  local_line_number: int
  end_column: int
  split_points: list[SplitPoint]


class SplitInfoProvider(cst.VisitorMetadataProvider):

  METADATA_DEPENDENCIES = (cst_meta.WhitespaceInclusivePositionProvider,)

  def __init__(self):
    super().__init__()
    self._split_points = {}

  def on_visit(self, node: cst.CSTNode) -> bool:
    super().on_visit(node)
    pos = self.get_metadata(cst_meta.WhitespaceInclusivePositionProvider, node)
    if pos.start.line != pos.end.line:
      self.set_metadata(node, None)
    else:
      split_points = self._split_points.setdefault(pos.start.line, [])
      split_info = SplitInfo(pos.start.line, pos.end.column, split_points)
      self.set_metadata(node, split_info)
    return True

  def visit_Call(self, node: cst.Call) -> bool:
    pos = self.get_metadata(cst_meta.WhitespaceInclusivePositionProvider, node)
    remaining_line_length = self.get_metadata(
        cst_meta.WhitespaceInclusivePositionProvider,
        node.whitespace_before_args).start.column
    self._split_points.setdefault(pos.start.line, []).append(
        CallSplitPoint(node, remaining_line_length))
    return True


class LineSplitter(cst.CSTTransformer):

  METADATA_DEPENDENCIES = (SplitInfoProvider,)

  def __init__(self, config: style.Config, line: cst.SimpleStatementLine,
               visual_line_strings: list[str]):
    if len(line.body) != 1:
      raise NotImplementedError
    self._config = config
    self._line = line
    self._visual_line_strings = visual_line_strings
    self._split_point: t.Optional[SplitPoint] = None

  @property
  def has_done_split(self) -> bool:
    return self._split_point is not None

  def on_visit(self, node: cst.CSTNode) -> bool:
    if self._split_point:
      # We have already decided to split the line, no need to visit other nodes.
      return False
    return super().on_visit(node)

  def on_leave(self, original_node: cst.CSTNode,
               updated_node: cst.CSTNode) -> VisitorLeaveUpdate:
    if self._split_point:
      # We have already decided where to split the line, no need to keep
      # searching.
      return super().on_leave(original_node, updated_node)
    split_info = self.get_metadata(SplitInfoProvider, original_node)
    if not split_info:
      return super().on_leave(original_node, updated_node)
    visual_line = self._visual_line_strings[split_info.local_line_number - 1]
    if len(visual_line) > self._config["COLUMN_LIMIT"]:
      if split_info.split_points:
        # Use the first available split point.
        split_point = split_info.split_points[0]
        line_length_after_split = split_point.remaining_line_length
        if line_length_after_split >= split_info.end_column:
          pass
        else:
          self._split_point = split_info.split_points[0]
    return super().on_leave(original_node, updated_node)

  def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool:
    if node is not self._line:
      raise ValueError(
          "Line splitter is visiting a line it's not been configured for.")
    return True

  def leave_SimpleStatementLine(
      self, original_node: cst.SimpleStatementLine,
      updated_node: cst.SimpleStatementLine) -> VisitorLeaveUpdate:
    if self._split_point:
      updated_node = self._split_point.split(self._line)
    return updated_node
