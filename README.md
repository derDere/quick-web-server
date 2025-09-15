# quick-web-server (qws)

Simple zero-config development helper: start a local static HTTP server and an HTTPS proxy (self-signed) in one command. Optional live-reload for rapid iteration.

## Features

- Static HTTP server (Python built-in `http.server`)
- Optional Livereload (auto-refresh browser) via `--reload`
- HTTPS forwarding proxy using `local-ssl-proxy` (Node.js + self-signed cert)
- Automatic random free ports (`--random-http-port`, `--random-proxy-port`)
- One-shot installer creates a `qws` command launcher
- Cross-platform (Windows, macOS, Linux) best-effort
- Automatically opens the browser with `--open`

## Requirements

Mandatory:
- Python 3.8+ (tested on 3.x)

Optional (for HTTPS proxy):
- Node.js + npx (for `local-ssl-proxy`)

Optional (for live reload):
- Python package `livereload` (installed automatically during `--install`)

## Installation

Option A: Clone and install (recommended)
```bash
git clone <your-repo-url> quick-web-server
cd quick-web-server
python start.py --install
```

Option B: Download `start.py` and run directly (no global command created):
```bash
python start.py --help
```

After a successful `--install`, a `qws` launcher is placed in a user-writable directory. If that directory is not on your PATH you will get an info message telling you what to add.

### Windows Notes
- Creates `qws.cmd` and `qws.ps1` in first writable PATH directory or `%APPDATA%/Python/Scripts`.
- If PowerShell execution policy blocks the script, you can run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (evaluate security implications first).

### Linux / macOS Notes
- Falls back to `~/.local/bin` if no writable PATH directory is found.
- Ensure `~/.local/bin` is on PATH, e.g. add to shell profile:
	```sh
	export PATH="$HOME/.local/bin:$PATH"
	```

## Quick Start

Serve current directory with HTTP on 8080 and HTTPS proxy on 8443:
```bash
qws
```

Serve with auto-open browser:
```bash
qws --open
```

Random ports (helpful when avoiding conflicts):
```bash
qws --random-http-port --random-proxy-port --open
```

Live reload (auto-refresh on file changes):
```bash
qws --reload --open
```

Disable components:
```bash
qws --disable-http           # only HTTPS proxy (use case: forward existing service)
qws --disable-proxy          # only HTTP server
```

Dry run (just print what would start):
```bash
qws --dry-run
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--disable-http` | `-H` | Disable starting the HTTP server |
| `--disable-proxy` | `-P` | Disable starting the HTTPS proxy |
| `--http-port N` | `-t` | Set HTTP port (default 8080) |
| `--proxy-port N` | `-p` | Set HTTPS proxy port (default 8443) |
| `--random-http-port` | `-r` | Use a random free HTTP port |
| `--random-proxy-port` | `-s` | Use a random free proxy port |
| `--host ADDR` | `-b` | Bind address for both services (default 127.0.0.1) |
| `--http-host ADDR` | `-x` | Specific HTTP bind address (overrides `--host` for HTTP) |
| `--proxy-host ADDR` | `-y` | Specific proxy bind address (overrides `--host` for proxy) |
| `--reload` | `-R` | Enable livereload server instead of plain HTTP server |
| `--dry-run` | `-d` | Print commands only |
| `--open` | `-o` | Open the site in your default browser after startup |
| `--install` | (none) | Install dependencies and create the `qws` command |

Hidden internal flag: `--run-livereload-server` (used internally when `--reload` spawns a second process).

## How It Works

1. HTTP server: Uses Python's builtin `http.server` (or `livereload.Server` when `--reload`).
2. HTTPS proxy: Uses `npx local-ssl-proxy` to create a local self-signed HTTPS endpoint that forwards to the HTTP port.
3. Live Reload: Watches all files in the working directory (`*`). Refresh triggers on changes.

## Browser Opening Delay

The script waits ~10 seconds (`time.sleep(10)`) before auto-opening the browser to give the proxy time to finish certificate setup. You can adjust this in `open_website()` if needed.

## Troubleshooting

Problem: `qws` not found after install
- Ensure the installation directory is on PATH (message printed during install)
- On Linux/macOS: `echo $PATH` and confirm `~/.local/bin`

Problem: HTTPS not working / certificate warning
- Self-signed cert is expected to be untrusted. Proceed manually or add exception.

Problem: `local-ssl-proxy` command slow first time
- The installer warms the npx cache, but first use can still take a moment.

Problem: Live reload not refreshing
- Ensure `livereload` was installed: `pip show livereload`
- Restart with `--reload`

Problem: Permission denied when creating launcher
- Re-run with elevated privileges OR add the fallback directory to PATH manually.

## Uninstall

Delete the created launcher files (`qws`, `qws.cmd`, `qws.ps1`) from the install directory. No other persistent state is stored.

## Roadmap / Ideas

- Optional directory argument to serve a different root
- Colored logging
- Config file (.qws.json)
- Built-in simple templated index

## Contributing

Issues and PRs welcome. Keep changes small and focused.

## License

See `LICENSE`.

