"""Prepare Windows-formatted inputs before handing control to Bash."""

import os
from pathlib import Path
import subprocess
import sys


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if action in {"prepare", "render-config", "generate-cert", "setup-host",
                  "add-ftpsrv", "verify"}:
        # A new .gitattributes rule does not rewrite an existing checkout.
        # Normalize only preparation inputs, preserving permissions and bytes
        # other than CRLF line endings. Generated files still live in /work.
        paths = sorted(Path("scripts").glob("*.sh")) + [Path(".env")]
        for path in paths:
            if not path.is_file():
                continue
            try:
                original = path.read_bytes()
                normalized = original.replace(b"\r\n", b"\n")
                if normalized != original:
                    path.write_bytes(normalized)
                    print(f"Normalized CRLF line endings: {path}", flush=True)
            except OSError as error:
                print(f"error: cannot normalize {path}: {error}", file=sys.stderr)
                return 1

    runner = Path(__file__).with_suffix(".sh")
    # Reading as text also handles an existing CRLF checkout of this runner.
    source = runner.read_text(encoding="utf-8")
    bash = os.environ.get("BASH_BIN", "bash")
    command = [bash, "-c", source, str(runner), *sys.argv[1:]]
    if os.name == "nt":
        return subprocess.call(command)
    os.execvp(bash, command)


if __name__ == "__main__":
    sys.exit(main())
