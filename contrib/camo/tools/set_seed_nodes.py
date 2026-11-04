#!/usr/bin/env python3
"""Write CAMO's built-in seed nodes into the node source and the website in one step.

Usage:
  python3 contrib/camo/tools/set_seed_nodes.py --stagenet 203.0.113.10 198.51.100.7
  python3 contrib/camo/tools/set_seed_nodes.py --mainnet 203.0.113.10 198.51.100.7 192.0.2.44
  python3 contrib/camo/tools/set_seed_nodes.py --stagenet 203.0.113.10 --mainnet 198.51.100.7 --dry-run

Each address is an IPv4 address, optionally with :port (default: 39740 stagenet, 29740 testnet, 19740 mainnet).
Re-running replaces the previous list for that network (it does not append).

What it changes:
  src/p2p/net_node.inl       get_ip_seed_nodes(): the addresses a fresh node contacts first
  website/stagenet.html      the --add-priority-node example (stagenet only; first two addresses)
Then rebuild camod, run the tests, commit, and copy website/ to the public camo-website repo.
"""
import argparse
import ipaddress
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
NET_NODE = ROOT / "src/p2p/net_node.inl"
STAGENET_PAGE = ROOT / "website/stagenet.html"
DEFAULT_PORT = {"mainnet": 19740, "testnet": 29740, "stagenet": 39740}
# which branch of get_ip_seed_nodes() holds each network (mainnet is the final else)
BRANCH = {"testnet": "cryptonote::TESTNET", "stagenet": "cryptonote::STAGENET", "mainnet": None}


def parse_addr(text, net):
    host, _, port = text.partition(":")
    try:
        ip = ipaddress.IPv4Address(host)
    except ValueError:
        sys.exit(f"not an IPv4 address: {text!r}")
    if not ip.is_global:
        sys.exit(f"{ip} is private/reserved; seed nodes need public addresses")
    port = int(port) if port else DEFAULT_PORT[net]
    if not 1 <= port <= 65535:
        sys.exit(f"bad port in {text!r}")
    return f"{ip}:{port}"


def function_body(src):
    start = src.index("::get_ip_seed_nodes() const")
    open_brace = src.index("{", start)
    depth, i = 0, open_brace
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return open_brace, i
        i += 1


def set_branch(src, net, addrs):
    a, b = function_body(src)
    body = src[a:b]
    if BRANCH[net]:
        m = re.search(r"(if \(m_nettype == %s\)\s*\{)(.*?)(\n    \})" % re.escape(BRANCH[net]), body, re.S)
    else:  # mainnet: the final "else { ... }" before "return full_addrs;"
        m = re.search(r"(\n    else\s*\{)((?:(?!\n    else).)*?)(\n    \}\s*\n    return full_addrs;)", body, re.S)
    if not m:
        sys.exit(f"could not find the {net} branch in get_ip_seed_nodes()")
    inner = "".join(f'\n      full_addrs.insert("{x}");' for x in addrs)
    body = body[:m.start(2)] + inner + body[m.end(2):]
    return src[:a] + body + src[b:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for net in DEFAULT_PORT:
        ap.add_argument(f"--{net}", nargs="+", default=None, metavar="IP[:PORT]")
    ap.add_argument("--dry-run", action="store_true", help="show the changes without writing")
    args = ap.parse_args()
    lists = {net: [parse_addr(x, net) for x in getattr(args, net)] for net in DEFAULT_PORT if getattr(args, net)}
    if not lists:
        ap.error("give at least one of --mainnet/--testnet/--stagenet")

    src = NET_NODE.read_text()
    new = src
    for net, addrs in lists.items():
        if len(set(addrs)) != len(addrs):
            sys.exit(f"duplicate address in --{net}")
        new = set_branch(new, net, addrs)
        print(f"{net}: " + ", ".join(addrs))

    page = STAGENET_PAGE.read_text()
    new_page = page
    if "stagenet" in lists:
        # the page's example command: ./camod --stagenet \ --add-priority-node A \ --add-priority-node B
        flags = "".join(f" \\\n  --add-priority-node {addr}" for addr in lists["stagenet"][:2])
        new_page, n = re.subn(r"(<pre><code>\./camod --stagenet)( \\\n  --add-priority-node .*?)(</code></pre>)",
                              lambda m: m.group(1) + flags + m.group(3), page, count=1, flags=re.S)
        if n != 1:
            sys.exit("could not find the camod --stagenet example in website/stagenet.html")

    if args.dry_run:
        import difflib
        for path, old, cur in ((NET_NODE, src, new), (STAGENET_PAGE, page, new_page)):
            sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), cur.splitlines(True),
                                                       str(path.relative_to(ROOT)), str(path.relative_to(ROOT))))
        return
    NET_NODE.write_text(new)
    if new_page != page:
        STAGENET_PAGE.write_text(new_page)
    print("updated", NET_NODE.relative_to(ROOT), "and" if new_page != page else "",
          STAGENET_PAGE.relative_to(ROOT) if new_page != page else "")
    print("next: rebuild camod, run contrib/camo/regtest-demo.sh, commit, sync website/ to camo-website")


if __name__ == "__main__":
    main()
