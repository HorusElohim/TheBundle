import click
import bundle
import subprocess

LOGGER = bundle.logging.getLogger(__name__)


def apply_black_to_file(path: bundle.typing.Union[bundle.Path, str]):
    LOGGER.info("applying black to '%s' ...", path)
    p = bundle.process.Process(command=f"black {path}")
    p(shell=True, text=True)
    LOGGER.info("black applied to  '%s' ✅", path)


@click.command()
@click.option("--path", default=bundle.__path__[0], help="Path to format with Black.")
def main(path):
    """Simple script that applies Black formatter to a given path."""
    apply_black_to_file(path)


if __name__ == "__main__":
    main()
