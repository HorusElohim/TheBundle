import click
import bundle


LOGGER = bundle.setup_logging(name=__name__, level=10)


def apply_black_to_file(path: bundle.Path | str):
    LOGGER.info("applying black to '%s' ...", path)
    p = bundle.Process(command=f"black {path}")
    p(shell=True, text=True)
    LOGGER.info("black applied to  '%s' ✅", path)


@click.command()
@click.argument("path", default=bundle.__path__[0])
def main(path):
    """Simple script that applies Black formatter to a given path."""
    apply_black_to_file(path)


if __name__ == "__main__":
    main()
