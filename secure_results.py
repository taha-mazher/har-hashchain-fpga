"""Phase 5 results for the hash-chain paper: tamper table, comparison with published SHA-256 cores, energy figure.
Writes out/secure_tamper.txt, out/secure_compare.txt and paper_secure/fig_energy.png.
Hardware numbers come from vivado/out_sha_* (core alone, out of context) and out/secure_vivado_results.txt.
"""
import hashlib
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from chain import KEY, build, load, verify

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')


def tamper():
    recs = load('uci')[0]
    k200 = KEY
    for _ in range(200):
        k200 = hashlib.sha256(k200).digest()
    modes = {'plain': (None, False), 'keyed': (KEY, False), 'forward-secure': (KEY, True)}
    i = next(i for i in range(100, len(recs) - 1) if recs[i] != recs[i + 1])
    edit = list(recs); edit[100] = ((edit[100][0] + 1) % 5,) + edit[100][1:]
    swap = list(recs); swap[i], swap[i + 1] = swap[i + 1], swap[i]
    attacks = {  # name: f(true hashes, key, fs) -> (records shown to the verifier, hashes shown)
        'Change one class (window 100)': lambda h, k, fs: (edit, h),
        'Delete one window (100)': lambda h, k, fs: (recs[:100] + recs[101:], h[:100] + h[101:]),
        f'Swap two windows ({i}, {i + 1})': lambda h, k, fs: (swap, h),
        'Drop the last 10 windows': lambda h, k, fs: (recs[:-10], h[:-10]),
        'Change window 100, recompute all hashes (no key)': lambda h, k, fs: (edit, build(edit)),
        'Device stolen at 200, key read, window 100 rewritten':
            lambda h, k, fs: (edit, h[:100] + build(edit[100:], (k200 if fs else k), fs, h[99], 100)),
    }
    head = f'{"Attack (UCI recording 1, " + str(len(recs)) + " windows)":53s}' + ''.join(
        f' {m + a:>{len(m + a) + 1}s}' for m in modes for a in ('', ' + anchor'))
    rows = [head]
    for name, f in attacks.items():
        cells = []
        for m, (key, fs) in modes.items():
            h = build(recs, key, fs)
            for anchor in (None, h[-1]):
                r, hs = f(h, key, fs)
                n = verify(r, hs, key, anchor, fs)
                cells.append(f'{"missed" if n == len(r) else "caught at " + str(n):>{len(m) + 1}s}')
                cells[-1] = f'{cells[-1]:>{len(m + (" + anchor" if anchor else "")) + 1}s}'
        rows.append(f'{name:53s}' + ''.join(f' {c}' for c in cells))
    return rows


def grab(path, pat):
    return re.search(pat, open(path).read()).group(1)


def compare():
    rows = [f'{"SHA-256 core":38s} {"FPGA":22s} {"slices":>6s} {"LUTs":>5s} {"FFs":>5s} {"MHz":>6s} {"cycles":>6s} {"Mbps":>6s}  source']
    for tag, name, cyc in (('sha_iter', 'This work, standard (sha256_iter)', 66), ('sha_lite', 'This work, low-area (sha256_lite)', 65),
                           ('sha_sw', 'secworks (open source), same flow', 67)):
        d = os.path.join(HERE, 'vivado', f'out_{tag}')
        u, t = os.path.join(d, 'utilization_routed.rpt'), os.path.join(d, 'timing_routed.rpt')
        mhz = 1000 / (20 - float(grab(t, r'WNS\(ns\).*\n.*\n\s*(-?[\d.]+)')))
        rows.append(f'{name:38s} {"Artix-7 xc7a35t":22s} {grab(u, r"\| Slice\s+\|\s*(\d+)"):>6s} {grab(u, r"\| Slice LUTs\s*\|\s*(\d+)"):>5s} '
                    f'{grab(u, r"\| Slice Registers\s*\|\s*(\d+)"):>5s} {mhz:6.1f} {cyc:6d} {512 * mhz / cyc:6.0f}  measured, MHz = 1/(20 ns - slack)')
    for r in (('Santos et al. 2024, 1 core', 'Virtex-6', '1933', '6730', '794', '12.67', '65', '100', '[Sensors 24:3908, Tables 1, 3]'),
              ('Kieu-Do-Nguyen et al. 2021', 'Artix-7 / Zynq-7000', '327', '-', '-', '141.84', '-', '1404', 'as reported in Santos Table 3'),
              ('Kammoun et al. 2021', 'Zynq-7000 XC7Z020', '1305', '-', '-', '135', '-', '1063', 'as reported in Santos Table 3'),
              ('Garcia et al. 2014', 'Virtex-5', '139', '-', '-', '64.45', '-', '118', 'as reported in Santos Table 3')):
        rows.append(f'{r[0]:38s} {r[1]:22s} {r[2]:>6s} {r[3]:>5s} {r[4]:>5s} {r[5]:>6s} {r[6]:>6s} {r[7]:>6s}  {r[8]}')
    return rows


def energy_fig():
    sec = {l.split()[0]: l.split() for l in open(os.path.join(OUT, 'secure_vivado_results.txt')).read().splitlines()[1:]}
    gyro_mj = 745e-6 * 1.8 * 2.56 * 1e3   # BMI160: 925 uA both sensors - 180 uA accel only, 1.8 V, one 2.56 s window
    idle = lambda t: float(sec[t][10]) * 2.56 * 1e6   # idle dynamic mW x 2.56 s, in nJ
    bars = [('Cascade inference (active)', float(sec['cascade_uci'][7]), '#2a78d6'),
            ('SHA-256 link (active)', float(sec['sec_uci_lite_plain'][8]), '#eb6834'),
            ('HMAC link (active)', float(sec['sec_uci_lite_keyed'][8]), '#eb6834'),
            ('Forward-secure link (active)', float(sec['sec_uci_lite_fs'][8]), '#eb6834'),
            ('Idle clock, clock gated', idle('sec_uci_lite_fs_g'), '#eda100'),
            ('Idle clock, not gated', idle('sec_uci_lite_plain'), '#eda100'),
            ('Gyroscope kept off (saved)', gyro_mj * 1e6, '#1baf7a')]
    fig, ax = plt.subplots(figsize=(6.5, 3.4), dpi=200)
    y = range(len(bars))
    ax.barh(y, [b[1] for b in bars], color=[b[2] for b in bars], height=0.55)
    ax.set_xscale('log')
    ax.set_yticks(list(y), [b[0] for b in bars], fontsize=8)
    ax.invert_yaxis()
    for i, (_, v, _) in enumerate(bars):
        ax.text(v * 1.3, i, f'{v / 1e6:.2f} mJ' if v > 1e5 else f'{v:.1f} nJ', va='center', fontsize=8, color='#333333')
    ax.set_xlim(1, 3e7)
    ax.set_xlabel('Dynamic energy per 2.56 s window (nJ, log scale)', fontsize=8)
    ax.tick_params(axis='x', labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.grid(axis='x', color='#e5e5e5', linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    os.makedirs(os.path.join(HERE, 'paper_secure'), exist_ok=True)
    fig.savefig(os.path.join(HERE, 'paper_secure', 'fig_energy.png'))
    return gyro_mj


def main():
    for name, rows in (('secure_tamper.txt', tamper()), ('secure_compare.txt', compare())):
        print('\n'.join(rows) + '\n')
        with open(os.path.join(OUT, name), 'w') as f:
            f.write('\n'.join(rows) + '\n')
    print(f'gyroscope saving per window {energy_fig():.2f} mJ; figure written')


if __name__ == '__main__':
    main()
