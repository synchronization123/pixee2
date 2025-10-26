# Launcher.pyw
"""
DefectDojo Engagement Manager Launcher (full)
- Silent server start (no console) and robust stop/kill
- Minimize to system tray (pystray + Pillow required for tray)
- Check for new version from API, download .zip, extract and replace files
- Save/update token.json from GUI (token displayed masked: first 4 + last 4 visible)
- Optional psutil for more reliable process cleanup
- All long-running/network tasks run in background threads
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess, sys, threading, requests, json, time, os, signal, tempfile, shutil, zipfile, traceback

# Optional libraries
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    pystray = None
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import psutil
except Exception:
    psutil = None

# Windows creation flags (safe getattr)
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)

# Configurable: API host & endpoints
API_BASE = "https://demo.defectdojo.org"
ENGAGEMENT_ENDPOINT = "/api/v2/engagements/14/"
DOWNLOAD_ENDPOINT = "/api/v2/engagements/14/files/download/1/"

# Files/folders to remove before replacing with update
REMOVE_LIST = ["static", "templates", "app.py", "version.json"]

# ---------- Utility functions ----------

def safe_join_cwd(*parts):
    return os.path.join(os.getcwd(), *parts)

def mask_token_display(token: str) -> str:
    """
    Mask token so first 4 and last 4 characters visible, middle replaced by •.
    If token shorter than or equal to 8 chars, show first char + dots + last char as fallback.
    """
    if not token:
        return ""
    s = str(token)
    if len(s) <= 8:
        # show first 1 and last 1, with dots in between
        if len(s) <= 2:
            return s[0] + "•" * (len(s)-1) if len(s) > 1 else s
        return s[0] + "•" * (len(s)-2) + s[-1]
    return s[:4] + "•" * (len(s)-8) + s[-4:]

# ---------- Main Launcher class ----------

class DefectDojoLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("DefectDojo Engagement Manager")
        self.root.geometry("680x460")
        self.root.resizable(False, False)

        # process management
        self.process = None
        self.pid = None
        self.server_running = False

        # tray objects
        self.tray_icon = None
        self._tray_visible = False

        # token handling
        self._full_token = None  # store the real token in memory (not masked)
        self.token_mask_var = tk.StringVar(value="")  # shown in the disabled entry

        # version info
        self.local_version_var = tk.StringVar(value=self._read_local_version() or "N/A")
        self.remote_version_var = tk.StringVar(value="Remote version: N/A")

        # build UI
        self._build_ui()

        # minimize->tray binding
        self.root.bind("<Unmap>", self._on_unmap)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # load token initially
        self._load_token_to_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')

        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="DefectDojo Engagement Manager", font=("Segoe UI", 16, "bold")).pack(pady=(0,8))

        # Top row: Local version and token controls
        top_frame = ttk.Frame(main)
        top_frame.pack(fill=tk.X, pady=(0,8))

        # Local version display
        ver_frame = ttk.Frame(top_frame)
        ver_frame.pack(side=tk.LEFT, padx=(0,12))
        ttk.Label(ver_frame, text="Local version:").pack(anchor=tk.W)
        ttk.Label(ver_frame, textvariable=self.local_version_var, font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        # Token area (masked)
        token_frame = ttk.Frame(top_frame)
        token_frame.pack(side=tk.LEFT, padx=(4,12))
        ttk.Label(token_frame, text="API Token:").pack(anchor=tk.W)
        token_entry = ttk.Entry(token_frame, textvariable=self.token_mask_var, width=42, state="readonly")
        token_entry.pack(side=tk.LEFT)
        # Buttons: Edit and Save
        ttk.Button(token_frame, text="Edit Token", command=self._edit_token_dialog).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(token_frame, text="Save Token", command=self._save_token_from_ui).pack(side=tk.LEFT, padx=(6,0))

        # Update/version area
        action_frame = ttk.LabelFrame(main, text="Update / Version", padding=10)
        action_frame.pack(fill=tk.X, pady=(8,10))
        action_row = ttk.Frame(action_frame)
        action_row.pack(fill=tk.X)
        ttk.Button(action_row, text="Check for new version", command=self.check_new_version).pack(side=tk.LEFT)
        ttk.Button(action_row, text="Open version.json", command=self.open_version_json).pack(side=tk.LEFT, padx=(8,0))
        ttk.Label(action_frame, textvariable=self.remote_version_var).pack(anchor=tk.W, pady=(8,0))
        ttk.Label(action_frame, text="(If remote version is 'demo' or equals local, no download.)", font=("Segoe UI", 8)).pack(anchor=tk.W)

        # Server status frame
        status_frame = ttk.LabelFrame(main, text="Server Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(8,10))
        self.status_label = ttk.Label(status_frame, text="Status: Stopped", font=("Segoe UI", 11, "bold"))
        self.status_label.pack()
        self.url_label = ttk.Label(status_frame, text="", font=("Segoe UI", 9), foreground="blue")
        self.url_label.pack()

        # Buttons
        btns = ttk.Frame(main)
        btns.pack(pady=(8,6))
        self.start_btn = ttk.Button(btns, text="Start Server", width=16, command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=6)
        self.stop_btn = ttk.Button(btns, text="Stop Server", width=16, command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=6)
        self.open_btn = ttk.Button(btns, text="Open Browser", width=16, command=self.open_browser, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=6)

        # Tray controls
        tray_frame = ttk.Frame(main)
        tray_frame.pack(fill=tk.X, pady=(6,0))
        ttk.Button(tray_frame, text="Hide to Tray Now", command=self.hide_to_tray).pack(side=tk.LEFT, padx=(0,6))
        ttk.Button(tray_frame, text="Tray Help", command=self._tray_help).pack(side=tk.LEFT)

        # Footer: dependency status
        deps = f"pystray: {'OK' if pystray else 'Missing'}    pillow: {'OK' if Image else 'Missing'}    psutil: {'OK' if psutil else 'Missing'}"
        ttk.Label(main, text=deps, font=("Segoe UI", 8)).pack(side=tk.BOTTOM, pady=(8,0))

    # ---------------- Token helpers ----------------
    def _token_path(self):
        return safe_join_cwd("token.json")

    def _read_token(self):
        """Read token.json and return token string or None."""
        try:
            p = self._token_path()
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # accept several possible keys
                        for k in ("token", "Token", "auth", "authorization"):
                            if k in data and data[k]:
                                return str(data[k])
                    if isinstance(data, str):
                        return data
        except Exception:
            pass
        return None

    def _load_token_to_ui(self):
        """Load token from disk and display masked in UI."""
        tok = self._read_token()
        self._full_token = tok
        self.token_mask_var.set(mask_token_display(tok) if tok else "")

    def _edit_token_dialog(self):
        """
        Open a modal dialog asking the user to enter the full token.
        Prefills with the real token if present (not masked).
        """
        prompt = "Enter API token (will be saved to token.json). Leave empty to delete saved token."
        # Use a simpledialog that shows plain text entry for token (user must type or paste)
        initial = self._full_token or ""
        result = simpledialog.askstring("Edit Token", prompt, initialvalue=initial, parent=self.root, show=None)
        # If user presses Cancel, result is None and we do nothing.
        if result is None:
            return
        # Trim and store in memory (but don't write to disk until Save Token pressed)
        result = result.strip()
        self._full_token = result if result else None
        self.token_mask_var.set(mask_token_display(self._full_token) if self._full_token else "")

    def _save_token_from_ui(self):
        """Write current in-memory token to token.json. If empty, delete file."""
        try:
            if not self._full_token:
                # delete token.json if exists
                p = self._token_path()
                if os.path.exists(p):
                    os.remove(p)
                messagebox.showinfo("Token", "Saved token cleared (token.json deleted).")
                self.token_mask_var.set("")
                return
            with open(self._token_path(), "w", encoding="utf-8") as f:
                json.dump({"token": self._full_token}, f, indent=2)
            messagebox.showinfo("Token", "token.json saved.")
            # ensure masked display updated
            self.token_mask_var.set(mask_token_display(self._full_token))
        except Exception as e:
            messagebox.showerror("Token", f"Failed to save token.json:\n{e}")

    # ---------------- Version helpers ----------------
    def _version_path(self):
        return safe_join_cwd("version.json")

    def _read_local_version(self):
        try:
            p = self._version_path()
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    j = json.load(f)
                    if isinstance(j, dict) and "version" in j:
                        return str(j["version"])
                    if isinstance(j, str):
                        return j
        except Exception:
            pass
        return None

    def open_version_json(self):
        try:
            p = self._version_path()
            if not os.path.exists(p):
                messagebox.showinfo("version.json", "version.json not found.")
                return
            with open(p, "r", encoding="utf-8") as f:
                txt = f.read()
            dlg = tk.Toplevel(self.root)
            dlg.title("version.json")
            txtw = tk.Text(dlg, width=80, height=18)
            txtw.pack(fill=tk.BOTH, expand=True)
            txtw.insert("1.0", txt)
            txtw.config(state=tk.DISABLED)
            ttk.Button(dlg, text="Close", command=dlg.destroy).pack(pady=6)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open version.json:\n{e}")

    # ---------------- Networking helpers ----------------
    def _get_headers(self):
        headers = {}
        if self._full_token:
            headers["Authorization"] = f"Token {self._full_token}"
        return headers

    def check_new_version(self):
        threading.Thread(target=self._check_new_version_thread, daemon=True).start()

    def _check_new_version_thread(self):
        self._set_status_text("Checking remote version...", "orange")
        try:
            url = API_BASE.rstrip("/") + ENGAGEMENT_ENDPOINT
            resp = requests.get(url, headers=self._get_headers(), timeout=12)
            if resp.status_code != 200:
                raise Exception(f"API returned status {resp.status_code}")
            j = resp.json()
            # robust extraction of 'version'
            remote_version = None
            if isinstance(j, dict):
                # common direct keys
                remote_version = j.get("version") or j.get("Version")
                # nested possibilities
                if not remote_version and "params" in j and isinstance(j["params"], dict):
                    remote_version = j["params"].get("version")
                if not remote_version and "custom_fields" in j and isinstance(j["custom_fields"], dict):
                    remote_version = j["custom_fields"].get("version")
                # full recursive search fallback
                if not remote_version:
                    def find_version(d):
                        if isinstance(d, dict):
                            if "version" in d:
                                return d["version"]
                            for v in d.values():
                                r = find_version(v)
                                if r:
                                    return r
                        if isinstance(d, list):
                            for item in d:
                                r = find_version(item)
                                if r:
                                    return r
                        return None
                    remote_version = find_version(j)
            if remote_version is None:
                raise Exception("Remote 'version' not found in API response.")
            # update remote version label
            self.root.after(0, lambda: self.remote_version_var.set(f"Remote version: {remote_version}"))
            # logic for demo or equal
            if str(remote_version).lower() == "demo":
                self._set_status_text("Remote version is 'demo' — skipping update.", "blue")
                return
            local_ver = self._read_local_version()
            if local_ver is not None and str(remote_version) == str(local_ver):
                self._set_status_text("Local version matches remote. No update required.", "green")
                return
            # ask user to confirm download
            ask_msg = f"Remote version {remote_version} available (local: {local_ver}).\nDownload & install now?"
            if not messagebox.askyesno("Update available", ask_msg):
                self._set_status_text("Update cancelled by user.", "blue")
                return
            # proceed download
            self._set_status_text("Downloading update...", "orange")
            download_url = API_BASE.rstrip("/") + DOWNLOAD_ENDPOINT
            tmpdir = tempfile.mkdtemp(prefix="dd_update_")
            zip_path = os.path.join(tmpdir, "update.zip")
            # stream download
            with requests.get(download_url, headers=self._get_headers(), stream=True, timeout=60) as r:
                if r.status_code not in (200, 201, 202):
                    raise Exception(f"Download failed with status {r.status_code}")
                with open(zip_path, "wb") as fd:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            fd.write(chunk)
            # validate zip
            if not zipfile.is_zipfile(zip_path):
                raise Exception("Downloaded file is not a valid zip archive.")
            self._set_status_text("Applying update...", "orange")
            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            # remove old targets
            for rel in REMOVE_LIST:
                path = safe_join_cwd(rel)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    elif os.path.isfile(path):
                        os.remove(path)
                except Exception:
                    # ignore but continue
                    pass
            # copy extracted files into cwd
            copied_any = False
            for rootdir, dirs, files in os.walk(extract_dir):
                rel_root = os.path.relpath(rootdir, extract_dir)
                target_root = safe_join_cwd(rel_root) if rel_root != "." else os.getcwd()
                os.makedirs(target_root, exist_ok=True)
                for fname in files:
                    src = os.path.join(rootdir, fname)
                    dst = os.path.join(target_root, fname)
                    try:
                        shutil.copy2(src, dst)
                        copied_any = True
                    except Exception:
                        try:
                            if os.path.exists(dst):
                                os.remove(dst)
                            shutil.copy2(src, dst)
                            copied_any = True
                        except Exception:
                            pass
            # cleanup zip and temp dir
            try:
                os.remove(zip_path)
            except Exception:
                pass
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
            if not copied_any:
                raise Exception("Update applied but no files were copied. Check zip contents.")
            # write new version.json
            try:
                with open(self._version_path(), "w", encoding="utf-8") as vf:
                    json.dump({"version": str(remote_version)}, vf, indent=2)
                self.root.after(0, lambda: self.local_version_var.set(str(remote_version)))
            except Exception:
                pass
            self._set_status_text(f"Update to {remote_version} applied successfully.", "green")
            messagebox.showinfo("Update", f"Update to version {remote_version} applied successfully.")
        except Exception as e:
            tb = traceback.format_exc()
            print("Update error:", tb)
            self._set_status_text("Update failed. See error dialog.", "red")
            messagebox.showerror("Update failed", f"{e}")

    # ---------------- Server start / stop (silent) ----------------
    def _python_interpreter(self):
        exe = sys.executable
        if sys.platform == "win32":
            if exe.lower().endswith("pythonw.exe"):
                return exe
            sibling = os.path.join(os.path.dirname(exe), "pythonw.exe")
            if os.path.exists(sibling):
                return sibling
        return exe

    def start_server(self):
        if self.server_running:
            messagebox.showinfo("Info", "Server already running.")
            return
        try:
            interpreter = self._python_interpreter()
            cmd = [interpreter, "app.py"]

            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW | DETACHED_PROCESS
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                except Exception:
                    startupinfo = None

            if sys.platform == "win32":
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                    creationflags=creationflags, startupinfo=startupinfo, shell=False
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid, shell=False
                )

            self.pid = self.process.pid
            self.server_running = True
            self._set_status_text("Status: Starting...", "orange")
            self.start_btn.config(state=tk.DISABLED)
            threading.Thread(target=self._check_server_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Start failed", f"Could not start server:\n{e}")
            self.server_running = False
            self.process = None
            self.pid = None

    def _check_server_thread(self):
        for _ in range(12):
            time.sleep(1)
            try:
                r = requests.get("http://127.0.0.1:5000/", timeout=2)
                if r.status_code == 200:
                    self.root.after(0, self._on_server_started)
                    return
            except Exception:
                continue
        self.root.after(0, self._on_server_failed)

    def _on_server_started(self):
        self._set_status_text("Status: Running", "green")
        self.url_label.config(text="http://127.0.0.1:5000")
        self.stop_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Server", "Server started successfully.")

    def _on_server_failed(self):
        self._set_status_text("Status: Failed", "red")
        self.start_btn.config(state=tk.NORMAL)
        self.server_running = False

    def stop_server(self):
        if not self.server_running and not self.pid:
            return
        try:
            pid = self.pid
            try:
                if self.process:
                    self.process.terminate()
            except Exception:
                pass
            if sys.platform != "win32" and pid:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except Exception:
                    pass
            start = time.time()
            while time.time() - start < 3:
                if not self._is_process_alive(pid):
                    break
                time.sleep(0.2)
            if self._is_process_alive(pid):
                if sys.platform == "win32":
                    try:
                        subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                else:
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    except Exception:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except Exception:
                            pass
            # psutil cleanup
            if psutil:
                try:
                    if psutil.pid_exists(pid):
                        rootp = psutil.Process(pid)
                        for child in rootp.children(recursive=True):
                            try:
                                child.kill()
                            except Exception:
                                pass
                        try:
                            rootp.kill()
                        except Exception:
                            pass
                    else:
                        for p in psutil.process_iter(['pid','cmdline']):
                            try:
                                cmdline = " ".join(p.info.get('cmdline') or [])
                                if "app.py" in cmdline:
                                    p.kill()
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception as e:
            print("stop_server error:", e)
        finally:
            self._cleanup_after_stop()

    def _cleanup_after_stop(self):
        try:
            if self.process:
                try:
                    self.process.wait(timeout=0.2)
                except Exception:
                    pass
        except Exception:
            pass
        self.process = None
        self.pid = None
        self.server_running = False
        self._set_status_text("Status: Stopped", "red")
        self.url_label.config(text="")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)

    def _is_process_alive(self, pid):
        if not pid:
            return False
        if psutil:
            return psutil.pid_exists(pid)
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def open_browser(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:5000")

    # ---------------- Tray integration ----------------
    def _create_icon_image(self, size=64, text="DD"):
        if Image is None or ImageDraw is None:
            return None
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, size-1, size-1), fill=(34,113,230,255))
        try:
            if ImageFont:
                try:
                    font = ImageFont.truetype("arial.ttf", int(size*0.42))
                except Exception:
                    font = ImageFont.load_default()
                w, h = draw.textsize(text, font=font)
                draw.text(((size-w)/2, (size-h)/2), text, fill="white", font=font)
            else:
                draw.text((size*0.28, size*0.28), text, fill="white")
        except Exception:
            pass
        return img

    def hide_to_tray(self):
        if not pystray or Image is None:
            messagebox.showwarning("Tray not available", "pystray or pillow not installed. Install with:\n\npip install pystray pillow")
            return
        if self._tray_visible:
            return
        try:
            self.root.withdraw()
        except Exception:
            self.root.iconify()

        img = self._create_icon_image(64, "DD") or None
        menu = pystray.Menu(
            pystray.MenuItem("Restore", lambda icon, item: self._tray_restore()),
            pystray.MenuItem("Stop Server", lambda icon, item: self._tray_stop_server()),
            pystray.MenuItem("Exit", lambda icon, item: self._tray_exit())
        )
        self.tray_icon = pystray.Icon("defectdojo_launcher", img, "DefectDojo", menu)
        try:
            self.tray_icon.run_detached(self._tray_run)
        except Exception:
            def run_icon():
                try:
                    self.tray_icon.run()
                except Exception:
                    pass
            threading.Thread(target=run_icon, daemon=True).start()
        self._tray_visible = True

    def _tray_run(self, icon):
        try:
            icon.visible = True
        except Exception:
            pass
        try:
            icon.onclick = lambda x=None: self._tray_restore()
        except Exception:
            pass

    def _tray_restore(self):
        self.root.after(0, self._do_restore)

    def _do_restore(self):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self._tray_visible = False
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def _tray_stop_server(self):
        self.root.after(0, self.stop_server)

    def _tray_exit(self):
        self.root.after(0, self.exit_app)

    def _on_unmap(self, event):
        try:
            if self.root.state() == "iconic":
                self.hide_to_tray()
        except Exception:
            pass

    def _tray_help(self):
        if not pystray:
            messagebox.showinfo("Tray Help", "pystray is not installed. Install with:\n\npip install pystray pillow")
            return
        messagebox.showinfo("Tray Help", "Minimize hides to tray. Use tray menu to Restore/Stop Server/Exit.")

    # ---------------- Utilities ----------------
    def _set_status_text(self, text, color="black"):
        def applyit():
            self.status_label.config(text=text, foreground=color)
        try:
            self.root.after(0, applyit)
        except Exception:
            applyit()

    # ---------------- Exit ----------------
    def exit_app(self):
        if self.server_running:
            if not messagebox.askyesno("Confirm", "Stop server and exit?"):
                return
            self.stop_server()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
            self._tray_visible = False
        try:
            self.root.destroy()
        except Exception:
            pass

# -------------------- run main --------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = DefectDojoLauncher(root)
    root.mainloop()
