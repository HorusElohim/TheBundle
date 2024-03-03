from pathlib import Path


def ensure_path(path: str | Path) -> Path:
    if path is not None:
        path = Path(path)
        if not path.exists():
            if path.suffix:  # If the path has a file extension, ensure parent directory
                path.parent.mkdir(parents=True, exist_ok=True)
            else:  # Path is a directory
                path.mkdir(parents=True, exist_ok=True)
    return path


def retrieves_tests_paths(
    category: str,
    ref_dir: str | Path,
    tmp_dir: str | Path,
    class_instance: object,
    suffix: str,
    extension: str = "json",
) -> tuple[Path, Path, Path, Path]:

    category = category.split("/")
    filename = f"{type(class_instance).__name__}_{suffix}.{extension}"
    ref_path = ensure_path(ref_dir / "ref" / Path(*category) / filename)
    tmp_path = ensure_path(tmp_dir / Path(*category) / filename)
    failed_path = ensure_path(ref_dir / "failed" / Path(*category) / filename)
    failed_error_log_path = ensure_path(ref_dir / "failed" / Path(*category) / "logs" / filename)

    return (
        ref_path,
        tmp_path,
        failed_path,
        failed_error_log_path,
    )
