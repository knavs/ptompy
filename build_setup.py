"""
Build PtoMpy setup.exe from the Nuitka standalone folder.

Prerequisites:
  1. Run Nuitka build first:  python build_nuitka.py
  2. Install Inno Setup 6:    https://jrsoftware.org/isdl.php

Then run:  python build_setup.py

Output: build/PtoMpy_Setup_0.2.exe (or similar, depending on version in setup.iss)
"""
import os
import subprocess
import sys


def _find_iscc():
    """Return path to Inno Setup compiler (ISCC.exe), or None."""
    prog = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidates = [
        os.path.join(prog, "Inno Setup 6", "ISCC.exe"),
        os.path.join(prog, "Inno Setup 5", "ISCC.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    # Try PATH
    try:
        subprocess.run(["iscc", "/?"], capture_output=True, timeout=5)
        return "iscc"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    dist = os.path.join(root, "build", "main.dist")
    iss = os.path.join(root, "setup.iss")

    if not os.path.isdir(dist):
        print("Nuitka build folder not found:", dist)
        print("Run first:  python build_nuitka.py")
        sys.exit(1)
    if not os.path.isfile(iss):
        print("setup.iss not found:", iss)
        sys.exit(1)

    iscc = _find_iscc()
    if not iscc:
        print("Inno Setup compiler (ISCC.exe) not found.")
        print("Install Inno Setup 6 from: https://jrsoftware.org/isdl.php")
        print("Or run manually:  \"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe\" setup.iss")
        sys.exit(1)

    os.chdir(root)
    print("Running Inno Setup:", iscc, iss)
    subprocess.check_call([iscc, iss])


if __name__ == "__main__":
    main()
