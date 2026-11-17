#!/usr/bin/env python3
# Copyright (c) 2026, The CAMO Project. BSD-3-Clause, see LICENSE.
"""Ghillie rig helper: lets a paired phone start, stop and watch mining on THIS computer.

    python3 ghillie-rig-agent.py setup --address <your CAMO address> [--stagenet] [--max-threads N] [--name "iMac"]
    python3 ghillie-rig-agent.py pair      # prints the pairing code to type/scan into Ghillie > Rigs > Pair
    python3 ghillie-rig-agent.py run       # keep running while you want phone control (next to camod)

Security model
  * The phone talks to this helper directly on your local network, over TLS with a self-signed certificate whose
    SHA-256 fingerprint travels in the pairing code: the phone accepts no other certificate.
  * Every request carries a 256-bit secret from the pairing code (compared in constant time). `setup --new-secret`
    or deleting ~/.camo-rig/secret unpairs every phone.
  * The phone can only: read status, start mining with 1..max-threads threads, stop mining. The payout address is
    fixed here at setup and never comes from the phone; no other camod or wallet call is reachable through this
    helper, and it never sees keys.
  * camod's RPC is reached on 127.0.0.1 only. Mining needs camod running on this computer (as for mining today).
"""
import argparse, base64, hashlib, hmac, json, os, socket, ssl, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = os.path.expanduser(os.environ.get("CAMO_RIG_HOME", "~/.camo-rig"))
CFG, CERT, KEY, SECRET = (os.path.join(HOME, n) for n in ("config.json", "cert.pem", "key.pem", "secret"))
PORTS = {"mainnet": (19741, 19760), "stagenet": (39741, 39760), "testnet": (29741, 29760)}  # camod RPC, helper
PREFIX = {"mainnet": "C", "stagenet": "Q", "testnet": ("K", "L")}


def die(msg):
    sys.exit("ghillie-rig-agent: " + msg)


def load_cfg():
    try:
        with open(CFG) as f:
            return json.load(f)
    except FileNotFoundError:
        die("not set up yet. Run: python3 ghillie-rig-agent.py setup --address <your CAMO address> [--stagenet]")


def write_private(path, data, mode="w"):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, mode) as f:
        f.write(data)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no packet is sent; picks the interface with the default route
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def cert_fingerprint():
    with open(CERT) as f:
        der = ssl.PEM_cert_to_DER_cert(f.read())
    return hashlib.sha256(der).hexdigest()


