# Tamper-evident activity log on FPGA: SHA-256 hash chain on an early-exit HAR cascade

A wearable activity classifier that signs its own history. Every 1.28 s (2.56 s windows with 50% overlap), the FPGA classifies the wearer's activity and folds the result into a SHA-256 hash chain, the same structure a blockchain uses to link blocks. Anyone who later edits, deletes or reorders a logged decision breaks the chain. Publishing the latest hash somewhere outside the device (a server, a ledger, a blockchain) also catches records dropped from the end.

Target uses: soldier and first-responder monitoring, clinical trials and remote patient monitoring, insurance and workplace safety, anywhere a log of what a body did has to hold up later.

The classifier is the sensor-gated cascade from the companion repo `har-sensor-cascade` (included here as `rtl/cascade.v`). Everything is written in Verilog, verified bit for bit against Python, and synthesised for an Artix-7 (xc7a35ticsg324-1L) at 50 MHz in Vivado 2024.2.

## Three security modes

| Mode | What it computes per window | Compressions | Stops |
|---|---|---|---|
| Plain chain | h = SHA-256(record) | 1 | edits, deletions, reordering |
| Keyed (HMAC) | h = HMAC-SHA256(key, record) | 2 | also someone without the key rebuilding the whole chain |
| Forward-secure | HMAC with key k, then k = SHA-256(k) | 5 | also someone who steals the device and reads the current key: old windows used keys that no longer exist |

Each record is 37 bytes and fits one SHA-256 block: previous hash (32 bytes), window number (4 bytes), and one byte holding the class, the second-sensor enable bit and the stage-2 flag. The HMAC inner and outer pads are precomputed as midstates, so keyed mode costs 2 compressions instead of 4. Forward-secure mode follows the evolving-key idea of Schneier and Kelsey (1998) and Bellare and Yee (forward integrity).

## Tamper test

UCI recording 1, 280 windows (`secure_results.py`, `out/secure_tamper.txt`). "Anchor" means the last hash was published off the device.

| Attack | Plain | Plain + anchor | Keyed | Forward-secure | Forward-secure + anchor |
|---|---|---|---|---|---|
| Change one class (window 100) | caught at 100 | caught at 100 | caught at 100 | caught at 100 | caught at 100 |
| Delete one window | caught at 100 | caught at 100 | caught at 100 | caught at 100 | caught at 100 |
| Swap two windows | caught at 114 | caught at 114 | caught at 114 | caught at 114 | caught at 114 |
| Drop the last 10 windows | missed | caught | missed | missed | caught |
| Edit window 100 and recompute every hash (no key) | missed | caught at the end | caught at 0 | caught at 0 | caught at 0 |
| Device stolen at window 200, key read, window 100 rewritten | missed | caught at the end | missed | caught at 100 | caught at 100 |

Truncation needs an anchor in every mode; no key can prove that records you never saw existed.

## Hardware results

UCI cascade with the low-area SHA-256 core, post-route, power from SAIF activity of gate-level simulation on the 5,053 UCI test windows. All builds are bit-exact in gate-level simulation.

| Design | LUTs | FFs | Slices | WNS (ns) | Hash energy per window | Idle power | Idle energy per classification (1.28 s) |
|---|---|---|---|---|---|---|---|
| Cascade alone | 358 | 286 | 126 | +5.63 | n/a | n/a | n/a |
| Plain chain | 1,101 | 1,006 | 376 | +5.13 | 18.8 nJ | 0.906 mW | 1.16 mJ |
| Keyed | 1,228 | 1,010 | 384 | +4.95 | 38.0 nJ | 0.925 mW | 1.18 mJ |
| Forward-secure | 1,716 | 1,532 | 534 | +4.98 | 105 nJ | 1.315 mW | 1.68 mJ |
| Any mode, clock-gated | 1,101 to 1,718 | 1,005 to 1,531 | 382 to 545 | +4.76 to +5.35 | same | 0.059 mW | 0.076 mJ |

The hash is ready 67, 133 or 331 cycles after the classification (plain, keyed, forward-secure).

**The point of the gating result:** the hashing itself costs nanojoules, but a clock left running between windows costs millijoules, as much as the gyroscope the cascade saves by staying off (1.72 mJ for each 1.28 s it stays off, BMI160 at an assumed 1.8 V). Ungated, the idle clock would eat 67 to 98% of that saving; gated, 4.4%. With the clock gated between windows, idle power is 0.059 mW in all three modes, so the strongest protection costs practically the same as none.

### SHA-256 cores on their own

Out of context, same part and flow (`out/secure_compare.txt`):

| Core | Slices | LUTs | FFs | MHz | Cycles | Mbps |
|---|---|---|---|---|---|---|
| This work, standard (`sha256_iter.v`) | 273 | 1,011 | 1,033 | 83.9 | 66 | 651 |
| This work, low-area (`sha256_lite.v`) | 299 | 1,058 | 431 | 66.1 | 65 | 520 |
| secworks open-source core, same flow | 409 | 1,430 | 1,054 | 67.1 | 67 | 513 |

