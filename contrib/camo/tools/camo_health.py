#!/usr/bin/env python3
# Copyright (c) 2026, The CAMO Project
# BSD-3-Clause, see LICENSE.
"""CAMO network health check: are the seed nodes up, on the same chain, and producing blocks normally?

Seed nodes keep RPC on 127.0.0.1 (deploy-seed-node.sh), so remote nodes are queried over SSH; nothing new is exposed.

  # from your computer, the three stagenet seeds (SSH key access as root):
  python3 camo_health.py --stagenet ssh://root@203.0.113.10 ssh://root@203.0.113.11 ssh://root@203.0.113.12
  # on a server, its own node:
  python3 camo_health.py --stagenet http://127.0.0.1:39741
  # keep watching, alert only when something changes (message on stdin of the command):
  python3 camo_health.py --stagenet --watch 300 --alert-cmd 'curl -s -d @- https://ntfy.sh/<private-topic>' NODES...

A node can be named: seed1=ssh://root@203.0.113.10 . ssh://user@host:PORT queries that RPC port on the server.

Checks: every node answers, is synchronized and has peers; the genesis block is CAMO's for that network and block 1
pays the 640,000 CAMO allocation; all nodes agree on the block hash at the lowest common height and their tips are
close; block times (last 30 and last 720 blocks) and time since the last block; competing chains seen by the nodes,
and reorganizations since the previous run (block hashes are remembered in a small state file); sudden hashrate
changes (difficulty up or down by --hashrate-jump within the last 120 blocks: a large miner arriving or leaving, the
usual setup for a 51% attack); block bursts (far more blocks arriving between two runs than chance allows, e.g.
10 in 2 minutes: a selfish miner releasing hidden blocks, or a flood of new hashrate; --burst-blocks); and block timestamps in the future (difficulty manipulation). Which miner
found a block cannot be seen on CAMO (rewards go to one-time addresses), so miner share is watched through these signals.
Double-spend watch: the transactions (and the key images they spend) of the last blocks are remembered; after a reorg,
a transaction that vanished while another transaction spends the same key image is CRIT (the signature of a 51%
double-spend: which txid lost, which won, at what height); a vanished transaction that isn't back in the mempool is
WARN. Key images and txids are public chain data; nothing here identifies anyone.

Exit code: 0 OK, 1 WARN, 2 CRIT (Nagios-style), so it also works from cron or a monitoring system. Read-only: it
only calls get_info, get_block_header_by_height, get_block_headers_range, get_alternate_chains and, for the
double-spend watch, get_block, get_transactions and get_transaction_pool_hashes.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
import urllib.request

COIN = 10**12
ALLOCATION = 640_000 * COIN          # block 1 coinbase: founder + marketing + burn (camo_allocation.h)
TARGET = 60                          # seconds per block (DIFFICULTY_TARGET_V2)
NETS = {
    # name: (default RPC port, genesis hash, get_info nettype)
    'mainnet': (19741, '9b1db372e5494d8acaa221dc3d4c7fa180a78a9f3a2f7259ad854f9258265636', 'mainnet'),
    'testnet': (29741, 'a8cc2770fb80c8420c27f3e1fcc72ac0467ee196bf6037f281301e4cd1f825a6', 'testnet'),
    'stagenet': (39741, '3732cfe00673bca31bbc44a3e5d52b6f554f8bdbb6ccaaaa1e6d17dc0bc3e76d', 'stagenet'),
    # regtest: mainnet genesis, used by the self-test (contrib/camo/tools/test_camo_health.sh)
    'regtest': (19741, '9b1db372e5494d8acaa221dc3d4c7fa180a78a9f3a2f7259ad854f9258265636', 'fakechain'),
}
OK, WARN, CRIT = 0, 1, 2
LEVEL = {OK: 'OK', WARN: 'WARN', CRIT: 'CRIT'}


class Node:
    def __init__(self, spec, default_port, timeout):
        self.name, _, target = spec.rpartition('=') if '=' in spec.split('://')[0] else ('', '', spec)
        self.timeout = timeout
        if target.startswith('ssh://'):
            hostpart = target[len('ssh://'):]
            host, port = hostpart, default_port
            if hostpart.count(':') == 1:
                host, p = hostpart.split(':')
                port = int(p)
            self.ssh, self.base = host, 'http://127.0.0.1:%d' % port
            self.name = self.name or host.split('@')[-1]
        else:
            self.ssh, self.base = None, target.rstrip('/')
            self.name = self.name or target.split('://')[-1]

    def _post(self, path, payload):
        data = json.dumps(payload).encode()
        if self.ssh:
            cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % self.timeout, self.ssh,
                   'curl -s --max-time %d -H "Content-Type: application/json" --data-binary @- %s%s'
                   % (self.timeout, self.base, path)]
            out = subprocess.run(cmd, input=data, capture_output=True, timeout=self.timeout * 2 + 5)
            if out.returncode != 0 or not out.stdout:
                raise RuntimeError('ssh/curl failed: ' + (out.stderr.decode(errors='replace').strip()[-200:] or
                                                          'exit %d' % out.returncode))
            body = out.stdout
        else:
            req = urllib.request.Request(self.base + path, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read()
        return json.loads(body)

    def info(self):
        return self._post('/get_info', {})

    def rpc(self, method, **params):
        r = self._post('/json_rpc', {'jsonrpc': '2.0', 'id': '0', 'method': method, 'params': params})
        if 'error' in r:
            raise RuntimeError('%s: %s' % (method, r['error'].get('message', r['error'])))
        return r['result']


def fmt_secs(s):
    s = int(s)
    return '%dh%02dm' % (s // 3600, s % 3600 // 60) if s >= 3600 else '%dm%02ds' % (s // 60, s % 60) if s >= 60 else '%ds' % s


def hashrate_finding(headers, factor, window=120):
    """(level, message) if difficulty changed by more than `factor` within the last `window` blocks, else None."""
    if factor <= 1 or len(headers) < 2:
        return None
    seg = headers[-(window + 1):]
    old, new = int(seg[0]['difficulty']), int(seg[-1]['difficulty'])
    if old <= 0 or new <= 0:
        return None
    blocks = len(seg) - 1
    if new >= old * factor:
        return WARN, ('hashrate surge: difficulty x%.1f in the last %d blocks (%d -> %d): a large miner arrived; '
                      'watch for reorgs' % (new / old, blocks, old, new))
    if old >= new * factor:
        return WARN, ('hashrate drop: difficulty /%.1f in the last %d blocks (%d -> %d): a large miner left'
                      % (old / new, blocks, old, new))
    return None


def timestamp_finding(headers, now, ahead_minutes, window=30):
    """(level, message) if recent blocks are dated more than `ahead_minutes` after `now`, else None."""
    ahead = [h for h in headers[-window:] if h['timestamp'] > now + ahead_minutes * 60]
    if not ahead:
        return None
    worst = max(h['timestamp'] for h in ahead) - now
    return WARN, ('%d of the last %d blocks are dated in the future (up to %s ahead): possible timestamp '
                  'manipulation' % (len(ahead), min(window, len(headers)), fmt_secs(worst)))


INDEX_DEPTH = 60  # blocks whose transactions are remembered for the double-spend watch


def block_txs(node, height):
    """(block hash, {txid: [key images]}) for the block at `height`, coinbase excluded."""
    blk = node.rpc('get_block', height=height)
    txids = blk.get('tx_hashes') or []
    txs = {}
    if txids:
        r = node._post('/get_transactions', {'txs_hashes': txids, 'decode_as_json': True})
        for t in r.get('txs', []):
            vin = json.loads(t['as_json']).get('vin', [])
            txs[t['tx_hash']] = [i['key']['k_image'] for i in vin if 'key' in i]
    return blk['block_header']['hash'], txs


def double_spend_findings(old_index, new_index, changed_from, pool):
    """Findings for transactions that a reorg removed. old_index/new_index: {height: {'hash': h, 'txs': {txid:
    [key images]}}} before/after; changed_from: first height whose block was replaced; pool: txids in the mempool."""
    old_txs = {}
    for h, b in old_index.items():
        if h >= changed_from:
            for txid, kis in b['txs'].items():
                old_txs[txid] = (h, kis)
    new_txs, new_ki = set(), {}
    for h, b in new_index.items():
        if h >= changed_from:
            for txid, kis in b['txs'].items():
                new_txs.add(txid)
                for ki in kis:
                    new_ki[ki] = (txid, h)
    found = []
    for txid, (h, kis) in sorted(old_txs.items(), key=lambda x: x[1][0]):
        if txid in new_txs:
            continue
        rival = next((new_ki[ki] for ki in kis if ki in new_ki and new_ki[ki][0] != txid), None)
        if rival:
            found.append((CRIT, 'doublespend:' + txid[:16],
                          'POSSIBLE DOUBLE-SPEND: tx %s (was in block %d) was replaced by tx %s (block %d) spending '
                          'the same coins; tell exchanges to freeze deposits of that tx' % (txid, h, rival[0], rival[1])))
        elif txid in pool:
            found.append((OK, 'requeued:' + txid[:16], 'tx %s left block %d in a reorg and is back in the mempool'
                          % (txid, h)))
        else:
            found.append((WARN, 'vanished:' + txid[:16], 'tx %s left block %d in a reorg and is not in the mempool'
                          % (txid, h)))
    return found


def poisson_tail(k, lam):
    """P(X >= k) for X ~ Poisson(lam)."""
    if k <= 0:
        return 1.0
    term = total = math.exp(-lam)
    for i in range(1, k):
        term *= lam / i
        total += term
    return max(0.0, 1.0 - total)


def burst_finding(prev, now, height, min_blocks, odds=1e-4):
    """(level, message) if more blocks arrived since the previous run than chance allows, else None.
    prev: {'t': unix time, 'height': h} remembered by the previous run (arrival times, not miner timestamps,
    which a miner sets itself). A burst means a miner released blocks it had kept hidden (selfish mining) or a
    sudden flood of hashrate that difficulty has not caught up with yet."""
    if not prev or min_blocks <= 0:
        return None
    elapsed, new = now - prev['t'], height - prev['height']
    if elapsed <= 0 or elapsed > 3 * 3600 or new < min_blocks:
        return None
    lam = elapsed / TARGET
    p = poisson_tail(new, lam)
    if p >= odds:
        return None
    return WARN, ('block burst: %d blocks arrived in %s (about %.0f expected; chance by luck below 1 in %s): a miner '
                  'may have released hidden blocks (selfish mining) or a large miner just arrived; watch for reorgs '
                  'and hold large deposits a little longer' % (new, fmt_secs(elapsed), lam,
                                                              '{:,}'.format(int(round(1 / odds)))))


def check(args, nodes, state):
    """Run all checks once. Returns (level, findings, report_lines, new_state)."""
    port, genesis, nettype = NETS[args.net]
    findings = []                     # (level, key, message); key identifies the problem for change detection
    lines = []

    def add(level, key, msg):
        findings.append((level, key, msg))

    up = []
    for n in nodes:
        try:
            i = n.info()
            if i.get('status') != 'OK':
                raise RuntimeError('status ' + str(i.get('status')))
            up.append((n, i))
        except Exception as e:  # noqa: BLE001 (any failure to answer is the finding)
            add(CRIT, 'down:' + n.name, '%s: not answering (%s)' % (n.name, str(e)[:160]))
    if not up:
        add(CRIT, 'all-down', 'no node answered')
        return summarize(findings, lines, state)

    for n, i in up:
        peers = i.get('incoming_connections_count', 0) + i.get('outgoing_connections_count', 0)
        lines.append('%-18s height %-8d peers %-3d %s  %s' % (n.name, i['height'], peers, i['top_block_hash'][:16],
                                                            i.get('version', '?')))
        if i.get('nettype') != nettype:
            add(CRIT, 'net:' + n.name, '%s: is on %s, expected %s' % (n.name, i.get('nettype'), args.net))
        if i.get('offline'):
            add(WARN, 'offline:' + n.name, '%s: running with --offline' % n.name)
        elif peers < args.min_peers:
            add(WARN if peers else CRIT, 'peers:' + n.name, '%s: only %d peer(s)' % (n.name, peers))
        if i.get('busy_syncing') or not i.get('synchronized', True):
            add(WARN, 'sync:' + n.name, '%s: still syncing (target height %s)' % (n.name, i.get('target_height')))
    versions = sorted({i.get('version', '?') for _, i in up})
    if len(versions) > 1:
        add(WARN, 'versions', 'nodes run different versions: ' + ', '.join(versions))

    # Same chain? Compare genesis, block 1 and the block hash at the lowest common height.
    common = min(i['height'] for _, i in up) - 1
    hashes = {}
    for n, i in up:
        try:
            g = n.rpc('get_block_header_by_height', height=0)['block_header']['hash']
            if g != genesis:
                add(CRIT, 'genesis:' + n.name, '%s: genesis %s… is not CAMO %s genesis' % (n.name, g[:16], args.net))
            if i['height'] > 1:
                b1 = n.rpc('get_block_header_by_height', height=1)['block_header']
                if b1['reward'] != ALLOCATION:
                    add(CRIT, 'block1:' + n.name, '%s: block 1 pays %.6f CAMO, not the 640,000 allocation'
                        % (n.name, b1['reward'] / COIN))
            hashes[n.name] = n.rpc('get_block_header_by_height', height=common)['block_header']['hash']
        except Exception as e:  # noqa: BLE001
            add(CRIT, 'rpc:' + n.name, '%s: header query failed (%s)' % (n.name, str(e)[:160]))
    if len(set(hashes.values())) > 1:
        groups = {}
        for name, h in hashes.items():
            groups.setdefault(h, []).append(name)
        add(CRIT, 'split', 'CHAIN SPLIT at height %d: ' % common +
            '; '.join('%s… %s' % (h[:12], ','.join(v)) for h, v in groups.items()))
    tips = [i['height'] for _, i in up]
    if max(tips) - min(tips) > args.max_lag:
        add(WARN, 'lag', 'tips differ by %d blocks (%d..%d)' % (max(tips) - min(tips), min(tips), max(tips)))

    # Block times, from the node with the highest tip.
    best, bi = max(up, key=lambda x: x[1]['height'])
    top = bi['height'] - 1
    lo = max(1, top - 719)
    headers = []
    try:
        for start in range(lo, top + 1, 500):
            headers += best.rpc('get_block_headers_range', start_height=start,
                                end_height=min(start + 499, top))['headers']
    except Exception as e:  # noqa: BLE001
        add(WARN, 'headers', '%s: could not read recent headers (%s)' % (best.name, str(e)[:160]))
    if headers:
        ts = [h['timestamp'] for h in headers]
        age = time.time() - ts[-1]

        def avg(n):
            seg = ts[-(n + 1):]
            return (seg[-1] - seg[0]) / (len(seg) - 1) if len(seg) > 1 else None
        a30, a720 = avg(30), avg(720)
        lines.append('blocks: last %s ago; avg %s over last %d, %s over last %d; difficulty %s' % (
            fmt_secs(age), fmt_secs(a30) if a30 else '-', min(30, len(ts) - 1), fmt_secs(a720) if a720 else '-',
            len(ts) - 1, bi.get('difficulty')))
        if age > args.stall_crit * 60:
            add(CRIT, 'stall', 'no new block for %s (tip %d)' % (fmt_secs(age), top))
        elif age > args.stall_warn * 60:
            add(WARN, 'stall', 'no new block for %s (tip %d)' % (fmt_secs(age), top))
        if a30 and len(ts) > 30 and not (TARGET / 3 <= a30 <= TARGET * 3):
            add(WARN, 'blocktime', 'last 30 blocks averaged %s (target 60s); difficulty is still adjusting'
                % fmt_secs(a30))
        synced = not (bi.get('busy_syncing') or not bi.get('synchronized', True))
        burst = burst_finding(state.get('arrival'), time.time(), top, args.burst_blocks) if synced else None
        state = dict(state, arrival={'t': time.time(), 'height': top})
        for key, found in (('burst', burst), ('hashrate', hashrate_finding(headers, args.hashrate_jump)),
                           ('timestamps', timestamp_finding(headers, time.time(), args.future_minutes))):
            if found:
                add(found[0], key, found[1])

    # Competing chains the nodes know about.
    for n, i in up:
        try:
            alts = n.rpc('get_alternate_chains').get('chains', [])
        except Exception:  # noqa: BLE001 (older/restricted nodes: skip)
            continue
        recent = [c for c in alts if c['height'] > top - 1000]
        deepest = max((c['length'] for c in recent), default=0)
        if deepest >= args.reorg_crit:
            add(CRIT, 'alt:' + n.name, '%s: competing chain %d blocks long' % (n.name, deepest))
        elif deepest >= args.reorg_warn:
            add(WARN, 'alt:' + n.name, '%s: competing chain %d blocks long' % (n.name, deepest))

    # Reorganizations since the last run: a remembered block hash that changed.
    seen = {int(k): v for k, v in state.get('hashes', {}).items()}
    now = {h['height']: h['hash'] for h in headers[-200:]}
    changed = sorted(h for h in seen if h in now and now[h] != seen[h])
    if changed:
        depth = max(seen) - changed[0] + 1
        lvl = CRIT if depth >= args.reorg_crit else WARN if depth >= args.reorg_warn else OK
        msg = 'reorganization since last run: %d block(s) replaced from height %d' % (depth, changed[0])
        if lvl:
            add(lvl, 'reorg:%d' % changed[0], msg)
        else:
            lines.append(msg + ' (normal at this depth)')
    # Double-spend watch: remember recent blocks' transactions; after a reorg, compare old and new.
    old_index = {int(k): v for k, v in state.get('txindex', {}).items()}
    new_index = {}
    if headers and getattr(args, 'tx_watch', True):
        try:
            for h in sorted(now)[-INDEX_DEPTH:]:
                prev = old_index.get(h)
                if prev and prev['hash'] == now[h]:
                    new_index[h] = prev
                else:
                    bh, txs = block_txs(best, h)
                    new_index[h] = {'hash': bh, 'txs': txs}
            if changed and old_index:
                try:
                    pool = set(best._post('/get_transaction_pool_hashes', {}).get('tx_hashes') or [])
                except Exception:  # noqa: BLE001 (restricted node: treat as empty)
                    pool = set()
                for lvl, key, msg in double_spend_findings(old_index, new_index, changed[0], pool):
                    if lvl:
                        add(lvl, key, msg)
                    else:
                        lines.append(msg)
        except Exception as e:  # noqa: BLE001
            add(WARN, 'txwatch', '%s: double-spend watch could not read blocks (%s)' % (best.name, str(e)[:160]))
            new_index = old_index
        state = dict(state, txindex={str(k): v for k, v in new_index.items()})
    if now:
        state = dict(state, hashes={str(k): v for k, v in now.items()})
    return summarize(findings, lines, state)


def summarize(findings, lines, state):
    level = max((f[0] for f in findings), default=OK)
    return level, findings, lines, state


def load_state(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, path)


def alert(cmd, text):
    if not cmd:
        return
    try:
        subprocess.run(cmd, shell=True, input=(text + '\n').encode(), timeout=30)
    except Exception as e:  # noqa: BLE001
        print('alert command failed: %s' % e, file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('\n', 2)[2])
    g = p.add_mutually_exclusive_group()
    for net in ('testnet', 'stagenet', 'regtest'):
        g.add_argument('--' + net, dest='net', action='store_const', const=net)
    p.set_defaults(net='mainnet')
    p.add_argument('nodes', nargs='+', help='http://host:port, or ssh://user@host[:rpcport], optionally name=...')
    p.add_argument('--min-peers', type=int, default=2, help='warn below this many peers (default 2)')
    p.add_argument('--max-lag', type=int, default=3, help='warn if node tips differ by more blocks (default 3)')
    p.add_argument('--stall-warn', type=float, default=10, help='minutes without a block before WARN (default 10)')
    p.add_argument('--stall-crit', type=float, default=30, help='minutes without a block before CRIT (default 30)')
    p.add_argument('--reorg-warn', type=int, default=3, help='reorg/competing-chain depth for WARN (default 3)')
    p.add_argument('--reorg-crit', type=int, default=10, help='reorg/competing-chain depth for CRIT (default 10)')
    p.add_argument('--hashrate-jump', type=float, default=3,
                   help='warn if difficulty changes by this factor within 120 blocks (default 3; 0 = off)')
    p.add_argument('--future-minutes', type=float, default=10,
                   help='warn if recent blocks are dated this many minutes ahead of this clock (default 10)')
    p.add_argument('--burst-blocks', type=int,
                   help='warn when at least this many blocks arrive between runs far faster than chance allows '
                        '(default 6; 0 = off; off on regtest, which mines instantly)')
    p.add_argument('--no-tx-watch', dest='tx_watch', action='store_false',
                   help='skip the double-spend watch (it reads the last %d blocks\' transactions)' % INDEX_DEPTH)
    p.add_argument('--timeout', type=int, default=15, help='seconds per query (default 15)')
    p.add_argument('--state', help='state file (default ~/.camo-health/<network>.json)')
    p.add_argument('--json', action='store_true', help='print one JSON object instead of text')
    p.add_argument('--watch', type=int, metavar='SECONDS', help='repeat every SECONDS; alert only on changes')
    p.add_argument('--alert-cmd', help='shell command run with the alert text on stdin (WARN/CRIT and recovery)')
    args = p.parse_args()
    if args.burst_blocks is None:
        args.burst_blocks = 0 if args.net == 'regtest' else 6
    state_path = args.state or os.path.expanduser('~/.camo-health/%s.json' % args.net)
    nodes = [Node(s, NETS[args.net][0], args.timeout) for s in args.nodes]

    last_keys = None
    while True:
        state = load_state(state_path)
        level, findings, lines, state = check(args, nodes, state)
        save_state(state_path, state)
        stamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        text = '\n'.join(['CAMO %s health: %s  (%s)' % (args.net, LEVEL[level], stamp)] + lines +
                         ['%s: %s' % (LEVEL[lv], m) for lv, _, m in sorted(findings, key=lambda f: -f[0])])
        if args.json:
            print(json.dumps({'network': args.net, 'status': LEVEL[level], 'time': stamp, 'report': lines,
                              'findings': [{'level': LEVEL[lv], 'key': k, 'message': m} for lv, k, m in findings]}))
        else:
            print(text + '\n', flush=True)
        keys = {k for lv, k, _ in findings if lv >= WARN}
        if args.watch:
            if last_keys is not None and keys != last_keys:
                alert(args.alert_cmd, text if keys else 'CAMO %s health: back to OK (%s)' % (args.net, stamp))
            elif last_keys is None and keys:
                alert(args.alert_cmd, text)
            last_keys = keys
            time.sleep(args.watch)
        else:
            if keys:
                alert(args.alert_cmd, text)
            sys.exit(level)


if __name__ == '__main__':
    main()
