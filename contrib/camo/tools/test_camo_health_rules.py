#!/usr/bin/env python3
# Copyright (c) 2026, The CAMO Project
# BSD-3-Clause, see LICENSE.
"""Offline tests for camo_health.py's hashrate, timestamp, double-spend, block-burst and status-feed checks (regtest runs at fixed difficulty, so these use
synthetic block headers). Run: python3 contrib/camo/tools/test_camo_health_rules.py"""
import importlib.util
import os
import sys

spec = importlib.util.spec_from_file_location('camo_health', os.path.join(os.path.dirname(__file__), 'camo_health.py'))
ch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ch)

NOW = 1797400000
failed = 0


def headers(diffs, start=NOW - 7200, step=60):
    return [{'difficulty': d, 'timestamp': start + i * step} for i, d in enumerate(diffs)]


def expect(name, got, want_level, want_text=None):
    global failed
    ok = (got is None and want_level is None) or (got is not None and got[0] == want_level and
                                                    (want_text is None or want_text in got[1]))
    print('%s: %s%s' % ('PASS' if ok else 'FAIL', name, '' if ok else ' (got %r)' % (got,)))
    failed += not ok


steady = headers([100000 + (i % 7) * 1000 for i in range(200)])
expect('steady difficulty is OK', ch.hashrate_finding(steady, 3), None)
expect('x4 surge within 120 blocks is WARN', ch.hashrate_finding(headers([100000] * 100 + [400000] * 100), 3),
       ch.WARN, 'surge')
expect('/4 drop within 120 blocks is WARN', ch.hashrate_finding(headers([400000] * 100 + [100000] * 100), 3),
       ch.WARN, 'drop')
expect('x2 change is OK at factor 3', ch.hashrate_finding(headers([100000] * 100 + [200000] * 100), 3), None)
expect('surge older than the window is OK', ch.hashrate_finding(headers([100000] * 30 + [400000] * 170), 3), None)
expect('factor 0 turns it off', ch.hashrate_finding(headers([1] * 100 + [400000] * 100), 0), None)
expect('fixed-difficulty regtest is OK', ch.hashrate_finding(headers([1] * 200), 3), None)

normal = headers([1] * 60, start=NOW - 3600)
expect('timestamps up to now are OK', ch.timestamp_finding(normal, NOW, 10), None)
future = normal[:-3] + [{'difficulty': 1, 'timestamp': NOW + 3600 + i} for i in range(3)]
expect('blocks dated 1 h ahead are WARN', ch.timestamp_finding(future, NOW, 10), ch.WARN, '3 of the last 30')
slight = normal[:-1] + [{'difficulty': 1, 'timestamp': NOW + 300}]
expect('5 min ahead is OK at 10 min', ch.timestamp_finding(slight, NOW, 10), None)

# Double-spend watch (key images are what a spend consumes; a rival tx spending the same one = double-spend).
def idx(blocks):
    return {h: {'hash': 'b%d' % h, 'txs': txs} for h, txs in blocks.items()}


old = idx({100: {'t_pay': ['ki_A']}, 101: {'t_other': ['ki_B']}, 102: {}})


def levels(found):
    return sorted((lvl, key.split(':')[0]) for lvl, key, _ in found)


got = ch.double_spend_findings(old, idx({100: {'t_steal': ['ki_A']}, 101: {}, 102: {}}), 100, {'t_other'})
expect('rival spend of the same key image is CRIT', levels(got)[-1] if got else None, ch.CRIT, 'doublespend')
global_ds = [m for lvl, k, m in got if lvl == ch.CRIT]
expect('the CRIT names the losing and winning tx', (ch.CRIT, global_ds[0]) if global_ds else None, ch.CRIT, 't_pay')
expect('a tx back in the mempool is not an alarm', next(((l, m) for l, k, m in got if 't_other' in m), None), ch.OK,
       'back in the mempool')
got = ch.double_spend_findings(old, idx({100: {}, 101: {}, 102: {}}), 100, set())
expect('a vanished tx not in the mempool is WARN', (got[0][0], got[0][2]) if got else None, ch.WARN, 'not in the mempool')
got = ch.double_spend_findings(old, idx({100: {'t_pay': ['ki_A']}, 101: {'t_other': ['ki_B']}, 102: {}}), 100, set())
expect('a reorg that keeps every tx is quiet', got or None, None)
got = ch.double_spend_findings(old, idx({100: {'t_pay': ['ki_A']}, 101: {}, 102: {'t_other': ['ki_B']}}), 101, set())
expect('a tx re-mined in a later block is quiet', got or None, None)
got = ch.double_spend_findings(old, idx({100: {'t_steal': ['ki_A']}, 101: {'t_other': ['ki_B']}}), 101, set())
expect('blocks before the reorg are not compared', got or None, None)

