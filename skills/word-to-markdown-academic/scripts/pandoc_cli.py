"""Invoke an installed Pandoc binary, including pypandoc_binary installations."""
from pathlib import Path
import shutil
import subprocess
import sys


def find_pandoc() -> str:
    executable = shutil.which("pandoc")
    if executable:
        return executable
    try:
        import pypandoc
        return pypandoc.get_pandoc_path()
    except (ImportError, OSError) as exc:
        raise RuntimeError("Install Pandoc in PATH or run: python -m pip install pypandoc_binary") from exc


if __name__ == "__main__":
    try:
        raise SystemExit(subprocess.call([find_pandoc(), *sys.argv[1:]]))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
