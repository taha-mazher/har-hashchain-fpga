"""Tamper-evident log for the cascade: a SHA-256 (or HMAC-SHA256) hash chain over every window's result.

Record per window (37 bytes = 296 bits, one SHA-256 block after padding):
  prev hash (32 B) | window number (4 B, big-endian, from 0 at each recording) | byte: class<<2 | sensor_en<<1 | used_s2
  plain : h_w = SHA256(record)
  keyed : h_w = HMAC-SHA256(KEY, record)   (2 compressions per window with precomputed ipad/opad states)
  fs    : h_w = HMAC-SHA256(k_w, record), k_w+1 = SHA256(k_w), k_0 = KEY   (forward-secure: the old key is
          overwritten, so a key read out of a stolen device cannot re-sign earlier windows; 5 compressions)
The chain restarts at each recording (h_-1 = 0), matching the reset the testbench gives the RTL.
Reads out/cascade_<name>.mem (from cascade_hw.py), writes out/chain_<name>.mem: one line per window,
class sensor_en used_s2 plain keyed fs hashes.
Usage: python chain.py [name ...]   (default: every out/cascade_*.mem; runs the tamper self-check, then writes the vectors)
"""
import hashlib
import hmac
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = bytes(range(32))  # test key only; a real device would hold a per-device secret


def record(prev, n, cls, en, used):
    return prev + n.to_bytes(4, 'big') + bytes([cls << 2 | en << 1 | used])


def link(prev, n, r, key=None):
    m = record(prev, n, *r)
    return hmac.new(key, m, 'sha256').digest() if key else hashlib.sha256(m).digest()


def build(recs, key=None, fs=False, h=bytes(32), n0=0):
    """Chain hashes for recs; h, n0 continue a chain from an earlier head (key is then that window's key)."""
    out = []
    for n, r in enumerate(recs, n0):
        h = link(h, n, r, key)
        out.append(h)
        if fs:
            key = hashlib.sha256(key).digest()
    return out


def verify(recs, hashes, key=None, anchor=None, fs=False):
    """Index of the first window whose stored hash does not match, len(recs) if the log is intact.
    anchor = the latest hash as published elsewhere; it catches a log rebuilt from scratch."""
    for n, h in enumerate(build(recs, key, fs)):
        if n >= len(hashes) or h != hashes[n]:
            return n
    if len(hashes) != len(recs) or (anchor is not None and (not hashes or hashes[-1] != anchor)):
        return len(recs) - 1 if recs else 0
    return len(recs)


def load(name):
    """Recordings as lists of (class, sensor_en, used_s2), split on the new-recording flag."""
    recs = []
    for line in open(os.path.join(HERE, 'out', f'cascade_{name}.mem')):
        f = line.split()
        if f[0] == '1':
            recs.append([])
        recs[-1].append(tuple(int(v, 16) for v in f[-4:-1]))
    return recs


def demo(recs):
    """Each tampering is caught at the right window; a rebuilt plain chain is caught only by the anchor."""
    for key in (None, KEY):
        hs = build(recs, key)
        assert verify(recs, hs, key) == len(recs)
        edit = list(recs); edit[10] = ((edit[10][0] + 1) % 5,) + edit[10][1:]
        assert verify(edit, hs, key) == 10                                  # changed class
        assert verify(recs[:10] + recs[11:], hs[:10] + hs[11:], key) == 10  # deleted window
        i = next(i for i in range(len(recs) - 1) if recs[i] != recs[i + 1])
        swap = list(recs); swap[i], swap[i + 1] = swap[i + 1], swap[i]
        assert verify(swap, hs, key) == i                                   # reordered windows
        forged = build(edit)                                                # attacker rebuilds with no key
        assert verify(edit, forged, key, anchor=hs[-1]) < len(recs)
    assert verify(edit, build(edit), None) == len(edit)  # plain chain alone: rebuild passes without an anchor
    assert verify(edit, build(edit), KEY) == 0           # keyed chain: rebuild without the key fails at once
    fs = build(recs, KEY, True)                           # forward-secure: key stolen at window 200 cannot re-sign 100
    k200 = KEY
    for _ in range(200):
        k200 = hashlib.sha256(k200).digest()
    assert verify(recs, fs, KEY, fs=True) == len(recs) and verify(edit, fs, KEY, fs=True) == 10
    assert verify(edit, fs[:10] + build(edit[10:], k200, True, fs[9], 10), KEY, fs=True) == 10
    st = build(recs, KEY)                                 # static key stolen: the same rewrite passes
    assert verify(edit, st[:10] + build(edit[10:], KEY, False, st[9], 10), KEY) == len(edit)
    assert hashlib.sha256(b'abc').hexdigest().startswith('ba7816bf')  # NIST FIPS 180-2 example


def main(name):
    recs = load(name)
    demo(max(recs, key=len))
    lines = []
    for r in recs:
        for (cls, en, used), hp, hk, hf in zip(r, build(r), build(r, KEY), build(r, KEY, True)):
            lines.append(f'{cls:x} {en:x} {used:x} {hp.hex()} {hk.hex()} {hf.hex()}')
    with open(os.path.join(HERE, 'out', f'chain_{name}.mem'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'{name}: {len(recs)} recordings, {len(lines)} windows, tamper checks passed; '
          f'last plain hash {build(recs[-1])[-1].hex()[:16]}...')


if __name__ == '__main__':
    for n in sys.argv[1:] or sorted(os.path.basename(f)[8:-4] for f in glob.glob(os.path.join(HERE, 'out', 'cascade_*.mem'))):
        main(n)
