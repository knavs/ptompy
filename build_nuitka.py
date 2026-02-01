"""
Build PtoMpy with Nuitka. Run: python build_nuitka.py

Options:
  --mingw64      Use MinGW64 (Nuitka downloads it locally). Requires Python 3.12
                 or lower; Python 3.13+ needs MSVC instead.
  --venv-py312   Create a Python 3.12 venv, install nuitka+Pillow, and run the
                 build with --mingw64 (no MSVC needed). Use when current Python
                 is 3.13+ and you don't have Visual Studio.

For Python 3.13+ without --mingw64: the script tries to find Visual Studio via
vswhere and run the build in that environment. Otherwise install "Build Tools
for Visual Studio" with "Desktop development with C++".


100% cursor generated
"""
import os
import subprocess
import sys


def _find_python312():
    """Return path to Python 3.12 executable, or None."""
    candidates = [["py", "-3.12"]] if sys.platform == "win32" else []
    candidates += [["python3.12"], ["python3"], ["python"]]
    for cmd in candidates:
        try:
            out = subprocess.run(
                cmd + ["-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=10,
            )
            if out.returncode != 0 or not out.stdout.strip():
                continue
            exe = out.stdout.strip()
            v = subprocess.run([exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], capture_output=True, text=True, timeout=5)
            if v.returncode == 0 and v.stdout.strip() == "3.12":
                return exe
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _run_with_venv_py312(root):
    """Create Python 3.12 venv, install deps, run build_nuitka.py --mingw64."""
    py312 = _find_python312()
    if not py312:
        print("Python 3.12 not found. Install it (e.g. python.org or pyenv) and ensure 'py -3.12' or 'python3.12' works.")
        sys.exit(1)
    venv_dir = os.path.join(root, ".venv312")
    script = os.path.join(root, "build_nuitka.py")
    if not os.path.isdir(venv_dir):
        print("Creating venv with Python 3.12 at", venv_dir)
        subprocess.check_call([py312, "-m", "venv", venv_dir])
    venv_python = os.path.join(venv_dir, "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(venv_dir, "bin", "python")
    if not os.path.isfile(venv_python):
        venv_python = os.path.join(venv_dir, "bin", "python") if sys.platform != "win32" else venv_python
    print("Installing nuitka and Pillow in venv...")
    subprocess.check_call([venv_python, "-m", "pip", "install", "-q", "nuitka", "Pillow"])
    argv = [venv_python, script, "--mingw64"]
    print("Running:", " ".join(argv))
    subprocess.check_call(argv, cwd=root)


def _find_vcvars64():
    """Return path to vcvars64.bat if Visual Studio/Build Tools is installed."""
    vswhere = os.path.join(
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        r"Microsoft Visual Studio\Installer\vswhere.exe",
    )
    if not os.path.isfile(vswhere):
        return None
    # Try with C++ component first; then any VS installation (in case component ID changed).
    for requires in ["Microsoft.VisualStudio.Component.VC.Tools.x86.x64", None]:
        try:
            args = [vswhere, "-latest", "-products", "*", "-property", "installationPath"]
            if requires:
                args = [vswhere, "-latest", "-products", "*", "-requires", requires, "-property", "installationPath"]
            out = subprocess.run(args, capture_output=True, text=True, timeout=10)
            if out.returncode != 0 or not out.stdout:
                continue
            base = out.stdout.strip().split("\n")[0].strip()
            path = os.path.join(base, "VC", "Auxiliary", "Build", "vcvars64.bat")
            if os.path.isfile(path):
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    if "--venv-py312" in sys.argv:
        sys.argv.remove("--venv-py312")
        _run_with_venv_py312(root)
        return

    try:
        import nuitka  # noqa: F401
    except ImportError:
        print("Nuitka is not installed in this environment.")
        print("Install it with:  pip install nuitka Pillow")
        print("Or use a dedicated build env:  python build_nuitka.py --venv-py312")
        sys.exit(1)

    use_mingw64 = "--mingw64" in sys.argv
    if use_mingw64:
        sys.argv.remove("--mingw64")

    os.chdir(root)
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",
        "--include-module=ptompy",
        "--output-dir=build",
        "--output-filename=ptompy.exe",
        "--windows-console-mode=disable",
        # Minimize footprint: exclude modules not used by main.py/ptompy
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=test",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=pydoc",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=distutils",
        "--nofollow-import-to=pip",
        "--nofollow-import-to=idlelib",
        "--nofollow-import-to=ensurepip",
        "--nofollow-import-to=lib2to3",
        "--nofollow-import-to=tkinter.test",
        "--nofollow-import-to=multiprocessing",
        "--nofollow-import-to=concurrent.futures",
        "main.py",
    ]
    if use_mingw64:
        cmd.insert(5, "--mingw64")
        if sys.version_info >= (3, 13):
            print("Warning: MinGW64 is not supported with Python 3.13+. Use Python 3.12 for --mingw64, or install MSVC.")
    elif sys.version_info >= (3, 13):
        cmd.insert(5, "--msvc=latest")
    # Favicon: prefer icons/favicon.ico so favicon can live with other icons
    favicon_src = os.path.join(root, "icons", "favicon.ico")
    if not os.path.isfile(favicon_src):
        favicon_src = os.path.join(root, "favicon.ico")
    if os.path.isfile(favicon_src):
        rel = os.path.relpath(favicon_src, root).replace("\\", "/")
        cmd.insert(-1, f"--include-data-files={rel}=favicon.ico")
    if os.path.isdir(os.path.join(root, "icons")):
        cmd.insert(-1, "--include-data-dir=icons=icons")
    # Optional: use --onefile for a single executable (slower startup)
    # cmd.insert(-2, "--onefile")

    # On Windows with Python 3.13+, Nuitka needs MSVC (unless --mingw64). Run inside
    # a VS environment so the compiler is on PATH.
    if sys.platform == "win32" and sys.version_info >= (3, 13) and not use_mingw64:
        vcvars = _find_vcvars64()
        if vcvars:
            full_inner = subprocess.list2cmdline(cmd)
            shell_cmd = f'call "{vcvars}" && {full_inner}'
            print("Using Visual Studio environment:", vcvars)
            subprocess.check_call(["cmd", "/c", shell_cmd])
            return
        # vcvars not found; try Nuitka anyway (it may find MSVC via registry).
        try:
            subprocess.check_call(cmd)
            return
        except subprocess.CalledProcessError:
            pass
        # Fall back to Python 3.12 venv + MinGW64 (no MSVC or --venv-py312 needed).
        print("MSVC not found. Using Python 3.12 venv + MinGW64...")
        _run_with_venv_py312(root)
        return
    subprocess.check_call(cmd)

if __name__ == "__main__":
    main()
