"""Defines PkgConfigService and PkgConfigResult (data class)"""

import asyncio
import os
import shlex
from pathlib import Path

from bundle.core import logger, tracer
from bundle.core.process import Process

from ..resolved import PkgConfigResolved, PkgConfigResult
from ..specs import PkgConfigSpec

log = logger.get_logger(__name__)


def get_env_with_pkg_config_path(extra_dirs: list[Path] | None = None) -> dict[str, str]:
    """
    Computes PKG_CONFIG_PATH and returns a modified copy of os.environ.

    Parameters:
    - extra_dirs: Optional list of Path objects to prepend.

    Returns:
    - A modified copy of os.environ with PKG_CONFIG_PATH set.
    """
    env = os.environ.copy()
    if not extra_dirs:
        return env

    path_sep = os.pathsep  # Automatically uses ';' on Windows, ':' elsewhere
    new_paths = [str(p.resolve()) for p in extra_dirs]
    existing_paths = env.get("PKG_CONFIG_PATH", "").split(path_sep)
    existing_paths = [p for p in existing_paths if p]
    # Maintain order: extra_dirs paths first, then existing paths without duplicates
    final_paths = new_paths + [p for p in existing_paths if p not in new_paths]
    env["PKG_CONFIG_PATH"] = path_sep.join(final_paths)
    log.debug(f"Computed PKG_CONFIG_PATH for subprocess: {env['PKG_CONFIG_PATH']}")
    return env


def _parse_cflags_output(cflags_str: str) -> tuple[list[str], list[str]]:
    """Parses --cflags output into include dirs and other compile flags."""
    flags = shlex.split(cflags_str)
    include_dirs = [f[2:] for f in flags if f.startswith("-I")]
    other_flags = [f for f in flags if not f.startswith("-I")]
    log.debug(f"Parsed cflags: include_dirs={include_dirs}, other_flags={other_flags}")
    return include_dirs, other_flags


def _parse_libs_output(libs_str: str) -> tuple[list[str], list[str], list[str]]:
    """Parses --libs output into library dirs, library names, and other link flags."""
    flags = shlex.split(libs_str)
    library_dirs = [f[2:] for f in flags if f.startswith("-L")]
    libraries = [f[2:] for f in flags if f.startswith("-l")]
    other_flags = [f for f in flags if not (f.startswith("-L") or f.startswith("-l"))]
    log.debug(f"Parsed libs: library_dirs={library_dirs}, libraries={libraries}, other_flags={other_flags}")
    return library_dirs, libraries, other_flags


class PkgConfigService:
    def __init__(self, executable: str = "pkg-config"):
        self.executable = executable

    @tracer.Async.decorator.call_raise
    async def query(
        self,
        package_name: str,
        option: str,
        extra_dirs: list[str] | None = None,
    ) -> list[str]:
        """
        Runs pkg-config for a single package with the given option.
        Returns the output as a list of strings.
        """
        if not package_name:
            log.warning(f"Empty package_name provided to pkg-config query for option {option}.")
            return []

        cmd_parts = [self.executable, option, package_name]
        cmd_str = " ".join(shlex.quote(part) for part in cmd_parts)

        proc = Process(name=f"PkgConfigService.query{option}")
        path_extra_dirs = [Path(d) for d in extra_dirs] if extra_dirs else None
        env = get_env_with_pkg_config_path(path_extra_dirs)
        result = await proc(cmd_str, env=env)

        if result.returncode != 0:
            log.warning(
                f"pkg-config query for '{cmd_str}' failed or package not found: {result.stderr.strip()}. Returning empty list."
            )
            return []

        output = result.stdout.strip()
        return shlex.split(output)

    @tracer.Async.decorator.call_raise
    async def resolve_pkgconfig(self, pkg_name: str, extra_dirs: list[str] | None = None) -> PkgConfigResult:
        log.debug(f"Resolving pkg-config for package: {pkg_name}")

        cflags_list, libs_list = await asyncio.gather(
            self.query(pkg_name, "--cflags", extra_dirs),
            self.query(pkg_name, "--libs", extra_dirs),
        )

        cflags_output = " ".join(shlex.quote(s) for s in cflags_list)
        libs_output = " ".join(shlex.quote(s) for s in libs_list)
        include_dirs, compile_flags = _parse_cflags_output(cflags_output)
        library_dirs, libraries, link_flags = _parse_libs_output(libs_output)

        return PkgConfigResult(
            name=pkg_name,
            include_dirs=include_dirs,
            compile_flags=compile_flags,
            library_dirs=library_dirs,
            libraries=libraries,
            link_flags=link_flags,
        )

    @tracer.Async.decorator.call_raise
    async def resolve(self, spec: PkgConfigSpec) -> PkgConfigResolved:
        """
        Resolves PkgConfigSpec to PkgConfigResolved by calling pkg-config for each package.
        """
        if len(spec.packages) == 0:
            log.debug("No packages in PkgConfigSpec, returning empty PkgConfigResolved.")
            return PkgConfigResolved(spec=spec, resolved=[])

        tasks = [self.resolve_pkgconfig(pkg_name, spec.extra_dirs) for pkg_name in spec.packages]
        resolved_results = await asyncio.gather(*tasks)

        return PkgConfigResolved(spec=spec, resolved=list(resolved_results))
