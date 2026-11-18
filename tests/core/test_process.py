# Copyright 2026 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import json
import os
import sys
from pathlib import Path
from typing import Type

import pytest

from bundle.core import Process, ProcessError, ProcessStream
from bundle.core import process as process_module

SUCCESS_COMMANDS = [
    "echo validcommand",
]
FAILING_COMMANDS = [
    "invalidcommand",  # Command does not exist
]

# List of process classes to test
PROCESS_CLASSES = [Process, ProcessStream]
PROCESS_CLASS_TYPE = type[Process] | type[ProcessStream]


# Mark all tests in this module as asynchronous
pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
@pytest.mark.parametrize("command", SUCCESS_COMMANDS)
@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)  # 5ms + ~3ms
async def test_process_success(process_class: PROCESS_CLASS_TYPE, command, request):
    process = process_class(name="Success")
    process_return = await process(command)
    process_return.__test_name = request.node.name.strip()
    return process_return


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
@pytest.mark.parametrize("command", FAILING_COMMANDS)
@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)  # 5ms + ~3ms
async def test_process_failure(process_class, command, request):
    process = process_class(name="ExpectedFail")
    with pytest.raises(ProcessError) as exc_info:
        await process(command)
    process_error_result = exc_info.value
    process_error_result.result.__test_name = request.node.name.strip()
    return process_error_result.result


async def test_argv_preserves_literal_arguments_cwd_and_environment(tmp_path):
    directory = tmp_path / "working directory with spaces"
    directory.mkdir()
    arguments = ["two words", 'quote"value', "$(echo not-a-shell)", "semi;colon", "*", ""]
    program = (
        "import json, os, sys; "
        "print(json.dumps([sys.argv[1:], os.getcwd(), os.environ['EXEC_FIXTURE']])); "
        "print('child stderr', file=sys.stderr)"
    )
    result = await Process(name="Literal arguments")(
        [sys.executable, "-c", program, *arguments],
        cwd=directory,
        env={**os.environ, "EXEC_FIXTURE": "literal environment"},
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == [arguments, str(directory), "literal environment"]
    assert result.stderr == f"child stderr{os.linesep}"
    assert isinstance(result.command, str)
    assert "semi;colon" in result.command


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
async def test_argv_failure_preserves_exit_status_and_diagnostics(process_class):
    with pytest.raises(ProcessError) as caught:
        await process_class()([sys.executable, "-c", "import sys; print('diagnostic', file=sys.stderr); sys.exit(17)"])
    assert caught.value.result.returncode == 17
    assert caught.value.result.stderr == f"diagnostic{os.linesep}"
    assert "diagnostic" in str(caught.value)


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
async def test_missing_argv_executable_propagates_native_launch_error(process_class):
    with pytest.raises(FileNotFoundError):
        await process_class()(["bundle-executable-that-does-not-exist"])


async def test_stream_preserves_argv_and_existing_callbacks(tmp_path):
    class RecordingProcess(ProcessStream):
        async def callback_stdout(self, line):
            stdout.append(line)

        async def callback_stderr(self, line):
            stderr.append(line)

    stdout, stderr = [], []
    script = tmp_path / "script with spaces.py"
    script.write_text("import sys\nprint(sys.argv[1])\nprint('stream error', file=sys.stderr)\n")
    result = await RecordingProcess()([sys.executable, script, "literal;*value"])
    assert stdout == [f"literal;*value{os.linesep}"]
    assert stderr == [f"stream error{os.linesep}"]
    assert result.stdout == "".join(stdout)
    assert result.stderr == "".join(stderr)


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
async def test_process_preserves_child_line_endings(process_class, newline):
    stdout = f"child stdout{newline}"
    stderr = f"child stderr{newline}"
    program = f"import sys; sys.stdout.buffer.write({stdout.encode()!r}); sys.stderr.buffer.write({stderr.encode()!r})"
    result = await process_class()([sys.executable, "-c", program])
    assert result.stdout == stdout
    assert result.stderr == stderr


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
@pytest.mark.parametrize("argv", [[], ["echo", 42], ["echo", "nul\x00argument"]])
async def test_invalid_argv_is_rejected_before_spawning(process_class, argv):
    with pytest.raises((TypeError, ValueError)):
        await process_class()(argv)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("echo 'two words' | cat", ("echo 'two words' | cat",)),
        ("", ("",)),
        (["echo", Path("file with spaces"), ""], ("echo", "file with spaces", "")),
        (("echo", "literal;$(value)"), ("echo", "literal;$(value)")),
    ],
)
async def test_parse_args_preserves_shell_strings_and_literal_arguments(command, expected):
    assert process_module.parse_args(command) == expected


@pytest.mark.parametrize(("command", "error"), [([], ValueError), ([42], TypeError), ([b"binary"], TypeError)])
async def test_parse_args_rejects_empty_or_nontext_argument_sequences(command, error):
    with pytest.raises(error):
        process_module.parse_args(command)
