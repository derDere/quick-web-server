import argparse
import subprocess
import sys
import socket
import time
import os
import shutil

# ANSI color constants (foreground only)
C_RED = "\033[31m"
C_YELLOW = "\033[33m"
C_CYAN = "\033[36m"
C_RESET = "\033[0m"


DEFAULT_HTTP_PORT = 8080
DEFAULT_PROXY_PORT = 8443
DEFAULT_HOST = "127.0.0.1"

__RUN_LIVERELOAD_SERVER = f"--run-livereload-server"
RUN_LIVERELOAD_SERVER = __RUN_LIVERELOAD_SERVER.lstrip("-").replace('-', '_')
__RELOAD = f"--reload"
RELOAD = __RELOAD.lstrip("-").replace('-', '_')
__HTTP_PORT = f"--http-port"
HTTP_PORT = __HTTP_PORT.lstrip("-").replace('-', '_')
__HTTP_HOST = f"--http-host"
HTTP_HOST = __HTTP_HOST.lstrip("-").replace('-', '_')
__RANDOM_HTTP_PORT = f"--random-http-port"
RANDOM_HTTP_PORT = __RANDOM_HTTP_PORT.lstrip("-").replace('-', '_')
__RANDOM_PROXY_PORT = f"--random-proxy-port"
RANDOM_PROXY_PORT = __RANDOM_PROXY_PORT.lstrip("-").replace('-', '_')


def install_dependencies():
    """Blindly install runtime dependencies based on detected OS & package manager.

    Requirements (no pre-check logic, as requested):
    - Install Node.js (using first available package manager) so we can run a global HTTPS proxy tool.
    - Install global npm package 'local-ssl-proxy'.
    - Install Python package 'livereload'.

    We DO detect which package manager binary exists (that's not a dependency check, just environment discovery).
    We DO NOT skip commands if already installed; failures are reported but not fatal.
    """

    py_exe = sys.executable
    system = sys.platform  # 'win32', 'darwin', 'linux'

    def run(cmd, shell=False):
        print(f"{C_CYAN}[install] RUN -> {' '.join(cmd) if isinstance(cmd, list) else cmd}{C_RESET}")
        try:
            subprocess.run(cmd, check=False, shell=shell)
        except Exception as e:
            print(f"{C_YELLOW}[install][warn] Execution failed: {e}{C_RESET}")

    def which(cmd):
        return shutil.which(cmd) is not None

    # Determine package manager & formulate install commands for Node.js
    install_cmds = []

    if system == "win32":
        # Preference order: winget, choco, scoop
        if which("winget"):
            install_cmds.append(["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS", "-h"])
        elif which("choco"):
            install_cmds.append(["choco", "install", "-y", "nodejs-lts"])
        elif which("scoop"):
            install_cmds.append(["scoop", "install", "nodejs-lts"])
        else:
            print(f"{C_YELLOW}[install][info] No supported Windows package manager (winget|choco|scoop) detected. Skipping Node install attempt.{C_RESET}")
    
    elif system == "darwin":
        # macOS: brew or port
        if which("brew"):
            install_cmds.append(["brew", "update"])
            install_cmds.append(["brew", "install", "node"])
        elif which("port"):
            install_cmds.append(["sudo", "port", "selfupdate"])
            install_cmds.append(["sudo", "port", "install", "nodejs18"])
        else:
            print(f"{C_YELLOW}[install][info] No supported macOS package manager (brew|port) detected. Skipping Node install attempt.{C_RESET}")
    
    else:
        # Assume Linux / Unix-like
        # Preference order: apt, dnf, yum, pacman, zypper, apk
        if which("apt"):
            install_cmds.append(["sudo", "apt", "update"])
            install_cmds.append(["sudo", "apt", "install", "-y", "nodejs", "npm"])
        elif which("dnf"):
            install_cmds.append(["sudo", "dnf", "install", "-y", "nodejs", "npm"])
        elif which("yum"):
            install_cmds.append(["sudo", "yum", "install", "-y", "nodejs", "npm"])
        elif which("pacman"):
            install_cmds.append(["sudo", "pacman", "-Sy", "--noconfirm", "nodejs", "npm"])
        elif which("zypper"):
            install_cmds.append(["sudo", "zypper", "install", "-y", "nodejs", "npm"])
        elif which("apk"):
            install_cmds.append(["sudo", "apk", "add", "nodejs", "npm"])
        else:
            print(f"{C_YELLOW}[install][info] No known Linux package manager found (apt|dnf|yum|pacman|zypper|apk). Skipping Node install attempt.{C_RESET}")

    # Execute package manager commands
    for c in install_cmds:
        run(c)

    # Install global npm dependency (Windows uses same PowerShell pattern as runtime npx usage)
    if system == "win32":
        npm_ps1_candidates = [
            r"C:\\Program Files\\nodejs\\npm.ps1",
            r"C:\\Program Files (x86)\\nodejs\\npm.ps1",
        ]
        npm_ps1 = next((p for p in npm_ps1_candidates if os.path.exists(p)), None)
        if npm_ps1:
            run([
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", npm_ps1,
                "install", "-g", "local-ssl-proxy",
            ])
        else:
            # Fallback to plain npm (may still work if PATH provides it)
            run(["npm", "install", "-g", "local-ssl-proxy"])
    else:
        run(["npm", "install", "-g", "local-ssl-proxy"])  # non-Windows standard path

    # Install Python dependency (no prior check)
    run([py_exe, "-m", "pip", "install", "--upgrade", "livereload"])

    print("[install] Install routine finished (errors above, if any, are non-fatal).")


