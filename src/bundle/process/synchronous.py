# Copyright 2023 HorusElohim

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


import subprocess
import signal
import os
from typing import Callable
import shlex

from ._abc import ProcessABC, StreamingProcessABC
from .. import logger
from . import data
from . import LOGGER


@data.dataclass
class Process(ProcessABC):
    def exec(self, **kwds) -> bool:
        LOGGER.debug(f"running {self.command}")
        try:
            self._process = subprocess.run(shlex.split(self.command), **kwds)
            self.returncode = self._process.returncode
            self.stdout = self._process.stdout
            self.stderr = self._process.stderr
        except Exception as e:
            LOGGER.error(f"Unexpected error: {e}")
            self.returncode = e.returncode
            self.stdout = e.stdout
            self.stderr = e.stderr
            report += f"\nException: {e} \nstderr: {e.stderr}"
        finally:
            self._reset_process()
            if self.returncode == 0:
                LOGGER.debug(f"ran {logger.Emoji.success}")
                return True
            else:
                LOGGER.error(f"ran {logger.Emoji.failed}")
                LOGGER.error(f"{self}")
                return False

    def terminate(self):
        if self._process is not None:
            os.kill(self.process.pid, signal.SIGINT)


@data.dataclass
class StreamingProcess(StreamingProcessABC, Process):
    def exec(self, **kwds) -> bool:
        report = f"Process `{self.command}`"
        try:
            self._process = subprocess.Popen(
                self.command,
                **kwds,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Poll process for new output until finished
            while self._process.poll() is None:
                if self._process.stdout:
                    for line in iter(self._process.stdout.readline, ""):
                        if line and self.stdout_callback:
                            self.stdout_callback(line)
                        self.stdout += line

                if self._process.stderr:
                    for line in iter(self._process.stderr.readline, ""):
                        if line and self.stderr_callback:
                            self.stderr_callback(line)
                        self.stderr += line

            # Flush remaining streams
            if self._process.stdout:
                for line in self._process.stdout.readlines():
                    if self.stdout_callback:
                        self.stdout_callback(line)
                    self.stdout += line

            if self._process.stderr:
                for line in self._process.stderr.readlines():
                    if self.stderr_callback:
                        self.stderr_callback(line)
                    self.stderr += line

            self.returncode = self._process.returncode

        except subprocess.CalledProcessError as e:
            self.returncode = e.returncode
            self.stderr = e.stderr
            report += f"\nException: {e} \nstderr: {e.stderr}"
        finally:
            self._reset_process()

            if self.returncode == 0:
                LOGGER.debug(f"{report}: {logger.Emoji.success}")
                return True
            else:
                LOGGER.error(f"{report}: {logger.Emoji.failed}")
                if self.stderr:
                    LOGGER.error(f"stderr: {self.stderr}")
                return False
