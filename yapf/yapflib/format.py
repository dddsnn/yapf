# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""TODO+++++++++++++
"""

import abc
import dataclasses as dc
import typing as t

import libcst as cst
import libcst.metadata as cst_meta

from yapf.yapflib import style

VisitorLeaveUpdate = (
    cst.CSTNodeT | cst.RemovalSentinel | cst.FlattenSentinel[cst.CSTNodeT])


class BaseFormatter(cst.CSTTransformer):
  """TODO+++++++++++
  """

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


# TODO change arch: first pass just fixing whitespace, pretending everything fits in one line.
# then on leave of a simplestatementline (or suite), start a new visitor that
# does the whole wrapping business++++++++++
class ModuleFormatter(BaseFormatter):
  """TODO+++++++++++
  TODO module from ctor must be the one we're visiting+++++
  """

  def __init__(self, module: cst.Module, config: style.Config):
    super().__init__(module, config)
    self._current_indent_level = 0
    # self._asd = None
    # print(module)
    # print('++++++++++++')

  def visit_Module(self, node: cst.Module) -> bool:
    if node is not self._module:
      print("------------")
      print(node)
      print(type(node))
      raise ValueError(
          "Module formatter is visiting a module its not been configured for.")
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
    # REFACTOR take indent string from config++++++++
    # TODO with tabs, disregard indend_width (only ever 1 tab)++++++++++++
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
    # updated = updated_node.visit(call_formatter)
    # self._asd = updated
    # return updated

  def leave_Import(self, original_node: cst.Import,
                   updated_node: cst.Import) -> VisitorLeaveUpdate:
    return updated_node.with_changes(
        whitespace_after_import=cst.SimpleWhitespace(' '))

  def leave_EmptyLine(self, original_node: cst.EmptyLine,
                      updated_node: cst.EmptyLine) -> VisitorLeaveUpdate:
    return cst.RemovalSentinel.REMOVE

  # TODO also SimpleStatementSuite?+++++
  def leave_SimpleStatementLine(
      self, original_node: cst.SimpleStatementLine,
      updated_node: cst.SimpleStatementLine) -> VisitorLeaveUpdate:
    # print(self._asd)
    # return updated_node.with_deep_changes(
    #     self._asd,
    #     whitespace_after_func=cst.SimpleWhitespace('                 '))
    # print('---------------')
    # print(self._module.code_for_node(updated_node))
    # print('---------------')
    # TODO test calls with the correct indent level+++++++++
    # PERF instead of creating a splitter for every line, check here whether the
    # line is short enough+++++++++++++
    # REFACTOR create the minimodule here and visit it with the splitter
    # directly? so the splitter doesn't have to visit it with itself?++++++
    # REFACTOR or use one line splitter for everything? call with every line?++++++
    # return updated_node.visit(TestTransformer())
    # return updated_node
    line_splitter = LineSplitter(self._config, updated_node,
                                 self._current_indent_level)
    return line_splitter.split_line()

  def leave_ClassDef(self, original_node: cst.ClassDef,
                     updated_node: cst.ClassDef) -> VisitorLeaveUpdate:
    # print('-----------')
    # print('-----------')
    # print(updated_node)
    return updated_node

  def leave_FunctionDef(self, original_node: cst.FunctionDef,
                        updated_node: cst.FunctionDef) -> VisitorLeaveUpdate:
    # print('-----------')
    # print(self._module.code_for_node(updated_node))
    # print('-----------')
    # print(updated_node)
    return updated_node


# REFACTOR should we just inline this again in the module formatter?+++++++
class CallFormatter(BaseFormatter):
  """TODO+++++++++++
  """

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
    # TODO we need to check this for a bunch of other things as well. check the
    # tests comma formatting in the module formatter, it's at least those, and
    #  probably a couple more++++++++
    if self._call.args and self._call.args[-1].comma is original_node:
      return super().leave_Comma(
          original_node, updated_node, no_whitespace_after=True)
    return super().leave_Comma(original_node, updated_node)


class SplitPoint(abc.ABC):

  def __init__(self, node: cst.CSTNode) -> None:
    self._node = node

  @abc.abstractmethod
  def split(self, line: cst.SimpleStatementLine):
    raise NotImplementedError


class CallSplitPoint(SplitPoint):

  def split(self, line: cst.SimpleStatementLine):
    return line.with_deep_changes(
        self._node,
        whitespace_before_args=cst.ParenthesizedWhitespace(
            last_line=cst.SimpleWhitespace(' ')))


@dc.dataclass(frozen=True)
class SplitInfo:
  end_column: int
  split_points: list[SplitPoint]


# REFACTOR is it possible to integrate this into visit calls of the LineSplitter
# itself? would it be useful?++++++++
# TODO also operate on other stuff than SimpleStatementLine+++++++
class SplitInfoProvider(cst.VisitorMetadataProvider):

  METADATA_DEPENDENCIES = (cst_meta.WhitespaceInclusivePositionProvider,)

  # TODO also SimpleStatementSuite, possibly others++++++++
  def __init__(self):
    super().__init__()
    self._first_line_leading_indent = 4  # TODO++++++++++
    self._split_points = {}

  def on_visit(self, node: cst.CSTNode) -> bool:
    super().on_visit(node)
    pos = self.get_metadata(cst_meta.WhitespaceInclusivePositionProvider, node)
    if pos.start.line != pos.end.line:
      # TODO we only handle nodes that are on a single line,right? this should work?++++++++++++
      self.set_metadata(node, None)
    else:
      split_points = self._split_points.setdefault(pos.start.line, [])
      # TODO the split points we're recording here may actually be before the node
      # we're recording them for (and may be the first ones if the line is already too long before the
      # first possible split point). add tests for this
      # TODO and also test that we never run into an infinite loop either where we
      # have lines that are too long but can't be broken, or where breaking them
      # doesn't make them shorter (e.g. because there is a function with a long
      # name and args are supposed to be aligned to the opening paren, but a
      # long arg name keeps spilling over the edge; adding newlines won't help)
      self.set_metadata(node, SplitInfo(pos.end.column, split_points))
    return True

  def visit_Call(self, node: cst.Call) -> bool:
    pos = self.get_metadata(cst_meta.WhitespaceInclusivePositionProvider, node)
    self._split_points.setdefault(pos.start.line,
                                  []).append(CallSplitPoint(node))

    return True


# TODO this implementation assumes that we always only look forward when
# splitting lines, i.e. when we make a decision "split here", it is correct, and
# we never need to go back to revisit it, no matter what follows in the line.
# is this assumption always correct? no, at the very least it doesn't work with
# coalescing brackets (although that's a very limited context we could handle)+++++++++++
# TODO we also need to handle SimpleStatementSuite, and possibly others+++++++
class LineSplitter(cst.CSTTransformer):
  """TODO+++++++++++
  """

  METADATA_DEPENDENCIES = (SplitInfoProvider,)

  def __init__(self, config: style.Config, line: cst.SimpleStatementLine,
               indent_level: int):
    self._config = config
    # TODO line necessary?++++++++
    if len(line.body) != 1:
      # TODO+++++++++++++++
      raise NotImplementedError
    self._line = line
    self._indent_level = indent_level
    self._split_point: t.Optional[SplitPoint] = None

  def split_line(self) -> cst.SimpleStatementLine:
    # REFACTOR this seems janky++++++++
    # TODO at least explain what and why we're doing here+++++++
    self._module = cst.Module(body=[self._line])

    lines = [
        line for line in self._module.code_for_node(self._line).split('\n')
        if line
    ]
    self._line_lengths = [len(line) for line in lines]
    self._line_lengths[0] += self._indent_level * self._config['INDENT_WIDTH']
    if all(l <= self._config['COLUMN_LIMIT'] for l in self._line_lengths):
      print('nothing to do here')
      return self._line
    wrapper = cst_meta.MetadataWrapper(self._module, unsafe_skip_copy=True)
    formatted_module = wrapper.visit(self)
    assert len(formatted_module.body) == 1
    formatted_line = formatted_module.body[0]
    assert isinstance(formatted_line, cst.SimpleStatementLine)
    return formatted_line

  def on_visit(self, node: cst.CSTNode) -> bool:
    if self._split_point:
      # We have already decided to split the line, no need to visit other nodes.
      return False
    return super().on_visit(node)

  def on_leave(self, original_node: cst.CSTNode,
               updated_node: cst.CSTNode) -> VisitorLeaveUpdate:
    split_info = self.get_metadata(SplitInfoProvider, original_node)
    if split_info and split_info.end_column > 70:
      print(f'{type(updated_node)} ends at {split_info.end_column}')
      if self._split_point:
        print('but a split has already been set')
      elif not split_info.split_points:
        print('but there are no available split points')
      else:
        print(
            f'setting split of {updated_node} to first of {len(split_info.split_points)} points'
        )
        self._split_point = split_info.split_points[0]
    return super().on_leave(original_node, updated_node)

  def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool:
    # TODO necessary?++++++++++
    if node is not self._line:
      raise ValueError(
          "Line splitter is visiting a line it's not been configured for.")
    return True

  # TODO also SimpleStatementSuite?+++++
  def leave_SimpleStatementLine(
      self, original_node: cst.SimpleStatementLine,
      updated_node: cst.SimpleStatementLine) -> VisitorLeaveUpdate:
    print('--------- line start ---------')
    if self._split_point:
      print('split has been set, applying')
      before = updated_node
      updated_node = self._split_point.split(self._line)
      print(before is updated_node)
      print(before.deep_equals(updated_node))
    # print(self.get_metadata(SplitInfoProvider, original_node.body[0]))
    print('--------- statements ---------')
    for statement in updated_node.body:
      print(self._module.code_for_node(statement))
    print('--------- original line ---------')
    print(self._module.code_for_node(original_node))
    print('--------- updated line ---------')
    updated_code = self._module.code_for_node(updated_node)
    lines = [line for line in updated_code.split('\n') if line]
    print(lines)
    print(updated_code)
    print('--------- line end ---------')
    return updated_node
