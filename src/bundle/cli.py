import rich_click as click
from bundle import BUNDLE_LOGGER
from bundle.core import logger, tracer

click.rich_click.SHOW_ARGUMENTS = True

log = logger.get_logger(__name__)

banner = """
╔═════════════════════════════════╗
║       T H E   B U N D L E       ║
╚═════════════════════════════════╝
"""
click.echo(click.style(banner, fg="green"))

LOG_LEVEL_MAP = {
    "debug": logger.Level.DEBUG,
    "info": logger.Level.INFO,
    "warning": logger.Level.WARNING,
    "error": logger.Level.ERROR,
    "critical": logger.Level.CRITICAL,
}


@click.group(name="bundle")
@click.option(
    "-l",
    "--log-level",
    default="info",
    type=click.Choice(LOG_LEVEL_MAP.keys(), case_sensitive=False),
    help="Set the logging level.",
)
@click.pass_context
def main(ctx: click.Context, log_level: str):
    """Main CLI entry point for The Bundle."""
    level = LOG_LEVEL_MAP[log_level.lower()]
    BUNDLE_LOGGER.setLevel(level)
    logger.get_logger().setLevel(level)
    log.setLevel(level)


@main.command()
@tracer.Sync.decorator.call_raise
async def version():
    """The Bundle Package version."""
    try:
        from bundle._version import version
    except ImportError:
        version = "unknown"
    log.info(f"Version: {version}")


def add_cli_submodule(submodule_name: str) -> None:
    """Dynamically import & register subcommands (still traced)."""
    try:
        module = __import__(f"bundle.{submodule_name}.cli", fromlist=[submodule_name])
        cmd = getattr(module, submodule_name, None)
        if cmd:
            main.add_command(cmd)
        else:
            log.warning(f"'{submodule_name}' not found in module {module}.")
    except ImportError as e:
        log.warning(f"Couldn’t import bundle.{submodule_name}.cli → {e}")


for sub in [
    "testing",
    "scraper",
    "website",
    "youtube",
    "pybind",
]:
    add_cli_submodule(sub)
