"""Meaningful privacy and degraded-environment checks for the system probe."""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/github-project-guide/scripts/system_info.py"
SPEC = importlib.util.spec_from_file_location("system_info", SCRIPT)
system_info = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(system_info)


class SystemInfoTests(unittest.TestCase):
    def test_default_does_not_probe_details(self):
        with patch.object(system_info.platform, "system", return_value="Linux"), \
             patch.object(system_info.platform, "release", return_value="6.8.0"), \
             patch.object(system_info.platform, "machine", return_value="aarch64"), \
             patch.object(system_info, "_read_memory") as memory, \
             patch.object(system_info.shutil, "which") as which, \
             patch.object(system_info.subprocess, "run") as run:
            result = system_info.collect_system_info()
        memory.assert_not_called()
        which.assert_not_called()
        run.assert_not_called()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(set(result["fields"]), {
            "os_name", "os_version", "os_version_kind", "cpu_architecture"
        })
        self.assertEqual(result["fields"]["os_version_kind"], "kernel")

    def test_restricted_macos_memory_preserves_other_fields(self):
        outputs = [
            subprocess.CompletedProcess([], 0, stdout="26.6.2\n"),
            subprocess.CalledProcessError(1, [], stderr="private path must not leak"),
        ]
        with patch.object(system_info.platform, "system", return_value="Darwin"), \
             patch.object(system_info.platform, "machine", return_value="arm64"), \
             patch.object(system_info.subprocess, "run", side_effect=outputs) as run, \
             patch.object(system_info.shutil, "which", return_value="/private/path/to/tool"):
            result = system_info.collect_system_info(details=True)
        self.assertEqual(result["fields"]["os_version"], "26.6.2")
        self.assertIsNone(result["fields"]["memory_bytes"])
        self.assertEqual(result["fields"]["cpu_architecture"], "arm64")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["probe_errors"][0]["field"], "memory_bytes")
        self.assertNotIn("private", str(result))
        self.assertEqual(run.call_args_list[0].args[0], ["/usr/bin/sw_vers", "-productVersion"])
        self.assertEqual(run.call_args_list[1].args[0], ["/usr/sbin/sysctl", "-n", "hw.memsize"])
        for call in run.call_args_list:
            self.assertFalse(call.kwargs["shell"])
            self.assertEqual(call.kwargs["timeout"], 3)

    def test_absent_tools_are_unknown_and_not_executed(self):
        with patch.object(system_info.platform, "system", return_value="Linux"), \
             patch.object(system_info.platform, "release", return_value="6.8.0"), \
             patch.object(system_info.platform, "machine", return_value="x86_64"), \
             patch.object(system_info.os, "sysconf", side_effect=[1024, 4096]), \
             patch.object(system_info.shutil, "which", return_value=None), \
             patch.object(system_info.subprocess, "run") as run:
            result = system_info.collect_system_info(details=True)
        run.assert_not_called()
        self.assertEqual(result["fields"]["memory_bytes"], 4194304)
        self.assertEqual(result["fields"]["tool_availability"], {
            "python": "unknown", "node": "unknown", "git": "unknown"
        })
        self.assertEqual(len(result["probe_errors"]), 3)
        self.assertTrue(all(error["reason"] == "executable not found on PATH" for error in result["probe_errors"]))

    def test_version_timeout_does_not_hide_architecture(self):
        with patch.object(system_info.platform, "system", return_value="Darwin"), \
             patch.object(system_info.platform, "machine", return_value="arm64"), \
             patch.object(system_info.subprocess, "run", side_effect=subprocess.TimeoutExpired([], 3)):
            result = system_info.collect_system_info()
        self.assertIsNone(result["fields"]["os_version"])
        self.assertEqual(result["fields"]["cpu_architecture"], "arm64")
        self.assertEqual(result["probe_errors"], [{"field": "os_version", "reason": "system probe timed out"}])

    def test_invalid_linux_memory_is_not_reported_as_negative(self):
        with patch.object(system_info.platform, "system", return_value="Linux"), \
             patch.object(system_info.os, "sysconf", side_effect=[-1, 4096]), \
             patch.object(system_info.shutil, "which", return_value="/bin/example"):
            result = system_info.collect_system_info(details=True)
        self.assertIsNone(result["fields"]["memory_bytes"])
        self.assertEqual(result["probe_errors"][0]["field"], "memory_bytes")


if __name__ == "__main__":
    unittest.main()
