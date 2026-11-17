#!/usr/bin/env python3
"""End-to-end test of ghillie-rig-agent.py against a throwaway regtest camod.

    python3 contrib/camo/tools/test_rig_agent.py [build/release/bin]

Checks: pairing code contents, certificate pinning, wrong secret refused + lockout, status, start (thread cap,
payout fixed by the computer), stop. Exits non-zero on any failure.
"""
import base64, hashlib, json, os, shutil, socket, ssl, subprocess, sys, tempfile, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "../../../build/release/bin"))
AGENT = os.path.join(HERE, "ghillie-rig-agent.py")
BURN = "Cdqd3jC3ocP6H1BX4G2Uis8qVYj6ddShVfqGaxkvCE64YEgGgZTt5RjLZ4toVBJ3pae1HJR1AcWQxBmSRi55ePTv4dxHzs8"
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    fails += not ok


def call(code, path, body=None, secret=None, fp=None):
    """Talk to the helper like the phone does: TLS, accept only the pinned certificate fingerprint."""
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE  # pinning below replaces CA checks
    with socket.create_connection((code["host"], code["port"]), timeout=15) as raw:
        with ctx.wrap_socket(raw) as s:
            got = hashlib.sha256(s.getpeercert(binary_form=True)).hexdigest()
            if got != (fp or code["fp"]):
                return "pin-mismatch", None
            data = json.dumps(body).encode() if body is not None else b""
            req = (f"{'POST' if body is not None else 'GET'} {path} HTTP/1.1\r\nHost: rig\r\nConnection: close\r\n"
                   f"Authorization: Bearer {secret or code['secret']}\r\nContent-Type: application/json\r\n"
                   f"Content-Length: {len(data)}\r\n\r\n").encode() + data
            s.sendall(req)
            resp = b""
            while chunk := s.recv(65536):
                resp += chunk
    head, _, payload = resp.partition(b"\r\n\r\n")
    return int(head.split()[1]), json.loads(payload or b"{}")


def main():
    tmp = tempfile.mkdtemp(prefix="rigtest-")
    env = dict(os.environ, CAMO_RIG_HOME=os.path.join(tmp, "rig"))
    camod = subprocess.Popen([os.path.join(BIN, "camod"), "--regtest", "--offline", "--fixed-difficulty", "1",
                              "--data-dir", os.path.join(tmp, "chain"), "--non-interactive", "--no-zmq",
                              "--log-file", os.path.join(tmp, "camod.log")], stdout=subprocess.DEVNULL)
    agent = None
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:19741/get_info", timeout=2)
                break
            except OSError:
                time.sleep(1)
        out = subprocess.run([sys.executable, AGENT, "setup", "--address", BURN, "--max-threads", "2", "--name", "test-rig"],
                             env=env, capture_output=True, text=True)
        check("setup", out.returncode == 0, out.stdout.strip().splitlines()[0] if out.stdout else out.stderr)
        bad = subprocess.run([sys.executable, AGENT, "setup", "--address", "4" + BURN[1:]], env=env, capture_output=True, text=True)
        check("setup refuses a non-CAMO address", bad.returncode != 0)
        check("key and secret are private", all(os.stat(os.path.join(env["CAMO_RIG_HOME"], f)).st_mode & 0o077 == 0
                                                for f in ("key.pem", "secret", "config.json")))
        pair = subprocess.run([sys.executable, AGENT, "pair"], env=env, capture_output=True, text=True).stdout
        line = next(l for l in pair.splitlines() if l.startswith("ghillie-rig:"))
        b64 = line[len("ghillie-rig:"):]
        code = json.loads(base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4)))
        check("pairing code has host, port, fingerprint, 256-bit secret",
              code["port"] == 19760 and len(code["fp"]) == 64 and len(base64.urlsafe_b64decode(code["secret"] + "=")) == 32)
        code["host"] = "127.0.0.1"
        agent = subprocess.Popen([sys.executable, AGENT, "run"], env=env, stdout=subprocess.PIPE, text=True)
        for _ in range(30):
            try:
                socket.create_connection(("127.0.0.1", 19760), timeout=1).close()
                break
            except OSError:
                time.sleep(0.3)

        st, body = call(code, "/v1/status")
        check("status with the right secret", st == 200 and body["camod"] and body["mining"] is False, str(body))
        check("phone sees only a shortened payout", body.get("payout") == BURN[:8] + "…" + BURN[-4:])
        check("wrong certificate fingerprint is refused by the phone", call(code, "/v1/status", fp="0" * 64)[0] == "pin-mismatch")
        st, _ = call(code, "/v1/start", {"threads": 1}, secret="A" * 43)
        check("wrong secret refused", st == 401)
        time.sleep(1)
        st, body = call(code, "/v1/status")
        check("not mining after a refused start", body["mining"] is False)

        st, body = call(code, "/v1/start", {"threads": 64, "miner_address": "attacker"})
        check("start capped at max threads", st == 200 and body["mining"] and body["threads"] == 2, str(body))
        time.sleep(4)
        info = json.load(urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:19741/mining_status", data=b"{}")))
        check("payout is the computer's address, not the phone's", info.get("address") == BURN, info.get("address", "")[:12])
        for _ in range(90):  # RandomX needs a little while to initialise
            st, body = call(code, "/v1/status")
            if body.get("height", 0) > 2:
                break
            time.sleep(2)
        check("blocks are being mined", body.get("height", 0) > 2, f"height {body.get('height')}, {body.get('hashrate')} H/s")
        st, body = call(code, "/v1/start", {"threads": 1})
        check("change threads while mining", st == 200 and body["mining"] and body["threads"] == 1, str(body))
        st, body = call(code, "/v1/stop", {})
        check("stop", st == 200 and body["mining"] is False, str(body))

        for _ in range(5):
            call(code, "/v1/status", secret="B" * 43)
        st, _ = call(code, "/v1/status")
        check("lockout after 5 wrong secrets (even the right one waits)", st == 401)
    finally:
        if agent:
            agent.terminate()
        camod.terminate()
        camod.wait(30)
        shutil.rmtree(tmp, ignore_errors=True) if not fails else print('kept', tmp)
    print("ALL PASS" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