def install_command():
    """Create a small launcher script named 'qws' in a user-writable bin directory.

    Strategy:
    - Determine a target scripts/bin directory in PATH (first writable match) or fall back to:
      * Windows: %APPDATA%/Python/Scripts (create if needed)
      * POSIX: ~/.local/bin (create if needed)
    - Create (overwrite) a launcher that executes this start.py with Python.
    - Provide both a .cmd (Windows) and a bare 'qws' shell script (POSIX) when appropriate.
    - Inform the user if the chosen directory is not on PATH.
    """
    script_dir = os.path.abspath(os.path.dirname(__file__))
    start_script = os.path.join(script_dir, os.path.basename(__file__))

    is_windows = os.name == "nt"
    path_dirs = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]

    def is_system_dir(p: str) -> bool:
        pl = p.lower()
        return any(seg in pl for seg in ["program files", "windows", "system32", "systemroot"])

    def is_writable(p: str) -> bool:
        if not os.path.isdir(p):
            return False
        test_file = os.path.join(p, f".__qws_write_test_{os.getpid()}")
        try:
            with open(test_file, "w") as tf:
                tf.write("ok")
            os.remove(test_file)
            return True
        except Exception:
            return False

    # Rank PATH dirs: prefer user-space, writable, non-system.
    candidate_dirs = []
    for d in path_dirs:
        if is_writable(d):
            candidate_dirs.append(d)

    # Filter out system dirs unless nothing else available.
    user_candidates = [d for d in candidate_dirs if not is_system_dir(d)]

    target_dir = user_candidates[0] if user_candidates else (candidate_dirs[0] if candidate_dirs else None)

    if target_dir is None:
        if is_windows:
            base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Python", "Scripts")
        else:
            base = os.path.join(os.path.expanduser("~"), ".local", "bin")
        target_dir = base
    else:
        # Informative message showing where we'll install (only for debug / clarity)
        print(f"{C_CYAN}[install] Using existing writable PATH directory for launcher: {target_dir}{C_RESET}")

    created_files = []

    if is_windows:
        launcher_cmd_path = os.path.join(target_dir, "qws.cmd")
        launcher_ps1_path = os.path.join(target_dir, "qws.ps1")
        py_exe = sys.executable
        cmd_content = f"@echo off\n\n" \
                      f"REM Auto-generated launcher for quick-web-server\n" \
                      f""""{py_exe}" "{start_script}" %*"""
        ps1_content = f"# Auto-generated launcher for quick-web-server\n& '{py_exe}' '{start_script}' $args"
        try:
            with open(launcher_cmd_path, "w", encoding="utf-8") as f:
                f.write(cmd_content)
            created_files.append(launcher_cmd_path)
            with open(launcher_ps1_path, "w", encoding="utf-8") as f:
                f.write(ps1_content)
            created_files.append(launcher_ps1_path)
        except Exception as e:
            print(f"{C_YELLOW}[install][warn] Could not write Windows launchers: {e}{C_RESET}")
    else:
        launcher_path = os.path.join(target_dir, "qws")
        py_exe = sys.executable
        # Use $@ (all args) safely quoted; we intentionally avoid further shell escaping here.
        sh_content = (
            "#!/usr/bin/env sh\n"
            "# Auto-generated launcher for quick-web-server\n"
            f"exec '{py_exe}' '{start_script}' \"$@\"\n"
        )
        try:
            with open(launcher_path, "w", encoding="utf-8") as f:
                f.write(sh_content)
            os.chmod(launcher_path, 0o755)
            created_files.append(launcher_path)
        except Exception as e:
            print(f"{C_YELLOW}[install][warn] Could not write POSIX launcher: {e}{C_RESET}")

    # PATH notice
    path_contains = any(os.path.abspath(target_dir).lower() == os.path.abspath(p).lower() for p in path_dirs)
    if not path_contains:
        if is_windows:
            print(f"{C_YELLOW}[install][info] Add '{target_dir}' to your PATH to use 'qws' directly.{C_RESET}")
        else:
            print(f"{C_YELLOW}[install][info] Ensure '{target_dir}' is in your PATH (e.g., export PATH=\"{target_dir}:$PATH\").{C_RESET}")

    if created_files:
        print("[install] Installed launcher(s):")
        for cf in created_files:
            print("  -", cf)
    else:
        print(f"{C_YELLOW}[install][warn] No launcher files were created.{C_RESET}")

    print("[install] Command installation complete.")