def cmd_setup(a):
    net = "stagenet" if a.stagenet else "testnet" if a.testnet else "mainnet"
    addr = a.address.strip()
    if not addr.startswith(PREFIX[net]) or not 95 <= len(addr) <= 106:
        die(f"that is not a CAMO {net} address (it should start with {PREFIX[net]}).")
    os.makedirs(HOME, mode=0o700, exist_ok=True)
    cpus = os.cpu_count() or 2
    cfg = {"network": net, "address": addr, "name": a.name or socket.gethostname().split(".")[0],
           "max_threads": max(1, min(a.max_threads or max(1, cpus * 3 // 4), cpus))}
    write_private(CFG, json.dumps(cfg, indent=2))
    if a.new_secret or not os.path.exists(SECRET):
        write_private(SECRET, base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="))
    if not (os.path.exists(CERT) and os.path.exists(KEY)):
        # Two steps that both OpenSSL and macOS's LibreSSL accept.
        for cmd in (["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", KEY],
                    ["openssl", "req", "-new", "-x509", "-key", KEY, "-out", CERT, "-days", "3650", "-subj", "/CN=ghillie-rig"]):
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                die("could not create the TLS certificate with openssl:\n" + r.stderr)
        os.chmod(KEY, 0o600)
    print(f"Set up for {net}: rewards always go to {addr[:8]}…{addr[-4:]}, at most {cfg['max_threads']} of {cpus} CPU threads.")
    print("Next: python3 ghillie-rig-agent.py pair")


def pairing_code(cfg):
    with open(SECRET) as f:
        secret = f.read().strip()
    blob = {"v": 1, "name": cfg["name"], "net": cfg["network"], "host": lan_ip(), "port": PORTS[cfg["network"]][1],
            "fp": cert_fingerprint(), "secret": secret}
    return "ghillie-rig:" + base64.urlsafe_b64encode(json.dumps(blob, separators=(",", ":")).encode()).decode().rstrip("=")


def cmd_pair(a):
    cfg = load_cfg()
    code = pairing_code(cfg)
    print("Pairing code (treat it like a password: anyone with it on your Wi-Fi can start or stop your mining):\n")
    print(code + "\n")
    try:
        subprocess.run(["qrencode", "-t", "ANSIUTF8", code], check=True)
        print("\nScan it in Ghillie: Rigs > Pair a computer > Scan.")
    except (OSError, subprocess.CalledProcessError):
        print("Copy it into Ghillie: Rigs > Pair a computer > Paste. (Install `qrencode` to show a QR code here.)")


def rpc(cfg, method, params=None):
    port = PORTS[cfg["network"]][0]
    req = urllib.request.Request(f"http://127.0.0.1:{port}/{method}", data=json.dumps(params or {}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def status(cfg):
    try:
        m = rpc(cfg, "mining_status")
        info = rpc(cfg, "get_info")
    except OSError:
        return {"camod": False, "name": cfg["name"], "network": cfg["network"]}
    return {"camod": True, "name": cfg["name"], "network": cfg["network"], "mining": bool(m.get("active")),
            "hashrate": int(m.get("speed") or 0), "threads": int(m.get("threads_count") or 0),
            "max_threads": cfg["max_threads"], "cpus": os.cpu_count() or 0, "height": int(info.get("height") or 0),
            "payout": cfg["address"][:8] + "…" + cfg["address"][-4:]}


class Handler(BaseHTTPRequestHandler):
    server_version = "ghillie-rig/1"
    timeout = 15  # seconds; a stalled client cannot hold a thread
    cfg = None
    secret = b""
    fails = {}
    lock = threading.Lock()

    def log_message(self, fmt, *args):  # quiet: one line per action
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        ip = self.client_address[0]
        with self.lock:
            n, until = self.fails.get(ip, (0, 0))
            if until > time.time():
                return False
        got = (self.headers.get("Authorization") or "").removeprefix("Bearer ").encode()
        ok = hmac.compare_digest(got, self.secret)
        with self.lock:
            if ok:
                self.fails.pop(ip, None)
            else:
                n += 1
                self.fails[ip] = (n, time.time() + (60 if n >= 5 else 0))  # 5 wrong secrets: 1 minute lockout
        return ok

    def _body(self):
        n = min(int(self.headers.get("Content-Length") or 0), 4096)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        if not self._authorized():
            return self._send(401, {"error": "not paired"})
        if self.path == "/v1/status":
            return self._send(200, status(self.cfg))
        self._send(404, {"error": "unknown"})

    def do_POST(self):
        if not self._authorized():
            return self._send(401, {"error": "not paired"})
        cfg = self.cfg
        try:
            if self.path == "/v1/start":
                want = self._body().get("threads")
                threads = int(want) if isinstance(want, int) else cfg["max_threads"]
                threads = max(1, min(threads, cfg["max_threads"]))
                if rpc(cfg, "mining_status").get("active"):  # camod refuses start while mining: change = stop + start
                    rpc(cfg, "stop_mining")
                r = rpc(cfg, "start_mining", {"miner_address": cfg["address"], "threads_count": threads,
                                              "do_background_mining": False, "ignore_battery": False})
                print(time.strftime("%H:%M:%S"), f"phone: start mining, {threads} threads ->", r.get("status"))
                return self._send(200, status(cfg) | {"result": r.get("status")})
            if self.path == "/v1/stop":
                r = rpc(cfg, "stop_mining")
                print(time.strftime("%H:%M:%S"), "phone: stop mining ->", r.get("status"))
                return self._send(200, status(cfg) | {"result": r.get("status")})
        except OSError:
            return self._send(503, {"error": "camod is not running on this computer"})
        self._send(404, {"error": "unknown"})


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # dropped/garbled connections: no tracebacks
        pass


def cmd_run(a):
    cfg = load_cfg()
    with open(SECRET) as f:
        Handler.secret = f.read().strip().encode()
    Handler.cfg = cfg
    port = PORTS[cfg["network"]][1]
    httpd = Server(("0.0.0.0", port), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(CERT, KEY)
    # Handshake in the request thread (lazily), so one slow client cannot block new connections.
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True, do_handshake_on_connect=False)
    print(f"Ghillie rig helper for {cfg['name']} ({cfg['network']}) on {lan_ip()}:{port}. Ctrl-C stops it.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    p = argparse.ArgumentParser(description="Control CAMO mining on this computer from Ghillie on your phone.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("--address", required=True, help="your CAMO address that receives the rewards")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--stagenet", action="store_true")
    g.add_argument("--testnet", action="store_true")
    s.add_argument("--max-threads", type=int, help="the most CPU threads a phone may start (default 3/4 of them)")
    s.add_argument("--name", help="what the phone calls this computer")
    s.add_argument("--new-secret", action="store_true", help="unpair every phone")
    sub.add_parser("pair")
    sub.add_parser("run")
    a = p.parse_args()
    {"setup": cmd_setup, "pair": cmd_pair, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
