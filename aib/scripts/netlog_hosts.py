#!/usr/bin/env python3
# Copyright 2026 The AI Browser Authors. BSD-3-Clause (same as Chromium).
"""Summarize the hosts a NetLog shows the browser contacting.

Usage: netlog_hosts.py NETLOG.json --phase-start UNIX_MS [--sites a.com,b.org]

Every host contacted before --phase-start (the idle phase) is unsolicited.
After it, a host counts as unsolicited when its request has no top-frame
site (i.e. the browser made it, not a page) and it isn't one of --sites.
Exits 1 if anything unsolicited was found.
"""

import argparse
import json
import re
import sys
from urllib.parse import urlsplit


def load(path):
  with open(path, encoding='utf-8', errors='replace') as f:
    text = f.read().rstrip()
  # A netlog from a crash or kill lacks its closing brackets.
  for suffix in ('', ']}', '}]}', '"}]}'):
    try:
      return json.loads(text.rstrip(',') + suffix)
    except json.JSONDecodeError:
      continue
  sys.exit(f'could not parse {path}')


def host_of(url):
  try:
    return urlsplit(url).hostname
  except ValueError:
    return None


def top_frame_site(params):
  for key in ('network_anonymization_key', 'network_isolation_key'):
    v = params.get(key)
    if isinstance(v, str) and v:
      m = re.search(r'https?://[^ ,)]+', v)
      return m.group(0) if m else None
  return None


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('netlog')
  ap.add_argument('--phase-start', type=float, default=float('inf'),
                  help='unix ms when the user-driven phase began')
  ap.add_argument('--sites', default='')
  args = ap.parse_args()
  log = load(args.netlog)
  consts = log['constants']
  types = {v: k for k, v in consts['logEventTypes'].items()}
  offset = float(consts.get('timeTickOffset', 0))
  sites = {s.strip().lower() for s in args.sites.split(',') if s.strip()}

  hosts = {}  # host -> {'idle': n, 'browse': n, 'tops': set(), 'kinds': set()}
  for ev in log.get('events', []):
    name = types.get(ev.get('type'))
    params = ev.get('params') or {}
    host = None
    if name == 'URL_REQUEST_START_JOB':
      host = host_of(params.get('url', ''))
    elif name in ('HOST_RESOLVER_MANAGER_REQUEST', 'HOST_RESOLVER_DNS_TASK'):
      host = params.get('host')
      if host and '://' in host:
        host = host_of(host)
    elif name in ('QUIC_SESSION', 'HTTP2_SESSION_INITIALIZED'):
      host = params.get('host')
    if not host:
      continue
    host = host.lower().split(':')[0]
    if host in ('localhost', '127.0.0.1', '::1', '[::1]'):
      continue
    t = float(ev.get('time', 0)) + offset
    rec = hosts.setdefault(host, {'idle': 0, 'browse': 0, 'tops': set(),
                                  'kinds': set()})
    rec['idle' if t < args.phase_start else 'browse'] += 1
    rec['kinds'].add(name)
    tf = top_frame_site(params)
    if tf:
      rec['tops'].add(tf)

  def is_site(h):
    return any(h == s or h.endswith('.' + s) for s in sites)

  unsolicited = []
  print('| host | idle | browse | top-frame sites | verdict |')
  print('|---|---|---|---|---|')
  for h in sorted(hosts):
    r = hosts[h]
    if r['idle']:
      verdict = 'UNSOLICITED (idle)'
    elif is_site(h):
      verdict = 'visited site'
    elif r['tops']:
      verdict = 'page subresource'
    else:
      verdict = 'UNSOLICITED (browser-initiated)'
    if verdict.startswith('UNSOLICITED'):
      unsolicited.append(h)
    tops = ', '.join(sorted(r['tops']))[:80]
    print(f"| {h} | {r['idle']} | {r['browse']} | {tops} | {verdict} |")
  print()
  print(f'unsolicited hosts: {len(unsolicited)}')
  for h in unsolicited:
    print(f'  - {h}')
  return 1 if unsolicited else 0


if __name__ == '__main__':
  sys.exit(main())
