"""Read-only checks: no downloads, browser launches, or credential inspection."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    print("Python:", sys.version.split()[0], "(3.11+ recommended)")
    print("Node.js:", shutil.which("node") or "MISSING: browser downloads need Node.js 22+")
    if shutil.which("node"):
        subprocess.run([shutil.which("node"), "--version"], check=True)
    pandoc = shutil.which("pandoc")
    if not pandoc and importlib.util.find_spec("pypandoc"):
        import pypandoc
        try:
            pandoc = pypandoc.get_pandoc_path()
        except OSError:
            pass
    print("Pandoc:", pandoc or "MISSING: install Pandoc or pypandoc_binary")
    for module, purpose in [("PIL", "image cleanup"), ("markitdown", "optional text conversion"),
                            ("pypdf", "PDF checks"), ("pdfplumber", "PDF extraction"),
                            ("yaml", "downloader settings"), ("jsonschema", "settings validation"),
                            ("selenium", "Firefox live session"), ("websocket", "publisher DevTools")]:
        print(f"{module}: {'available' if importlib.util.find_spec(module) else 'not installed'} ({purpose})")
    print("Browser login and institutional entitlement must be checked in the user's browser.")
    print("No browser settings or user credentials were read or changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
