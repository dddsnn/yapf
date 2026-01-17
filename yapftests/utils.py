# -*- coding: utf-8 -*-
# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utilities for tests."""

import contextlib
import io
import os
import sys
import tempfile
import unittest.mock as um

import precisely.base
import precisely.coercion
import precisely.results


@contextlib.contextmanager
def stdout_redirector(stream):  # pylint: disable=invalid-name
  old_stdout = sys.stdout
  sys.stdout = stream
  try:
    yield
  finally:
    sys.stdout = old_stdout


# NamedTemporaryFile is useless because on Windows the temporary file would be
# created with O_TEMPORARY, which would not allow the file to be opened a
# second time, even by the same process, unless the same flag is used.
# Thus we provide a simplified version ourselves.
#
# Note: returns a tuple of (io.file_obj, file_path), instead of a file_obj with
# a .name attribute
#
# Note: `buffering` is set to -1 despite documentation of NamedTemporaryFile
# says None. This is probably a problem with the python documentation.
@contextlib.contextmanager
def NamedTempFile(mode='w+b',
                  buffering=-1,
                  encoding=None,
                  errors=None,
                  newline=None,
                  suffix=None,
                  prefix=None,
                  dirname=None,
                  text=False):
  """Context manager creating a new temporary file in text mode."""
  (fd, fname) = tempfile.mkstemp(
      suffix=suffix, prefix=prefix, dir=dirname, text=text)
  f = io.open(
      fd,
      mode=mode,
      buffering=buffering,
      encoding=encoding,
      errors=errors,
      newline=newline)
  yield f, fname
  f.close()
  os.remove(fname)


@contextlib.contextmanager
def TempFileContents(dirname,
                     contents,
                     encoding='utf-8',
                     newline='',
                     suffix=None):
  # Note: NamedTempFile properly handles unicode encoding when using mode='w'
  with NamedTempFile(
      dirname=dirname,
      mode='w',
      encoding=encoding,
      newline=newline,
      suffix=suffix) as (f, fname):
    f.write(contents)
    f.flush()
    yield fname


class MockCallMatcher(precisely.base.Matcher):

  def __init__(self, call_args, call_kwargs):
    self._call_args = call_args
    self._call_kwargs = call_kwargs

  def match(self, actual) -> precisely.results.Result:
    if not isinstance(actual, um._Call):
      return precisely.results.unmatched('was not a mock call')
    actual_args, actual_kwargs = actual
    if len(self._call_args) != len(actual_args):
      return precisely.results.unmatched(
          f'expected {len(self._call_args)} args, but got {len(actual_args)}')
    if set(self._call_kwargs) != set(actual_kwargs):
      return precisely.results.unmatched(
          f'expected kwargs {set(self._call_kwargs)}, but got '
          f'{set(actual_kwargs)}')
    for i, (arg, actual_arg) in enumerate(zip(self._call_args, actual_args)):
      result = precisely.coercion.to_matcher(arg).match(actual_arg)
      if not result.is_match:
        return precisely.results.unmatched('arg {} {}'.format(
            i, result.explanation))
    for key in self._call_kwargs:
      kwarg = self._call_kwargs[key]
      actual_kwarg = actual_kwargs[key]
      result = precisely.coercion.to_matcher(kwarg).match(actual_kwarg)
      if not result.is_match:
        return precisely.results.unmatched('kwarg {} {}'.format(
            key, result.explanation))
    return precisely.results.matched()

  def describe(self):
    return 'a mock call with:{}'.format(
        precisely.results.indented_list(
            [self._describe_args(),
             self._describe_kwargs()]))

  def _describe_args(self):
    if not self._call_args:
      return 'no args'
    return 'args:{}'.format(
        precisely.results.indented_list(
            precisely.coercion.to_matcher(arg).describe()
            for arg in self._call_args))

  def _describe_kwargs(self):
    if not self._call_kwargs:
      return 'no kwargs'
    return 'kwargs:{}'.format(
        precisely.results.indented_list([
            '{}={}'.format(key,
                           precisely.coercion.to_matcher(value).describe())
            for key, value in self._call_kwargs.items()
        ]))


class ExactCallMatcher(precisely.base.Matcher):

  def __init__(self, calls: tuple[MockCallMatcher]):
    self._calls = calls

  def match(self, actual) -> precisely.results.Result:
    if not isinstance(actual, um.Mock):
      return precisely.results.unmatched('was not a mock')
    if len(self._calls) != len(actual.call_args_list):
      return precisely.results.unmatched(
          f'expected {len(self._calls)} calls, but got '
          f'{len(actual.call_args_list)}')
    zipped_calls = zip(self._calls, actual.call_args_list)
    for i, (call, actual_call) in enumerate(zipped_calls):
      result = precisely.coercion.to_matcher(call).match(actual_call)
      if not result.is_match:
        return precisely.results.unmatched('call {} {}'.format(
            i, result.explanation))
    return precisely.results.matched()

  def describe(self):
    return 'a mock that was called with:{}'.format(
        precisely.results.indented_list(
            call.describe() for call in self._calls))


def mock_call(*args, **kwargs) -> MockCallMatcher:
  return MockCallMatcher(args, kwargs)


def called_exactly_with(*calls: MockCallMatcher) -> ExactCallMatcher:
  return ExactCallMatcher(calls)
