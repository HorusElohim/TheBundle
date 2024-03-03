import click
import bundle
import shutil
import os

LOGGER = bundle.core.logger.setup_root_logger(name=__name__, level=10)


@click.command()
@click.option("--path", default=bundle.__path__[0], type=click.Path(exists=True), help="Path to format with Black.")
def main(path):
    """Simple script that clean all the __pycache__ to a given path."""
    for root, dirs, files in os.walk(path):
        if "__pycache__" in dirs:
            pycache_path = bundle.Path(root) / "__pycache__"
            LOGGER.info(f"Removing {pycache_path}")
            shutil.rmtree(pycache_path)


if __name__ == "__main__":
    main()
