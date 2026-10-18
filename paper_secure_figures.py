"""Figures for the hash-chain paper (AEJ). Writes PNGs to hw_fix/paper_secure/. The energy figure is made by secure_results.py.

fig_arch.png: architecture of cascade_secure.v
fig_ga.png  : graphical abstract, sized for the AEJ box (3.13 x 2.54 in)
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from paper_figures import C, INK, MUTED, NL, arrow, box, note

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper_secure')


def fig_arch():
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.set_xlim(0, 15.4); ax.set_ylim(0, 6.4); ax.axis('off')
    ax.add_patch(FancyBboxPatch((0.1, 0.25), 11.9, 5.85, boxstyle='round,pad=0.02,rounding_size=0.1',
                                fc='#f6f6f4', ec=MUTED, lw=0.8, ls='--'))
    ax.text(1.45, 5.65, 'FPGA (Artix-7)', ha='center', fontsize=6.8, color=MUTED)
    box(ax, 0.3, 3.9, 2.3, 1.2, ['Early-exit', 'cascade'], fc='#e8f0fb', bold=True)
    box(ax, 0.3, 2.2, 2.3, 1.0, ['Window', 'counter n'])
    box(ax, 3.4, 2.7, 2.5, 1.6, ['Record builder', 'prev | n | class,', 'sensor_en, used_s2'])
    box(ax, 6.9, 2.7, 2.2, 1.6, ['SHA-256 core', '1 round', 'per cycle'], fc='#fdeee7', bold=True)
    box(ax, 9.9, 2.7, 1.7, 1.6, ['Chain', 'register', 'h(n)'], fc='#e9f7f1')
    box(ax, 6.9, 4.75, 2.2, 0.9, ['Key k', 'k <- SHA-256(k)'])
    box(ax, 3.4, 0.5, 8.2, 0.8, ['Sequencer: 1, 2 or 5 compressions per window'], fs=6.3)
    box(ax, 0.3, 0.5, 2.3, 0.8, ['Clock gate', '(BUFGCE)'], fc='#fdf3d9', fs=6)
    box(ax, 12.8, 2.7, 2.5, 1.6, ['Off-device', 'anchor', '(server, ledger)'], fc='white')
    arrow(ax, 2.6, 4.5, 3.4, 3.8)
    arrow(ax, 2.6, 2.7, 3.4, 3.2)
    arrow(ax, 5.9, 3.5, 6.9, 3.5)
    arrow(ax, 9.1, 3.5, 9.9, 3.5)
    ax.plot([10.75, 10.75, 4.65], [2.7, 2.1, 2.1], color=INK, lw=1)
    arrow(ax, 4.65, 2.1, 4.65, 2.7)
    note(ax, 7.7, 1.75, ['prev = h(n-1)'], ha='center')
    ax.annotate('', (8.0, 4.3), (8.0, 4.75), arrowprops=dict(arrowstyle='-|>', color=C[1], lw=1.1, ls='--'))
    note(ax, 9.25, 5.2, ['forward-secure', 'mode only'], color=C[1])
    arrow(ax, 11.6, 3.5, 12.8, 3.5)
    fig.savefig(os.path.join(OUT, 'fig_arch.png'), dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def fig_graphical_abstract():
    fig, ax = plt.subplots(figsize=(3.13, 2.54))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8.1); ax.axis('off')
    fs = 6.2
    box(ax, 0.1, 6.3, 2.6, 1.3, ['Wearable', 'sensors'], fc='#e8f0fb', fs=fs)
    box(ax, 3.4, 6.3, 3.0, 1.3, ['HAR cascade', 'on FPGA'], fc='#e8f0fb', fs=fs, bold=True)
    box(ax, 7.1, 6.3, 2.8, 1.3, ['Activity', 'per window'], fc='#e9f7f1', fs=fs)
    arrow(ax, 2.7, 6.95, 3.4, 6.95); arrow(ax, 6.4, 6.95, 7.1, 6.95)
    for i, lab in enumerate(['h(n-2)', 'h(n-1)', 'h(n)']):
        box(ax, 0.6 + i * 3.0, 3.75, 2.2, 1.1, [lab], fc='#fdeee7', fs=fs, bold=True)
        if i:
            arrow(ax, 2.8 + (i - 1) * 3.0, 4.3, 3.6 + (i - 1) * 3.0, 4.3)
    note(ax, 5.0, 3.25, ['SHA-256 hash chain, one link per window'], color=C[1], ha='center')
    ax.annotate('', (7.7, 4.85), (8.5, 6.3), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1))
    ax.add_patch(FancyBboxPatch((0.1, 0.15), 9.8, 2.55, boxstyle='round,pad=0.02,rounding_size=0.1', fc='#f6f6f4', ec=MUTED, lw=0.8))
    ax.text(5.0, 2.2, 'Edits, deletions and reordering caught at the exact window', ha='center', fontsize=5.6, color=INK)
    ax.text(2.6, 0.95, NL.join(['Forward-secure HMAC', '1,716 LUTs, 105 nJ']), ha='center', fontsize=6, color=INK, weight='bold')
    ax.text(7.4, 0.95, NL.join(['Idle, clock gated', '0.059 mW in every mode']), ha='center', fontsize=6, color=C[1], weight='bold')
    fig.savefig(os.path.join(OUT, 'fig_ga.png'), dpi=400, bbox_inches='tight', facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    fig_arch()
    fig_graphical_abstract()
