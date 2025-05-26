from pathlib import Path
from bundle.core import tracer
from bundle.pybind.services import CMakeService


@tracer.Sync.decorator.call_raise
async def main():
    source = Path(__file__).parent
    build = source / "_build"
    install = source / "_install"
    await CMakeService.configure(source, build, install_path=install)
    await CMakeService.build(source, build, target="install")


if __name__ == "__main__":
    main()
