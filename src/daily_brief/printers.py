"""Find a printer to send the edition to, via CUPS (macOS and Linux).

A queue that exists and is enabled is used; that doesn't prove the printer is
switched on, so the PDF is always kept as well. No CUPS (e.g. Windows) or no
usable queue means no printer: the caller then only saves the PDF.
"""

import os
import shutil
import subprocess

# Queues that don't put ink on paper.
VIRTUAL = ("fax", "pdf", "xps", "onenote")


def _lpstat(*args: str) -> str:
    env = {**os.environ, "LC_ALL": "C"}  # lpstat's output is localized otherwise
    r = subprocess.run(["lpstat", *args], capture_output=True, text=True, env=env)
    return r.stdout


def available() -> list[dict]:
    """Every print queue with whether it can take a job, the system default first."""
    if not shutil.which("lpstat"):
        return []
    default = _lpstat("-d").partition("destination:")[2].strip()
    queues = []
    for line in _lpstat("-p").splitlines():
        if not line.startswith("printer "):
            continue
        name = line.split()[1]
        queues.append({
            "name": name,
            "default": name == default,
            "usable": "disabled" not in line and not any(v in name.lower() for v in VIRTUAL),
        })
    return sorted(queues, key=lambda q: not q["default"])


def find(preferred: str = "") -> str | None:
    """The preferred queue if it's usable, else the default, else the first usable one."""
    usable = [q["name"] for q in available() if q["usable"]]
    if preferred:
        return preferred if preferred in usable else None
    return usable[0] if usable else None
