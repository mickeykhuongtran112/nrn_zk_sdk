"""Launch with: python -m tests.demo_app --port COM13 --baud 115200 --ports 1."""

import argparse
import time
import webbrowser
from pathlib import Path
from .records import EventLog
from .server import Runtime, DemoServer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", default="COM13", help="Default device port; Connect is always manual")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--ports", type=int, choices=(1, 4, 8, 16), default=1)
    p.add_argument("--address", type=lambda s: int(s, 0), default=0)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--http-port", type=int, default=8765)
    p.add_argument("--log-dir", type=Path, default=Path("local_data/demo_logs"))
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    log = EventLog(
        args.log_dir / (time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1000000}.jsonl")
    )
    runtime = Runtime(
        log, {k: getattr(args, k) for k in ("port", "baud", "ports", "address", "timeout")}
    )
    try:
        with DemoServer(runtime, args.http_port) as server:
            url = f"http://127.0.0.1:{server.server_port}"
            print("ZK SDK Test Console:", url, flush=True)
            print("No COM port is opened until Connect. Close with Ctrl+C.", flush=True)
            print("JSONL log:", log.path.resolve(), flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping owned inventory and closing the reader...", flush=True)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