def install_app():
    install_dependencies()
    install_command()


def open_browser(url):
    try:
        if sys.platform == "win32":
            os.startfile(url)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as e:
        print(f"{C_YELLOW}Could not open browser: {e}{C_RESET}")


def live_reload_server(args):
    host = args.http_host or args.host
    http_port = args.http_port

    try:
        from livereload import Server  # type: ignore
    except Exception as e:  # ModuleNotFoundError or other import errors
        print(f"{C_YELLOW}livereload package not available ({e}){C_RESET}")
        print(f"{C_YELLOW}Install it via 'pip install livereload'{C_RESET}")
        return

    server = Server()
    server.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    server.watch("*")

    # Root directory is current working directory.
    print(f"Starting live reload server on http://{host}:{http_port}")

    try:
        server.serve(
            host=host,
            port=http_port,
            root=".",
            restart_delay=0.5,
            debug=True,
            live_css=True,
        )
    except KeyboardInterrupt:
        print(f"{C_YELLOW}Live reload server interrupted. Exiting...{C_RESET}")
    except OSError as oe:
        print(f"{C_RED}Port {http_port} unavailable or other OS error: {oe}{C_RESET}")
    except Exception as e:
        print(f"{C_RED}Unexpected error in live reload server: {e}{C_RESET}")
    finally:
        # livereload Server.serve() blocks; cleanup is implicit on exit.
        pass


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def start_http_server(args):
    if getattr(args, "disable_http", False):
        return None

    try:
        host = args.http_host or args.host
        http_port = args.http_port

        if getattr(args, RELOAD, False):
            print("Using live-reload HTTP server.")
            script_path = os.path.abspath(__file__)
            cmd = [
                sys.executable,
                script_path,
                __RUN_LIVERELOAD_SERVER,
                __HTTP_PORT, str(http_port),
                __HTTP_HOST, host,
            ]
        else:
            print("Using standard HTTP server.")
            cmd = [sys.executable, "-m", "http.server", str(http_port), "--bind", host]

        if getattr(args, "dry_run", False):
            print("DRY-RUN HTTP:", " ".join(cmd))
            return None

        return subprocess.Popen(cmd)
    except Exception as e:
        print(f"{C_RED}Fehler beim Starten des HTTP-Servers: {e}{C_RESET}")
        return None


