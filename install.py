"""Install selected skills without replacing existing skill directories."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
DEPENDENCIES = {"nature-downloader": ["web-access"], "researchwiki-steward": ["word-to-markdown-academic"]}


def planned_skills(selected: list[str] | None) -> list[str]:
    available = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
    requested = list(selected) if selected else sorted(available)
    missing = set(requested) - available
    if missing:
        raise ValueError("Unknown skills: " + ", ".join(sorted(missing)))
    result = []
    for name in requested:
        if name not in result:
            result.append(name)
        for dependency in DEPENDENCIES.get(name, []):
            if dependency not in result:
                result.append(dependency)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude"], default="codex")
    parser.add_argument("--destination", type=Path, help="Explicit skills directory")
    parser.add_argument("--only", nargs="+", metavar="SKILL")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    destination = (args.destination or Path.home() / (".agents" if args.agent == "codex" else ".claude") / "skills").expanduser().resolve()
    try:
        names = planned_skills(args.only)
        # Check the complete plan before making any directory or copying any file.
        collisions = [str(destination / name) for name in names if (destination / name).exists()]
        if collisions:
            raise FileExistsError("Existing skills were preserved; nothing installed:\n" + "\n".join(collisions))
        for name in names:
            print(f"{name} -> {destination / name}")
        if args.dry_run:
            print("Dry run: no files changed.")
            return 0
        destination.mkdir(parents=True, exist_ok=True)
        for name in names:
            shutil.copytree(ROOT / "skills" / name, destination / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "runtime", "node_modules", "config.env"))
        print(f"Installed {len(names)} skills. Reload your agent's skills list.")
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
