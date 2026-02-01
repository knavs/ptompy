# Agent instructions – PtoMpy

## Project

**PtoMpy** converts MATLAB `.p` (p-code) files to `.m` source. It is a Python port of `ptom.c`. The app is a small Windows GUI (tkinter + Pillow) that lets the user pick a `.p` file, convert it, and open the resulting `.m` file.

## Key files

| File | Role |
|------|------|
| `main.py` | Entry point. Tkinter GUI: select `.p` file, convert (calls `ptompy`), open `.m` in Notepad. Window height grows with content (`_fit_window_height()`). |
| `ptompy.py` | Core logic: read `.p` → descramble → uncompress (stdlib zlib) → decode bytecode → write `.m`. API: `init()`, `parse(pfile, mfile)`. `parse()` returns `(code, msg)`; catches `KeyboardInterrupt` and `Exception`. |
| `build_nuitka.py` | Nuitka build script. Produces standalone `build/` with `ptompy.exe`. |
| `setup.iss`, `build_setup.py` | Inno Setup: optional setup.exe from build (`python build_setup.py` → `build/PtoMpy_Setup_*.exe`). |
| `matlab_formatter.py` | Used by ptompy for formatting/emitting `.m` source. |
| `ptom.c` / `ptom.h` | Original C reference; not built by this repo. |

**Folder layout**

- **examples/** – Sample `.p` / `.m` files and test outputs (e.g. `example.p`, `rician_orig.p`, `Test_*.m`).
- **icons/** – App icons (window, buttons, panel logo). Used by `main.py`, Nuitka build, and `setup.iss`. Icons: `open-pfile.ico`, `convert.ico`, `open-mfile.ico`, `app.ico`, `logo.ico`; optionally `favicon.ico` (Nuitka/build: `icons/favicon.ico` or root `favicon.ico`).

## Conventions

- **Platform**: Windows-oriented (Notepad for opening `.m`, Nuitka exe).
- **Python**: 3.x. Nuitka build: Python 3.12 works with MinGW64; 3.13+ needs MSVC or the script’s Python 3.12 venv path.
- **Dependencies**: See `requirements.txt`. GUI needs `Pillow`; build needs `nuitka` + `Pillow`.

## Build (Nuitka)

- Run: `python build_nuitka.py`
  - On Python 3.13+: script looks for MSVC (vswhere → vcvars64.bat). If not found, it tries Nuitka anyway, then falls back to a Python 3.12 venv + MinGW64 (no need to pass `--venv-py312` if 3.12 is installed).
  - Options: `--mingw64` (use MinGW64 with current Python; requires Python ≤3.12), `--venv-py312` (force create 3.12 venv and build with MinGW64).
- Output: standalone folder under `build/` with `ptompy.exe`, favicon. Favicon is included from `icons/favicon.ico` if present, else root `favicon.ico`. Nuitka options include `--standalone`, tk-inter plugin, `--include-module=ptompy`, and `--nofollow-import-to=...` for a smaller footprint.
- Optional: `python build_setup.py` (requires Inno Setup 6) → `build/PtoMpy_Setup_*.exe` installer.

## What to change / avoid

- **main.py** “Open m-file”: uses `subprocess.Popen(["notepad", ...])`; safe on Windows. Changing to another editor or `os.startfile` is fine if requested.
- **ptompy**: Keep compatibility with the existing API used by `main.py`; decompression uses stdlib zlib only.
- **build_nuitka.py**: Preserve the flow (vcvars → try Nuitka → fallback to 3.12 venv). Adjust Nuitka flags (e.g. `--nofollow-import-to`) only when needed for size or compatibility.
