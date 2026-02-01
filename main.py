#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import Tk, ttk, Frame, Label, StringVar
from tkinter.filedialog import askopenfilename


import ptompy

CONFIG_APP_NAME = 'ptompy tool'
CONFIG_APP_VERSION = 0.2


def _set_windows_taskbar_icon():
    """Set Windows AppUserModelID so the taskbar shows our icon instead of Python's when run as python main.py."""
    if sys.platform != "win32":
        return
    try:
        ctypes = __import__("ctypes")
        shell32 = ctypes.windll.shell32  # noqa: F821
        shell32.SetCurrentProcessExplicitAppUserModelID("PtoMpy.App")
    except Exception:
        pass

def _app_base():
    """Base path for app assets (script dir or exe dir when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def _icon_path(name):
    """Path to icons/<name>.ico if it exists, else None."""
    p = _app_base() / "icons" / (name if name.endswith(".ico") else f"{name}.ico")
    return str(p) if p.is_file() else None


class ParseGUI(object):
    def __init__(self, master):
        self.root = master
        self.mainframe = Frame(master)
        self.mainframe.pack(fill='both', expand=True)
        self.pfile = None  # Path to selected .p file; .m path is always pfile.with_suffix('.m')
        self.pwd = _app_base()
        # Title: what the app does
        self.title_label = Label(self.mainframe, text="MATLAB/Octave .p → .m")
        self.title_label.pack(side="top")
        self.title_label2 = Label(self.mainframe, text="Decode pcode to source.")
        self.title_label2.pack(side="top")

        # Which .p file is selected (shown after "Select p-file")
        self.filename = StringVar()
        self.filename.set("No file selected")
        self.filename_label = Label(self.mainframe, textvariable=self.filename)
        self.filename_label.pack()
        # Status: ready / converting / saved / error
        self.status = StringVar()
        self.status.set("Select a .p file, then click Convert")
        self.status_label = Label(
            self.mainframe,
            textvariable=self.status,
            fg='green',
            wraplength=400,
            justify='left',
        )
        self.status_label.pack(anchor='w', fill='x')
        btn_frame = Frame(self.mainframe)
        btn_frame.pack(side="top", pady=(4, 0))
        icon_size = (16, 16)
        self._btn_imgs = []

        # Helper function to load icons
        def _btn_icon(name):
            path = _icon_path(name)
            
            img = Image.open(path).convert("RGBA").resize(icon_size)
            tkimg = ImageTk.PhotoImage(img)
            self._btn_imgs.append(tkimg)
            return tkimg
        # enddef

        # Control buttons        
        self.select_file = ttk.Button(btn_frame, text="1. Select p-file", command=self.select_pfile, image=_btn_icon("open-pfile"), compound="left")
        self.select_file.pack(side="left")
        self.convert_btn = ttk.Button(btn_frame, text="2. Convert!", command=self.parse_file, image=_btn_icon("convert"), compound="left")
        self.convert_btn.pack(side="left")
        self.open_mfile_btn = ttk.Button(btn_frame, text="3. Open m-file", command=self.view_mfile, image=_btn_icon("open-mfile"), compound="left")
        self.open_mfile_btn.pack(side="left")
        self.progressbar = ttk.Progressbar(mode="indeterminate")
        self.progressbar.pack_forget()

    def _fit_window_height(self, min_h=130):
        """Resize window height to fit content (status wrap, progress bar, etc.)."""
        self.root.update_idletasks()
        req = self.mainframe.winfo_reqheight()
        new_h = max(min_h, req+5)  # padding for title bar and margin
        self.root.geometry(f'450x{new_h}')

    def select_pfile(self):
        path_str = askopenfilename(initialdir=self.pwd)
        if not path_str or not path_str.endswith('.p'):
            return  # user cancelled; keep current filename and status
        
        self.pfile = Path(path_str)
        self.pwd = self.pfile.parent
        self.mfile = self.pfile.with_suffix('.m')

        self.filename.set("File: " + self.pfile.name)
        self.status.set("Click Convert to decode and save .m file")
        self.status_label.config(fg='green')
        self._fit_window_height()

    def view_mfile(self):
        if not self.pfile:
            return
        mfile = self.pfile.with_suffix('.m')
        if mfile.exists():
            subprocess.Popen(["notepad", str(mfile.resolve())])

    def parse_file(self):
        self.progressbar.pack()
        self.progressbar.start()
        if not self.pfile or self.pfile.suffix != '.p':
            self.progressbar.stop()
            self.progressbar.pack_forget()
            self.status.set("Please select a .p (MATLAB) file!")
            self.status_label.config(fg='red')

        elif self.filename.get() != 'No file selected' and self.pfile.suffix == '.p':
            self.status.set("Decoding... (most files decode in a few seconds)")
            code, msg = ptompy.parse(self.pfile, self.mfile)
            self.progressbar.stop()
            self.progressbar.pack_forget() 
            self.status.set(f"{msg}")
            self.status_label.config(fg='red' if code != 0 else 'green')

        else:
            self.progressbar.stop()
            self.progressbar.pack_forget()
            self.status.set("Please select a .p (MATLAB) file!")
            self.status_label.config(fg='red')
        # endif
        self._fit_window_height()


def _logo_from_ico(ico_name, size=(64, 64)):
    """Load .ico and return ImageTk.PhotoImage for panel logo, or None on failure."""
    try:
        ico_path = _icon_path(ico_name)
        img = Image.open(ico_path).convert("RGBA").resize(size)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def info():
    print("*"*100)
    print(__doc__ or f"{CONFIG_APP_NAME} - convert Matlab .p to .m")
    print("Version:      ", f"{CONFIG_APP_NAME} \t{ptom_get_version():.2f}")
    print("Platform:     ", sys.platform)
    print("Python:       ", sys.version[:5], 'located at', sys.executable)
    print("Usage:")
    print("\t ptompy.exe pfile [mfile]  - convert pfile to mfile (mfile defaults to pfile.m)")
    print("\t exit - to quit program (when running without args)")
    print("*"*100)

def ptom_get_version():
    return CONFIG_APP_VERSION

def main():
    mode = "tui" if len(sys.argv) > 1 else "gui"
    info()
    if mode == "gui":
        _set_windows_taskbar_icon()  # So taskbar shows app icon, not Python, when run as python main.py
        root_widget = Tk()
        win_icon = _icon_path("app")
        
        root_widget.iconbitmap(win_icon)
        
        ParseGUI(root_widget)
        # Use same icon as window for panel logo so they match (octave-logo scales well)
        img_logo = _logo_from_ico(_icon_path("logo"))
        root_widget._panel_logo = img_logo  # keep reference
        Label(root_widget, image=img_logo).place(x=45, y=0)
        root_widget.wm_title(CONFIG_APP_NAME)
        root_widget.geometry('450x130')
        root_widget.resizable(width=False, height=True)
        root_widget.mainloop()
    elif mode == "tui":
        if not ptompy.init():
            print("Initialization failed")
            return
        if len(sys.argv) in (2, 3) and sys.argv[1] != "--tui":
            pfile = sys.argv[1]
            mfile = sys.argv[2] if len(sys.argv) >= 3 else str(Path(pfile).with_suffix('.m'))
            code, msg = ptompy.parse(pfile, mfile)
            print(msg)
            return
        while True:
            pfile = input("pfile (or exit): ").strip()
            if not pfile or pfile.lower() == "exit":
                break
            mfile_in = input("mfile (Enter = same name .m): ").strip()
            mfile = mfile_in if mfile_in else str(Path(pfile).with_suffix('.m'))
            code, msg = ptompy.parse(pfile, mfile)
            print(msg)
    else:
        print('Running with sample data.')
        print('')
        print('----------PARSE LOG START------------------')
        code, msg = ptompy.parse("examples/rician_orig.p", "examples/rician_orig.m")
        print('----------PARSE LOG END--------------------')
        print(f"Result: [{code}] {msg}")
        print('Run with default settings')

if __name__ == "__main__":
    main()