def start_ssl_proxy(args):
    if getattr(args, "disable_proxy", False):
        return None

    try:
        proxy_host = args.proxy_host or args.host
        proxy_port = args.proxy_port

        thost = args.http_host or args.host
        tport = args.http_port

        system = sys.platform  # 'win32'
        if system == 'win32';
            cmd = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", "C:\\Program Files\\nodejs\\npx.ps1",
                "--yes", "local-ssl-proxy",
                "--source", str(proxy_port),
                "--target", str(tport),
                "--hostname", proxy_host,
            ]
        else:
            cmd = [
                "npx",
                "--yes", "local-ssl-proxy",
                "--source", str(proxy_port),
                "--target", str(tport),
                "--hostname", proxy_host,
            ]

        if getattr(args, "dry_run", False):
            print("DRY-RUN PROXY:", " ".join(cmd))
            return None

        return subprocess.Popen(cmd)

    except Exception as e:
        print(f"{C_RED}Fehler beim Starten des SSL-Proxys: {e}{C_RESET}")
        return None


def open_website(args):
    open_flag = getattr(args, "open", False)
    if not open_flag:
        return
    time.sleep(10)
    proxy_disabled = getattr(args, "disable_proxy", False)
    if proxy_disabled:
        host = args.http_host or args.host
        port = args.http_port
        protocol = "http"
    else:
        host = args.proxy_host or args.host
        port = args.proxy_port
        protocol = "https"
    url = f"{protocol}://{host}:{port}/"
    print(f"Öffne Webseite: {url}")
    open_browser(url)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="qws",
        description="HTTP-Server & HTTPS-Proxy (standardmäßig beide aktiv).",
    )

    # Disable Flags
    parser.add_argument("--disable-http", "-H", action="store_true", help="HTTP-Server deaktivieren.")
    parser.add_argument("--disable-proxy", "-P", action="store_true", help="HTTPS-Proxy deaktivieren.")

    # Ports
    parser.add_argument(__HTTP_PORT, "-t", type=int, default=DEFAULT_HTTP_PORT, help=f"Port HTTP (Default {DEFAULT_HTTP_PORT}).")
    parser.add_argument("--proxy-port", "-p", type=int, default=DEFAULT_PROXY_PORT, help=f"Port Proxy (Default {DEFAULT_PROXY_PORT}).")

    # Random Ports
    parser.add_argument(__RANDOM_HTTP_PORT, "-r", action="store_true", help="Zufälligen freien Port für HTTP verwenden.")
    parser.add_argument(__RANDOM_PROXY_PORT, "-s", action="store_true", help="Zufälligen freien Port für Proxy verwenden.")

    # Hosts
    parser.add_argument("--host", "-b", default=DEFAULT_HOST, help=f"Gemeinsame Bind-Adresse (Default {DEFAULT_HOST}).")
    parser.add_argument(__HTTP_HOST, "-x", default=None, help="Spezifische Bind-Adresse HTTP.")
    parser.add_argument("--proxy-host", "-y", default=None, help="Spezifische Bind-Adresse Proxy.")

    # Dev / Utility
    parser.add_argument(__RELOAD, "-R", action="store_true", help="Reload-Modus.")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Nur anzeigen, nichts starten.")

    # Second Process
    parser.add_argument(__RUN_LIVERELOAD_SERVER, action="store_true", help=f"Dont use this directly! Use {__RELOAD} instead!")

    # Open browser after startup
    parser.add_argument("--open", "-o", action="store_true", help="Öffne die Webseite im Standardbrowser.")

    # Install Arguments
    parser.add_argument("--install", action="store_true", help="Installiere Abhängigkeiten und richte den Befehl 'qws' ein.")

    args = parser.parse_args()

    install_app_flag = getattr(args, "install", False)
    if install_app_flag:
        install_app()
        return 0

    # set ports if random ports are requested
    if getattr(args, RANDOM_HTTP_PORT, False):
        args.http_port = get_free_port()
    if getattr(args, RANDOM_PROXY_PORT, False):
        args.proxy_port = get_free_port()
    
    run_livereload_server = getattr(args, RUN_LIVERELOAD_SERVER, False)
    if run_livereload_server:
        live_reload_server(args)
        return 0

    # start services
    http_proc = start_http_server(args)
    proxy_proc = start_ssl_proxy(args)
    open_website(args)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"{C_YELLOW}Beende Prozesse...{C_RESET}")
            if http_proc:
                http_proc.terminate()
            if proxy_proc:
                proxy_proc.terminate()
            break

    if http_proc:
        http_proc.wait()
    if proxy_proc:
        proxy_proc.wait()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
