import click
import bundle
import shutil
import os

LOGGER = bundle.logging.getLogger(__name__)


@bundle.data.dataclass
class CleanPyCache(bundle.tasks.Task):
    def exec(self) -> None:
        if not self.path.is_dir():
            raise ValueError(f"The path {self.path} is not a valid directory.")

        for root, dirs, files in os.walk(self.path):
            if "__pycache__" in dirs:
                pycache_path = bundle.Path(root) / "__pycache__"
                LOGGER.info(f"Removing {pycache_path}")
                shutil.rmtree(pycache_path)


@click.command()
@click.option("--path", default=bundle.__path__[0], help="Path to format with Black.")
def main(path):
    """Simple script that clean all the __pycache__ to a given path."""
    CleanPyCache(path=bundle.Path(path))()


if __name__ == "__main__":
    main()
