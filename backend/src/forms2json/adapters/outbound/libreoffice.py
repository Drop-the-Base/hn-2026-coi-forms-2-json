"""LibreOffice headless as an unmodified program, never linked (ADR-0013)."""

import os
import signal
import subprocess
import tempfile
from pathlib import Path


class SofficeFailed(Exception):
    """soffice is missing, failed, timed out or wrote no output."""


def soffice_convert(content: bytes, suffix: str, target: str, timeout_seconds: float) -> bytes:
    """Converts a document to `target` ("docx", "pdf"); `suffix` hints the input type."""
    # Files and the soffice profile live only in a temp dir on tmpfs, removed always (NFR-06).
    with tempfile.TemporaryDirectory(prefix="forms2json-soffice-") as work:
        source = Path(work, f"input{suffix}")
        source.write_bytes(content)
        command = [
            "soffice",
            f"-env:UserInstallation={Path(work, 'profile').as_uri()}",
            "--headless",
            "--norestore",
            "--convert-to",
            target,
            "--outdir",
            str(Path(work, "out")),
            str(source),
        ]
        try:
            # Own session: on timeout kill the whole group, soffice.bin too, not only the wrapper.
            with subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "HOME": work},
                start_new_session=True,
            ) as process:
                try:
                    returncode = process.wait(timeout_seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    raise SofficeFailed("timeout") from None
            if returncode != 0:
                raise SofficeFailed(f"exit code {returncode}")
            return Path(work, "out", f"input.{target}").read_bytes()
        except OSError as error:  # soffice missing or no output file
            raise SofficeFailed(str(error)) from error
