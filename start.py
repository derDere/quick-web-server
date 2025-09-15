import argparse
import subprocess
import sys
import socket
import time
import os


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
    # ToDos: os.system calls to install needed packages
    pass


def open_browser(url):
    try:
        if sys.platform == "win32":
            os.startfile(url)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as e:
        print(f"Could not open browser: {e}")


def live_reload_server(args):
    host = args.http_host or args.host
    http_port = args.http_port

    try:
        from livereload import Server  # type: ignore
    except Exception as e:  # ModuleNotFoundError or other import errors
        print("livereload package not available (", e, ")")
        print("Install it via 'pip install livereload'")
        return

    server = Server()
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
        print("Live reload server interrupted. Exiting...")
    except OSError as oe:
        print(f"Port {http_port} unavailable or other OS error: {oe}")
    except Exception as e:
        print("Unexpected error in live reload server:", e)
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
        print("Fehler beim Starten des HTTP-Servers:", e)
        return None


def start_ssl_proxy(args):
    if getattr(args, "disable_proxy", False):
        return None

    try:
        proxy_host = args.proxy_host or args.host
        proxy_port = args.proxy_port

        thost = args.http_host or args.host
        tport = args.http_port

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

        if getattr(args, "dry_run", False):
            print("DRY-RUN PROXY:", " ".join(cmd))
            return None

        return subprocess.Popen(cmd)

    except Exception as e:
        print("Fehler beim Starten des SSL-Proxys:", e)
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

    args = parser.parse_args()

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
            print("Beende Prozesse...")
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
