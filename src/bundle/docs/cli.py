# Copyright 2024 HorusElohim

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
bundle docs CLI

  bundle docs build [--source .] [--output docs/_build/html] [--package src/bundle] [--theme furo]
  bundle docs serve [--output docs/_build/html] [--port 8000]
  bundle docs init  [--source .]
"""

from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def docs():
    """Build and serve Sphinx documentation."""
    pass


@docs.command()
@click.option(
    "--source",
    "-s",
    type=click.Path(exists=True),
    default=".",
    help="Project root directory (where pyproject.toml lives).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="docs/_build/html",
    help="Output directory for built HTML.",
)
@click.option(
    "--package",
    "-p",
    type=str,
    default=None,
    help="Package path to document (auto-detected from pyproject.toml).",
)
@click.option(
    "--theme",
    type=click.Choice(["furo", "sphinx_rtd_theme", "pydata_sphinx_theme"]),
    default="furo",
    help="Sphinx HTML theme.",
)
@tracer.Sync.decorator.call_raise
async def build(source: str, output: str, package: str | None, theme: str):
    """Build HTML documentation from docstrings and READMEs."""
    from bundle.docs.builder import DocsBuilder
    from bundle.docs.config import DocsConfig
    from bundle.docs.discovery import discover_project

    source_path = Path(source).resolve()
    project_info = discover_project(source_path)

    package_dirs = [package] if package else project_info["package_dirs"]
    autoapi_dirs = [str(source_path / d) for d in package_dirs]

    config = DocsConfig(
        project_name=project_info["name"],
        project_version=project_info.get("version", ""),
        author=project_info.get("author", ""),
        source_dir=source_path,
        output_dir=Path(output).resolve(),
        package_dirs=package_dirs,
        autoapi_dirs=autoapi_dirs,
        theme=theme,
    )

    builder = DocsBuilder(config)
    result = await builder.build()
    log.info("Documentation built at: %s", result)


@docs.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(exists=True),
    default="docs/_build/html",
    help="Directory of built HTML docs.",
)
@click.option("--port", type=int, default=8000, help="Port for the local server.")
@tracer.Sync.decorator.call_raise
async def serve(output: str, port: int):
    """Serve built documentation locally for preview."""
    from bundle.core import ProcessStream

    log.info("Serving docs at http://localhost:%d from %s", port, output)
    proc = ProcessStream(name="docs-serve")
    await proc(f"python -m http.server {port} --directory {output}")


@docs.command()
@click.option(
    "--source",
    "-s",
    type=click.Path(exists=True),
    default=".",
    help="Project root directory.",
)
@tracer.Sync.decorator.call_raise
async def init(source: str):
    """Initialize persistent Sphinx configuration files in a project."""
    from bundle.docs.config import DocsConfig
    from bundle.docs.discovery import discover_project

    source_path = Path(source).resolve()
    project_info = discover_project(source_path)

    package_dirs = project_info["package_dirs"]
    autoapi_dirs = [str(source_path / d) for d in package_dirs]

    config = DocsConfig(
        project_name=project_info["name"],
        project_version=project_info.get("version", ""),
        author=project_info.get("author", ""),
        source_dir=source_path,
        output_dir=source_path / "docs" / "_build" / "html",
        package_dirs=package_dirs,
        autoapi_dirs=autoapi_dirs,
    )

    docs_dir = source_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    conf_path = docs_dir / "conf.py"
    conf_path.write_text(config.generate_conf_py())
    log.info("Written %s", conf_path)

    index_path = docs_dir / "index.md"
    if not index_path.exists():
        index_path.write_text(
            f"# {config.project_name}\n\nWelcome to the {config.project_name} documentation.\n"
        )
        log.info("Written %s", index_path)

    log.info("Sphinx configuration initialized in %s", docs_dir)
