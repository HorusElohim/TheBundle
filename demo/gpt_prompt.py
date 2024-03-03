import click
import bundle
import os

LOGGER = bundle.core.logger.setup_root_logger(name=__name__, level=10)


@click.command()
@click.argument("path", type=click.Path(exists=True))
def main(path):
    """Simple script that produce the GPT prompt content of a given path."""
    output = ""
    target_path = bundle.Path(path)
    if target_path.is_file():
        output += str(path) + ":\n"
        output += target_path.read_text() + "\n"
    else:
        for root, _, files in os.walk(path):
            for file in files:
                file_path: bundle.Path = bundle.Path(root) / file
                is_pycache = "__pycache__" in str(file_path)
                if not is_pycache:
                    LOGGER.info(f"File found {file_path}")
                    output += str(file_path) + ":\n"
                    try:
                        output += file_path.read_text() + "\n"
                    except:
                        pass
    LOGGER.info(f"GPT prompt:\n {output}")


if __name__ == "__main__":
    main()