# Block bursts (selfish mining): arrivals between runs, from the remembered {'t', 'height'}.
prev = {'t': NOW - 120, 'height': 1000}
expect('normal 2 blocks in 2 minutes is OK', ch.burst_finding(prev, NOW, 1002, 6), None)
expect('lucky 6 blocks in 2 minutes is OK', ch.burst_finding(prev, NOW, 1006, 6), None)
expect('12 blocks in 2 minutes is WARN', ch.burst_finding(prev, NOW, 1012, 6), ch.WARN, 'selfish mining')
expect('message gives counts and time', ch.burst_finding(prev, NOW, 1012, 6), ch.WARN, '12 blocks arrived in 2m00s')
expect('first run (no memory) is OK', ch.burst_finding(None, NOW, 1012, 6), None)
expect('0 turns it off', ch.burst_finding(prev, NOW, 1050, 0), None)
expect('60 blocks in an hour is OK', ch.burst_finding({'t': NOW - 3600, 'height': 1000}, NOW, 1060, 6), None)
expect('100 blocks in an hour is WARN', ch.burst_finding({'t': NOW - 3600, 'height': 1000}, NOW, 1100, 6), ch.WARN)
expect('catching up after a long gap is OK', ch.burst_finding({'t': NOW - 86400, 'height': 1000}, NOW, 3000, 6),
       None)
expect('a reorg to a shorter tip is OK', ch.burst_finding(prev, NOW, 995, 6), None)

# Public status feed: OK / CAUTION / HOLD, sticky.
def feed(findings, st=None, t=NOW, hours=2.0):
    return ch.feed_status(findings, st, t, hours)
DS = (ch.CRIT, 'doublespend:abcd', 'POSSIBLE DOUBLE-SPEND: tx a ... replaced by tx b')
s0 = feed([])
expect('quiet network is OK', (0, s0[0]) if s0[0] == 'OK' and not s0[1] else None, 0)
s1 = feed([DS])
expect('double-spend is HOLD', (0, s1[0]) if s1[0] == 'HOLD' else None, 0)
expect('HOLD says why', (0, s1[1][0]) if s1[1] else None, 0, 'DOUBLE-SPEND')
s2 = feed([], s1[3], NOW + 120)
expect('HOLD stays on the next quiet run', (0, s2[0]) if s2[0] == 'HOLD' else None, 0)
s3 = feed([], s2[3], NOW + 2 * 3600 + 1)
expect('HOLD clears after 2 hours', (0, s3[0]) if s3[0] == 'OK' else None, 0)
s4 = feed([(ch.CRIT, 'down:seed1', 'seed1: not answering')])
expect('a dead node is not HOLD', (0, s4[0]) if s4[0] == 'OK' else None, 0)
s5 = feed([(ch.CRIT, 'stall', 'no new block for 40m')])
expect('a stall is not HOLD', (0, s5[0]) if s5[0] == 'OK' else None, 0)
s6 = feed([(ch.WARN, 'burst', 'block burst: 12 blocks')])
expect('a block burst is CAUTION', (0, s6[0]) if s6[0] == 'CAUTION' else None, 0)
s7 = feed([(ch.WARN, 'reorg:500', 'reorganization: 4 blocks')], s1[3], NOW + 60)
expect('HOLD outranks a later CAUTION', (0, s7[0]) if s7[0] == 'HOLD' else None, 0)
s8 = feed([(ch.CRIT, 'reorg:500', 'reorganization: 12 blocks')])
expect('a deep (CRIT) reorg is HOLD', (0, s8[0]) if s8[0] == 'HOLD' else None, 0)
s9 = feed([], s6[3], NOW + 31 * 60)
expect('CAUTION clears after 30 minutes', (0, s9[0]) if s9[0] == 'OK' else None, 0)

print('ALL PASS' if not failed else '%d FAILED' % failed)
sys.exit(1 if failed else 0)
