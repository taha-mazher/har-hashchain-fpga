#!/bin/bash
# Bit-exact check of cascade_secure.v (cascade + hash chain) on every exported model, for both SHA-256 cores
# and every chain mode, with and without clock gating. Run from WSL.
# Usage: [LITES="1 0"] [KEYS="0 1 2"] [GATES="0 1"] run_secure_sim.sh [cascade_uci cascade_pamap2_101 ...] (default: all)
set -e
cd "$(dirname "$0")"
if command -v iverilog >/dev/null; then IV=iverilog; VVP=vvp; IVB=; VVM=
else
    R=~/iverilog-local/root; L=$R/usr/lib/x86_64-linux-gnu
    export LD_LIBRARY_PATH=$L
    IV=$R/usr/bin/iverilog; VVP=$R/usr/bin/vvp; IVB=-B$L/ivl; VVM=-M$L/ivl
fi
T=tb_cascade_secure
for name in ${@:-$(cd mem && ls -d cascade_*)}; do
    d=mem/$name/
    P=$(tr -d '\r\n' < "$d/params.txt" | sed "s/\([A-Z_0-9]*\)=/-P $T.\1=/g")
    for lite in ${LITES:-1 0}; do for keyed in ${KEYS:-0 1 2}; do for gate in ${GATES:-0 1}; do
        echo "== $name lite=$lite keyed=$keyed gate=$gate"
        $IV $IVB -g2005 $P -P $T.MEM_DIR=\"$d\" -P $T.TEST_FILE=\"../out/$name.mem\" \
            -P $T.CHAIN_FILE=\"../out/chain_${name#cascade_}.mem\" -P $T.KEYED=$keyed -P $T.LITE=$lite -P $T.GATE=$gate \
            -o /tmp/sec_$name $T.v cascade_secure.v cascade.v sha256_lite.v sha256_iter.v clk_gate.v
        $VVP $VVM /tmp/sec_$name | grep -E "windows=|RESULT|MISMATCH|TIMEOUT"
    done; done; done
done
