"""Table of routed results for the plain cascade and every cascade_secure variant (out_sec_*), UCI test set.
Energy per window = average dynamic power (whole design, or one instance from the hierarchy) x simulated time / windows.
The simulated time is the testbench's own pacing (it waits for each hash), so these are per-window energies for
back-to-back windows. Idle = the same netlist held idle after reset (power_idle_mw.rpt); for gated builds the clock
after the BUFGCE is declared stopped (see power_secure.tcl). Per deployed 2.56 s window, the dynamic energy is the
active energy plus idle dynamic power x 2.56 s (the active part lasts microseconds). Static power is not included."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = 5053


def grab(path, pat):
    m = re.search(pat, open(path).read())
    return m.group(1) if m else '0'


rows = []
for tag in ('cascade_uci', 'sec_uci_lite_plain', 'sec_uci_lite_keyed', 'sec_uci_iter_plain', 'sec_uci_iter_keyed',
            'sec_uci_lite_fs', 'sec_uci_lite_plain_g', 'sec_uci_lite_keyed_g', 'sec_uci_lite_fs_g'):
    d = os.path.join(HERE, f'out_{tag}')
    u, t, p = (os.path.join(d, f) for f in ('utilization_routed.rpt', 'timing_routed.rpt', 'power_saif_mw.rpt'))
    log = open(os.path.join(HERE, f'xsim_{tag}.log')).read()
    sim_s = float(grab(os.path.join(HERE, f'xsim_{tag}.log'), r'finish called at time : (\d+) ns')) * 1e-9
    nj = lambda mw: float(mw) * 1e-3 * sim_s / WINDOWS * 1e9
    rows.append((tag, grab(u, r'\| Slice LUTs\s*\|\s*(\d+)'), grab(u, r'\| Slice Registers\s*\|\s*(\d+)'),
                 grab(u, r'\| Slice\s+\|\s*(\d+)'), grab(t, r'WNS\(ns\).*\n.*\n\s*(-?[\d.]+)'),
                 grab(p, r'Total On-Chip Power \(mW\)\s*\|\s*([\d.]+)'), grab(p, r'\| Dynamic \(mW\)\s*\|\s*([\d.]+)'),
                 nj(grab(p, r'\| Dynamic \(mW\)\s*\|\s*([\d.]+)')), nj(grab(p, r'\|\s+core\s+\|\s*([\d.]+)')),
                 'PASS' if 'RESULT: PASS' in log else 'FAIL'))
    ip = os.path.join(d, 'power_idle_mw.rpt')
    idle = float(grab(ip, r'\| Dynamic \(mW\)\s*\|\s*([\d.]+)')) if os.path.exists(ip) else None
    rows[-1] += (idle, None if idle is None else rows[-1][7] / 1e6 + idle * 2.56)

hdr = f"{'design':20s} {'LUTs':>5} {'FFs':>5} {'slices':>6} {'WNS ns':>7} {'total mW':>8} {'dyn mW':>7} {'dyn nJ/win':>10} {'hash nJ/win':>11} {'gate sim':>8} {'idle mW':>8} {'mJ/2.56s win':>12}"
out = [hdr] + [f'{r[0]:20s} {r[1]:>5} {r[2]:>5} {r[3]:>6} {r[4]:>7} {r[5]:>8} {r[6]:>7} {r[7]:>10.1f} {r[8]:>11.1f} {r[9]:>8} {'-' if r[10] is None else f'{r[10]:.3f}':>8} {'-' if r[11] is None else f'{r[11]:.3f}':>12}' for r in rows]
print('\n'.join(out))
with open(os.path.join(HERE, '..', 'out', 'secure_vivado_results.txt'), 'w') as f:
    f.write('\n'.join(out) + '\n')
