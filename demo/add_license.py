import asyncio
import os
import bundle

LOGGER = bundle.logging.getLogger(__name__)

LICENSE_TEXT = """# Copyright 2023 HorusElohim

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
"""

EXCLUDED_FILE = ["_version.py"]


@bundle.data.dataclass
class FindPythonFilesTask(bundle.tasks.AsyncTask):
    async def exec(self):
        tasks = []
        for root, _, files in os.walk(self.path):
            for file in files:
                if file.endswith(".py") and file not in EXCLUDED_FILE:
                    file_path = os.path.join(root, file)
                    task = AddLicenseTask(name="AddLicenseTask", path=file_path)
                    tasks.append(task())
        await asyncio.gather(*tasks)


@bundle.data.dataclass
class AddLicenseTask(bundle.tasks.AsyncTask):
    async def exec(self):
        with open(self.path, "r+", encoding="utf-8") as f:
            content = f.read()
            if "Copyright 2023 HorusElohim" not in content:
                LOGGER.warn("missing LICENSE for %s", self.path)
                f.seek(0, 0)
                f.write(LICENSE_TEXT + "\n\n" + content)
                LOGGER.info("LICENSE added %s", self.path)


async def apply_license_to_files(path):
    find_task = FindPythonFilesTask(name="FindPythonFilesTask", path=path)
    await find_task()


if __name__ == "__main__":
    import click

    @click.command()
    @click.option("--path", default=bundle.__path__[0], help="Path to apply the license.")
    def main(path):
        """Simple script that applies a license comment to Python files in a given path."""
        asyncio.run(apply_license_to_files(path))

    main()
