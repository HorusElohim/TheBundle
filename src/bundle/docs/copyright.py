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

from __future__ import annotations

import re
from pathlib import Path

from bundle.core import logger

log = logger.get_logger(__name__)

# Apache 2.0 license header template.
# Placeholders: {year}, {owner}, {comment}, {blank_comment}
_APACHE2_TEMPLATE = """\
{comment} Copyright {year} {owner}
{blank_comment}
{comment} Licensed to the Apache Software Foundation (ASF) under one
{comment} or more contributor license agreements.  See the NOTICE file
{comment} distributed with this work for additional information
{comment} regarding copyright ownership.  The ASF licenses this file
{comment} to you under the Apache License, Version 2.0 (the
{comment} "License"); you may not use this file except in compliance
{comment} with the License.  You may obtain a copy of the License at
{blank_comment}
{comment}   http://www.apache.org/licenses/LICENSE-2.0
{blank_comment}
{comment} Unless required by applicable law or agreed to in writing,
{comment} software distributed under the License is distributed on an
{comment} "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
{comment} KIND, either express or implied.  See the License for the
{comment} specific language governing permissions and limitations
{comment} under the License.
"""

# Map file extensions to (line_comment, blank_line_comment) pairs
_COMMENT_STYLES: dict[str, tuple[str, str]] = {
    ".py": ("#", "#"),
    ".cpp": ("//", "//"),
    ".c": ("//", "//"),
    ".h": ("//", "//"),
    ".hpp": ("//", "//"),
    ".js": ("//", "//"),
    ".ts": ("//", "//"),
    ".rs": ("//", "//"),
    ".go": ("//", "//"),
}

# Regex that matches "Copyright <year> <owner>" with any comment prefix
_COPYRIGHT_RE = re.compile(r"Copyright\s+(\d{4})\s+(.+)")


def render_header(year: int, owner: str, suffix: str) -> str:
    """Render a copyright + license header for the given file type.

    Args:
        year: Copyright year.
        owner: Copyright holder name.
        suffix: File extension (e.g. ".py", ".cpp").

    Returns:
        The formatted header string, or empty string for unsupported types.
    """
    style = _COMMENT_STYLES.get(suffix)
    if style is None:
        return ""
    comment, blank_comment = style
    return _APACHE2_TEMPLATE.format(
        year=year,
        owner=owner,
        comment=comment,
        blank_comment=blank_comment,
    )


def scan_copyright(
    root: Path,
    extensions: tuple[str, ...] = (".py", ".cpp", ".c", ".h", ".hpp"),
    exclude_patterns: tuple[str, ...] = (
        "__pycache__",
        "_version.py",
        "vendor",
        "node_modules",
    ),
) -> tuple[list[Path], list[Path]]:
    """Scan a directory tree and classify files by copyright header presence.

    Args:
        root: Directory to scan recursively.
        extensions: File extensions to check.
        exclude_patterns: Path substrings to skip.

    Returns:
        Tuple of (files_with_copyright, files_without_copyright).
    """
    with_header: list[Path] = []
    without_header: list[Path] = []

    for ext in extensions:
        for path in sorted(root.rglob(f"*{ext}")):
            if any(ex in str(path) for ex in exclude_patterns):
                continue
            try:
                head = path.read_text(errors="replace")[:500]
            except OSError:
                continue
            if _COPYRIGHT_RE.search(head):
                with_header.append(path)
            else:
                without_header.append(path)

    return with_header, without_header


def update_copyright_year(path: Path, new_year: int) -> bool:
    """Update the copyright year in a file's header.

    Args:
        path: File to update.
        new_year: Year to set.

    Returns:
        True if the file was modified, False if no copyright line was found.
    """
    content = path.read_text()
    new_content, count = re.subn(
        r"(Copyright\s+)\d{4}(\s+)",
        rf"\g<1>{new_year}\2",
        content,
        count=1,
    )
    if count == 0:
        return False
    if new_content != content:
        path.write_text(new_content)
        log.info("Updated copyright year to %d in %s", new_year, path)
        return True
    return False


def add_copyright_header(path: Path, year: int, owner: str) -> bool:
    """Prepend a copyright + license header to a file that lacks one.

    Args:
        path: File to prepend the header to.
        year: Copyright year.
        owner: Copyright holder name.

    Returns:
        True if the header was added, False if unsupported extension or already present.
    """
    content = path.read_text()
    if _COPYRIGHT_RE.search(content[:500]):
        return False

    header = render_header(year, owner, path.suffix)
    if not header:
        log.warning("No comment style for %s, skipping %s", path.suffix, path)
        return False

    path.write_text(header + "\n" + content)
    log.info("Added copyright header to %s", path)
    return True