Published figures for Santos et al. 2024, Kieu-Do-Nguyen et al. 2021, Kammoun et al. 2021 and Garcia et al. 2014 are listed in `out/secure_compare.txt`, quoted as reported in Santos et al., Sensors 24:3908, Table 3.

The low-area core keeps the message schedule in a shift-register delay line (SRL), cutting flip-flops by 58%. Inside the full design it wins on every metric, because its output is combinational and does not duplicate the chain register.

## How it works

`rtl/cascade_secure.v` wraps the cascade. When a window's class is ready, a small sequencer feeds one, two or five blocks to the SHA-256 core:

- **Plain:** one block, from the SHA-256 initial value.
- **Keyed:** inner hash from the ipad midstate, parked in the previous-hash register, then the outer hash from the opad midstate.
- **Forward-secure:** ipad block from k, record block, opad block from k, outer block, then k = SHA-256(k).

The 256-bit hash is read out as eight 32-bit words through a `hash_sel` port, to fit the package pins. `rtl/clk_gate.v` is a BUFGCE in synthesis and a latch-and-AND gate in simulation; the clock runs only while there is work in flight. One record is processed at a time.

Parameters: `KEYED` (0 plain, 1 HMAC, 2 forward-secure), `LITE` (core choice), `GATE` (clock gating), plus the cascade's own parameters.

## Repository layout

```
chain.py              Python golden model: builds plain / keyed / forward-secure chains, verify(), tamper self-check,
                      writes out/chain_<name>.mem (expected hash per window)
sha256_ref.py         SHA-256 compression function written out by hand, checked against hashlib/hmac; core test vectors
secure_results.py     tamper table, comparison with published cores, energy figure

rtl/cascade_secure.v  cascade + hash chain top level
rtl/cascade.v         the classifier (from har-sensor-cascade)
rtl/sha256_iter.v     SHA-256 core, one round per cycle
rtl/sha256_lite.v     low-area SHA-256 core
rtl/sha256_secworks.v wrapper for the third-party secworks core (comparison only)
rtl/clk_gate.v        clock gate
rtl/tb_*.v, run_*.sh  testbenches and Icarus Verilog scripts
rtl/mem/              classifier ROMs per model

vivado/               build, SAIF and power scripts; out_*/ holds the routed reports
out/                  test vectors, expected chains, result tables, simulation logs
paper_secure/         AEJ manuscript builder (build_paper.py, refs.json) and its figures
paper_secure_figures.py  architecture figure and graphical abstract (uses helpers from paper_figures.py)
third_party/          secworks SHA-256 (BSD 2-clause, see its LICENSE)
```

## Reproducing

**Python** 3.10+ with numpy and matplotlib. The test key is `bytes(range(32))`, for testing only.

```
python sha256_ref.py      # core test vectors
python chain.py           # tamper self-check, then expected chains for every model
python secure_results.py  # tables and figure
```

**Simulation** (Icarus Verilog, e.g. in WSL):

```
bash rtl/run_sha_sim.sh       # both cores against 207 vectors plus the real chain workload
bash rtl/run_secure_sim.sh    # full design: every model x core x mode x gating
```

108 of 108 full-design runs are bit-exact (UCI plus 8 PAMAP2 subjects, both cores, three modes, gated and ungated): every one of the 8 hash words matches Python on every window.

**Vivado** 2024.2 (free Standard edition). From `vivado/`:

```
powershell -File run_secure.ps1 -Name cascade_uci -Lite 1 -Keyed 2 -Gate 1 -Tag sec_uci_lite_fs_g
python collect_secure.py      # -> out/secure_vivado_results.txt
```

`run_secure_all.ps1` and `run_secure_v2.ps1` build every variant in the tables. Scripts assume Vivado at `C:\Xilinx\Vivado\2024.2`.

## Paper

The AEJ manuscript is generated by `paper_secure/build_paper.py` from the author's previous AEJ Word file, which is not in this repo. The built .docx and .pdf are kept out until the paper is published.

## Limitations

- **No board yet.** All figures are simulation plus Vivado post-route estimates; nothing is measured on hardware.
- **Static power dominates.** The Artix-7 draws about 58 to 60 mW static (about 77 mJ per classification), far more than everything above. The results are about dynamic cost; a deployed device would need a low-static FPGA or an ASIC.
- **Gated idle power needs a modelling step.** Vivado's power tool ignores both the SAIF activity on a clock net and the BUFGCE enable, so it reports gated idle power equal to ungated. `vivado/power_secure.tcl` models the stopped clock with `create_generated_clock -divide_by 1000000` on the gate output. That is a stated assumption, not a measurement.
- **Key storage is out of scope.** The key is a synthesis parameter. A real device would keep it in eFUSE or a secure element.
- **One record in flight.** Fine at one window per 1.28 s; a faster sensor stream would need a queue.

## Third-party code

`third_party/secworks_sha256` is Joachim Strömbergson's SHA-256 core (BSD 2-clause), used only as a comparison baseline under the same synthesis flow.
