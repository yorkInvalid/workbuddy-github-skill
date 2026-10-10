#!/usr/bin/env python3
"""Read a small, privacy-conscious system summary using only the standard library."""

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
import platform
import shutil
import subprocess


SCHEMA_VERSION = 1
COMMAND_TIMEOUT = 3


def _command_output(command):
    """Run only the fixed OS utilities supplied by this module, without a shell."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        timeout=COMMAND_TIMEOUT,
        shell=False,
    )
    value = result.stdout.strip()
    if not value:
        raise ValueError("empty system utility output")
    return value


def _read_memory(system):
    if system == "Darwin":
        value = int(_command_output(["/usr/sbin/sysctl", "-n", "hw.memsize"]))
    elif system == "Linux":
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages <= 0 or page_size <= 0:
            raise ValueError("physical memory is unavailable")
        value = pages * page_size
    elif system == "Windows":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("physical memory is unavailable")
        value = status.ullTotalPhys
    else:
        raise NotImplementedError("physical memory probe is unsupported")
    if value <= 0:
        raise ValueError("physical memory is unavailable")
    return value


def _failure_reason(error):
    # Never include exception text: it can contain user-specific paths or stderr.
    if isinstance(error, subprocess.TimeoutExpired):
        return "system probe timed out"
    if isinstance(error, PermissionError):
        return "system probe permission denied"
    if isinstance(error, subprocess.CalledProcessError):
        return "system utility returned an error; access may be restricted"
    if isinstance(error, NotImplementedError):
        return "probe unsupported on this system"
    return "system probe failed (%s)" % type(error).__name__


def collect_system_info(details=False):
    """Unavailable fields are null/unknown; a failed probe never aborts the report."""
    errors = []

    def probe(field, function):
        try:
            value = function()
            if value is None or value == "":
                raise ValueError("empty probe result")
            return value
        except Exception as error:
            errors.append({"field": field, "reason": _failure_reason(error)})
            return None

    system = probe("os_name", platform.system)
    fields = {
        "os_name": "macOS" if system == "Darwin" else system,
        "os_version": None,
        "os_version_kind": None,
        "cpu_architecture": probe("cpu_architecture", platform.machine),
    }
    if system == "Darwin":
        fields["os_version"] = probe(
            "os_version", lambda: _command_output(["/usr/bin/sw_vers", "-productVersion"])
        )
        fields["os_version_kind"] = "product"
    elif system == "Windows":
        fields["os_version"] = probe("os_version", platform.version)
        fields["os_version_kind"] = "product"
    elif system:
        fields["os_version"] = probe("os_version", platform.release)
        fields["os_version_kind"] = "kernel"

    if details:
        fields["memory_bytes"] = probe("memory_bytes", lambda: _read_memory(system))
        tool_status = {}
        for label, names in (("python", ("python3", "python")), ("node", ("node",)), ("git", ("git",))):
            field = "tool_availability." + label
            found = probe(field, lambda names=names: any(shutil.which(name) for name in names))
            if found:
                tool_status[label] = "available"
            else:
                tool_status[label] = "unknown"
                if found is False:
                    errors.append({"field": field, "reason": "executable not found on PATH"})
        fields["tool_availability"] = tool_status

    return {
        "schema_version": SCHEMA_VERSION,
        "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "partial" if errors else "ok",
        "fields": fields,
        "probe_errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--details",
        action="store_true",
        help="also read physical memory and check python/node/git on PATH (never run them)",
    )
    args = parser.parse_args()
    print(json.dumps(collect_system_info(details=args.details), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
