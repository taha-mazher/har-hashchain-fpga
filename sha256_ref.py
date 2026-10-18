"""SHA-256 compression function (FIPS 180-4) and test vectors for the RTL cores.

compress(h, block) is one 64-round compression with feed-forward: what one call of rtl/sha256_iter.v computes.
hashlib does not expose it, so it is checked here against hashlib and hmac on whole messages.
Writes out/sha256_vectors.mem: lines of  h_in(64 hex) block(128 hex) h_out(64 hex)
  NIST "abc" (1 block), NIST 448-bit message (2 blocks, the second chained), HMAC ipad/opad midstates,
  chain records from chain.py, and random h_in/block pairs.
Also out/sha256_chain_vectors.mem: the real plain-chain workload (first UCI recording, up to 1,000 windows, all from the IV).
"""
import hashlib
import hmac
import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
M = 0xffffffff
K = [int((p ** (1 / 3) % 1) * 2 ** 32) for p in [n for n in range(2, 312) if all(n % d for d in range(2, n))][:64]]
IV = [int((p ** 0.5 % 1) * 2 ** 32) for p in (2, 3, 5, 7, 11, 13, 17, 19)]


def rotr(x, n):
    return (x >> n | x << (32 - n)) & M


def compress(h, block):
    w = list(struct.unpack('>16I', block))
    for t in range(16, 64):
        s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ w[t - 15] >> 3
        s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ w[t - 2] >> 10
        w.append((w[t - 16] + s0 + w[t - 7] + s1) & M)
    a, b, c, d, e, f, g, hh = h
    for t in range(64):
        t1 = (hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + (e & f ^ ~e & g) + K[t] + w[t]) & M
        t2 = ((rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + (a & b ^ a & c ^ b & c)) & M
        a, b, c, d, e, f, g, hh = (t1 + t2) & M, a, b, c, (d + t1) & M, e, f, g
    return [(x + y) & M for x, y in zip(h, (a, b, c, d, e, f, g, hh))]


def pad(msg, prefix_bytes=0):
    """Padded blocks for msg, as if prefix_bytes had already been hashed (64 for HMAC's key block)."""
    n = (len(msg) + prefix_bytes) * 8
    m = msg + b'\x80' + b'\0' * ((55 - len(msg)) % 64) + struct.pack('>Q', n)
    return [m[i:i + 64] for i in range(0, len(m), 64)]


def sha256(msg, h=IV, prefix_bytes=0):
    for b in pad(msg, prefix_bytes):
        h = compress(h, b)
    return h


def hmac_midstates(key):
    k = key.ljust(64, b'\0')
    return compress(IV, bytes(x ^ 0x36 for x in k)), compress(IV, bytes(x ^ 0x5c for x in k))


def hmac_sha256(mid, msg):
    """HMAC from precomputed midstates: what the keyed hardware does (2 compressions for a 37-byte record)."""
    inner = sha256(msg, mid[0], 64)
    return sha256(b''.join(struct.pack('>I', x) for x in inner), mid[1], 64)


def hx(words):
    return ''.join(f'{x:08x}' for x in words)


def main():
    rnd = random.Random(0)
    msgs = [b'abc', b'abcdbcdecdefdefgefghfghighijhijkijkljklmjklmnklmnolmnopmnopnopq', b'', bytes(range(200))]
    for m in msgs:
        assert hx(sha256(m)) == hashlib.sha256(m).hexdigest()
    from chain import KEY
    mid = hmac_midstates(KEY)
    for m in msgs + [bytes(37)]:
        assert hx(hmac_sha256(mid, m)) == hmac.new(KEY, m, 'sha256').hexdigest()

    cases = []
    for m in msgs[:2]:
        h = IV
        for b in pad(m):
            cases.append((h, b)); h = compress(h, b)
    k = KEY.ljust(64, b'\0')
    cases += [(IV, bytes(x ^ 0x36 for x in k)), (IV, bytes(x ^ 0x5c for x in k))]
    rec = bytes(32) + bytes(4) + bytes([0b10000])
    cases += [(IV, pad(rec)[0]), (mid[0], pad(rec, 64)[0])]
    cases += [([rnd.getrandbits(32) for _ in range(8)], rnd.randbytes(64)) for _ in range(200)]
    with open(os.path.join(HERE, 'out', 'sha256_vectors.mem'), 'w') as f:
        f.writelines(f'{hx(h)} {b.hex()} {hx(compress(h, b))}\n' for h, b in cases)
    print(f'reference matches hashlib and hmac; wrote {len(cases)} compression vectors')
    # the plain-chain workload: one block from the IV per window, first 1,000 UCI windows (any core, incl. IV-only)
    from chain import load, record
    prev, lines = bytes(32), []
    for n, r in enumerate(load('uci')[0][:1000]):
        b = pad(record(prev, n, *r))[0]
        prev = b''.join(struct.pack('>I', x) for x in compress(IV, b))
        lines.append(f'{hx(IV)} {b.hex()} {prev.hex()}\n')
    with open(os.path.join(HERE, 'out', 'sha256_chain_vectors.mem'), 'w') as f:
        f.writelines(lines)


if __name__ == '__main__':
    main()
