#!/usr/bin/env python3
# Copyright (c) 2026, The CAMO Project
# BSD-3-Clause, see LICENSE.
"""Offline tests for camo_health.py's hashrate and timestamp checks (regtest runs at fixed difficulty, so these use
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

print('ALL PASS' if not failed else '%d FAILED' % failed)
sys.exit(1 if failed else 0)
