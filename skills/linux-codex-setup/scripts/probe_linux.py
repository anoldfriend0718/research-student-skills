#!/usr/bin/env python3
"""Read-only Linux deployment inventory, Python 3.6+ and standard library only.

No network checks, installation, service mutations or credential/config dumps.
Missing tools are observations; this is not an end-to-end readiness test.
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path


def command_result(argv):
    """Bound execution time and retain only output needed for version/status."""
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                universal_newlines=True, timeout=8)
        return {"exit_code": result.returncode,
                "output": result.stdout.strip()[:600]}
    except subprocess.TimeoutExpired:
        return {"error": "timeout_after_8_seconds"}
    except OSError as exc:
        return {"error": type(exc).__name__}


def libc_info():
    """Prefer libc's runtime value; ELF symbol scanning can underreport glibc."""
    try:
        value = os.confstr("CS_GNU_LIBC_VERSION")
        if value:
            name, version = value.split(None, 1)
            return {"name": name, "version": version, "source": "os.confstr"}
    except (ValueError, OSError, AttributeError):
        pass
    name, version = platform.libc_ver()
    return {"name": name, "version": version,
            "source": "platform.libc_ver_heuristic", "requires_verification": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", default=[],
                        help="Known user service to inspect; repeat as needed")
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("Run this probe on the target Linux host, not the client.")
    for name in args.service:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]*\.service", name):
            parser.error("Expected a plain systemd service name ending in .service")
    os_info = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key in ("ID", "VERSION_ID", "PRETTY_NAME"):
                os_info[key] = value.strip('"')
    except OSError:
        os_info["error"] = "os-release_unavailable"
    report = {"schema_version": 2, "os": os_info,
              "hostname": platform.node(),
              "architecture": platform.machine(), "kernel": platform.release(),
              "libc": libc_info(), "uid": os.getuid(),
              "python": platform.python_version(),
              "proxy_env_present": {key: bool(os.environ.get(key)) for key in
                  ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY")},
              "tools": {}, "user_services": {}}
    commands = {"codex": ["--version"], "node": ["--version"],
                "tmux": ["-V"], "podman": ["--version"],
                "systemctl": ["--version"], "getenforce": [], "bwrap": ["--version"]}
    for name, options in commands.items():
        executable = shutil.which(name)
        if name == "codex" and executable is None:
            candidate = Path.home() / ".local/bin/codex"
            if candidate.is_file() and os.access(str(candidate), os.X_OK):
                executable = str(candidate)
        if executable:
            report["tools"][name] = command_result([executable] + options)
            report["tools"][name]["path"] = executable
        else:
            report["tools"][name] = {"available": False, "scope": "current_process_PATH"}
    systemctl = shutil.which("systemctl")
    for name in args.service:
        if systemctl:
            report["user_services"][name] = command_result([
                systemctl, "--user", "show", "--no-pager",
                "--property=LoadState,ActiveState,SubState,UnitFileState,Type,RemainAfterExit",
                name])
        else:
            report["user_services"][name] = {"error": "systemctl_unavailable"}
    report["limits"] = ["No authentication, network or model request tested",
                        "No service started, restarted or enabled",
                        "No credential files or proxy addresses read",
                        "Tool paths and proxy flags describe this process, not other hosts, containers or daemons",
                        "No Dot task sandbox startup tested"]
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
